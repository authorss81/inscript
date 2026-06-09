# -*- coding: utf-8 -*-
"""
studio_app.py — InScript v3.0.0  Studio Web App
================================================================
`inscript --studio [--studio-port 8080] [--project-dir .]`

Starts a local HTTP server that serves the full InScript Studio IDE.
Open http://localhost:8080 in any browser.

Architecture
────────────
  Python HTTP server (this file) on port 8080
    GET  /           → Studio HTML SPA
    POST /rpc        → forwards to StudioBridge (port 8765)
    GET  /files      → project file tree JSON
    GET  /read?f=… → read a file
    POST /write      → write a file
    GET  /status     → bridge health

The Studio HTML is a self-contained SPA (no npm, no build step) that uses:
  • CodeMirror 5 (via CDN) for the editor
  • highlight.js (via CDN) for syntax highlighting
  • Vanilla JS — zero framework dependencies

Usage
─────
  inscript --studio                          # uses current dir
  inscript --studio --project-dir my_game/   # specific project
  inscript --studio --studio-port 9090       # custom port
"""

from __future__ import annotations
import os, sys, json, threading, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional
from urllib.parse import urlparse, parse_qs

DEFAULT_STUDIO_PORT = 8080
DEFAULT_BRIDGE_PORT = 8765

# ─────────────────────────────────────────────────────────────────────────────
# Studio HTML — the entire IDE as a single self-contained page
# ─────────────────────────────────────────────────────────────────────────────

_STUDIO_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>InScript Studio</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- CodeMirror -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/theme/material-darker.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/python/python.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/addon/edit/matchbrackets.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/addon/edit/closebrackets.min.js"></script>
<style>
:root {
  --bg:        #1e1e2e; --bg2:  #2a2a3e; --bg3:  #313145;
  --fg:        #cdd6f4; --fg2:  #a6adc8; --fg3:  #6c7086;
  --accent:    #89b4fa; --green:#a6e3a1; --red:  #f38ba8;
  --yellow:    #f9e2af; --teal: #94e2d5; --mauve:#cba6f7;
  --border:    #45475a; --pad:  8px;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg);
       color: var(--fg); height: 100vh; display: flex; flex-direction: column;
       overflow: hidden; font-size: 13px; }

/* ── Top bar ── */
#topbar { display:flex; align-items:center; gap:8px; padding:6px 12px;
          background:var(--bg2); border-bottom:1px solid var(--border);
          min-height:40px; flex-shrink:0; }
#topbar .logo { font-weight:700; font-size:15px; color:var(--accent);
                margin-right:8px; letter-spacing:.5px; }
#topbar .project-name { color:var(--fg2); font-size:12px; }
.spacer { flex:1; }
button { padding:5px 12px; border:none; border-radius:5px; cursor:pointer;
         font-size:12px; font-weight:600; transition:.15s; }
