#!/usr/bin/env python3
"""v3.9.6.3 — Test Lambda compilation in py_compiler.

Tests:
  1. |x| x * 2 — single expression body
  2. |a, b| a + b — multi-param
  3. || 42 — zero-param
  4. |n| n + x — closure capture of scene var
  5. map(arr, |x| x * 2) — lambda as function arg
  6. Lambda assigned to var and called
  7. |x| { return x * 2 } — block body with return
  8. Nested lambda: |x| |y| x + y
  9. Lambda with type annotations
  10. Lambda in f-string (complex expression)
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
        for k in state:
            if k not in analyzer._scope.symbols:
                analyzer._scope.symbols[k] = Symbol(k, T_ANY, kind="var")
        analyzer._scope.symbols["nil"] = Symbol("nil", T_ANY, kind="var")
        analyzer.analyze(ast)

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
# Test 1: Basic lambda — single expression body
# ═══════════════════════════════════════════════════════════════════════════════
test("basic lambda |x| x * 2",
     r"""scene Test { on_start { let f = |x| x * 2; result = f(5) } }""",
     [], {"result": 0}, ("result", 10))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: Multi-param lambda
# ═══════════════════════════════════════════════════════════════════════════════
test("multi-param lambda |a, b| a + b",
     r"""scene Test { on_start { let add = |a, b| a + b; result = add(10, 20) } }""",
     [], {"result": 0}, ("result", 30))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: Zero-param lambda
# ═══════════════════════════════════════════════════════════════════════════════
test("zero-param lambda || 42",
     r"""scene Test { on_start { let f = || 42; result = f() } }""",
     [], {"result": 0}, ("result", 42))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: Closure — lambda captures scene variable
# ═══════════════════════════════════════════════════════════════════════════════
test("lambda captures scene variable",
     r"""scene Test { on_start { let f = |n| n + x; result = f(10) } }""",
     [], {"x": 5, "result": 0}, ("result", 15))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: Lambda as function argument
# ═══════════════════════════════════════════════════════════════════════════════
def run_map(arr, fn):
    return [fn(x) for x in arr]

test("lambda as function argument",
     r"""scene Test { on_start { let result = map(arr, |x| x * 2) } }""",
     [], {"arr": [1, 2, 3], "result": None}, lambda s: s.get("result") == [2, 4, 6],
     globs={"map": run_map, "print": print, "string": str, "int": int})

# ═══════════════════════════════════════════════════════════════════════════════
# Test 6: Lambda with scene var + param interaction
# ═══════════════════════════════════════════════════════════════════════════════
test("lambda using scene var and param",
     r"""scene Test { on_start { let f = |n| n * scale + offset; result = f(10) } }""",
     [], {"scale": 3, "offset": 1, "result": 0}, ("result", 31))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 7: Block body lambda — |x| { return x * 2 }
# ═══════════════════════════════════════════════════════════════════════════════
test("block body lambda",
     r"""scene Test { on_start { let f = |x| { return x * 3 }; result = f(7) } }""",
     [], {"result": 0}, ("result", 21))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 8: Nested lambda — |x| |y| x + y
# ═══════════════════════════════════════════════════════════════════════════════
test("nested lambda",
     r"""scene Test { on_start { let f = |x| |y| x + y; result = f(3)(4) } }""",
     [], {"result": 0}, ("result", 7))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 9: Lambda with type annotations (params ignored)
# ═══════════════════════════════════════════════════════════════════════════════
test("lambda with type annotations",
     r"""scene Test { on_start { let f = |x: int, y: int| x * y; result = f(6, 7) } }""",
     [], {"result": 0}, ("result", 42))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 10: Lambda with filtering (complex use case)
# ═══════════════════════════════════════════════════════════════════════════════
def run_filter(arr, fn):
    return [x for x in arr if fn(x)]

test("lambda with filter",
     r"""scene Test { on_start { let result = filter(arr, |x| x > 2) } }""",
     [], {"arr": [1, 2, 3, 4, 5], "result": None}, lambda s: s.get("result") == [3, 4, 5],
     globs={"filter": run_filter, "print": print, "string": str, "int": int})

# ═══════════════════════════════════════════════════════════════════════════════
# Test 11: Lambda with complex expression body
# ═══════════════════════════════════════════════════════════════════════════════
test("lambda with complex expression",
     r"""scene Test { on_start { let f = |a, b| (a + b) * 2 - 1; result = f(5, 3) } }""",
     [], {"result": 0}, ("result", 15))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 12: Lambda in on_update with dt capture
# ═══════════════════════════════════════════════════════════════════════════════
test("lambda in on_update",
     r"""scene Test { on_update(dt: float) { let f = |x| x * dt; result = f(2) } }""",
     ["dt"], {"result": 0}, ("result", 2/60))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 13: Three-param lambda
# ═══════════════════════════════════════════════════════════════════════════════
test("three-param lambda",
     r"""scene Test { on_start { let f = |a, b, c| a + b + c; result = f(1, 2, 3) } }""",
     [], {"result": 0}, ("result", 6))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 14: Lambda calling another lambda (higher-order)
# ═══════════════════════════════════════════════════════════════════════════════
test("lambda returns lambda (curried call)",
     r"""scene Test { on_start { let add = |a| |b| a + b; result = add(10)(20) } }""",
     [], {"result": 0}, ("result", 30))

# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════
TOTAL = PASS + FAIL
print(f"\n{'='*50}")
print(f"  v3.9.6.3 — Lambdas: {PASS}/{TOTAL} passed")
print(f"{'='*50}")
sys.exit(0 if FAIL == 0 else 1)
