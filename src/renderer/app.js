'use strict'

const $ = (sel, root=document) => root.querySelector(sel)
const $$ = (sel, root=document) => [...root.querySelectorAll(sel)]

const iconPaths = {
  camera:'<path d="M14.5 4 16 6h3a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h3l1.5-2h5Z"/><circle cx="12" cy="13" r="3.5"/>',
  plug:'<path d="m12 22 4-4-4-4"/><path d="M16 18H7a5 5 0 0 1-5-5v-1"/><path d="M6 2v4"/><path d="M10 2v4"/><path d="M4 6h8v2a4 4 0 0 1-8 0V6Z"/>',
  target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  scan:'<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><circle cx="12" cy="12" r="3"/>',
  flask:'<path d="M9 3h6"/><path d="M10 3v6l-5 9a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3l-5-9V3"/><path d="M7.5 15h9"/>',
  settings:'<path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21a2 2 0 1 1-4 0v-.09A1.7 1.7 0 0 0 8.5 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.1-.4H3a2 2 0 1 1 0-4h.09A1.7 1.7 0 0 0 4.6 8.5a1.7 1.7 0 0 0-.34-1.88l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-.6 1.7 1.7 0 0 0 .4-1.1V3a2 2 0 1 1 4 0v.09A1.7 1.7 0 0 0 15.5 4.6a1.7 1.7 0 0 0 1.88-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.7 1.7 0 0 0 19.4 9c.13.36.34.7.6 1 .3.27.68.42 1.1.4H21a2 2 0 1 1 0 4h-.09c-.4-.02-.8.13-1.1.4-.27.3-.47.64-.6 1Z"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
  folder:'<path d="M3 6a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6Z"/>',
  play:'<path d="m8 5 11 7-11 7V5Z"/>',
  square:'<rect x="4" y="4" width="16" height="16" rx="2"/>',
  trash:'<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="m19 6-1 14H6L5 6"/><path d="M10 11v5"/><path d="M14 11v5"/>',
  save:'<path d="M5 3h12l2 2v16H5V3Z"/><path d="M8 3v6h8V3"/><path d="M8 21v-7h8v7"/>',
  chevron:'<path d="m9 18 6-6-6-6"/>',
  terminal:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="m7 9 3 3-3 3"/><path d="M13 15h4"/>',
  sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.66 6.34l1.41-1.41"/>',
  moon:'<path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z"/>',
  monitor:'<rect x="3" y="4" width="18" height="14" rx="2"/><path d="M8 22h8M12 18v4"/>',
  x:'<path d="M6 6l12 12M18 6 6 18"/>', minus:'<path d="M5 12h14"/>', max:'<rect x="5" y="5" width="14" height="14" rx="1"/>',
  check:'<path d="m5 12 4 4L19 6"/>', alert:'<path d="M10.3 3.7 2.8 17a2 2 0 0 0 1.7 3h15a2 2 0 0 0 1.7-3L13.7 3.7a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/>'
}
function icon(name, cls='') { return `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${iconPaths[name]||iconPaths.info}</svg>` }
function themeIcon(theme){return theme==='light'?'sun':theme==='dark'?'moon':'monitor'}

const state = {
  page:'connect', theme:localStorage.getItem('handeye-theme') || 'dark', backend:'starting', runtime:null,
  data:{ config:{output_dir:'',camera_index:0,camera_width:640,camera_height:480,chessboard_cols:11,chessboard_rows:8,square_size_mm:15,ros_input_type:'pose',pose_topic:'/arm/pose',joint_dof:5,joint_names:'',capture_topic:'',status_topic:'/handeye/status'}, camera:{open:false,board_found:false,width:640,height:480}, ros:{running:false,pose:null}, intrinsics:{count:0,exists:false}, handeye:{count:0,samples_exists:false}, output_dir:'' },
  preview:'', logs:'', intrinsicQuality:'standard', handeyeQuality:'standard', sampleMode:'auto', manualType:'quaternion', angleUnit:'deg', solveMode:'robust',
  intrinsicResult:null, solveResult:null, runtimeInstallLog:'', runtimeInstallState:'idle'
}

