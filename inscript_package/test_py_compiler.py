#!/usr/bin/env python3
"""Test py_compiler with real pong.ins hooks."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from lexer import Lexer
from parser import Parser
from analyzer import Analyzer, Symbol, T_ANY
from py_compiler import compile_hook

# ── load pong.ins ────────────────────────────────────────────────────────────
pong_path = os.path.join(os.path.dirname(__file__), "examples", "pong.ins")
with open(pong_path, encoding="utf-8") as f:
    source = f.read()

toks = Lexer(source).tokenize()
ast = Parser(toks).parse()
analyzer = Analyzer()
# Register game namespace objects
for _name in ["screen", "draw", "draw3d", "input", "audio", "font",
              "math2d", "Color", "clock",
              "WHITE","BLACK","RED","GREEN","BLUE","YELLOW","CYAN","MAGENTA",
              "ORANGE","GRAY","DARK_GRAY","LIGHT_GRAY","PURPLE","PINK",
              "TEAL","NAVY","LIME","BROWN","SKY","GOLD","TRANSPARENT",
              "print", "string", "int", "float", "bool", "len", "clamp",
              "sin", "cos", "sqrt", "abs", "floor", "ceil", "round", "random"]:
    analyzer._scope.symbols[_name] = Symbol(_name, T_ANY, kind="var")
analyzer.analyze(ast)

scene = None
for node in ast.body:
    if hasattr(node, 'name') and node.name == 'Pong':
        scene = node
        break

if not scene:
    print("❌ No scene Pong found")
    sys.exit(1)

hooks = {h.hook_type: h for h in scene.hooks}
print(f"Hooks: {', '.join(hooks.keys())}")

# ── compile each hook ────────────────────────────────────────────────────────
all_ok = True
for hook_type in ["on_start", "on_update", "on_draw"]:
    h = hooks.get(hook_type)
    if not h:
        continue
    params = [p.name for p in h.params]
    hc = compile_hook(h.body, params, hook_type)
    status = "✅" if hc else "❌"
    print(f"  {status} {hook_type:12s} params={params}" + (f" compiled" if hc else " FAILED"))
    if not hc:
        all_ok = False

if all_ok:
    print("\nAll hooks compiled successfully!")
    
    # ── execute compiled hooks with mock namespaces ──────────────────────────
    class MockInput:
        def key_down(self, k): return False
        def key_pressed(self, k): return False
        def _update(self, e): pass
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
    class MockClock:
        def _tick(self, dt): pass
    class MockColor:
        pass
    
    globs = {
        "screen": MockScreen(), "draw": MockDraw(), "input": MockInput(),
        "audio": None, "font": None, "math2d": None, "Color": MockColor(),
        "clock": MockClock(),
        "print": print, "string": str, "int": int, "float": float,
        "len": len, "clamp": lambda v, lo, hi: lo if v < lo else hi if v > hi else v,
        "sin": __import__("math").sin, "cos": __import__("math").cos,
        "sqrt": __import__("math").sqrt, "abs": abs, "floor": int,
    }
    from py_compiler import compile_hook as _ch
    state = {
        "ball_x": 400.0, "ball_y": 300.0, "bvx": 280.0, "bvy": 140.0,
        "ly": 260.0, "ry": 260.0, "sl": 2, "sr": 3, "winner": 0,
        "speed": 1.2, "W": 800, "H": 600, "PAD_W": 12, "PAD_H": 80,
        "BALL_R": 8.0, "PAD_SPEED": 320.0, "BALL_SPEED": 280.0, "MAX_SCORE": 7,
    }
    for hook_type in ["on_start", "on_update", "on_draw"]:
        h = hooks.get(hook_type)
        if not h:
            continue
        params = [p.name for p in h.params]
        hc = _ch(h.body, params, hook_type)
        if hc:
            try:
                hc.exec(globs, [1/60], state)
                print(f"  ✅ {hook_type:12s} executed OK")
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"  ❌ {hook_type:12s} execution failed: {e}")
else:
    print("\nSome hooks failed")
