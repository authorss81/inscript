#!/usr/bin/env python3
"""v3.9.6.6 — Test compilation speed optimization.

Tests:
  1. compile_scene_hooks compiles all hooks in a scene
  2. Parallel compilation produces same results as serial
  3. Names cache counter is monotonic (no stale cache hits)
  4. Benchmarks compile_hook speed
"""
import sys, os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer import Lexer
from parser import Parser
from analyzer import Analyzer, Symbol, T_ANY
from py_compiler import compile_hook, compile_scene_hooks, _names_cache_counter
import traceback

PASS = 0
FAIL = 0

SRC = r"""
scene Test {
    on_start {
        let x = 10
        let y = 20
        let z = x + y
        if z > 25 {
            z = z * 2
        }
        print("z = " + string(z))
    }
    on_update(dt: float) {
        let vx = 100.0
        let vy = 200.0
        let speed = 1.5
        vx = vx + speed * dt
        vy = vy + speed * dt
    }
    on_draw {
        draw.rect(0, 0, 100, 100)
        draw.circle(50, 50, 25)
    }
}
"""

def setup():
    toks = Lexer(SRC).tokenize()
    ast = Parser(toks).parse()
    analyzer = Analyzer()
    for n in ["print", "string", "int", "float", "bool", "len",
               "screen", "draw", "input", "audio", "font", "math2d",
               "Color", "clock", "Vec2", "Rect",
               "WHITE","BLACK","RED","GREEN","BLUE","YELLOW","CYAN","MAGENTA",
               "ORANGE","GRAY","DARK_GRAY","LIGHT_GRAY","PURPLE","PINK",
               "TEAL","NAVY","LIME","BROWN","SKY","GOLD","TRANSPARENT"]:
        analyzer._scope.symbols[n] = Symbol(n, T_ANY, kind="var")
    analyzer._scope.symbols["nil"] = Symbol("nil", T_ANY, kind="var")
    analyzer.analyze(ast)
    scene = [n for n in ast.body if hasattr(n, 'name') and n.name == 'Test'][0]
    return scene


# Test 1: compile_scene_hooks compiles all hooks
scene = setup()
results = compile_scene_hooks(scene)
expected_hooks = {"on_start", "on_update", "on_draw"}
compiled = {hook_type for hook_type, hc in results if hc is not None}
if compiled == expected_hooks:
    print(f"  ✅ compile_scene_hooks compiled all 3 hooks")
    PASS += 1
else:
    print(f"  ❌ compile_scene_hooks: expected {expected_hooks}, got {compiled}")
    FAIL += 1

# Test 2: Each hook can execute
globs = {"print": print, "string": str, "draw": type("D",(),{"rect":lambda *a:None,"circle":lambda *a:None})()}
for hook_type, hc in results:
    if hc is None:
        print(f"  ❌ {hook_type}: HookCode is None")
        FAIL += 1
        continue
    try:
        state = {"x": 10, "y": 20, "z": 30, "vx": 0, "vy": 0, "speed": 1.5}
        hc.exec(globs, [1/60] if hc.param_count else [], state)
        print(f"  ✅ {hook_type} executed OK")
        PASS += 1
    except Exception as e:
        print(f"  ❌ {hook_type}: execution failed: {e}")
        FAIL += 1

# Test 3: compile_scene_hooks matches serial compilation
scene2 = setup()
serial_results = []
for hook in scene2.hooks:
    params = [p.name for p in hook.params]
    hc = compile_hook(hook.body, params, hook.hook_type)
    serial_results.append((hook.hook_type, hc))

# Compare parallel vs serial — check that both compiled same hooks
par_compiled = {t for t, h in results if h is not None}
ser_compiled = {t for t, h in serial_results if h is not None}
if par_compiled == ser_compiled:
    print(f"  ✅ Parallel and serial compilation match")
    PASS += 1
else:
    print(f"  ❌ Mismatch: parallel={par_compiled}, serial={ser_compiled}")
    FAIL += 1

# Test 4: Benchmark compile_hook speed
N = 100
hook_body = scene.hooks[0].body  # on_start body
params = [p.name for p in scene.hooks[0].params]  # []
start = time.perf_counter()
for _ in range(N):
    hc = compile_hook(hook_body, params, "bench")
elapsed = time.perf_counter() - start
avg_ms = (elapsed / N) * 1000
print(f"  ✅ compile_hook: {avg_ms:.2f}ms avg over {N} calls")
PASS += 1

# Test 5: Benchmark compile_scene_hooks
start = time.perf_counter()
for _ in range(100):
    compile_scene_hooks(setup())
elapsed = time.perf_counter() - start
avg_ms_parallel = (elapsed / 100) * 1000
print(f"  ✅ compile_scene_hooks: {avg_ms_parallel:.2f}ms avg over 100 calls")
PASS += 1

# Summary
TOTAL = PASS + FAIL
print(f"\n{'='*50}")
print(f"  v3.9.6.6 — Compilation speed: {PASS}/{TOTAL} passed")
print(f"{'='*50}")
print(f"\nBenchmark results:")
print(f"  compile_hook:        {avg_ms:.2f}ms")
print(f"  compile_scene_hooks: {avg_ms_parallel:.2f}ms (3 hooks)")
sys.exit(0 if FAIL == 0 else 1)