function createMockApi() {
  let mock = JSON.parse(JSON.stringify(state.data)); mock.mock=true
  const listeners=[]; const runtime=[]
  function emit(event,data){ listeners.forEach(fn=>fn({kind:'event',event,data})) }
  setTimeout(()=>runtime.forEach(fn=>fn({state:'ready',python:'sandbox-mock',rosSetup:'/opt/ros/humble/setup.bash'})),100)
  return {
    request: async (method,params={}) => {
      if(method==='get_state'||method==='ping') return method==='ping'?{pong:true,mock:true}:mock
      if(method==='set_config'){ Object.assign(mock.config,params); mock.output_dir=mock.config.output_dir; emit('state',mock); return mock }
      if(method==='open_camera'){ mock.camera.open=true; mock.camera.board_found=true; emit('state',mock); return mock.camera }
      if(method==='close_camera'){ mock.camera.open=false; emit('state',mock); return mock.camera }
      if(method==='start_ros'){ mock.ros.running=true; mock.ros.pose={values:[.412,-.083,.536,.012,.713,.008,.701],frame_id:'arm_base_link',timestamp:Date.now()/1000}; emit('pose',mock.ros.pose); emit('state',mock); return mock.ros }
      if(method==='stop_ros'){ mock.ros.running=false; mock.ros.pose=null; emit('state',mock); return mock.ros }
      if(method==='capture_intrinsic'){ mock.intrinsics.count++; emit('intrinsic',{count:mock.intrinsics.count,sharpness:186,board_coverage_percent:23.4}); emit('state',mock); return {count:mock.intrinsics.count,sharpness:186,board_coverage_percent:23.4} }
      if(method==='solve_intrinsic'){ mock.intrinsics.exists=true; emit('state',mock); return {reprojection_error_px:.184,reprojection_error_median_px:.161,reprojection_error_max_px:.302,image_width:640,image_height:480} }
      if(method==='clear_intrinsic'){mock.intrinsics.count=0;emit('state',mock);return {count:0}}
      if(method==='capture_handeye'){mock.handeye.count++;emit('handeye',{count:mock.handeye.count,reprojection_error_px:.217,distance_mm:533,sharpness:171,pixels_per_square:24.9});emit('state',mock);return {count:mock.handeye.count,reprojection_error_px:.217,distance_mm:533,sharpness:171,pixels_per_square:24.9}}
      if(method==='save_samples'){mock.handeye.samples_exists=true;emit('state',mock);return {count:mock.handeye.count,path:'/tmp/handeye/samples.yaml'}}
      if(method==='clear_samples'){mock.handeye.count=0;emit('state',mock);return {count:0}}
      if(method==='run_tool'){const text=`[mock] ${params.name} completed\n`;emit('log',{text}); const result={translation_m:[.041,-.018,.087],quaternion_xyzw:[.003,.012,-.004,.9999],translation_rms_mm:2.31,rotation_rms_deg:.42,transform_matrix:[[1,0,0,.041],[0,1,0,-.018],[0,0,1,.087],[0,0,0,1]]}; return {ok:true,exit_code:0,log:text,result}}
      return {}
    },
    selectDirectory:async()=>'/home/user/handeye-output', runtimeInfo:async()=>({appVersion:'1.0.0',packaged:false,ubuntu:'22.04',rosDistro:'humble',rosSetup:'/opt/ros/humble/setup.bash',python:'sandbox-mock',runtimePython:'/home/user/.local/share/handeye-calibration/.venv/bin/python',runtimeInstalled:true}),
    runtimeInstall:async()=>({ok:true,python:'/home/user/.local/share/handeye-calibration/.venv/bin/python'}), backendRestart:async()=>({ok:true}),
    onEvent:fn=>{listeners.push(fn);return()=>{}}, onRuntime:fn=>{runtime.push(fn);return()=>{}}, onRuntimeInstall:()=>()=>{}, onStderr:()=>()=>{}, onWindowState:()=>()=>{}, window:{minimize(){},maximize(){},close(){}}
  }
}
const api = window.handeye || (location.search.includes('mock=1') ? createMockApi() : null)

function applyTheme(theme) {
  state.theme=theme
  localStorage.setItem('handeye-theme',theme)
  const light=theme==='light'||(theme==='system'&&matchMedia('(prefers-color-scheme: light)').matches)
  document.documentElement.classList.toggle('light',light)
  document.documentElement.classList.toggle('dark',!light)
  const seg=$('#theme-segment')
  if(seg)$$('button',seg).forEach(b=>b.classList.toggle('active',b.dataset.theme===theme))
  const menu=$('#appearance-menu')
  if(menu)$$('[data-theme]',menu).forEach(b=>b.classList.toggle('active',b.dataset.theme===theme))
  const iconHost=$('#appearance-icon')
  if(iconHost)iconHost.innerHTML=icon(themeIcon(theme))
  const toggle=$('#appearance-toggle')
  if(toggle)toggle.setAttribute('aria-label',`Appearance ${theme}`)
}

function dot(status){return `<span class="status-dot ${status}"></span>`}
function toast(title,message='',kind='success'){
  const host=$('#toasts'); if(!host)return; const el=document.createElement('div');el.className='toast';el.innerHTML=`${dot(kind)}<div><b>${escapeHtml(title)}</b>${message?`<span>${escapeHtml(message)}</span>`:''}</div>`;host.appendChild(el);setTimeout(()=>el.remove(),4200)
}
function escapeHtml(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]))}
function n(v,d=3){const x=Number(v);return Number.isFinite(x)?x.toFixed(d):'—'}

function themeMenuChoice(theme,label,description){return `<button class="appearance-option ${state.theme===theme?'active':''}" data-theme="${theme}"><span class="theme-option-icon">${icon(themeIcon(theme))}</span><span class="appearance-option-copy"><b>${label}</b><small>${description}</small></span><span class="appearance-check">${state.theme===theme?icon('check'):''}</span></button>`}
function themeSettingsChoice(theme,label){return `<button class="theme-choice ${state.theme===theme?'active':''}" data-theme="${theme}"><span class="theme-option-icon">${icon(themeIcon(theme))}</span><span>${label}</span></button>`}
function bindAppearanceMenu(){
  const toggle=$('#appearance-toggle'),menu=$('#appearance-menu')
  if(!toggle||!menu)return
  toggle.onclick=e=>{e.stopPropagation();menu.classList.toggle('hidden');if(!menu.classList.contains('hidden'))requestAnimationFrame(()=>menu.classList.add('visible'))}
  $$('[data-theme]',menu).forEach(b=>b.onclick=e=>{e.stopPropagation();applyTheme(b.dataset.theme);closeAppearanceMenu()})
  document.addEventListener('pointerdown',e=>{if(!menu.contains(e.target)&&e.target!==toggle&&!toggle.contains(e.target)){closeAppearanceMenu()}},{passive:true})
}

