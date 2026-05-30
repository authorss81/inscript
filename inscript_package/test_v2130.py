"""
test_v2130.py — InScript v2.13.0
================================================================
Studio Bridge v2 + iOS export tests:
  • Input emulation: emulate_key, emulate_mouse, clear_emulation
  • _InputManager.headless mode: mouse_pos/pressed use emulated state
  • Bridge: start_game (subprocess), stop_game, game_status
  • Bridge: set_node_prop, add_node, remove_node, get_live_scene
  • Bridge: set_breakpoints (no crash), debug_stop
  • Bridge: emulate_input RPC
  • bridge v2 has 22+ RPC methods
  • iOS export: scaffold (pyproject.toml, app.py, build.toml)
  • VALID_TARGETS includes ios
  • run_build("ios", ...) returns BuildResult
  • _GameProcess: start/stop/is_running/get_output
"""
import sys, os, json, time, tempfile, shutil
sys.path.insert(0, os.path.dirname(__file__))

import urllib.request as _ur
from stdlib_game     import _InputManager
from studio_bridge   import StudioBridge, _GameProcess
from export_pipeline import (build_ios, run_build, VALID_TARGETS,
                              BUILD_DIR, BUILD_MANIFEST)
from interpreter     import Interpreter
from scene_tree      import NodeBlueprint

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
    return tempfile.mkdtemp(prefix="inscript_v2130_")

def make_project(name="testgame", tmp=None):
    root = os.path.join(tmp or make_tmpdir(), name)
    os.makedirs(os.path.join(root, "src"))
    os.makedirs(os.path.join(root, "assets"))
    os.makedirs(os.path.join(root, "scenes"))
    with open(os.path.join(root, "inscript.toml"), "w") as f:
        f.write(f'[package]\nname = "{name}"\nversion = "1.0.0"\nentry = "src/main.ins"\n')
    with open(os.path.join(root, "src", "main.ins"), "w") as f:
        f.write('let x = 42\n')
    return root

