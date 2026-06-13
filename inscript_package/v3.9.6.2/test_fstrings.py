#!/usr/bin/env python3
"""v3.9.6.2 — Test F-string compilation in py_compiler.

Tests:
  1. Basic f-string with scene variable
  2. F-string with expression (a + b)
  3. F-string with format spec {:.2f}
  4. Escaped braces {{ and }}
  5. Raw f-string rf"..." (backslash preserved)
  6. F-string with game namespace (Color::RED)
  7. F-string with hook param (dt)
  8. Multiple expressions in one f-string
  9. F-string with method/property call
  10. Nested expressions inside f-string
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer import Lexer
from parser import Parser
from analyzer import Analyzer, Symbol, T_ANY
from py_compiler import compile_hook
import traceback

PASS = 0
FAIL = 0

def test(name, src, param_names, state, expected, globs=None):
    """Compile a hook body, execute it, and verify the result."""
    global PASS, FAIL
    try:
        toks = Lexer(src).tokenize()
        ast = Parser(toks).parse()
        analyzer = Analyzer()
        for n in ["print", "string", "int", "float", "bool", "len",
                   "screen", "draw", "input", "audio", "font", "math2d",
                   "Color", "clock", "Vec2", "Rect",
                   "WHITE","BLACK","RED","GREEN","BLUE","YELLOW","CYAN","MAGENTA",
                   "ORANGE","GRAY","DARK_GRAY","LIGHT_GRAY","PURPLE","PINK",
                   "TEAL","NAVY","LIME","BROWN","SKY","GOLD","TRANSPARENT"]:
            analyzer._scope.symbols[n] = Symbol(n, T_ANY, kind="var")
        # Register state keys as scene variables
        for k in state:
            if k not in analyzer._scope.symbols:
                analyzer._scope.symbols[k] = Symbol(k, T_ANY, kind="var")
        analyzer._scope.symbols["nil"] = Symbol("nil", T_ANY, kind="var")
        analyzer.analyze(ast)

        # Extract the first scene hook body
        hook = None
        for node in ast.body:
            if hasattr(node, 'hooks') and node.hooks:
                hook = node.hooks[0]
                break
        if hook is None:
            print(f"  ❌ {name}: no hook found")
            FAIL += 1
            return

        hc = compile_hook(hook.body, param_names, "test")
        if hc is None:
            print(f"  ❌ {name}: compilation returned None")
            FAIL += 1
            return

        g = globs or {"print": print, "string": str, "int": int, "float": float}
        hc.exec(g, [1/60] if "dt" in param_names else [], state)

        if isinstance(expected, tuple):
            key, val = expected
            result = state.get(key)
            if result == val:
                print(f"  ✅ {name}: {key}={result!r}")
                PASS += 1
            else:
                print(f"  ❌ {name}: expected {key}={val!r}, got {result!r}")
                FAIL += 1
        elif callable(expected):
            if expected(state):
                print(f"  ✅ {name}")
                PASS += 1
            else:
                print(f"  ❌ {name}: predicate failed, state={state}")
                FAIL += 1
        else:
            print(f"  ❌ {name}: invalid expected value")
            FAIL += 1
    except Exception as e:
        traceback.print_exc()
        print(f"  ❌ {name}: {e}")
        FAIL += 1


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: Basic f-string with scene variable
# ═══════════════════════════════════════════════════════════════════════════════
test("basic f-string with scene variable",
     r"""scene Test { on_start { let msg = f"hello {name}"; result = msg } }""",
     [], {"name": "world", "result": ""}, ("result", "hello world"))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: F-string with expression
# ═══════════════════════════════════════════════════════════════════════════════
test("f-string with expression",
     r"""scene Test { on_start { let msg = f"sum = {a + b}"; result = msg } }""",
     [], {"a": 10, "b": 20, "result": ""}, ("result", "sum = 30"))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: F-string with format spec
# ═══════════════════════════════════════════════════════════════════════════════
test("f-string with format spec",
     r"""scene Test { on_start { let msg = f"pi = {pi:.2f}"; result = msg } }""",
     [], {"pi": 3.14159, "result": ""}, ("result", "pi = 3.14"))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: Escaped braces {{ and }}
# ═══════════════════════════════════════════════════════════════════════════════
test("f-string with escaped braces",
     r"""scene Test { on_start { let msg = f"{{hello}} {name}"; result = msg } }""",
     [], {"name": "world", "result": ""}, ("result", "{hello} world"))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: Raw f-string (backslash preserved)
# ═══════════════════════════════════════════════════════════════════════════════
test("raw f-string preserves backslash",
     r"""scene Test { on_start { let msg = rf"path = C:\Users\{name}"; result = msg } }""",
     [], {"name": "test", "result": ""}, ("result", r"path = C:\Users\test"))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 6: F-string with game namespace
# ═══════════════════════════════════════════════════════════════════════════════
class MockColor:
    RED = "#FF0000"

test("f-string with game namespace",
     r"""scene Test { on_start { let msg = f"color = {Color::RED}"; result = msg } }""",
     [], {"result": ""}, ("result", "color = #FF0000"),
     globs={"Color": MockColor, "print": print, "string": str})

# ═══════════════════════════════════════════════════════════════════════════════
# Test 7: F-string with hook param (dt)
# ═══════════════════════════════════════════════════════════════════════════════
def check_dt(state):
    msg = state.get("result", "")
    return "dt = " in msg and "0.016" in msg

test("f-string with hook param dt",
     r"""scene Test { on_update(dt: float) { let msg = f"dt = {dt}"; result = msg } }""",
     ["dt"], {"result": ""}, lambda s: "dt = 0.016" in s.get("result", ""))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 8: Multiple expressions in one f-string
# ═══════════════════════════════════════════════════════════════════════════════
test("multiple expressions in one f-string",
     r"""scene Test { on_start { let msg = f"{a} + {b} = {a + b}"; result = msg } }""",
     [], {"a": 3, "b": 5, "result": ""}, ("result", "3 + 5 = 8"))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 9: F-string with property/method access
# ═══════════════════════════════════════════════════════════════════════════════
class MockVec2:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __str__(self):
        return f"({self.x}, {self.y})"

test("f-string with property access",
     r"""scene Test { on_start { let msg = f"pos = ({pos.x}, {pos.y})"; result = msg } }""",
     [], {"pos": MockVec2(100, 200), "result": ""}, ("result", "pos = (100, 200)"),
     globs={"print": print, "string": str})

# ═══════════════════════════════════════════════════════════════════════════════
# Test 10: F-string in on_update with scene variables
# ═══════════════════════════════════════════════════════════════════════════════
test("f-string in on_update with scene vars",
     r"""scene Test { on_update(dt: float) { let msg = f"frame={frame} dt={dt:.3f}"; result = msg } }""",
     ["dt"], {"frame": 42, "result": ""}, lambda s: "frame=42" in s.get("result", ""))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 11: F-string with bool value
# ═══════════════════════════════════════════════════════════════════════════════
test("f-string with bool",
     r"""scene Test { on_start { let msg = f"flag = {flag}"; result = msg } }""",
     [], {"flag": True, "result": ""}, ("result", "flag = True"))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 12: F-string with nil/null value
# ═══════════════════════════════════════════════════════════════════════════════
test("f-string with nil",
     r"""scene Test { on_start { let msg = f"val = {val}"; result = msg } }""",
     [], {"val": None, "result": ""}, ("result", "val = None"))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 13: Empty f-string
# ═══════════════════════════════════════════════════════════════════════════════
test("empty f-string",
     r"""scene Test { on_start { let msg = f""; result = msg } }""",
     [], {"result": ""}, ("result", ""))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 14: F-string only literals (no expressions)
# ═══════════════════════════════════════════════════════════════════════════════
test("f-string with no expressions (literal only)",
     r"""scene Test { on_start { let msg = f"hello world"; result = msg } }""",
     [], {"result": ""}, ("result", "hello world"))

# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════
TOTAL = PASS + FAIL
print(f"\n{'='*50}")
print(f"  v3.9.6.2 — F-strings: {PASS}/{TOTAL} passed")
print(f"{'='*50}")
sys.exit(0 if FAIL == 0 else 1)