function shell(){
  $('#app').innerHTML=`<div class="app-shell">
    <header class="titlebar">
      <div class="brand-mini"><span class="logo-mark">${icon('target')}</span><b>HandEye Calibration</b></div>
      <div class="titlebar-center">ROS2 Calibration Workstation</div>
      <div class="title-actions"><div class="appearance-wrap"><button class="title-button appearance-toggle" id="appearance-toggle" aria-label="Appearance"><span id="appearance-icon">${icon(themeIcon(state.theme))}</span></button><div class="appearance-menu hidden" id="appearance-menu"><div class="appearance-menu-label">Appearance</div>${themeMenuChoice('system','System','Follow system')}${themeMenuChoice('dark','Dark','Low light')}${themeMenuChoice('light','Light','Daylight')}</div></div><span class="title-separator"></span><button class="title-button" id="win-min">${icon('minus')}</button><button class="title-button" id="win-max">${icon('max')}</button><button class="title-button close" id="win-close">${icon('x')}</button></div>
    </header>
    <div class="app-body">
      <aside class="sidebar">
        <div class="sidebar-hero"><div class="eyebrow">AgroTech · SCAU</div><h1>HandEye</h1><p>手眼标定工作站<br>Eye-in-hand calibration</p></div>
        <div class="nav-caption">Calibration</div><nav class="nav-list">
          ${nav('connect','plug','Connect','01')}${nav('intrinsics','scan','Intrinsics','02')}${nav('handeye','target','Hand-Eye','03')}${nav('solve','flask','Solve & Verify','04')}
        </nav>
        <div class="nav-caption" style="margin-top:13px">Application</div><nav class="nav-list">${nav('settings','settings','Settings','')}${nav('about','info','About','')}</nav>
        <div class="sidebar-spacer"></div><div class="runtime-card"><div class="runtime-line">${dot('warning')}<span id="runtime-label">Backend starting</span></div><div class="runtime-line" id="ros-sidebar">ROS2 environment · checking</div></div>
      </aside>
      <section class="content-wrap"><div class="top-status"><span class="breadcrumb" id="breadcrumb">Calibration / Connect</span><span class="pill" id="camera-pill">${dot('warning')} Camera Offline</span><span class="pill" id="ros-pill">${dot('warning')} ROS2 Offline</span><span class="pill" id="board-pill">${dot('warning')} Board —</span></div><main class="content"><div id="page"></div></main></section>
    </div><div class="toast-stack" id="toasts"></div></div>`
  $('#win-min').onclick=()=>api?.window?.minimize();$('#win-max').onclick=()=>api?.window?.maximize();$('#win-close').onclick=()=>api?.window?.close()
  bindAppearanceMenu()
  $$('.nav-item').forEach(b=>b.onclick=()=>navigate(b.dataset.page))
}
function nav(page,ico,label,step){return `<button class="nav-item" data-page="${page}">${icon(ico)}<span>${label}</span>${step?`<span class="step">${step}</span>`:''}</button>`}
function closeAppearanceMenu(){const menu=$('#appearance-menu');if(!menu)return;menu.classList.remove('visible');setTimeout(()=>menu.classList.add('hidden'),130)}
function navigate(page){closeAppearanceMenu();if(page===state.page)return;state.page=page;renderPage(true);requestAnimationFrame(()=>{$('.content').scrollTop=0})}

function pageHead(kicker,title,desc,actions=''){return `<div class="page-head"><div class="page-head-main"><div class="page-kicker">${kicker}</div><h2 class="page-title">${title}</h2><p class="page-description">${desc}</p></div>${actions?`<div class="page-actions">${actions}</div>`:''}</div>`}
function card(title,subtitle,ico,body,footer='',accent=false){return `<section class="card"><div class="card-head"><span class="card-icon ${accent?'accent':''}">${icon(ico)}</span><div><h3 class="card-title">${title}</h3>${subtitle?`<p class="card-subtitle">${subtitle}</p>`:''}</div></div><div class="card-body">${body}</div>${footer?`<div class="card-footer">${footer}</div>`:''}</section>`}
function field(label,id,value,type='text',help=''){return `<div class="field"><label for="${id}">${label}</label><input class="control" id="${id}" type="${type}" value="${escapeHtml(value)}"/>${help?`<div class="help">${help}</div>`:''}</div>`}
function btn(id,label,ico='play',kind='',extra=''){return `<button class="btn ${kind}" id="${id}" ${extra}>${icon(ico)}${label}</button>`}
function preview(){const cam=state.data.camera||{};return `<section class="card preview-card"><div class="preview-toolbar"><b>Camera Preview</b><span class="pill" id="preview-live-pill">${dot(cam.open?'success':'warning')} ${cam.open?'Live':'Offline'}</span><span class="meta" id="preview-size">${cam.width||640} × ${cam.height||480}</span></div><div class="preview-surface" id="preview-surface">${state.preview?`<img class="preview-image" src="data:image/jpeg;base64,${state.preview}"/>`:`<div class="preview-empty"><div class="ring">${icon('camera')}</div><b>等待相机画面</b><span>打开相机后在此显示实时棋盘检测结果</span></div>`}</div></section>`}

