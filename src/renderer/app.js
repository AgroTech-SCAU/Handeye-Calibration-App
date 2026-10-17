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

// Every card defaults to collapsed except the camera preview, which defaults to expanded
// Preserve an explicit false value when a user chooses to collapse the preview
function loadExpandedCards(){
  try{
    const saved=JSON.parse(localStorage.getItem('handeye-expanded-cards')||'{}')
    if(!saved || typeof saved!=='object' || Array.isArray(saved)) return {}
    return Object.fromEntries(Object.entries(saved).filter(([key,expanded])=>key.includes('::') && (expanded===true || (key.endsWith('::camera-preview') && expanded===false))))
  }catch{return {}}
}

const state = {
  page:'connect', theme:localStorage.getItem('handeye-theme') || 'dark', language:initialLanguage, backend:'starting', runtime:null,
  data:{ config:{output_dir:'',camera_source:'ros',image_topic:'',camera_info_topic:'',camera_frame:'',robot_base_frame:'',robot_end_frame:'',camera_index:0,camera_width:640,camera_height:480,chessboard_cols:11,chessboard_rows:8,square_size_mm:15,board_type:'chessboard',charuco_squares_x:14,charuco_squares_y:9,charuco_marker_size_mm:15,charuco_dictionary:'DICT_5X5_100',charuco_min_corners:6,charuco_legacy_pattern:false,ros_input_type:'transform',pose_topic:'',joint_dof:5,joint_names:'',capture_topic:'',status_topic:'/handeye/status'}, camera:{open:false,board_found:false,width:640,height:480}, ros:{running:false,pose:null}, intrinsics:{count:0,exists:false}, handeye:{count:0,samples_exists:false}, validation:{reference_status:'unavailable',report:null,live_count:0,import_path:''}, output_dir:'' },
  arucoDictionaries:[], discoveredTopics:[], discoveredOnce:false, topicDetails:{}, autoFilled:new Set(), inspectingTopic:false, preview:'', logs:'', intrinsicQuality:'standard', handeyeQuality:'standard', sampleMode:'auto', manualType:'quaternion', angleUnit:'deg', solveMode:'robust',
  intrinsicResult:null, solveResult:null, validationMode:'offline', spatialServoMode:'manual', validationThresholds:{translation_rms_mm:5,rotation_rms_deg:1,projection_rms_px:4}, selectedSampleIds:new Set(), busyJob:null, toolCompletions:new Map(), runtimeInstallLog:'', runtimeInstallState:'idle', expandedCards:loadExpandedCards()
}

const ARUCO_DICTIONARIES=[
  ...['4X4','5X5','6X6','7X7'].flatMap(series=>['50','100','250','1000'].map(size=>`DICT_${series}_${size}`)),
  'DICT_ARUCO_ORIGINAL','DICT_APRILTAG_16h5','DICT_APRILTAG_25h9','DICT_APRILTAG_36h10','DICT_APRILTAG_36h11'
]

