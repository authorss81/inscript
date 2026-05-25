"""
test_v290.py — InScript v2.9.0
================================================================
Hot Reload tests:
  • HotReloader.start() — initial load
  • HotReloader.tick() — no-change: returns changed=False
  • Function patching: updated fn body is live after reload
  • State preservation: let var values survive reload
  • Struct patching: struct methods updated, instances keep fields
  • node patching: NodeBlueprint re-registered
  • @hot_reload: stable fn NOT re-patched on reload
  • on_reload() hook called after successful reload
  • Syntax error: errors reported, old code keeps running
  • ReloadResult fields (changed, success, patched, restored, errors, elapsed_ms)
  • HotReloader.reload_count increments
  • _collect_declared_names utility
  • _snapshot_globals / _restore_snapshot isolation

All tests run without a game window.
"""
import sys, os, time, tempfile, shutil
sys.path.insert(0, os.path.dirname(__file__))

from interpreter import Interpreter
from hot_reload  import (HotReloader, ReloadResult,
                          _collect_declared_names, _snapshot_globals)

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

def check_contains(name, collection, item):
    if item in collection: ok(name)
    else: fail(name, f"{item!r} not in {collection!r}")

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_tmpdir():
    return tempfile.mkdtemp(prefix="inscript_v290_")

def write_ins(path, source):
    with open(path, "w", encoding="utf-8") as f:
        f.write(source)
    # Ensure a new mtime (filesystem resolution may be 1s on some systems)
    t = time.time() + 1
    os.utime(path, (t, t))

# ─────────────────────────────────────────────────────────────────────────────
# 1. start() — initial load
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 1. start() initial load ────────────────────────────────────────────")

tmp = make_tmpdir()
try:
    src_path = os.path.join(tmp, "game.ins")
    write_ins(src_path, "let x = 42\nfn add(a, b) { return a + b }")

    interp = Interpreter()
    rl = HotReloader(src_path, interp)
    result = rl.start()

    check("start returns ReloadResult",  type(result).__name__, "ReloadResult")
    check("start: changed=True",         result.changed,  True)
    check("start: success=True",         result.success,  True)
    check("start: no errors",            result.errors,   [])
    check_true("start: elapsed_ms >= 0", result.elapsed_ms >= 0)
    check("reload_count after start",    rl.reload_count, 1)

    # Variables and functions defined
    x_val = interp._globals._store.get("x")
    check("x defined after start",       x_val, 42)
    check_true("add defined after start", "add" in interp._globals._store)

finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 2. tick() — no change
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 2. tick() — no change ──────────────────────────────────────────────")

tmp2 = make_tmpdir()
try:
    src = os.path.join(tmp2, "g.ins")
    write_ins(src, "let score = 0")
    rl2 = HotReloader(src, Interpreter())
    rl2.start()

    r_nochg = rl2.tick()
    check("no change: changed=False",  r_nochg.changed,  False)
    check("no change: success=True",   r_nochg.success,  True)
    check("reload_count unchanged",    rl2.reload_count, 1)

