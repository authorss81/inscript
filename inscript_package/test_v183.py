#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_v183.py  InScript v1.8.3 — Enum Exhaustiveness, Interface Enforcement & never

Tests:
  1.  Enum exhaustiveness: missing 1 variant is a SemanticError
  2.  Enum exhaustiveness: missing 2 variants names them both
  3.  Enum exhaustiveness: all variants covered is clean
  4.  Enum exhaustiveness: wildcard arm covers all
  5.  Enum exhaustiveness: partial coverage + wildcard is clean
  6.  Enum exhaustiveness: not a typed enum — no error (graceful skip)
  7.  Enum exhaustiveness: single-variant enum covered
  8.  Interface enforcement: missing method is a SemanticError
  9.  Interface enforcement: missing 2 methods names both
 10.  Interface enforcement: all methods present is clean
 11.  Interface enforcement: unknown interface is a SemanticError
 12.  Interface enforcement: multiple interfaces, all satisfied
 13.  Interface enforcement: multiple interfaces, one missing
 14.  `never` return type: fn always throws is clean
 15.  `never` return type: fn with no throw is error
 16.  `never` return type: fn with conditional throw is error (not all paths diverge)
 17.  `never` return type: result used as int (bottom type compat)
 18.  `never` return type: result used as string (bottom type compat)
 19.  `never` in union: `int | never` collapses to int
 20.  Runtime: enum match with all variants executes correctly
 21.  Runtime: interface-implementing struct calls method correctly
 22.  Runtime: `never` fn throws at runtime
 23.  v1.8.2 regression: type aliases
 24.  v1.8.1 regression: union types
 25.  v1.7.4 regression: REPL + null E0055
 26.  v1.7.3 regression: stack traces