function renderConnect(){const c=state.data.config,cam=state.data.camera,ros=state.data.ros;return `<div class="page">${pageHead('Calibration · Step 01','Connect','配置输出路径、相机和机器人输入接口保持算法合同不变，只负责建立一次可靠的采集会话')}
<div class="grid three" style="margin-bottom:14px"><div class="metric"><div class="metric-label">Camera</div><div class="metric-value" style="color:${cam.open?'var(--success)':'var(--text-secondary)'}">${cam.open?'Connected':'Offline'}</div><div class="metric-meta">Device ${c.camera_index} · ${c.camera_width}×${c.camera_height}</div></div><div class="metric"><div class="metric-label">ROS2 Robot Input</div><div class="metric-value" style="color:${ros.running?'var(--success)':'var(--text-secondary)'}">${ros.running?'Receiving':'Disconnected'}</div><div class="metric-meta">${escapeHtml(c.pose_topic)}</div></div><div class="metric"><div class="metric-label">Output</div><div class="metric-value">${state.data.handeye?.count||0}<small>samples</small></div><div class="metric-meta">${escapeHtml(c.output_dir||'Not configured')}</div></div></div>
<div class="grid preview-layout">${preview()}<div class="stack">
${card('Project & Camera','本地 OpenCV CameraSession，与主仓库行为一致','camera',`<div class="form-row"><div class="field full"><label>输出目录</label><div class="inline-control"><input class="control" id="output-dir" value="${escapeHtml(c.output_dir)}"/><button class="btn" id="browse-output">${icon('folder')}浏览</button></div></div>${field('相机编号','camera-index',c.camera_index,'number')}${field('分辨率宽','camera-width',c.camera_width,'number')}${field('分辨率高','camera-height',c.camera_height,'number')}</div>`,`<div class="actions">${btn('save-connect','保存设置','save')}${cam.open?btn('close-camera','关闭相机','square',''):btn('open-camera','打开相机','camera','primary')}</div>`,true)}
${card('Robot Interface','自动模式保持主仓库 PoseStamped / JointState 合同','plug',`<div class="form-row"><div class="field"><label>输入类型</label><select class="control" id="ros-input-type"><option value="pose" ${c.ros_input_type==='pose'?'selected':''}>PoseStamped</option><option value="joints" ${c.ros_input_type==='joints'?'selected':''}>JointState</option></select></div>${field('输入话题','pose-topic',c.pose_topic)}${field('关节自由度','joint-dof',c.joint_dof,'number')}${field('关节顺序（可选）','joint-names',c.joint_names||'')}${field('采集触发（可选）','capture-topic',c.capture_topic||'')}${field('状态发布（可选）','status-topic',c.status_topic||'')}</div>`,`<div class="actions">${ros.running?btn('stop-ros','断开 ROS2','square'):btn('start-ros','连接 ROS2','plug','primary')}</div>`,false)}
<div class="callout">${icon('info')}<div><b>接口语义不变</b><br>PoseStamped 为完整末端位姿；JointState 仍使用 algorithms/robot_params.yaml 做 FKGUI 不改变采样与求解算法</div></div>
</div></div></div>`}

function boardFields(){const c=state.data.config;return `<div class="form-row three">${field('角点列数','board-cols',c.chessboard_cols,'number')}${field('角点行数','board-rows',c.chessboard_rows,'number')}${field('方格边长 / mm','square-mm',c.square_size_mm,'number')}</div>`}
function qualitySegment(id,current){return `<div class="segmented amber" id="${id}"><button data-value="standard" class="${current==='standard'?'active':''}">标准</button><button data-value="strict" class="${current==='strict'?'active':''}">严格</button><button data-value="minimal" class="${current==='minimal'?'active':''}">极简</button></div>`}
function renderIntrinsics(){const x=state.data.intrinsics||{},cam=state.data.camera;const target=state.intrinsicQuality==='strict'?15:state.intrinsicQuality==='minimal'?3:10;const pct=Math.min(100,(x.count||0)/target*100);return `<div class="page">${pageHead('Calibration · Step 02','Camera Intrinsics','采集不同位置、距离和倾角的棋盘图像质量门限、最少图片数和 OpenCV 标定行为完全来自主仓库',btn('go-handeye','Next: Hand-Eye','chevron'))}
<div class="grid preview-layout">${preview()}<div class="stack">${card('Calibration Board','内参与外参必须使用相同棋盘参数','scan',boardFields(),`${btn('save-board','保存棋盘参数','save')}`)}
${card('Capture Session','标准模式建议 20–30 张；绿色检测后再采集','camera',`<div class="progress-label"><span>已采集 ${x.count||0} 张</span><span>最低 ${target} 张</span></div><div class="progress-track"><div class="progress-bar" style="width:${pct}%"></div></div><div style="margin-top:14px"><div class="field"><label>采样质量</label>${qualitySegment('intrinsic-quality',state.intrinsicQuality)}</div></div><div class="grid two" style="margin-top:13px"><div class="metric"><div class="metric-label">Chessboard</div><div class="metric-value" id="board-live" style="font-size:17.25px;color:${cam.board_found?'var(--success)':'var(--warning)'}">${cam.board_found?'Detected':'Not detected'}</div></div><div class="metric"><div class="metric-label">Intrinsics file</div><div class="metric-value" style="font-size:17.25px;color:${x.exists?'var(--success)':'var(--text-secondary)'}">${x.exists?'Ready':'Pending'}</div></div></div>`,`<div class="actions">${btn('capture-intrinsic','Capture','camera','primary large',cam.open?'':'disabled')}${btn('solve-intrinsic','Solve & Save','flask','',x.count>=target?'':'disabled')}${btn('clear-intrinsic','Clear','trash','danger')}</div>`,true)}
${state.intrinsicResult?`<div class="callout">${icon('check')}<div><b>内参已保存</b><br>RMS ${n(state.intrinsicResult.reprojection_error_px,4)} px · Median ${n(state.intrinsicResult.reprojection_error_median_px,4)} px · Max ${n(state.intrinsicResult.reprojection_error_max_px,4)} px</div></div>`:''}</div></div></div>`}

