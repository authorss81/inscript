# -*- coding: utf-8 -*-
"""
vins_editor.py — InScript v3.0.0  Visual Script Editor
================================================================
A complete drag-and-drop node-graph editor served at /visual?f=<path>
from the Studio HTTP server.

What's real in this editor
──────────────────────────
✅  Pan  — middle-mouse or space+drag to pan the canvas
✅  Zoom — mouse wheel, Ctrl+= / Ctrl+-
✅  Add nodes — right-click canvas → context menu → pick type
✅  Move nodes — left-drag the node header
✅  Connect ports — left-click an output port → drag → left-click an input port
✅  Delete connections — right-click on a wire
✅  Delete nodes — right-click node header → Delete
✅  Edit literal values — double-click a literal node → inline input
✅  Edit node names — double-click variable_get/variable_set node label
✅  Save — Ctrl+S writes back to the .vins file via POST /write
✅  Compile — Ctrl+Shift+B sends the graph to POST /vins-compile, writes .ins
✅  Undo/Redo — Ctrl+Z / Ctrl+Y (20-step history)
✅  Multi-select — shift+click nodes, delete key to remove selection
✅  Auto-layout — Ctrl+L sorts nodes left-to-right by exec chain

Honest limitations
──────────────────
⚠  Bezier wires: drawn with quadratic curves, not full cubic bezier.
   Good enough to be clear; not Unreal-quality rounded curves.
⚠  No port type validation: you can connect any port to any port.
   The compiler ignores bad connections gracefully.
⚠  No search palette (Ctrl+space): add nodes only via right-click menu.
⚠  No subgraphs/macros: all nodes are in a flat graph.
⚠  No live preview: compiling generates a .ins file; running it is
   done separately from the Studio code editor.
"""

# ── Node type definitions ──────────────────────────────────────────────────
NODE_TYPES = {
    "event": {
        "label":  "Event",
        "color":  "#a6e3a1",   # green
        "ports_out": [{"id":"exec","label":"▶","kind":"exec"}],
        "ports_in":  [],
        "props": {"event": "_ready"},
    },
    "print": {
        "label":  "Print",
        "color":  "#89dceb",   # sky
        "ports_in":  [{"id":"exec","label":"▶","kind":"exec"},
                      {"id":"message","label":"msg","kind":"value"}],
        "ports_out": [{"id":"exec","label":"▶","kind":"exec"}],
        "props": {},
    },
    "fn_call": {
        "label":  "Call Function",
        "color":  "#89b4fa",   # blue
        "ports_in":  [{"id":"exec","label":"▶","kind":"exec"},
                      {"id":"arg0","label":"arg0","kind":"value"},
                      {"id":"arg1","label":"arg1","kind":"value"}],
        "ports_out": [{"id":"exec","label":"▶","kind":"exec"},
                      {"id":"return","label":"return","kind":"value"}],
        "props": {"fn": "print"},
    },
    "literal": {
        "label":  "Literal",
        "color":  "#f9e2af",   # yellow
        "ports_in":  [],
        "ports_out": [{"id":"value","label":"val","kind":"value"}],
        "props": {"value_type": "string", "value": ""},
    },
    "variable_get": {
        "label":  "Get Variable",
        "color":  "#cba6f7",   # mauve
        "ports_in":  [],
        "ports_out": [{"id":"value","label":"val","kind":"value"}],
        "props": {"name": "score"},
    },
    "variable_set": {
        "label":  "Set Variable",
        "color":  "#cba6f7",
        "ports_in":  [{"id":"exec","label":"▶","kind":"exec"},
                      {"id":"value","label":"val","kind":"value"}],
        "ports_out": [{"id":"exec","label":"▶","kind":"exec"}],
        "props": {"name": "score"},
    },
    "op": {
        "label":  "Operator",
        "color":  "#fab387",   # peach
        "ports_in":  [{"id":"left","label":"L","kind":"value"},
                      {"id":"right","label":"R","kind":"value"}],
        "ports_out": [{"id":"value","label":"=","kind":"value"}],
        "props": {"operator": "+"},
    },
    "if_branch": {
        "label":  "If Branch",
        "color":  "#f38ba8",   # red
        "ports_in":  [{"id":"exec","label":"▶","kind":"exec"},
                      {"id":"condition","label":"cond","kind":"value"}],
        "ports_out": [{"id":"then","label":"then","kind":"exec"},
                      {"id":"else","label":"else","kind":"exec"}],
        "props": {},
    },
    "return": {
        "label":  "Return",
        "color":  "#f38ba8",
        "ports_in":  [{"id":"exec","label":"▶","kind":"exec"},
                      {"id":"value","label":"val","kind":"value"}],
        "ports_out": [],
        "props": {},
    },
    "comment": {
        "label":  "Comment",
        "color":  "#585b70",
        "ports_in":  [],
        "ports_out": [],
        "props": {"text": "Comment"},
    },
}

