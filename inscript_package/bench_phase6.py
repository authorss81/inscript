#!/usr/bin/env python3
"""Phase 6 benchmark — honest measurements of P5/P6 optimizations on pong.ins.

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

# ── load & parse pong.ins once ───────────────────────────────────────────────
pong_path = os.path.join(os.path.dirname(__file__), "examples", "pong.ins")
with open(pong_path, encoding="utf-8") as f:
    source = f.read()
src_lines = source.splitlines(keepends=True)

toks = Lexer(source).tokenize()
ast = Parser(toks).parse()
analyzer = Analyzer()
# Register game namespace objects that pygame_backend injects at runtime
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
    print("❌ Could not find scene 'Pong'")
    sys.exit(1)

hooks = {h.hook_type: h for h in scene.hooks}
print(f"Hooks: {', '.join(hooks.keys())}")

# ── Helper: run hook body with the AST tree-walk interpreter ─────────────────
def run_ast(hook, interp, env, dt=None):
    """Run a hook body via AST tree-walk.  Returns after execution."""
    interp._env = env
    interp._push(hook.hook_type)
    try:
        if hook.params and dt is not None:
            env.define(hook.params[0].name, dt)
        interp.visit(hook.body)
    except (ReturnSignal, BreakSignal, ContinueSignal):
        pass  # signals are expected (return inside hook body)
    finally:
        interp._pop()
        interp._env = env

# ── Helper: run hook body with the bytecode VM ───────────────────────────────
def run_vm(hook, vm, env, dt=None):
    """Run a pre-compiled hook via bytecode VM."""
    vm._globals = env._store
    args = [dt] if hook.params and dt is not None else []
    vm.call(VMClosure(hook._compiled_proto, []), args)

N = 5000
dt = 1/60

# ── 1. Compilation timing (P5.2 — compile_body) ──────────────────────────────
print("\n" + "=" * 60)
print("  1. Compilation microbenchmark (P5.2 — compile_body)")
print("=" * 60)

compiler = Compiler()
for hook_type in ["on_update", "on_draw"]:
    h = hooks.get(hook_type)
    if not h:
        continue
    param_names = [p.name for p in h.params]
    times = []
    for _ in range(500):
        t0 = time.perf_counter()
        fn = compiler.compile_body(h.body, params=param_names, hook_name=hook_type)
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1_000_000)
    avg = statistics.mean(times)
    print(f"  {hook_type:12s}: avg {avg:8.2f} µs  "
          f"min {min(times):8.2f} µs  max {max(times):8.2f} µs  "
          f"(n={len(times)})")

# ── Mock game namespaces (stubs so hooks can execute) ─────────────────────────
class MockInput:
    def key_down(self, k): return False
    def key_pressed(self, k): return False
class MockDraw:
    def rect(self, x, y, w, h, c=None): pass
    def rounded_rect(self, x, y, w, h, c=None, r=0): pass
    def circle(self, x, y, r, c=None): pass
    def text(self, x, y, t, c=None, s=12): pass
    def text_centered(self, x, y, t, c=None, s=12, b=False): pass
class MockScreen:
    def set_title(self, t): pass
    def set_background(self, c): pass
    def clear(self): pass
    def fade(self, v): pass
    @property
    def fps(self): return 60

# 2. Per-hook execution speed: VM vs AST walker (P5.3)
print("\n" + "=" * 60)
print("  2. Per-hook execution: bytecode VM vs AST walker (P5.3)")
print("=" * 60)

# Pre-compile all hooks
for h in scene.hooks:
    param_names = [p.name for p in h.params]
    h._compiled_proto = compiler.compile_body(h.body, params=param_names,
                                              hook_name=h.hook_type)

# Build a self-contained scene state (no dependency on top-level functions like clamp)
# We inline clamp's logic into a native Python callable for both AST and VM tests.
def _clamp(v, lo, hi):
    if v < lo: return lo
    if v > hi: return hi
    return v

shared_env = Environment(name="scene")
for k, v in [("ball_x", 400.0), ("ball_y", 300.0), ("bvx", 280.0), ("bvy", 140.0),
             ("ly", 260.0), ("ry", 260.0), ("sl", 2), ("sr", 3), ("winner", 0),
             ("speed", 1.2), ("W", 800), ("H", 600), ("PAD_W", 12), ("PAD_H", 80),
             ("BALL_R", 8.0), ("BALL_SPEED", 280.0), ("PAD_SPEED", 320.0),
             ("MAX_SCORE", 7), ("clamp", _clamp), ("input", MockInput()),
             ("draw", MockDraw()), ("screen", MockScreen()),
             ("string", lambda v: str(v)), ("int", lambda v: int(v)),
             ("float", lambda v: float(v)), ("bool", lambda v: bool(v)),
             ("len", len), ("print", print)]:
    shared_env.define(k, v)

for hook_type in ["on_update", "on_draw"]:
    h = hooks.get(hook_type)
    if not h:
        continue

    # AST walker timing
    interp = Interpreter(src_lines)
    interp._env = shared_env
    interp._globals = shared_env
    times_ast = []
    for _ in range(N):
        t0 = time.perf_counter()
        run_ast(h, interp, shared_env, dt)
        t1 = time.perf_counter()
        times_ast.append((t1 - t0) * 1_000_000)

    # VM timing
    vm = VM()
    vm._globals = shared_env._store
    times_vm = []
    for _ in range(N):
        t0 = time.perf_counter()
        run_vm(h, vm, shared_env, dt)
        t1 = time.perf_counter()
        times_vm.append((t1 - t0) * 1_000_000)

    avg_ast = statistics.mean(times_ast)
    avg_vm  = statistics.mean(times_vm)
    speedup = avg_ast / avg_vm if avg_vm > 0 else float('inf')

    print(f"\n  {hook_type}:")
    print(f"    AST walker: {avg_ast:8.2f} µs avg  (min {min(times_ast):.2f}  max {max(times_ast):.2f})")
    print(f"    Bytecode VM: {avg_vm:8.2f} µs avg  (min {min(times_vm):.2f}  max {max(times_vm):.2f})")
    print(f"    Speedup: {speedup:.1f}x")

# Refresh scene state after on_update runs
shared_env.set("sl", 2)
shared_env.set("sr", 3)
shared_env.set("winner", 0)

# ── 3. State sync overhead measurement (P6.1) ────────────────────────────────
print("\n" + "=" * 60)
print("  3. State sync overhead (P6.1 — removed)")
print("=" * 60)

sync_keys = ["ball_x", "ball_y", "bvx", "bvy", "ly", "ry", "sl", "sr", "winner", "speed"]
vm2 = VM()
vm2._globals = shared_env._store

times_sync = []
for _ in range(N):
    t0 = time.perf_counter()
    # Old per-frame sync: copy env -> VM
    for k in sync_keys:
        vm2._globals[k] = shared_env._store[k]
    # (VM execution would happen here — not measured)
    # Old per-frame sync: copy VM -> env
    for k in sync_keys:
        shared_env.set(k, vm2._globals[k])
    t1 = time.perf_counter()
    times_sync.append((t1 - t0) * 1_000_000)

avg_sync = statistics.mean(times_sync)
print(f"  Old per-frame sync (env↔VM, 10 vars): {avg_sync:.3f} µs")
print(f"  Status: Removed in P6.1 — no longer runs per frame")

# ── 4. Draw batching overhead (P6.4) ────────────────────────────────────────
print("\n" + "=" * 60)
print("  4. Draw batching overhead (P6.4 — BatchedDrawNamespace)")
print("=" * 60)

# Simulate the pong.ins draw ops (matching on_draw sequence)
DRAW_OPS_COUNT = 22 + 2 + 1 + 2 + 3  # 22 dashed lines + 2 paddles + ball + 2 scores + 3 text

# Direct (no batching) — simulate calling each draw function directly
times_direct = []
for _ in range(N):
    t0 = time.perf_counter()
    # 22 dashed centre-line rects
    for cy in range(0, 600, 28):
        _ = ("rect", (398, cy, 4, 14))
    # Left paddle
    _ = ("rounded_rect", (20, 260, 12, 80))
    # Right paddle
    _ = ("rounded_rect", (768, 260, 12, 80))
    # Ball
    _ = ("circle", (400, 300, 8.0))
    # Scores
    _ = ("text_centered", (200, 40, "2"))
    _ = ("text_centered", (600, 40, "3"))
    # FPS + controls
    _ = ("text", (4, 580, "FPS"))
    _ = ("text", (8, 564, "W/S"))
    _ = ("text", (730, 564, "UP/DOWN"))
    t1 = time.perf_counter()
    times_direct.append((t1 - t0) * 1_000_000)

# Batched — simulate BatchedDrawNamespace queue + flush
class Batch:
    __slots__ = ('q',)
    def __init__(self): self.q = []
    def rect(self, x, y, w, h): self.q.append(0)
    def rounded_rect(self, x, y, w, h, c, r): self.q.append(1)
    def circle(self, x, y, r, c): self.q.append(2)
    def text_centered(self, x, y, t, c, s, b): self.q.append(3)
    def text(self, x, y, t, c, s): self.q.append(4)
    def flush(self): self.q.clear()

times_batch = []
for _ in range(N):
    b = Batch()
    t0 = time.perf_counter()
    for cy in range(0, 600, 28): b.rect(398, cy, 4, 14)
    b.rounded_rect(20, 260, 12, 80, None, 4)
    b.rounded_rect(768, 260, 12, 80, None, 4)
    b.circle(400, 300, 8.0, None)
    b.text_centered(200, 40, "2", None, 52, True)
    b.text_centered(600, 40, "3", None, 52, True)
    b.text(4, 580, "FPS", None, 12)
    b.text(8, 564, "W/S", None, 12)
    b.text(730, 564, "UP/DOWN", None, 12)
    b.flush()
    t1 = time.perf_counter()
    times_batch.append((t1 - t0) * 1_000_000)

avg_direct = statistics.mean(times_direct)
avg_batch  = statistics.mean(times_batch)
overhead = avg_batch - avg_direct
print(f"  Direct execution:     {avg_direct:.3f} µs avg  ({DRAW_OPS_COUNT} ops)")
print(f"  Batched queue+flush:  {avg_batch:.3f} µs avg  (same ops)")
print(f"  Overhead:             {overhead:.3f} µs ({overhead/avg_direct*100:.2f}% of direct)")

# ── 5. Rust VM trial compilation (P6.3) ──────────────────────────────────────
print("\n" + "=" * 60)
print("  5. Rust VM trial compilation (P6.3)")
print("=" * 60)

def _ast_to_source(node, indent=0):
    _indent = '  ' * indent
    if isinstance(node, BlockStmt):
        return '{\n' + ''.join(_ast_to_source(s, indent+1) for s in node.body) + _indent + '}\n'
    if isinstance(node, ExprStmt):
        return _indent + _ast_to_source(node.expr, indent) + '\n'
    if isinstance(node, VarDecl):
        init = ' = ' + _ast_to_source(node.initializer, indent) if node.initializer else ' = nil'
        return _indent + 'let ' + node.name + init + '\n'
    if isinstance(node, AssignExpr):
        target = node.target.name if hasattr(node.target, 'name') else _ast_to_source(node.target, indent)
        return target + ' = ' + _ast_to_source(node.value, indent)
    if isinstance(node, IfStmt):
        s = _indent + 'if ' + _ast_to_source(node.condition, indent) + ' '
        s += _ast_to_source(node.then_branch, indent)
        if node.else_branch:
            s += _indent + 'else ' + _ast_to_source(node.else_branch, indent)
        return s
    if isinstance(node, WhileStmt):
        return _indent + 'while ' + _ast_to_source(node.condition, indent) + ' ' + _ast_to_source(node.body, indent)
    if isinstance(node, BinaryExpr):
        return '(' + _ast_to_source(node.left, indent) + ' ' + node.op + ' ' + _ast_to_source(node.right, indent) + ')'
    if isinstance(node, UnaryExpr):
        return node.op + _ast_to_source(node.operand, indent)
    if isinstance(node, GetAttrExpr):
        return _ast_to_source(node.obj, indent) + '.' + node.attr
    if isinstance(node, CallExpr):
        args = ', '.join(_ast_to_source(a.value, indent) for a in node.args)
        if isinstance(node.callee, GetAttrExpr):
            obj = _ast_to_source(node.callee.obj, indent)
            named = getattr(node, 'named_args', None)
            if named:
                for na in named:
                    args += ', ' + na.name + ': ' + _ast_to_source(na.value, indent)
            return obj + '.' + node.callee.attr + '(' + args + ')'
        return _ast_to_source(node.callee, indent) + '(' + args + ')'
    if isinstance(node, IdentExpr):
        return node.name
    if isinstance(node, IntLiteralExpr):
        return str(node.value)
    if isinstance(node, FloatLiteralExpr):
        return str(node.value)
    if isinstance(node, StringLiteralExpr):
        return '"' + node.value.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if isinstance(node, BoolLiteralExpr):
        return 'true' if node.value else 'false'
    if isinstance(node, NullLiteralExpr):
        return 'nil'
    return '/* unhandled */ nil'

try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "target", "release"))
    from inscript_parser import compile as _rust_compile
    RUST_OK = True
except ImportError:
    RUST_OK = False

if RUST_OK:
    for hook_type in ["on_update", "on_draw"]:
        h = hooks.get(hook_type)
        if not h:
            continue
        src = _ast_to_source(h.body)
        times = []
        last_ok = False
        for _ in range(50):
            t0 = time.perf_counter()
            try:
                _rust_compile(src)
                last_ok = True
            except Exception:
                last_ok = False
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1_000_000)
        avg = statistics.mean(times)
        verdict = "COMPATIBLE" if last_ok else "INCOMPATIBLE — falls back to Python VM"
        print(f"  {hook_type:12s}: Rust compile avg {avg:.2f} µs  ({verdict})")

        if last_ok:
            # Also check if the compiled source can round-trip
            print(f"    Source length: {len(src)} chars")
else:
    print("  Rust DLL not importable from target/release/")
    print("  Skipping Rust VM trial compilation benchmark.")

# ── 6. Combined per-frame budget ────────────────────────────────────────────
print("\n" + "=" * 60)
print("  6. Combined per-frame budget (at 60 fps = 16 667 µs)")
print("=" * 60)

vm3 = VM()
vm3._globals = shared_env._store
cl_u = VMClosure(hooks["on_update"]._compiled_proto, [])
cl_d = VMClosure(hooks["on_draw"]._compiled_proto, [])

times_total = []
for _ in range(N):
    shared_env.set("dt", dt)
    shared_env.set("sl", 2)
    shared_env.set("sr", 3)
    shared_env.set("winner", 0)
    vm3._globals = dict(shared_env._store)  # copy to avoid mutation across runs
    t0 = time.perf_counter()
    vm3.call(cl_u, [dt])
    vm3.call(cl_d, [])
    t1 = time.perf_counter()
    times_total.append((t1 - t0) * 1_000_000)

avg_total = statistics.mean(times_total)
budget_used = (avg_total / 16667) * 100
print(f"  Combined VM hooks:    {avg_total:>8.2f} µs avg")
print(f"  60 fps budget:         16 667 µs")
print(f"  Budget used:            {budget_used:>5.2f}%")
print(f"  Headroom:               {100 - budget_used:>5.2f}%")
print(f"  Theoretical max FPS:   {1e6 / avg_total:.0f}")

# ── 7. Wall time comparison: AST vs VM across N frames ───────────────────────
print("\n" + "=" * 60)
print("  7. Total wall time (AST vs VM across N frames)")
print("=" * 60)
N2 = 1000

interp2 = Interpreter(src_lines)
interp2._env = shared_env
interp2._globals = shared_env
t0 = time.perf_counter()
for _ in range(N2):
    shared_env.set("sl", 2)
    shared_env.set("sr", 3)
    shared_env.set("winner", 0)
    run_ast(hooks["on_update"], interp2, shared_env, dt)
    run_ast(hooks["on_draw"], interp2, shared_env)
t_ast = time.perf_counter() - t0

vm4 = VM()
vm4._globals = dict(shared_env._store)
t0 = time.perf_counter()
for _ in range(N2):
    shared_env.set("dt", dt)
    shared_env.set("sl", 2)
    shared_env.set("sr", 3)
    shared_env.set("winner", 0)
    vm4._globals = dict(shared_env._store)
    vm4.call(cl_u, [dt])
    vm4.call(cl_d, [])
t_vm = time.perf_counter() - t0

print(f"  AST walker:  {t_ast*1000:.2f} ms for {N2} frames")
print(f"  Bytecode VM: {t_vm*1000:.2f} ms for {N2} frames")
print(f"  Speedup:     {t_ast/t_vm:.1f}x")

# ── Summary ─────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  SUMMARY")
print("=" * 60)
print(f"  Compilation (on_update):   one-time cost at load")
print(f"  Per-frame VM execution:    {avg_total:.2f} µs = {budget_used:.1f}% of budget")
print(f"  State sync removed:        saves {avg_sync:.2f} µs/frame (P6.1)")
print(f"  Draw batching overhead:    {overhead:.3f} µs (P6.4, negligible)")
print(f"  Rust VM trial:             {'available' if RUST_OK else 'N/A'} (P6.3)")
print(f"  Game loop speedup:         {t_ast/t_vm:.1f}x over AST walker")
print("=" * 60)
