#!/usr/bin/env node
import { spawn, execFileSync } from 'node:child_process'
import { readFileSync, writeFileSync, mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import process from 'node:process'

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..')
const RENDERER = path.join(ROOT, 'src', 'renderer')
const SCREENSHOT = process.env.HANDEYE_SMOKE_SCREENSHOT || path.join(ROOT, 'renderer-smoke.png')

function which(name) {
  try { return execFileSync('which', [name], { encoding: 'utf8' }).trim() } catch { return '' }
}
function browserBin() {
  return process.env.CHROMIUM_BIN || which('chromium') || which('chromium-browser') || which('google-chrome') || which('google-chrome-stable')
}
function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)) }

class CDP {
  constructor(ws) { this.ws = ws; this.seq = 0; this.pending = new Map() }
  static async connect(url) {
    const ws = new WebSocket(url)
    await new Promise((resolve, reject) => {
      ws.addEventListener('open', resolve, { once: true })
      ws.addEventListener('error', reject, { once: true })
    })
    const cdp = new CDP(ws)
    ws.addEventListener('message', event => {
      const msg = JSON.parse(event.data)
      if (msg.id && cdp.pending.has(msg.id)) {
        const { resolve, reject } = cdp.pending.get(msg.id)
        cdp.pending.delete(msg.id)
        if (msg.error) reject(new Error(msg.error.message || JSON.stringify(msg.error)))
        else resolve(msg.result || {})
      }
    })
    return cdp
  }
  call(method, params = {}) {
    const id = ++this.seq
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject })
      this.ws.send(JSON.stringify({ id, method, params }))
    })
  }
  close() { this.ws.close() }
}

function assembleRenderer() {
  let html = readFileSync(path.join(RENDERER, 'index.html'), 'utf8')
  const css = readFileSync(path.join(RENDERER, 'styles.css'), 'utf8')
  let locales = readFileSync(path.join(RENDERER, 'locales.js'), 'utf8')
  let js = readFileSync(path.join(RENDERER, 'app.js'), 'utf8')
  html = html
    .replace(/\s*<meta http-equiv="Content-Security-Policy"[^>]+\/>/, '')
    .replace(/<link rel="stylesheet" href="styles\.css"\s*\/>/, `<style>${css}</style>`)
    .replace(/<script src="locales\.js"><\/script>/, '')
    .replace(/<script src="app\.js"><\/script>/, '')
  locales = locales.replaceAll('localStorage.', 'window.__handeyeLocalStorage.')
  js = js
    .replace(
      "const api = window.handeye || (location.search.includes('mock=1') ? createMockApi() : null)",
      'const api = createMockApi()'
    )
    .replaceAll('localStorage.', 'window.__handeyeLocalStorage.')
  js = "window.__handeyeStore={'handeye-language':'en'};window.__handeyeLocalStorage={getItem:k=>window.__handeyeStore[k]??null,setItem:(k,v)=>{window.__handeyeStore[k]=String(v)}};\n" + locales + '\n' + js
  return { html, js }
}