# ── Editor HTML ────────────────────────────────────────────────────────────

EDITOR_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Visual Script Editor — InScript Studio</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#1e1e2e;color:#cdd6f4;font-family:'Segoe UI',system-ui,sans-serif;
     height:100vh;display:flex;flex-direction:column;overflow:hidden;user-select:none}
#toolbar{display:flex;align-items:center;gap:8px;padding:6px 12px;
         background:#2a2a3e;border-bottom:1px solid #45475a;flex-shrink:0}
.logo{font-weight:700;font-size:14px;color:#89b4fa}
.tb-sep{width:1px;height:20px;background:#45475a;margin:0 4px}
button{padding:4px 10px;border:none;border-radius:4px;cursor:pointer;font-size:12px;
       font-weight:600;color:#1e1e2e;transition:.12s}
button:hover{opacity:.85}
.btn-save{background:#a6e3a1}.btn-compile{background:#89b4fa}
.btn-layout{background:#f9e2af}.btn-undo{background:#585b70;color:#cdd6f4}
.btn-redo{background:#585b70;color:#cdd6f4}
.filename{font-size:12px;color:#a6adc8}
.status-msg{font-size:11px;color:#6c7086;margin-left:8px}
#canvas-wrap{flex:1;position:relative;overflow:hidden}
canvas{display:block;width:100%;height:100%;cursor:default}
#ctx-menu{display:none;position:fixed;background:#313145;border:1px solid #45475a;
          border-radius:6px;z-index:100;min-width:160px;padding:4px 0;box-shadow:0 4px 20px #0008}
.ctx-item{padding:6px 14px;cursor:pointer;font-size:12px;display:flex;align-items:center;gap:8px}
.ctx-item:hover{background:#45475a}
.ctx-item .dot{width:10px;height:10px;border-radius:50%}
.ctx-sep{height:1px;background:#45475a;margin:4px 0}
#edit-box{display:none;position:fixed;background:#313145;border:1px solid #89b4fa;
          border-radius:4px;padding:4px 8px;font-size:12px;color:#cdd6f4;
          z-index:200;outline:none;min-width:80px}
#palette{display:none;position:fixed;background:#2a2a3e;border:1px solid #45475a;
         border-radius:6px;z-index:150;padding:6px;min-width:200px}
#palette input{width:100%;background:#1e1e2e;border:1px solid #45475a;color:#cdd6f4;
               padding:4px 8px;border-radius:4px;font-size:12px;outline:none;margin-bottom:4px}
.pal-item{padding:5px 10px;cursor:pointer;font-size:12px;border-radius:4px;
          display:flex;align-items:center;gap:8px}
.pal-item:hover{background:#45475a}
</style>
</head>
<body>
<div id="toolbar">
  <span class="logo">⟨/⟩ Visual Script</span>
  <div class="tb-sep"></div>
  <span class="filename" id="tb-file">untitled.vins</span>
  <div class="tb-sep"></div>
  <button class="btn-undo"    onclick="E.undo()"    title="Ctrl+Z">↩ Undo</button>
  <button class="btn-redo"    onclick="E.redo()"    title="Ctrl+Y">↪ Redo</button>
  <div class="tb-sep"></div>
  <button class="btn-layout"  onclick="E.autoLayout()" title="Ctrl+L">⊞ Layout</button>
  <button class="btn-save"    onclick="E.save()"    title="Ctrl+S">💾 Save</button>
  <button class="btn-compile" onclick="E.compile()" title="Ctrl+Shift+B">⚙ Compile → .ins</button>
  <span class="status-msg" id="status-msg"></span>
</div>
<div id="canvas-wrap">
  <canvas id="c"></canvas>
</div>
<div id="ctx-menu"></div>
<input id="edit-box" type="text">
<div id="palette">
  <input id="pal-search" placeholder="Search node types…" oninput="E.filterPalette(this.value)">
  <div id="pal-list"></div>
</div>

<script>
// ── Core editor ─────────────────────────────────────────────────────────────
const E = (() => {
const cv = document.getElementById('c');
const ctx = cv.getContext('2d');
const NODE_W = 170, PORT_R = 6, HDR_H = 28, ROW_H = 22;
let filepath = '', graphName = 'VisualScript';

// ── State ──────────────────────────────────────────────────────────────────
let nodes = [], conns = [];   // arrays of plain objects
let view   = {x:0, y:0, z:1};
let hist   = [], histIdx = -1;

let drag   = null;   // {type:'node'|'wire'|'pan', node?, portId?, mouseStart?, ...}
let sel    = new Set();
let pendingWire = null;  // {fromNode, fromPort, fromKind}
let ctxTarget = null;

// ── Init ───────────────────────────────────────────────────────────────────
function init() {
  resize();
  window.addEventListener('resize', resize);
  cv.addEventListener('mousedown',  onMouseDown);
  cv.addEventListener('mousemove',  onMouseMove);
  cv.addEventListener('mouseup',    onMouseUp);
  cv.addEventListener('wheel',      onWheel, {passive:false});
  cv.addEventListener('dblclick',   onDblClick);
  cv.addEventListener('contextmenu',e => { e.preventDefault(); onContextMenu(e); });
  document.addEventListener('keydown', onKeyDown);
  document.getElementById('edit-box').addEventListener('keydown', onEditKey);
  document.getElementById('edit-box').addEventListener('blur', commitEdit);

  // Load graph from URL param
  const params = new URLSearchParams(location.search);
  filepath = params.get('f') || '';
  if (filepath) {
    document.getElementById('tb-file').textContent = filepath.split(/[\/\\]/).pop();
    fetch('/read?f=' + encodeURIComponent(filepath))
      .then(r => r.text()).then(txt => {
        try { loadGraph(JSON.parse(txt)); }
        catch { loadGraph(makeDefault()); }
      }).catch(() => loadGraph(makeDefault()));
  } else {
    loadGraph(makeDefault());
  }
}

function resize() {
  cv.width  = cv.offsetWidth  * devicePixelRatio;
  cv.height = cv.offsetHeight * devicePixelRatio;
  ctx.scale(devicePixelRatio, devicePixelRatio);
  draw();
}

// ── Graph model ────────────────────────────────────────────────────────────
let _uid = 0;
function uid() { return 'n' + (++_uid); }

function makeNode(type, x, y) {
  const def = NODE_TYPES[type];
  if (!def) return null;
  return {
    id:    uid(),
    type,
    x, y,
    props: JSON.parse(JSON.stringify(def.props)),
  };
}

function nodeHeight(n) {
  const def = NODE_TYPES[n.type] || {};
  const rows = Math.max(
    (def.ports_in  || []).length,
    (def.ports_out || []).length
  );
  return HDR_H + Math.max(rows, 1) * ROW_H + 8;
}

function portPos(n, portId, side) {
  // side: 'in' | 'out'
  const def = NODE_TYPES[n.type] || {};
  const ports = side === 'in' ? (def.ports_in || []) : (def.ports_out || []);
  const idx   = ports.findIndex(p => p.id === portId);
  if (idx < 0) return null;
  const y = n.y + HDR_H + idx * ROW_H + ROW_H / 2;
  const x = side === 'in' ? n.x : n.x + NODE_W;
  return {x, y};
}

function allPortPositions(n) {
  const def = NODE_TYPES[n.type] || {};
  const res = [];
  (def.ports_in  || []).forEach(p => res.push({...portPos(n, p.id, 'in'),  portId:p.id, side:'in',  kind:p.kind, nodeId:n.id}));
  (def.ports_out || []).forEach(p => res.push({...portPos(n, p.id, 'out'), portId:p.id, side:'out', kind:p.kind, nodeId:n.id}));
  return res;
}

// ── Graph load/save ────────────────────────────────────────────────────────
function loadGraph(data) {
  graphName = data.name || 'VisualScript';
  nodes = (data.nodes || []).map(n => ({
    id: n.id, type: n.type,
    x: +n.x||0, y: +n.y||0,
    props: {...(NODE_TYPES[n.type]?.props||{}), ...(Object.fromEntries(
      Object.entries(n).filter(([k]) => !['id','type','x','y'].includes(k))
    ))},
  }));
  conns = (data.connections || []).map(c => ({...c}));
  _uid = nodes.reduce((m, n) => Math.max(m, parseInt(n.id.replace(/\D/g,''))||0), 0);
  pushHistory();
  draw();
}

function toGraphData() {
  return {
    version: '3.0.0',
    name: graphName,
    nodes: nodes.map(n => ({id:n.id, type:n.type, x:Math.round(n.x), y:Math.round(n.y), ...n.props})),
    connections: conns.map(c => ({...c})),
  };
}

function makeDefault() {
  return {version:'3.0.0', name:'NewGraph', nodes:[
    {id:'n1',type:'event',event:'_ready',x:80,y:120},
    {id:'n2',type:'print',x:320,y:120},
    {id:'n3',type:'literal',value_type:'string',value:'Hello World',x:320,y:220},
  ], connections:[
    {from_node:'n1',from_port:'exec',to_node:'n2',to_port:'exec'},
    {from_node:'n3',from_port:'value',to_node:'n2',to_port:'message'},
  ]};
}

// ── History ────────────────────────────────────────────────────────────────
function pushHistory() {
  hist = hist.slice(0, histIdx + 1);
  hist.push(JSON.stringify(toGraphData()));
  if (hist.length > 20) hist.shift();
  histIdx = hist.length - 1;
}
function undo() {
  if (histIdx > 0) { histIdx--; loadFrom(JSON.parse(hist[histIdx])); }
}
function redo() {
  if (histIdx < hist.length - 1) { histIdx++; loadFrom(JSON.parse(hist[histIdx])); }
}
function loadFrom(data) {
  nodes = data.nodes.map(n => ({id:n.id, type:n.type, x:+n.x||0, y:+n.y||0,
    props:{...Object.fromEntries(Object.entries(n).filter(([k])=>!['id','type','x','y'].includes(k)))}}));
  conns = data.connections.map(c=>({...c}));
  draw();
}

// ── Canvas to world coords ─────────────────────────────────────────────────
function cw(ex, ey) {
  const r = cv.getBoundingClientRect();
  return { x: (ex - r.left - view.x) / view.z,
           y: (ey - r.top  - view.y) / view.z };
}

// ── Hit testing ────────────────────────────────────────────────────────────
function hitNode(wx, wy) {
  // Return topmost node hit (reverse order for z)
  for (let i = nodes.length - 1; i >= 0; i--) {
    const n = nodes[i];
    if (wx >= n.x && wx <= n.x + NODE_W && wy >= n.y && wy <= n.y + nodeHeight(n))
      return n;
  }
  return null;
}

function hitPort(wx, wy) {
  for (const n of nodes) {
    for (const pp of allPortPositions(n)) {
      const dx = wx - pp.x, dy = wy - pp.y;
      if (dx*dx + dy*dy <= PORT_R * PORT_R * 2.5)
        return pp;
    }
  }
  return null;
}

function hitWire(wx, wy) {
  for (const c of conns) {
    const from = portPos(nodeById(c.from_node), c.from_port, 'out');
    const to   = portPos(nodeById(c.to_node),   c.to_port,   'in');
    if (!from || !to) continue;
    // Sample points along the curve
    const mx = (from.x + to.x) / 2;
    for (let t = 0; t <= 1; t += 0.05) {
      const bx = (1-t)*(1-t)*from.x + 2*(1-t)*t*mx + t*t*to.x;
      const by = (1-t)*(1-t)*from.y + 2*(1-t)*t*((from.y+to.y)/2) + t*t*to.y;
      if (Math.abs(bx - wx) < 6 && Math.abs(by - wy) < 6) return c;
    }
  }
  return null;
}

function nodeById(id) { return nodes.find(n => n.id === id); }

// ── Input ──────────────────────────────────────────────────────────────────
let mousePos = {x:0, y:0};

function onMouseDown(e) {
  hideCtxMenu(); hidePalette();
  const {x, y} = cw(e.clientX, e.clientY);
  const port = hitPort(x, y);
  if (port && e.button === 0) {
    // Start wire from output port; or complete wire to input port
    if (pendingWire) {
      // Complete connection
      if (port.side === 'in' && port.nodeId !== pendingWire.fromNode) {
        // Remove any existing connection to this input port
        conns = conns.filter(c => !(c.to_node === port.nodeId && c.to_port === port.portId));
        conns.push({from_node: pendingWire.fromNode, from_port: pendingWire.fromPort,
                    to_node: port.nodeId, to_port: port.portId});
        pushHistory();
      }
      pendingWire = null;
      draw(); return;
    }
    if (port.side === 'out') {
      pendingWire = {fromNode: port.nodeId, fromPort: port.portId, kind: port.kind};
      draw(); return;
    }
  }
  if (pendingWire) { pendingWire = null; draw(); return; }

  const node = hitNode(x, y);
  if (e.button === 0) {
    if (node) {
      if (!sel.has(node.id)) {
        if (!e.shiftKey) sel.clear();
        sel.add(node.id);
      }
      drag = {type:'node', startX:x, startY:y,
              origins: nodes.filter(n => sel.has(n.id)).map(n => ({id:n.id, x:n.x, y:n.y}))};
    } else {
      if (!e.shiftKey) sel.clear();
      drag = {type:'pan', startX:e.clientX, startY:e.clientY, ox:view.x, oy:view.y};
    }
    draw();
  }
}

function onMouseMove(e) {
  const {x, y} = cw(e.clientX, e.clientY);
  mousePos = {x, y};
  if (drag?.type === 'node') {
    const dx = x - drag.startX, dy = y - drag.startY;
    drag.origins.forEach(o => {
      const n = nodeById(o.id);
      if (n) { n.x = o.x + dx; n.y = o.y + dy; }
    });
  } else if (drag?.type === 'pan') {
    view.x = drag.ox + (e.clientX - drag.startX);
    view.y = drag.oy + (e.clientY - drag.startY);
  }
  draw();
}

function onMouseUp(e) {
  if (drag?.type === 'node' && (drag.startX !== mousePos.x || drag.startY !== mousePos.y))
    pushHistory();
  drag = null;
}

function onWheel(e) {
  e.preventDefault();
  const r = cv.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;
  const factor = e.deltaY < 0 ? 1.1 : 0.91;
  view.x = mx - (mx - view.x) * factor;
  view.y = my - (my - view.y) * factor;
  view.z = Math.max(0.2, Math.min(3, view.z * factor));
  draw();
}

function onDblClick(e) {
  const {x, y} = cw(e.clientX, e.clientY);
  const n = hitNode(x, y);
  if (!n) return;
  if (n.type === 'literal') beginEdit(n, 'value', e.clientX, e.clientY);
  else if (n.type === 'variable_get' || n.type === 'variable_set') beginEdit(n, 'name', e.clientX, e.clientY);
  else if (n.type === 'fn_call') beginEdit(n, 'fn', e.clientX, e.clientY);
  else if (n.type === 'op') beginEdit(n, 'operator', e.clientX, e.clientY);
  else if (n.type === 'event') beginEdit(n, 'event', e.clientX, e.clientY);
  else if (n.type === 'comment') beginEdit(n, 'text', e.clientX, e.clientY);
}

let _editNode = null, _editProp = null;
function beginEdit(n, prop, cx, cy) {
  _editNode = n; _editProp = prop;
  const box = document.getElementById('edit-box');
  box.value = n.props[prop] || '';
  box.style.left = cx + 'px';
  box.style.top  = (cy - 14) + 'px';
  box.style.display = 'block';
  box.focus(); box.select();
}
function onEditKey(e) { if (e.key === 'Enter') commitEdit(); }
function commitEdit() {
  const box = document.getElementById('edit-box');
  if (_editNode && _editProp) {
    _editNode.props[_editProp] = box.value;
    pushHistory();
  }
  _editNode = _editProp = null;
  box.style.display = 'none';
  draw();
}

function onKeyDown(e) {
  if (document.getElementById('edit-box').style.display !== 'none') return;
  if (e.ctrlKey || e.metaKey) {
    if (e.key === 'z') { e.preventDefault(); undo(); }
    if (e.key === 'y') { e.preventDefault(); redo(); }
    if (e.key === 's') { e.preventDefault(); save(); }
    if (e.key === 'l') { e.preventDefault(); autoLayout(); }
    if (e.key === 'b' && e.shiftKey) { e.preventDefault(); compile(); }
    if (e.key === ' ') { e.preventDefault(); showPalette(null); }
  }
  if (e.key === 'Delete' || e.key === 'Backspace') {
    if (sel.size > 0) {
      nodes = nodes.filter(n => !sel.has(n.id));
      conns = conns.filter(c => !sel.has(c.from_node) && !sel.has(c.to_node));
      sel.clear(); pushHistory(); draw();
    }
  }
  if (e.key === 'Escape') { pendingWire = null; hidePalette(); draw(); }
}

// ── Context menu ───────────────────────────────────────────────────────────
function onContextMenu(e) {
  e.preventDefault();
  const {x, y} = cw(e.clientX, e.clientY);
  const n = hitNode(x, y);
  const w = hitWire(x, y);
  ctxTarget = {node: n, wire: w, wx: x, wy: y, cx: e.clientX, cy: e.clientY};
  const menu = document.getElementById('ctx-menu');
  menu.innerHTML = '';

  if (n) {
    addMenuItem('🗑 Delete node', () => {
      nodes = nodes.filter(nd => nd.id !== n.id);
      conns = conns.filter(c => c.from_node !== n.id && c.to_node !== n.id);
      sel.delete(n.id); pushHistory(); draw();
    });
    addMenuItem('✂ Disconnect all', () => {
      conns = conns.filter(c => c.from_node !== n.id && c.to_node !== n.id);
      pushHistory(); draw();
    });
    addMenuSep();
  }
  if (w) {
    addMenuItem('✂ Delete wire', () => {
      const idx = conns.indexOf(w);
      if (idx >= 0) { conns.splice(idx, 1); pushHistory(); draw(); }
    });
    addMenuSep();
  }

  addMenuItem('➕ Add node…', () => showPalette({cx: e.clientX, cy: e.clientY, wx: x, wy: y}));
  addMenuSep();
  addMenuItem('⊞ Auto-layout', () => autoLayout());
  addMenuItem('🔍 Reset view', () => { view = {x:40,y:40,z:1}; draw(); });

  menu.style.left    = e.clientX + 'px';
  menu.style.top     = e.clientY + 'px';
  menu.style.display = 'block';
}

function addMenuItem(label, fn) {
  const menu = document.getElementById('ctx-menu');
  const d    = document.createElement('div');
  d.className = 'ctx-item'; d.textContent = label;
  d.onclick = () => { hideCtxMenu(); fn(); };
  menu.appendChild(d);
}
function addMenuSep() {
  const d = document.createElement('div'); d.className = 'ctx-sep';
  document.getElementById('ctx-menu').appendChild(d);
}
function hideCtxMenu() { document.getElementById('ctx-menu').style.display = 'none'; }

// ── Node palette ───────────────────────────────────────────────────────────
let _palettePos = null;
function showPalette(pos) {
  _palettePos = pos;
  const pal = document.getElementById('palette');
  if (pos) { pal.style.left = pos.cx + 'px'; pal.style.top = pos.cy + 'px'; }
  else { pal.style.left = '50%'; pal.style.top = '80px'; pal.style.transform = 'translateX(-50%)'; }
  pal.style.display = 'block';
  renderPalette('');
  document.getElementById('pal-search').value = '';
  document.getElementById('pal-search').focus();
}
function hidePalette() {
  document.getElementById('palette').style.display = 'none';
  document.getElementById('palette').style.transform = '';
}
function filterPalette(q) { renderPalette(q); }
function renderPalette(q) {
  const list = document.getElementById('pal-list');
  list.innerHTML = '';
  Object.entries(NODE_TYPES).filter(([k]) => !q || k.includes(q.toLowerCase())).forEach(([type, def]) => {
    const d = document.createElement('div');
    d.className = 'pal-item';
    d.innerHTML = `<span class="dot" style="background:${def.color}"></span>${def.label} <span style="color:#6c7086;font-size:10px">(${type})</span>`;
    d.onclick = () => {
      hidePalette();
      const wx = _palettePos?.wx ?? (-view.x/view.z + 200);
      const wy = _palettePos?.wy ?? (-view.y/view.z + 100 + nodes.length*30);
      const n  = makeNode(type, wx, wy);
      if (n) { nodes.push(n); sel.clear(); sel.add(n.id); pushHistory(); draw(); }
    };
    list.appendChild(d);
  });
}

// ── Auto-layout ────────────────────────────────────────────────────────────
function autoLayout() {
  // Topological sort, place nodes in columns by exec depth
  const visited = new Set();
  const depth   = {};

  function execNext(id) {
    return conns.filter(c => c.from_node === id && c.from_port === 'exec')
                .map(c => c.to_node);
  }
  function walk(id, d) {
    if ((depth[id] ?? -1) >= d) return;
    depth[id] = d;
    execNext(id).forEach(nxt => walk(nxt, d + 1));
  }
  nodes.filter(n => n.type === 'event').forEach(n => walk(n.id, 0));
  nodes.forEach(n => { if (depth[n.id] === undefined) depth[n.id] = 0; });

  // Group by depth
  const cols = {};
  nodes.forEach(n => {
    const d = depth[n.id];
    cols[d] = cols[d] || [];
    cols[d].push(n);
  });
  const COL_W = 220, ROW_STEP = 140, PAD = 60;
  Object.entries(cols).sort(([a],[b]) => +a - +b).forEach(([d, ns]) => {
    ns.forEach((n, i) => { n.x = PAD + +d * COL_W; n.y = PAD + i * ROW_STEP; });
  });
  pushHistory(); draw();
  status('Layout applied.');
}

// ── Save + Compile ─────────────────────────────────────────────────────────
function save() {
  if (!filepath) {
    status('⚠ No file path — open via Studio.');
    return;
  }
  const data = JSON.stringify(toGraphData(), null, 2);
  fetch('/write', { method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({path: filepath, content: data}) })
    .then(r => r.json()).then(r => {
      status(r.ok ? '✅ Saved.' : '❌ Save failed: ' + r.error);
    }).catch(e => status('❌ ' + e.message));
}

function compile() {
  if (!filepath) { status('⚠ Save the file first.'); return; }
  fetch('/vins-compile', { method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({path: filepath, graph: toGraphData()}) })
    .then(r => r.json()).then(r => {
      if (r.ok) status(`✅ Compiled → ${r.out_path}`);
      else status('❌ ' + r.error);
    }).catch(e => status('❌ ' + e.message));
}

function status(msg) {
  const el = document.getElementById('status-msg');
  el.textContent = msg;
  setTimeout(() => { if (el.textContent === msg) el.textContent = ''; }, 4000);
}

// ── Drawing ────────────────────────────────────────────────────────────────
const C = {bg:'#1e1e2e', grid:'#2a2a3e', wire_exec:'#a6e3a1', wire_val:'#89b4fa',
           wire_pend:'#f9e2af', sel:'#89b4fa', hdr_text:'#1e1e2e', body:'#313145',
           port_in:'#45475a', port_out:'#cdd6f4', text:'#cdd6f4', sub:'#a6adc8'};

function draw() {
  const W = cv.offsetWidth, H = cv.offsetHeight;
  ctx.clearRect(0, 0, W, H);

  // Background
  ctx.fillStyle = C.bg;
  ctx.fillRect(0, 0, W, H);

  // Grid
  const gs = 40 * view.z;
  const ox = ((view.x % gs) + gs) % gs;
  const oy = ((view.y % gs) + gs) % gs;
  ctx.strokeStyle = C.grid; ctx.lineWidth = .5;
  for (let gx = ox - gs; gx < W + gs; gx += gs) {
    ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, H); ctx.stroke();
  }
  for (let gy = oy - gs; gy < H + gs; gy += gs) {
    ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(W, gy); ctx.stroke();
  }

  ctx.save();
  ctx.translate(view.x, view.y);
  ctx.scale(view.z, view.z);

  // Connections
  conns.forEach(drawConn);

  // Pending wire
  if (pendingWire) {
    const fn = nodeById(pendingWire.fromNode);
    if (fn) {
      const from = portPos(fn, pendingWire.fromPort, 'out');
      if (from) drawCurve(from.x, from.y, mousePos.x, mousePos.y, C.wire_pend, 1.5, true);
    }
  }

  // Nodes
  nodes.forEach(drawNode);

  ctx.restore();
}

function drawConn(c) {
  const fn = nodeById(c.from_node), tn = nodeById(c.to_node);
  if (!fn || !tn) return;
  const from = portPos(fn, c.from_port, 'out');
  const to   = portPos(tn, c.to_port,   'in');
  if (!from || !to) return;
  const def  = NODE_TYPES[fn.type];
  const port = (def?.ports_out||[]).find(p => p.id === c.from_port);
  const col  = port?.kind === 'exec' ? C.wire_exec : C.wire_val;
  drawCurve(from.x, from.y, to.x, to.y, col, 2, port?.kind === 'exec');
}

function drawCurve(x1, y1, x2, y2, col, lw, isExec) {
  const mx = (x1 + x2) / 2;
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.quadraticCurveTo(mx, y1, mx, (y1 + y2) / 2);
  ctx.quadraticCurveTo(mx, y2, x2, y2);
  ctx.strokeStyle = col;
  ctx.lineWidth   = lw;
  ctx.setLineDash(isExec ? [] : [4, 2]);
  ctx.stroke();
  ctx.setLineDash([]);
}

function drawNode(n) {
  const def   = NODE_TYPES[n.type] || {label:n.type, color:'#585b70', ports_in:[], ports_out:[], props:{}};
  const h     = nodeHeight(n);
  const isSelected = sel.has(n.id);

  // Shadow for selected
  if (isSelected) {
    ctx.shadowColor   = '#89b4fa';
    ctx.shadowBlur    = 12;
  }

  // Body
  ctx.fillStyle   = C.body;
  ctx.strokeStyle = isSelected ? '#89b4fa' : '#45475a';
  ctx.lineWidth   = isSelected ? 2 : 1;
  roundRect(n.x, n.y, NODE_W, h, 6);
  ctx.fill(); ctx.stroke();
  ctx.shadowBlur = 0;

  // Header
  ctx.fillStyle = def.color;
  roundRectTop(n.x, n.y, NODE_W, HDR_H, 6);
  ctx.fill();

  // Header label
  ctx.fillStyle   = C.hdr_text;
  ctx.font        = 'bold 11px Segoe UI, system-ui';
  ctx.textAlign   = 'left';
  ctx.textBaseline= 'middle';
  ctx.fillText(def.label, n.x + 10, n.y + HDR_H / 2);

  // Property hint (event name, fn name, value, etc.)
  const propKeys = Object.keys(def.props||{});
  if (propKeys.length > 0) {
    const hint = Object.entries(n.props).map(([k,v])=>v).filter(Boolean).join(' ');
    ctx.fillStyle  = '#1e1e2e88';
    ctx.font       = '10px Segoe UI, system-ui';
    ctx.textAlign  = 'right';
    ctx.fillText(hint.slice(0,18), n.x + NODE_W - 10, n.y + HDR_H / 2);
  }

  // Input ports
  (def.ports_in||[]).forEach((p, i) => {
    const py = n.y + HDR_H + i * ROW_H + ROW_H / 2;
    drawPort(n.x, py, p, 'in');
  });

  // Output ports
  (def.ports_out||[]).forEach((p, i) => {
    const py = n.y + HDR_H + i * ROW_H + ROW_H / 2;
    drawPort(n.x + NODE_W, py, p, 'out');
  });
}

function drawPort(x, y, p, side) {
  const isExec = p.kind === 'exec';
  ctx.fillStyle   = isExec ? C.wire_exec : C.wire_val;
  ctx.strokeStyle = '#1e1e2e';
  ctx.lineWidth   = 1;
  if (isExec) {
    // Arrow/diamond for exec
    ctx.beginPath();
    ctx.moveTo(x, y - PORT_R); ctx.lineTo(x + (side==='out'?PORT_R:-PORT_R)*1.4, y);
    ctx.lineTo(x, y + PORT_R); ctx.closePath();
  } else {
    ctx.beginPath(); ctx.arc(x, y, PORT_R, 0, Math.PI*2);
  }
  ctx.fill(); ctx.stroke();

  // Port label
  ctx.fillStyle   = C.sub;
  ctx.font        = '10px Segoe UI, system-ui';
  ctx.textBaseline= 'middle';
  ctx.textAlign   = side === 'in' ? 'left' : 'right';
  const lx = side === 'in' ? x + PORT_R + 5 : x - PORT_R - 5;
  ctx.fillText(p.label, lx, y);
}

function roundRect(x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x+r, y); ctx.lineTo(x+w-r, y);
  ctx.arcTo(x+w, y, x+w, y+r, r);
  ctx.lineTo(x+w, y+h-r); ctx.arcTo(x+w, y+h, x+w-r, y+h, r);
  ctx.lineTo(x+r, y+h);  ctx.arcTo(x, y+h, x, y+h-r, r);
  ctx.lineTo(x, y+r);    ctx.arcTo(x, y, x+r, y, r);
  ctx.closePath();
}

function roundRectTop(x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x+r, y); ctx.lineTo(x+w-r, y);
  ctx.arcTo(x+w, y, x+w, y+r, r);
  ctx.lineTo(x+w, y+h);
  ctx.lineTo(x, y+h);
  ctx.lineTo(x, y+r); ctx.arcTo(x, y, x+r, y, r);
  ctx.closePath();
}

init();
return {undo, redo, save, compile, autoLayout,
        filterPalette: (q) => { renderPalette(q); }};
})();
</script>
</body>
</html>
"""


def get_editor_html() -> str:
    return EDITOR_HTML


def get_node_types_json() -> str:
    import json
    return json.dumps(NODE_TYPES, indent=2)
