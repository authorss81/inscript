#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_v184.py  InScript v1.8.4 — Type Inference for Method Chains

Tests:
  1.  arr.filter(fn) infers Array<elem>
  2.  arr.map(fn) infers Array<T> from fn return type
  3.  arr.map(fn(x:int){return x*2}) → Array<int>
  4.  arr.map(fn(x){return x.to_string()}) → Array<string>
  5.  Chained: arr.filter(...).map(...) preserves type
  6.  Chained: filter.map.take still Array<int>
  7.  arr.len() → int
  8.  arr.sum() → int for int array
  9.  arr.any(fn) → bool
  10. arr.all(fn) → bool
  11. arr.join(sep) → string
  12. arr.first() → int? (optional)
  13. arr.find(fn) → int? (optional)
  14. arr.take(n) → Array<int>
  15. arr.skip(n) → Array<int>
  16. arr.sorted() → Array<int>
  17. arr.reversed() → Array<int>
  18. str.split(sep) → Array<string>
  19. str.len() → int
  20. str.lower() → string
  21. str.upper() → string
  22. str.trim() → string
  23. str.starts_with() → bool
  24. str.contains() → bool
  25. Return type inference: fn with int return → int
  26. Return type inference: fn with string return → string
  27. Return type inference: fn with bool return → bool
  28. Return type inference: fn with float return → float
  29. Return type inference: fn with mixed returns stays any
  30. Return type inference: annotated fn unchanged
  31. Inferred return type used in type check
  32. Runtime: map result is correct
  33. Runtime: filter result is correct
  34. Runtime: chained map.filter works
  35. v1.8.3 regression: enum exhaustiveness
  36. v1.8.3 regression: interface enforcement
  37. v1.8.2 regression: type aliases
  38. v1.7.4 regression: REPL + null E0055

