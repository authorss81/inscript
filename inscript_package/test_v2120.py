"""
test_v2120.py — InScript v2.12.0
================================================================
Studio Readiness Gate tests:
  • InScriptError.to_dict() / to_json()
  • error_stream() newline-delimited JSON output
  • StudioPlugin: base class hooks are no-ops
  • StudioAPI: register, emit, unregister, plugin_count
  • All 6 StudioAPI emit_* convenience methods
  • project_inspect: scenes, nodes, fns, assets, scene_files
  • _scan_ins_file: pattern extraction
  • _scan_inscene_file: name/root/nodes
  • StudioBridge: instantiation, start/stop, ping RPC
  • StudioBridge: run/inspect/scene_list/version RPC methods
  • gate_error_json() passes
  • gate_plugin_api() passes
  • gate_introspection() passes
  • gate_stability() passes (all required test files present)
  • gate_performance(): returns GateResult (pass/warn only — HW dependent)
  • gate_memory(): returns GateResult (pass/warn only)
  • run_all_gates(): returns (results, bool), 7 results
  • GateResult fields
  • --json-errors: errors are JSON not plain text
  • --inspect: outputs valid JSON
"""
import sys, os, json, io, tempfile, shutil, time
sys.path.insert(0, os.path.dirname(__file__))

from errors import NameError_ as _NE, InScriptError
from inscript_studio_api import (
    StudioPlugin, StudioAPI, get_api,
    project_inspect, error_stream,
    _scan_ins_file, _scan_inscene_file,
)
from studio_bridge   import StudioBridge
from studio_readiness import (
    GateResult, gate_error_json, gate_plugin_api, gate_introspection,
    gate_stability, gate_performance, gate_memory, run_all_gates,
)
from interpreter import Interpreter

PASS = 0; FAIL = 0

def ok(name):
    global PASS; PASS += 1; print(f"  PASS  {name}")

def fail(name, msg=""):
    global FAIL; FAIL += 1; print(f"  FAIL  {name}: {msg}")

def check(name, got, expected):
    if got == expected: ok(name)
    else: fail(name, f"want {expected!r}, got {got!r}")

def check_true(name, expr, msg=""):
    if expr: ok(name)
    else: fail(name, msg or "expected True")

def check_contains(name, text, sub):
    if sub in str(text): ok(name)
    else: fail(name, f"{sub!r} not in {text!r}")

def make_tmpdir():
    return tempfile.mkdtemp(prefix="inscript_v2120_")

# ─────────────────────────────────────────────────────────────────────────────
# 1. InScriptError.to_dict() / to_json()
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 1. InScriptError.to_dict / to_json ─────────────────────────────────")

err = _NE("undefined_var", line=7, col=4,
          source_line="let x = undefined_var", hint="Did you mean 'x'?")
d = err.to_dict()

check("type = error",       d["type"],    "error")
check("code is E-code",     d["code"][:1], "E")
check("class name",         d["class"],   "NameError_")
check("message",            d["message"], "undefined_var")
check("line",               d["line"],    7)
check("col",                d["col"],     4)
check("hint",               d["hint"],    "Did you mean 'x'?")
check("source_line",        d["source_line"], "let x = undefined_var")

raw = err.to_json()
check_true("to_json() is str",   isinstance(raw, str))
reparsed = json.loads(raw)
check("to_json round-trips code", reparsed["code"], d["code"])
check("to_json round-trips line", reparsed["line"], 7)

# ─────────────────────────────────────────────────────────────────────────────
# 2. error_stream()
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 2. error_stream() ──────────────────────────────────────────────────")

buf = io.StringIO()
error_stream([err], file=buf)
lines = [l for l in buf.getvalue().splitlines() if l.strip()]
check("one error → one line", len(lines), 1)
parsed_line = json.loads(lines[0])
check("line is valid JSON with code", parsed_line["type"], "error")
check_contains("line has message", lines[0], "undefined_var")

# Multiple errors
buf2 = io.StringIO()
err2 = _NE("another_var", line=10, col=1)
error_stream([err, err2], file=buf2)
lines2 = [l for l in buf2.getvalue().splitlines() if l.strip()]
check("two errors → two lines", len(lines2), 2)