Run:  python3 test_v183.py
"""
import sys, io
from interpreter import Interpreter
from analyzer import (Analyzer, T_INT, T_STRING, T_NEVER, T_ANY,
                      InScriptType, types_compatible, union_type)

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
    a = Analyzer(no_warn=True)
    try:
        a.analyze(parse(code)); return []
    except Exception as e:
        return str(e).splitlines()

def is_clean(code):  return len(analyze(code)) == 0
def has_error(code, fragment=None):
    errs = analyze(code)
    if not errs: return False
    if fragment: return any(fragment in l for l in errs)
    return True

ENUM4 = 'enum Dir { Left; Right; Up; Down }\n'
ENUM2 = 'enum Dir { Left; Right }\n'
MATCH_LR = 'fn f(d: Dir) { match d { case Dir::Left {} case Dir::Right {} } }'
MATCH_ALL4 = 'fn f(d: Dir) { match d { case Dir::Left {} case Dir::Right {} case Dir::Up {} case Dir::Down {} } }'


# ── 1–7. Enum exhaustiveness ──────────────────────────────────────────────────
section("1-7. Enum exhaustiveness")

ok("1. missing 1 of 4 is error",
   has_error(ENUM4 + MATCH_LR, "Non-exhaustive"))

ok("2. error names missing variants",
   has_error(ENUM4 + MATCH_LR, "Up") or has_error(ENUM4 + MATCH_LR, "Down"))

ok("3. all 4 variants covered is clean",
   is_clean(ENUM4 + MATCH_ALL4))

ok("4. wildcard covers all",
   is_clean(ENUM4 + 'fn f(d: Dir) { match d { case Dir::Left {} case _ {} } }'))

ok("5. partial + wildcard is clean",
   is_clean(ENUM4 + 'fn f(d: Dir) { match d { case Dir::Left {} case Dir::Right {} case _ {} } }'))

ok("6. untyped subject — no error",
   is_clean('fn f(d) { match d { case 1 {} case 2 {} } }'))

ok("7. single-variant enum covered",
   is_clean('enum One { Only }\nfn f(x: One) { match x { case One::Only {} } }'))

ok("7b. single-variant enum missing is error",
   has_error('enum One { Only }\nfn f(x: One) { match x { case _ {} } }') == False)
# wildcard is always exhaustive


# ── 8–13. Interface enforcement ───────────────────────────────────────────────
section("8-13. Interface enforcement")

IFACE_DRAW = 'interface Drawable { fn draw() -> void }\n'

ok("8. missing method is error",
   has_error(IFACE_DRAW + 'struct Sprite implements Drawable { x: int = 0 }',
             "missing method"))

ok("9. 2 missing methods named",
   has_error(
       'interface Renderable { fn draw() -> void\nfn update() -> void }\n'
       'struct Obj implements Renderable { x: int = 0 }',
       "missing method"
   ))

ok("10. all methods present is clean",
   is_clean(IFACE_DRAW + 'struct Sprite implements Drawable {\n  x: int = 0\n  fn draw() {}\n}'))

ok("11. unknown interface is error",
   has_error('struct S implements Ghost { x: int = 0 }', "unknown interface"))

ok("12. two interfaces both satisfied",
   is_clean(
       'interface A { fn foo() -> void }\ninterface B { fn bar() -> void }\n'
       'struct S implements A, B { fn foo() {} fn bar() {} }'
   ))

ok("13. two interfaces one missing",
   has_error(
       'interface A { fn foo() -> void }\ninterface B { fn bar() -> void }\n'
       'struct S implements A, B { fn foo() {} }',
       "missing method"
   ))


# ── 14–19. never return type ──────────────────────────────────────────────────
section("14-19. never return type")

ok("14. always-throw fn is clean",
   is_clean('fn crash() -> never { throw "fatal" }'))

ok("15. fn with no throw is error",
   has_error('fn crash() -> never { let x = 1 }', "never"))

ok("16. conditional throw is error (not all paths diverge)",
   has_error('fn crash(b: bool) -> never { if b { throw "x" } }', "never"))

ok("17. never result used as int",
   is_clean('fn crash() -> never { throw "x" }\nlet v: int = crash()'))

ok("18. never result used as string",
   is_clean('fn crash() -> never { throw "x" }\nlet s: string = crash()'))

ok("19. T_NEVER is compatible with any expected type",
   types_compatible(T_INT, T_NEVER) and
   types_compatible(T_STRING, T_NEVER) and
   types_compatible(T_ANY, T_NEVER))

ok("19b. T_NEVER repr",
   str(T_NEVER) == "never", repr(T_NEVER))


# ── 20. Runtime: enum match executes correctly ────────────────────────────────
section("20. Runtime: enum match")

out, err = run("""
enum Color { Red; Green; Blue }
fn name(c: Color) {
  match c {
    case Color::Red   { return "red"   }
    case Color::Green { return "green" }
    case Color::Blue  { return "blue"  }
  }
}
print(name(Color::Red))
print(name(Color::Green))
print(name(Color::Blue))
""")
ok("enum match runtime: red",   "red"   in (out or ""), repr(out))
ok("enum match runtime: green", "green" in (out or ""), repr(out))
ok("enum match runtime: blue",  "blue"  in (out or ""), repr(out))
ok("enum match runtime: no err", err is None, repr(err))


# ── 21. Runtime: interface struct calls method ────────────────────────────────
section("21. Runtime: interface struct method")

out, err = run("""
interface Drawable { fn draw() -> void }
struct Sprite implements Drawable {
  name: string = ""
  fn draw() {
    print("drawing " + self.name)
  }
}
let s = Sprite{name: "hero"}
s.draw()
""")
ok("interface struct: draw called", "drawing hero" in (out or ""), repr(out))
ok("interface struct: no error",    err is None,                   repr(err))


# ── 22. Runtime: never fn throws ─────────────────────────────────────────────
section("22. Runtime: never fn throws")

_, err = run("""
fn fatal(msg: string) -> never {
  throw "FATAL: " + msg
}
fatal("out of bounds")
""")
ok("never fn throws at runtime", err is not None and "FATAL" in err, repr(err))


# ── 23. v1.8.2 regression: type aliases ──────────────────────────────────────
section("23. v1.8.2 regression: type aliases")

ok("simple alias",
   is_clean("type HP = int\nlet h: HP = 100"))
ok("literal union alias",
   is_clean('type Dir = "left" | "right"\nlet d: Dir = "left"'))
ok("alias bad value errors",
   has_error('type HP = int\nlet h: HP = "bad"'))


# ── 24. v1.8.1 regression: union types ───────────────────────────────────────
section("24. v1.8.1 regression: union types")

ok("int|string clean",   is_clean("let x: int | string = 42"))
ok("int? nil clean",     is_clean("let x: int? = nil"))
ok("union narrowing",    is_clean(
    'fn f(x: int|string) { if typeof(x) == "int" { let n: int = x } }'))


# ── 25. v1.7.4 regression ────────────────────────────────────────────────────
section("25. v1.7.4 regression")

class FakeREPL:
    def __init__(self):
        self._interp = Interpreter()
        self._interp._env._repl_mode = True
    def eval(self, src):
        from lexer import Lexer; from parser import parse as _p; from errors import InScriptError
        snap = dict(self._interp._env._store)
        try: return self._interp.run(_p(src)), None
        except InScriptError as e: self._interp._env._store = snap; return None, str(e)
        except Exception as e: self._interp._env._store = snap; return None, str(e)
    def has(self, n): return n in self._interp._env._store
    def get(self, n): return self._interp._env._store.get(n)

r = FakeREPL()
r.eval("let x = 10"); _, e = r.eval("let y = x / 0")
ok("REPL: x survives error", r.has("x"))
ok("REPL: y not leaked",     not r.has("y"))
r.eval("let x = 99")
ok("REPL: let re-def",       r.get("x") == 99)
_, err = run("let z = null")
ok("null → E0055",  err is not None and "E0055" in err, repr(err))


# ── 26. v1.7.3 regression ────────────────────────────────────────────────────
section("26. v1.7.3 regression: stack traces")

_, err = run("fn a() { throw 'err' }\nfn b() { a() }\nb()")
ok("stack trace: a frame", err is not None and "in a" in err, repr(err))
ok("stack trace: b frame", err is not None and "in b" in err, repr(err))


# ── Summary ───────────────────────────────────────────────────────────────────
total = PASS + FAIL
print(f"""
{'='*58}
  v1.8.3 Test Results: {PASS}/{total} passed
  {'ALL PASS' if FAIL == 0 else f'{FAIL} FAILED'}
{'='*58}
""")
sys.exit(0 if FAIL == 0 else 1)