Run:  python3 test_v184.py
"""
import sys, io, re
from interpreter import Interpreter
from analyzer import (Analyzer, T_INT, T_FLOAT, T_STRING, T_BOOL, T_ANY,
                      T_NEVER, InScriptType, types_compatible,
                      array_type, optional_type)

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

def infer(src, name=None):
    """Analyze src, return type of last defined name (or given name)."""
    from parser import parse
    a = Analyzer(no_warn=True)
    try:
        a.analyze(parse(src))
    except Exception:
        pass
    if name is None:
        last = [s for s in src.split('\n') if 'let ' in s or 'fn ' in s]
        if not last: return T_ANY
        m = re.search(r'(?:let |fn )(\w+)', last[-1])
        name = m.group(1) if m else None
    if name is None: return T_ANY
    sym = a._scope.lookup(name)
    return sym.type_ if sym else T_ANY


# ── 1–6. Array.filter / map / chained ────────────────────────────────────────
section("1-6. Array filter / map / chain")

ok("1. filter preserves Array<int>",
   infer("let a=[1,2,3]\nlet r=a.filter(fn(x){return x>0})") == array_type(T_INT))

ok("2. map infers Array<int> from *2",
   infer("let a=[1,2,3]\nlet r=a.map(fn(x){return x*2})") == array_type(T_INT))

ok("3. map fn(x:int) explicit param",
   infer("let a=[1,2,3]\nlet r=a.map(fn(x: int){return x+1})") == array_type(T_INT))

ok("4. map fn returning bool → Array<bool>",
   infer("let a=[1,2,3]\nlet r=a.map(fn(x){return x>0})") == array_type(T_BOOL))

ok("5. filter.map chain → Array<int>",
   infer("let a=[1,2,3]\nlet r=a.filter(fn(x){return x>1}).map(fn(x){return x*10})")
   == array_type(T_INT))

ok("6. filter.map.take chain → Array<int>",
   infer("let a=[1,2,3]\nlet r=a.filter(fn(x){return x>0}).map(fn(x){return x}).take(2)")
   == array_type(T_INT))


# ── 7–13. Array scalar methods ────────────────────────────────────────────────
section("7-13. Array scalar methods")

ok("7. len() → int",
   infer("let a=[1,2,3]\nlet r=a.len()") == T_INT)

ok("8. sum() → int",
   infer("let a=[1,2,3]\nlet r=a.sum()") == T_INT)

ok("9. any(fn) → bool",
   infer("let a=[1,2,3]\nlet r=a.any(fn(x){return x>0})") == T_BOOL)

ok("10. all(fn) → bool",
   infer("let a=[1,2,3]\nlet r=a.all(fn(x){return x>0})") == T_BOOL)

ok("11. join(sep) → string",
   infer('let a=[1,2,3]\nlet r=a.join(",")') == T_STRING)

ok("12. first() → optional int",
   infer("let a=[1,2,3]\nlet r=a.first()") == optional_type(T_INT))

ok("13. find(fn) → optional int",
   infer("let a=[1,2,3]\nlet r=a.find(fn(x){return x>2})") == optional_type(T_INT))


# ── 14–17. Array structural methods ──────────────────────────────────────────
section("14-17. Array structural methods")

ok("14. take(n) → Array<int>",
   infer("let a=[1,2,3]\nlet r=a.take(2)") == array_type(T_INT))

ok("15. skip(n) → Array<int>",
   infer("let a=[1,2,3]\nlet r=a.skip(1)") == array_type(T_INT))

ok("16. sorted() → Array<int>",
   infer("let a=[3,1,2]\nlet r=a.sorted()") == array_type(T_INT))

ok("17. reversed() → Array<int>",
   infer("let a=[1,2,3]\nlet r=a.reversed()") == array_type(T_INT))


# ── 18–24. String methods ─────────────────────────────────────────────────────
section("18-24. String methods")

ok("18. split → Array<string>",
   infer('let s="a,b,c"\nlet r=s.split(",")') == array_type(T_STRING))

ok("19. len() → int",
   infer('let s="hello"\nlet r=s.len()') == T_INT)

ok("20. lower() → string",
   infer('let s="HI"\nlet r=s.lower()') == T_STRING)

ok("21. upper() → string",
   infer('let s="hi"\nlet r=s.upper()') == T_STRING)

ok("22. trim() → string",
   infer('let s="  hi  "\nlet r=s.trim()') == T_STRING)

ok("23. starts_with() → bool",
   infer('let s="hello"\nlet r=s.starts_with("he")') == T_BOOL)

ok("24. contains() → bool",
   infer('let s="hello"\nlet r=s.contains("ll")') == T_BOOL)


# ── 25–30. Return type inference ──────────────────────────────────────────────
section("25-30. Return type inference")

ok("25. fn body returns int → inferred int",
   infer("fn double(x: int) { return x * 2 }") == T_INT)

ok("26. fn body returns string → inferred string",
   infer('fn greet(name: string) { return "Hello " + name }') == T_STRING)

ok("27. fn body returns bool → inferred bool",
   infer("fn is_pos(x: int) { return x > 0 }") == T_BOOL)

ok("28. fn body returns float → inferred float",
   infer("fn half(x: float) { return x / 2.0 }") == T_FLOAT)

ok("29. mixed returns stays any",
   infer("fn f(b: bool) { if b { return 1 } return \"str\" }") == T_ANY)

ok("30. annotated fn: annotation wins",
   infer("fn f(x: int) -> string { return \"x\" }") == T_STRING)


# ── 31. Inferred type used in downstream check ────────────────────────────────
section("31. Inferred type downstream")

from parser import parse as _parse

def is_clean(code):
    a = Analyzer(no_warn=True)
    try: a.analyze(_parse(code)); return True
    except: return False

def has_error(code):
    a = Analyzer(no_warn=True)
    try: a.analyze(_parse(code)); return False
    except: return True

ok("31. inferred int fn return used as int",
   is_clean("fn double(x: int) { return x * 2 }\nlet r: int = double(5)"))

ok("31b. inferred string fn return used as string",
   is_clean('fn greet(n: string) { return "Hi " + n }\nlet r: string = greet("Alice")'))


# ── 32–34. Runtime: map/filter work correctly ─────────────────────────────────
section("32-34. Runtime correctness")

out, err = run("""
let nums = [1, 2, 3, 4, 5]
let doubled = nums.map(fn(x) { return x * 2 })
for n in doubled { print(n) }
""")
ok("32. map doubles correctly",
   out == "2\n4\n6\n8\n10" and err is None, repr(out))

out, err = run("""
let nums = [1, 2, 3, 4, 5]
let evens = nums.filter(fn(x) { return x % 2 == 0 })
for n in evens { print(n) }
""")
ok("33. filter keeps evens",
   out == "2\n4" and err is None, repr(out))

out, err = run("""
let nums = [1, 2, 3, 4, 5]
let result = nums.filter(fn(x) { return x > 2 }).map(fn(x) { return x * 10 })
for n in result { print(n) }
""")
ok("34. chained filter.map",
   out == "30\n40\n50" and err is None, repr(out))


# ── 35–38. Regressions ────────────────────────────────────────────────────────
section("35-38. Regressions")

ok("35. v1.8.3: enum exhaustiveness error",
   has_error(
       "enum Dir { Left; Right; Up }\n"
       "fn f(d: Dir) { match d { case Dir::Left {} case Dir::Right {} } }"
   ))

ok("36. v1.8.3: interface enforcement",
   has_error(
       "interface Drawable { fn draw() -> void }\n"
       "struct S implements Drawable { x: int = 0 }"
   ))

ok("37. v1.8.2: type alias",
   is_clean("type HP = int\nlet h: HP = 100"))

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
ok("38. v1.7.4: REPL x survives error", r.has("x"))
_, err = run("let z = null")
ok("38b. v1.7.4: null → E0055", err is not None and "E0055" in err, repr(err))


# ── Summary ───────────────────────────────────────────────────────────────────
total = PASS + FAIL
print(f"""
{'='*58}
  v1.8.4 Test Results: {PASS}/{total} passed
  {'ALL PASS' if FAIL == 0 else f'{FAIL} FAILED'}
{'='*58}
""")
sys.exit(0 if FAIL == 0 else 1)