.btn-run    { background:var(--green); color:#1e1e2e; }
.btn-stop   { background:var(--red);   color:#1e1e2e; }
.btn-debug  { background:var(--mauve); color:#1e1e2e; }
.btn-reload { background:var(--yellow);color:#1e1e2e; }
.btn-build  { background:var(--accent);color:#1e1e2e; }
button:hover { opacity:.85; transform:translateY(-1px); }
button:disabled { opacity:.4; cursor:default; transform:none; }
.status-dot { width:8px; height:8px; border-radius:50%; background:var(--fg3); }
.status-dot.running { background:var(--green); box-shadow:0 0 6px var(--green); }
.status-dot.error   { background:var(--red);   box-shadow:0 0 6px var(--red); }

/* ── Main layout ── */
#main { display:flex; flex:1; overflow:hidden; }

/* ── Left sidebar ── */
#sidebar { width:220px; flex-shrink:0; border-right:1px solid var(--border);
           display:flex; flex-direction:column; background:var(--bg2); }
.panel-header { padding:8px 12px; font-weight:600; font-size:11px;
                text-transform:uppercase; letter-spacing:.8px; color:var(--fg3);
                border-bottom:1px solid var(--border); }
#file-tree { flex:1; overflow-y:auto; padding:4px 0; }
.file-item { padding:4px 12px 4px 20px; cursor:pointer; display:flex;
             align-items:center; gap:6px; border-radius:4px; margin:1px 4px; }
.file-item:hover { background:var(--bg3); }
.file-item.active { background:var(--bg3); color:var(--accent); }
.file-icon { font-size:11px; }

/* ── Editor center ── */
#editor-pane { flex:1; display:flex; flex-direction:column; overflow:hidden; }
#editor-tabs { display:flex; background:var(--bg2); border-bottom:1px solid var(--border); }
.tab { padding:6px 16px; cursor:pointer; font-size:12px; color:var(--fg2);
       border-right:1px solid var(--border); white-space:nowrap; }
.tab.active { color:var(--accent); border-bottom:2px solid var(--accent);
              background:var(--bg); }
.tab .close-btn { margin-left:6px; opacity:.5; }
.tab .close-btn:hover { opacity:1; color:var(--red); }
#editor-wrap { flex:1; overflow:hidden; position:relative; }
.CodeMirror { height:100% !important; font-size:13px; line-height:1.5;
              font-family:'JetBrains Mono','Fira Code',monospace; }
#save-indicator { position:absolute; top:8px; right:16px; font-size:11px;
                  color:var(--fg3); pointer-events:none; z-index:10; }

/* ── Right inspector ── */
#inspector { width:240px; flex-shrink:0; border-left:1px solid var(--border);
             display:flex; flex-direction:column; background:var(--bg2); overflow:hidden; }
#scene-tree { flex:1; overflow-y:auto; padding:4px 0; }
.node-item { padding:4px 12px; cursor:pointer; display:flex;
             align-items:center; gap:6px; }
.node-item:hover { background:var(--bg3); }
.node-item.selected { background:var(--bg3); color:var(--teal); }
.node-badge { font-size:10px; background:var(--bg3); padding:1px 5px;
              border-radius:3px; color:var(--fg3); }
#props-panel { border-top:1px solid var(--border); padding:8px; overflow-y:auto;
               max-height:200px; }
.prop-row { display:flex; align-items:center; gap:6px; margin-bottom:4px; }
.prop-label { font-size:11px; color:var(--fg2); flex:0 0 80px; }
.prop-input { flex:1; background:var(--bg); border:1px solid var(--border);
              color:var(--fg); padding:3px 6px; border-radius:4px; font-size:11px; }
.prop-input:focus { outline:none; border-color:var(--accent); }

/* ── Bottom console ── */
#bottom-panel { height:160px; flex-shrink:0; border-top:1px solid var(--border);
                display:flex; flex-direction:column; background:var(--bg2); }
#console-tabs { display:flex; background:var(--bg2); border-bottom:1px solid var(--border); }
.ctab { padding:4px 12px; cursor:pointer; font-size:11px; color:var(--fg3); }
.ctab.active { color:var(--accent); border-bottom:2px solid var(--accent); }
#console-output { flex:1; overflow-y:auto; padding:6px 10px;
                  font-family:'JetBrains Mono','Fira Code',monospace;
                  font-size:11px; line-height:1.6; background:var(--bg); }
.line-out  { color:var(--fg2); }
.line-err  { color:var(--red); }
.line-info { color:var(--teal); }
.line-ok   { color:var(--green); }
</style>
</head>
<body>

