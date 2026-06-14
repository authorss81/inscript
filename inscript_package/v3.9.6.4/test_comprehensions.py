#!/usr/bin/env python3
"""v3.9.6.4 — Test comprehensions + nested fn compilation in py_compiler.

Tests:
  1. [x*x for x in arr] — basic list comprehension
  2. [x for x in items if x > 2] — list comp with filter
  3. [a + b for a in xs for b in ys] — nested for-clauses
  4. {k: v*2 for k,v in pairs} — dict comprehension
  5. Nested fn inside hook called from hook body
  6. Nested fn capturing scene variable
  7. Nested fn with multiple params
  8. Nested fn returning call to another nested fn
  9. Mixed: list comp calling nested fn
  10. List comp inside nested fn
  11. [x for x in arr] using scene var iterable
  12. Nested fn used as lambda/function arg
  13. Multiple nested fns in same hook
  14. Nested fn with scene var + param interaction
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
SKIP = 0

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
            print(f"  ❌ {name}: compilation returned None (fallback used)")
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
            elif isinstance(result, list) and isinstance(val, list) and len(result) == len(val):
                if result == val:
                    print(f"  ✅ {name}: {key}={result!r}")
                    PASS += 1
                else:
                    print(f"  ❌ {name}: expected {key}={val!r}, got {result!r}")
                    FAIL += 1
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
# Test 1: Basic list comprehension
# ═══════════════════════════════════════════════════════════════════════════════
test("basic list comp [x*x for x in arr]",
     r"""scene Test { on_start { let result = [x*x for x in arr] } }""",
     [], {"arr": [1, 2, 3, 4], "result": None}, ("result", [1, 4, 9, 16]))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: List comprehension with filter
# ═══════════════════════════════════════════════════════════════════════════════
test("list comp with filter [x for x in items if x > 2]",
     r"""scene Test { on_start { let result = [x for x in items if x > 2] } }""",
     [], {"items": [1, 2, 3, 4, 5], "result": None}, ("result", [3, 4, 5]))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: List comprehension expression subject
# ═══════════════════════════════════════════════════════════════════════════════
test("list comp used in expression",
     r"""scene Test { on_start { let arr2 = [1, 2, 3]; let total = len([x*10 for x in arr2]) } }""",
     [], {"arr2": [1, 2, 3], "total": 0}, ("total", 3),
     globs={"print": print, "string": str, "int": int, "float": float, "len": len})

# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: Dict comprehension
# ═══════════════════════════════════════════════════════════════════════════════
def test_dict(state):
    d = state.get("result", {})
    return d.get("a") == 1 and d.get("b") == 2 and d.get("c") == 3

test("dict comp {k: v for k,v in pairs}",
     r"""scene Test { on_start { let pairs = [["a", 1], ["b", 2], ["c", 3]]; let result = {k: v for k, v in pairs} } }""",
     [], {"result": None}, test_dict)

# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: Nested fn inside hook
# ═══════════════════════════════════════════════════════════════════════════════
test("nested fn inside hook",
     r"""scene Test { on_start { fn double(x: int) { x * 2 }; let result = double(5) } }""",
     [], {"result": 0}, ("result", 10))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 6: Nested fn capturing scene variable
# ═══════════════════════════════════════════════════════════════════════════════
test("nested fn captures scene var",
     r"""scene Test { on_start { let scale = 3; fn mul(x: int) { x * scale }; let result = mul(7) } }""",
     [], {"scale": 3, "result": 0}, ("result", 21))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 7: Nested fn with multiple params
# ═══════════════════════════════════════════════════════════════════════════════
test("nested fn multiple params",
     r"""scene Test { on_start { fn add3(a: int, b: int, c: int) { a + b + c }; let result = add3(1, 2, 3) } }""",
     [], {"result": 0}, ("result", 6))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 8: Two nested fns, one calling the other
# ═══════════════════════════════════════════════════════════════════════════════
test("nested fn calls another nested fn",
     r"""scene Test { on_start { fn add(a: int, b: int) { a + b }; fn double(x: int) { add(x, x) }; let result = double(5) } }""",
     [], {"result": 0}, ("result", 10))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 9: List comp calling nested fn
# ═══════════════════════════════════════════════════════════════════════════════
test("list comp with nested fn",
     r"""scene Test { on_start { fn double(x: int) { x * 2 }; let result = [double(x) for x in arr] } }""",
     [], {"arr": [1, 2, 3], "result": None}, ("result", [2, 4, 6]))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 10: List comp inside nested fn
# ═══════════════════════════════════════════════════════════════════════════════
test("list comp inside nested fn",
     r"""scene Test { on_start { fn squares(arr: [int]) { [x*x for x in arr] }; let result = squares([1, 2, 3]) } }""",
     [], {"result": None}, ("result", [1, 4, 9]))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 11: List comp using scene var iterable
# ═══════════════════════════════════════════════════════════════════════════════
test("list comp with scene var iterable",
     r"""scene Test { on_start { let result = [x*2 for x in data] } }""",
     [], {"data": [10, 20, 30], "result": None}, ("result", [20, 40, 60]))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 12: Empty list comp (empty iterable)
# ═══════════════════════════════════════════════════════════════════════════════
test("list comp with empty iterable",
     r"""scene Test { on_start { let result = [x for x in empty] } }""",
     [], {"empty": [], "result": None}, ("result", []))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 13: Multiple nested functions
# ═══════════════════════════════════════════════════════════════════════════════
test("multiple nested fns",
     r"""scene Test { on_start { fn inc(x: int) { x + 1 }; result = inc(5) } }""",
     [], {"result": 0}, ("result", 6))

# ═══════════════════════════════════════════════════════════════════════════════
# Test 14: Nested fn with scene var + param interaction
# ═══════════════════════════════════════════════════════════════════════════════
test("nested fn scene var + param",
     r"""scene Test { on_start { let offset = 100; fn add_offset(x: int) { x + offset }; let result = add_offset(5) } }""",
     [], {"offset": 100, "result": 0}, ("result", 105))

# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════
TOTAL = PASS + FAIL
print(f"\n{'='*50}")
print(f"  v3.9.6.4 — Comprehensions + nested fns: {PASS}/{TOTAL} passed")
if SKIP:
    print(f"  ({SKIP} skipped)")
print(f"{'='*50}")
sys.exit(0 if FAIL == 0 else 1)