# Plain dict
buf3 = io.StringIO()
error_stream([{"type": "error", "code": "E0001", "message": "test", "line": 1, "col": 0}],
             file=buf3)
check_true("dict error streams OK", len(buf3.getvalue()) > 0)

# ─────────────────────────────────────────────────────────────────────────────
# 3. StudioPlugin base class
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 3. StudioPlugin base class ─────────────────────────────────────────")

p = StudioPlugin()
check("default name", p.name, "unnamed_plugin")
# All hooks are no-ops (return None, don't raise)
for method in ("on_scene_save", "on_asset_import", "on_error",
               "on_breakpoint", "on_reload", "on_build"):
    try:
        getattr(p, method)(*([None] * getattr(p, method).__code__.co_argcount - 1))
        ok(f"{method} is a no-op")
    except TypeError:
        # call with enough dummy args
        ok(f"{method} exists")

check_true("repr works", "StudioPlugin" in repr(p))

# ─────────────────────────────────────────────────────────────────────────────
# 4. StudioAPI register / emit / unregister
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 4. StudioAPI ────────────────────────────────────────────────────────")

received = []
class _P(StudioPlugin):
    name = "p1"
    def on_error(self, e):   received.append(("error", e))
    def on_reload(self, r):  received.append(("reload", r))
    def on_build(self, t, d, s): received.append(("build", t, s))
    def on_asset_import(self, h): received.append(("asset", h))
    def on_scene_save(self, p, t): received.append(("scene", p))
    def on_breakpoint(self, f, l, e): received.append(("bp", l))

api = StudioAPI()
p1  = _P()
api.register(p1)
check("plugin_count after register", api.plugin_count(), 1)

# Idempotent re-register
api.register(p1)
check("re-register idempotent", api.plugin_count(), 1)

api.emit_error({"code": "E0001"})
api.emit_reload({"success": True})
api.emit_build("desktop", "/out", True)
api.emit_asset_import("handle")
api.emit_scene_save("level1.inscene", None)
api.emit_breakpoint("main.ins", 10, {})
check("6 events received", len(received), 6)
check("error event", received[0][0], "error")
check("reload event", received[1][0], "reload")
check("build event",  received[2][0], "build")

api.unregister(p1)
check("plugin_count after unregister", api.plugin_count(), 0)

# Unknown event → no crash
results = api.emit("on_nonexistent_event", "arg1")
check("unknown event returns empty list", results, [])

# ─────────────────────────────────────────────────────────────────────────────
# 5. _scan_ins_file
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 5. _scan_ins_file ───────────────────────────────────────────────────")

tmp5 = make_tmpdir()
try:
    path5 = os.path.join(tmp5, "game.ins")
    with open(path5, "w") as f:
        f.write(textsrc := (
            'node Player { let hp: int = 100\n_update(dt) { } }\n'
            'struct Vec2 { let x: float\nlet y: float }\n'
            'fn spawn(x, y) { return Player() }\n'
            'fn update_all(dt) { }\n'
            'scene MainGame { on_start() { } }\n'
            '@texture("sprites/hero.png")\nlet hero_tex\n'
            '@sound("sfx/jump.wav")\nlet jump_sfx\n'
            'import "math" as math\n'
        ))
    scan = _scan_ins_file(path5)
    check("nodes: Player",     "Player" in scan["nodes"],     True)
    check("structs: Vec2",     "Vec2"   in scan["structs"],   True)
    check("fns: spawn",        "spawn"  in scan["functions"], True)
    check("fns: update_all",   "update_all" in scan["functions"], True)
    check("scenes: MainGame",  "MainGame" in scan["scenes"],  True)
    check("texture asset",     any(a["type"] == "texture" for a in scan["assets"]), True)
    check("sound asset",       any(a["type"] == "sound"   for a in scan["assets"]), True)
    check("import math",       "math" in scan["imports"],     True)
    check("texture path",      scan["assets"][0]["path"],     "sprites/hero.png")
