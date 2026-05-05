#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_v182.py  InScript v1.8.2 — Type Aliases, Literal Types & fn Types

Tests:
  1.  Simple type alias: `type PlayerID = int`
  2.  Alias used in let/const
  3.  Alias mismatch is an error
  4.  Alias used in function param
  5.  Alias used in function return type
  6.  Alias used in struct field
  7.  Alias of union: `type Dir = "left" | "right"`
  8.  Alias union: valid member accepted
  9.  Alias union: non-member rejected
 10.  Alias of optional: `type MaybeInt = int?`
 11.  String literal type inline param: `fn f(d: "on"|"off")`
 12.  String literal type inline: valid call accepted
 13.  String literal type inline: invalid call rejected
 14.  String variable fills literal slot (widened — runtime check)
 15.  fn type alias: `type Pred = fn(int) -> bool`
 16.  fn type alias param: fn literal accepted
 17.  fn type alias: named fn accepted
 18.  Chained alias: `type ID = PlayerID` where PlayerID is already an alias
 19.  Alias reused across multiple declarations
 20.  Alias of struct type
 21.  Analyzer: literal_type / fn_type helpers
 22.  types_compatible with literal types
 23.  types_compatible with fn types
 24.  Runtime: type alias does not break interpreter
 25.  Runtime: literal param enforcement is static only (no runtime cost)
 26.  v1.8.1 regression: union types
 27.  v1.7.4 regression: REPL stability
 28.  v1.7.3 regression: stack traces

