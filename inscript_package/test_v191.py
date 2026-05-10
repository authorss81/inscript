#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_v191.py  InScript v1.9.1 — Deprecation Errors & Compat Tool

Tests:
  1.  compat: null usage detected
  2.  compat: div usage detected
  3.  compat: bare :[] annotation detected
  4.  compat: --no-typecheck in source detected
  5.  compat: clean file returns 0
  6.  compat: multiple issues in one file
  7.  compat: directory walk finds all .ins files
  8.  compat: comment lines skipped
  9.  compat: nonexistent path returns 1
 10.  compat: message includes migrate hint
 11.  bare 'array' in strict mode is a SemanticError
 12.  bare 'array' NOT in strict mode is clean (backwards compat)
 13.  typed [int] array still works in strict mode
 14.  --no-typecheck emits deprecation warning to stderr
 15.  --unsafe-no-check works as replacement (no warning)
 16.  --unsafe-no-check skips type checking
 17.  v1.8.4 regression: method chain inference
 18.  v1.8.3 regression: enum exhaustiveness
 19.  v1.8.2 regression: type aliases
 20.  v1.7.4 regression: REPL stability

Run:  python3 test_v191.py
"""
import sys, io, os, tempfile, shutil
from interpreter import Interpreter
from analyzer import Analyzer
from parser import parse

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

def is_clean(code, strict=False):
    a = Analyzer(no_warn=True, strict=strict)
    try: a.analyze(parse(code)); return True
    except: return False

def has_error(code, strict=False):
    return not is_clean(code, strict=strict)

# Load inscript module
import importlib.util
_spec = importlib.util.spec_from_file_location("inscript_mod",
    os.path.join(os.path.dirname(__file__), "inscript.py"))
_ins = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ins)


# ── 1–10. compat tool ─────────────────────────────────────────────────────────
section("1-10. inscript compat tool")

tmpdir = tempfile.mkdtemp()
try:
    def make_file(name, content):
        p = os.path.join(tmpdir, name)
        with open(p, 'w') as f: f.write(content)
        return p

    dirty = make_file("dirty.ins", "let x = null\nlet y = x div 2\nlet arr: [] = []\n")
    clean = make_file("clean.ins", "let x = nil\nlet y = x // 2\n")
    comment = make_file("comments.ins", "# let bad = null\nlet ok = nil\n")  # v1.9.6: # comments
    multi   = make_file("multi.ins", "let a = null\nlet b = null\nlet c = nil\n")

    # Capture stdout for compat output
    def compat(path):
        buf = io.StringIO(); sys.stdout = buf
        ret = _ins._compat_files(path)
        sys.stdout = sys.__stdout__
        return ret, buf.getvalue()

    r1, out1 = compat(dirty)
    ok("1. null detected",       r1 == 1 and "null" in out1,  repr(out1[:100]))
    ok("2. div detected",        r1 == 1 and "div" in out1,   repr(out1[:100]))
    ok("3. bare :[] detected",   r1 == 1 and "[]" in out1,    repr(out1[:100]))

    with open(dirty, 'w') as f: f.write("--no-typecheck\n")
    r_flag, out_flag = compat(dirty)
    ok("4. --no-typecheck detected", r_flag == 1 and "no-typecheck" in out_flag, repr(out_flag[:100]))

    r2, out2 = compat(clean)
    ok("5. clean file returns 0",    r2 == 0, repr(out2[:80]))

    r3, out3 = compat(multi)
    ok("6. multiple issues in one file", r3 == 1 and out3.count("null") >= 2, repr(out3[:120]))

    # Directory walk
    subdir = os.path.join(tmpdir, "sub")
    os.makedirs(subdir)
    make_file("sub/a.ins", "let x = null\n")
    make_file("sub/b.ins", "let y = nil\n")
    make_file("sub/c.txt", "let z = null\n")  # non-.ins, should be ignored
    r4, out4 = compat(subdir)
    ok("7. dir walk: .ins files found",  r4 == 1,                  repr(out4[:80]))
    ok("7b. dir walk: .txt file ignored", "c.txt" not in out4,     repr(out4[:80]))

    # Comment lines skipped
    r5, out5 = compat(comment)
    ok("8. comment lines skipped", r5 == 0, repr(out5[:80]))

    # Nonexistent path
    r6, _ = compat(os.path.join(tmpdir, "nonexistent.ins"))
    ok("9. nonexistent returns 1", r6 == 1)

    # Migrate hint in output
    with open(dirty, 'w') as f: f.write("let x = null\n")
    r7, out7 = compat(dirty)
    ok("10. migrate hint in output", "migrate" in out7.lower(), repr(out7[:100]))

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)


# ── 11–13. bare array type ────────────────────────────────────────────────────
section("11-13. Bare array type in strict mode")

ok("11. bare 'array' in strict is error",
   has_error("let x: array = []", strict=True))

ok("12. bare 'array' non-strict is clean",
   is_clean("let x: array = []", strict=False))

ok("13. typed [int] array in strict is clean",
   is_clean("let nums: [int] = [1,2,3]", strict=True))

ok("13b. [int] typed array in strict is clean",
   is_clean("let nums: [int] = [1,2,3]", strict=True))


# ── 14–16. --no-typecheck deprecation / --unsafe-no-check ────────────────────
section("14-16. --no-typecheck deprecation")

def run_main(argv):
    """Run inscript.main() with given argv, capture stderr."""
    import sys as _sys
    old_argv = _sys.argv
    _sys.argv = ["inscript"] + argv
    buf = io.StringIO(); _sys.stderr = buf
    try: _ins.main()
    except SystemExit: pass
    except Exception: pass
    finally:
        _sys.stderr = _sys.__stderr__
        _sys.argv   = old_argv
    return buf.getvalue()

stderr14 = run_main(["--no-typecheck", "nonexistent_file_xyz.ins"])
ok("14. --no-typecheck emits deprecation warning",
   "deprecated" in stderr14.lower() or "deprecated" in stderr14, repr(stderr14[:120]))

stderr15 = run_main(["--unsafe-no-check", "nonexistent_file_xyz.ins"])
ok("15. --unsafe-no-check has no deprecation warning",
   "deprecated" not in stderr15.lower(), repr(stderr15[:80]))

ok("16. --unsafe-no-check skip message is clean",
   "no-typecheck" not in stderr15.lower(), repr(stderr15[:80]))


# ── 17. v1.8.4 regression: method chain inference ────────────────────────────
section("17. v1.8.4 regression: method chain inference")

from analyzer import array_type, T_INT, T_BOOL, T_STRING
import re

def infer_type(src, name=None):
    a = Analyzer(no_warn=True)
    try: a.analyze(parse(src))
    except: pass
    if name is None:
        m = re.search(r'(?:let |fn )(\w+)', src.split('\n')[-1])
        name = m.group(1) if m else None
    sym = a._scope.lookup(name) if name else None
    return sym.type_ if sym else None

ok("map → Array<int>",
   infer_type("let a=[1,2,3]\nlet r=a.map(fn(x){return x*2})") == array_type(T_INT))
ok("filter → Array<int>",
   infer_type("let a=[1,2,3]\nlet r=a.filter(fn(x){return x>0})") == array_type(T_INT))
ok("len() → int",
   infer_type("let a=[1,2,3]\nlet r=a.len()") == T_INT)
ok("return type inferred",
   infer_type("fn double(x: int) { return x * 2 }") == T_INT)


# ── 18. v1.8.3 regression ────────────────────────────────────────────────────
section("18. v1.8.3 regression: enum + interface + never")

ok("enum exhaustiveness error",
   has_error("enum Dir { Left; Right; Up }\nfn f(d: Dir) { match d { case Dir::Left {} } }"))

ok("interface missing method error",
   has_error("interface Drawable { fn draw() -> void }\nstruct S implements Drawable { x: int = 0 }"))

ok("never return type clean",
   is_clean("fn crash() -> never { throw \"x\" }"))


# ── 19. v1.8.2 regression ────────────────────────────────────────────────────
section("19. v1.8.2 regression: type aliases + literal types")

ok("type alias int",
   is_clean("type HP = int\nlet h: HP = 100"))

ok("literal union alias",
   is_clean('type Dir = "left" | "right"\nlet d: Dir = "left"'))

ok("literal union bad value errors",
   has_error('type Dir = "left" | "right"\nlet d: Dir = "up"'))


# ── 20. v1.7.4 regression ────────────────────────────────────────────────────
section("20. v1.7.4 regression: REPL + null E0055")

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
ok("null → E0055", err is not None and "E0055" in err, repr(err))


# ── Summary ───────────────────────────────────────────────────────────────────
total = PASS + FAIL
print(f"""
{'='*58}
  v1.9.1 Test Results: {PASS}/{total} passed
  {'ALL PASS' if FAIL == 0 else f'{FAIL} FAILED'}
{'='*58}
""")
sys.exit(0 if FAIL == 0 else 1)
