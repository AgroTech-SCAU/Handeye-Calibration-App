'use strict'

// GPU-backed read-only renderer for the HandEye model inspector
// Uses the same WebGL rasterization approach as the SerialArm-Core viewer
// Geometry is uploaded once and camera interaction updates only the view matrix
;(function(){
  const sub=(a,b)=>a.map((v,i)=>v-b[i])
  const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
  const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
  const length=a=>Math.hypot(...a)
  const normal=a=>{const m=length(a);return m<1e-10?[0,0,1]:a.map(v=>v/m)}
  const add=(a,b)=>a.map((v,i)=>v+b[i])
  const scale=(a,k)=>a.map(v=>v*k)
  const m4=(m)=>m?m.flat():[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
  const pt=(m,p)=>[m[0]*p[0]+m[1]*p[1]+m[2]*p[2]+m[3],m[4]*p[0]+m[5]*p[1]+m[6]*p[2]+m[7],m[8]*p[0]+m[9]*p[1]+m[10]*p[2]+m[11]]
  function perspective(fov,aspect,near,far){const f=1/Math.tan(fov/2),nf=1/(near-far);return [f/aspect,0,0,0,0,f,0,0,0,0,(far+near)*nf,-1,0,0,2*far*near*nf,0]}
  function lookAt(eye,center){
    const z=normal(sub(eye,center)),x=normal(cross([0,0,1],z)),y=cross(z,x)
    return [x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1]
  }
  function mult(a,b){const m=new Float32Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++)for(let k=0;k<4;k++)m[c*4+r]+=a[k*4+r]*b[c*4+k];return m}
  function shader(gl,type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)){const e=gl.getShaderInfoLog(s);gl.deleteShader(s);throw Error(`WebGL shader: ${e}`)}return s}
  function program(gl,vs,fs){const p=gl.createProgram(),a=shader(gl,gl.VERTEX_SHADER,vs),b=shader(gl,gl.FRAGMENT_SHADER,fs);gl.attachShader(p,a);gl.attachShader(p,b);gl.linkProgram(p);gl.deleteShader(a);gl.deleteShader(b);if(!gl.getProgramParameter(p,gl.LINK_STATUS)){const e=gl.getProgramInfoLog(p);gl.deleteProgram(p);throw Error(`WebGL link: ${e}`)}return p}
  const MESH_VS=`attribute vec3 a_position; attribute vec3 a_normal; uniform mat4 u_vp; varying float v_shade; void main(){gl_Position=u_vp*vec4(a_position,1.);vec3 n=normalize(a_normal);float key=abs(dot(n,normalize(vec3(.55,-.45,.75))));float fill=abs(dot(n,normalize(vec3(-.60,.35,.60))));v_shade=0.50+0.35*key+0.18*fill;}`
  const MESH_FS=`precision mediump float; varying float v_shade;uniform vec4 u_color; void main(){gl_FragColor=vec4(u_color.rgb*v_shade,u_color.a);}`
  const LINE_VS=`attribute vec3 a_position; attribute vec4 a_color;uniform mat4 u_vp;varying vec4 v_color;void main(){gl_Position=u_vp*vec4(a_position,1.);v_color=a_color;}`
  const LINE_FS=`precision mediump float;varying vec4 v_color;void main(){gl_FragColor=v_color;}`
  function hexColor(name){let hash=3;for(const c of name)hash=(hash*31+c.charCodeAt(0))%360;const hue=(hash%65)+190,lit=((hash%20)+58)/100,sat=.16;const channel=(n)=>{let k=(n+hue/30)%12;return lit-sat*Math.min(lit,1-lit)*Math.max(-1,Math.min(k-3,9-k,1))};return [channel(0),channel(8),channel(4),1]}
  // A bounded fallback for environments where WebGL creation is blocked by drivers/policy
  // On capable hardware the GPU path above/below is always used
  class CanvasFallback {
    constructor(canvas){this.canvas=canvas;this.ctx=canvas.getContext('2d',{alpha:false});this.tris=[];this.pending=0;this.view=null;this.disposed=false;this.mode='canvas-fallback'}
    upload(tris){this.tris=tris}
    schedule(view){this.view=view;if(this.pending||this.disposed)return;this.pending=requestAnimationFrame(()=>{this.pending=0;if(!this.disposed)this.render(this.view)})}
    render(view){
      if(!view||!this.ctx)return
      const bounds=this.canvas.getBoundingClientRect(),w=Math.max(2,Math.round(bounds.width)),h=Math.max(2,Math.round(bounds.height))
      if(w<3||h<3)return
      if(this.canvas.width!==w||this.canvas.height!==h){this.canvas.width=w;this.canvas.height=h}
      const ctx=this.ctx;ctx.fillStyle='#101827';ctx.fillRect(0,0,w,h)
      const z=normal([Math.cos(view.pitch)*Math.sin(view.yaw),Math.cos(view.pitch)*Math.cos(view.yaw),Math.sin(view.pitch)])
      const x=normal(cross([0,0,1],z)),y=cross(z,x),eye=add(view.target,scale(z,view.distance)),f=Math.min(w,h)*1.15
      const project=p=>{const d=sub(p,eye),depth=-dot(d,z);return depth>.002?{x:w/2+dot(d,x)*f/depth,y:h/2-dot(d,y)*f/depth,z:depth}:null}
      const visible=[],max=1700,stride=Math.max(1,Math.ceil(this.tris.length/max))
      for(let i=0;i<this.tris.length;i+=stride){const tri=this.tris[i];if(!view.layers[tri.layer])continue
        const projected=tri.v.map(project);if(projected.some(p=>!p))continue
        const nn=normal(cross(sub(tri.v[1],tri.v[0]),sub(tri.v[2],tri.v[0])))
        const light=.58+.38*Math.abs(dot(nn,[.35,.55,.76]))
        visible.push({p:projected,z:projected.reduce((v,p)=>v+p.z,0)/3,tri,light})
      }
      visible.sort((a,b)=>b.z-a.z)
      for(const {p,tri,light} of visible){ctx.beginPath();ctx.moveTo(p[0].x,p[0].y);ctx.lineTo(p[1].x,p[1].y);ctx.lineTo(p[2].x,p[2].y);ctx.closePath()
        if(tri.layer==='collision')ctx.fillStyle='rgba(62,150,228,.28)'
        else if(tri.name===view.selected)ctx.fillStyle=`rgba(245,172,77,${Math.min(light,1)})`
        else if(tri.color?.length>=3)ctx.fillStyle=`rgb(${Math.round(tri.color[0]*light*255)},${Math.round(tri.color[1]*light*255)},${Math.round(tri.color[2]*light*255)})`
        else ctx.fillStyle=`rgb(${Math.round(light*137)},${Math.round(light*154)},${Math.round(light*170)})`
        ctx.fill()
      }
      const drawLine=(p,q,color)=>{const a=project(p),b=project(q);if(!a||!b)return;ctx.strokeStyle=color;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke()}
      ctx.lineWidth=1.1
      const gridRadius=Math.max(.25,Math.min(1.2,view.distance*.48)),step=gridRadius/5
      for(let i=-5;i<=5;i++){
        drawLine([i*step,-gridRadius,0],[i*step,gridRadius,0],'rgba(145,166,190,.16)')
        drawLine([-gridRadius,i*step,0],[gridRadius,i*step,0],'rgba(145,166,190,.16)')
      }
      const axis=(matrix,full)=>{const m=m4(matrix),o=pt(m,[0,0,0]);let len=full?.10:.075
        for(const [index,color] of [[0,'#ff6868'],[1,'#43d995'],[2,'#609afa']]){const p=[0,0,0];p[index]=len;drawLine(o,pt(m,p),color)}
      }
      if(view.layers.frames){for(const [name,m] of Object.entries(view.data.frames||{}))if(name===view.selected||name===view.data.root)axis(m,name===view.selected)}
      if(view.layers.joints){for(const joint of view.data.joints||[]){if(joint.kind==='fixed')continue;const m=view.data.frames?.[joint.child];if(m)drawLine(pt(m4(m),[0,0,0]),pt(m4(m),scale(joint.axis||[0,0,1],.13)),'#ffb33c')}}
      if(view.layers.camera){if(view.data.camera_frame)axis(view.data.camera_frame.transform,true);if(view.data.board_frame)axis(view.data.board_frame.transform,true)}
    }
    dispose(){this.disposed=true;if(this.pending)cancelAnimationFrame(this.pending);this.tris=[];this.view=null}
  }
  class GPUScene {
    constructor(canvas){
      this.canvas=canvas
      const gl=canvas.getContext('webgl',{antialias:true,alpha:false,depth:true,preserveDrawingBuffer:false,powerPreference:'high-performance'})
      if(!gl)return new CanvasFallback(canvas)
      this.gl=gl;this.mode='webgl'
      this.meshProgram=program(gl,MESH_VS,MESH_FS);this.lineProgram=program(gl,LINE_VS,LINE_FS)
      this.meshLocations={position:gl.getAttribLocation(this.meshProgram,'a_position'),normal:gl.getAttribLocation(this.meshProgram,'a_normal'),vp:gl.getUniformLocation(this.meshProgram,'u_vp'),color:gl.getUniformLocation(this.meshProgram,'u_color')}
      this.lineLocations={position:gl.getAttribLocation(this.lineProgram,'a_position'),color:gl.getAttribLocation(this.lineProgram,'a_color'),vp:gl.getUniformLocation(this.lineProgram,'u_vp')}
      this.batches=[];this.lines=null;this.pending=0;this.view=null;this.disposed=false
      gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA)
      this.contextLost=e=>{e.preventDefault();this.lost=true}
      this.canvas.addEventListener('webglcontextlost',this.contextLost,false)
    }
    upload(tris){
      const gl=this.gl
      this.batches.forEach(x=>gl.deleteBuffer(x.buffer));this.batches=[]
      const groups=new Map()
      for(const tri of tris){
        const rgba=Array.isArray(tri.color)&&tri.color.length>=3?tri.color.slice(0,4):hexColor(tri.name)
        while(rgba.length<4)rgba.push(1)
        const key=JSON.stringify([tri.name,tri.layer,rgba])
        let group=groups.get(key)
        if(!group){group={name:tri.name,layer:tri.layer,color:rgba,data:[]};groups.set(key,group)}
        const [a,b,c]=tri.v,n=normal(cross(sub(b,a),sub(c,a)))
        for(const p of tri.v)group.data.push(...p,...n)
      }
      for(const group of groups.values()){
        const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer)
        gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(group.data),gl.STATIC_DRAW)
        this.batches.push({name:group.name,layer:group.layer,color:group.color,buffer,count:group.data.length/6})
      }
      gl.bindBuffer(gl.ARRAY_BUFFER,null)
    }
    schedule(view){if(this.disposed)return;this.view=view;if(this.pending)return;this.pending=requestAnimationFrame(()=>{this.pending=0;if(!this.disposed&&this.view&&!this.lost)this.render(this.view)})}
    buildLines(view){
      const values=[]
      const line=(p,q,rgba)=>{values.push(...p,...rgba,...q,...rgba)}
      const gridRadius=Math.max(.25,Math.min(1.2,view.distance*.48)),step=gridRadius/5
      for(let i=-5;i<=5;i++){
        line([i*step,-gridRadius,0],[i*step,gridRadius,0],[.37,.43,.53,.11])
        line([-gridRadius,i*step,0],[gridRadius,i*step,0],[.37,.43,.53,.11])
      }
      const axis=(matrix,selected)=>{if(!matrix)return;const m=m4(matrix),o=pt(m,[0,0,0]);const dim=selected?.13:.088;const alpha=selected?1:.8
        for(const [idx,color] of [[0,[1,.33,.32,alpha]],[1,[.30,.9,.55,alpha]],[2,[.33,.57,1,alpha]]]){
          const p=[0,0,0];p[idx]=dim
          const tip=pt(m,p)
          line(o,tip,color)
          // Two small fins provide an arrowhead to indicate the positive axis
          const back=[0,0,0];back[idx]=dim*.78
          const other=(idx+1)%3
          for(const sign of [-1,1]){
            const arm=back.slice();arm[other]=sign*dim*.095
            line(tip,pt(m,arm),color)
          }
        }
      }
      if(view.layers.frames){
        for(const [name,m] of Object.entries(view.data.frames||{}))if(name===view.selected||name===view.data.root)axis(m,name===view.selected)
      }
      if(view.layers.joints){
        for(const joint of view.data.joints||[]){if(joint.kind==='fixed')continue;const matrix=view.data.frames?.[joint.child];if(!matrix)continue;const m=m4(matrix);line(pt(m,[0,0,0]),pt(m,scale(joint.axis||[0,0,1],.13)),[1,.70,.18,1])}
      }
      if(view.layers.camera){if(view.data.camera_frame)axis(view.data.camera_frame.transform,true);if(view.data.board_frame)axis(view.data.board_frame.transform,true)}
      return new Float32Array(values)
    }
    render(view){
      const gl=this.gl,canvas=this.canvas,rect=canvas.getBoundingClientRect()
      if(rect.width<2||rect.height<2)return
      const dpr=Math.min(devicePixelRatio||1,1.5),w=Math.max(2,Math.round(rect.width*dpr)),h=Math.max(2,Math.round(rect.height*dpr))
      if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h}
      gl.viewport(0,0,w,h)
      gl.clearColor(.078,.105,.15,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT)
      const eye=add(view.target,scale([Math.cos(view.pitch)*Math.sin(view.yaw),Math.cos(view.pitch)*Math.cos(view.yaw),Math.sin(view.pitch)],view.distance))
      const vp=mult(perspective(Math.PI/4.7,w/h,Math.max(view.distance/10000,.001),Math.max(view.distance*100,50)),lookAt(eye,view.target))
      const ml=this.meshLocations
      gl.useProgram(this.meshProgram);gl.uniformMatrix4fv(ml.vp,false,vp)
      gl.enableVertexAttribArray(ml.position);gl.enableVertexAttribArray(ml.normal)
      for(const batch of this.batches){if(!view.layers[batch.layer])continue
        gl.bindBuffer(gl.ARRAY_BUFFER,batch.buffer)
        gl.vertexAttribPointer(ml.position,3,gl.FLOAT,false,24,0)
        gl.vertexAttribPointer(ml.normal,3,gl.FLOAT,false,24,12)
        const selected=batch.name===view.selected,c=batch.color,alpha=batch.layer==='collision'?.24:(selected?1:c[3])
        const highlight=selected?[1,.70,.32]:c
        gl.uniform4f(ml.color,highlight[0],highlight[1],highlight[2],alpha)
        gl.depthMask(batch.layer!=='collision')
        gl.drawArrays(gl.TRIANGLES,0,batch.count)
      }
      gl.depthMask(true);gl.disableVertexAttribArray(ml.position);gl.disableVertexAttribArray(ml.normal)
      const lineVerts=this.buildLines(view)
      if(lineVerts.length){
        if(!this.lines)this.lines=gl.createBuffer()
        gl.bindBuffer(gl.ARRAY_BUFFER,this.lines);gl.bufferData(gl.ARRAY_BUFFER,lineVerts,gl.DYNAMIC_DRAW)
        const ln=this.lineLocations
        gl.useProgram(this.lineProgram);gl.uniformMatrix4fv(ln.vp,false,vp)
        gl.enableVertexAttribArray(ln.position);gl.enableVertexAttribArray(ln.color)
        gl.vertexAttribPointer(ln.position,3,gl.FLOAT,false,28,0);gl.vertexAttribPointer(ln.color,4,gl.FLOAT,false,28,12)
        gl.disable(gl.DEPTH_TEST)
        gl.drawArrays(gl.LINES,0,lineVerts.length/7)
        gl.enable(gl.DEPTH_TEST)
        gl.disableVertexAttribArray(ln.position);gl.disableVertexAttribArray(ln.color)
      }
      gl.bindBuffer(gl.ARRAY_BUFFER,null)
    }
    dispose(){
      this.disposed=true;if(this.pending)cancelAnimationFrame(this.pending)
      this.canvas.removeEventListener('webglcontextlost',this.contextLost,false)
      const gl=this.gl
      this.batches.forEach(x=>gl.deleteBuffer(x.buffer));this.batches=[]
      if(this.lines)gl.deleteBuffer(this.lines)
      gl.deleteProgram(this.meshProgram);gl.deleteProgram(this.lineProgram)
      this.view=null
    }
  }
  window.HandeyeGPUScene=GPUScene
})()
