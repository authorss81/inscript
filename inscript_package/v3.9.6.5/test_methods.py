#!/usr/bin/env python3
"""v3.9.6.5 — Test method calls + named args in py_compiler.

Tests:
  1. obj.method() — basic method call
  2. obj.method(args) — method with positional args
  3. Named/keyword arguments obj.method(a: 1, b: 2)
  4. Named args with scene vars
  5. Chained method calls obj.set_val(5).get_val()
  6. Triple-chained method
  7. Method returning callable (higher-order)
  8. Method on scene var (assigned from another var)
  9. Multi-arg method
  10. Method with side effect
  11. Method on method result (stored in var)
  12. Method with scene var as arg
  13. Method call on nested fn return
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


class Obj:
    def __init__(self):
        self.val = 0
    def get_val(self):
        return self.val
    def add(self, x):
        return self.val + x
    def set_val(self, v):
        self.val = v
        return self
    def make_adder(self, n):
        def adder(x):
            return n + x
        return adder
    def add_mul(self, a, b, c):
        return a + b + c
    def triple(self):
        self.val *= 3
        return self

_g = {"Obj": Obj, "print": print, "string": str, "int": int, "float": float}

# Test 1: Basic method call
test("basic method call obj.get_val()",
     r"""scene Test { on_start { let result = obj.get_val() } }""",
     [], {"obj": Obj(), "result": None}, ("result", 0), globs=_g)

# Test 2: Method with positional args
test("method with args obj.add(5)",
     r"""scene Test { on_start { let result = obj.add(5) } }""",
     [], {"obj": Obj(), "result": None}, ("result", 5), globs=_g)

# Test 3: Named/keyword arguments
test("named args obj.add_mul(a: 1, b: 2, c: 3)",
     r"""scene Test { on_start { let result = obj.add_mul(a: 1, b: 2, c: 3) } }""",
     [], {"obj": Obj(), "result": None}, ("result", 6), globs=_g)

# Test 4: Named args with scene vars
test("named args with scene vars",
     r"""scene Test { on_start { result = obj.add_mul(a: a_val, b: b_val, c: c_val) } }""",
     [], {"obj": Obj(), "a_val": 1, "b_val": 2, "c_val": 3, "result": None}, ("result", 6), globs=_g)

# Test 5: Chained method calls (returns self)
test("chained method obj.set_val(5).get_val()",
     r"""scene Test { on_start { let result = obj.set_val(5).get_val() } }""",
     [], {"obj": Obj(), "result": None}, ("result", 5), globs=_g)

# Test 6: Triple-chained method
test("triple-chained method",
     r"""scene Test { on_start { let result = obj.set_val(2).triple().get_val() } }""",
     [], {"obj": Obj(), "result": None}, ("result", 6), globs=_g)

# Test 7: Method returning callable (higher-order)
test("method returns callable obj.make_adder(3)(7)",
     r"""scene Test { on_start { let result = obj.make_adder(3)(7) } }""",
     [], {"obj": Obj(), "result": None}, ("result", 10), globs=_g)

# Test 8: Method on scene var (assigned from another var)
test("method on scene var",
     r"""scene Test { on_start { let myobj = obj; let result = myobj.get_val() } }""",
     [], {"obj": Obj(), "result": None}, ("result", 0), globs=_g)

# Test 9: Multi-arg method
test("multi-arg method",
     r"""scene Test { on_start { let result = obj.add_mul(1, 2, 3) } }""",
     [], {"obj": Obj(), "result": None}, ("result", 6), globs=_g)

# Test 10: Method with side effect
test("method with side effect",
     r"""scene Test { on_start { obj.set_val(42); result = obj.get_val() } }""",
     [], {"obj": Obj(), "result": None}, ("result", 42), globs=_g)

# Test 11: Method on method result (stored in var)
test("method on method result",
     r"""scene Test { on_start { let r = obj.set_val(10); result = r.get_val() } }""",
     [], {"obj": Obj(), "result": None}, ("result", 10), globs=_g)

# Test 12: Method with scene var as arg
test("method with scene var arg",
     r"""scene Test { on_start { result = obj.add(val) } }""",
     [], {"obj": Obj(), "val": 7, "result": None}, ("result", 7), globs=_g)

# Test 13: Method call on nested fn return
test("method call on nested fn return",
     r"""scene Test { on_start { fn get_o() { obj }; let o = get_o(); result = o.get_val() } }""",
     [], {"obj": Obj(), "result": None}, ("result", 0), globs=_g)

TOTAL = PASS + FAIL
print(f"\n{'='*50}")
print(f"  v3.9.6.5 — Methods + named args: {PASS}/{TOTAL} passed")
print(f"{'='*50}")
sys.exit(0 if FAIL == 0 else 1)