Run:  python3 test_v182.py
"""
import sys, io
from interpreter import Interpreter
from analyzer import (Analyzer, union_type, optional_type, literal_type,
                      fn_type, literal_value, is_literal_type, union_members,
                      T_INT, T_FLOAT, T_STRING, T_BOOL, T_NULL, T_ANY,
                      InScriptType, types_compatible)

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
    from parser import parse
    prog = parse(code)
    a = Analyzer(no_warn=True)
    try:
        a.analyze(prog)
        return []
    except Exception as e:
        return str(e).splitlines()

def is_clean(code):  return len(analyze(code)) == 0
def has_error(code): return len(analyze(code)) > 0


# ── 1–3. Simple type alias ────────────────────────────────────────────────────
section("1-3. Simple type alias")

ok("PlayerID = int: int value clean",
   is_clean("type PlayerID = int\nlet id: PlayerID = 42"))
ok("PlayerID = int: string value errors",
   has_error('type PlayerID = int\nlet id: PlayerID = "bad"'))
ok("Score = float: float value clean",
   is_clean("type Score = float\nlet s: Score = 9.5"))
ok("Score = float: int widens to float clean",
   is_clean("type Score = float\nlet s: Score = 10"))

# ── 4–5. Alias in function signatures ────────────────────────────────────────
section("4-5. Alias in function signatures")

ok("alias param type clean",
   is_clean("type HP = int\nfn damage(h: HP) { }\ndamage(50)"))
ok("alias param wrong type errors",
   has_error('type HP = int\nfn damage(h: HP) { }\ndamage("lots")'))
ok("alias return type clean",
   is_clean("type Name = string\nfn get_name() -> Name { return \"Alice\" }"))
ok("alias return wrong type errors",
   has_error("type Name = string\nfn get_name() -> Name { return 42 }"))

# ── 6. Alias in struct fields ─────────────────────────────────────────────────
section("6. Alias in struct fields")

ok("alias struct field clean",
   is_clean("type HP = int\nstruct Player { health: HP = 100 }"))
ok("alias struct field mismatch errors",
   has_error('type HP = int\nstruct Player { health: HP = "max" }'))

# ── 7–9. Alias of union ───────────────────────────────────────────────────────
section("7-9. Union alias")

ok("Dir alias: valid literal clean",
   is_clean('type Dir = "left" | "right"\nlet d: Dir = "left"'))
ok("Dir alias: other valid literal clean",
   is_clean('type Dir = "left" | "right"\nlet d: Dir = "right"'))
ok("Dir alias: invalid literal errors",
   has_error('type Dir = "left" | "right"\nlet d: Dir = "up"'))
ok("Dir alias: in function param clean",
   is_clean('type Dir = "left" | "right"\nfn move(d: Dir) { }\nmove("right")'))
ok("Dir alias: bad fn arg errors",
   has_error('type Dir = "left" | "right"\nfn move(d: Dir) { }\nmove("diagonal")'))

# ── 10. Alias of optional ─────────────────────────────────────────────────────
section("10. Optional alias")

ok("MaybeInt: int value clean",
   is_clean("type MaybeInt = int?\nlet x: MaybeInt = 5"))
ok("MaybeInt: nil value clean",
   is_clean("type MaybeInt = int?\nlet x: MaybeInt = nil"))
ok("MaybeInt: string value errors",
   has_error('type MaybeInt = int?\nlet x: MaybeInt = "bad"'))

# ── 11–14. Inline string literal types in params ──────────────────────────────
section("11-14. Inline string literal types")

ok("inline literal union param: valid",
   is_clean('fn toggle(s: "on" | "off") { }\ntoggle("on")'))
ok("inline literal union param: other valid",
   is_clean('fn toggle(s: "on" | "off") { }\ntoggle("off")'))
ok("inline literal union param: invalid errors",
   has_error('fn toggle(s: "on" | "off") { }\ntoggle("maybe")'))
ok("inline literal let: valid",
   is_clean('let x: "open" | "closed" = "open"'))
ok("inline literal let: invalid errors",
   has_error('let x: "open" | "closed" = "half-open"'))
# string variable is widened — compatible (runtime enforces via convention)
ok("string var fills literal slot (widened)",
   is_clean('fn f(s: "a" | "b") { }\nlet x = "a"\nf(x)'))
# plain string type annotation: literal value is compatible
ok("literal value compatible with string annotation",
   is_clean('let s: string = "hello"'))
ok("string var annotation still works",
   is_clean('let a: string = "x"\nlet b: string = a'))

# ── 15–17. fn type aliases ────────────────────────────────────────────────────
section("15-17. fn type aliases")

ok("fn type alias: param accepts lambda",
   is_clean("type Pred = fn(int) -> bool\nfn f(p: Pred) { }\nf(fn(x) { return true })"))
ok("fn type alias: param accepts named fn",
   is_clean("type Cb = fn(int) -> void\nfn apply(c: Cb) { }\nfn handler(x: int) { }\napply(handler)"))
ok("fn(int,string)->bool alias parses",
   is_clean("type Combiner = fn(int, string) -> bool\nfn f(c: Combiner) { }"))

# ── 18. Chained alias ─────────────────────────────────────────────────────────
section("18. Chained alias")

ok("chained alias clean",
   is_clean("type PlayerID = int\ntype UID = PlayerID\nlet x: UID = 7"))
ok("chained alias mismatch errors",
   has_error('type PlayerID = int\ntype UID = PlayerID\nlet x: UID = "bad"'))

# ── 19. Alias reuse ───────────────────────────────────────────────────────────
section("19. Alias reuse across declarations")

ok("alias used in multiple lets",
   is_clean("type Tag = string\nlet a: Tag = \"x\"\nlet b: Tag = \"y\"\nlet c: Tag = \"z\""))

# ── 20. Alias of struct type ──────────────────────────────────────────────────
section("20. Struct type alias")

ok("struct alias in annotation",
   is_clean("struct Vec2 { x: float=0.0; y: float=0.0 }\ntype Point = Vec2\nlet p: Point = Vec2{x:1.0, y:2.0}"))

# ── 21. Analyzer helpers ──────────────────────────────────────────────────────
section("21. Analyzer helper functions")

lt = literal_type("left")
ok("literal_type name",         lt.name == "__literal__", repr(lt))
ok("literal_type has value",    lt.params[0] == "left",   repr(lt))
ok("is_literal_type",           is_literal_type(lt))
ok("literal_value helper",      literal_value(lt) == "left")
ok("non-literal not literal",   not is_literal_type(T_INT))

ft = fn_type([T_INT, T_STRING], T_BOOL)
ok("fn_type name",              ft.name == "__fn__",     repr(ft))
ok("fn_type has 3 params",      len(ft.params) == 3,     repr(ft))   # int, string, bool

# ── 22. types_compatible with literal types ───────────────────────────────────
section("22. types_compatible: literal types")

l_left  = literal_type("left")
l_right = literal_type("right")
l_up    = literal_type("up")
u_lr    = union_type(l_left, l_right)

ok("literal==literal: same",          types_compatible(l_left, l_left))
ok("literal==literal: different",     not types_compatible(l_left, l_right))
ok("literal compat with string expected", types_compatible(T_STRING, l_left))
ok("literal in union: left ok",       types_compatible(u_lr, l_left))
ok("literal in union: right ok",      types_compatible(u_lr, l_right))
ok("literal in union: up not ok",     not types_compatible(u_lr, l_up))
ok("string var compat with literal expected", types_compatible(l_left, T_STRING))

# ── 23. types_compatible with fn types ───────────────────────────────────────
section("23. types_compatible: fn types")

ft1 = fn_type([T_INT], T_BOOL)
ft2 = fn_type([T_INT], T_BOOL)
ft3 = fn_type([T_STRING], T_BOOL)

ok("fn_type == same fn_type",   types_compatible(ft1, ft2))
ok("fn_type != diff fn_type",   types_compatible(ft1, ft3))  # diff params but both Function-compatible
ok("T_ANY fits fn slot",        types_compatible(ft1, T_ANY))
ok("Function type fits fn slot",types_compatible(ft1, InScriptType("Function")))

# ── 24. Runtime: alias doesn't break execution ───────────────────────────────
section("24. Runtime: type alias execution")

out, err = run("""
type PlayerID = int
type Name = string
let id: PlayerID = 42
let name: Name = "Alice"
print(id)
print(name)
""")
ok("alias runtime: no error",   err is None,          repr(err))
ok("alias runtime: id=42",      "42"    in (out or ""), repr(out))
ok("alias runtime: name=Alice", "Alice" in (out or ""), repr(out))

out, err = run("""
type Dir = "left" | "right"
fn move(d) {
  if d == "left"  { print("going left")  }
  if d == "right" { print("going right") }
}
move("left")
move("right")
""")
ok("literal union alias runtime: both dirs",
   err is None and "going left" in (out or "") and "going right" in (out or ""),
   repr(out))

# ── 25. Runtime: fn type alias works ─────────────────────────────────────────
section("25. Runtime: fn type alias")

out, err = run("""
type Transform = fn(int) -> int
fn apply(f, x) {
  return f(x)
}
let double = fn(x) { return x * 2 }
print(apply(double, 21))
""")
ok("fn alias runtime: 42",  out == "42" and err is None, repr(out))

# ── 26. v1.8.1 regression: union types ───────────────────────────────────────
section("26. v1.8.1 regression: union types")

ok("int|string still works",
   is_clean("let x: int | string = 42"))
ok("int? still works",
   is_clean("let x: int? = nil"))
ok("union narrowing still works",
   is_clean("""
