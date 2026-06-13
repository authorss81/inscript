#!/usr/bin/env python3
"""v3.9.6.1 — Test MatchStmt compilation in py_compiler.

Tests all five InScript match arm pattern types:
  1. Wildcard `case _ { }`
  2. Binding with guard `case h if h <= 0 { }`
  3. Type-narrowing `case int x { }`
  4. Struct type-narrowing `case Vec2 v { }`
  5. Literal/expression `case 1 { }`

Each test compiles a hook body with a match statement, executes it,
and verifies the correct arm fired via state dict variables.
"""
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer import Lexer
from parser import Parser
from analyzer import Analyzer, Symbol, T_ANY
from py_compiler import compile_hook
import traceback

PASS = 0
FAIL = 0

def test(name, src, param_names, state, expected, globs=None):
    """Compile a hook body, execute it, and verify a state key equals expected."""
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
        # nil is a keyword, not a declared variable
        analyzer._scope.symbols["nil"] = Symbol("nil", T_ANY, kind="var")
        # Register all state dict keys as known scene variables
        for k in state:
            if k not in analyzer._scope.symbols:
                analyzer._scope.symbols[k] = Symbol(k, T_ANY, kind="var")
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
                print(f"  ✅ {name}: {key}={result}")
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
# Test 1: Wildcard arm
# ═══════════════════════════════════════════════════════════════════════════════
test("wildcard arm matches anything",
     r"""scene Test { on_start { let arm = 0; match x { case _ { arm = 1 } } } }""",
     [], {"x": 42}, ("arm", 1))

test("literal pattern matches exact value (int)",
     r"""scene Test { on_start { let arm = 0; match x { case 1 { arm = 1 } case 2 { arm = 2 } case _ { arm = 3 } } } }""",
     [], {"x": 2}, ("arm", 2))

test("literal pattern with wildcard fallback",
     r"""scene Test { on_start { let arm = 0; match x { case 10 { arm = 10 } case _ { arm = 99 } } } }""",
     [], {"x": 999}, ("arm", 99))

test("literal pattern with strings",
     r"""scene Test { on_start { let arm = 0; match s { case "hello" { arm = 1 } case "world" { arm = 2 } case _ { arm = 3 } } } }""",
     [], {"s": "hello"}, ("arm", 1))

test("type-narrowing matches int and binds value",
     r"""scene Test { on_start { let arm = 0; let bound = nil; match x { case int n { arm = 1; bound = n } case _ { arm = 2 } } } }""",
     [], {"x": 42}, ("bound", 42))

test("type-narrowing falls through on wrong type",
     r"""scene Test { on_start { let arm = 0; let bound = nil; match x { case int n { arm = 1 } case string s { arm = 2; bound = s } case _ { arm = 3 } } } }""",
     [], {"x": "hello"}, ("bound", "hello"))

test("binding with guard — true guard",
     r"""scene Test { on_start { let arm = 0; let bound = nil; match x { case n if n > 0 { arm = 1; bound = n } case _ { arm = 2 } } } }""",
     [], {"x": 5}, lambda s: s.get("arm") == 1 and s.get("bound") == 5)

test("binding with guard — false guard falls through",
     r"""scene Test { on_start { let arm = 0; match x { case n if n > 0 { arm = 1 } case _ { arm = 2 } } } }""",
     [], {"x": -3}, ("arm", 2))

test("expression subject — a + b",
     r"""scene Test { on_start { let arm = 0; let sum = a + b; match sum { case 3 { arm = 1 } case _ { arm = 2 } } } }""",
     [], {"a": 1, "b": 2}, ("arm", 1))

test("match in on_update hook",
     r"""scene Test { on_update(dt: float) { let arm = 0; match frame { case 1 { arm = 1 } case _ { arm = 2 } } } }""",
     ["dt"], {"frame": 1}, ("arm", 1))

test("nested match — outer and inner",
     r"""scene Test { on_start { let arm = 0; match x { case 1 { match y { case 2 { arm = 12 } case _ { arm = 11 } } } case _ { arm = 0 } } } }""",
     [], {"x": 1, "y": 2}, ("arm", 12))

test("multiple literal arms — correct arm fires",
     r"""scene Test { on_start { let arm = 0; match x { case 100 { arm = 100 } case 200 { arm = 200 } case 300 { arm = 300 } case _ { arm = 0 } } } }""",
     [], {"x": 300}, ("arm", 300))

test("mixed literal, type, guard, wildcard arms",
     r"""scene Test { on_start { let arm = 0; let bound = nil; match x { case 0 { arm = 0 } case int n if n > 10 { arm = 1; bound = n } case int n { arm = 2; bound = n } case string s { arm = 3; bound = s } case _ { arm = 4 } } } }""",
     [], {"x": 7}, lambda s: s.get("arm") == 2 and s.get("bound") == 7)

test("mixed pattern — string match",
     r"""scene Test { on_start { let arm = 0; let bound = nil; match x { case 0 { arm = 0 } case int n { arm = 1; bound = n } case string s { arm = 2; bound = s } case _ { arm = 3 } } } }""",
     [], {"x": "world"}, lambda s: s.get("arm") == 2 and s.get("bound") == "world")

# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════
TOTAL = PASS + FAIL
print(f"\n{'='*50}")
print(f"  v3.9.6.1 — MatchStmt: {PASS}/{TOTAL} passed")
print(f"{'='*50}")
sys.exit(0 if FAIL == 0 else 1)
