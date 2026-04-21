#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_v120.py — InScript v1.2.0 feature tests

Covers:
  • Generic type enforcement  (Stack<int> rejects non-int)
  • Unused variable warnings  (analyzer.py)
  • Unreachable code warnings (analyzer.py)
  • mat4 stdlib module        (stdlib_game.py)

Run:  python3 test_v120.py
"""

import sys, math, traceback
from interpreter import Interpreter
from analyzer import Analyzer
from parser import parse
from errors import InScriptRuntimeError

# ─── helpers ──────────────────────────────────────────────────────────────────

PASS = 0; FAIL = 0

def _run(src):
    i = Interpreter()
    i.execute(src)
    return i

def _err(src):
    """Run and expect InScriptRuntimeError. Returns the exception."""
    try:
        Interpreter().execute(src)
        return None   # no error — caller will FAIL
    except InScriptRuntimeError as e:
        return e

def _warns(src, kind=None, no_warn_unused=False):
    prog = parse(src)
    a = Analyzer(src.splitlines(), no_warn_unused=no_warn_unused)
    a.analyze(prog)
    if kind:
        return [w for w in a._warnings if w.kind == kind]
    return a._warnings

def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  ✅ {name}")
        PASS += 1
    else:
        print(f"  ❌ {name}{' — '+detail if detail else ''}")
        FAIL += 1

def section(title):
    print(f"\n{'─'*60}\n  {title}\n{'─'*60}")

# ─── 1. Generic type enforcement ──────────────────────────────────────────────

section("1. Generic type enforcement")

STACK = """
struct Stack<T> {
    items: [] = []
    fn push(val: T) { self.items = self.items + [val] }
    fn peek() { return self.items[self.items.len() - 1] }
    fn size() { return self.items.len() }
}
"""

# 1a: correct type accepted
try:
    i = _run(STACK + """
let s = Stack<int>{}
s.push(1)
s.push(2)
s.push(3)
""")
    ok("Stack<int> accepts int", True)
except Exception as e:
    ok("Stack<int> accepts int", False, str(e))

# 1b: wrong type rejected at push
e = _err(STACK + """
let s = Stack<int>{}
s.push("hello")
""")
ok("Stack<int> rejects string",
   e is not None and "Generic type error" in str(e) and "int" in str(e))

# 1c: float rejected from Stack<int>
e = _err(STACK + """
let s = Stack<int>{}
s.push(3.14)
""")
ok("Stack<int> rejects float",
   e is not None and "Generic type error" in str(e))

# 1d: Stack<string> accepts string
try:
    _run(STACK + """
let s = Stack<string>{}
s.push("hello")
s.push("world")
""")
    ok("Stack<string> accepts string", True)
except Exception as e:
    ok("Stack<string> accepts string", False, str(e))

# 1e: Stack<string> rejects int
e = _err(STACK + """
let s = Stack<string>{}
s.push(42)
""")
ok("Stack<string> rejects int",
   e is not None and "Generic type error" in str(e))

# 1f: Stack<float> accepts float
try:
    _run(STACK + """
let s = Stack<float>{}
s.push(1.5)
s.push(2.7)
""")
    ok("Stack<float> accepts float", True)
except Exception as e:
    ok("Stack<float> accepts float", False, str(e))

# 1g: multi type-param Pair<A,B>
PAIR = """
struct Pair<A, B> {
    first: [] = []
    second: [] = []
    fn set_first(v: A)  { self.first  = [v] }
    fn set_second(v: B) { self.second = [v] }
}
"""
try:
    _run(PAIR + """
let p = Pair<int, string>{}
p.set_first(42)
p.set_second("hello")
""")
    ok("Pair<int,string> accepts correct types", True)
except Exception as e:
    ok("Pair<int,string> accepts correct types", False, str(e))

e = _err(PAIR + """
let p = Pair<int, string>{}
p.set_first("wrong")
""")
ok("Pair<int,string>.set_first rejects string",
   e is not None and "Generic type error" in str(e))

e = _err(PAIR + """
let p = Pair<int, string>{}
p.set_second(99)
""")
ok("Pair<int,string>.set_second rejects int",
   e is not None and "Generic type error" in str(e))

# 1h: non-generic struct unaffected
try:
    _run("""