function createMockApi() {
  let mock = JSON.parse(JSON.stringify(state.data)); mock.mock=true; mock.aruco_dictionaries=ARUCO_DICTIONARIES
  const listeners=[]; const runtime=[]
  function emit(event,data){ listeners.forEach(fn=>fn({kind:'event',event,data})) }
  setTimeout(()=>runtime.forEach(fn=>fn({state:'ready',python:'sandbox-mock',rosSetup:'/opt/ros/humble/setup.bash'})),100)
  return {
    request: async (method,params={}) => {
      if(method==='get_state'||method==='ping') return method==='ping'?{pong:true,mock:true}:mock
      if(method==='set_config'){ Object.assign(mock.config,params); mock.output_dir=mock.config.output_dir; emit('state',mock); return mock }
      if(method==='update_board'){ const {reset_captures,...board}=params;Object.assign(mock.config,board);if(reset_captures){mock.intrinsics.count=0;mock.handeye.count=0}emit('state',mock);return mock }
      if(method==='discover_topics')return {topics:[]};
      if(method==='inspect_topic')return {received:false,metadata:{}};
      if(method==='connect_robot'){mock.ros.running=true;mock.ros.pose={values:[.412,-.083,.536,.012,.713,.008,.701],frame_id:mock.config.robot_base_frame||'base_link',child_frame_id:mock.config.robot_end_frame||'tool0',timestamp:Date.now()/1000};mock.camera.open=true;mock.camera.receiving=true;emit('pose',mock.ros.pose);emit('state',mock);return mock}
      if(method==='disconnect_robot'){mock.ros.running=false;mock.ros.pose=null;mock.camera.open=false;mock.camera.receiving=false;emit('state',mock);return mock}
      if(method==='import_camera_info'||method==='import_intrinsics')return {path:'/tmp/handeye/camera_intrinsics.yaml'};
      if(method==='export_matrix')return {path:'/tmp/handeye/handeye_transform.yaml'};
      if(method==='get_model_preview')return {name:'Demo Robot',root:'base_link',links:[{name:'base_link',visuals:[{layer:'visual',transform:[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],geometry:{type:'box',size:[.2,.2,.12]},vertices:[]} ]},{name:'tool0',visuals:[{layer:'visual',transform:[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],geometry:{type:'cylinder',radius:.018,length:.14},vertices:[]}]}],joints:[{name:'tool_fixed',parent:'base_link',child:'tool0',kind:'fixed',axis:[0,0,1]}],frames:{base_link:[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],tool0:[[1,0,0,0],[0,1,0,0],[0,0,1,.2],[0,0,0,1]]},model_pose:'illustrative',frames_note:'URDF reference pose',warnings:[],mesh_count:0};
      if(method==='set_validation_overlay')return {enabled:Boolean(params.enabled)};
      if(method==='freeze_validation'){mock.validation={reference_status:'ready',frames:['tool0','camera_optical_frame'],train_count:20,live_count:0,import_path:'',report:null};emit('state',mock);return {path:'/tmp/handeye/validation_reference.yaml'}}
      if(method==='import_validation'){mock.validation.import_path=params.path;return {path:params.path,count:7}}
      if(method==='capture_validation'){mock.validation.live_count++;return {count:mock.validation.live_count}}
      if(method==='clear_validation'){mock.validation.live_count=0;mock.validation.report=null;return {count:0}}
      if(method==='export_validation')return {path:'/tmp/handeye/validation_report.yaml'};
      if(method==='open_camera'){ mock.camera.open=true; mock.camera.board_found=true; emit('state',mock); return mock.camera }
      if(method==='close_camera'){ mock.camera.open=false; emit('state',mock); return mock.camera }
      if(method==='start_ros'){ mock.ros.running=true; mock.ros.pose={values:[.412,-.083,.536,.012,.713,.008,.701],frame_id:'arm_base_link',timestamp:Date.now()/1000}; emit('pose',mock.ros.pose); emit('state',mock); return mock.ros }
      if(method==='stop_ros'){ mock.ros.running=false; mock.ros.pose=null; emit('state',mock); return mock.ros }
      if(method==='capture_intrinsic'){ mock.intrinsics.count++; emit('intrinsic',{count:mock.intrinsics.count,sharpness:186,board_coverage_percent:23.4}); emit('state',mock); return {count:mock.intrinsics.count,sharpness:186,board_coverage_percent:23.4} }
      if(method==='solve_intrinsic'){ mock.intrinsics.exists=true; emit('state',mock); return {reprojection_error_px:.184,reprojection_error_median_px:.161,reprojection_error_max_px:.302,image_width:640,image_height:480} }
      if(method==='clear_intrinsic'){mock.intrinsics.count=0;emit('state',mock);return {count:0}}
      if(method==='capture_handeye'){mock.handeye.count++;emit('handeye',{count:mock.handeye.count,reprojection_error_px:.217,distance_mm:533,sharpness:171,pixels_per_square:24.9});emit('state',mock);return {count:mock.handeye.count,reprojection_error_px:.217,distance_mm:533,sharpness:171,pixels_per_square:24.9}}
      if(method==='save_samples'){mock.handeye.samples_exists=true;emit('state',mock);return {count:mock.handeye.count,path:'/tmp/handeye/samples.yaml'}}
      if(method==='import_samples'){mock.handeye.samples=Array.from({length:12},(_,i)=>({id:i+1,reprojection_error_px:0.18+i*.009,captured_at:'',quality_mode:'standard'}));mock.handeye.count=12;mock.handeye.quality_mode='standard';mock.handeye.samples_exists=true;emit('state',mock);return {count:12,quality_mode:'standard',path:'/tmp/handeye/samples.yaml'}}
      if(method==='delete_samples'){mock.handeye.samples=(mock.handeye.samples||[]).filter(x=>!params.ids.includes(x.id));mock.handeye.count=mock.handeye.samples.length;emit('state',mock);return {deleted:params.ids,count:mock.handeye.count}}
      if(method==='start_tool'){const id='mock_'+Date.now();setTimeout(()=>{const data={id,name:params.name,ok:true,cancelled:false,result:params.name==='solve'?{transform_matrix:[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]}:null};emit('tool_done',data)},1100);return {id,name:params.name}}
      if(method==='cancel_tool')return {cancelled:true}
      if(method==='clear_samples'){mock.handeye.count=0;emit('state',mock);return {count:0}}
      if(method==='run_tool'){const text=`[mock] ${params.name} completed\n`;emit('log',{text}); const result={translation_m:[.041,-.018,.087],quaternion_xyzw:[.003,.012,-.004,.9999],translation_rms_mm:2.31,rotation_rms_deg:.42,transform_matrix:[[1,0,0,.041],[0,1,0,-.018],[0,0,1,.087],[0,0,0,1]]}; return {ok:true,exit_code:0,log:text,result}}
      return {}
    },
    selectIntrinsics:async()=>'/tmp/handeye/intrinsics.yaml', selectRobotDescriptionFolder:async()=>'', selectRobotModel:async()=>'', selectSamples:async()=>'/tmp/handeye/samples.yaml', selectDirectory:async()=>'/home/user/handeye-output', runtimeInfo:async()=>({packaged:false,ubuntu:'22.04',rosDistro:'humble',rosSetup:'/opt/ros/humble/setup.bash',python:'sandbox-mock',runtimePython:'/home/user/.local/share/handeye-calibration/.venv/bin/python',runtimeInstalled:true}),
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
          ${nav('connect','plug',t('nav.connect'),'01')}${nav('intrinsics','scan',t('nav.intrinsics'),'02')}${nav('handeye','target',t('nav.handeye'),'03')}${nav('solve','flask',t('nav.solve'),'04')}${nav('validation','check',t('nav.validation'),'05')}
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
  if(state.page==='validation'&&state.validationMode==='spatial'&&state.spatialServoMode==='auto'&&state.data.servo?.busy){
    try{await api?.request('cancel_servo',{})}catch{}
    toast(t('servo.cancelRequested'),'','warning')
  }
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
  if(api?.request)void api.request('set_validation_overlay',{enabled:page==='validation'&&state.validationMode==='live',spatial:page==='validation'&&state.validationMode==='spatial'}).catch(()=>{})
  renderPage(false)
  const content=$('.content')
  if(content)content.scrollTop=0
  if(!prefersReducedMotion())animateCurrentPage()
}
function navigate(page){closeAppearanceMenu();void transitionToPage(page)}

function pageHead(kicker,title,desc,actions=''){return `<div class="page-head"><div class="page-head-main"><div class="page-kicker">${kicker}</div><h2 class="page-title">${title}</h2><p class="page-description">${desc}</p></div>${actions?`<div class="page-actions">${actions}</div>`:''}</div>`}
// Card identities must not depend on translated Chinese/English display titles.
const CARD_TITLE_KEYS = [
  'connect.projectSettings', 'connect.robotInterface',
  'intrinsics.boardTitle', 'intrinsics.captureTitle',
  'samples.manager', 'handeye.robotPose', 'handeye.collectionTitle',
  'solve.pipeline', 'solve.transform', 'validation.freezeTitle', 'solve.log',
  'spatial.modeTitle', 'spatial.step1', 'spatial.step2', 'spatial.step3', 'spatial.report',
  'validation.fixed', 'validation.datasetTitle', 'validation.liveTitle',
  'validation.offlineTitle', 'validation.runTitle', 'validation.reportTitle',
  'settings.appearance', 'settings.runtime', 'settings.language',
  'about.experience', 'about.core'
]
function cardKey(title,explicit=''){
  const key=explicit || CARD_TITLE_KEYS.find(candidate=>t(candidate)===String(title)) || String(title).trim()
  return `${state.page}::${encodeURIComponent(key)}`
}
function isCardExpanded(key){
  if(key.endsWith('::camera-preview'))return state.expandedCards[key]!==false
  return state.expandedCards[key]===true
}
function setCardExpanded(key,expanded){
  if(key.endsWith('::camera-preview'))state.expandedCards[key]=Boolean(expanded)
  else if(expanded)state.expandedCards[key]=true
  else delete state.expandedCards[key]
  localStorage.setItem('handeye-expanded-cards',JSON.stringify(state.expandedCards))
}
function cardToggle(key,expanded){
  // This button is the only interactive control in its heading, so clicks never bubble
  // to a second handler or operate on another card found by a document query.
  const action=expanded?(state.language==='zh-CN'?'收起':'Collapse'):(state.language==='zh-CN'?'展开':'Expand')
  return `data-card-toggle="${escapeHtml(key)}" aria-expanded="${expanded}" aria-label="${action}" title="${action}"`
}
function card(title,subtitle,ico,body,footer='',accent=false,options={}){
  const key=cardKey(title,options.key), collapsible=options.collapsible!==false
  const expanded=!collapsible||isCardExpanded(key)
  return `<section class="card ${expanded?'':'collapsed'}" data-card-key="${escapeHtml(key)}">
    <div class="card-head">
      <span class="card-icon ${accent?'accent':''}">${icon(ico)}</span>
      ${collapsible?`<button type="button" class="card-head-trigger" ${cardToggle(key,expanded)}><span class="card-summary"><span class="card-title">${title}</span>${subtitle?`<span class="card-subtitle">${subtitle}</span>`:''}</span><span class="card-toggle">${icon('chevron')}</span></button>`:`<div class="card-summary"><h3 class="card-title">${title}</h3>${subtitle?`<p class="card-subtitle">${subtitle}</p>`:''}</div>`}
    </div>
    <div class="card-body" ${expanded?'':'hidden'}>${body}</div>
    ${footer?`<div class="card-footer" ${expanded?'':'hidden'}>${footer}</div>`:''}
  </section>`
}
function field(label,id,value,type='text',help=''){return `<div class="field"><label for="${id}">${label}</label><input class="control" id="${id}" type="${type}" value="${escapeHtml(value)}"/>${help?`<div class="help">${help}</div>`:''}</div>`}
function btn(id,label,ico='play',kind='',extra=''){return `<button class="btn ${kind}" id="${id}" ${extra}>${icon(ico)}${label}</button>`}
function workflowHelp(key){return `<div class="workflow-help">${icon('info')}<span>${t(key)}</span></div>`}
function preview(){
  const cam=state.data.camera||{},key=cardKey('preview','camera-preview'),expanded=isCardExpanded(key)
  return `<section class="card preview-card ${expanded?'':'collapsed'}" data-card-key="${escapeHtml(key)}">
    <div class="preview-toolbar"><button class="preview-head-trigger" type="button" ${cardToggle(key,expanded)}>
      <b>${t('preview.title')}</b><span class="pill" id="preview-live-pill">${dot(cam.receiving?'success':'warning')} ${cam.receiving?t('status.live'):cam.open?t('status.waiting'):t('status.offline')}</span>
      <span class="meta" id="preview-size">${cam.width||640} × ${cam.height||480}</span><span class="card-toggle">${icon('chevron')}</span>
    </button></div>
    <div class="preview-surface" id="preview-surface" ${expanded?'':'hidden'}>${state.preview?`<img class="preview-image" src="data:image/jpeg;base64,${state.preview}"/>`:`<div class="preview-empty"><div class="ring">${icon('camera')}</div><b>${t('preview.waitingTitle')}</b><span>${t('preview.waitingDesc')}</span></div>`}</div>
  </section>`
}

function interfaceGuide(kind){
  const guides={
    transform:t('guide.transform'), pose:t('guide.pose'),tf:t('guide.tf'),joints:t('guide.joints')
  }
  return `<div class="interface-guide" id="robot-input-guide">${icon('info')}<span>${guides[kind]||guides.transform}</span></div>`
}
function modelPanel(){
  const m=state.data.robot_model||{},c=state.data.config||{}
  const has=Boolean(m.loaded)
  const modelCaption=has?`${escapeHtml(m.name||'robot')} · ${m.links?.length||0} Links · ${m.active_joints?.length||0} Active Joints`:t('guide.modelMissing')
  const all=has?(m.links||[]):[]
  return `<div class="interface-section model-section">
    <div class="interface-section-title">${icon('scan')}<b>${t('guide.modelTitle')}</b><span class="model-tag">${c.ros_input_type==='joints'?t('guide.required'):t('guide.optional')}</span></div>
    <div class="help">${t('guide.modelDesc')}</div>
    <div class="model-summary">${dot(has?'success':'warning')}<b>${modelCaption}</b></div>
    ${m.error?`<div class="help model-error">${escapeHtml(m.error)}</div>`:''}
    <div class="actions model-actions">${btn('import-robot-model',t('guide.importModel'),'folder','',state.data.ros?.running?'disabled':'')}${btn('import-description-folder',t('guide.importFolder'),'folder','',state.data.ros?.running?'disabled':'')}${btn('load-robot-description',t('guide.rosModel'),'scan','',state.data.ros?.running?'disabled':'')}
      ${has?btn('open-model-viewer',t('guide.view3D'),'target','primary'):''}${has?btn('clear-robot-model',t('guide.clearModel'),'trash','',state.data.ros?.running?'disabled':''):''}</div>
    ${has?`<div class="help">${t('guide.viewerHint')}</div><details class="model-link-details"><summary>${t('guide.linksShow')}</summary><div class="model-links">${all.map(x=>`<span>${escapeHtml(x)}</span>`).join('')}</div><div class="help">${t('guide.fixedOnly')}</div></details>`:''}
    <div class="help">${t('guide.modelNoTF')}</div>
  </div>`
}
function capabilitiesPanel(){
 const pose=state.data.ros?.pose,cam=state.data.camera||{},model=state.data.robot_model||{}
 const rows=[
  [t('guide.capCalibrate'),!!pose&&cam.receiving,t('guide.capCalibrateHint')],
  [t('guide.capGeom'),!!pose&&cam.receiving&&!!state.data.validation?.reference_status&&state.data.validation?.reference_status==='ready',t('guide.capGeomHint')],
  [t('guide.capTouch'),!!pose&&cam.receiving&&model.loaded&&state.data.validation?.reference_status==='ready',t('guide.capTouchHint')],
  [t('guide.capServo'),false,t('guide.capServoHint')]
 ]
 return `<details class="interface-advanced capability-guide"><summary>${t('guide.capabilities')}</summary><div class="capability-list">${rows.map(([name,ready,hint])=>`<div class="capability-row"><span>${dot(ready?'success':'warning')}<b>${name}</b></span><div class="help">${hint}</div></div>`).join('')}</div><div class="help">${t('guide.statusExplainer')}</div></details>`
}
const TOPIC_TYPES={
  image:'sensor_msgs/msg/Image',info:'sensor_msgs/msg/CameraInfo',
  pose:'geometry_msgs/msg/PoseStamped',transform:'geometry_msgs/msg/TransformStamped',
  joints:'sensor_msgs/msg/JointState',capture:'std_msgs/msg/Bool',status:'std_msgs/msg/String'
}
function availableTopics(kind){const type=TOPIC_TYPES[kind];return (state.discoveredTopics||[]).filter(v=>v.types?.includes(type)).map(v=>v.topic)}
function topicField(label,id,value,kind,optional=false){
  const topics=availableTopics(kind)
  if(kind==='status'&&!topics.includes('/handeye/status'))topics.unshift('/handeye/status')
  const missing=Boolean(value&&!topics.includes(value))
  const options=[`<option value="">${t(optional?'connect.optionalTopic':'connect.chooseTopic')}</option>`]
  if(missing)options.push(`<option value="${escapeHtml(value)}" disabled selected>${escapeHtml(value)} · ${t('connect.notDiscovered')}</option>`)
  for(const topic of topics)options.push(`<option value="${escapeHtml(topic)}" ${topic===value?'selected':''}>${escapeHtml(topic)}</option>`)
  const hint= !state.discoveredOnce?t('connect.searchFirst'):topics.length?`${topics.length} ${t('connect.topicCount')}`:t('connect.noMatchingTopics')
  return `<div class="field"><label for="${id}">${label}</label><select class="control topic-select" id="${id}" data-kind="${kind}">${options.join('')}</select><div class="topic-hint" data-hint-for="${id}">${hint}</div></div>`
}
function cameraMetaText(){const c=state.data.camera||{},d=state.topicDetails.image||state.topicDetails.info||{};const frame=c.frame_id||d.frame_id||state.data.config.camera_frame||'—';const w=c.width||d.width,h=c.height||d.height;return `${t('field.cameraFrame')}: ${escapeHtml(frame)}${w&&h?` · ${w} × ${h}`:''}${c.camera_info_ready?' · CameraInfo ✓':''}`}
function robotMetaText(){const p=state.data.ros?.pose||{},kind=state.data.config.ros_input_type,d=state.topicDetails[kind==='transform'?'transform':'pose']||{};const base=p.frame_id||d.frame_id||(kind==='transform'?'':state.data.config.robot_base_frame)||'—';const end=p.child_frame_id||d.child_frame_id||(kind==='transform'?'':state.data.config.robot_end_frame)||'—';return `${t('field.baseFrame')}: ${escapeHtml(base)} · ${t('field.endFrame')}: ${escapeHtml(end)}`}
function renderConnect(){
  const c=state.data.config,cam=state.data.camera||{},ros=state.data.ros||{}
  const isRos=c.camera_source!=='v4l2',kind=c.ros_input_type||'transform'
  const active=cam.open||ros.running,connected=cam.open&&ros.running
  return `<div class="page">${pageHead(t('connect.kicker'),t('connect.title'),t('connect.desc'))}${workflowHelp('guide.connectWorkflow')}
  <div class="grid three" style="margin-bottom:14px">
    <div class="metric"><div class="metric-label">${t('connect.metricCamera')}</div><div class="metric-value" id="connect-camera-state" style="color:${cam.receiving?'var(--success)':'var(--text-secondary)'}">${cam.receiving?t('status.connected'):cam.open?t('status.waiting'):t('status.offline')}</div><div class="metric-meta">${escapeHtml(isRos?c.image_topic:t('connect.device',{index:c.camera_index,width:c.camera_width,height:c.camera_height}))}</div></div>
    <div class="metric"><div class="metric-label">${t('connect.metricRobot')}</div><div class="metric-value" id="connect-robot-state" style="color:${ros.pose?'var(--success)':'var(--text-secondary)'}">${ros.pose?t('status.receiving'):ros.running?t('status.waiting'):t('status.offline')}</div><div class="metric-meta">${escapeHtml(kind==='tf'?(c.robot_base_frame+' → '+c.robot_end_frame):c.pose_topic)}</div></div>
    <div class="metric"><div class="metric-label">${t('connect.metricOutput')}</div><div class="metric-value">${state.data.handeye?.count||0}<small>${t('connect.samples')}</small></div><div class="metric-meta" id="connect-output-meta">${escapeHtml(c.output_dir||t('connect.notConfigured'))}</div></div>
  </div>
  <div class="grid preview-layout">${preview()}<div class="stack">
    ${card(t('connect.projectSettings'),t('connect.projectSettingsDesc'),'folder',`<div class="field"><label for="output-dir">${t('field.outputDir')}</label><div class="inline-control"><input class="control" id="output-dir" value="${escapeHtml(c.output_dir)}"/><button class="btn" id="browse-output">${icon('folder')}${t('action.browse')}</button></div></div>`)}
    ${card(t('connect.robotInterface'),t('connect.robotInterfaceDesc'),'plug',`
    <div class="interface-section"><div class="interface-section-title">${icon('camera')}<b>${t('connect.cameraInterface')}</b></div>
      <div class="form-row"><div class="field full"><label for="camera-source">${t('field.cameraSource')}</label><select class="control" id="camera-source"><option value="ros" ${isRos?'selected':''}>ROS2 Image</option><option value="v4l2" ${!isRos?'selected':''}>V4L2 / USB</option></select></div></div>
      <div class="form-row" id="camera-ros-fields" style="display:${isRos?'grid':'none'}">${topicField(t('field.imageTopic'),'image-topic',c.image_topic,'image')}${topicField('CameraInfo','camera-info-topic',c.camera_info_topic,'info',true)}</div>
      <div class="form-row" id="camera-local-fields" style="display:${!isRos?'grid':'none'}">${field(t('field.cameraIndex'),'camera-index',c.camera_index,'number')}${field(t('field.width'),'camera-width',c.camera_width,'number')}${field(t('field.height'),'camera-height',c.camera_height,'number')}</div>
      <div class="form-row"><div class="field full">${field(t('field.cameraFrame'),'camera-frame',c.camera_frame||'')}<div class="detected-meta" id="camera-detected">${cameraMetaText()}</div></div></div>
    </div>
    <div class="interface-section"><div class="interface-section-title">${icon('target')}<b>${t('connect.armInterface')}</b></div>
      <div class="form-row"><div class="field"><label for="ros-input-type">${t('field.inputType')}</label><select class="control" id="ros-input-type"><option value="transform" ${kind==='transform'?'selected':''}>TransformStamped · ${t('guide.recommended')}</option><option value="tf" ${kind==='tf'?'selected':''}>TF2</option><option value="pose" ${kind==='pose'?'selected':''}>PoseStamped</option><option value="joints" ${kind==='joints'?'selected':''}>JointState + URDF</option></select></div><div class="field" id="pose-topic-field" style="display:${kind==='tf'?'none':''}">${topicField(t('field.inputTopic'),'pose-topic',c.pose_topic,kind)}</div></div>
      ${interfaceGuide(kind)}
      <div class="form-row" id="robot-frame-fields">${kind==='transform'?
        `<div class="field"><label for="robot-base-frame">${t('field.baseFrame')} · ${t('connect.fromTransform')}</label><input class="control" id="robot-base-frame" readonly placeholder="${t('connect.waitingTransform')}" value="${escapeHtml(ros.pose?.frame_id||state.topicDetails.transform?.frame_id||'')}"/></div><div class="field"><label for="robot-end-frame">${t('field.endFrame')} · ${t('connect.fromTransform')}</label><input class="control" id="robot-end-frame" readonly placeholder="${t('connect.waitingTransform')}" value="${escapeHtml(ros.pose?.child_frame_id||state.topicDetails.transform?.child_frame_id||'')}"/></div>`:
        `${field(t('field.baseFrame'),'robot-base-frame',c.robot_base_frame||'')}${field(t('field.endFrame'),'robot-end-frame',c.robot_end_frame||'')}`}</div>
      <div class="detected-meta" id="robot-detected">${robotMetaText()}</div>
      <div class="form-row" id="joint-settings" style="display:${kind==='joints'?'grid':'none'}">${field(t('field.jointDof'),'joint-dof',c.joint_dof,'number')}${field(t('field.jointNames'),'joint-names',c.joint_names||'','text',t('guide.jointNamesHint'))}</div>
    </div>
    ${modelPanel()}
    <details class="interface-advanced"><summary>${t('servo.interfaceHeading')}</summary>
      <div class="help">${t('servo.robotContract')}</div>
      <div class="form-row" style="margin-top:12px">
        <div class="field"><label for="interface-motion-action">${t('servo.motionAction')}</label><input class="control" id="interface-motion-action" value="${escapeHtml(c.motion_action||'/move_action')}"/></div>
        <div class="field"><label for="interface-motion-group">${t('servo.motionGroup')}</label><input class="control" id="interface-motion-group" value="${escapeHtml(c.motion_group||'arm')}"/></div>
      </div>
      <div class="actions" style="margin-top:12px">${btn('servo-interface-save',t('servo.saveMotion'),'save')}${btn('servo-interface-check',t('servo.checkMotion'),'scan')}</div>
      <div class="help">${t('servo.depthHint')}</div>
    </details>
    ${capabilitiesPanel()}
    <details class="interface-advanced"><summary>${t('connect.advanced')}</summary><div class="form-row">${topicField(t('field.captureTopic'),'capture-topic',c.capture_topic||'','capture',true)}${topicField(t('field.statusTopic'),'status-topic',c.status_topic||'','status',true)}</div><div class="help">${t('connect.statusIsOutput')}</div></details>
    `,`<div class="actions connection-actions">${btn('discover-topics',t('action.discoverTopics'),'scan','')}${active?btn('disconnect-robot',t('action.disconnectRobot'),'square',''):btn('connect-robot',t('action.connectRobot'),'plug','primary')}</div><div class="connection-note" id="connection-message">${connected?t('connect.connectedHint'):t('connect.connectionHint')}</div>`,true)}
  </div></div></div>`
}

const BOARD_KEYS=['board_type','chessboard_cols','chessboard_rows','square_size_mm','charuco_squares_x','charuco_squares_y','charuco_marker_size_mm','charuco_dictionary','charuco_min_corners','charuco_legacy_pattern']
function arucoDictionaryField(value){
  const known=state.data.aruco_dictionaries||ARUCO_DICTIONARIES
  const options=known.includes(value)?known:[value,...known]
  return `<div class="field"><label for="charuco-dictionary">${t('board.dictionary')}</label><select class="control" id="charuco-dictionary">${options.map(name=>`<option value="${escapeHtml(name)}" ${name===value?'selected':''}>${escapeHtml(name)}</option>`).join('')}</select></div>`
}
function boardSummary(){const c=state.data.config||{};const shape=c.board_type==='charuco'?`${c.charuco_squares_x} × ${c.charuco_squares_y}`:`${c.chessboard_cols} × ${c.chessboard_rows}`;return `${c.board_type==='charuco'?'CharUco':t('board.chessboard')} · ${shape} · ${c.square_size_mm} mm`}
function boardEditor(){return `<details class="board-inline-editor"><summary><span class="board-inline-label">${icon('scan')}<strong>${t('intrinsics.boardTitle')}</strong></span><span class="board-inline-summary">${escapeHtml(boardSummary())}</span></summary><div class="board-inline-content">${boardFields()}<div class="actions" style="margin-top:12px">${btn('save-board',t('intrinsics.saveBoard'),'refresh-cw','primary')}</div></div></details>`}
function boardFields(){
  const c=state.data.config;const isCharuco=c.board_type==='charuco'
  return `<div class="form-row"><div class="field"><label for="board-type">${t('board.type')}</label><select class="control" id="board-type"><option value="chessboard" ${!isCharuco?'selected':''}>${t('board.chessboard')}</option><option value="charuco" ${isCharuco?'selected':''}>CharUco</option></select></div>${field(t('board.square'),'square-mm',c.square_size_mm,'number')}</div>
  <div class="form-row" id="board-chess-fields" style="display:${isCharuco?'none':'grid'}">${field(t('board.cols'),'board-cols',c.chessboard_cols,'number')}${field(t('board.rows'),'board-rows',c.chessboard_rows,'number')}</div>
  <div id="board-charuco-fields" style="display:${isCharuco?'block':'none'}"><div class="form-row three">${field(t('board.squaresX'),'charuco-x',c.charuco_squares_x??14,'number')}${field(t('board.squaresY'),'charuco-y',c.charuco_squares_y??9,'number')}${field(t('board.marker'),'charuco-marker',c.charuco_marker_size_mm??15,'number')}</div><div class="form-row">${arucoDictionaryField(c.charuco_dictionary??'DICT_5X5_100')}${field(t('board.minCorners'),'charuco-min',c.charuco_min_corners??6,'number')}</div><div class="field"><label><input id="charuco-legacy" type="checkbox" ${c.charuco_legacy_pattern?'checked':''}> ${t('board.patternCompat')}</label></div></div><div class="help">${t('board.sessionHelp')}</div>`
}
function segmentedControl(id,current,options,extraClass='amber'){
  return `<div class="segmented ${extraClass}" id="${id}"><span class="segmented-indicator" aria-hidden="true"></span>${options.map(([value,label])=>`<button data-value="${value}" class="${current===value?'active':''}">${label}</button>`).join('')}</div>`
}
function qualitySegment(id,current){return segmentedControl(id,current,[['standard',t('quality.standard')],['strict',t('quality.strict')],['minimal',t('quality.minimal')]])}
function renderIntrinsics(){const x=state.data.intrinsics||{},cam=state.data.camera;const target=state.intrinsicQuality==='strict'?15:state.intrinsicQuality==='minimal'?3:10;const pct=Math.min(100,(x.count||0)/target*100);return `<div class="page">${pageHead(t('intrinsics.kicker'),t('intrinsics.title'),t('intrinsics.desc'),btn('go-handeye',t('intrinsics.next'),'chevron'))}${workflowHelp('guide.intrinsicsWorkflow')}
<div class="grid preview-layout">${preview()}<div class="stack">${card(t('intrinsics.boardTitle'),t('intrinsics.boardDesc'),'scan',boardFields(),`${btn('save-board',t('intrinsics.saveBoard'),'refresh-cw','primary')}`)}
${card(t('intrinsics.captureTitle'),t('intrinsics.captureDesc'),'camera',`<div class="progress-label"><span>${t('intrinsics.captured',{count:x.count||0})}</span><span id="intrinsic-target">${t('intrinsics.minimum',{count:target})}</span></div><div class="progress-track"><div class="progress-bar" id="intrinsic-progress" style="width:${pct}%"></div></div><div style="margin-top:14px"><div class="field"><label>${t('intrinsics.quality')}</label>${qualitySegment('intrinsic-quality',state.intrinsicQuality)}</div></div><div class="grid two" style="margin-top:13px"><div class="metric"><div class="metric-label">${t('intrinsics.chessboard')}</div><div class="metric-value" id="board-live" style="font-size:17.25px;color:${cam.board_found?'var(--success)':'var(--warning)'}">${cam.board_found?t('status.detected'):t('status.notDetected')}</div></div><div class="metric"><div class="metric-label">${t('intrinsics.file')}</div><div class="metric-value" style="font-size:17.25px;color:${x.exists?'var(--success)':'var(--text-secondary)'}">${x.exists?t('status.ready'):t('status.pending')}</div></div></div>`,`<div class="actions">${btn('capture-intrinsic',t('intrinsics.capture'),'camera','primary large',cam.open?'':'disabled')}${btn('solve-intrinsic',t('intrinsics.solveSave'),'flask','',x.count>=target?'':'disabled')}${btn('clear-intrinsic',t('action.clear'),'trash','danger')}${btn('import-camera-info',t('action.useCameraInfo'),'plug')}${btn('import-intrinsics',t('action.importIntrinsics'),'folder')}</div>`,true)}
${state.intrinsicResult?`<div class="callout">${icon('check')}<div><b>${t('intrinsics.saved')}</b><br>RMS ${n(state.intrinsicResult.reprojection_error_px,4)} px · Median ${n(state.intrinsicResult.reprojection_error_median_px,4)} px · Max ${n(state.intrinsicResult.reprojection_error_max_px,4)} px</div></div>`:''}</div></div></div>`}

function poseText(){const p=state.data.ros?.pose;if(!p)return t('robot.waitingData');const v=p.values||[];return `frame : ${p.frame_id||'-'} → ${p.child_frame_id||state.data.config.robot_end_frame||'-'}\nxyz   : ${n(v[0],5)}  ${n(v[1],5)}  ${n(v[2],5)} m\nxyzw  : ${n(v[3],5)}  ${n(v[4],5)}  ${n(v[5],5)}  ${n(v[6],5)}`}
function manualFields(){let labels=state.manualType==='quaternion'?['x','y','z','qx','qy','qz','qw']:state.manualType==='rpy'?['x','y','z','roll','pitch','yaw']:Array.from({length:Number(state.data.config.joint_dof)||5},(_,i)=>`q${i+1}`);return `<div class="form-row three">${labels.map((l,i)=>field(l,`manual-${i}`,state.manualType==='quaternion'&&i===6?1:0,'number')).join('')}</div>`}
function manualInputPanel(){return `<div class="manual-input-panel ${state.sampleMode==='manual'?'open':''}" id="manual-input-panel"><div class="manual-input-inner"><div class="divider"></div><div class="form-row"><div class="field"><label>${t('manual.type')}</label><select class="control" id="manual-type"><option value="quaternion" ${state.manualType==='quaternion'?'selected':''}>${t('manual.poseQuaternion')}</option><option value="rpy" ${state.manualType==='rpy'?'selected':''}>${t('manual.poseRpy')}</option><option value="joints" ${state.manualType==='joints'?'selected':''}>${t('manual.jointAngles')}</option></select></div><div class="field"><label>${t('manual.angleUnit')}</label><select class="control" id="angle-unit"><option value="deg" ${state.angleUnit==='deg'?'selected':''}>deg</option><option value="rad" ${state.angleUnit==='rad'?'selected':''}>rad</option></select></div></div><div id="manual-fields" style="margin-top:11px">${manualFields()}</div></div></div>`}
const HAND_EYE_TARGETS = {minimal:8, standard:20, strict:30}
function qualityTarget(){return HAND_EYE_TARGETS[state.handeyeQuality] || 20}
function sampleManager(){
  const items=state.data.handeye?.samples||[]
  const selection=state.selectedSampleIds
  const rows=items.map(s=>`<label class="sample-row"><input type="checkbox" class="sample-check" value="${s.id}" ${selection.has(s.id)?'checked':''}><span class="sample-number">#${s.id}</span><span class="sample-error">${s.reprojection_error_px!=null&&Number.isFinite(Number(s.reprojection_error_px))?n(s.reprojection_error_px,3)+' px':'—'}</span><span class="sample-date">${escapeHtml(s.captured_at||'')}</span></label>`).join('')
  return card(t('samples.manager'),t('samples.managerHint'),'scan',`<div class="sample-manager-top"><span>${t('samples.count',{count:items.length})}</span><button class="btn small" id="select-all-samples">${t('samples.selectAll')}</button></div><div class="sample-list">${rows||`<div class="help">${t('samples.empty')}</div>`}</div>`, `<div class="actions">${state.page==='solve'?btn('import-samples',t('samples.import'),'folder'):''}${btn('delete-selected-samples',t('samples.deleteSelected'),'trash','danger',selection.size?'':'disabled')}</div>`,true)
}
function handeyeQualitySegment(){
  const count=state.data.handeye?.count||0
  const html=qualitySegment('handeye-quality',state.handeyeQuality)
  return count ? html.replaceAll('<button ', '<button disabled title="'+escapeHtml(t('samples.qualityLocked'))+'" ') : html
}

function renderHandeye(){const h=state.data.handeye||{},ros=state.data.ros||{};const target=qualityTarget(),pct=Math.min(100,(h.count||0)/target*100);return `<div class="page">${pageHead(t('handeye.kicker'),t('handeye.title'),t('handeye.desc'),btn('go-solve',t('handeye.next'),'chevron'))}${workflowHelp('guide.handeyeWorkflow')}
<div class="grid preview-layout">${preview()}<div class="stack">${card(t('handeye.robotPose'),ros.running?t('handeye.robotAutoReceiving'):t('handeye.robotChooseSource'),'target',`<div class="pose-box" id="pose-live">${escapeHtml(poseText())}</div><div style="margin-top:12px"><div class="field"><label>${t('handeye.source')}</label>${segmentedControl('sample-mode',state.sampleMode,[['auto',t('handeye.auto')],['manual',t('handeye.manual')]])}</div></div>${manualInputPanel()}<div class="help">${t('guide.samplePoseHint')}</div>`)}
${boardEditor()}
${card(t('handeye.collectionTitle'),t('handeye.collectionDesc'),'scan',`<div class="progress-label"><span>${t('handeye.captured',{count:h.count||0})}</span><span id="handeye-recommended">${t('handeye.recommended',{count:target})}</span></div><div class="progress-track"><div class="progress-bar" id="handeye-progress" style="width:${pct}%"></div></div><div style="margin-top:14px"><div class="field"><label>${t('intrinsics.quality')}</label>${handeyeQualitySegment()}<div class="help">${t('guide.qualityHint')}</div></div></div><div class="grid three" style="margin-top:13px"><div class="metric"><div class="metric-label">${t('handeye.samples')}</div><div class="metric-value">${h.count||0}</div></div><div class="metric"><div class="metric-label">${t('handeye.camera')}</div><div class="metric-value" style="font-size:16.1px;color:${state.data.camera?.open?'var(--success)':'var(--warning)'}">${state.data.camera?.open?t('status.ready'):t('status.offline')}</div></div><div class="metric"><div class="metric-label">${t('handeye.robot')}</div><div class="metric-value" id="robot-source-status" style="font-size:16.1px;color:${state.sampleMode==='manual'||ros.pose?'var(--success)':'var(--warning)'}">${state.sampleMode==='manual'?t('status.manual'):ros.pose?t('status.ready'):t('status.waiting')}</div></div></div>`,`<div class="actions">${btn('capture-handeye',t('handeye.capture'),'target','primary large')}${btn('save-samples',t('handeye.save'),'save')}${btn('import-samples',t('samples.import'),'folder')}${btn('clear-samples',t('action.clear'),'trash','danger')}</div>`,true)}${sampleManager()}</div></div></div>`}

function matrixHtml(result){const m=result?.transform_matrix;if(!Array.isArray(m)||m.length!==4)return `<div class="pose-box">${t('solve.waitingResult')}</div>`;return `<div class="result-matrix">${m.flat().map(v=>`<span>${n(v,6)}</span>`).join('')}</div>`}
function renderSolve(){const h=state.data.handeye||{};const r=state.solveResult;return `<div class="page">${pageHead(t('solve.kicker'),t('solve.title'),t('solve.desc'))}${workflowHelp('guide.solveWorkflow')}
<div class="grid two" style="margin-bottom:14px"><div class="metric"><div class="metric-label">samples.yaml</div><div class="metric-value" style="font-size:17.25px;color:${h.samples_exists?'var(--success)':'var(--warning)'}">${h.samples_exists?t('status.ready'):t('status.notSaved')}</div><div class="metric-meta">${escapeHtml(h.samples_path||'')}</div></div><div class="metric"><div class="metric-label">${t('solve.result')}</div><div class="metric-value" style="font-size:17.25px;color:${r?'var(--success)':'var(--text-secondary)'}">${r?t('status.solved'):t('status.waiting')}</div><div class="metric-meta">samples_result.yaml</div></div></div>
<div class="grid preview-layout"><div class="stack">${card(t('solve.pipeline'),t('solve.pipelineDesc'),'flask',`<div class="field"><label>${t('solve.mode')}</label>${segmentedControl('solve-mode',state.solveMode,[['robust',t('solve.robust')],['minimal',t('solve.opencv')],['ba',t('solve.ba')]])}<div class="help">${t('guide.solveModeHint')}</div></div><div class="divider"></div><div class="actions">${btn('run-diagnose',t('action.diagnose'),'scan')}${btn('run-solve',t('action.solve'),'play','primary')}</div>`)}
${card(t('solve.transform'),t('solve.transformDesc'),'target',`${r?`<div class="help">${escapeHtml(r.parent_frame||'?')} → ${escapeHtml(r.child_frame||'?')} · m</div>`:''}${matrixHtml(r)}${r?`<div class="grid two" style="margin-top:12px"><div class="metric"><div class="metric-label">${t('solve.translationRms')}</div><div class="metric-value">${n(r.translation_rms_mm,3)}<small>mm</small></div></div><div class="metric"><div class="metric-label">${t('solve.rotationRms')}</div><div class="metric-value">${n(r.rotation_rms_deg,3)}<small>deg</small></div></div></div>`:''}`)}</div>
${r?`<div class="actions" style="margin:10px 0">${btn('copy-matrix',t('action.copyMatrix'),'save')}${btn('export-matrix',t('action.exportMatrix'),'folder')}</div>`:''}
${card(t('validation.freezeTitle'),t('validation.freezeHint'),'check',`<div class="actions">${btn('freeze-validation',t('validation.freeze'),'check','primary')}${btn('go-validation',t('validation.goto'),'arrow-right')}</div>`)}
${sampleManager()}
${card(t('solve.log'),t('solve.logDesc'),'terminal',`<div class="log-box" id="log-box">${escapeHtml(state.logs||t('solve.noOutput'))}</div>`,`<span style="font-size:11.5px;color:var(--text-dim)">${t('solve.coreProtected')}</span>`)}</div></div>`}


function validationTrend(report){
  const rows=report?.samples||[]
  if(!rows.length)return `<div class="validation-empty">${t('validation.noReport')}</div>`
  const width=680,height=210,left=46,right=18,top=19,bottom=31
  const series=[['translation_error_mm','#f59e0b',t('validation.translation')],['rotation_error_deg','#38bdf8',t('validation.rotation')]]
  const maximum=Math.max(1,...rows.flatMap(r=>[Number(r.translation_error_mm)||0,Number(r.rotation_error_deg)||0]))*1.15
  const x=i=>left+(width-left-right)*i/Math.max(1,rows.length-1)
  const y=v=>height-bottom-(height-top-bottom)*Math.max(0,Number(v)||0)/maximum
  const lines=series.map(([key,color])=>`<polyline fill="none" stroke="${color}" stroke-width="2.4" stroke-linejoin="round" points="${rows.map((r,i)=>`${x(i)},${y(r[key])}`).join(' ')}"/>`)
  const points=series.flatMap(([key,color])=>rows.map((r,i)=>`<circle cx="${x(i)}" cy="${y(r[key])}" r="3" fill="${color}"><title>ID ${escapeHtml(r.id)} · ${n(r[key],3)}</title></circle>`))
  const grid=[0,.5,1].map(f=>{const yy=y(f*maximum);return `<line x1="${left}" x2="${width-right}" y1="${yy}" y2="${yy}" stroke="currentColor" opacity=".12"/><text x="${left-8}" y="${yy+4}" text-anchor="end" fill="currentColor" opacity=".6" font-size="11">${n(f*maximum,1)}</text>`}).join('')
  return `<div class="validation-trend"><svg role="img" aria-label="${escapeHtml(t('validation.chart'))}" viewBox="0 0 ${width} ${height}" width="100%">${grid}${lines.join('')}${points.join('')}<text x="${width-right}" y="${height-7}" text-anchor="end" fill="currentColor" opacity=".65" font-size="11">${escapeHtml(t('validation.sampleAxis'))}</text></svg><div class="validation-legend"><span style="--series:#f59e0b">${t('validation.translation')} · mm</span><span style="--series:#38bdf8">${t('validation.rotation')} · °</span></div></div>`
}
function validationMetric(label,value,unit){return `<div class="metric"><div class="metric-label">${label}</div><div class="metric-value">${Number.isFinite(Number(value))?n(value,3):'—'} <small>${unit}</small></div></div>`}
function validationReport(report){
  if(!report)return `<div class="validation-empty">${t('validation.noReport')}</div>`
  const m=report.metrics||{},rows=report.samples||[]
  const status=report.status==='pass'?t('validation.pass'):report.status==='fail'?t('validation.fail'):t('validation.insufficient')
  const badgeColor=report.status==='pass'?'var(--success)':report.status==='fail'?'var(--danger)':'var(--warning)'
  const metrics=`<div class="grid three validation-metrics">${validationMetric(t('validation.transRms'),m.translation_mm_rms,'mm')}${validationMetric(t('validation.rotRms'),m.rotation_deg_rms,'°')}${validationMetric(t('validation.projRms'),m.projection_px_rms,'px')}${validationMetric(t('validation.transP95'),m.translation_mm_p95,'mm')}${validationMetric(t('validation.rotP95'),m.rotation_deg_p95,'°')}${validationMetric(t('validation.projP95'),m.projection_px_p95,'px')}</div>`
  const list=rows.map(r=>`<tr><td>#${escapeHtml(r.id)}</td><td>${n(r.translation_error_mm,3)}</td><td>${n(r.rotation_error_deg,3)}</td><td>${n(r.prediction_reprojection_rms_px,3)}</td></tr>`).join('')
  return `<div class="validation-status" style="--status-color:${badgeColor}"><b>${status}</b><span>${t('validation.reportCount',{count:rows.length})}</span></div>${metrics}${validationTrend(report)}<div class="validation-table-wrap"><table class="validation-table"><thead><tr><th>ID</th><th>${t('validation.translation')} mm</th><th>${t('validation.rotation')} °</th><th>${t('validation.projection')} px</th></tr></thead><tbody>${list}</tbody></table></div><p class="help">${t('validation.limitNote')}</p>`
}
function renderSpatialValidation(){
 if(state.spatialServoMode==='auto')return renderRgbdServoValidation()
 const v=state.data.validation||{},sp=state.data.spatial||{},ref=sp.contact,m=state.data.robot_model||{}
 const ready=v.reference_status==='ready',links=m.fixed_links?.length?m.fixed_links:(m.links||[]),preferred=state.spatialLink|| (links.includes('tip')?'tip':links.includes('tool0')?'tool0':links[0]||'')
 if(!links.includes(preferred))state.spatialLink=preferred
 const errors=(sp.measurements||[])
 const rows=errors.map(r=>`<tr><td>#${r.id}</td><td>${n(r.error_xyz_mm?.[0],2)}</td><td>${n(r.error_xyz_mm?.[1],2)}</td><td>${n(r.error_xyz_mm?.[2],2)}</td><td>${n(r.error_mm,2)}</td></tr>`).join('')
 return `<div class="page">${pageHead(t('validation.kicker'),t('spatial.title'),t('spatial.subtitle'))}
  <div class="validation-mode">${segmentedControl('spatial-submode',state.spatialServoMode,[['manual',t('servo.manual')],['auto',t('servo.automatic')]])}</div>
  ${card(t('spatial.modeTitle'),t('spatial.modeIntro'),'target',`<div class="interface-guide">${icon('info')}<span>${t('spatial.manualOnly')}</span></div><div class="help">${t('spatial.servoRequirements')}</div>`)}
  <div class="validation-mode">${segmentedControl('validation-mode','spatial',[['offline',t('validation.offline')],['live',t('validation.live')],['spatial',t('spatial.mode')]])}</div>
  <div class="grid preview-layout">${preview()}<div class="stack">
  ${card(t('spatial.step1'),t('spatial.step1Desc'),'check',`<div class="help">${ready?t('validation.ready'):t('spatial.needFreeze')}</div><div class="help">${m.loaded?`${escapeHtml(m.name)} · ${m.links.length} Links`:t('guide.modelMissing')}</div>`,`<div class="actions">${btn('spatial-freeze',t('validation.freeze'),'check')}${btn('spatial-connect',t('spatial.gotoConnect'),'plug')}</div>`)}
  ${card(t('spatial.step2'),t('spatial.step2Desc'),'target',`<div class="field"><label for="spatial-tool-link">${t('spatial.tool')}</label><select class="control" id="spatial-tool-link">${links.map(link=>`<option value="${escapeHtml(link)}" ${link===preferred?'selected':''}>${escapeHtml(link)}</option>`).join('')}</select><div class="help">${t('spatial.toolHint')}</div></div><div class="field"><label for="spatial-corner-id">${t('spatial.corner')}</label><input class="control" type="number" id="spatial-corner-id" min="0" step="1" value="${state.spatialCorner??0}"/><div class="help">${t('spatial.cornerHint')}</div></div>
  <div class="pose-box" style="margin-top:10px">${ref?`${t('spatial.point')}: ${ref.point_m.map(v=>n(v,5)).join('  ')} m\n${escapeHtml(ref.link)} · ID ${ref.corner_id}`:t('spatial.noContact')}</div>`,`<div class="actions">${btn('spatial-resolve',t('spatial.previewLink'),'scan','',m.loaded?'':'disabled')}${btn('spatial-contact',t('spatial.recordContact'),'target','primary',ready&&m.loaded?'':'disabled')}</div>`,true)}
  ${card(t('spatial.step3'),t('spatial.step3Desc'),'camera',`<div class="help">${t('spatial.measureHint')}</div><div class="grid two" style="margin-top:12px">${validationMetric(t('spatial.rms'),sp.rms_mm,'mm')}${validationMetric(t('spatial.max'),sp.max_mm,'mm')}</div><div class="help">${t('spatial.count',{count:sp.count||0})}</div>`,`<div class="actions">${btn('spatial-measure',t('spatial.measure'),'scan','primary',ref?'':'disabled')}${btn('spatial-clear',t('spatial.clear'),'trash','danger',ref?'':'disabled')}</div>`,true)}
  </div></div>
  ${card(t('spatial.report'),t('spatial.reportDesc'),'flask',`<div class="validation-table-wrap"><table class="validation-table"><thead><tr><th>ID</th><th>X mm</th><th>Y mm</th><th>Z mm</th><th>3D mm</th></tr></thead><tbody>${rows||`<tr><td colspan="5">${t('spatial.noData')}</td></tr>`}</tbody></table></div><div class="help">${t('spatial.limit')}</div>`)}
 </div>`
}

function renderRgbdServoValidation(){
 const cfg=state.data.config||{}, servo=state.data.servo||{},target=servo.target,model=state.data.robot_model||{},links=model.fixed_links?.length?model.fixed_links:(model.links||[])
 const preferred=state.spatialLink&&links.includes(state.spatialLink)?state.spatialLink:(links.includes('tip')?'tip':links.includes('tool0')?'tool0':links[0]||'')
 const status=servo.phase||'idle',working=servo.busy||['moving','observing','settling','cancelling'].includes(status)
 const history=(servo.history||[]).slice(-12).reverse().map(row=>`<tr><td>${row.step}</td><td>${n(row.distance_mm,2)} mm</td><td>${(row.target_base_m||[]).map(x=>n(x,3)).join(', ')}</td></tr>`).join('')
 return `<div class="page">${pageHead(t('validation.kicker'),t('spatial.title'),t('servo.pageHint'))}
 <div class="validation-mode">${segmentedControl('spatial-submode',state.spatialServoMode,[['manual',t('servo.manual')],['auto',t('servo.automatic')]])}</div>
 ${workflowHelp('servo.workflow')}
 <div class="grid preview-layout">${preview()}<div class="stack">
 ${card(t('servo.requirements'),t('servo.requirementsHint'),'info',`<div class="help">${t('servo.robotContract')}</div><div class="help">${t('servo.safety')}</div><div class="help">${t('servo.depthHint')}</div>`)}
 ${card(t('servo.configure'),t('servo.configureHint'),'plug',`
 <div class="field"><label>${t('servo.depthTopic')}</label><input class="control" id="servo-depth-topic" value="${escapeHtml(cfg.aligned_depth_topic||'')}" placeholder="/camera/aligned_depth_to_color/image_raw"/></div>
 <div class="help">${servo.depth_ready?t('servo.depthReady'):t('servo.depthMissing')}</div>
 <div class="form-row"><div class="field"><label>${t('servo.motionAction')}</label><input class="control" id="servo-motion-action" value="${escapeHtml(cfg.motion_action||'/move_action')}"/></div><div class="field"><label>${t('servo.motionGroup')}</label><input class="control" id="servo-motion-group" value="${escapeHtml(cfg.motion_group||'arm')}"/></div></div>
 <div class="help">${t('servo.motionHelp')}</div>`, `<div class="actions">${btn('servo-connect-depth',t('servo.connectDepth'),'camera','primary',working?'disabled':'')}${btn('servo-save-motion',t('servo.saveMotion'),'save','',working?'disabled':'')}${btn('servo-check-motion',t('servo.checkMotion'),'scan','',working?'disabled':'')}</div>`,true)}
 ${card(t('servo.target'),t('servo.targetHint'),'target',`
 <div class="field"><label>${t('servo.targetLink')}</label><select class="control" id="servo-target-link">${links.map(x=>`<option value="${escapeHtml(x)}" ${x===preferred?'selected':''}>${escapeHtml(x)}</option>`).join('')}</select></div>
 <div class="pose-box" id="servo-target-info">${target?`${t('servo.targetXYZ')} ${target.point_base_m.map(x=>n(x,4)).join(' / ')} m\nRGB (${n(target.u,0)}, ${n(target.v,0)}) · ${n(target.depth_m,3)} m`:t('servo.noTarget')}</div>
 <div class="help">${t('servo.pickHint')}</div>
 <div class="help">${t('servo.orientation')}</div>
 `,`<div class="actions">${btn('servo-clear-selection',t('servo.clearSelection'),'trash','',working?'disabled':'')}</div>`)}
 ${card(t('servo.execute'),t('servo.executeHint'),'play',`
 <div class="form-row three">${field(t('servo.step'),'servo-step',15,'number')}${field(t('servo.clearance'),'servo-clearance',35,'number')}${field(t('servo.maxSteps'),'servo-max-steps',8,'number')}</div>
 <label class="servo-safety-label"><input type="checkbox" id="servo-safety-confirm" ${working?'disabled':''}> ${t('servo.acknowledge')}</label>
 <div class="servo-run-status" id="servo-run-status"><b>${escapeHtml(status)}</b><span>${escapeHtml(servo.message||'')}</span></div>
 <div class="help">${t('servo.clearanceHint')}</div>
 `,`<div class="actions">${btn('servo-start',t('servo.start'),'play','primary',target&&!working?'':'disabled')}${btn('servo-cancel',t('servo.cancel'),'square','danger',working?'':'disabled')}</div>`,true)}
 </div></div>
 ${card(t('servo.results'),t('servo.resultsHint'),'flask',`<div class="validation-table-wrap"><table class="validation-table"><thead><tr><th>#</th><th>${t('servo.remaining')}</th><th>${t('servo.position')}</th></tr></thead><tbody id="servo-history">${history||`<tr><td colspan="3">${t('servo.noHistory')}</td></tr>`}</tbody></table></div><div class="help">${t('servo.notAbsolute')}</div>`)}
 </div>`
}

function renderValidation(){
  const v=state.data.validation||{},mode=state.validationMode,ready=v.reference_status==='ready', report=v.reports?.[mode]||(mode==='live'?v.live_preview:null)
  if(mode==='spatial')return renderSpatialValidation()
  const online=mode==='live'
  const frames=(v.frames||[]).join(' → ')||'—'
  const source=online?(v.live_samples_path||'validation_samples.yaml'):(v.import_path||t('validation.chooseDataset'))
  return `<div class="page">${pageHead(t('validation.kicker'),t('validation.title'),t('validation.desc'))}${workflowHelp('guide.validationWorkflow')}
  ${card(t('validation.fixed'),t('validation.fixedHint'),'check',`<div class="validation-fixed"><div><span class="validation-status-label ${ready?'valid':''}">${ready?t('validation.ready'):v.reference_status==='stale'?t('validation.stale'):t('validation.missing')}</span><div class="help">${escapeHtml(frames)}</div><div class="help">${t('validation.trainCount',{count:v.train_count||0})}</div></div><div class="actions">${btn('validation-freeze',t('validation.freeze'),'check')}</div></div>`)}
  <div class="validation-mode">${segmentedControl('validation-mode',mode,[['offline',t('validation.offline')],['live',t('validation.live')],['spatial',t('spatial.mode')]])}</div>
  <div class="grid preview-layout">${online?preview():card(t('validation.datasetTitle'),t('validation.datasetHint'),'folder',`<div class="pose-box validation-path">${escapeHtml(source)}</div><div class="help">${t('validation.independence')}</div>`,`<div class="actions">${btn('validation-import',t('validation.import'),'folder','primary')}</div>`,true)}
  <div class="stack">${online?card(t('validation.liveTitle'),t('validation.liveHint'),'camera',`<div class="metric"><div class="metric-label">${t('validation.liveCount')}</div><div class="metric-value">${v.live_count||0}</div></div><div class="validation-legend"><span style="--series:#22c55e">${t('validation.observed')}</span><span style="--series:#f97316">${t('validation.predicted')}</span></div><div class="help">${t('validation.liveSafety')}</div>`,`<div class="actions">${btn('validation-capture',t('validation.capture'),'target','primary',ready?'':'disabled')}${btn('validation-clear',t('validation.clear'),'trash','danger')}</div>`,true):card(t('validation.offlineTitle'),t('validation.offlineHint'),'scan',`<div class="help">${t('validation.offlineInfo')}</div>`)}
  ${card(t('validation.runTitle'),t('validation.runHint'),'flask',`<div class="help">${t('validation.refNote')}</div><div class="form-row three validation-thresholds">${field(t('validation.limitTrans'),'limit-translation',state.validationThresholds.translation_rms_mm,'number')}${field(t('validation.limitRot'),'limit-rotation',state.validationThresholds.rotation_rms_deg,'number')}${field(t('validation.limitProj'),'limit-projection',state.validationThresholds.projection_rms_px,'number')}</div>`,`<div class="actions">${btn('validation-run',t('validation.run'),'play','primary',ready&&(online?(v.live_count||0)>0:!!v.import_path)?'':'disabled')}${btn('validation-export',t('validation.export'),'save','',v.reports?.[mode]?'':'disabled')}</div>`,true)}</div></div>
  ${card(t('validation.reportTitle'),t('validation.reportDesc'),'check',validationReport(report))}</div>`
}

// Keep settings cards in independent columns so a collapsed card never stretches to match an expanded sibling.
function renderSettings(){const rt=state.runtime||{};const installed=Boolean(rt.runtimeInstalled);return `<div class="page">${pageHead(t('settings.kicker'),t('settings.title'),t('settings.desc'))}<div class="settings-layout"><div class="settings-column">${card(t('settings.appearance'),t('settings.appearanceDesc'),'sun',`<div class="field"><label>${t('settings.theme')}</label><div class="theme-selector" id="theme-segment">${themeSettingsChoice('system',t('appearance.system'))}${themeSettingsChoice('dark',t('appearance.dark'))}${themeSettingsChoice('light',t('appearance.light'))}</div></div>`)}${card(t('settings.runtime'),t('settings.runtimeDesc'),'terminal',`<div class="runtime-health"><div>${dot(installed?'success':'warning')}<b id="runtime-health-label">${installed?t('runtime.ready'):t('runtime.notInstalled')}</b></div><span id="runtime-health-path">${escapeHtml(rt.runtimePython||'~/.local/share/handeye-calibration/.venv/bin/python')}</span></div><div class="pose-box" id="runtime-info-box" style="margin-top:11px">Ubuntu : ${escapeHtml(rt.ubuntu||'unknown')}
ROS    : ${escapeHtml(rt.rosDistro||'not detected')}
Setup  : ${escapeHtml(rt.rosSetup||'not detected')}
Python : ${escapeHtml(rt.python||'unknown')}
Interface: HandEye</div><div class="help" style="margin-top:10px">${t('runtime.help')}</div><div class="mini-log ${state.runtimeInstallLog?'':'hidden'}" id="runtime-install-log">${escapeHtml(state.runtimeInstallLog.slice(-5000))}</div>`,`<div class="actions"><button class="btn primary" id="install-runtime" ${state.runtimeInstallState==='running'?'disabled':''}>${icon('play')}<span id="install-runtime-label">${state.runtimeInstallState==='running'?t('runtime.installing'):installed?t('runtime.repair'):t('runtime.install')}</span></button><button class="btn" id="restart-backend">${icon('terminal')}${t('runtime.restart')}</button></div>`,true)}</div><div class="settings-column">${card(t('settings.language'),t('settings.languageDesc'),'info',`<div class="field"><label>${t('settings.languageLabel')}</label>${segmentedControl('language-selector',state.language,[['zh-CN',t('settings.zhCN')],['en',t('settings.english')]],'amber')}</div>`)}</div></div>`}
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
  if(state.data.handeye?.count && state.data.handeye?.quality_mode){state.handeyeQuality=state.data.handeye.quality_mode}
  const present=new Set((state.data.handeye?.samples||[]).map(x=>Number(x.id)))
  for(const id of state.selectedSampleIds){if(!present.has(id))state.selectedSampleIds.delete(id)}
  $$('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.page===state.page))
  const names={connect:t('nav.connect'),intrinsics:t('nav.intrinsics'),handeye:t('nav.handeye'),solve:t('nav.solve'),validation:t('nav.validation'),settings:t('nav.settings'),about:t('nav.about')}
  $('#breadcrumb').textContent=(['settings','about'].includes(state.page)?t('breadcrumb.application'):t('breadcrumb.calibration'))+' / '+names[state.page]
  const html={connect:renderConnect,intrinsics:renderIntrinsics,handeye:renderHandeye,solve:renderSolve,validation:renderValidation,settings:renderSettings,about:renderAbout}[state.page]()
  $('#page').innerHTML=html
  if(animate)animateCurrentPage()
  bindPage(); updateShell()
}

async function commitOutputDirectory(selected){
  const previous=state.data.config?.output_dir||''
  const proposed=String(selected??'').trim()
  const input=$('#output-dir')
  if(!proposed){
    if(input)input.value=previous
    toast(t('toast.operationFailed'),t('connect.needOutput'),'warning')
    return false
  }
  if(proposed===previous){
    if(input)input.value=previous
    return true
  }
  try{
    // Persist only the output path and leave other unsaved connection settings intact
    const saved=await request('set_config',{output_dir:proposed})
    state.data=saved
    const path=saved.config.output_dir
    const currentInput=$('#output-dir')
    if(currentInput)currentInput.value=path
    const meta=$('#connect-output-meta')
    if(meta)meta.textContent=path
    toast(t('toast.settingsSaved'),path,'success')
    return true
  }catch(_error){
    // Revert to the active directory after a backend rejection
    const currentInput=$('#output-dir')
    if(currentInput)currentInput.value=previous
    return false
  }
}

function configFromForm(scope='connect'){
  const c={...state.data.config};
  if(scope==='connect'){
    c.output_dir=$('#output-dir')?.value??c.output_dir;c.camera_source=$('#camera-source')?.value??c.camera_source;c.image_topic=$('#image-topic')?.value??c.image_topic;c.camera_info_topic=$('#camera-info-topic')?.value??c.camera_info_topic;c.camera_frame=$('#camera-frame')?.value??c.camera_frame;c.robot_base_frame=$('#robot-base-frame')?.value??c.robot_base_frame;c.robot_end_frame=$('#robot-end-frame')?.value??c.robot_end_frame;c.camera_index=Number($('#camera-index')?.value??c.camera_index);c.camera_width=Number($('#camera-width')?.value??c.camera_width);c.camera_height=Number($('#camera-height')?.value??c.camera_height);c.ros_input_type=$('#ros-input-type')?.value??c.ros_input_type;c.pose_topic=$('#pose-topic')?.value??c.pose_topic;c.joint_dof=Number($('#joint-dof')?.value??c.joint_dof);c.joint_names=$('#joint-names')?.value??c.joint_names;c.capture_topic=$('#capture-topic')?.value??c.capture_topic;c.status_topic=$('#status-topic')?.value??c.status_topic
    if(c.ros_input_type==='transform'){c.robot_base_frame='';c.robot_end_frame=''}
  }
  if(scope==='board'){
    c.board_type=$('#board-type')?.value??c.board_type;c.chessboard_cols=Number($('#board-cols')?.value??c.chessboard_cols);c.chessboard_rows=Number($('#board-rows')?.value??c.chessboard_rows);c.square_size_mm=Number($('#square-mm')?.value??c.square_size_mm)
    c.charuco_squares_x=Number($('#charuco-x')?.value??c.charuco_squares_x);c.charuco_squares_y=Number($('#charuco-y')?.value??c.charuco_squares_y);c.charuco_marker_size_mm=Number($('#charuco-marker')?.value??c.charuco_marker_size_mm);c.charuco_dictionary=$('#charuco-dictionary')?.value??c.charuco_dictionary;c.charuco_min_corners=Number($('#charuco-min')?.value??c.charuco_min_corners);c.charuco_legacy_pattern=$('#charuco-legacy')?.checked??c.charuco_legacy_pattern
  }
  return c
}
function busyOverlay(label,cancellable=true){
  let node=document.getElementById('work-modal')
  if(!node){node=document.createElement('div');node.id='work-modal';node.className='work-modal-backdrop';document.body.appendChild(node)}
  node.innerHTML=`<div class="work-modal-card" role="dialog" aria-modal="true" aria-live="polite"><div class="work-loader"></div><h3>${escapeHtml(label)}</h3><p id="work-detail">${t('work.running')}</p><button class="btn" id="cancel-work" ${cancellable?'':'disabled'}>${t('work.cancel')}</button></div>`
  node.style.display='flex'
  return node
}
function hideBusy(){const node=document.getElementById('work-modal');if(node)node.style.display='none'}
async function busyRequest(method,params,label){
  let finished=false,ignored=false
  const timer=setTimeout(()=>{
    if(finished)return
    busyOverlay(label,false)
    const detail=document.getElementById('work-detail')
    if(detail)detail.textContent=t('work.waiting')
  },450)
  try{return await request(method,params)}finally{finished=true;clearTimeout(timer);hideBusy()}
}
async function launchCalculation(name,params,label){
  if(state.busyJob){toast(t('work.running'),'','warning');return}
  const job={id:null,name,label,cancelRequested:false,done:false}
  state.busyJob=job
  const overlay=busyOverlay(label,true)
  $('#cancel-work')?.addEventListener('click',async()=>{
    if(job.cancelRequested||job.done)return
    job.cancelRequested=true
    const detail=$('#work-detail');if(detail)detail.textContent=t('work.cancelling')
    $('#cancel-work').disabled=true
    if(job.id){try{await api.request('cancel_tool',{id:job.id})}catch(e){toast(t('toast.operationFailed'),String(e),'danger')}}
  })
  try{
    const result=await api.request('start_tool',{name,...params})
    job.id=result.id
    if(job.cancelRequested)await api.request('cancel_tool',{id:job.id})
    const completed=state.toolCompletions.get(job.id)
    if(completed){state.toolCompletions.delete(job.id);completeCalculation(completed)}
  }catch(e){state.busyJob=null;hideBusy();toast(t('toast.operationFailed'),e.message||String(e),'danger')}
}
function completeCalculation(data){
  const job=state.busyJob
  if(!job||!job.id||job.id!==data.id){state.toolCompletions.set(data.id,data);return}
  job.done=true
  state.busyJob=null
  hideBusy()
  if(data.name==='solve')state.solveResult=data.ok?data.result||null:null
  if(data.name==='intrinsic'&&data.ok)state.intrinsicResult=data.result||null
  if(data.cancelled)toast(t('work.cancelled'),'','warning')
  else if(data.ok)toast(t('toast.toolComplete',{name:job.label}),'','success')
  else toast(t('toast.operationFailed'),t('solve.failed'),'danger')
  refreshState().then(()=>{if(['solve','intrinsics','validation'].includes(state.page))renderPage(false)})
}
async function request(method,params={},okMessage=''){
  if(!api){toast(t('toast.backendUnavailable'),t('toast.useElectron'),'danger');throw new Error('backend unavailable')}
  try{const r=await api.request(method,params);if(okMessage)toast(okMessage,'','success');return r}catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger');throw e}
}
async function saveConfig(scope='connect'){const r=await request('set_config',configFromForm(scope),t('toast.settingsSaved'));state.data=r;renderPage()}
async function updateBoardSettings(){
  const current=state.data.config||{}
  const fromForm=configFromForm('board')
  const changes=Object.fromEntries(BOARD_KEYS.filter(key=>fromForm[key]!==current[key]).map(key=>[key,fromForm[key]]))
  if(!Object.keys(changes).length){toast(t('board.unchanged'),'','success');return}
  const captured=(Number(state.data.intrinsics?.count)||0)+(Number(state.data.handeye?.count)||0)
  if(captured){
    if(!window.confirm(t('board.confirmClear',{count:captured})))return
    changes.reset_captures=true
  }
  const button=$('#save-board')
  if(button)button.disabled=true
  try{
    const result=await request('update_board',changes,t('toast.boardUpdated'))
    state.data=result
    state.intrinsicResult=null
    state.solveResult=null
    renderPage(false)
  }finally{if($('#save-board'))$('#save-board').disabled=false}
}

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
function updateHandeyeQualityView(){
  const target=qualityTarget(),count=Number(state.data.handeye?.count)||0
  const recommended=$('#handeye-recommended'),progress=$('#handeye-progress')
  if(recommended)recommended.textContent=t('handeye.recommended',{count:target})
  if(progress)progress.style.width=`${Math.min(100,count/target*100)}%`
}
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
function validateConnection(c){
  if(!c.output_dir?.trim())return t('connect.needOutput')
  if(c.camera_source==='ros'&&!c.image_topic)return t('connect.needImage')
  if(c.ros_input_type!=='tf'&&!c.pose_topic)return t('connect.needPose')
  if(c.ros_input_type==='pose'&&!c.robot_end_frame.trim())return t('connect.needEnd')
  if(c.ros_input_type==='joints'&&!state.data.robot_model?.loaded)return t('guide.jointsNeedModel')
  if(['tf','joints'].includes(c.ros_input_type)&&(!c.robot_base_frame.trim()||!c.robot_end_frame.trim()))return t('connect.needFrames')
  const check=(value,kind)=>!value||availableTopics(kind).includes(value)
  if(state.discoveredOnce){
    if(c.camera_source==='ros'&&(!check(c.image_topic,'image')||!check(c.camera_info_topic,'info')))return t('connect.topicMissing')
    if(c.ros_input_type!=='tf'&&!check(c.pose_topic,c.ros_input_type))return t('connect.topicMissing')
    if(!check(c.capture_topic,'capture'))return t('connect.topicMissing')
  }
  return ''
}
function applyTopicDetails(kind,data){
  state.topicDetails[kind]=data
  const update=(id,value)=>{const input=$('#'+id);if(input&&value&&(!input.value.trim()||state.autoFilled.has(id))){input.value=value;state.autoFilled.add(id)}}
  if(kind==='image'||kind==='info'){
    update('camera-frame',data.frame_id)
    const old=state.topicDetails.image||{}, info=state.topicDetails.info||{}
    if(old.frame_id&&info.frame_id&&old.frame_id!==info.frame_id)toast(t('toast.operationFailed'),t('connect.cameraFrameMismatch'),'warning')
    if(old.width&&info.width&&(old.width!==info.width||old.height!==info.height))toast(t('toast.operationFailed'),t('connect.cameraSizeMismatch'),'warning')
  }
  if(kind==='pose'||kind==='transform'){
    update('robot-base-frame',data.frame_id)
    if(kind==='transform'){
      const base=$('#robot-base-frame'),end=$('#robot-end-frame')
      if(base)base.value=data.frame_id||''
      if(end)end.value=data.child_frame_id||''
    }
  }
  if(kind==='joints'){
    update('robot-base-frame',data.frame_id)
    if(data.joint_names?.length){update('joint-names',data.joint_names.join(','));const dof=$('#joint-dof');if(dof)dof.value=data.joint_names.length}
  }
  const camera=$('#camera-detected');if(camera)camera.innerHTML=cameraMetaText()
  const robot=$('#robot-detected');if(robot)robot.innerHTML=robotMetaText()
}
function bindTopicSelect(el){
  if(!el)return
  el.addEventListener('change',async()=>{
    const kind=el.dataset.kind,value=el.value
    if(kind==='transform'){
      delete state.topicDetails.transform
      const base=$('#robot-base-frame'),end=$('#robot-end-frame')
      if(base)base.value=''
      if(end)end.value=''
    }
    if(!value){delete state.topicDetails[kind];return}
    if(kind==='image'){
      delete state.topicDetails.image
      delete state.topicDetails.info
      // Use an existing matching CameraInfo publisher only, do not synthesize a topic
      const guess=value.replace(/\/image(?:_raw)?$/, '/camera_info')
      const info=$('#camera-info-topic')
      if(info&&!info.value&&availableTopics('info').includes(guess)){
        info.value=guess
        void inspectSelection('info',guess)
      }
    }
    await inspectSelection(kind,value)
  })
}
async function inspectSelection(kind,value){
  const messageType=TOPIC_TYPES[kind]
  if(!value||!messageType)return
  try{
    const result=await api.request('inspect_topic',{topic:value,message_type:messageType})
    if(result?.received&&result.metadata){
      const id={image:'image-topic',info:'camera-info-topic',pose:'pose-topic',transform:'pose-topic',joints:'pose-topic',capture:'capture-topic'}[kind]
      if($('#'+id)?.value===value)applyTopicDetails(kind,result.metadata)
    }
  }catch(e){toast(t('toast.operationFailed'),e.message||String(e),'warning')}
}
function bindCollapsibleCards(){
  $$('[data-card-toggle]').forEach(toggle=>toggle.addEventListener('click',()=>{
    const card=toggle.closest('.card')
    if(!card || card.dataset.cardKey!==toggle.dataset.cardToggle)return
    const expanded=toggle.getAttribute('aria-expanded')!=='true'
    setCardExpanded(card.dataset.cardKey,expanded)
    card.classList.toggle('collapsed',!expanded)
    toggle.setAttribute('aria-expanded',String(expanded))
    const label=expanded?(state.language==='zh-CN'?'收起':'Collapse'):(state.language==='zh-CN'?'展开':'Expand')
    toggle.setAttribute('aria-label',label)
    toggle.title=label
    // Keep the DOM intact so forms and controls do not lose their unsaved values.
    card.querySelectorAll(':scope > .card-body,:scope > .card-footer,:scope > .preview-surface').forEach(content=>{
      content.hidden=!expanded
    })
  }))
  // The original board editor uses native details. Persist its expanded state too.
  $$('.board-inline-editor').forEach(details=>{
    const key=cardKey('board-editor','board-editor')
    details.open=isCardExpanded(key)
    details.addEventListener('toggle',()=>{
      if(details.isConnected)setCardExpanded(key,details.open)
    })
  })
}
function bindPage(){
  bindCollapsibleCards()
  $('#board-type')?.addEventListener('change',e=>{
    const charuco=e.target.value==='charuco'
    $('#board-chess-fields').style.display=charuco?'none':'grid'
    $('#board-charuco-fields').style.display=charuco?'block':'none'
    if(charuco&&Number($('#square-mm').value)<=Number($('#charuco-marker').value))$('#square-mm').value=20
  })
  bindSegment('spatial-submode','spatialServoMode',()=>{if(state.data.servo?.busy&&state.spatialServoMode!=='auto')void api?.request('cancel_servo',{});renderPage(false)});
  bindSegment('validation-mode','validationMode',()=>{if(state.data.servo?.busy&&state.validationMode!=='spatial')void api?.request('cancel_servo',{});void api?.request('set_validation_overlay',{enabled:state.validationMode==='live',spatial:state.validationMode==='spatial'});renderPage(false)});
  bindSegment('intrinsic-quality','intrinsicQuality',updateIntrinsicQualityView);bindSegment('handeye-quality','handeyeQuality',updateHandeyeQualityView);bindSegment('sample-mode','sampleMode',updateSampleModeView);bindSegment('solve-mode','solveMode')
  $('#servo-interface-save')?.addEventListener('click',async()=>{
    try{const r=await request('set_servo_motion_config',{action:$('#interface-motion-action').value,group:$('#interface-motion-group').value});await refreshState();toast(t('servo.saved'),'','success')}
    catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger')}
  })
  $('#servo-interface-check')?.addEventListener('click',async()=>{
    try{const result=await request('check_servo_motion',{});toast(result.available?t('servo.motionAvailable'):t('servo.motionUnavailable'),result.reason,result.available?'success':'warning')}
    catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger')}
  })
  $('#servo-target-link')?.addEventListener('change',e=>{state.spatialLink=e.target.value})
  $('#servo-connect-depth')?.addEventListener('click',async()=>{
    try{await request('connect_servo_depth',{topic:$('#servo-depth-topic').value},t('servo.connectDepth'));await refreshState();toast(t('servo.depthReady'),'','success')}
    catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger')}
  })
  $('#servo-check-motion')?.addEventListener('click',async()=>{
    try{const result=await request('check_servo_motion',{});toast(result.available?t('servo.motionAvailable'):t('servo.motionUnavailable'),result.reason,result.available?'success':'warning')}
    catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger')}
  })
  $('#servo-save-motion')?.addEventListener('click',async()=>{
    try{await request('set_servo_motion_config',{action:$('#servo-motion-action').value,group:$('#servo-motion-group').value});await refreshState();toast(t('servo.saved'),'','success')}
    catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger')}
  })
  const servoSurface=$('#preview-surface')
  if(servoSurface&&state.page==='validation'&&state.validationMode==='spatial'&&state.spatialServoMode==='auto'){
    servoSurface.classList.add('servo-pick-mode')
    const toUV=(event,rect)=>({u:(event.clientX-rect.left)/rect.width,v:(event.clientY-rect.top)/rect.height})
    let startPoint=null,selection=null
    servoSurface.addEventListener('pointerdown',event=>{
      const img=$('.preview-image',servoSurface)
      if(!img?.naturalWidth||state.data.servo?.busy||event.button!==0)return
      const rect=img.getBoundingClientRect()
      if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)return
      startPoint=toUV(event,rect)
      selection=document.createElement('div');selection.className='servo-selection-box'
      servoSurface.appendChild(selection)
      servoSurface.setPointerCapture(event.pointerId)
      event.preventDefault()
    })
    servoSurface.addEventListener('pointermove',event=>{
      if(!startPoint||!selection)return
      const img=$('.preview-image',servoSurface),rect=img.getBoundingClientRect(),host=servoSurface.getBoundingClientRect()
      const at=toUV(event,rect)
      const x1=Math.min(startPoint.u,at.u),y1=Math.min(startPoint.v,at.v)
      const x2=Math.max(startPoint.u,at.u),y2=Math.max(startPoint.v,at.v)
      selection.style.left=`${rect.left-host.left+x1*rect.width}px`
      selection.style.top=`${rect.top-host.top+y1*rect.height}px`
      selection.style.width=`${(x2-x1)*rect.width}px`
      selection.style.height=`${(y2-y1)*rect.height}px`
    })
    servoSurface.addEventListener('pointerup',async event=>{
      if(!startPoint)return
      const img=$('.preview-image',servoSurface),rect=img.getBoundingClientRect()
      const at=toUV(event,rect)
      selection?.remove();selection=null
      const x0=startPoint.u,y0=startPoint.v;startPoint=null
      const width=Math.abs(x0-at.u),height=Math.abs(y0-at.v)
      const roi=width*rect.width>=8&&height*rect.height>=8?{width,height}:null
      const u=(x0+at.u)/2,v=(y0+at.v)/2
      if(u<=0||u>=1||v<=0||v>=1)return
      const link=$('#servo-target-link')?.value
      if(!link){toast(t('guide.modelMissing'),'','warning');return}
      try{await request('select_servo_target',{u,v,link,roi});await refreshState();toast(t('servo.selected'),'','success')}
      catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger')}
    })
    servoSurface.addEventListener('pointercancel',()=>{startPoint=null;selection?.remove();selection=null})
  }
  $('#servo-clear-selection')?.addEventListener('click',async()=>{
    try{await request('clear_servo_target',{});await refreshState()}catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger')}
  })
  $('#servo-start')?.addEventListener('click',async()=>{
    if(!$('#servo-safety-confirm')?.checked){toast(t('servo.needSafety'),'','danger');return}
    const step_m=Number($('#servo-step').value)/1000,clearance_m=Number($('#servo-clearance').value)/1000,max_steps=Number($('#servo-max-steps').value)
    if(!window.confirm(t('servo.confirmMotion')))return
    try{await request('start_servo',{step_m,clearance_m,max_steps,confirm:'I_UNDERSTAND_ROBOT_MOTION'});await refreshState()}
    catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger')}
  })
  $('#servo-cancel')?.addEventListener('click',async()=>{
    try{await request('cancel_servo',{});toast(t('servo.cancelRequested'),'','warning');await refreshState()}
    catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger')}
  })
  $('#spatial-tool-link')?.addEventListener('change',e=>{state.spatialLink=e.target.value})
  $('#spatial-corner-id')?.addEventListener('change',e=>{state.spatialCorner=Number(e.target.value)})
  $('#spatial-connect')?.addEventListener('click',()=>navigate('connect'))
  $('#spatial-freeze')?.addEventListener('click',async()=>{
    if(!window.confirm(t('validation.confirmFreeze')))return
    await request('freeze_validation',{},t('validation.frozen'));await refreshState()
  })
  $('#spatial-resolve')?.addEventListener('click',async()=>{
    try{const r=await request('resolve_tool_link',{link:$('#spatial-tool-link').value});toast(t('spatial.previewLink'),r.position_m.map(x=>n(x,5)).join(', ')+' m','success')}
    catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger')}
  })
  $('#spatial-contact')?.addEventListener('click',async()=>{
    if(!window.confirm(t('spatial.confirmContact')))return
    const link=$('#spatial-tool-link').value,corner_id=Number($('#spatial-corner-id').value)
    try{await request('record_spatial_contact',{link,corner_id},t('spatial.recordContact'));state.spatialLink=link;state.spatialCorner=corner_id;await refreshState();toast(t('spatial.recordContact'),t('spatial.recorded'),'success')}
    catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger')}
  })
  $('#spatial-measure')?.addEventListener('click',async()=>{
    try{const r=await request('measure_spatial_target',{},t('spatial.measure'));await refreshState();toast(t('spatial.measure'),`${n(r.error_mm,2)} mm`,'success')}
    catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger')}
  })
  $('#spatial-clear')?.addEventListener('click',async()=>{
    if(!window.confirm(t('spatial.confirmClear')))return
    await request('clear_spatial',{});await refreshState()
  })
  $('#camera-source')?.addEventListener('change',e=>{const ros=e.target.value==='ros';$('#camera-ros-fields').style.display=ros?'grid':'none';$('#camera-local-fields').style.display=ros?'none':'grid'})
  $('#ros-input-type')?.addEventListener('change',e=>{
    const mode=e.target.value
    $('#pose-topic-field').style.display=mode==='tf'?'none':''
    $('#joint-settings').style.display=mode==='joints'?'grid':'none'
    const host=$('#pose-topic-field')
    if(mode!=='tf'&&host){host.innerHTML=topicField(t('field.inputTopic'),'pose-topic','',mode);bindTopicSelect($('#pose-topic'))}
    const frames=$('#robot-frame-fields')
    if(frames){
      const c=state.data.config
      frames.innerHTML=mode==='transform'?
        `<div class="field"><label for="robot-base-frame">${t('field.baseFrame')} · ${t('connect.fromTransform')}</label><input class="control" id="robot-base-frame" readonly placeholder="${t('connect.waitingTransform')}"/></div><div class="field"><label for="robot-end-frame">${t('field.endFrame')} · ${t('connect.fromTransform')}</label><input class="control" id="robot-end-frame" readonly placeholder="${t('connect.waitingTransform')}"/></div>`:
        `${field(t('field.baseFrame'),'robot-base-frame',c.robot_base_frame||'')}${field(t('field.endFrame'),'robot-end-frame',c.robot_end_frame||'')}`
    }
    const guide=$('#robot-input-guide')
    if(guide)guide.innerHTML=icon('info')+'<span>'+({transform:t('guide.transform'),pose:t('guide.pose'),tf:t('guide.tf'),joints:t('guide.joints')}[mode]||'')+'</span>'
    if(mode==='joints'&&!state.data.robot_model?.loaded){toast(t('guide.modelTitle'),t('guide.joints'),'warning')}
    delete state.topicDetails.transform
    if(mode!=='transform')for(const id of ['robot-base-frame','robot-end-frame'])$('#'+id)?.addEventListener('input',()=>state.autoFilled.delete(id))
  })
  $$('.topic-select').forEach(bindTopicSelect)
  for(const id of ['camera-frame','robot-base-frame','robot-end-frame','joint-names']){
    $('#'+id)?.addEventListener('input',()=>state.autoFilled.delete(id))
  }
  $('#discover-topics')?.addEventListener('click',async()=>{
    const button=$('#discover-topics');button.disabled=true
    try{
      // Keep in-progress edits, even when the user has not connected yet
      const pending=configFromForm('connect')
      const result=await request('discover_topics')
      state.discoveredTopics=result.topics||[]
      state.discoveredOnce=true
      state.data.config={...state.data.config,...pending}
      renderPage(false)
      toast(t('action.discoverTopics'),`${state.discoveredTopics.length} ${t('connect.topicCount')}`,'success')
    }finally{if($('#discover-topics'))$('#discover-topics').disabled=false}
  })
  $('#import-robot-model')?.addEventListener('click',async()=>{
    try{
      const path=await api?.selectRobotModel?.()
      if(!path)return
      await request('import_robot_model',{path},t('guide.importModel'))
      await refreshState();toast(t('guide.modelTitle'),t('guide.imported'),'success')
    }catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger')}
  })
  $('#import-description-folder')?.addEventListener('click',async()=>{
    try{
      const path=await api?.selectRobotDescriptionFolder?.()
      if(!path)return
      await request('import_robot_model',{path},t('guide.importModel'))
      await refreshState();toast(t('guide.modelTitle'),t('guide.imported'),'success')
    }catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger')}
  })
  $('#open-model-viewer')?.addEventListener('click',async()=>{
    try{
      await window.HandeyeModelViewer.open((method,params)=>api.request(method,params),()=>state.language)
    }catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger')}
  })
  $('#load-robot-description')?.addEventListener('click',async()=>{
    try{await request('import_ros_model',{},t('guide.rosModel'));await refreshState();toast(t('guide.modelTitle'),t('guide.imported'),'success')}
    catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger')}
  })
  $('#clear-robot-model')?.addEventListener('click',async()=>{
    if(!window.confirm(t('guide.confirmClear')))return
    await request('clear_robot_model',{},t('guide.clearModel'));await refreshState()
  })
  $('#browse-output')?.addEventListener('click',async()=>{
    try{
      const p=await api?.selectDirectory($('#output-dir')?.value||state.data.config?.output_dir||'')
      if(p)await commitOutputDirectory(p)
    }catch(error){toast(t('toast.operationFailed'),error.message||String(error),'danger')}
  })
  // Persist manually typed paths before the next state refresh
  $('#output-dir')?.addEventListener('change',async event=>{await commitOutputDirectory(event.target.value)})
  $('#connect-robot')?.addEventListener('click',async()=>{
    const config=configFromForm('connect')
    const error=validateConnection(config)
    if(error){toast(t('toast.operationFailed'),error,'danger');return}
    const button=$('#connect-robot');button.disabled=true
    try{
      const saved=await request('set_config',config)
      state.data=saved
      await request('connect_robot')
      await refreshState()
      toast(t('action.connectRobot'),t('connect.waitingForData'),'success')
    }finally{if($('#connect-robot'))$('#connect-robot').disabled=false}
  })
  $('#disconnect-robot')?.addEventListener('click',async()=>{
    await request('disconnect_robot',{},t('action.disconnectRobot'))
    state.preview=''
    await refreshState()
  })
  $('#import-camera-info')?.addEventListener('click',async()=>{const r=await request('import_camera_info',{},t('toast.settingsSaved'));toast(t('intrinsics.saved'),r.path,'success');await refreshState()})
  $('#import-intrinsics')?.addEventListener('click',async()=>{const path=await api?.selectIntrinsics?.();if(!path)return;const r=await request('import_intrinsics',{path},t('toast.settingsSaved'));toast(t('intrinsics.saved'),r.path,'success');await refreshState()})
  $('#copy-matrix')?.addEventListener('click',async()=>{const r=state.solveResult;if(!r)return;const content=`${r.parent_frame} -> ${r.child_frame}\n${r.transform_matrix.map(row=>row.map(v=>Number(v).toFixed(8)).join('  ')).join('\n')}`;await navigator.clipboard.writeText(content);toast(t('action.copyMatrix'),'','success')})
  $('#export-matrix')?.addEventListener('click',async()=>{const r=await request('export_matrix',{},t('action.exportMatrix'));toast(t('toast.saveComplete'),r.path,'success')})
  $('#save-board')?.addEventListener('click',updateBoardSettings)
  $('#capture-intrinsic')?.addEventListener('click',async()=>{const r=await request('capture_intrinsic',{quality_mode:state.intrinsicQuality},t('toast.intrinsicCaptured'));toast(t('toast.sampleQuality'),`Sharpness ${n(r.sharpness,0)} · Coverage ${n(r.board_coverage_percent,1)}%`,'success');await refreshState()})
  $('#solve-intrinsic')?.addEventListener('click',async()=>{await launchCalculation('intrinsic',{quality_mode:state.intrinsicQuality},t('intrinsics.solveSave'))})
  $('#clear-intrinsic')?.addEventListener('click',async()=>{await request('clear_intrinsic',{},t('toast.intrinsicCleared'));state.intrinsicResult=null;await refreshState()})
  $('#go-handeye')?.addEventListener('click',()=>navigate('handeye'));$('#go-solve')?.addEventListener('click',()=>navigate('solve'))
  $('#manual-type')?.addEventListener('change',e=>{state.manualType=e.target.value;refreshManualFields()});$('#angle-unit')?.addEventListener('change',e=>{state.angleUnit=e.target.value})
  $('#capture-handeye')?.addEventListener('click',async()=>{const params={mode:state.sampleMode,quality_mode:state.handeyeQuality};if(state.sampleMode==='manual'){params.manual_type=state.manualType;params.angle_unit=state.angleUnit;params.values=$$('[id^="manual-"]').map(e=>Number(e.value))}const r=await request('capture_handeye',params,t('toast.handeyeCaptured'));toast(t('toast.sampleQuality'),`Reproj ${n(r.reprojection_error_px,3)} px · ${n(r.pixels_per_square,1)} px/square`,'success');await refreshState()})
  $$('.sample-check').forEach(el=>el.addEventListener('change',()=>{const id=Number(el.value);if(el.checked)state.selectedSampleIds.add(id);else state.selectedSampleIds.delete(id);const button=$('#delete-selected-samples');if(button)button.disabled=!state.selectedSampleIds.size}))
  $('#select-all-samples')?.addEventListener('click',()=>{const checkboxes=$$('.sample-check');const all=checkboxes.every(el=>el.checked);state.selectedSampleIds.clear();checkboxes.forEach(el=>{el.checked=!all;if(!all)state.selectedSampleIds.add(Number(el.value))});const button=$('#delete-selected-samples');if(button)button.disabled=!state.selectedSampleIds.size})
  $('#delete-selected-samples')?.addEventListener('click',async()=>{const ids=[...state.selectedSampleIds].sort((a,b)=>a-b);if(!ids.length)return;if(!window.confirm(t('samples.confirmDelete',{ids:ids.join(', ')})))return;await busyRequest('delete_samples',{ids},t('samples.deleting'));state.selectedSampleIds.clear();state.solveResult=null;state.logs='';await refreshState()})
  $('#import-samples')?.addEventListener('click',async()=>{
    let path
    try {
      path=await api?.selectSamples?.(state.data.config?.output_dir||'')
    } catch(error) {
      toast(t('toast.operationFailed'),error.message||String(error),'danger')
      return
    }
    if(!path)return
    if((state.data.handeye?.count||0)&&!window.confirm(t('samples.confirmReplace')))return
    let result
    try {
      result=await busyRequest('import_samples',{path,replace:true},t('samples.importing'))
    } catch(_error) {
      return
    }
    if(!result)return
    state.handeyeQuality=result.quality_mode||'standard'
    state.selectedSampleIds.clear()
    state.solveResult=null
    state.logs=''
    await refreshState()
  })
  $('#save-samples')?.addEventListener('click',async()=>{const r=await request('save_samples',{},t('toast.samplesSaved'));toast(t('toast.saveComplete'),r.path,'success');await refreshState()})
  $('#clear-samples')?.addEventListener('click',async()=>{if((state.data.handeye?.count||0)&&!window.confirm(t('samples.confirmClear')))return;await request('clear_samples',{},t('toast.samplesCleared'));state.selectedSampleIds.clear();state.solveResult=null;state.logs='';await refreshState()})
  for(const [id,name,labelKey] of [['run-diagnose','diagnose','action.diagnose'],['run-solve','solve','action.solve']]) $('#'+id)?.addEventListener('click',async()=>{
    if(name==='solve'){state.solveResult=null;renderPage(false)}
    await launchCalculation(name,{solve_mode:state.solveMode},t(labelKey))
  })
  for(const id of ['freeze-validation','validation-freeze'])$('#'+id)?.addEventListener('click',async()=>{
    if((state.data.validation?.live_count||0)>0&&!window.confirm(t('validation.confirmFreeze')))return
    try{await request('freeze_validation',{},t('validation.frozen'));await refreshState();if(id==='freeze-validation')navigate('validation')}catch(_error){}
  })
  $('#go-validation')?.addEventListener('click',()=>navigate('validation'))
  $('#validation-import')?.addEventListener('click',async()=>{
    let path=''
    try{path=await api?.selectSamples?.(state.data.config?.output_dir||'')}catch(e){toast(t('toast.operationFailed'),e.message||String(e),'danger');return}
    if(!path)return
    try{await request('import_validation',{path},t('validation.imported'));await refreshState()}catch(_error){}
  })
  $('#validation-capture')?.addEventListener('click',async()=>{
    try{const r=await request('capture_validation',{},t('validation.captured'));await refreshState()}catch(_error){}
  })
  $('#validation-clear')?.addEventListener('click',async()=>{
    if(!window.confirm(t('validation.confirmClear')))return
    try{await request('clear_validation',{},t('validation.cleared'));await refreshState()}catch(_error){}
  })
  $('#validation-run')?.addEventListener('click',async()=>{
    const limits={translation_rms_mm:Number($('#limit-translation')?.value),rotation_rms_deg:Number($('#limit-rotation')?.value),projection_rms_px:Number($('#limit-projection')?.value)}
    if(!Object.values(limits).every(x=>Number.isFinite(x)&&x>0)){toast(t('toast.operationFailed'),t('validation.invalidLimits'),'danger');return}
    state.validationThresholds=limits
    await launchCalculation(state.validationMode==='offline'?'validate_offline':'validate_live',{thresholds:limits},t('validation.running'))
  })
  $('#validation-export')?.addEventListener('click',async()=>{
    try{const r=await request('export_validation',{mode:state.validationMode},t('validation.exported'));toast(t('validation.reportPath'),r.path,'success')}catch(_error){}
  })
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
function updateShell(){const cam=state.data.camera||{},ros=state.data.ros||{};const p=$('#camera-pill');if(p)p.innerHTML=`${dot(cam.receiving?'success':'warning')} ${t('status.camera')} ${cam.receiving?t('status.live'):cam.open?t('status.waiting'):t('status.offline')}`;const r=$('#ros-pill');if(r)r.innerHTML=`${dot(ros.running?'success':'warning')} ROS2 ${ros.running?t('status.rosConnected'):t('status.rosOffline')}`;const cstat=$('#connect-camera-state');if(cstat){cstat.textContent=cam.receiving?t('status.connected'):cam.open?t('status.waiting'):t('status.offline');cstat.style.color=cam.receiving?'var(--success)':'var(--text-secondary)'}const rstat=$('#connect-robot-state');if(rstat){rstat.textContent=ros.pose?t('status.receiving'):ros.running?t('status.waiting'):t('status.offline');rstat.style.color=ros.pose?'var(--success)':'var(--text-secondary)'}const pl=$('#preview-live-pill');if(pl)pl.innerHTML=`${dot(cam.receiving?'success':'warning')} ${cam.receiving?t('status.live'):cam.open?t('status.waiting'):t('status.offline')}`;const cm=$('#camera-detected');if(cm)cm.innerHTML=cameraMetaText();const rm=$('#robot-detected');if(rm)rm.innerHTML=robotMetaText();const b=$('#board-pill');if(b)b.innerHTML=`${dot(cam.board_found?'success':'warning')} ${t('status.board')} ${cam.board_found?t('status.detected'):'—'}`;const rl=$('#runtime-label');if(rl){rl.textContent=backendStateLabel(state.backend);rl.previousElementSibling?.classList.toggle('success',state.backend==='ready')}const rs=$('#ros-sidebar');if(rs)rs.textContent=state.runtime?.rosSetup?`ROS · ${state.runtime.rosSetup.split('/').slice(-2,-1)[0]}`:t('status.rosNotDetected')}
let pendingPreview=null
let previewRaf=0
function updatePreviewFrame(data){
  state.preview=data.jpeg||''
  state.data.camera={...(state.data.camera||{}),open:true,receiving:true,board_found:Boolean(data.board_found),width:data.width,height:data.height}
  updateShell()
  pendingPreview=data
  if(previewRaf)return
  previewRaf=requestAnimationFrame(()=>{
    previewRaf=0
    const frame=pendingPreview
    pendingPreview=null
    if(!frame)return
    const surface=$('#preview-surface')
    let img=null
    if(surface){
      img=$('.preview-image',surface)
      if(!img){surface.innerHTML='<img class="preview-image" alt="Camera preview" decoding="async">';img=$('.preview-image',surface)}
      if(img&&frame.jpeg)img.src='data:image/jpeg;base64,'+frame.jpeg
    }
    const live=$('#preview-live-pill')
    if(live)live.innerHTML=`${dot('success')} ${t('status.live')}`
    const size=$('#preview-size')
    if(size)size.textContent=`${frame.width||640} × ${frame.height||480}`
    if(state.page==='validation'&&state.validationMode==='spatial'&&state.spatialServoMode==='auto'){
      const target=state.data.servo?.target
      let marker=surface?$('.servo-target-marker',surface):null
      if(target&&surface&&img&&img.getBoundingClientRect().width>0){
        if(!marker){marker=document.createElement('div');marker.className='servo-target-marker';marker.textContent='+';surface.appendChild(marker)}
        const rect=img.getBoundingClientRect(),host=surface.getBoundingClientRect()
        marker.style.left=`${rect.left-host.left+(target.u/(frame.width||640))*rect.width}px`
        marker.style.top=`${rect.top-host.top+(target.v/(frame.height||480))*rect.height}px`
      }else marker?.remove()
    }
    const board=$('#board-live')
    if(board){board.textContent=frame.board_found?t('board.detectedCount',{count:frame.corner_count||0}):t('status.notDetected');board.style.color=frame.board_found?'var(--success)':'var(--warning)'}
  })
}

function updatePoseView(data){state.data.ros={...(state.data.ros||{}),running:true,pose:data};const pose=$('#pose-live');if(pose)pose.textContent=poseText();if(state.page==='connect'){applyTopicDetails(state.data.config.ros_input_type==='transform'?'transform':'pose',{frame_id:data.frame_id,child_frame_id:data.child_frame_id})}updateShell()}
function updateRuntimeView(){const rt=state.runtime||{};const installed=Boolean(rt.runtimeInstalled);const label=$('#runtime-health-label');if(label)label.textContent=installed?t('runtime.ready'):t('runtime.notInstalled');const pathEl=$('#runtime-health-path');if(pathEl)pathEl.textContent=rt.runtimePython||'~/.local/share/handeye-calibration/.venv/bin/python';const info=$('#runtime-info-box');if(info)info.textContent=`Ubuntu : ${rt.ubuntu||t('common.unknown')}
ROS    : ${rt.rosDistro||t('common.notDetected')}
Setup  : ${rt.rosSetup||t('common.notDetected')}
Python : ${rt.python||t('common.unknown')}
Interface: HandEye`;const log=$('#runtime-install-log');if(log){log.textContent=state.runtimeInstallLog.slice(-5000);log.classList.toggle('hidden',!state.runtimeInstallLog)}const install=$('#install-runtime');if(install)install.disabled=state.runtimeInstallState==='running';const installLabel=$('#install-runtime-label');if(installLabel)installLabel.textContent=state.runtimeInstallState==='running'?t('runtime.installing'):installed?t('runtime.repair'):t('runtime.install')}
function appendBackendLog(text){state.logs+=text||'';const log=$('#log-box');if(log){log.textContent=state.logs;log.scrollTop=log.scrollHeight}}
async function refreshState(){if(!api)return;try{state.data=await api.request('get_state');updateShell();renderPage(false)}catch(e){state.backend='error';updateShell()}}
function handleEvent(msg){const {event,data}=msg;if(event==='state'){state.data=data;updateShell()}else if(event==='preview'){updatePreviewFrame(data)}else if(event==='pose'){updatePoseView(data)}else if(event==='log'){appendBackendLog(data.text||'')}else if(event==='error'){toast('Backend',data?.message||t('error.unknown'),'danger')}else if(event==='camera_metadata'){state.data.camera={...(state.data.camera||{}),frame_id:data?.frame_id||state.data.camera?.frame_id,width:data?.width||state.data.camera?.width,height:data?.height||state.data.camera?.height};if(state.page==='connect')applyTopicDetails('image',data)}else if(event==='servo_progress'){state.data.servo={...(state.data.servo||{}),...data};const box=$('#servo-run-status');if(box)box.innerHTML=`<b>${escapeHtml(data.phase||'')}</b><span>${escapeHtml(data.message||'')}</span>`;const cancel=$('#servo-cancel');if(cancel)cancel.disabled=!data.busy;if(['failed','cancelled','completed','incomplete'].includes(data.phase))void refreshState()}else if(event==='servo_feedback'){const box=$('#servo-run-status span');if(box&&data.text)box.textContent=data.text}else if(event==='servo_finished'){toast(t('servo.completed'),data.report_path||'',data.status==='failed'?'danger':data.status==='cancelled'?'warning':'success');void refreshState()}else if(event==='tool_done'){completeCalculation(data)}}

async function boot(){document.documentElement.lang=state.language;shell();applyTheme(state.theme);renderPage(false);syncResponsiveShell();if(!responsiveListenerBound){responsiveListenerBound=true;window.addEventListener('resize',syncResponsiveShell,{passive:true})}if(!api){state.backend='unavailable';updateShell();toast(t('toast.bridgeMissing'),t('toast.startApp'),'warning');return}api.onEvent?.(handleEvent);api.onRuntime?.(m=>{state.backend=m.state||'unknown';state.runtime={...(state.runtime||{}),...m};updateShell();updateRuntimeView()});api.onRuntimeInstall?.(m=>{if(m.state==='starting')state.runtimeInstallState='running';if(m.state==='log')state.runtimeInstallLog+=(m.text||'');if(m.state==='done')state.runtimeInstallState='done';if(m.state==='error')state.runtimeInstallState='error';updateRuntimeView()});api.onStderr?.(t=>appendBackendLog('[backend] '+t));try{state.runtime=await api.runtimeInfo();const ping=await api.request('ping');state.backend=ping.pong?'ready':'error';state.data=await api.request('get_state')}catch(e){state.backend='error';toast(t('toast.backendStartFailed'),e.message,'danger')}updateShell();renderPage(false)}
boot()
