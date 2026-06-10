#!/usr/bin/env python3
"""Phase 7 benchmark — Python AST compilation vs bytecode VM vs AST walker.

Runs without pygame display by exercising the compiler + VM engines directly.
"""
import sys, os, time, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser import Parser
from analyzer import Analyzer, Symbol, T_ANY
from ast_nodes import *
from interpreter import Interpreter
from environment import Environment
from compiler import Compiler, compile_body as _compile_body
from vm import VM, VMClosure
from errors import ReturnSignal, BreakSignal, ContinueSignal
from py_compiler import compile_hook as _py_compile

pong_path = os.path.join(os.path.dirname(__file__), "examples", "pong.ins")
with open(pong_path, encoding="utf-8") as f:
    source = f.read()
src_lines = source.splitlines(keepends=True)

toks = Lexer(source).tokenize()
ast = Parser(toks).parse()
analyzer = Analyzer()
for _name in ["screen", "draw", "draw3d", "input", "audio", "font",
              "math2d", "Color", "clock",
              "WHITE","BLACK","RED","GREEN","BLUE","YELLOW","CYAN","MAGENTA",
              "ORANGE","GRAY","DARK_GRAY","LIGHT_GRAY","PURPLE","PINK",
              "TEAL","NAVY","LIME","BROWN","SKY","GOLD","TRANSPARENT"]:
    analyzer._scope.symbols[_name] = Symbol(_name, T_ANY, kind="var")
analyzer.analyze(ast)

scene = None
for node in ast.body:
    if hasattr(node, 'name') and node.name == 'Pong':
        scene = node
        break
if not scene:
    print("No scene Pong found"); sys.exit(1)

hooks = {h.hook_type: h for h in scene.hooks}
print(f"Hooks: {', '.join(hooks.keys())}")

def _clamp(v, lo, hi):
    if v < lo: return lo
    if v > hi: return hi
    return v

N = 5000
dt = 1/60

# ── 1. Compilation speed ──────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  1. Compilation speed")
print("=" * 60)

compiler = Compiler()
for hook_type in ["on_update", "on_draw"]:
    h = hooks.get(hook_type)
    if not h: continue
    param_names = [p.name for p in h.params]

    # Phase 5: compile_body
    times_p5 = []
    for _ in range(500):
        t0 = time.perf_counter()
        fn = compiler.compile_body(h.body, params=param_names, hook_name=hook_type)
        t1 = time.perf_counter()
        times_p5.append((t1 - t0) * 1_000_000)

    # Phase 7: py_compiler
    times_p7 = []
    for _ in range(500):
        t0 = time.perf_counter()
        hc = _py_compile(h.body, param_names, hook_type)
        t1 = time.perf_counter()
        times_p7.append((t1 - t0) * 1_000_000)

    avg_p5 = statistics.mean(times_p5)
    avg_p7 = statistics.mean(times_p7)
    print(f"  {hook_type:12s}:")
    print(f"    compile_body:  avg {avg_p5:>8.2f} µs")
    print(f"    py_compiler:   avg {avg_p7:>8.2f} µs")
    print(f"    ratio:         {avg_p7/avg_p5:.1f}x")

# ── 2. Per-hook execution speed ───────────────────────────────────────────
print("\n" + "=" * 60)
print("  2. Per-hook execution speed (N=5000)")
print("=" * 60)

# Pre-compile all hooks
for h in scene.hooks:
    param_names = [p.name for p in h.params]
    h._compiled_proto = compiler.compile_body(h.body, params=param_names,
                                              hook_name=h.hook_type)
    h._compiled_hook  = _py_compile(h.body, param_names, h.hook_type)

# Shared mock state
state = {
    "ball_x": 400.0, "ball_y": 300.0, "bvx": 280.0, "bvy": 140.0,
    "ly": 260.0, "ry": 260.0, "sl": 2, "sr": 3, "winner": 0,
    "speed": 1.2, "W": 800, "H": 600, "PAD_W": 12, "PAD_H": 80,
    "BALL_R": 8.0, "BALL_SPEED": 280.0, "PAD_SPEED": 320.0,
    "MAX_SCORE": 7,
}

class MockInput:
    def key_down(self, k): return False
    def key_pressed(self, k): return False
class MockDraw:
    def rect(self, x, y, w, h, c=None): pass
    def rounded_rect(self, x, y, w, h, c=None, r=0): pass
    def circle(self, x, y, r, c=None): pass
    def text(self, x, y, t, c=None, s=12): pass
    def text_centered(self, x, y, t, c=None, s=12, b=False): pass
    def flush(self): pass
class MockScreen:
    def set_title(self, t): pass
    def set_background(self, c): pass
    def clear(self): pass
    def fade(self, v): pass
    @property
    def fps(self): return 60

game_globals = {
    "draw": MockDraw(), "screen": MockScreen(), "input": MockInput(),
    "print": print, "string": str, "int": int, "float": float,
    "len": len, "clamp": _clamp,
}

env = Environment(name="scene")
for k, v in state.items():
    env.define(k, v)