<!-- Top bar -->
<div id="topbar">
  <span class="logo">⟨/⟩ InScript Studio</span>
  <span class="project-name" id="project-name">Loading...</span>
  <div class="spacer"></div>
  <div class="status-dot" id="status-dot" title="Game status"></div>
  <button class="btn-run"    id="btn-run"   onclick="runGame()">▶ Run</button>
  <button class="btn-stop"   id="btn-stop"  onclick="stopGame()" disabled>■ Stop</button>
  <button class="btn-debug"  id="btn-debug" onclick="debugGame()">🐛 Debug</button>
  <button class="btn-reload" id="btn-reload" onclick="hotReload()">⟳ Reload</button>
  <div style="width:1px;height:24px;background:var(--border);margin:0 4px"></div>
  <button class="btn-build"  onclick="showBuildMenu()">📦 Build ▾</button>
  <button style="background:var(--mauve)" onclick="newVisualScript()">🔷 New .vins</button>
  <div id="build-menu" style="display:none;position:absolute;top:42px;right:8px;
    background:var(--bg3);border:1px solid var(--border);border-radius:6px;z-index:100;min-width:120px;">
    <div class="file-item" onclick="buildTarget('desktop')">🖥 Desktop</div>
    <div class="file-item" onclick="buildTarget('web')">🌐 Web</div>
    <div class="file-item" onclick="buildTarget('android')">🤖 Android</div>
    <div class="file-item" onclick="buildTarget('ios')">📱 iOS</div>
  </div>
</div>

<!-- Main layout -->
<div id="main">

  <!-- File tree -->
  <div id="sidebar">
    <div class="panel-header">📁 Files</div>
    <div id="file-tree">Loading...</div>
    <div class="panel-header" style="margin-top:auto">🖼 Assets</div>
    <div id="asset-list" style="max-height:120px;overflow-y:auto;padding:4px 0"></div>
  </div>

  <!-- Editor -->
  <div id="editor-pane">
    <div id="editor-tabs">
      <div class="tab active" id="tab-welcome">Welcome</div>
    </div>
    <div id="editor-wrap">
      <div id="save-indicator"></div>
      <textarea id="editor-textarea"></textarea>
    </div>
  </div>

  <!-- Inspector -->
  <div id="inspector">
    <div class="panel-header">🎬 Scene Tree</div>
    <div id="scene-tree"><div style="padding:8px;color:var(--fg3)">Run a game to inspect</div></div>
    <div class="panel-header">🔧 Properties</div>
    <div id="props-panel"><div style="color:var(--fg3);font-size:11px">Select a node</div></div>
  </div>

</div>

<!-- Console -->
<div id="bottom-panel">
  <div id="console-tabs">
    <div class="ctab active" onclick="switchTab(this,'console')">Output</div>
    <div class="ctab" onclick="switchTab(this,'errors')">Errors</div>
    <div class="ctab" onclick="switchTab(this,'debug')">Debug</div>
  </div>
  <div id="console-output">
    <div class="line-info">InScript Studio v3.0.0 — ready.</div>
    <div class="line-info">⚠ Game preview: pygame games open a native OS window — stdout is captured here.</div>
    <div class="line-info">ℹ Scene inspector works in ▶ Run mode (interpreter). For subprocess games, see docs.</div>
  </div>
</div>

<script>
// ── State ──────────────────────────────────────────────────────────────────
const S = {
  projectDir: '.',
  openFile:   null,
  gameRunning: false,
  outputPoll: null,
  outputSince: 0,
  selectedNode: null,
};

// ── Boot ───────────────────────────────────────────────────────────────────
let editor;
window.addEventListener('load', async () => {
  editor = CodeMirror.fromTextArea(document.getElementById('editor-textarea'), {
    mode: 'python', theme: 'material-darker', lineNumbers: true,
    matchBrackets: true, autoCloseBrackets: true, indentUnit: 4,
    tabSize: 4, indentWithTabs: false, lineWrapping: false,
  });
  editor.on('change', () => {
    document.getElementById('save-indicator').textContent = '● unsaved';
  });
  // Ctrl+S → save
  editor.setOption('extraKeys', {
    'Ctrl-S': () => saveFile(),
    'Cmd-S':  () => saveFile(),
  });

  await refreshAll();
  log('info', 'Project loaded. Press ▶ Run or open a .ins file.');
});

// ── API helpers ────────────────────────────────────────────────────────────
async function rpc(method, params={}) {
  try {
    const r = await fetch('/rpc', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({method, params, id: Date.now()})
    });
    return await r.json();
  } catch(e) { return {error: e.message}; }
}

async function getFiles() {
  try {
    const r = await fetch('/files');
    return await r.json();
  } catch { return []; }
}

