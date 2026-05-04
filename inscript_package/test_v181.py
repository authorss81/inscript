#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_v181.py  InScript v1.8.1 — Union Types & Optionals

Tests:
  1.  `int | string` — basic union declared and assigned
  2.  Union assignment: both member types accepted
  3.  Union assignment: non-member type rejected
  4.  `int?` shorthand — sugar for `int | nil`
  5.  Nullable param: nil accepted
  6.  Nullable param: non-nil value accepted
  7.  Union in function params
  8.  Union in function return type
  9.  Union narrowing: typeof(x) == "int" narrows inside block
 10.  Union narrowing: typeof(x) == "string" narrows
 11.  `nil` assignable to union containing nil
 12.  Union: `int | float` — int widens to float (compatible)
 13.  Nested union flattening: `(int|string)|bool` == `int|string|bool`
 14.  Single-member union collapses to plain type
 15.  Union struct field
 16.  Analyzer: union type repr
 17.  Runtime: typeof() returns correct string for union-typed values
 18.  Runtime: nil-safe optional chaining on `T?`
 19.  v1.7.4 regression: REPL stability
 20.  v1.7.3 regression: stack traces

Run:  python3 test_v181.py
"""
import sys, io
from interpreter import Interpreter
from analyzer import Analyzer, union_type, optional_type, union_members, \
    T_INT, T_FLOAT, T_STRING, T_BOOL, T_NULL, T_ANY, InScriptType, types_compatible

PASS = FAIL = 0

def ok(name, cond, detail=""):
    global PASS, FAIL
    tag = "OK  " if cond else "FAIL"
    print(f"  {tag}  {name}" + (f"  [{detail}]" if detail else ""))
    if cond: PASS += 1
    else:    FAIL += 1

def section(t): print(f"\n--- {t} ---")

def run(code):
    buf = io.StringIO(); sys.stdout = buf
    try:
        Interpreter().execute(code)
        sys.stdout = sys.__stdout__
        return buf.getvalue().strip(), None
    except Exception as e:
        sys.stdout = sys.__stdout__
        return buf.getvalue().strip(), str(e)

def run_out(code): return run(code)[0]
def run_err(code): return run(code)[1]

def analyze(code):
    """Return list of error strings (empty = clean)."""
    from parser import parse
    prog = parse(code)
    a = Analyzer(no_warn=True)
    try:
        a.analyze(prog)
        return []
    except Exception as e:
        return str(e).splitlines()

def has_error(code): return len(analyze(code)) > 0
def is_clean(code):  return len(analyze(code)) == 0


# ── 1. Basic union declared and assigned ─────────────────────────────────────
section("1. Basic union declaration")

ok("int|string: int value clean",
   is_clean("let x: int | string = 42"))
ok("int|string: string value clean",
   is_clean('let x: int | string = "hello"'))
ok("int|string: bool value error",
   has_error("let x: int | string = true"))

# ── 2. Union assignment: both member types accepted ───────────────────────────
section("2. Union re-assignment")

ok("reassign union int→string clean",
   is_clean('let x: int | string = 42\nx = "hello"'))
ok("reassign union string→int clean",
   is_clean('let x: int | string = "hi"\nx = 99'))
ok("reassign union to bool errors",
   has_error('let x: int | string = 42\nx = true'))

# ── 3. Non-member type rejected ───────────────────────────────────────────────
section("3. Non-member type rejection")

ok("float not in int|string",
   has_error("let x: int | string = 3.14"))
ok("bool not in int|string|float",
   has_error("let x: int | string | float = true"))

# ── 4. `int?` shorthand for `int | nil` ──────────────────────────────────────
section("4. Optional shorthand T?")

ok("int? accepts int",
   is_clean("let x: int? = 42"))
ok("int? accepts nil",
   is_clean("let x: int? = nil"))
ok("int? rejects string",
   has_error('let x: int? = "hello"'))
ok("string? accepts nil",
   is_clean("let x: string? = nil"))
ok("string? accepts string",
   is_clean('let x: string? = "hi"'))

# ── 5–6. Nullable params ─────────────────────────────────────────────────────
section("5-6. Nullable function params")

ok("fn(x: int?) nil arg clean",
   is_clean("fn f(x: int?) { }\nf(nil)"))
ok("fn(x: int?) int arg clean",
   is_clean("fn f(x: int?) { }\nf(42)"))
ok("fn(x: int?) string arg error",
   has_error('fn f(x: int?) { }\nf("bad")'))

# ── 7. Union params ───────────────────────────────────────────────────────────
section("7. Union function params")

ok("fn(x: int|bool) int ok",
   is_clean("fn f(x: int | bool) { }\nf(1)"))
ok("fn(x: int|bool) bool ok",
   is_clean("fn f(x: int | bool) { }\nf(true)"))
ok("fn(x: int|bool) string error",
   has_error('fn f(x: int | bool) { }\nf("bad")'))

# ── 8. Union return type ──────────────────────────────────────────────────────
section("8. Union return type")

ok("fn -> int|string returns int clean",
   is_clean("fn f() -> int | string { return 1 }"))
ok("fn -> int|string returns string clean",
   is_clean('fn f() -> int | string { return "hi" }'))
ok("fn -> int|string returns bool error",
   has_error("fn f() -> int | string { return true }"))

# ── 9-10. Union narrowing via typeof ─────────────────────────────────────────
section("9-10. Union narrowing with typeof")

ok("typeof narrow int clean",
   is_clean("""
