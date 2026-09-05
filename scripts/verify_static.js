'use strict'
const fs = require('fs')
const path = require('path')
const { spawnSync } = require('child_process')
const root = path.resolve(__dirname, '..')
const required = [
  'desktop/main.js','desktop/preload.js','src/renderer/index.html','src/renderer/styles.css','src/renderer/app.js','backend/bridge.py','package.json'
]
for (const rel of required) {
  if (!fs.existsSync(path.join(root, rel))) throw new Error(`missing ${rel}`)
}
for (const rel of ['desktop/main.js','desktop/preload.js','src/renderer/app.js']) {
  const r = spawnSync(process.execPath, ['--check', path.join(root, rel)], { encoding:'utf8' })
  if (r.status !== 0) throw new Error(`${rel} syntax failed:\n${r.stderr}`)
}
const html = fs.readFileSync(path.join(root,'src/renderer/index.html'),'utf8')
if (!html.includes('styles.css') || !html.includes('app.js')) throw new Error('renderer entry is incomplete')
const css = fs.readFileSync(path.join(root,'src/renderer/styles.css'),'utf8')
for (const token of ['--accent: #f59e0b','.sidebar','.titlebar','.card']) if (!css.includes(token)) throw new Error(`missing design token ${token}`)
console.log('STATIC VERIFY: PASS')