async function readFile(path) {
  try {
    const r = await fetch('/read?f=' + encodeURIComponent(path));
    return await r.text();
  } catch { return ''; }
}

async function writeFile(path, content) {
  try {
    await fetch('/write', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({path, content})
    });
  } catch {}
}

// ── Refresh ────────────────────────────────────────────────────────────────
async function refreshAll() {
  await Promise.all([refreshFiles(), refreshInspect()]);
}

async function refreshFiles() {
  const files = await getFiles();
  const tree  = document.getElementById('file-tree');
  if (!files.length) { tree.innerHTML = '<div style="padding:8px;color:var(--fg3)">No .ins files found</div>'; return; }
  tree.innerHTML = files.map(f => `
    <div class="file-item ${S.openFile===f?'active':''}" onclick="openFile('${f.replace(/\\/g,'/')}')">
      <span class="file-icon">${f.endsWith('.ins')?'📄':f.endsWith('.inscene')?'🎬':f.endsWith('.vins')?'🔷':f.endsWith('.toml')?'⚙':'📎'}</span>
      <span>${f.split(/[\/\\]/).pop()}</span>
      ${f.endsWith('.vins') ? '<span style="font-size:10px;color:var(--mauve);margin-left:auto">VS</span>' : ''}
    </div>`).join('');
}

async function refreshInspect() {
  const r = await rpc('inspect', {dir: S.projectDir});
  if (!r.result) return;
  const data = r.result;
  document.getElementById('project-name').textContent = data.project_dir.split(/[\/\\]/).pop();

  const assetList = document.getElementById('asset-list');
  assetList.innerHTML = (data.assets||[]).map(a =>
    `<div class="file-item" title="${a.path}"><span>${a.type==='texture'?'🖼':a.type==='sound'?'🔊':a.type==='tilemap'?'🗺':'📝'}</span><span>${a.path.split('/').pop()}</span></div>`
  ).join('') || '<div style="padding:8px;color:var(--fg3)">No assets</div>';
}

// ── File ops ───────────────────────────────────────────────────────────────
async function openFile(path) {
  S.openFile = path;
  // .vins files → open in visual editor (new tab)
  if (path.endsWith('.vins')) {
    window.open('/visual?f=' + encodeURIComponent(path), '_blank');
    refreshFiles();
    return;
  }
  const content = await readFile(path);
  editor.setValue(content);
  editor.clearHistory();
  document.getElementById('save-indicator').textContent = '';
  document.getElementById('tab-welcome').textContent = path.split(/[\/\\]/).pop();
  document.getElementById('tab-welcome').title = path;
  refreshFiles();
}

async function saveFile() {
  if (!S.openFile) return;
  const content = editor.getValue();
  await writeFile(S.openFile, content);
  document.getElementById('save-indicator').textContent = '✓ saved';
  setTimeout(() => { document.getElementById('save-indicator').textContent = ''; }, 2000);
  log('info', `Saved ${S.openFile}`);
}

// ── Game controls ──────────────────────────────────────────────────────────
async function runGame() {
  const file = S.openFile || await getEntryPoint();
  if (!file) { log('err', 'No .ins file open. Open a file first.'); return; }
  log('info', `Starting ${file}…`);
  S.outputSince = 0;
  const r = await rpc('start_game', {file: file});
  if (r.error) { log('err', r.error); return; }
  S.gameRunning = true;
  document.getElementById('status-dot').className = 'status-dot running';
  document.getElementById('btn-run').disabled = true;
  document.getElementById('btn-stop').disabled = false;
  log('ok', `Game started (pid ${r.result.pid})`);
  startOutputPoll();
}

async function stopGame() {
  clearInterval(S.outputPoll);
  const r = await rpc('stop_game', {});
  S.gameRunning = false;
  document.getElementById('status-dot').className = 'status-dot';
  document.getElementById('btn-run').disabled = false;
  document.getElementById('btn-stop').disabled = true;
  log('info', 'Game stopped.');
  refreshSceneTree();
}

