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

const PAGE_EXIT_MS = 160
const PAGE_ENTER_MS = 420
let navigationEpoch = 0
let responsiveListenerBound = false

const i18n = window.HandEyeI18n
const initialLanguage = i18n?.loadLanguage?.() || 'en'

const state = {
  page:'connect', theme:localStorage.getItem('handeye-theme') || 'dark', language:initialLanguage, backend:'starting', runtime:null,
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

function t(key, variables={}) {
  return i18n?.t?.(state.language, key, variables) ?? key
}
function setLanguage(language) {
  if(!['zh-CN','en'].includes(language) || language===state.language)return
  state.language=language
  i18n?.setStoredLanguage?.(language)
  document.documentElement.lang=language
  updateShellLanguage()
  renderPage(false)
  updateShell()
  requestAnimationFrame(()=>syncAllSegmentIndicators(false))
}

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
  if(toggle)toggle.setAttribute('aria-label',`${t('appearance.title')} ${theme}`)
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
      <div class="brand-mini"><span class="logo-mark">${icon('target')}</span><b>${t('app.title')}</b></div>
      <div class="titlebar-center">${t('app.workstation')}</div>
      <div class="title-actions"><div class="appearance-wrap"><button class="title-button appearance-toggle" id="appearance-toggle" aria-label="${t('appearance.title')}"><span id="appearance-icon">${icon(themeIcon(state.theme))}</span></button><div class="appearance-menu hidden" id="appearance-menu"><div class="appearance-menu-label">${t('appearance.title')}</div>${themeMenuChoice('system',t('appearance.system'),t('appearance.systemDesc'))}${themeMenuChoice('dark',t('appearance.dark'),t('appearance.darkDesc'))}${themeMenuChoice('light',t('appearance.light'),t('appearance.lightDesc'))}</div></div><span class="title-separator"></span><button class="title-button" id="win-min">${icon('minus')}</button><button class="title-button" id="win-max">${icon('max')}</button><button class="title-button close" id="win-close">${icon('x')}</button></div>
    </header>
    <div class="app-body">
      <aside class="sidebar">
        <div class="sidebar-hero"><div class="eyebrow">AgroTech · SCAU</div><h1>HandEye</h1><p>${t('sidebar.subtitle')}<br>${t('sidebar.eyeInHand')}</p></div>
        <div class="nav-caption">${t('sidebar.calibration')}</div><nav class="nav-list">
          ${nav('connect','plug',t('nav.connect'),'01')}${nav('intrinsics','scan',t('nav.intrinsics'),'02')}${nav('handeye','target',t('nav.handeye'),'03')}${nav('solve','flask',t('nav.solve'),'04')}
        </nav>
        <div class="nav-caption" style="margin-top:13px">${t('sidebar.application')}</div><nav class="nav-list">${nav('settings','settings',t('nav.settings'),'')}${nav('about','info',t('nav.about'),'')}</nav>
        <div class="sidebar-spacer"></div><div class="runtime-card"><div class="runtime-line">${dot('warning')}<span id="runtime-label">${t('status.backendState',{state:'starting'})}</span></div><div class="runtime-line" id="ros-sidebar">${t('status.rosChecking')}</div></div>
      </aside>
      <section class="content-wrap"><div class="top-status"><span class="breadcrumb" id="breadcrumb">${t('breadcrumb.calibration')} / ${t('nav.connect')}</span><span class="pill" id="camera-pill">${dot('warning')} ${t('status.camera')} ${t('status.offline')}</span><span class="pill" id="ros-pill">${dot('warning')} ROS2 ${t('status.rosOffline')}</span><span class="pill" id="board-pill">${dot('warning')} ${t('status.board')} —</span></div><main class="content"><div id="page"></div></main></section>
    </div><div class="toast-stack" id="toasts"></div></div>`
  $('#win-min').onclick=()=>api?.window?.minimize();$('#win-max').onclick=()=>api?.window?.maximize();$('#win-close').onclick=()=>api?.window?.close()
  bindAppearanceMenu()
  $$('.nav-item').forEach(b=>b.onclick=()=>navigate(b.dataset.page))
}
function nav(page,ico,label,step){return `<button class="nav-item" data-page="${page}">${icon(ico)}<span>${label}</span>${step?`<span class="step">${step}</span>`:''}</button>`}
function updateShellLanguage(){
  const title=$('.titlebar-center');if(title)title.textContent=t('app.workstation')
  const hero=$('.sidebar-hero p');if(hero)hero.innerHTML=`${t('sidebar.subtitle')}<br>${t('sidebar.eyeInHand')}`
  const captions=$$('.nav-caption');if(captions[0])captions[0].textContent=t('sidebar.calibration');if(captions[1])captions[1].textContent=t('sidebar.application')
  const labels={connect:'nav.connect',intrinsics:'nav.intrinsics',handeye:'nav.handeye',solve:'nav.solve',settings:'nav.settings',about:'nav.about'}
  for(const [page,key] of Object.entries(labels)){const label=$(`.nav-item[data-page="${page}"] > span:not(.step)`);if(label)label.textContent=t(key)}
  const menu=$('#appearance-menu')
  if(menu){
    const heading=$('.appearance-menu-label',menu);if(heading)heading.textContent=t('appearance.title')
    const rows=$$('.appearance-option',menu)
    const copy=[['appearance.system','appearance.systemDesc'],['appearance.dark','appearance.darkDesc'],['appearance.light','appearance.lightDesc']]
    rows.forEach((row,index)=>{const pair=copy[index];if(!pair)return;const b=$('b',row),small=$('small',row);if(b)b.textContent=t(pair[0]);if(small)small.textContent=t(pair[1])})
  }
  const toggle=$('#appearance-toggle');if(toggle)toggle.setAttribute('aria-label',t('appearance.title'))
}
function closeAppearanceMenu(){const menu=$('#appearance-menu');if(!menu)return;menu.classList.remove('visible');setTimeout(()=>menu.classList.add('hidden'),130)}
function prefersReducedMotion(){return matchMedia('(prefers-reduced-motion: reduce)').matches}
async function transitionToPage(page){
  if(page===state.page)return
  const epoch=++navigationEpoch
  const oldPage=$('#page > .page')
  if(oldPage&&!prefersReducedMotion()){
    try{
      await oldPage.animate([
        {opacity:1,transform:'translate3d(0,0,0) scale(1)'},
        {opacity:.18,transform:'translate3d(0,-6px,0) scale(.996)'}
      ],{duration:PAGE_EXIT_MS,easing:'cubic-bezier(.4,0,.6,1)',fill:'forwards'}).finished
    }catch{}
    if(epoch!==navigationEpoch)return
  }
  state.page=page
  renderPage(false)
  const content=$('.content')
  if(content)content.scrollTop=0
  if(!prefersReducedMotion())animateCurrentPage()
}
function navigate(page){closeAppearanceMenu();void transitionToPage(page)}

function pageHead(kicker,title,desc,actions=''){return `<div class="page-head"><div class="page-head-main"><div class="page-kicker">${kicker}</div><h2 class="page-title">${title}</h2><p class="page-description">${desc}</p></div>${actions?`<div class="page-actions">${actions}</div>`:''}</div>`}
function card(title,subtitle,ico,body,footer='',accent=false){return `<section class="card"><div class="card-head"><span class="card-icon ${accent?'accent':''}">${icon(ico)}</span><div><h3 class="card-title">${title}</h3>${subtitle?`<p class="card-subtitle">${subtitle}</p>`:''}</div></div><div class="card-body">${body}</div>${footer?`<div class="card-footer">${footer}</div>`:''}</section>`}
function field(label,id,value,type='text',help=''){return `<div class="field"><label for="${id}">${label}</label><input class="control" id="${id}" type="${type}" value="${escapeHtml(value)}"/>${help?`<div class="help">${help}</div>`:''}</div>`}
function btn(id,label,ico='play',kind='',extra=''){return `<button class="btn ${kind}" id="${id}" ${extra}>${icon(ico)}${label}</button>`}
function preview(){const cam=state.data.camera||{};return `<section class="card preview-card"><div class="preview-toolbar"><b>${t('preview.title')}</b><span class="pill" id="preview-live-pill">${dot(cam.open?'success':'warning')} ${cam.open?t('status.live'):t('status.offline')}</span><span class="meta" id="preview-size">${cam.width||640} × ${cam.height||480}</span></div><div class="preview-surface" id="preview-surface">${state.preview?`<img class="preview-image" src="data:image/jpeg;base64,${state.preview}"/>`:`<div class="preview-empty"><div class="ring">${icon('camera')}</div><b>${t('preview.waitingTitle')}</b><span>${t('preview.waitingDesc')}</span></div>`}</div></section>`}

function renderConnect(){const c=state.data.config,cam=state.data.camera,ros=state.data.ros;return `<div class="page">${pageHead(t('connect.kicker'),t('connect.title'),t('connect.desc'))}
<div class="grid three" style="margin-bottom:14px"><div class="metric"><div class="metric-label">${t('connect.metricCamera')}</div><div class="metric-value" style="color:${cam.open?'var(--success)':'var(--text-secondary)'}">${cam.open?t('status.connected'):t('status.offline')}</div><div class="metric-meta">${t('connect.device',{index:c.camera_index,width:c.camera_width,height:c.camera_height})}</div></div><div class="metric"><div class="metric-label">${t('connect.metricRobot')}</div><div class="metric-value" style="color:${ros.running?'var(--success)':'var(--text-secondary)'}">${ros.running?t('status.receiving'):t('status.disconnected')}</div><div class="metric-meta">${escapeHtml(c.pose_topic)}</div></div><div class="metric"><div class="metric-label">${t('connect.metricOutput')}</div><div class="metric-value">${state.data.handeye?.count||0}<small>${t('connect.samples')}</small></div><div class="metric-meta">${escapeHtml(c.output_dir||t('connect.notConfigured'))}</div></div></div>
<div class="grid preview-layout">${preview()}<div class="stack">
${card(t('connect.projectCamera'),t('connect.projectCameraDesc'),'camera',`<div class="form-row"><div class="field full"><label>${t('field.outputDir')}</label><div class="inline-control"><input class="control" id="output-dir" value="${escapeHtml(c.output_dir)}"/><button class="btn" id="browse-output">${icon('folder')}${t('action.browse')}</button></div></div>${field(t('field.cameraIndex'),'camera-index',c.camera_index,'number')}${field(t('field.width'),'camera-width',c.camera_width,'number')}${field(t('field.height'),'camera-height',c.camera_height,'number')}</div>`,`<div class="actions">${btn('save-connect',t('action.saveSettings'),'save')}${cam.open?btn('close-camera',t('action.closeCamera'),'square',''):btn('open-camera',t('action.openCamera'),'camera','primary')}</div>`,true)}
${card(t('connect.robotInterface'),t('connect.robotInterfaceDesc'),'plug',`<div class="form-row"><div class="field"><label>${t('field.inputType')}</label><select class="control" id="ros-input-type"><option value="pose" ${c.ros_input_type==='pose'?'selected':''}>PoseStamped</option><option value="joints" ${c.ros_input_type==='joints'?'selected':''}>JointState</option></select></div>${field(t('field.inputTopic'),'pose-topic',c.pose_topic)}${field(t('field.jointDof'),'joint-dof',c.joint_dof,'number')}${field(t('field.jointNames'),'joint-names',c.joint_names||'')}${field(t('field.captureTopic'),'capture-topic',c.capture_topic||'')}${field(t('field.statusTopic'),'status-topic',c.status_topic||'')}</div>`,`<div class="actions">${ros.running?btn('stop-ros',t('action.disconnectRos'),'square'):btn('start-ros',t('action.connectRos'),'plug','primary')}</div>`,false)}
<div class="callout">${icon('info')}<div><b>${t('connect.interfaceTitle')}</b><br>${t('connect.interfaceBody')}</div></div>
</div></div></div>`}

function boardFields(){const c=state.data.config;return `<div class="form-row three">${field(t('board.cols'),'board-cols',c.chessboard_cols,'number')}${field(t('board.rows'),'board-rows',c.chessboard_rows,'number')}${field(t('board.square'),'square-mm',c.square_size_mm,'number')}</div>`}
function segmentedControl(id,current,options,extraClass='amber'){
  return `<div class="segmented ${extraClass}" id="${id}"><span class="segmented-indicator" aria-hidden="true"></span>${options.map(([value,label])=>`<button data-value="${value}" class="${current===value?'active':''}">${label}</button>`).join('')}</div>`
}
function qualitySegment(id,current){return segmentedControl(id,current,[['standard',t('quality.standard')],['strict',t('quality.strict')],['minimal',t('quality.minimal')]])}
function renderIntrinsics(){const x=state.data.intrinsics||{},cam=state.data.camera;const target=state.intrinsicQuality==='strict'?15:state.intrinsicQuality==='minimal'?3:10;const pct=Math.min(100,(x.count||0)/target*100);return `<div class="page">${pageHead(t('intrinsics.kicker'),t('intrinsics.title'),t('intrinsics.desc'),btn('go-handeye',t('intrinsics.next'),'chevron'))}
<div class="grid preview-layout">${preview()}<div class="stack">${card(t('intrinsics.boardTitle'),t('intrinsics.boardDesc'),'scan',boardFields(),`${btn('save-board',t('intrinsics.saveBoard'),'save')}`)}
${card(t('intrinsics.captureTitle'),t('intrinsics.captureDesc'),'camera',`<div class="progress-label"><span>${t('intrinsics.captured',{count:x.count||0})}</span><span id="intrinsic-target">${t('intrinsics.minimum',{count:target})}</span></div><div class="progress-track"><div class="progress-bar" id="intrinsic-progress" style="width:${pct}%"></div></div><div style="margin-top:14px"><div class="field"><label>${t('intrinsics.quality')}</label>${qualitySegment('intrinsic-quality',state.intrinsicQuality)}</div></div><div class="grid two" style="margin-top:13px"><div class="metric"><div class="metric-label">${t('intrinsics.chessboard')}</div><div class="metric-value" id="board-live" style="font-size:17.25px;color:${cam.board_found?'var(--success)':'var(--warning)'}">${cam.board_found?t('status.detected'):t('status.notDetected')}</div></div><div class="metric"><div class="metric-label">${t('intrinsics.file')}</div><div class="metric-value" style="font-size:17.25px;color:${x.exists?'var(--success)':'var(--text-secondary)'}">${x.exists?t('status.ready'):t('status.pending')}</div></div></div>`,`<div class="actions">${btn('capture-intrinsic',t('intrinsics.capture'),'camera','primary large',cam.open?'':'disabled')}${btn('solve-intrinsic',t('intrinsics.solveSave'),'flask','',x.count>=target?'':'disabled')}${btn('clear-intrinsic',t('action.clear'),'trash','danger')}</div>`,true)}
${state.intrinsicResult?`<div class="callout">${icon('check')}<div><b>${t('intrinsics.saved')}</b><br>RMS ${n(state.intrinsicResult.reprojection_error_px,4)} px · Median ${n(state.intrinsicResult.reprojection_error_median_px,4)} px · Max ${n(state.intrinsicResult.reprojection_error_max_px,4)} px</div></div>`:''}</div></div></div>`}

function poseText(){const p=state.data.ros?.pose;if(!p)return t('robot.waitingData');const v=p.values||[];return `frame : ${p.frame_id||'-'}\nxyz   : ${n(v[0],5)}  ${n(v[1],5)}  ${n(v[2],5)} m\nxyzw  : ${n(v[3],5)}  ${n(v[4],5)}  ${n(v[5],5)}  ${n(v[6],5)}`}
function manualFields(){let labels=state.manualType==='quaternion'?['x','y','z','qx','qy','qz','qw']:state.manualType==='rpy'?['x','y','z','roll','pitch','yaw']:Array.from({length:Number(state.data.config.joint_dof)||5},(_,i)=>`q${i+1}`);return `<div class="form-row three">${labels.map((l,i)=>field(l,`manual-${i}`,state.manualType==='quaternion'&&i===6?1:0,'number')).join('')}</div>`}
function manualInputPanel(){return `<div class="manual-input-panel ${state.sampleMode==='manual'?'open':''}" id="manual-input-panel"><div class="manual-input-inner"><div class="divider"></div><div class="form-row"><div class="field"><label>${t('manual.type')}</label><select class="control" id="manual-type"><option value="quaternion" ${state.manualType==='quaternion'?'selected':''}>${t('manual.poseQuaternion')}</option><option value="rpy" ${state.manualType==='rpy'?'selected':''}>${t('manual.poseRpy')}</option><option value="joints" ${state.manualType==='joints'?'selected':''}>${t('manual.jointAngles')}</option></select></div><div class="field"><label>${t('manual.angleUnit')}</label><select class="control" id="angle-unit"><option value="deg" ${state.angleUnit==='deg'?'selected':''}>deg</option><option value="rad" ${state.angleUnit==='rad'?'selected':''}>rad</option></select></div></div><div id="manual-fields" style="margin-top:11px">${manualFields()}</div></div></div>`}
function renderHandeye(){const h=state.data.handeye||{},ros=state.data.ros||{};const target=20,pct=Math.min(100,(h.count||0)/target*100);return `<div class="page">${pageHead(t('handeye.kicker'),t('handeye.title'),t('handeye.desc'),btn('go-solve',t('handeye.next'),'chevron'))}
<div class="grid preview-layout">${preview()}<div class="stack">${card(t('handeye.robotPose'),ros.running?t('handeye.robotAutoReceiving'):t('handeye.robotChooseSource'),'target',`<div class="pose-box" id="pose-live">${escapeHtml(poseText())}</div><div style="margin-top:12px"><div class="field"><label>${t('handeye.source')}</label>${segmentedControl('sample-mode',state.sampleMode,[['auto',t('handeye.auto')],['manual',t('handeye.manual')]])}</div></div>${manualInputPanel()}`)}
${card(t('handeye.collectionTitle'),t('handeye.collectionDesc'),'scan',`<div class="progress-label"><span>${t('handeye.captured',{count:h.count||0})}</span><span>${t('handeye.recommended',{count:target})}</span></div><div class="progress-track"><div class="progress-bar" style="width:${pct}%"></div></div><div style="margin-top:14px"><div class="field"><label>${t('intrinsics.quality')}</label>${qualitySegment('handeye-quality',state.handeyeQuality)}</div></div><div class="grid three" style="margin-top:13px"><div class="metric"><div class="metric-label">${t('handeye.samples')}</div><div class="metric-value">${h.count||0}</div></div><div class="metric"><div class="metric-label">${t('handeye.camera')}</div><div class="metric-value" style="font-size:16.1px;color:${state.data.camera?.open?'var(--success)':'var(--warning)'}">${state.data.camera?.open?t('status.ready'):t('status.offline')}</div></div><div class="metric"><div class="metric-label">${t('handeye.robot')}</div><div class="metric-value" id="robot-source-status" style="font-size:16.1px;color:${state.sampleMode==='manual'||ros.pose?'var(--success)':'var(--warning)'}">${state.sampleMode==='manual'?t('status.manual'):ros.pose?t('status.ready'):t('status.waiting')}</div></div></div>`,`<div class="actions">${btn('capture-handeye',t('handeye.capture'),'target','primary large')}${btn('save-samples',t('handeye.save'),'save')}${btn('clear-samples',t('action.clear'),'trash','danger')}</div>`,true)}</div></div></div>`}

function matrixHtml(result){const m=result?.transform_matrix;if(!Array.isArray(m)||m.length!==4)return `<div class="pose-box">${t('solve.waitingResult')}</div>`;return `<div class="result-matrix">${m.flat().map(v=>`<span>${n(v,6)}</span>`).join('')}</div>`}
function renderSolve(){const h=state.data.handeye||{};const r=state.solveResult;return `<div class="page">${pageHead(t('solve.kicker'),t('solve.title'),t('solve.desc'))}
<div class="grid two" style="margin-bottom:14px"><div class="metric"><div class="metric-label">samples.yaml</div><div class="metric-value" style="font-size:17.25px;color:${h.samples_exists?'var(--success)':'var(--warning)'}">${h.samples_exists?t('status.ready'):t('status.notSaved')}</div><div class="metric-meta">${escapeHtml(h.samples_path||'')}</div></div><div class="metric"><div class="metric-label">${t('solve.result')}</div><div class="metric-value" style="font-size:17.25px;color:${r?'var(--success)':'var(--text-secondary)'}">${r?t('status.solved'):t('status.waiting')}</div><div class="metric-meta">samples_result.yaml</div></div></div>
<div class="grid preview-layout"><div class="stack">${card(t('solve.pipeline'),t('solve.pipelineDesc'),'flask',`<div class="field"><label>${t('solve.mode')}</label>${segmentedControl('solve-mode',state.solveMode,[['robust',t('solve.robust')],['minimal',t('solve.opencv')],['ba',t('solve.ba')]])}</div><div class="divider"></div><div class="actions">${btn('run-diagnose',t('action.diagnose'),'scan')}${btn('run-solve',t('action.solve'),'play','primary')}${btn('run-verify',t('action.verify'),'check')}</div>`)}
${card(t('solve.transform'),t('solve.transformDesc'),'target',`${matrixHtml(r)}${r?`<div class="grid two" style="margin-top:12px"><div class="metric"><div class="metric-label">${t('solve.translationRms')}</div><div class="metric-value">${n(r.translation_rms_mm,3)}<small>mm</small></div></div><div class="metric"><div class="metric-label">${t('solve.rotationRms')}</div><div class="metric-value">${n(r.rotation_rms_deg,3)}<small>deg</small></div></div></div>`:''}`)}</div>
${card(t('solve.log'),t('solve.logDesc'),'terminal',`<div class="log-box" id="log-box">${escapeHtml(state.logs||t('solve.noOutput'))}</div>`,`<span style="font-size:11.5px;color:var(--text-dim)">${t('solve.coreProtected')}</span>`)}</div></div>`}

function renderSettings(){const rt=state.runtime||{};const installed=Boolean(rt.runtimeInstalled);return `<div class="page">${pageHead(t('settings.kicker'),t('settings.title'),t('settings.desc'))}<div class="grid two">${card(t('settings.appearance'),t('settings.appearanceDesc'),'sun',`<div class="field"><label>${t('settings.theme')}</label><div class="theme-selector" id="theme-segment">${themeSettingsChoice('system',t('appearance.system'))}${themeSettingsChoice('dark',t('appearance.dark'))}${themeSettingsChoice('light',t('appearance.light'))}</div></div>`)}${card(t('settings.language'),t('settings.languageDesc'),'info',`<div class="field"><label>${t('settings.languageLabel')}</label>${segmentedControl('language-selector',state.language,[['zh-CN',t('settings.zhCN')],['en',t('settings.english')]],'amber')}</div>`)}${card(t('settings.runtime'),t('settings.runtimeDesc'),'terminal',`<div class="runtime-health"><div>${dot(installed?'success':'warning')}<b id="runtime-health-label">${installed?t('runtime.ready'):t('runtime.notInstalled')}</b></div><span id="runtime-health-path">${escapeHtml(rt.runtimePython||'~/.local/share/handeye-calibration/.venv/bin/python')}</span></div><div class="pose-box" id="runtime-info-box" style="margin-top:11px">Ubuntu : ${escapeHtml(rt.ubuntu||'unknown')}
ROS    : ${escapeHtml(rt.rosDistro||'not detected')}
Setup  : ${escapeHtml(rt.rosSetup||'not detected')}
Python : ${escapeHtml(rt.python||'unknown')}
App    : ${escapeHtml(rt.appVersion||'dev')}</div><div class="help" style="margin-top:10px">${t('runtime.help')}</div><div class="mini-log ${state.runtimeInstallLog?'':'hidden'}" id="runtime-install-log">${escapeHtml(state.runtimeInstallLog.slice(-5000))}</div>`,`<div class="actions"><button class="btn primary" id="install-runtime" ${state.runtimeInstallState==='running'?'disabled':''}>${icon('play')}<span id="install-runtime-label">${state.runtimeInstallState==='running'?t('runtime.installing'):installed?t('runtime.repair'):t('runtime.install')}</span></button><button class="btn" id="restart-backend">${icon('terminal')}${t('runtime.restart')}</button></div>`,true)}</div></div>`}
function renderAbout(){return `<div class="page">${pageHead(t('about.kicker'),t('about.title'),t('about.desc'))}<div class="grid two">${card(t('about.experience'),t('about.experienceDesc'),'info',`<div class="callout">${icon('info')}<div><b>${t('about.focusTitle')}</b><br>${t('about.focusBody')}</div></div>`)}${card(t('about.core'),t('about.coreDesc'),'check',`<div class="stack"><div class="runtime-line">${dot('success')} ${t('about.protected',{name:'algorithm_runner.py'})}</div><div class="runtime-line">${dot('success')} ${t('about.protected',{name:'calibration_engine.py'})}</div><div class="runtime-line">${dot('success')} ${t('about.protected',{name:'ros_interface.py'})}</div><div class="runtime-line">${dot('success')} ${t('about.protected',{name:'algorithms/*'})}</div></div>`)}</div></div>`}

function animateCurrentPage(){
  const page=$('#page > .page')
  if(!page)return
  requestAnimationFrame(()=>{
    page.animate([
      {opacity:.08,transform:'translate3d(0,12px,0) scale(.997)'},
      {opacity:1,transform:'translate3d(0,0,0) scale(1)'}
    ],{duration:PAGE_ENTER_MS,easing:'cubic-bezier(.16,1,.3,1)',fill:'both'})
    $$('.card',page).slice(0,10).forEach((card,index)=>card.animate([
      {opacity:.48,transform:'translate3d(0,8px,0)'},
      {opacity:1,transform:'translate3d(0,0,0)'}
    ],{duration:460,delay:32+index*24,easing:'cubic-bezier(.16,1,.3,1)',fill:'both'}))
  })
}

function renderPage(animate=false){
  $$('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.page===state.page))
  const names={connect:t('nav.connect'),intrinsics:t('nav.intrinsics'),handeye:t('nav.handeye'),solve:t('nav.solve'),settings:t('nav.settings'),about:t('nav.about')}
  $('#breadcrumb').textContent=(['settings','about'].includes(state.page)?t('breadcrumb.application'):t('breadcrumb.calibration'))+' / '+names[state.page]
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
  if(!api){toast(t('toast.backendUnavailable'),t('toast.useElectron'),'danger');throw new Error('backend unavailable')}
  try{const r=await api.request(method,params);if(okMessage)toast(okMessage,'','success');return r}catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger');throw e}
}
async function saveConfig(scope='connect'){const r=await request('set_config',configFromForm(scope),t('toast.settingsSaved'));state.data=r;renderPage()}
function syncSegmentIndicator(el,animate=true){
  if(!el)return
  const indicator=$('.segmented-indicator',el)
  const active=$('button.active',el)
  if(!indicator||!active)return
  const host=el.getBoundingClientRect()
  const rect=active.getBoundingClientRect()
  if(!animate)indicator.style.transition='none'
  indicator.style.width=`${rect.width}px`
  indicator.style.transform=`translate3d(${rect.left-host.left}px,0,0)`
  if(!animate)requestAnimationFrame(()=>indicator.style.removeProperty('transition'))
}
function syncAllSegmentIndicators(animate=false){$$('.segmented').forEach(el=>syncSegmentIndicator(el,animate))}
function updateIntrinsicQualityView(){
  const x=state.data.intrinsics||{}
  const target=state.intrinsicQuality==='strict'?15:state.intrinsicQuality==='minimal'?3:10
  const count=x.count||0
  const targetEl=$('#intrinsic-target')
  const progress=$('#intrinsic-progress')
  const solve=$('#solve-intrinsic')
  if(targetEl)targetEl.textContent=t('intrinsics.minimum',{count:target})
  if(progress)progress.style.width=`${Math.min(100,count/target*100)}%`
  if(solve)solve.disabled=count<target
}
function updateSampleModeView(){
  const panel=$('#manual-input-panel')
  panel?.classList.toggle('open',state.sampleMode==='manual')
  const status=$('#robot-source-status')
  if(status){
    const pose=state.data.ros?.pose
    status.textContent=state.sampleMode==='manual'?t('status.manual'):pose?t('status.ready'):t('status.waiting')
    status.style.color=state.sampleMode==='manual'||pose?'var(--success)':'var(--warning)'
  }
}
function refreshManualFields(){const host=$('#manual-fields');if(host)host.innerHTML=manualFields()}
function bindSegment(id,key,onChange){
  const el=$('#'+id)
  if(!el)return
  requestAnimationFrame(()=>syncSegmentIndicator(el,false))
  $$('button',el).forEach(b=>b.onclick=()=>{
    if(b.classList.contains('active'))return
    state[key]=b.dataset.value
    $$('button',el).forEach(item=>item.classList.toggle('active',item===b))
    syncSegmentIndicator(el,true)
    onChange?.(b.dataset.value)
  })
}
function bindPage(){
  bindSegment('intrinsic-quality','intrinsicQuality',updateIntrinsicQualityView);bindSegment('handeye-quality','handeyeQuality');bindSegment('sample-mode','sampleMode',updateSampleModeView);bindSegment('solve-mode','solveMode')
  $('#browse-output')?.addEventListener('click',async()=>{const p=await api?.selectDirectory($('#output-dir').value);if(p)$('#output-dir').value=p})
  $('#save-connect')?.addEventListener('click',()=>saveConfig('connect'))
  $('#open-camera')?.addEventListener('click',async()=>{await saveConfig('connect');await request('open_camera',{},t('toast.cameraOpened'));await refreshState()})
  $('#close-camera')?.addEventListener('click',async()=>{await request('close_camera',{},t('toast.cameraClosed'));await refreshState()})
  $('#start-ros')?.addEventListener('click',async()=>{await saveConfig('connect');const c=state.data.config;await request('start_ros',{input_type:c.ros_input_type,input_topic:c.pose_topic,capture_topic:c.capture_topic,status_topic:c.status_topic,joint_dof:c.joint_dof,joint_names:c.joint_names},t('toast.rosConnected'));await refreshState()})
  $('#stop-ros')?.addEventListener('click',async()=>{await request('stop_ros',{},t('toast.rosDisconnected'));await refreshState()})
  $('#save-board')?.addEventListener('click',()=>saveConfig('board'))
  $('#capture-intrinsic')?.addEventListener('click',async()=>{const r=await request('capture_intrinsic',{quality_mode:state.intrinsicQuality},t('toast.intrinsicCaptured'));toast(t('toast.sampleQuality'),`Sharpness ${n(r.sharpness,0)} · Coverage ${n(r.board_coverage_percent,1)}%`,'success');await refreshState()})
  $('#solve-intrinsic')?.addEventListener('click',async()=>{state.intrinsicResult=await request('solve_intrinsic',{quality_mode:state.intrinsicQuality},t('toast.intrinsicSolved'));await refreshState();renderPage()})
  $('#clear-intrinsic')?.addEventListener('click',async()=>{await request('clear_intrinsic',{},t('toast.intrinsicCleared'));state.intrinsicResult=null;await refreshState()})
  $('#go-handeye')?.addEventListener('click',()=>navigate('handeye'));$('#go-solve')?.addEventListener('click',()=>navigate('solve'))
  $('#manual-type')?.addEventListener('change',e=>{state.manualType=e.target.value;refreshManualFields()});$('#angle-unit')?.addEventListener('change',e=>{state.angleUnit=e.target.value})
  $('#capture-handeye')?.addEventListener('click',async()=>{const params={mode:state.sampleMode,quality_mode:state.handeyeQuality};if(state.sampleMode==='manual'){params.manual_type=state.manualType;params.angle_unit=state.angleUnit;params.values=$$('[id^="manual-"]').map(e=>Number(e.value))}const r=await request('capture_handeye',params,t('toast.handeyeCaptured'));toast(t('toast.sampleQuality'),`Reproj ${n(r.reprojection_error_px,3)} px · ${n(r.pixels_per_square,1)} px/square`,'success');await refreshState()})
  $('#save-samples')?.addEventListener('click',async()=>{const r=await request('save_samples',{},t('toast.samplesSaved'));toast(t('toast.saveComplete'),r.path,'success');await refreshState()})
  $('#clear-samples')?.addEventListener('click',async()=>{await request('clear_samples',{},t('toast.samplesCleared'));await refreshState()})
  for(const [id,name,labelKey] of [['run-diagnose','diagnose','action.diagnose'],['run-solve','solve','action.solve'],['run-verify','verify','action.verify']]) $('#'+id)?.addEventListener('click',async()=>{const b=$('#'+id);b.disabled=true;try{const r=await request('run_tool',{name,solve_mode:state.solveMode},t('toast.toolComplete',{name:t(labelKey)}));if(r.log&&!state.logs.includes(r.log))state.logs+=r.log;if(r.result)state.solveResult=r.result;renderPage();setTimeout(()=>{$('#log-box')?.scrollTo(0,999999)},0)}finally{if($('#'+id))$('#'+id).disabled=false}})
  $('#install-runtime')?.addEventListener('click',async()=>{if(!api?.runtimeInstall)return;state.runtimeInstallState='running';state.runtimeInstallLog='';renderPage();try{await api.runtimeInstall();state.runtimeInstallState='done';state.runtime=await api.runtimeInfo();toast(t('toast.runtimeInstalled'),t('toast.backendRestarted'),'success')}catch(e){state.runtimeInstallState='error';toast(t('toast.runtimeFailed'),e.message||String(e),'danger')}renderPage()})
  $('#restart-backend')?.addEventListener('click',async()=>{if(!api?.backendRestart)return;await api.backendRestart();toast(t('toast.backendRestarting'),'','success')})
  const theme=$('#theme-segment');if(theme)$$('button',theme).forEach(b=>b.onclick=()=>applyTheme(b.dataset.theme))
  const language=$('#language-selector');if(language){requestAnimationFrame(()=>syncSegmentIndicator(language,false));$$('button',language).forEach(b=>b.onclick=()=>{if(b.dataset.value===state.language)return;setLanguage(b.dataset.value)})}
}

function syncResponsiveShell(){
  const sidebar=$('.sidebar')
  sidebar?.classList.toggle('compact',innerWidth<=900)
  requestAnimationFrame(()=>syncAllSegmentIndicators(false))
}
function backendStateLabel(value){
  if(value==='ready')return t('status.backendReady')
  if(value==='starting')return t('status.backendStarting')
  if(value==='error')return t('status.backendError')
  if(value==='unavailable')return t('status.backendUnavailable')
  return t('status.backendState',{state:value})
}
function updateShell(){const cam=state.data.camera||{},ros=state.data.ros||{};const p=$('#camera-pill');if(p)p.innerHTML=`${dot(cam.open?'success':'warning')} ${t('status.camera')} ${cam.open?t('status.live'):t('status.offline')}`;const r=$('#ros-pill');if(r)r.innerHTML=`${dot(ros.running?'success':'warning')} ROS2 ${ros.running?t('status.rosConnected'):t('status.rosOffline')}`;const b=$('#board-pill');if(b)b.innerHTML=`${dot(cam.board_found?'success':'warning')} ${t('status.board')} ${cam.board_found?t('status.detected'):'—'}`;const rl=$('#runtime-label');if(rl){rl.textContent=backendStateLabel(state.backend);rl.previousElementSibling?.classList.toggle('success',state.backend==='ready')}const rs=$('#ros-sidebar');if(rs)rs.textContent=state.runtime?.rosSetup?`ROS · ${state.runtime.rosSetup.split('/').slice(-2,-1)[0]}`:t('status.rosNotDetected')}
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
    if(live)live.innerHTML=`${dot('success')} ${t('status.live')}`
    const size=$('#preview-size')
    if(size)size.textContent=`${frame.width||640} × ${frame.height||480}`
    const board=$('#board-live')
    if(board){board.textContent=frame.board_found?t('status.detected'):t('status.notDetected');board.style.color=frame.board_found?'var(--success)':'var(--warning)'}
  })
}

function updatePoseView(data){state.data.ros={...(state.data.ros||{}),running:true,pose:data};const pose=$('#pose-live');if(pose)pose.textContent=poseText();updateShell()}
function updateRuntimeView(){const rt=state.runtime||{};const installed=Boolean(rt.runtimeInstalled);const label=$('#runtime-health-label');if(label)label.textContent=installed?t('runtime.ready'):t('runtime.notInstalled');const pathEl=$('#runtime-health-path');if(pathEl)pathEl.textContent=rt.runtimePython||'~/.local/share/handeye-calibration/.venv/bin/python';const info=$('#runtime-info-box');if(info)info.textContent=`Ubuntu : ${rt.ubuntu||t('common.unknown')}
ROS    : ${rt.rosDistro||t('common.notDetected')}
Setup  : ${rt.rosSetup||t('common.notDetected')}
Python : ${rt.python||t('common.unknown')}
App    : ${rt.appVersion||'dev'}`;const log=$('#runtime-install-log');if(log){log.textContent=state.runtimeInstallLog.slice(-5000);log.classList.toggle('hidden',!state.runtimeInstallLog)}const install=$('#install-runtime');if(install)install.disabled=state.runtimeInstallState==='running';const installLabel=$('#install-runtime-label');if(installLabel)installLabel.textContent=state.runtimeInstallState==='running'?t('runtime.installing'):installed?t('runtime.repair'):t('runtime.install')}
function appendBackendLog(text){state.logs+=text||'';const log=$('#log-box');if(log){log.textContent=state.logs;log.scrollTop=log.scrollHeight}}
async function refreshState(){if(!api)return;try{state.data=await api.request('get_state');updateShell();renderPage(false)}catch(e){state.backend='error';updateShell()}}
function handleEvent(msg){const {event,data}=msg;if(event==='state'){state.data=data;updateShell()}else if(event==='preview'){updatePreviewFrame(data)}else if(event==='pose'){updatePoseView(data)}else if(event==='log'){appendBackendLog(data.text||'')}else if(event==='error'){toast('Backend',data?.message||t('error.unknown'),'danger')}else if(event==='tool_done'){if(data?.result)state.solveResult=data.result}}

async function boot(){document.documentElement.lang=state.language;shell();applyTheme(state.theme);renderPage(false);syncResponsiveShell();if(!responsiveListenerBound){responsiveListenerBound=true;window.addEventListener('resize',syncResponsiveShell,{passive:true})}if(!api){state.backend='unavailable';updateShell();toast(t('toast.bridgeMissing'),t('toast.startApp'),'warning');return}api.onEvent?.(handleEvent);api.onRuntime?.(m=>{state.backend=m.state||'unknown';state.runtime={...(state.runtime||{}),...m};updateShell();updateRuntimeView()});api.onRuntimeInstall?.(m=>{if(m.state==='starting')state.runtimeInstallState='running';if(m.state==='log')state.runtimeInstallLog+=(m.text||'');if(m.state==='done')state.runtimeInstallState='done';if(m.state==='error')state.runtimeInstallState='error';updateRuntimeView()});api.onStderr?.(t=>appendBackendLog('[backend] '+t));try{state.runtime=await api.runtimeInfo();const ping=await api.request('ping');state.backend=ping.pong?'ready':'error';state.data=await api.request('get_state')}catch(e){state.backend='error';toast(t('toast.backendStartFailed'),e.message,'danger')}updateShell();renderPage(false)}
boot()