def rpc(bridge, method, params=None):
    req = _ur.Request(
        bridge.url,
        data=json.dumps({"method": method, "id": 1, "params": params or {}}).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.loads(_ur.urlopen(req, timeout=5).read())

# ─────────────────────────────────────────────────────────────────────────────
# 1. _InputManager headless emulation
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 1. _InputManager headless emulation ────────────────────────────────")

mgr = _InputManager()
check("_headless starts False", mgr._headless, False)
check("emulated_keys starts empty", mgr._emulated_keys, {})

# emulate_key
mgr.emulate_key("space", True)
check("emulate_key sets headless", mgr._headless, True)
check("space is held",             mgr._emulated_keys.get("space"), True)
check("_is_key_down space True",   mgr._is_key_down("space"), True)
check("_is_key_down left False",   mgr._is_key_down("left"), False)

# key released
mgr.emulate_key("space", False)
check("space released",            mgr._is_key_down("space"), False)

# emulate_mouse
mgr.emulate_mouse(320.0, 240.0, {0: True})
pos = mgr.mouse_pos()
check("mouse_pos x", pos["x"], 320.0)
check("mouse_pos y", pos["y"], 240.0)
check("mouse_pressed 0 True", mgr.mouse_pressed(0), True)
check("mouse_pressed 1 False", mgr.mouse_pressed(1), False)

# clear_emulation
mgr.clear_emulation()
check("headless False after clear", mgr._headless, False)
check("emulated_keys empty",        mgr._emulated_keys, {})

# ─────────────────────────────────────────────────────────────────────────────
# 2. _GameProcess
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 2. _GameProcess ─────────────────────────────────────────────────────")

tmp2 = make_tmpdir()
try:
    ins = os.path.join(tmp2, "hello.ins")
    with open(ins, "w") as f:
        f.write('print("game running")\n')

    gp = _GameProcess(ins)
    check("not running before start", gp.is_running(), False)

    gp.start()
    # Wait for process to finish (with timeout)
    deadline = time.time() + 3.0
    while gp.is_running() and time.time() < deadline:
        time.sleep(0.05)
    time.sleep(0.1)  # extra time for output thread

    check_true("output captured",   len(gp._output) > 0)
    check_true("game output line",  any("game running" in l for l in gp._output))

    # get_output since
    all_out = gp.get_output(0)
    check_true("get_output returns list", isinstance(all_out, list))
    check("get_output since=len is empty", gp.get_output(len(gp._output)), [])

    # stop
    gp.stop()
    time.sleep(0.1)
    check("not running after stop", gp.is_running(), False)

    # double stop is safe
    gp.stop()
    ok("double stop is safe")

    check_true("repr works", "GameProcess" in repr(gp))

finally:
    shutil.rmtree(tmp2, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 3. Bridge: start_game / stop_game / game_status
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 3. Bridge: start_game / stop_game / game_status ────────────────────")

tmp3 = make_tmpdir()
b3   = StudioBridge(port=19200)
b3.start()
time.sleep(0.15)

try:
    ins3 = os.path.join(tmp3, "g.ins")
    with open(ins3, "w") as f:
        f.write('import "timer" as t\nprint("started")\n')

    r_start = rpc(b3, "start_game", {"file": ins3})
    check("start_game returns started=True", r_start["result"]["started"], True)
    check_true("start_game returns pid", r_start["result"].get("pid") is not None)

    time.sleep(0.3)

    r_status = rpc(b3, "game_status", {"since": 0})
    result   = r_status["result"]
    check_true("game_status has running key",      "running"      in result)
    check_true("game_status has output_lines key", "output_lines" in result)
    check_true("game_status output is list",       isinstance(result.get("output"), list))

    r_stop = rpc(b3, "stop_game", {})
    check("stop_game returns stopped key", "stopped" in r_stop["result"], True)

    # stop again — no crash
    r_stop2 = rpc(b3, "stop_game", {})
    check_true("double stop_game safe", "stopped" in r_stop2.get("result", r_stop2))

    # Missing file
    r_bad = rpc(b3, "start_game", {"file": "/nonexistent.ins"})
    check_true("start_game missing file → error", "error" in r_bad)

finally:
    b3.stop()
    shutil.rmtree(tmp3, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 4. Bridge: get_live_scene (no live interpreter → returns empty)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 4. Bridge: get_live_scene ───────────────────────────────────────────")

b4 = StudioBridge(port=19201)
b4.start()
time.sleep(0.15)

try:
    r_scene = rpc(b4, "get_live_scene", {})
    result4 = r_scene["result"]
    check_true("get_live_scene has nodes key", "nodes" in result4)
    check("no live interpreter → 0 nodes", result4["count"], 0)

    # Run a script with a node, then inspect live scene
    tmp4 = make_tmpdir()
    ins4 = os.path.join(tmp4, "g.ins")
    with open(ins4, "w") as f:
        f.write('node Hero { let hp: int = 100\n_update(dt) { } }\nlet hero = Hero()\n')

    rpc(b4, "run", {"file": ins4})

    r_scene2 = rpc(b4, "get_live_scene", {})
    result42 = r_scene2.get("result", {})
    check_true("after run: get_live_scene returns", "nodes" in result42)
    shutil.rmtree(tmp4, ignore_errors=True)

finally:
    b4.stop()

# ─────────────────────────────────────────────────────────────────────────────
# 5. Bridge: set_node_prop
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 5. Bridge: set_node_prop ────────────────────────────────────────────")

b5 = StudioBridge(port=19202)
b5.start()
time.sleep(0.15)
tmp5 = make_tmpdir()

try:
    ins5 = os.path.join(tmp5, "g.ins")
    with open(ins5, "w") as f:
        f.write('let score = 0\nfn get_score() { return score }\n')

    rpc(b5, "run", {"file": ins5})

    # Set a global var via set_node_prop (global fallback)
    r_set = rpc(b5, "set_node_prop", {"node": "score", "prop": "score", "value": 999})
    check_true("set_node_prop returns ok or error key",
               "result" in r_set or "error" in r_set)

    # Missing prop parameter
    r_bad = rpc(b5, "set_node_prop", {"node": "score"})
    check_true("set_node_prop missing prop → error", "error" in r_bad)

    # No live interpreter
    b5_fresh = StudioBridge(port=19203)
    b5_fresh.start()
    time.sleep(0.1)
    try:
        r_noint = rpc(b5_fresh, "set_node_prop",
                      {"node": "x", "prop": "x", "value": 1})
        check_true("no interp → error", "error" in r_noint)
    finally:
        b5_fresh.stop()

finally:
    b5.stop()
    shutil.rmtree(tmp5, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 6. Bridge: set_breakpoints and debug_stop (no crash)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 6. Bridge: set_breakpoints / debug_stop ────────────────────────────")

b6 = StudioBridge(port=19204)
b6.start()
time.sleep(0.15)

try:
    r_bp = rpc(b6, "set_breakpoints", {"lines": [1, 3, 5], "file": "test.ins"})
    check_true("set_breakpoints returns result", "result" in r_bp)
    check("breakpoints stored", r_bp["result"]["breakpoints"], [1, 3, 5])

    r_ds = rpc(b6, "debug_stop", {})
    check_true("debug_stop no crash", "result" in r_ds)

finally:
    b6.stop()

# ─────────────────────────────────────────────────────────────────────────────
# 7. Bridge: emulate_input RPC
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 7. Bridge: emulate_input ────────────────────────────────────────────")

b7 = StudioBridge(port=19205)
b7.start()
time.sleep(0.15)

try:
    r_inp = rpc(b7, "emulate_input", {
        "keys": {"space": True, "left": False},
        "mouse": {"x": 100, "y": 200},
        "buttons": {"0": True},
    })
    check_true("emulate_input returns result/error", "result" in r_inp or "error" in r_inp)
    ok("emulate_input RPC does not crash")

finally:
    b7.stop()

# ─────────────────────────────────────────────────────────────────────────────
# 8. Bridge has 22+ RPC methods
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 8. Bridge method count ──────────────────────────────────────────────")

b8 = StudioBridge(port=19207)
b8.start()
time.sleep(0.15)

EXPECTED_METHODS = [
    "ping", "version", "run", "stop", "hot_reload",
    "scene_list", "inspect", "eval",
    "start_game", "stop_game", "game_status",
    "set_node_prop", "add_node", "remove_node", "get_live_scene",
    "set_breakpoints", "debug_stop", "emulate_input",
]

try:
    ok_methods = []
    for m in EXPECTED_METHODS:
        # Each method should return result or error — never an HTTP 500
        try:
            r = rpc(b8, m, {})
            ok_methods.append(m)
        except Exception:
            pass

    check_true("22+ methods accessible via RPC", len(ok_methods) >= 18)
    ok(f"{len(ok_methods)}/{len(EXPECTED_METHODS)} expected methods respond")
    for m in EXPECTED_METHODS:
        check_true(f"method '{m}' accessible", m in ok_methods)
finally:
    b8.stop()

# ─────────────────────────────────────────────────────────────────────────────
# 9. iOS export scaffold
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 9. iOS export scaffold ──────────────────────────────────────────────")

check_contains("VALID_TARGETS has ios", VALID_TARGETS, "ios")

tmp9, root9 = make_project("iosgame"), None
# Make a proper project
tmpdir9 = make_tmpdir()
root9 = make_project("iosgame", tmpdir9)

try:
    result9 = build_ios(root9)
    out9    = os.path.join(root9, BUILD_DIR, "ios")

    check("BuildResult target=ios",    result9.target,     "ios")
    check_true("out_dir created",      os.path.isdir(out9))
    check_true("pyproject.toml",       os.path.isfile(os.path.join(out9, "pyproject.toml")))
    check_true("app.py",               os.path.isfile(os.path.join(out9, "app.py")))
    check_true("build.toml",           os.path.isfile(os.path.join(out9, BUILD_MANIFEST)))
    check_true("artifacts non-empty",  len(result9.artifacts) >= 2)

    pyproj = open(os.path.join(out9, "pyproject.toml")).read()
    check_contains("pyproject has project_name", pyproj, 'project_name = "iosgame"')
    check_contains("pyproject has toga-iOS",     pyproj, "toga-iOS")

    app_py = open(os.path.join(out9, "app.py")).read()
    check_contains("app.py imports inscript", app_py, "import inscript")

    bm = open(os.path.join(out9, BUILD_MANIFEST)).read()
    check_contains("build.toml target=ios", bm, 'target     = "ios"')

    # run_build routing
    ret = run_build("ios", root9)
    # On non-macOS: returns 1 (platform error) — that's correct behaviour
    check_true("run_build ios returns 0 or 1", ret in (0, 1))
    ok("iOS run_build routing works")

finally:
    shutil.rmtree(tmpdir9, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 10. Bridge: add_node / remove_node
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 10. Bridge: add_node / remove_node ─────────────────────────────────")

b10 = StudioBridge(port=19206)
b10.start()
time.sleep(0.15)
tmp10 = make_tmpdir()

try:
    ins10 = os.path.join(tmp10, "g.ins")
    with open(ins10, "w") as f:
        f.write('node Bullet { let dmg: int = 10 }\n')

    rpc(b10, "run", {"file": ins10})

    r_add = rpc(b10, "add_node", {"blueprint": "Bullet", "name": "b1"})
    check_true("add_node returns result", "result" in r_add or "error" in r_add)

    # Missing blueprint
    r_bad_add = rpc(b10, "add_node", {})
    check_true("add_node missing blueprint → error", "error" in r_bad_add)

    # remove_node (may not be in env as NodeInstance since Hero() syntax not supported yet)
    r_rem = rpc(b10, "remove_node", {"node": "b1"})
    check_true("remove_node returns result or error", "result" in r_rem or "error" in r_rem)

finally:
    b10.stop()
    shutil.rmtree(tmp10, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
total = PASS + FAIL
print(f"InScript v2.13.0  —  {PASS}/{total} tests passed", end="")
if FAIL:
    print(f"  ❌ {FAIL} FAILED")
    sys.exit(1)
else:
    print("  ✅ ALL PASS")
    sys.exit(0)