async function debugGame() {
  const file = S.openFile;
  if (!file) { log('err', 'Open a .ins file to debug.'); return; }
  log('info', `Debug run: ${file}`);
  await rpc('set_breakpoints', {lines: [], file});
  const r = await rpc('debug_run', {file});
  if (r.error) log('err', r.error);
  else log('ok', 'Debug session started.');
}

async function hotReload() {
  const file = S.openFile;
  if (!file) { log('info', 'No file open.'); return; }
  await saveFile();
  const r = await rpc('hot_reload', {file});
  if (r.error) { log('err', `Reload error: ${r.error}`); return; }
  const res = r.result || {};
  if (res.success) log('ok', `Hot reload ✅ patched: [${(res.patched||[]).join(', ')}]  ${res.elapsed_ms?.toFixed(1)}ms`);
  else log('err', `Reload failed: ${(res.errors||[]).join(', ')}`);
  refreshSceneTree();
}

function startOutputPoll() {
  S.outputPoll = setInterval(async () => {
    const r = await rpc('game_status', {since: S.outputSince});
    if (!r.result) return;
    const res = r.result;
    (res.output || []).forEach(line => { S.outputSince++; log('out', line); });
    if (!res.running && S.gameRunning) {
      S.gameRunning = false;
      clearInterval(S.outputPoll);
      document.getElementById('status-dot').className = 'status-dot';
      document.getElementById('btn-run').disabled = false;
      document.getElementById('btn-stop').disabled = true;
      log('info', '— game exited —');
      refreshSceneTree();
    }
  }, 300);
}

// ── Scene tree ─────────────────────────────────────────────────────────────
async function refreshSceneTree() {
  const r = await rpc('get_live_scene', {});
  if (!r.result || !r.result.nodes.length) {
    document.getElementById('scene-tree').innerHTML = '<div style="padding:8px;color:var(--fg3)">No live nodes</div>';
    return;
  }
  document.getElementById('scene-tree').innerHTML = r.result.nodes.map(n => `
    <div class="node-item ${S.selectedNode===n.name?'selected':''}" onclick="selectNode('${n.name}','${n.blueprint}')">
      <span>🔷</span><span>${n.name}</span>
      <span class="node-badge">${n.blueprint}</span>
    </div>`).join('');
}

async function selectNode(name, blueprint) {
  S.selectedNode = name;
  const r = await rpc('get_live_scene', {});
  if (!r.result) return;
  const node = r.result.nodes.find(n => n.name === name);
  if (!node) return;
  const props = node.props || {};
  const panel = document.getElementById('props-panel');
  if (!Object.keys(props).length) { panel.innerHTML = '<div style="color:var(--fg3);font-size:11px">No properties</div>'; return; }
  panel.innerHTML = Object.entries(props).map(([k,v]) => `
    <div class="prop-row">
      <span class="prop-label">${k}</span>
      <input class="prop-input" value="${v}" onchange="setProp('${name}','${k}',this.value)" />
    </div>`).join('');
  document.querySelectorAll('.node-item').forEach(el => el.classList.remove('selected'));
  refreshSceneTree();
}

async function setProp(node, prop, value) {
  const numVal = parseFloat(value);
  const v = isNaN(numVal) ? value : numVal;
  const r = await rpc('set_node_prop', {node, prop, value: v});
  if (r.error) log('err', `set_node_prop: ${r.error}`);
  else log('info', `${node}.${prop} = ${v}`);
}

// ── Build ──────────────────────────────────────────────────────────────────
function showBuildMenu() {
  const m = document.getElementById('build-menu');
  m.style.display = m.style.display === 'none' ? 'block' : 'none';
}
document.addEventListener('click', e => {
  if (!e.target.closest('#build-menu') && !e.target.textContent.includes('Build'))
    document.getElementById('build-menu').style.display = 'none';
});