function poseText(){const p=state.data.ros?.pose;if(!p)return 'Waiting for robot data';const v=p.values||[];return `frame : ${p.frame_id||'-'}\nxyz   : ${n(v[0],5)}  ${n(v[1],5)}  ${n(v[2],5)} m\nxyzw  : ${n(v[3],5)}  ${n(v[4],5)}  ${n(v[5],5)}  ${n(v[6],5)}`}
function manualFields(){let labels=state.manualType==='quaternion'?['x','y','z','qx','qy','qz','qw']:state.manualType==='rpy'?['x','y','z','roll','pitch','yaw']:Array.from({length:Number(state.data.config.joint_dof)||5},(_,i)=>`q${i+1}`);return `<div class="form-row three">${labels.map((l,i)=>field(l,`manual-${i}`,state.manualType==='quaternion'&&i===6?1:0,'number')).join('')}</div>`}
function renderHandeye(){const h=state.data.handeye||{},ros=state.data.ros||{};const target=20,pct=Math.min(100,(h.count||0)/target*100);return `<div class="page">${pageHead('Calibration · Step 03','Hand-Eye Sampling','固定棋盘，改变机械臂位置与姿态每次 Capture 保存当前图像与当前机器人位姿的一组样本',btn('go-solve','Next: Solve','chevron'))}
<div class="grid preview-layout">${preview()}<div class="stack">${card('Robot Pose',ros.running?'ROS2 自动数据正在接收':'可选择 ROS2 自动或手动输入','target',`<div class="pose-box" id="pose-live">${escapeHtml(poseText())}</div><div style="margin-top:12px"><div class="field"><label>采样来源</label><div class="segmented amber" id="sample-mode"><button data-value="auto" class="${state.sampleMode==='auto'?'active':''}">ROS2 自动</button><button data-value="manual" class="${state.sampleMode==='manual'?'active':''}">手动输入</button></div></div></div>${state.sampleMode==='manual'?`<div class="divider"></div><div class="form-row"><div class="field"><label>手动类型</label><select class="control" id="manual-type"><option value="quaternion" ${state.manualType==='quaternion'?'selected':''}>末端位姿 · Quaternion</option><option value="rpy" ${state.manualType==='rpy'?'selected':''}>末端位姿 · RPY</option><option value="joints" ${state.manualType==='joints'?'selected':''}>Joint angles</option></select></div><div class="field"><label>角度单位</label><select class="control" id="angle-unit"><option value="deg" ${state.angleUnit==='deg'?'selected':''}>deg</option><option value="rad" ${state.angleUnit==='rad'?'selected':''}>rad</option></select></div></div><div style="margin-top:11px">${manualFields()}</div>`:''}`)}
${card('Sample Collection','标准质量建议采集 20–30 组，并覆盖多轴旋转','scan',`<div class="progress-label"><span>${h.count||0} captured samples</span><span>${target} recommended</span></div><div class="progress-track"><div class="progress-bar" style="width:${pct}%"></div></div><div style="margin-top:14px"><div class="field"><label>采样质量</label>${qualitySegment('handeye-quality',state.handeyeQuality)}</div></div><div class="grid three" style="margin-top:13px"><div class="metric"><div class="metric-label">Samples</div><div class="metric-value">${h.count||0}</div></div><div class="metric"><div class="metric-label">Camera</div><div class="metric-value" style="font-size:16.1px;color:${state.data.camera?.open?'var(--success)':'var(--warning)'}">${state.data.camera?.open?'Ready':'Offline'}</div></div><div class="metric"><div class="metric-label">Robot</div><div class="metric-value" style="font-size:16.1px;color:${state.sampleMode==='manual'||ros.pose?'var(--success)':'var(--warning)'}">${state.sampleMode==='manual'?'Manual':ros.pose?'Ready':'Waiting'}</div></div></div>`,`<div class="actions">${btn('capture-handeye','Capture Sample','target','primary large')}${btn('save-samples','Save samples.yaml','save')}${btn('clear-samples','Clear','trash','danger')}</div>`,true)}</div></div></div>`}

function matrixHtml(result){const m=result?.transform_matrix;if(!Array.isArray(m)||m.length!==4)return '<div class="pose-box">Waiting for solve result</div>';return `<div class="result-matrix">${m.flat().map(v=>`<span>${n(v,6)}</span>`).join('')}</div>`}
function renderSolve(){const h=state.data.handeye||{};const r=state.solveResult;return `<div class="page">${pageHead('Calibration · Step 04','Solve & Verify','调用主仓库 algorithms/diagnose.py、solve.py、verify.pyGUI 只负责触发和展示，不改变任何求解数学')}
<div class="grid two" style="margin-bottom:14px"><div class="metric"><div class="metric-label">samples.yaml</div><div class="metric-value" style="font-size:17.25px;color:${h.samples_exists?'var(--success)':'var(--warning)'}">${h.samples_exists?'Ready':'Not saved'}</div><div class="metric-meta">${escapeHtml(h.samples_path||'')}</div></div><div class="metric"><div class="metric-label">Result</div><div class="metric-value" style="font-size:17.25px;color:${r?'var(--success)':'var(--text-secondary)'}">${r?'Solved':'Waiting'}</div><div class="metric-meta">samples_result.yaml</div></div></div>
<div class="grid preview-layout"><div class="stack">${card('Calibration Pipeline','按需运行，也可依次执行 Diagnose → Solve → Verify','flask',`<div class="field"><label>求解模式</label><div class="segmented amber" id="solve-mode"><button data-value="robust" class="${state.solveMode==='robust'?'active':''}">Robust</button><button data-value="minimal" class="${state.solveMode==='minimal'?'active':''}">OpenCV</button><button data-value="ba" class="${state.solveMode==='ba'?'active':''}">Bundle Adjustment</button></div></div><div class="divider"></div><div class="actions">${btn('run-diagnose','Diagnose','scan')}${btn('run-solve','Solve','play','primary')}${btn('run-verify','Verify','check')}</div>`)}
${card('Transform Result','默认 eye-in-hand 输出 ^gripper T_camera','target',`${matrixHtml(r)}${r?`<div class="grid two" style="margin-top:12px"><div class="metric"><div class="metric-label">Translation RMS</div><div class="metric-value">${n(r.translation_rms_mm,3)}<small>mm</small></div></div><div class="metric"><div class="metric-label">Rotation RMS</div><div class="metric-value">${n(r.rotation_rms_deg,3)}<small>deg</small></div></div></div>`:''}`)}</div>
${card('Algorithm Log','标准输出实时转发，便于诊断数据质量','terminal',`<div class="log-box" id="log-box">${escapeHtml(state.logs||'No algorithm output yet\n')}</div>`,`<span style="font-size:11.5px;color:var(--text-dim)">Core files are protected by verify_core.py</span>`)}</div></div>`}