fn describe(x: int | string) -> string {
  if typeof(x) == "int" {
    return "number"
  }
  return "text"
}
"""))

ok("typeof narrow string clean",
   is_clean("""
fn f(x: int | string | bool) {
  if typeof(x) == "string" {
    let s: string = x
  }
}
"""))

# Runtime: narrowing doesn't break execution
out, err = run("""
fn describe(x) {
  if typeof(x) == "int" {
    return "number"
  }
  return "text"
}
print(describe(42))
print(describe("hello"))
""")
ok("typeof runtime: int → 'number'",   out == "number\ntext" and err is None, repr(out))

# ── 11. nil assignable to union containing nil ────────────────────────────────
section("11. nil in union")

ok("nil ok in int|nil",        is_clean("let x: int | nil = nil"))
ok("nil ok in string|nil",     is_clean("let x: string | nil = nil"))
ok("nil NOT ok in int|string", has_error("let x: int | string = nil"))

# ── 12. int widens to float in union ─────────────────────────────────────────
section("12. int widens to float inside union")

ok("int compatible with float|string",
   is_clean("let x: float | string = 42"))
ok("int compatible with int|float",
   is_clean("let x: int | float = 3"))

# ── 13. Nested union flattening ───────────────────────────────────────────────
section("13. Nested union flattening")

u1 = union_type(T_INT, T_STRING)
u2 = union_type(u1, T_BOOL)          # (int|string)|bool → int|string|bool
ok("nested union flattens to 3 members", len(u2.params) == 3, repr(u2))
ok("int in flattened union",   T_INT    in u2.params, repr(u2))
ok("string in flattened union",T_STRING in u2.params, repr(u2))
ok("bool in flattened union",  T_BOOL   in u2.params, repr(u2))

# ── 14. Single-member union collapses ─────────────────────────────────────────
section("14. Single-member union collapse")

collapsed = union_type(T_INT)
ok("union_type(int) → int",   collapsed == T_INT, repr(collapsed))

# ── 15. Union struct field ────────────────────────────────────────────────────
section("15. Union in struct fields")

ok("struct union field int ok",
   is_clean("struct S { v: int | string = 0 }"))
ok("struct union field string ok",
   is_clean('struct S { v: int | string = "hi" }'))
ok("struct union field bool error",
   has_error("struct S { v: int | string = true }"))

# ── 16. Analyzer: union type repr ────────────────────────────────────────────
section("16. InScriptType repr")

u = union_type(T_INT, T_STRING, T_BOOL)
ok("union repr correct",  repr(u) == "Union<int, string, bool>", repr(u))

opt = optional_type(T_INT)
ok("optional repr correct", repr(opt) == "Union<int, null>", repr(opt))

ok("union_members on plain type", union_members(T_INT) == [T_INT])
ok("union_members on union",      set(union_members(u)) == {T_INT, T_STRING, T_BOOL})

# ── 17. types_compatible with unions ─────────────────────────────────────────
section("17. types_compatible")

u_is = union_type(T_INT, T_STRING)
ok("int compat with int|string",   types_compatible(u_is, T_INT))
ok("string compat with int|string",types_compatible(u_is, T_STRING))
ok("bool NOT compat with int|string", not types_compatible(u_is, T_BOOL))
ok("null compat with int|nil",     types_compatible(optional_type(T_INT), T_NULL))
ok("null NOT compat with int|string", not types_compatible(u_is, T_NULL))
ok("int compat with float|string (widens)", types_compatible(union_type(T_FLOAT, T_STRING), T_INT))

# ── 18. Runtime: typeof on union-typed values ────────────────────────────────
section("18. Runtime typeof")

out, err = run("""
let x = 42
print(typeof(x))
x = "hello"
print(typeof(x))
""")
ok("typeof(42) == 'int'",       out.split('\n')[0] == "int"    and err is None, repr(out))
ok("typeof('hello') == 'string'",out.split('\n')[1] == "string" and err is None, repr(out))

out, err = run("""
let x = nil
print(typeof(x))
""")
ok("typeof(nil) == 'nil'", out == "nil" and err is None, repr(out))

# ── 19. Runtime: optional chaining on T? ────────────────────────────────────
section("19. Optional chaining on T?")

out, err = run("""
struct Player { name: string = "" }
fn get_name(p) {
  return p?.name
}
let p1 = Player{name: "Alice"}
print(get_name(p1))
print(get_name(nil))
""")
ok("optional chain: non-nil",   "Alice" in (out or "") and err is None, repr(out))
ok("optional chain: nil → nil", "nil" in (out or ""),                   repr(out))

# ── 20. v1.7.4 regression ────────────────────────────────────────────────────
section("20. Regressions: v1.7.4 REPL + v1.7.3 traces")

from interpreter import Interpreter as _I
from errors import InScriptRuntimeError

# REPL env snapshot
class _R:
    def __init__(self):
        self._interp = _I()
        self._interp._env._repl_mode = True
    def eval(self, src):
        from lexer import Lexer; from parser import parse as _p; from errors import InScriptError
        snap = dict(self._interp._env._store)
        try:
            result = self._interp.run(_p(src))
            return result, None
        except InScriptError as e:
            self._interp._env._store = snap
            return None, str(e)
        except Exception as e:
            self._interp._env._store = snap
            return None, str(e)
    def has(self, n): return n in self._interp._env._store
    def get(self, n): return self._interp._env._store.get(n)

r = _R()
r.eval("let x = 10")
_, e = r.eval("let y = x / 0")
ok("v1.7.4: x survives error",    r.has("x"),               "x lost")
ok("v1.7.4: y not leaked",        not r.has("y"),            "y leaked")
r.eval("let x = 99")
ok("v1.7.4: let re-def works",    r.get("x") == 99,          repr(r.get("x")))

_, err = run("let z = null")
ok("v1.7.4: null → E0055",        err is not None and "E0055" in err, repr(err))

_, err = run("fn a() { throw 't' }\nfn b() { a() }\nb()")
ok("v1.7.3: stack trace works",   err is not None and "in a" in err, repr(err))

# ── Summary ───────────────────────────────────────────────────────────────────
total = PASS + FAIL
print(f"""
{'='*58}
  v1.8.1 Test Results: {PASS}/{total} passed
  {'ALL PASS' if FAIL == 0 else f'{FAIL} FAILED'}
{'='*58}
""")
sys.exit(0 if FAIL == 0 else 1)