async function buildTarget(target) {
  document.getElementById('build-menu').style.display = 'none';
  log('info', `Building for ${target}… (check output below)`);
  const r = await rpc('build', {target, project_dir: S.projectDir});
  if (r.error) { log('err', `Build error: ${r.error}`); return; }
  log('ok', `Build started for ${target}. Polling output…`);
  // Poll build output
  let since = 0;
  const poll = setInterval(async () => {
    const br = await rpc('build_status', {target, since});
    if (!br.result) { clearInterval(poll); return; }
    const res = br.result;
    (res.output || []).forEach(l => { since++; log('out', l); });
    if (!res.running) {
      clearInterval(poll);
      const last = (res.output || []).slice(-1)[0] || '';
      if (last.includes('exit 0')) log('ok', `✅ ${target} build complete.`);
      else log('err', `❌ ${target} build failed. Check output above.`);
    }
  }, 500);
}

// ── Console ────────────────────────────────────────────────────────────────
function log(type, msg) {
  const el = document.getElementById('console-output');
  const cls = {out:'line-out', err:'line-err', info:'line-info', ok:'line-ok'}[type] || 'line-out';
  const div = document.createElement('div');
  div.className = cls;
  div.textContent = msg;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

function switchTab(el, tab) {
  document.querySelectorAll('.ctab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
}

// ── Helpers ────────────────────────────────────────────────────────────────
async function getEntryPoint() {
  const files = await getFiles();
  const main = files.find(f => f.endsWith('main.ins'));
  return main || files[0] || null;
}

async function newVisualScript() {
  const name  = prompt('Visual script name (e.g. PlayerLogic):');
  if (!name) return;
  const fname = name.replace(/[^a-zA-Z0-9_]/g,'') + '.vins';
  const tmpl  = JSON.stringify({
    version:'3.9.3', name,
    nodes:[
      {id:'n1',type:'event',event:'_ready',x:80,y:120},
      {id:'n2',type:'print',x:320,y:120},
      {id:'n3',type:'literal',value_type:'string',value:'Hello from '+name,x:320,y:220},
    ],
    connections:[
      {from_node:'n1',from_port:'exec',to_node:'n2',to_port:'exec'},
      {from_node:'n3',from_port:'value',to_node:'n2',to_port:'message'},
    ]
  }, null, 2);
  await writeFile('src/' + fname, tmpl);
  log('ok', `Created src/${fname} — opening visual editor…`);
  await refreshFiles();
  window.open('/visual?f=' + encodeURIComponent('src/' + fname), '_blank');
}
</script>
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# HTTP handler
# ─────────────────────────────────────────────────────────────────────────────

class _StudioHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path

        if path in ("/", "/index.html"):
            self._send_html(_STUDIO_HTML)

        elif path == "/visual":
            # v3.0.0: Drag-and-drop visual script editor
            from vins_editor import get_editor_html
            self._send_html(get_editor_html())

        elif path == "/node-types":
            from vins_editor import get_node_types_json
            self._send(200, get_node_types_json().encode(), "application/json")

        elif path == "/files":
            files = self.server._app._get_file_list()
            self._send_json(files)

        elif path == "/read":
            params = parse_qs(parsed.query)
            fpath  = params.get("f", [""])[0]
            self._send_file_content(fpath)

        elif path == "/status":
            self._send_json({"ok": True, "version": "3.9.3",
                             "bridge_port": self.server._app._bridge_port})

        else:
            self._send(404, b"Not found", "text/plain")

    def do_POST(self):
        length  = int(self.headers.get("Content-Length", 0))
        body    = self.rfile.read(length)

        if self.path == "/rpc":
            # Forward to StudioBridge
            result = self.server._app._forward_rpc(body)
            self._send_json_raw(result)

        elif self.path == "/write":
            try:
                data    = json.loads(body)
                fpath   = data.get("path", "")
                content = data.get("content", "")
                full    = self.server._app._resolve(fpath)
                os.makedirs(os.path.dirname(full), exist_ok=True)
                with open(full, "w", encoding="utf-8") as f:
                    f.write(content)
                self._send_json({"ok": True})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)})

        elif self.path == "/vins-compile":
            # v3.0.0: compile graph JSON → .ins and write to disk
            try:
                data     = json.loads(body)
                vins_path = data.get("path", "")
                graph_data = data.get("graph", {})
                if not vins_path:
                    self._send_json({"ok": False, "error": "No path provided"})
                    return
                from visual_script import VinsGraph, VisualScriptCompiler
                graph    = VinsGraph(graph_data)
                compiler = VisualScriptCompiler(graph)
                source   = compiler.compile()
                out_path = os.path.splitext(
                    self.server._app._resolve(vins_path))[0] + ".ins"
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(source)
                # Return relative path for display
                rel_out = os.path.relpath(
                    out_path, self.server._app._project_dir)
                self._send_json({
                    "ok":       True,
                    "out_path": rel_out,
                    "errors":   compiler.errors,
                    "chars":    len(source),
                })
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)})

        else:
            self._send(404, b"Not found", "text/plain")

    def _send_html(self, html: str):
        self._send(200, html.encode(), "text/html; charset=utf-8")

    def _send_json(self, obj):
        self._send_json_raw(json.dumps(obj).encode())

    def _send_json_raw(self, raw: bytes):
        self._send(200, raw, "application/json")

    def _send_file_content(self, fpath: str):
        try:
            full = self.server._app._resolve(fpath)
            with open(full, encoding="utf-8") as f:
                self._send(200, f.read().encode(), "text/plain; charset=utf-8")
        except Exception:
            self._send(404, b"", "text/plain")

    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