finally:
    shutil.rmtree(tmp2, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 3. Function patching
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 3. Function patching ───────────────────────────────────────────────")

tmp3 = make_tmpdir()
try:
    src3 = os.path.join(tmp3, "g.ins")
    write_ins(src3, "fn greet() { return \"hello\" }")

    interp3 = Interpreter()
    rl3 = HotReloader(src3, interp3)
    rl3.start()

    greet_v1 = interp3._globals._store.get("greet")
    check_true("greet v1 defined", greet_v1 is not None)
    val_v1 = interp3._call_fn(greet_v1, [])
    check("greet v1 returns 'hello'", val_v1, "hello")

    # Modify the source
    write_ins(src3, "fn greet() { return \"world\" }")
    r3 = rl3.tick()
    check("fn patch: changed=True",  r3.changed, True)
    check("fn patch: success=True",  r3.success, True)
    check_contains("fn patch: greet in patched", r3.patched, "greet")

    greet_v2 = interp3._globals._store.get("greet")
    val_v2 = interp3._call_fn(greet_v2, [])
    check("greet v2 returns 'world' (patched)", val_v2, "world")

finally:
    shutil.rmtree(tmp3, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 4. State preservation — let var survives reload
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 4. State preservation ──────────────────────────────────────────────")

tmp4 = make_tmpdir()
try:
    src4 = os.path.join(tmp4, "g.ins")
    write_ins(src4, "let score = 0\nfn add_score(n) { score = score + n }")

    interp4 = Interpreter()
    rl4 = HotReloader(src4, interp4)
    rl4.start()

    # Simulate gameplay: increment score
    interp4._globals.set("score", 150)
    check("score set to 150", interp4._globals._store.get("score"), 150)

    # Reload with changed fn body — score should survive
    write_ins(src4, "let score = 0\nfn add_score(n) { score = score + n * 2 }")
    r4 = rl4.tick()
    check("state preserved: reload success", r4.success, True)

    score_after = interp4._globals._store.get("score")
    check("score 150 preserved after reload", score_after, 150)

    # New fn body doubles n
    add_fn = interp4._globals._store.get("add_score")
    interp4._call_fn(add_fn, [10])
    check("new add_score doubles n (10*2=20 → 170)", interp4._globals._store.get("score"), 170)

finally:
    shutil.rmtree(tmp4, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 5. @hot_reload — stable fn not re-patched
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 5. @hot_reload stable fn ───────────────────────────────────────────")

tmp5 = make_tmpdir()
try:
    src5 = os.path.join(tmp5, "g.ins")
    v1_src = "@hot_reload\nfn stable() { return 99 }\nfn regular() { return 1 }"
    write_ins(src5, v1_src)

    interp5 = Interpreter()
    rl5 = HotReloader(src5, interp5)
    rl5.start()

    stable_v1 = interp5._globals._store.get("stable")
    val_stable_v1 = interp5._call_fn(stable_v1, [])
    check("stable() v1 returns 99", val_stable_v1, 99)

    # Change source: both fns modified
    v2_src = "@hot_reload\nfn stable() { return 999 }\nfn regular() { return 2 }"
    write_ins(src5, v2_src)
    r5 = rl5.tick()

    # regular() should be patched
    reg_fn = interp5._globals._store.get("regular")
    check("regular() v2 = 2 (patched)", interp5._call_fn(reg_fn, []), 2)

    # stable() should NOT be patched — still returns 99
    stable_v2 = interp5._globals._store.get("stable")
    check("stable() still 99 (not patched by @hot_reload)",
          interp5._call_fn(stable_v2, []), 99)

    check_true("stable NOT in patched list", "stable" not in r5.patched)
    check_contains("regular IS in patched list", r5.patched, "regular")

finally:
    shutil.rmtree(tmp5, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 6. on_reload() hook
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 6. on_reload() hook ────────────────────────────────────────────────")

tmp6 = make_tmpdir()
try:
    src6 = os.path.join(tmp6, "g.ins")
    write_ins(src6, "let reloads = 0\nfn on_reload() { reloads = reloads + 1 }")

    interp6 = Interpreter()
    rl6 = HotReloader(src6, interp6)
    rl6.start()

    # First tick: no change
    rl6.tick()
    check("reloads still 0 on no-change tick", interp6._globals._store.get("reloads"), 0)

    # Trigger a reload
    write_ins(src6, "let reloads = 0\nfn on_reload() { reloads = reloads + 1 }\nfn noop() { }")
    r6 = rl6.tick()
    check("on_reload() called: reloads = 1", interp6._globals._store.get("reloads"), 1)

    # Second reload
    write_ins(src6, "let reloads = 0\nfn on_reload() { reloads = reloads + 1 }\nfn noop2() { }")
    rl6.tick()
    check("on_reload() called again: reloads = 2", interp6._globals._store.get("reloads"), 2)

finally:
    shutil.rmtree(tmp6, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 7. Syntax error — old code keeps running
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 7. Syntax error — old code keeps running ───────────────────────────")

tmp7 = make_tmpdir()
try:
    src7 = os.path.join(tmp7, "g.ins")
    write_ins(src7, "fn safe() { return 42 }")

    interp7 = Interpreter()
    rl7 = HotReloader(src7, interp7)
    rl7.start()

    safe_v1 = interp7._globals._store.get("safe")
    check("safe() v1 = 42", interp7._call_fn(safe_v1, []), 42)

    # Write broken source
    write_ins(src7, "fn safe( { BROKEN SYNTAX !!!")
    r7 = rl7.tick()
    check("broken reload: success=False",  r7.success, False)
    check_true("broken reload: errors non-empty", len(r7.errors) > 0)

    # Old fn still works
    safe_still = interp7._globals._store.get("safe")
    check("safe() still 42 after broken reload", interp7._call_fn(safe_still, []), 42)

finally:
    shutil.rmtree(tmp7, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 8. Node blueprint patching
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 8. Node blueprint patching ─────────────────────────────────────────")

tmp8 = make_tmpdir()
try:
    src8 = os.path.join(tmp8, "g.ins")
    write_ins(src8, "node Enemy { let hp: int = 10\n_update(dt) { hp = hp - 1 } }")

    interp8 = Interpreter()
    rl8 = HotReloader(src8, interp8)
    rl8.start()

    from scene_tree import NodeBlueprint
    bp_v1 = interp8._globals._store.get("Enemy")
    check_true("Enemy blueprint registered", isinstance(bp_v1, NodeBlueprint))

    # Patch: new hp default
    write_ins(src8, "node Enemy { let hp: int = 50\n_update(dt) { hp = hp - 2 } }")
    r8 = rl8.tick()
    check("node patch: success", r8.success, True)
    check_contains("Enemy in patched", r8.patched, "Enemy")

    bp_v2 = interp8._globals._store.get("Enemy")
    inst = bp_v2.instantiate("e1")
    check("patched Enemy hp default = 50", inst["hp"], 50)

finally:
    shutil.rmtree(tmp8, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 9. _collect_declared_names utility
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 9. _collect_declared_names ─────────────────────────────────────────")

from parser import parse as _parse

prog = _parse("fn foo() { }\nstruct Bar { let x: int }\nnode Baz { }\nlet score = 0")
names = _collect_declared_names(prog)
check_contains("foo in declared", names, "foo")
check_contains("Bar in declared", names, "Bar")
check_contains("Baz in declared", names, "Baz")
check_contains("score in declared", names, "score")

# ─────────────────────────────────────────────────────────────────────────────
# 10. _snapshot_globals — callables excluded
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 10. _snapshot_globals ──────────────────────────────────────────────")

interp_snap = Interpreter()
interp_snap.execute("let x = 10\nlet name = \"hero\"\nfn tick() { }")
snap = _snapshot_globals(interp_snap)

check("x in snapshot",     "x" in snap,    True)
check("name in snapshot",  "name" in snap, True)
check("tick NOT in snap",  "tick" in snap, False)  # callable excluded
check("x value",           snap["x"],      10)

# ─────────────────────────────────────────────────────────────────────────────
# 11. ReloadResult fields
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 11. ReloadResult fields ────────────────────────────────────────────")

rr = ReloadResult(True, True, ["fn_a", "fn_b"], ["score", "hp"], [], 3.14)
check("ReloadResult.changed",    rr.changed,    True)
check("ReloadResult.success",    rr.success,    True)
check("ReloadResult.patched",    rr.patched,    ["fn_a", "fn_b"])
check("ReloadResult.restored",   rr.restored,   ["score", "hp"])
check("ReloadResult.errors",     rr.errors,     [])
check("ReloadResult.elapsed_ms", rr.elapsed_ms, 3.14)
check_true("repr contains OK",   "OK" in repr(rr))

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
total = PASS + FAIL
print(f"InScript v2.9.0  —  {PASS}/{total} tests passed", end="")
if FAIL:
    print(f"  ❌ {FAIL} FAILED")
    sys.exit(1)
else:
    print("  ✅ ALL PASS")
    sys.exit(0)