struct Box {
    value: int = 0
    fn set(v: int) { self.value = v }
}
let b = Box{}
b.set(10)
""")
    ok("Non-generic struct unaffected", True)
except Exception as e:
    ok("Non-generic struct unaffected", False, str(e))

# ─── 2. Unused variable warnings ──────────────────────────────────────────────

section("2. Unused variable warnings")

# 2a: unused local is warned
w = _warns("""
fn foo() {
    let x = 5
    let y = 10
    return y
}
""", "unused")
ok("Unused 'x' warned, used 'y' not warned",
   len(w) == 1 and "'x'" in w[0].message)

# 2b: _-prefixed suppresses warning
w = _warns("""
fn foo() {
    let _unused = 42
    return 1
}
""", "unused")
ok("'_unused' suppresses warning", len(w) == 0)

# 2c: --no-warn-unused flag suppresses
w = _warns("""
fn foo() {
    let x = 5
    return 1
}
""", "unused", no_warn_unused=True)
ok("--no-warn-unused flag suppresses", len(w) == 0)

# 2d: global scope not warned
w = _warns("let config = 42\nlet debug = true", "unused")
ok("Global vars not warned", len(w) == 0)

# 2e: function params not warned
w = _warns("""
fn add(a: int, b: int) -> int {
    return a + b
}
""", "unused")
ok("Function params not warned as unused", len(w) == 0)

# 2f: used-in-later-scope counts
w = _warns("""
fn foo() {
    let x = 5
    if x > 3 {
        let y = x + 1
        return y
    }
    return 0
}
""", "unused")
ok("Variable used in nested scope counts as used", len(w) == 0)

# 2g: multiple unused all warned
w = _warns("""
fn bar() {
    let a = 1
    let b = 2
    let c = 3
    return 0
}
""", "unused")
ok("Multiple unused all warned", len(w) == 3)

# 2h: const unused also warned
w = _warns("""
fn baz() {
    const MAX = 100
    return 0
}
""", "unused")
ok("Unused const warned", len(w) == 1 and "'MAX'" in w[0].message)

# ─── 3. Unreachable code warnings ─────────────────────────────────────────────

section("3. Unreachable code warnings")

# 3a: code after return
w = _warns("""
fn foo() -> int {
    return 1
    let x = 2
}
""", "unreachable")
ok("Code after return warned", len(w) == 1)

# 3b: code after break
w = _warns("""
fn foo() {
    for i in 0..5 {
        break
        print(i)
    }
}
""", "unreachable")
ok("Code after break warned", len(w) == 1)

# 3c: code after continue
w = _warns("""
fn foo() {
    for i in 0..5 {
        continue
        print(i)
    }
}
""", "unreachable")
ok("Code after continue warned", len(w) == 1)

# 3d: code after throw
w = _warns("""
fn foo() {
    throw "error"
    let x = 1
}
""", "unreachable")
ok("Code after throw warned", len(w) == 1)

# 3e: no false positive — return at end
w = _warns("""
fn foo() -> int {
    let x = 1
    return x
}
""", "unreachable")
ok("No false positive: return at end", len(w) == 0)

# 3f: multiple dead statements all warned
w = _warns("""
fn foo() {
    return 1
    let a = 2
    let b = 3
    let c = 4
}
""", "unreachable")
ok("Multiple dead statements all warned", len(w) == 3)

# 3g: dead code still analyzed (inner errors caught)
# The dead stmt is visited so undefined-name errors can still fire
w = _warns("""
fn foo() -> int {
    let result = 42
    return result
    let dead = result
}
""", "unreachable")
ok("Dead code still visited for analysis", len(w) == 1)

# ─── 4. mat4 stdlib module ────────────────────────────────────────────────────

section("4. mat4 stdlib module")

from stdlib_game import (
    _mat4_identity, _mat4_zero, _mat4_from_list,
    _mat4_translate, _mat4_scale,
    _mat4_rotate_x, _mat4_rotate_y, _mat4_rotate_z, _mat4_rotate_axis,
    _mat4_mul, _mat4_mul_vec4,
    _mat4_transpose, _mat4_inverse, _mat4_det,
    _mat4_perspective, _mat4_ortho, _mat4_look_at,
    _mat4_to_array, _mat4_get,
)

def near(a, b, eps=1e-6):
    return abs(a - b) < eps

def mat_near_identity(m, eps=1e-6):
    a = m._m
    for col in range(4):
        for row in range(4):
            expected = 1.0 if row == col else 0.0
            if abs(a[col*4+row] - expected) > eps:
                return False, (row, col, a[col*4+row], expected)
    return True, None

# 4a: identity diagonal = 1, off-diag = 0
I = _mat4_identity()
ok("identity() diagonal is 1", all(I._m[i*4+i] == 1.0 for i in range(4)))
ok("identity() off-diagonal is 0", all(
    I._m[col*4+row] == 0.0 for col in range(4) for row in range(4) if row != col))

# 4b: zero matrix
Z = _mat4_zero()
ok("zero() all zeros", all(v == 0.0 for v in Z._m))

# 4c: from_array round-trip
data = list(range(16))
M = _mat4_from_list([float(x) for x in data])
ok("from_array round-trip", _mat4_to_array(M) == [float(x) for x in data])

# 4d: translate sets correct column
T = _mat4_translate(3.0, 5.0, 7.0)
a = T._m
ok("translate(3,5,7) col3 = (3,5,7,1)",
   near(a[12], 3) and near(a[13], 5) and near(a[14], 7) and near(a[15], 1))
ok("translate doesn't affect rotation part",
   near(a[0], 1) and near(a[5], 1) and near(a[10], 1))

# 4e: scale diagonal
S = _mat4_scale(2.0, 3.0, 4.0)
ok("scale(2,3,4) diagonal", near(S._m[0], 2) and near(S._m[5], 3) and near(S._m[10], 4))

# 4f: rotate_z(0) = identity
Rz0 = _mat4_rotate_z(0.0)
is_id, bad = mat_near_identity(Rz0)
ok("rotate_z(0) = identity", is_id)

# 4g: rotate_z(π/2) maps (1,0,0) → (0,1,0)
Rz90 = _mat4_rotate_z(math.pi / 2)
v = _mat4_mul_vec4(Rz90, [1.0, 0.0, 0.0, 0.0])
ok("rotate_z(π/2) maps (1,0,0)→(0,1,0)", near(v[0], 0) and near(v[1], 1) and near(v[2], 0))

# 4h: rotate_x(π/2) maps (0,1,0) → (0,0,1)
Rx90 = _mat4_rotate_x(math.pi / 2)
v = _mat4_mul_vec4(Rx90, [0.0, 1.0, 0.0, 0.0])
ok("rotate_x(π/2) maps (0,1,0)→(0,0,1)", near(v[0], 0) and near(v[1], 0) and near(v[2], 1))

# 4i: rotate_y(π/2) maps (0,0,1) → (1,0,0)  [right-hand rule: z→x]
Ry90 = _mat4_rotate_y(math.pi / 2)
v = _mat4_mul_vec4(Ry90, [0.0, 0.0, 1.0, 0.0])
ok("rotate_y(π/2) maps (0,0,1)→(1,0,0)", near(v[0], 1) and near(v[1], 0) and near(v[2], 0))

# 4j: mul(I, M) = M
M2 = _mat4_translate(1, 2, 3)
result = _mat4_mul(_mat4_identity(), M2)
ok("mul(I, M) = M", result._m == M2._m)

# 4k: mul(M, I) = M
result2 = _mat4_mul(M2, _mat4_identity())
ok("mul(M, I) = M", result2._m == M2._m)

# 4l: mul_vec4 — translate point
T2 = _mat4_translate(10.0, 20.0, 30.0)
v = _mat4_mul_vec4(T2, [0.0, 0.0, 0.0, 1.0])
ok("mul_vec4: translate point (0,0,0) by (10,20,30)",
   near(v[0], 10) and near(v[1], 20) and near(v[2], 30) and near(v[3], 1))

# 4m: mul_vec4 — direction (w=0) not affected by translate
v = _mat4_mul_vec4(T2, [1.0, 0.0, 0.0, 0.0])
ok("mul_vec4: direction (w=0) not translated",
   near(v[0], 1) and near(v[1], 0) and near(v[2], 0) and near(v[3], 0))

# 4n: transpose of identity = identity
Tr = _mat4_transpose(_mat4_identity())
is_id, _ = mat_near_identity(Tr)
ok("transpose(identity) = identity", is_id)

# 4o: transpose(transpose(M)) = M
M3 = _mat4_translate(1, 2, 3)
TT = _mat4_transpose(_mat4_transpose(M3))
ok("transpose(transpose(M)) = M", all(near(TT._m[i], M3._m[i]) for i in range(16)))

# 4p: transpose swaps rows/cols
T3 = _mat4_translate(7.0, 0.0, 0.0)
Tt = _mat4_transpose(T3)
ok("transpose moves col3 to row3",
   near(_mat4_get(T3, 0, 3), 7.0) and near(_mat4_get(Tt, 3, 0), 7.0))

# 4q: det(identity) = 1
ok("det(identity) = 1.0", near(_mat4_det(_mat4_identity()), 1.0))

# 4r: det(scale(2,3,4)) = 2*3*4 = 24
ok("det(scale(2,3,4)) = 24", near(_mat4_det(_mat4_scale(2,3,4)), 24.0))

# 4s: det(zero) = 0
ok("det(zero) = 0", near(_mat4_det(_mat4_zero()), 0.0))

# 4t: inverse(I) = I
inv_I = _mat4_inverse(_mat4_identity())
is_id, _ = mat_near_identity(inv_I)
ok("inverse(identity) = identity", is_id)

# 4u: M * inv(M) = I  (translate)
T4 = _mat4_translate(3, 5, 7)
prod = _mat4_mul(T4, _mat4_inverse(T4))
is_id, _ = mat_near_identity(prod)
ok("translate * inv(translate) = identity", is_id)

# 4v: M * inv(M) = I  (complex transform)
C = _mat4_mul(_mat4_mul(_mat4_translate(1,2,3), _mat4_scale(2,3,4)),
              _mat4_rotate_z(0.5))
prod = _mat4_mul(C, _mat4_inverse(C))
is_id, _ = mat_near_identity(prod, eps=1e-5)
ok("complex M * inv(M) = identity", is_id)

# 4w: inverse of non-invertible raises
try:
    _mat4_inverse(_mat4_zero())
    ok("inverse(zero) raises ValueError", False)
except ValueError:
    ok("inverse(zero) raises ValueError", True)

# 4x: rotate_axis(y, π/2) same as rotate_y(π/2)
Raxis = _mat4_rotate_axis(0, 1, 0, math.pi / 2)
Ry    = _mat4_rotate_y(math.pi / 2)
ok("rotate_axis(Y,π/2) == rotate_y(π/2)",
   all(near(Raxis._m[i], Ry._m[i], 1e-6) for i in range(16)))

# 4y: perspective matrix non-zero
P = _mat4_perspective(math.radians(60), 16/9, 0.1, 1000.0)
ok("perspective() non-trivial", not all(v == 0 for v in P._m))
ok("perspective() P*inv(P)=I", (lambda p: (lambda ok_, _: ok_)(*mat_near_identity(p, 1e-4)))(
    _mat4_mul(P, _mat4_inverse(P))))

# 4z: from InScript (import "mat4" as m4 syntax)
try:
    _run("""
import "mat4" as m4
let I = m4.identity()
let T = m4.translate(1.0, 2.0, 3.0)
let M = m4.mul(T, m4.identity())
let v = m4.mul_vec4(T, [0.0, 0.0, 0.0, 1.0])
let d = m4.det(I)
""")
    ok("mat4 usable from InScript", True)
except Exception as e:
    ok("mat4 usable from InScript", False, str(e))

# ─── Summary ─────────────────────────────────────────────────────────────────

total = PASS + FAIL
print(f"""
{'═'*60}
  v1.2.0 Test Results: {PASS}/{total} passed
  {'✅ ALL PASS' if FAIL == 0 else f'❌ {FAIL} FAILED'}
{'═'*60}
""")
sys.exit(0 if FAIL == 0 else 1)