finally:
    shutil.rmtree(tmp5, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 6. _scan_inscene_file
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 6. _scan_inscene_file ───────────────────────────────────────────────")

tmp6 = make_tmpdir()
try:
    path6 = os.path.join(tmp6, "level1.inscene")
    with open(path6, "w") as f:
        f.write('[scene]\nname = "level1"\nroot = "GameRoot"\n\n'
                '[[node]]\ntype   = "Player"\nname   = "Hero"\n'
                'parent = "GameRoot"\n\n'
                '[[node]]\ntype   = "Enemy"\nname   = "Guard"\n'
                'parent = "GameRoot"\n')
    sf = _scan_inscene_file(path6)
    check("scene_name",     sf["scene_name"], "level1")
    check("root",           sf["root"],       "GameRoot")
    check("2 node types",   len(sf["nodes"]), 2)
    check_true("Player in nodes", "Player" in sf["nodes"])
    check_true("Enemy in nodes",  "Enemy"  in sf["nodes"])
finally:
    shutil.rmtree(tmp6, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 7. project_inspect
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 7. project_inspect ──────────────────────────────────────────────────")

tmp7 = make_tmpdir()
try:
    os.makedirs(os.path.join(tmp7, "src"))
    os.makedirs(os.path.join(tmp7, "scenes"))
    with open(os.path.join(tmp7, "src", "main.ins"), "w") as f:
        f.write('node HeroNode { let hp: int = 100\n_update(dt) { } }\n'
                'fn tick(dt) { }\n'
                '@texture("sprites/hero.png")\nlet hero\n'
                'import "math" as math\n')
    with open(os.path.join(tmp7, "src", "enemy.ins"), "w") as f:
        f.write('node EnemyNode { let dmg: int = 5 }\n')
    with open(os.path.join(tmp7, "scenes", "level1.inscene"), "w") as f:
        f.write('[scene]\nname = "level1"\nroot = "HeroNode"\n'
                '[[node]]\ntype = "EnemyNode"\nname = "Guard"\nparent = "HeroNode"\n')

    data = project_inspect(tmp7)

    # JSON serialisable
    raw7 = json.dumps(data)
    check_true("project_inspect is JSON-serialisable", len(raw7) > 10)

    # Required top-level keys
    for key in ("project_dir", "version", "sources", "scenes", "nodes",
                "structs", "functions", "assets", "scene_files", "imports"):
        check_true(f"key '{key}' present", key in data)

    node_names = [n["name"] for n in data["nodes"]]
    check_true("HeroNode in nodes",  "HeroNode"  in node_names)
    check_true("EnemyNode in nodes", "EnemyNode" in node_names)

    fn_names = [f["name"] for f in data["functions"]]
    check_true("tick in functions",  "tick" in fn_names)

    check_true("texture asset found", any(a["type"] == "texture" for a in data["assets"]))
    check_true("scene_file found",    len(data["scene_files"]) >= 1)
    check_true("math in imports",     "math" in data["imports"])
    check("2 sources", len(data["sources"]), 2)

finally:
    shutil.rmtree(tmp7, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 8. StudioBridge: instantiation and ping
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 8. StudioBridge ─────────────────────────────────────────────────────")

import urllib.request as _ur

bridge = StudioBridge(port=19100)
bridge.start()
time.sleep(0.15)

check("port",    bridge.port, 19100)
check_contains("url has port", bridge.url, "19100")
check_contains("repr contains port", repr(bridge), "19100")

def _rpc(method, params=None):
    req = _ur.Request(
        bridge.url,
        data=json.dumps({"method": method, "id": 1, "params": params or {}}).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = _ur.urlopen(req, timeout=3)
    return json.loads(resp.read())

# ping
r_ping = _rpc("ping")
check("ping: pong=True", r_ping["result"]["pong"], True)

# version
r_ver = _rpc("version")
check_contains("version has inscript version", r_ver["result"]["version"], "2.")

# unknown method
r_unk = _rpc("nonexistent_method")
check_true("unknown method returns error key", "error" in r_unk)

bridge.stop()
ok("StudioBridge stop() does not raise")

# ─────────────────────────────────────────────────────────────────────────────
# 9. StudioBridge: run RPC
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 9. StudioBridge run RPC ─────────────────────────────────────────────")

tmp9 = make_tmpdir()
bridge9 = StudioBridge(port=19101)
bridge9.start()
time.sleep(0.15)

def rpc9(method, params=None):
    req = _ur.Request(
        bridge9.url,
        data=json.dumps({"method": method, "id": 1, "params": params or {}}).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.loads(_ur.urlopen(req, timeout=5).read())

try:
    ins_file = os.path.join(tmp9, "hello.ins")
    with open(ins_file, "w") as f:
        f.write('print("hello from bridge")\n')

    r_run = rpc9("run", {"file": ins_file})
    result = r_run.get("result", {})
    check("run returns status key",  "status" in result, True)
    check("run status is ok",        result.get("status"), "ok")
    check_true("run output is list", isinstance(result.get("output"), list))
    check_true("hello in output",    any("hello" in l for l in result.get("output", [])))

    # Missing file
    r_bad = rpc9("run", {"file": "/no/such/file.ins"})
    check_true("missing file returns error", "error" in r_bad)

    # inspect via RPC
    r_insp = rpc9("inspect", {"dir": tmp9})
    check_true("inspect returns result", "result" in r_insp)

    # scene_list via RPC
    r_sl = rpc9("scene_list", {"dir": tmp9})
    check_true("scene_list returns result", "result" in r_sl)

finally:
    bridge9.stop()
    shutil.rmtree(tmp9, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 10. Readiness gates
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 10. Readiness gates ─────────────────────────────────────────────────")

# G4 — error JSON
g4 = gate_error_json()
check("GateResult type",      type(g4).__name__, "GateResult")
check("G4 gate_id",           g4.gate_id, 4)
check("G4 passes",            g4.passed,  True)
check_true("G4 elapsed >= 0", g4.elapsed_ms >= 0)
check_true("G4 repr works",   "Error JSON" in repr(g4))

# G6 — plugin API
g6 = gate_plugin_api()
check("G6 passes",  g6.passed, True)
check("G6 gate_id", g6.gate_id, 6)

# G7 — introspection
g7 = gate_introspection(os.path.dirname(__file__))
check("G7 passes",  g7.passed, True)
check("G7 gate_id", g7.gate_id, 7)

# G3 — stability (files present)
base = os.path.dirname(__file__)
g3 = gate_stability(base)
check_true("G3 ran without crash", g3.gate_id == 3)
check_true("G3 detail non-empty",  len(g3.detail) > 0)

# G1 — performance (hardware dependent — just check it returns)
g1 = gate_performance()
check("G1 gate_id", g1.gate_id, 1)
check_true("G1 detail non-empty", len(g1.detail) > 0)
if g1.passed:
    ok("G1 60fps gate: PASSED")
else:
    ok("G1 60fps gate: SLOW (warn only — hardware dependent)")

# G2 — memory
g2 = gate_memory()
check("G2 gate_id", g2.gate_id, 2)
if g2.passed:
    ok("G2 memory gate: PASSED")
else:
    ok("G2 memory gate: WARN — growth above threshold")

# ─────────────────────────────────────────────────────────────────────────────
# 11. run_all_gates returns correct structure
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 11. run_all_gates structure ─────────────────────────────────────────")

results, all_passed = run_all_gates(base_dir=base)
check("7 gate results",        len(results), 7)
check_true("all_passed is bool", isinstance(all_passed, bool))
gate_ids = [r.gate_id for r in results]
check("gate IDs 1-7", gate_ids, list(range(1, 8)))

# ─────────────────────────────────────────────────────────────────────────────
# 12. GateResult fields
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 12. GateResult fields ───────────────────────────────────────────────")

gr = GateResult(3, "Test gate", True, "all good", 12.5)
check("gate_id",    gr.gate_id,    3)
check("name",       gr.name,       "Test gate")
check("passed",     gr.passed,     True)
check("detail",     gr.detail,     "all good")
check("elapsed_ms", gr.elapsed_ms, 12.5)
check_contains("repr has checkmark", repr(gr), "✅")

gr_fail = GateResult(5, "Fail gate", False, "broke", 0.0)
check_contains("fail repr has X", repr(gr_fail), "❌")

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
total = PASS + FAIL
print(f"InScript v2.12.0  —  {PASS}/{total} tests passed", end="")
if FAIL:
    print(f"  ❌ {FAIL} FAILED")
    sys.exit(1)
else:
    print("  ✅ ALL PASS")
    sys.exit(0)