async function waitJson(port) {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/json`)
      if (r.ok) { const pages = await r.json(); if (pages.length) return pages }
    } catch {}
    await sleep(100)
  }
  throw new Error('Chromium DevTools endpoint did not start')
}

async function evalValue(cdp, expression) {
  const out = await cdp.call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (out.exceptionDetails) throw new Error(out.exceptionDetails.text || 'renderer evaluation failed')
  return out.result?.value
}

async function waitForPageTitle(cdp, expected, timeoutMs = 1800) {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    const title = await evalValue(cdp, 'document.querySelector(".page-title")?.textContent')
    if (title === expected) return
    await sleep(25)
  }
  throw new Error(`page transition timed out waiting for ${expected}`)
}

async function main() {
  const bin = browserBin()
  if (!bin) throw new Error('Chromium/Chrome not found; set CHROMIUM_BIN to run renderer smoke test')
  const port = 9237
  const profile = mkdtempSync(path.join(tmpdir(), 'handeye-chromium-'))
  const child = spawn(bin, [
    '--headless=new', '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu',
    '--remote-allow-origins=*', `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`, 'about:blank'
  ], { stdio: ['ignore', 'ignore', 'ignore'] })

  let cdp
  try {
    const pages = await waitJson(port)
    cdp = await CDP.connect(pages[0].webSocketDebuggerUrl)
    await cdp.call('Page.enable')
    await cdp.call('Runtime.enable')
    const tree = await cdp.call('Page.getFrameTree')
    const { html, js } = assembleRenderer()
    await cdp.call('Page.setDocumentContent', { frameId: tree.frameTree.frame.id, html })
    await cdp.call('Runtime.evaluate', { expression: js })

    let navCount = 0
    for (let i = 0; i < 80; i++) {
      navCount = await evalValue(cdp, 'document.querySelectorAll(".nav-item").length')
      if (navCount === 6) break
      await sleep(100)
    }
    if (navCount !== 6) throw new Error(`expected 6 navigation items, got ${navCount}`)

    const title = await evalValue(cdp, 'document.querySelector(".page-title")?.textContent')
    if (title !== 'Connect') throw new Error(`expected Connect page, got ${title}`)
    const style = await evalValue(cdp, 'getComputedStyle(document.body).backgroundColor')
    if (style !== 'rgb(10, 10, 16)') throw new Error(`Dark theme not applied: ${style}`)
    const fontSize = await evalValue(cdp, 'parseFloat(getComputedStyle(document.body).fontSize)')
    if (Math.abs(fontSize - 16.1) > 0.02) throw new Error(`Font scale mismatch: ${fontSize}`)

    const stateStable = await evalValue(cdp, `(() => { const node=document.querySelector('#page > .page'); handleEvent({event:'state',data:state.data}); return document.querySelector('#page > .page')===node })()`)
    if (!stateStable) throw new Error('State event rebuilt the page')
    const previewStable = await evalValue(cdp, `(() => { const node=document.querySelector('#page > .page'); handleEvent({event:'preview',data:{jpeg:'',board_found:false,width:640,height:480}}); return document.querySelector('#page > .page')===node })()`)
    if (!previewStable) throw new Error('Preview event rebuilt the page')
    await evalValue(cdp, `state.data.camera.open=false; state.data.camera.board_found=false; state.preview=''; true`)

    const pagesToCheck = [
      ['intrinsics', 'Camera Intrinsics'], ['handeye', 'Hand-Eye Sampling'],
      ['solve', 'Solve & Verify'], ['settings', 'Settings'], ['about', 'About HandEye']
    ]
    await evalValue(cdp, `document.querySelector('[data-page="intrinsics"]').click(); true`)
    await sleep(70)
    const retainedDuringExit = await evalValue(cdp, 'document.querySelector(".page-title")?.textContent')
    if (retainedDuringExit !== 'Connect') throw new Error(`outgoing page was replaced too early: ${retainedDuringExit}`)
    await waitForPageTitle(cdp, 'Camera Intrinsics')
    for (const [page, expected] of pagesToCheck) {
      if (page !== 'intrinsics') {
        await evalValue(cdp, `document.querySelector('[data-page="${page}"]').click(); true`)
        await waitForPageTitle(cdp, expected)
      }
      const visibleText = await evalValue(cdp, 'document.querySelector(".content").innerText.toLowerCase()')
      if (visibleText.includes('kudu')) throw new Error(`reference project name visible on ${page}`)
    }
    await evalValue(cdp, `document.querySelector('[data-page="handeye"]').click(); true`)
    await waitForPageTitle(cdp, 'Hand-Eye Sampling')
    const poseStable = await evalValue(cdp, `(() => { const node=document.querySelector('#page > .page'); handleEvent({event:'pose',data:{values:[0.4,0,0.5,0,0,0,1],frame_id:'arm_base_link',timestamp:1}}); return document.querySelector('#page > .page')===node })()`)
    if (!poseStable) throw new Error('Pose event rebuilt the page')
    await evalValue(cdp, `state.data.ros.running=false; state.data.ros.pose=null; true`)
    await evalValue(cdp, `document.querySelector('[data-page="connect"]').click(); true`)
    await waitForPageTitle(cdp, 'Connect')
    await evalValue(cdp, `document.querySelector('#open-camera').click(); true`)
    for (let i = 0; i < 50; i++) {
      const ready = await evalValue(cdp, `document.querySelectorAll('.metric-value')[0]?.textContent.trim() === 'Connected'`)
      if (ready) break
      await sleep(50)
      if (i === 49) throw new Error('Open Camera action did not update Connect page')
    }
    await evalValue(cdp, `document.querySelector('#start-ros').click(); true`)
    for (let i = 0; i < 50; i++) {
      const ready = await evalValue(cdp, `document.querySelectorAll('.metric-value')[1]?.textContent.trim() === 'Receiving'`)
      if (ready) break
      await sleep(50)
      if (i === 49) throw new Error('ROS2 Connect action did not update status')
    }

    await evalValue(cdp, `document.querySelector('[data-page="intrinsics"]').click(); true`)
    await waitForPageTitle(cdp, 'Camera Intrinsics')
    const segmentStable = await evalValue(cdp, `(() => { const page=document.querySelector('#page > .page'); const indicator=document.querySelector('#intrinsic-quality .segmented-indicator'); window.__segmentBefore=indicator.style.transform; document.querySelector('#intrinsic-quality [data-value="strict"]').click(); return {same:document.querySelector('#page > .page')===page,before:window.__segmentBefore} })()`)
    if (!segmentStable.same) throw new Error('Segmented control rebuilt the page')
    await sleep(360)
    const indicatorMoved = await evalValue(cdp, `document.querySelector('#intrinsic-quality .segmented-indicator').style.transform !== window.__segmentBefore`)
    if (!indicatorMoved) throw new Error('Segmented indicator did not move')
    await evalValue(cdp, `document.querySelector('#intrinsic-quality [data-value="minimal"]').click(); true`)
    await sleep(340)
    for (let capture = 1; capture <= 3; capture++) {
      await evalValue(cdp, `document.querySelector('#capture-intrinsic').click(); true`)
      for (let i = 0; i < 50; i++) {
        const text = await evalValue(cdp, `document.querySelector('.content').innerText`)
        if (text.includes(`Images captured ${capture}`)) break
        await sleep(50)
        if (i === 49) throw new Error(`Intrinsic capture ${capture} did not update count`)
      }
    }
    await evalValue(cdp, `document.querySelector('#solve-intrinsic').click(); true`)
    for (let i = 0; i < 50; i++) {
      const text = await evalValue(cdp, `document.querySelector('.content').innerText`)
      if (text.includes('Intrinsics file') && text.includes('Ready')) break
      await sleep(50)
      if (i === 49) throw new Error('Solve Intrinsics action did not produce Ready state')
    }

    await evalValue(cdp, `document.querySelector('[data-page="handeye"]').click(); true`)
    await waitForPageTitle(cdp, 'Hand-Eye Sampling')
    await evalValue(cdp, `document.querySelector('#sample-mode [data-value="manual"]').click(); true`)
    await sleep(420)
    const manualOpen = await evalValue(cdp, `document.querySelector('#manual-input-panel').classList.contains('open')`)
    if (!manualOpen) throw new Error('Manual input panel did not open')
    await evalValue(cdp, `document.querySelector('#capture-handeye').click(); true`)
    for (let i = 0; i < 50; i++) {
      const text = await evalValue(cdp, `document.querySelector('.content').innerText`)
      if (text.includes('Samples captured 1')) break
      await sleep(50)
      if (i === 49) throw new Error('Capture Sample action did not update count')
    }
    await evalValue(cdp, `document.querySelector('#save-samples').click(); true`)
    await sleep(100)

    await evalValue(cdp, `document.querySelector('[data-page="solve"]').click(); true`)
    await waitForPageTitle(cdp, 'Solve & Verify')
    await evalValue(cdp, `document.querySelector('#run-solve').click(); true`)
    for (let i = 0; i < 50; i++) {
      const text = await evalValue(cdp, `document.querySelector('.content').innerText`)
      if (text.includes('Solved') && text.includes('2.310')) break
      await sleep(50)
      if (i === 49) throw new Error('Solve action did not render mock transform result')
    }

    await evalValue(cdp, `document.querySelector('[data-page="settings"]').click(); true`)
    await waitForPageTitle(cdp, 'Settings')
    const settingsText = await evalValue(cdp, `document.querySelector('.content').innerText`)
    if (!settingsText.includes('Install Runtime') && !settingsText.includes('Repair Runtime')) {
      throw new Error('Settings runtime action missing')
    }
    const languageOptions = await evalValue(cdp, `Array.from(document.querySelectorAll('#language-selector button')).map(el=>el.textContent.trim())`)
    if (languageOptions.length !== 2 || !languageOptions.includes('简体中文') || !languageOptions.includes('English')) {
      throw new Error(`Language selector options mismatch: ${JSON.stringify(languageOptions)}`)
    }
    await evalValue(cdp, `document.querySelector('#language-selector [data-value="zh-CN"]').click(); true`)
    await waitForPageTitle(cdp, '设置')
    const zhState = await evalValue(cdp, `({lang:document.documentElement.lang,stored:window.__handeyeStore['handeye-language'],connect:document.querySelector('[data-page="connect"] > span:not(.step)')?.textContent,count:state.data.handeye.count})`)
    if (zhState.lang !== 'zh-CN' || zhState.stored !== 'zh-CN' || zhState.connect !== '连接' || zhState.count !== 1) {
      throw new Error(`Chinese language switch failed or state changed: ${JSON.stringify(zhState)}`)
    }
    await evalValue(cdp, `document.querySelector('[data-page="solve"]').click(); true`)
    await waitForPageTitle(cdp, '求解与验证')
    const zhSolveButtons = await evalValue(cdp, `Array.from(document.querySelectorAll('#run-diagnose,#run-solve,#run-verify')).map(el=>el.textContent.trim())`)
    if (!zhSolveButtons.includes('诊断') || !zhSolveButtons.includes('求解') || !zhSolveButtons.includes('验证')) {
      throw new Error(`Chinese workflow actions are not localized: ${JSON.stringify(zhSolveButtons)}`)
    }
    await evalValue(cdp, `document.querySelector('[data-page="settings"]').click(); true`)
    await waitForPageTitle(cdp, '设置')
    await evalValue(cdp, `document.querySelector('#language-selector [data-value="en"]').click(); true`)
    await waitForPageTitle(cdp, 'Settings')
    const enState = await evalValue(cdp, `({lang:document.documentElement.lang,stored:window.__handeyeStore['handeye-language'],connect:document.querySelector('[data-page="connect"] > span:not(.step)')?.textContent,count:state.data.handeye.count})`)
    if (enState.lang !== 'en' || enState.stored !== 'en' || enState.connect !== 'Connect' || enState.count !== 1) {
      throw new Error(`English language switch failed or state changed: ${JSON.stringify(enState)}`)
    }
    const themeIconGeometry = await evalValue(cdp, `(() => Array.from(document.querySelectorAll('#theme-segment .theme-option-icon')).map(el => { const r=el.getBoundingClientRect(); return {w:r.width,h:r.height,y:r.y+r.height/2} }))()`)
    if (themeIconGeometry.length !== 3) throw new Error('Theme selector icon count mismatch')
    if (themeIconGeometry.some(item => Math.abs(item.w - 28) > 0.5 || Math.abs(item.h - 28) > 0.5)) throw new Error(`Theme icon box mismatch: ${JSON.stringify(themeIconGeometry)}`)
    if (Math.max(...themeIconGeometry.map(item => item.y)) - Math.min(...themeIconGeometry.map(item => item.y)) > 0.5) throw new Error(`Theme icons are not vertically aligned: ${JSON.stringify(themeIconGeometry)}`)
    const menuCount = await evalValue(cdp, `document.querySelector('#appearance-toggle').click(); document.querySelector('#appearance-menu').classList.contains('hidden') ? 0 : document.querySelectorAll('#appearance-menu .appearance-option').length`)
    if (menuCount !== 3) throw new Error(`Appearance menu did not open with 3 options: ${menuCount}`)
    const theme = await evalValue(cdp, `document.querySelector('#theme-segment [data-theme="light"]').click(); document.documentElement.className`)
    if (!String(theme).includes('light')) throw new Error('Light theme toggle failed')

    await evalValue(cdp, `document.querySelector('#theme-segment [data-theme="dark"]').click(); document.querySelector('[data-page="connect"]').click(); document.querySelector('#toasts').innerHTML=''; true`)
    await waitForPageTitle(cdp, 'Connect')
    await sleep(180)
    const appearanceClosed = await evalValue(cdp, `document.querySelector('#appearance-menu').classList.contains('hidden')`)
    if (!appearanceClosed) throw new Error('Appearance menu remained open after navigation')
    await cdp.call('Emulation.setDeviceMetricsOverride', { width: 880, height: 820, deviceScaleFactor: 1, mobile: false })
    await evalValue(cdp, `syncResponsiveShell(); true`)
    await sleep(120)
    const compactSidebar = await evalValue(cdp, `(() => { const el=document.querySelector('.sidebar'); return {compact:el.classList.contains('compact'),width:el.getBoundingClientRect().width} })()`)
    if (!compactSidebar.compact || compactSidebar.width > 80) throw new Error(`Responsive compact sidebar failed: ${JSON.stringify(compactSidebar)}`)
    await cdp.call('Emulation.setDeviceMetricsOverride', { width: 1020, height: 860, deviceScaleFactor: 1, mobile: false })
    await evalValue(cdp, `syncResponsiveShell(); true`)
    await sleep(120)
    const previewColumns = await evalValue(cdp, `getComputedStyle(document.querySelector('.preview-layout')).gridTemplateColumns`)
    if (String(previewColumns).trim().split(' ').length !== 1) throw new Error(`Responsive preview layout did not collapse: ${previewColumns}`)
    await cdp.call('Emulation.setDeviceMetricsOverride', { width: 1460, height: 940, deviceScaleFactor: 1, mobile: false })
    await evalValue(cdp, `syncResponsiveShell(); true`)
    await sleep(250)
    const shot = await cdp.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
    writeFileSync(SCREENSHOT, Buffer.from(shot.data, 'base64'))
    console.log(`RENDERER SMOKE: PASS (6 pages, dark/light theme, screenshot=${SCREENSHOT})`)
  } finally {
    try { cdp?.close() } catch {}
    try { child.kill('SIGTERM') } catch {}
  }
}

main().catch(error => { console.error(`RENDERER SMOKE: FAIL\n${error.stack || error}`); process.exit(1) })