function renderSettings(){const rt=state.runtime||{};const installed=Boolean(rt.runtimeInstalled);return `<div class="page">${pageHead('Application','Settings','管理 GUI 与运行时外壳，不修改标定算法参数')}<div class="grid two">${card('Appearance','支持系统 / 深色 / 浅色主题','sun',`<div class="field"><label>Theme</label><div class="theme-selector" id="theme-segment">${themeSettingsChoice('system','System')}${themeSettingsChoice('dark','Dark')}${themeSettingsChoice('light','Light')}</div></div>`)}${card('Python & ROS2 Runtime','使用宿主 ROS2 + 同版本 Python，避免 rclpy ABI 冲突','terminal',`<div class="runtime-health"><div>${dot(installed?'success':'warning')}<b id="runtime-health-label">${installed?'Per-user runtime ready':'Per-user runtime not installed'}</b></div><span id="runtime-health-path">${escapeHtml(rt.runtimePython||'~/.local/share/handeye-calibration/.venv/bin/python')}</span></div><div class="pose-box" id="runtime-info-box" style="margin-top:11px">Ubuntu : ${escapeHtml(rt.ubuntu||'unknown')}
ROS    : ${escapeHtml(rt.rosDistro||'not detected')}
Setup  : ${escapeHtml(rt.rosSetup||'not detected')}
Python : ${escapeHtml(rt.python||'unknown')}
App    : ${escapeHtml(rt.appVersion||'dev')}</div><div class="help" style="margin-top:10px">Ubuntu 20.04 → Foxy · 22.04 → Humble · 24.04 → Jazzy<br>Release 可在用户目录创建独立 .venv，不写入系统目录</div><div class="mini-log ${state.runtimeInstallLog?'':'hidden'}" id="runtime-install-log">${escapeHtml(state.runtimeInstallLog.slice(-5000))}</div>`,`<div class="actions"><button class="btn primary" id="install-runtime" ${state.runtimeInstallState==='running'?'disabled':''}>${icon('play')}<span id="install-runtime-label">${state.runtimeInstallState==='running'?'Installing':installed?'Repair Runtime':'Install Runtime'}</span></button><button class="btn" id="restart-backend">${icon('terminal')}Restart Backend</button></div>`,true)}</div></div>`}
function renderAbout(){return `<div class="page">${pageHead('AgroTech · SCAU','About HandEye','现代化手眼标定桌面应用，提供标定采集、求解验证与 Linux 桌面运行环境')}<div class="grid two">${card('Interface','专注清晰的桌面工作流','info',`<div class="callout">${icon('info')}<div><b>Focused calibration workflow</b><br>深色玻璃卡片、Amber accent、自定义 titlebar、sidebar workflow 与轻量微动画</div></div>`)}${card('Core Integrity','核心计算文件保持受保护边界','check',`<div class="stack"><div class="runtime-line">${dot('success')} algorithm_runner.py protected</div><div class="runtime-line">${dot('success')} calibration_engine.py protected</div><div class="runtime-line">${dot('success')} ros_interface.py protected</div><div class="runtime-line">${dot('success')} algorithms/* protected</div></div>`)}</div></div>`}

function animateCurrentPage(){
  const page=$('#page > .page')
  if(!page)return
  requestAnimationFrame(()=>{
    page.animate([
      {opacity:0,transform:'translate3d(0,9px,0)'},
      {opacity:1,transform:'translate3d(0,0,0)'}
    ],{duration:260,easing:'cubic-bezier(.16,1,.3,1)'})
    $$('.card',page).slice(0,8).forEach((card,index)=>card.animate([
      {opacity:.72,transform:'translate3d(0,5px,0)'},
      {opacity:1,transform:'translate3d(0,0,0)'}
    ],{duration:240,delay:index*18,easing:'cubic-bezier(.16,1,.3,1)',fill:'both'}))
  })
}

function renderPage(animate=false){
  $$('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.page===state.page))
  const names={connect:'Connect',intrinsics:'Intrinsics',handeye:'Hand-Eye',solve:'Solve & Verify',settings:'Settings',about:'About'}
  $('#breadcrumb').textContent=(['settings','about'].includes(state.page)?'Application':'Calibration')+' / '+names[state.page]
  const html={connect:renderConnect,intrinsics:renderIntrinsics,handeye:renderHandeye,solve:renderSolve,settings:renderSettings,about:renderAbout}[state.page]()
  $('#page').innerHTML=html
  if(animate)animateCurrentPage()
  bindPage(); updateShell()
}

function configFromForm(scope='connect'){
  const c={...state.data.config};
  if(scope==='connect'){
    c.output_dir=$('#output-dir')?.value??c.output_dir;c.camera_index=Number($('#camera-index')?.value??c.camera_index);c.camera_width=Number($('#camera-width')?.value??c.camera_width);c.camera_height=Number($('#camera-height')?.value??c.camera_height);c.ros_input_type=$('#ros-input-type')?.value??c.ros_input_type;c.pose_topic=$('#pose-topic')?.value??c.pose_topic;c.joint_dof=Number($('#joint-dof')?.value??c.joint_dof);c.joint_names=$('#joint-names')?.value??c.joint_names;c.capture_topic=$('#capture-topic')?.value??c.capture_topic;c.status_topic=$('#status-topic')?.value??c.status_topic
  }
  if(scope==='board'){c.chessboard_cols=Number($('#board-cols')?.value??c.chessboard_cols);c.chessboard_rows=Number($('#board-rows')?.value??c.chessboard_rows);c.square_size_mm=Number($('#square-mm')?.value??c.square_size_mm)}
  return c
}
async function request(method,params={},okMessage=''){
  if(!api){toast('Backend unavailable','请从 Electron 应用启动，而不是直接打开 HTML','danger');throw new Error('backend unavailable')}
  try{const r=await api.request(method,params);if(okMessage)toast(okMessage,'','success');return r}catch(e){toast('操作失败',e.message||String(e),'danger');throw e}
}
async function saveConfig(scope='connect'){const r=await request('set_config',configFromForm(scope),'设置已保存');state.data=r;renderPage()}
function bindSegment(id,key){const el=$('#'+id);if(!el)return;$$('button',el).forEach(b=>b.onclick=()=>{state[key]=b.dataset.value;renderPage()})}
function bindPage(){
  bindSegment('intrinsic-quality','intrinsicQuality');bindSegment('handeye-quality','handeyeQuality');bindSegment('sample-mode','sampleMode');bindSegment('solve-mode','solveMode')
  $('#browse-output')?.addEventListener('click',async()=>{const p=await api?.selectDirectory($('#output-dir').value);if(p)$('#output-dir').value=p})
  $('#save-connect')?.addEventListener('click',()=>saveConfig('connect'))
  $('#open-camera')?.addEventListener('click',async()=>{await saveConfig('connect');await request('open_camera',{},'相机已打开');await refreshState()})
  $('#close-camera')?.addEventListener('click',async()=>{await request('close_camera',{},'相机已关闭');await refreshState()})
  $('#start-ros')?.addEventListener('click',async()=>{await saveConfig('connect');const c=state.data.config;await request('start_ros',{input_type:c.ros_input_type,input_topic:c.pose_topic,capture_topic:c.capture_topic,status_topic:c.status_topic,joint_dof:c.joint_dof,joint_names:c.joint_names},'ROS2 已连接');await refreshState()})
  $('#stop-ros')?.addEventListener('click',async()=>{await request('stop_ros',{},'ROS2 已断开');await refreshState()})
  $('#save-board')?.addEventListener('click',()=>saveConfig('board'))
  $('#capture-intrinsic')?.addEventListener('click',async()=>{const r=await request('capture_intrinsic',{quality_mode:state.intrinsicQuality},'内参图片已采集');toast('采样质量',`Sharpness ${n(r.sharpness,0)} · Coverage ${n(r.board_coverage_percent,1)}%`,'success');await refreshState()})
  $('#solve-intrinsic')?.addEventListener('click',async()=>{state.intrinsicResult=await request('solve_intrinsic',{quality_mode:state.intrinsicQuality},'内参已计算并保存');await refreshState();renderPage()})
  $('#clear-intrinsic')?.addEventListener('click',async()=>{await request('clear_intrinsic',{},'内参采样已清空');state.intrinsicResult=null;await refreshState()})
  $('#go-handeye')?.addEventListener('click',()=>navigate('handeye'));$('#go-solve')?.addEventListener('click',()=>navigate('solve'))
  $('#manual-type')?.addEventListener('change',e=>{state.manualType=e.target.value;renderPage()});$('#angle-unit')?.addEventListener('change',e=>{state.angleUnit=e.target.value;renderPage()})
  $('#capture-handeye')?.addEventListener('click',async()=>{const params={mode:state.sampleMode,quality_mode:state.handeyeQuality};if(state.sampleMode==='manual'){params.manual_type=state.manualType;params.angle_unit=state.angleUnit;params.values=$$('[id^="manual-"]').map(e=>Number(e.value))}const r=await request('capture_handeye',params,'手眼样本已采集');toast('样本质量',`Reproj ${n(r.reprojection_error_px,3)} px · ${n(r.pixels_per_square,1)} px/square`,'success');await refreshState()})
  $('#save-samples')?.addEventListener('click',async()=>{const r=await request('save_samples',{},'samples.yaml 已保存');toast('保存完成',r.path,'success');await refreshState()})
  $('#clear-samples')?.addEventListener('click',async()=>{await request('clear_samples',{},'外参样本已清空');await refreshState()})
  for(const [id,name] of [['run-diagnose','diagnose'],['run-solve','solve'],['run-verify','verify']]) $('#'+id)?.addEventListener('click',async()=>{const b=$('#'+id);b.disabled=true;try{const r=await request('run_tool',{name,solve_mode:state.solveMode},`${name} 完成`);if(r.log&&!state.logs.includes(r.log))state.logs+=r.log;if(r.result)state.solveResult=r.result;renderPage();setTimeout(()=>{$('#log-box')?.scrollTo(0,999999)},0)}finally{if($('#'+id))$('#'+id).disabled=false}})
  $('#install-runtime')?.addEventListener('click',async()=>{if(!api?.runtimeInstall)return;state.runtimeInstallState='running';state.runtimeInstallLog='';renderPage();try{await api.runtimeInstall();state.runtimeInstallState='done';state.runtime=await api.runtimeInfo();toast('Runtime 安装完成','Python backend 已重新启动','success')}catch(e){state.runtimeInstallState='error';toast('Runtime 安装失败',e.message||String(e),'danger')}renderPage()})
  $('#restart-backend')?.addEventListener('click',async()=>{if(!api?.backendRestart)return;await api.backendRestart();toast('Backend restarting','','success')})
  const theme=$('#theme-segment');if(theme)$$('button',theme).forEach(b=>b.onclick=()=>applyTheme(b.dataset.theme))
}

function updateShell(){const cam=state.data.camera||{},ros=state.data.ros||{};const p=$('#camera-pill');if(p)p.innerHTML=`${dot(cam.open?'success':'warning')} Camera ${cam.open?'Live':'Offline'}`;const r=$('#ros-pill');if(r)r.innerHTML=`${dot(ros.running?'success':'warning')} ROS2 ${ros.running?'Connected':'Offline'}`;const b=$('#board-pill');if(b)b.innerHTML=`${dot(cam.board_found?'success':'warning')} Board ${cam.board_found?'Detected':'—'}`;const rl=$('#runtime-label');if(rl){rl.textContent=state.backend==='ready'?'Python backend · ready':`Backend · ${state.backend}`;rl.previousElementSibling?.classList.toggle('success',state.backend==='ready')}const rs=$('#ros-sidebar');if(rs)rs.textContent=state.runtime?.rosSetup?`ROS · ${state.runtime.rosSetup.split('/').slice(-2,-1)[0]}`:'ROS environment · not detected'}
let pendingPreview=null
let previewRaf=0
function updatePreviewFrame(data){
  state.preview=data.jpeg||''
  state.data.camera={...(state.data.camera||{}),open:true,board_found:Boolean(data.board_found),width:data.width,height:data.height}
  updateShell()
  pendingPreview=data
  if(previewRaf)return
  previewRaf=requestAnimationFrame(()=>{
    previewRaf=0
    const frame=pendingPreview
    pendingPreview=null
    if(!frame)return
    const surface=$('#preview-surface')
    if(surface){
      let img=$('.preview-image',surface)
      if(!img){surface.innerHTML='<img class="preview-image" alt="Camera preview" decoding="async">';img=$('.preview-image',surface)}
      if(img&&frame.jpeg)img.src='data:image/jpeg;base64,'+frame.jpeg
    }
    const live=$('#preview-live-pill')
    if(live)live.innerHTML=`${dot('success')} Live`
    const size=$('#preview-size')
    if(size)size.textContent=`${frame.width||640} × ${frame.height||480}`
    const board=$('#board-live')
    if(board){board.textContent=frame.board_found?'Detected':'Not detected';board.style.color=frame.board_found?'var(--success)':'var(--warning)'}
  })
}

function updatePoseView(data){state.data.ros={...(state.data.ros||{}),running:true,pose:data};const pose=$('#pose-live');if(pose)pose.textContent=poseText();updateShell()}
function updateRuntimeView(){const rt=state.runtime||{};const installed=Boolean(rt.runtimeInstalled);const label=$('#runtime-health-label');if(label)label.textContent=installed?'Per-user runtime ready':'Per-user runtime not installed';const pathEl=$('#runtime-health-path');if(pathEl)pathEl.textContent=rt.runtimePython||'~/.local/share/handeye-calibration/.venv/bin/python';const info=$('#runtime-info-box');if(info)info.textContent=`Ubuntu : ${rt.ubuntu||'unknown'}\nROS    : ${rt.rosDistro||'not detected'}\nSetup  : ${rt.rosSetup||'not detected'}\nPython : ${rt.python||'unknown'}\nApp    : ${rt.appVersion||'dev'}`;const log=$('#runtime-install-log');if(log){log.textContent=state.runtimeInstallLog.slice(-5000);log.classList.toggle('hidden',!state.runtimeInstallLog)}const install=$('#install-runtime');if(install)install.disabled=state.runtimeInstallState==='running';const installLabel=$('#install-runtime-label');if(installLabel)installLabel.textContent=state.runtimeInstallState==='running'?'Installing':installed?'Repair Runtime':'Install Runtime'}
function appendBackendLog(text){state.logs+=text||'';const log=$('#log-box');if(log){log.textContent=state.logs;log.scrollTop=log.scrollHeight}}
async function refreshState(){if(!api)return;try{state.data=await api.request('get_state');updateShell();renderPage(false)}catch(e){state.backend='error';updateShell()}}
function handleEvent(msg){const {event,data}=msg;if(event==='state'){state.data=data;updateShell()}else if(event==='preview'){updatePreviewFrame(data)}else if(event==='pose'){updatePoseView(data)}else if(event==='log'){appendBackendLog(data.text||'')}else if(event==='error'){toast('Backend',data?.message||'Unknown error','danger')}else if(event==='tool_done'){if(data?.result)state.solveResult=data.result}}

async function boot(){shell();applyTheme(state.theme);renderPage(false);if(!api){state.backend='unavailable';updateShell();toast('Electron bridge 未加载','请使用 npm start / Release 应用启动','warning');return}api.onEvent?.(handleEvent);api.onRuntime?.(m=>{state.backend=m.state||'unknown';state.runtime={...(state.runtime||{}),...m};updateShell();updateRuntimeView()});api.onRuntimeInstall?.(m=>{if(m.state==='starting')state.runtimeInstallState='running';if(m.state==='log')state.runtimeInstallLog+=(m.text||'');if(m.state==='done')state.runtimeInstallState='done';if(m.state==='error')state.runtimeInstallState='error';updateRuntimeView()});api.onStderr?.(t=>appendBackendLog('[backend] '+t));try{state.runtime=await api.runtimeInfo();const ping=await api.request('ping');state.backend=ping.pong?'ready':'error';state.data=await api.request('get_state')}catch(e){state.backend='error';toast('Backend 启动失败',e.message,'danger')}updateShell();renderPage(false)}
boot()
