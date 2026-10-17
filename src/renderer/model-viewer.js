'use strict'

// GPU-accelerated read-only Description viewer
// Model poses come exclusively from the backend's verified URDF transform resolver
;(function(){
  const $=(sel,root=document)=>root.querySelector(sel)
  const tr=(key)=>({
    viewer:'机械臂模型查看',tree:'Link / Joint',layers:'图层',visual:'外观模型',collision:'碰撞模型',frames:'坐标系',joints:'关节轴',camera:'相机 / 棋盘',select:'点击 Link 查看坐标',illustrative:'模型零位示意姿态',live:'真实 JointState 姿态',refresh:'刷新姿态',reset:'复位视角',close:'关闭',status:'状态',reference:'Frame 坐标来自已校验的 URDF 运动学模型',missing:'部分网格资源缺失，使用骨架和关节坐标显示',empty:'当前模型没有可显示的三维几何',help:'左键旋转 · 右键 / Shift 平移 · 滚轮缩放',base:'模型根坐标系',joint:'关联关节',matrix:'相对于模型根 Frame 的变换',noRobot:'末端 TransformStamped 不能反算完整关节角，仅绘制模型零位姿态',load:'正在加载模型几何',noPose:'当前没有有效的完整关节状态',error:'模型预览失败',stale:'历史标定板位置，不是实时测量',size:'模型 Link 数量',triangles:'网格三角面',axisLegend:'坐标轴图例',axisX:'X · 红色',axisY:'Y · 绿色',axisZ:'Z · 蓝色',axisJoint:'关节轴 · 橙色',dragHint:'拖动模型 · 左键旋转 · 右键平移 · 滚轮缩放'}[key]||key)
  const ident=()=>[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
  const mul=(a,b)=>{const m=Array(16).fill(0);for(let r=0;r<4;r++)for(let c=0;c<4;c++)for(let k=0;k<4;k++)m[r*4+c]+=a[r*4+k]*b[k*4+c];return m}
  const m4=(matrix)=>matrix?matrix.flat():ident()
  const pt=(m,p)=>[m[0]*p[0]+m[1]*p[1]+m[2]*p[2]+m[3],m[4]*p[0]+m[5]*p[1]+m[6]*p[2]+m[7],m[8]*p[0]+m[9]*p[1]+m[10]*p[2]+m[11]]
  const dot=(a,b)=>a.reduce((sum,x,i)=>sum+x*b[i],0)
  const minus=(a,b)=>a.map((v,i)=>v-b[i])
  const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
  const norm=(a)=>Math.hypot(...a)
  const unit=(a)=>a.map(x=>x/Math.max(1e-9,norm(a)))
  const clamp=(v,lo,hi)=>Math.max(lo,Math.min(hi,v))
  const hue=(name)=>{let h=3;for(const c of name)h=(h*31+c.charCodeAt(0))%360;return `hsl(${(h%65)+190},16%,${h%20+58}%)`}
  function localPrimitive(type,g){
    if(type==='box'){
      const [x,y,z]=(g.size||[.1,.1,.1]).map(v=>v/2)
      const v=[[-x,-y,-z],[x,-y,-z],[x,y,-z],[-x,y,-z],[-x,-y,z],[x,-y,z],[x,y,z],[-x,y,z]]
      const faces=[[0,1,2],[0,2,3],[4,6,5],[4,7,6],[0,4,5],[0,5,1],[1,5,6],[1,6,2],[2,6,7],[2,7,3],[3,7,4],[3,4,0]]
      return faces.flatMap(face=>face.flatMap(i=>v[i]))
    }
    const n=14,result=[]
    const radius=g.radius||.025,half=(g.length||.04)/2
    if(type==='sphere'){
      const bands=8
      for(let j=0;j<bands;j++){
        const t0=-Math.PI/2+j*Math.PI/bands,t1=-Math.PI/2+(j+1)*Math.PI/bands
        for(let i=0;i<n;i++){
          const a=i*Math.PI*2/n,b=(i+1)*Math.PI*2/n
          const vec=(t,p)=>[radius*Math.cos(t)*Math.cos(p),radius*Math.cos(t)*Math.sin(p),radius*Math.sin(t)]
          result.push(...vec(t0,a),...vec(t1,a),...vec(t1,b),...vec(t0,a),...vec(t1,b),...vec(t0,b))
        }
      }
      return result
    }
    if(type==='cylinder'){
      for(let i=0;i<n;i++){
        const a=i*Math.PI*2/n,b=(i+1)*Math.PI*2/n
        const p=(u,z)=>[radius*Math.cos(u),radius*Math.sin(u),z]
        result.push(...p(a,-half),...p(b,-half),...p(b,half),...p(a,-half),...p(b,half),...p(a,half))
        result.push(0,0,-half,...p(b,-half),...p(a,-half),0,0,half,...p(a,half),...p(b,half))
      }
    }
    return result
  }
  class Viewer {
    constructor(request, lang){this.request=request;this.lang=lang;this.data=null;this.selected='';this.yaw=-.7;this.pitch=.45;this.distance=1.2;this.target=[0,0,.25];this.drag=null;this.layers={visual:true,collision:false,frames:true,joints:true,camera:true};this.destroyed=false;this.tris=[]}
    label(key){if(this.lang()!=='zh-CN'){
      const en={viewer:'Robot model viewer',tree:'Link / Joint',layers:'Layers',visual:'Visual meshes',collision:'Collision',frames:'Link frames',joints:'Joint axes',camera:'Camera / board',select:'Select a link for details',illustrative:'URDF reference pose',live:'Live JointState pose',refresh:'Refresh state',reset:'Reset view',close:'Close',status:'Pose source',reference:'Frames from validated URDF kinematics',missing:'Some visual meshes are missing; using available geometry and link frames',empty:'No displayable visual mesh',help:'Left: orbit · Right / Shift: pan · Wheel: zoom',base:'Model root',joint:'Attached joint',matrix:'Transform from root frame',noRobot:'An end-effector pose alone does not define full joint positions',load:'Loading model geometry',noPose:'No complete live joint state',error:'Unable to open model',stale:'Board frame is historical, not live',size:'Links',triangles:'Mesh faces',axisLegend:'Coordinate axes',axisX:'X · red',axisY:'Y · green',axisZ:'Z · blue',axisJoint:'Joint axis · amber',dragHint:'Drag model · Left: orbit · Right: pan · Wheel: zoom'}
      return en[key]||key
    }return tr(key)}
    async open(){
      this.el=document.createElement('div');this.el.className='model-view-backdrop';this.el.id='handeye-model-viewer'
      this.el.innerHTML=`<section class="model-view-dialog" role="dialog" aria-modal="true" aria-label="${this.label('viewer')}">
        <header class="model-view-header"><div><b>${this.label('viewer')}</b><p>${this.label('reference')}</p></div><div class="model-view-header-actions"><button type="button" class="btn" data-role="refresh">${this.label('refresh')}</button><button type="button" class="btn" data-role="reset">${this.label('reset')}</button><button type="button" class="btn" data-role="close">${this.label('close')}</button></div></header>
        <div class="model-view-layout"><section class="model-view-main"><canvas class="model-view-canvas" tabindex="0"></canvas><div class="model-view-hint">${this.label('help')}</div><div class="model-view-axis-legend"><strong>${this.label('axisLegend')}</strong><span><i class="axis-x"></i>${this.label('axisX')}</span><span><i class="axis-y"></i>${this.label('axisY')}</span><span><i class="axis-z"></i>${this.label('axisZ')}</span><span><i class="axis-joint"></i>${this.label('axisJoint')}</span></div><div class="model-view-banner" data-role="banner">${this.label('load')}</div></section>
        <aside class="model-view-aside"><div class="model-view-section"><strong>${this.label('status')}</strong><div id="model-view-state"></div></div><div class="model-view-section"><strong>${this.label('layers')}</strong><div class="model-view-layers">${Object.keys(this.layers).map(k=>`<label><input data-layer="${k}" type="checkbox" ${this.layers[k]?'checked':''}>${this.label(k)}</label>`).join('')}</div></div><div class="model-view-section"><strong>${this.label('tree')}</strong><div class="model-view-tree" id="model-view-tree"></div></div><div class="model-view-section"><strong>${this.label('select')}</strong><div id="model-view-inspect"></div></div></aside></div>
      </section>`
      document.body.appendChild(this.el)
      this.canvas=$('.model-view-canvas',this.el);this.gpu=new window.HandeyeGPUScene(this.canvas)
      this.el.querySelector('[data-role="close"]').onclick=()=>this.close()
      this.el.querySelector('[data-role="refresh"]').onclick=()=>this.refresh()
      this.el.querySelector('[data-role="reset"]').onclick=()=>this.reset()
      this.el.querySelectorAll('[data-layer]').forEach(c=>c.onchange=()=>{this.layers[c.dataset.layer]=c.checked;this.draw()})
      this.keydown=(e)=>{if(e.key==='Escape'){e.preventDefault();this.close()}}
      document.addEventListener('keydown',this.keydown)
      this.canvas.addEventListener('contextmenu',e=>e.preventDefault())
      // Trackball/OrbitControls-style interaction with Z as the up axis
      // Grab the model: its visible movement follows the pointer on screen
      this.canvas.addEventListener('pointerdown',e=>{
        if(e.button!==0&&e.button!==2)return
        e.preventDefault()
        this.drag={x:e.clientX,y:e.clientY,yaw:this.yaw,pitch:this.pitch,target:[...this.target],pan:e.shiftKey||e.button===2}
        this.canvas.setPointerCapture(e.pointerId)
      })
      this.canvas.addEventListener('pointermove',e=>{
        if(!this.drag)return
        const dx=e.clientX-this.drag.x,dy=e.clientY-this.drag.y
        const height=Math.max(200,this.canvas.clientHeight)
        const orbitSpeed=3.2/height
        if(this.drag.pan){
          const side=[-Math.cos(this.yaw),Math.sin(this.yaw),0]
          const up=[-Math.sin(this.pitch)*Math.sin(this.yaw),-Math.sin(this.pitch)*Math.cos(this.yaw),Math.cos(this.pitch)]
          this.target=this.drag.target.map((v,i)=>v-(side[i]*dx-up[i]*dy)*this.distance/height*1.5)
        }else{
          // Natural CAD model drag in a Z-up scene
          this.yaw=this.drag.yaw + dx*orbitSpeed
          this.pitch=clamp(this.drag.pitch + dy*orbitSpeed,-1.48,1.48)
        }
        this.draw()
      })
      this.canvas.addEventListener('pointerup',()=>{this.drag=null})
      this.canvas.addEventListener('pointercancel',()=>{this.drag=null})
      this.canvas.addEventListener('dblclick',()=>this.reset())
      this.canvas.addEventListener('wheel',e=>{e.preventDefault();this.distance=clamp(this.distance*Math.exp(e.deltaY*.0011),.03,50);this.draw()},{passive:false})
      this.resize=new ResizeObserver(()=>this.draw());this.resize.observe(this.canvas)
      await this.refresh()
    }
    async refresh(){
      const banner=this.el?.querySelector('[data-role="banner"]');if(banner)banner.textContent=this.label('load')
      try{
        const next=await this.request('get_model_preview',{})
        if(this.destroyed)return
        this.data=next;this.selected=this.selected&&next.links.some(l=>l.name===this.selected)?this.selected:(next.links.find(l=>l.name==='tip')?.name||next.links[0]?.name||'')
        this.buildTriangles();this.fillTree();this.fillInfo()
        if(banner)banner.textContent=(next.model_pose==='joint_state'?this.label('live'):this.label('illustrative'))+(this.gpu.mode==='webgl'?' · WebGL':' · Canvas 降精度')
        this.draw()
      }catch(err){if(banner)banner.textContent=this.label('error')+': '+(err.message||String(err));throw err}
    }
    close(){this.destroyed=true;this.resize?.disconnect();this.gpu?.dispose();document.removeEventListener('keydown',this.keydown);this.el?.remove();window.HandeyeModelViewer.active=null}
    buildTriangles(){
      this.tris=[]
      for(const link of this.data.links){
        const frame=m4(this.data.frames[link.name]);
        for(const entry of link.visuals){
          let local=entry.vertices?.length?entry.vertices:localPrimitive(entry.geometry.type,entry.geometry)
          if(!local.length)continue
          const scale=entry.geometry.scale||[1,1,1]
          const transform=mul(frame,m4(entry.transform))
          let limit=0
          for(let i=0;i+8<local.length;i+=9){
            const a=pt(transform,[local[i]*scale[0],local[i+1]*scale[1],local[i+2]*scale[2]]),b=pt(transform,[local[i+3]*scale[0],local[i+4]*scale[1],local[i+5]*scale[2]]),c=pt(transform,[local[i+6]*scale[0],local[i+7]*scale[1],local[i+8]*scale[2]])
            if([...a,...b,...c].every(Number.isFinite))this.tris.push({name:link.name,layer:entry.layer,v:[a,b,c],color:entry.color})
            limit++
          }
        }
      }
      this.gpu.upload(this.tris)
    }
    fillTree(){
      const tree=this.el.querySelector('#model-view-tree'),children=new Map()
      for(const joint of this.data.joints){const list=children.get(joint.parent)||[];list.push(joint);children.set(joint.parent,list)}
      const visited=new Set()
      const render=(link,depth)=>{
        if(visited.has(link)||depth>40)return '';visited.add(link)
        const joint=this.data.joints.find(j=>j.child===link)
        return `<button type="button" class="model-view-link ${this.selected===link?'active':''}" data-link="${encodeURIComponent(link)}" style="padding-left:${10+Math.min(depth,14)*15}px"><span>${this.selected===link?'●':'○'}</span><span>${escapeText(link)}</span><small>${joint?.kind||'root'}</small></button>${(children.get(link)||[]).map(j=>render(j.child,depth+1)).join('')}`
      }
      tree.innerHTML=render(this.data.root,0)
      tree.querySelectorAll('[data-link]').forEach(button=>button.onclick=()=>{this.selected=decodeURIComponent(button.dataset.link);this.fillTree();this.fillInfo();this.draw()})
    }
    fillInfo(){
      const host=this.el.querySelector('#model-view-inspect')
      const matrix=this.data.frames[this.selected]
      const joint=this.data.joints.find(j=>j.child===this.selected)
      host.innerHTML=`<div class="model-view-inspect"><b>${escapeText(this.selected)}</b><small>${this.label('joint')}: ${escapeText(joint?.name||'—')} (${escapeText(joint?.kind||'root')})</small><small>${this.label('base')}: ${escapeText(this.data.root)}</small><small>${this.label('matrix')}:</small><pre>${matrix?matrix.map(row=>row.map(v=>Number(v).toFixed(4)).join('  ')).join('\n'):'—'}</pre></div>`
      const s=this.el.querySelector('#model-view-state')
      s.innerHTML=`<p>${escapeText(this.data.frames_note||'')}</p><p>${this.label('size')}: ${this.data.links.length} · ${this.label('triangles')}: ${this.tris.length}</p>${this.data.warnings?.length?`<details><summary>${this.label('missing')} (${this.data.warnings.length})</summary>${this.data.warnings.map(x=>`<p>${escapeText(x)}</p>`).join('')}</details>`:''}`
    }
    reset(){
      this.yaw=-.6;this.pitch=.55
      const all=Object.values(this.data?.frames||{}).map(m=>[m[0][3],m[1][3],m[2][3]])
      const stride=Math.max(1,Math.floor(this.tris.length/6000))
      for(let i=0;i<this.tris.length;i+=stride)all.push(...this.tris[i].v)
      if(all.length){let min=[Infinity,Infinity,Infinity],max=[-Infinity,-Infinity,-Infinity];for(const p of all){for(let i=0;i<3;i++){min[i]=Math.min(min[i],p[i]);max[i]=Math.max(max[i],p[i])}}this.target=min.map((v,i)=>(v+max[i])/2);this.distance=Math.max(.20,norm(minus(max,min))*1.05)}
      this.draw()
    }
    draw(){
      if(!this.gpu||!this.data)return
      this.gpu.schedule({yaw:this.yaw,pitch:this.pitch,distance:this.distance,target:[...this.target],selected:this.selected,layers:{...this.layers},data:this.data})
    }

  }
  function escapeText(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]))}
  window.HandeyeModelViewer={active:null,async open(request,lang){if(this.active){this.active.el?.querySelector('[data-role="close"]')?.focus();return}const view=new Viewer(request,lang);this.active=view;try{await view.open();view.reset()}catch(e){view.close();throw e}}}
})()