# ─────────────────────────────────────────────────────────────────────────────
# StudioApp
# ─────────────────────────────────────────────────────────────────────────────

class StudioApp:
    """
    Orchestrates the Studio web UI + StudioBridge together.
    """
    def __init__(self, project_dir: str = ".",
                 studio_port: int = DEFAULT_STUDIO_PORT,
                 bridge_port: int = DEFAULT_BRIDGE_PORT):
        self._project_dir = os.path.abspath(project_dir)
        self._studio_port = studio_port
        self._bridge_port = bridge_port
        self._server:  Optional[HTTPServer]   = None
        self._bridge   = None
        self._thread:  Optional[threading.Thread] = None

    # ── lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> "StudioApp":
        """Start both the bridge and the Studio HTTP server."""
        from studio_bridge import StudioBridge
        self._bridge = StudioBridge(port=self._bridge_port)
        self._bridge.start()

        self._server = HTTPServer(("localhost", self._studio_port), _StudioHandler)
        self._server._app = self
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        if self._server:
            self._server.shutdown()
        if self._bridge:
            self._bridge.stop()

    @property
    def url(self) -> str:
        return f"http://localhost:{self._studio_port}"

    # ── file system ───────────────────────────────────────────────────────────

    def _resolve(self, rel_path: str) -> str:
        full = os.path.normpath(os.path.join(self._project_dir, rel_path))
        if not full.startswith(self._project_dir):
            raise PermissionError("Path traversal denied")
        return full

    def _get_file_list(self) -> list:
        result = []
        for root, dirs, files in os.walk(self._project_dir):
            dirs[:] = [d for d in dirs
                       if d not in ("build", "__pycache__", "inscript_runtime")
                       and not d.startswith(".")]
            for fn in sorted(files):
                if fn.endswith((".ins", ".inscene", ".vins", ".toml")):
                    full = os.path.join(root, fn)
                    result.append(os.path.relpath(full, self._project_dir))
        return sorted(result)

    # ── bridge RPC proxy ──────────────────────────────────────────────────────

    def _forward_rpc(self, body: bytes) -> bytes:
        if self._bridge is None:
            return json.dumps({"error": "Bridge not started"}).encode()
        try:
            req_data = json.loads(body)
            method   = req_data.get("method", "")
            params   = req_data.get("params", {})
            req_id   = req_data.get("id")
            # Inject project dir for context-sensitive methods
            if method in ("inspect", "scene_list") and "dir" not in params:
                params["dir"] = self._project_dir
            result = self._bridge._dispatch(method, params)
            return json.dumps({"result": result, "id": req_id},
                              default=str).encode()
        except Exception as e:
            return json.dumps({"error": str(e), "id": None}).encode()

    def __repr__(self):
        return f"<StudioApp url={self.url} project={self._project_dir}>"