env.define("clamp", _clamp)
env.define("input", MockInput())
env.define("draw", MockDraw())
env.define("screen", MockScreen())
env.define("string", lambda v: str(v))
env.define("int", lambda v: int(v))
env.define("float", lambda v: float(v))
env.define("bool", lambda v: bool(v))
env.define("len", len)
env.define("print", print)

def run_ast(hook, interp, env, dt=None):
    interp._env = env
    interp._push(hook.hook_type)
    try:
        if hook.params and dt is not None:
            env.define(hook.params[0].name, dt)
        interp.visit(hook.body)
    except (ReturnSignal, BreakSignal, ContinueSignal):
        pass
    finally:
        interp._pop()

def run_vm(hook, vm, env, dt=None):
    args = [dt] if hook.params and dt is not None else []
    vm.call(VMClosure(hook._compiled_proto, []), args)

for hook_type in ["on_update", "on_draw"]:
    h = hooks.get(hook_type)
    if not h: continue

    # AST walker
    interp = Interpreter(src_lines)
    interp._env = env
    times_ast = []
    for _ in range(N):
        t0 = time.perf_counter()
        run_ast(h, interp, env, dt)
        t1 = time.perf_counter()
        times_ast.append((t1 - t0) * 1_000_000)
    avg_ast = statistics.mean(times_ast)

    # VM
    vm = VM()
    vm._globals = dict(env._store)
    times_vm = []
    for _ in range(N):
        t0 = time.perf_counter()
        run_vm(h, vm, env, dt)
        t1 = time.perf_counter()
        times_vm.append((t1 - t0) * 1_000_000)
    avg_vm = statistics.mean(times_vm)

    # Phase 7 (py_compiler)
    hc = h._compiled_hook
    times_p7 = []
    for _ in range(N):
        t0 = time.perf_counter()
        hc.exec(game_globals, [dt] if hook_type == "on_update" else [], state)
        t1 = time.perf_counter()
        times_p7.append((t1 - t0) * 1_000_000)
    avg_p7 = statistics.mean(times_p7)

    vs_ast = avg_ast / avg_p7 if avg_p7 > 0 else float('inf')
    vs_vm  = avg_vm / avg_p7 if avg_p7 > 0 else float('inf')

    print(f"\n  {hook_type}:")
    print(f"    AST walker:       {avg_ast:>8.2f} µs")
    print(f"    Bytecode VM:      {avg_vm:>8.2f} µs")
    print(f"    Py compiled:      {avg_p7:>8.2f} µs")
    print(f"    Speedup vs AST:   {vs_ast:.1f}x")
    print(f"    Speedup vs VM:    {vs_vm:.1f}x")

# ── 3. Total wall time ────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  3. Total wall time (1000 frames, on_update + on_draw)")
print("=" * 60)

N2 = 1000

# AST
interp2 = Interpreter(src_lines)
interp2._env = env
t0 = time.perf_counter()
for _ in range(N2):
    run_ast(hooks["on_update"], interp2, env, dt)
    run_ast(hooks["on_draw"], interp2, env)
t_ast = time.perf_counter() - t0

# VM
vm4 = VM()
vm4._globals = dict(env._store)
cl_u = VMClosure(hooks["on_update"]._compiled_proto, [])
cl_d = VMClosure(hooks["on_draw"]._compiled_proto, [])
t0 = time.perf_counter()
for _ in range(N2):
    vm4._globals = dict(env._store)
    vm4.call(cl_u, [dt])
    vm4.call(cl_d, [])
t_vm = time.perf_counter() - t0

# Phase 7
hc_u = hooks["on_update"]._compiled_hook
hc_d = hooks["on_draw"]._compiled_hook
t0 = time.perf_counter()
for _ in range(N2):
    hc_u.exec(game_globals, [dt], state)
    hc_d.exec(game_globals, [], state)
t_p7 = time.perf_counter() - t0

print(f"  AST walker:        {t_ast*1000:>8.2f} ms  ({t_ast*1e6/N2:.1f} µs/frame)")
print(f"  Bytecode VM:       {t_vm*1000:>8.2f} ms  ({t_vm*1e6/N2:.1f} µs/frame)")
print(f"  Py compiled (P7):  {t_p7*1000:>8.2f} ms  ({t_p7*1e6/N2:.1f} µs/frame)")
print(f"  P7 speedup vs AST: {t_ast/t_p7:.1f}x")
print(f"  P7 speedup vs VM:  {t_vm/t_p7:.1f}x")

print("\n" + "=" * 60)
print("  SUMMARY")
print("=" * 60)
if t_p7 < t_ast and t_p7 < t_vm:
    print(f"  Phase 7 is the FASTEST path: {t_ast/t_p7:.1f}x over AST, {t_vm/t_p7:.1f}x over VM")
elif t_p7 < t_ast:
    print(f"  Phase 7 beats AST ({t_ast/t_p7:.1f}x) but not VM ({t_vm/t_p7:.1f}x)")
elif t_p7 < t_vm:
    print(f"  Phase 7 beats VM ({t_vm/t_p7:.1f}x) but not AST ({t_ast/t_p7:.1f}x)")
else:
    print(f"  Phase 7 is slower than both AST ({t_ast/t_p7:.1f}x) and VM ({t_vm/t_p7:.1f}x)")
print("=" * 60)