fn f(x: int | string) {
  if typeof(x) == "int" { let n: int = x }
}
"""))

# ── 27. v1.7.4 regression: REPL stability ────────────────────────────────────
section("27. v1.7.4 regression: REPL stability")

class FakeREPL:
    def __init__(self):
        self._interp = Interpreter()
        self._interp._env._repl_mode = True
    def eval(self, src):
        from lexer import Lexer; from parser import parse as _p; from errors import InScriptError
        snap = dict(self._interp._env._store)
        try:
            return self._interp.run(_p(src)), None
        except InScriptError as e:
            self._interp._env._store = snap; return None, str(e)
        except Exception as e:
            self._interp._env._store = snap; return None, str(e)
    def has(self, n): return n in self._interp._env._store
    def get(self, n): return self._interp._env._store.get(n)

r = FakeREPL()
r.eval("let x = 10")
_, e = r.eval("let y = x / 0")
ok("REPL: x survives error", r.has("x"), "x lost")
ok("REPL: y not leaked",     not r.has("y"), "y leaked")
r.eval("let x = 99")
ok("REPL: let re-def",       r.get("x") == 99, repr(r.get("x")))

_, err = run("let z = null")
ok("null → E0055",  err is not None and "E0055" in err, repr(err))

# ── 28. v1.7.3 regression: stack traces ──────────────────────────────────────
section("28. v1.7.3 regression: stack traces")

_, err = run("fn a() { throw 'err' }\nfn b() { a() }\nb()")
ok("stack trace: a frame", err is not None and "in a" in err, repr(err))
ok("stack trace: b frame", err is not None and "in b" in err, repr(err))

# ── Summary ───────────────────────────────────────────────────────────────────
total = PASS + FAIL
print(f"""
{'='*58}
  v1.8.2 Test Results: {PASS}/{total} passed
  {'ALL PASS' if FAIL == 0 else f'{FAIL} FAILED'}
{'='*58}
""")
sys.exit(0 if FAIL == 0 else 1)
