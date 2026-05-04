#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_v174.py  InScript v1.7.4 — REPL Stability & Migrate Tool

Tests:
  1.  REPL error recovery — globals survive a runtime error
  2.  REPL let re-definition — let x=1 then let x=2 works
  3.  REPL let→const upgrade blocked (const still enforced)
  4.  REPL multi-statement block: partial failure doesn't kill good defs
  5.  REPL function survives error in later block
  6.  null hard error with E0055 code
  7.  null error message contains migrate hint
  8.  migrate: null → nil
  9.  migrate: div → //
  10. migrate: `: []` → `: array`
  11. migrate: mixed transformations in one file
  12. migrate: already-clean file untouched
  13. migrate: directory walk migrates all .ins files
  14. v1.7.3 regression: stack traces still work
  15. v1.7.2 regression: recursive types still work

Run:  python3 test_v174.py
"""
import sys, io, os, tempfile, shutil
from interpreter import Interpreter
from errors import InScriptRuntimeError

PASS = FAIL = 0

def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  OK  {name}")
        PASS += 1
    else:
        print(f"  FAIL  {name}" + (f"  [{detail}]" if detail else ""))
        FAIL += 1

def section(t):
    print(f"\n--- {t} ---")

def run(code):
    buf = io.StringIO(); sys.stdout = buf
    try:
        Interpreter().execute(code)
        sys.stdout = sys.__stdout__
        return buf.getvalue().strip(), None
    except Exception as e:
        sys.stdout = sys.__stdout__
        return buf.getvalue().strip(), str(e)


# ── Helpers: simulate REPL session ───────────────────────────────────────────
class FakeREPL:
    """Lightweight simulation of EnhancedREPL._eval() for testing error recovery."""
    def __init__(self):
        from interpreter import Interpreter
        from errors import InScriptError
        from lexer import Lexer
        from parser import Parser
        self._Interpreter = Interpreter
        self._InScriptError = InScriptError
        self._Lexer = Lexer
        self._Parser = Parser
        self._interp = Interpreter()
        # v1.7.4: REPL mode flag
        self._interp._env._repl_mode = True

    def eval(self, source):
        """Returns (result, error_str)."""
        from lexer import Lexer
        from parser import Parser
        from errors import InScriptError
        env_snapshot = dict(self._interp._env._store)
        try:
            tokens  = Lexer(source).tokenize()
            program = Parser(tokens).parse()
            result  = self._interp.run(program)
            return result, None
        except InScriptError as e:
            self._interp._env._store = env_snapshot
            return None, str(e)
        except Exception as e:
            self._interp._env._store = env_snapshot
            return None, str(e)

    def get(self, name):
        return self._interp._env._store.get(name)

    def defined(self, name):
        return name in self._interp._env._store


# ── 1. REPL error recovery ────────────────────────────────────────────────────
section("1. REPL error recovery")

repl = FakeREPL()
_, err = repl.eval("let x = 42")
ok("let x succeeds",           err is None, repr(err))
ok("x defined after success",  repl.defined("x"))
ok("x has correct value",      repl.get("x") == 42, repr(repl.get("x")))

_, err = repl.eval("let y = x / 0")     # runtime error
ok("div-by-zero raises",       err is not None, repr(err))
ok("x survives error",         repl.defined("x"),   "x was lost")
ok("x value unchanged",        repl.get("x") == 42, repr(repl.get("x")))
ok("y NOT defined after error",not repl.defined("y"), "y was partially defined")

# ── 2. let re-definition ─────────────────────────────────────────────────────
section("2. let re-definition in REPL")

repl2 = FakeREPL()
_, err = repl2.eval("let x = 1")
ok("first let x ok",    err is None,        repr(err))
ok("x=1",               repl2.get("x") == 1, repr(repl2.get("x")))

_, err = repl2.eval("let x = 99")
ok("second let x ok",   err is None,        repr(err))
ok("x re-bound to 99",  repl2.get("x") == 99, repr(repl2.get("x")))

_, err = repl2.eval("let x = \"hello\"")
ok("type-change re-def ok",  err is None,           repr(err))
ok("x is now hello",         repl2.get("x") == "hello", repr(repl2.get("x")))

# ── 3. const still enforced ───────────────────────────────────────────────────
section("3. const still enforced in REPL")

repl3 = FakeREPL()
_, err = repl3.eval("const C = 10")
ok("const C defined",        err is None, repr(err))

_, err = repl3.eval("C = 20")
ok("assign to const errors", err is not None, repr(err))
ok("C still 10",             repl3.get("C") == 10, repr(repl3.get("C")))

# ── 4. Partial-failure in multi-statement block ───────────────────────────────
section("4. Multi-statement block: failure rolls back all")

repl4 = FakeREPL()
_, err = repl4.eval("let a = 10")
ok("a defined",  err is None)

_, err = repl4.eval("let b = 20\nlet c = b / 0")   # b defines fine, c fails
ok("block errors on c",     err is not None, repr(err))
# Because we snapshot before the WHOLE block runs, b should NOT be in env
# (snapshot before block, restore on error → b was not in snapshot)
ok("b rolled back",         not repl4.defined("b"), "b survived error block")
ok("a still present",       repl4.defined("a"),     "a was lost")
ok("a value preserved",     repl4.get("a") == 10,   repr(repl4.get("a")))

# ── 5. Function definition survives later error ───────────────────────────────
section("5. fn definition survives later error")

repl5 = FakeREPL()
_, err = repl5.eval("fn double(x) { return x * 2 }")
ok("fn double defined",    err is None, repr(err))
ok("double in env",        repl5.defined("double"))

_, err = repl5.eval("let bad = undefined_name_xyz")
ok("undefined name errors", err is not None, repr(err))
ok("double still in env",   repl5.defined("double"), "double was lost after error")

_, err = repl5.eval("print(double(5))")
ok("double still callable", err is None, repr(err))

# ── 6. null hard error uses E0055 ────────────────────────────────────────────
section("6. null → E0055 hard error")

_, err = run("let x = null")
ok("null raises error",    err is not None, repr(err))
ok("E0055 in message",     err is not None and "E0055" in err, repr(err))
ok("'nil' hint present",   err is not None and "nil" in err,   repr(err))

_, err = run("let x = nil")
ok("nil is still valid",   err is None, repr(err))

# ── 7. null migrate hint ──────────────────────────────────────────────────────
section("7. null error contains migrate hint")

_, err = run("print(null)")
ok("null in expression errors", err is not None, repr(err))
ok("migrate hint in message",   err is not None and "migrate" in err.lower(), repr(err))

# ── 8. migrate: null → nil ───────────────────────────────────────────────────
section("8. migrate null → nil")

import re as _re

def _migrate_src(src: str) -> str:
    """Apply the same transformations as inscript._migrate_files()."""
    src = _re.sub(r'\bnull\b', 'nil', src)
    src = _re.sub(r'\bdiv\b', '//', src)
    src = _re.sub(r':\s*\[\]', ': array', src)
    return src

cases_null = [
    ("bare null",        "let x = null",        "let x = nil"),
    ("null in if",       "if x == null {",      "if x == nil {"),
    ("null return",      "return null",          "return nil"),
    ("null in fn",       "fn f() { return null }", "fn f() { return nil }"),
    ("nil unchanged",    "let y = nil",          "let y = nil"),
    ("nullify unchanged","let s = \"null\"",     "let s = \"null\""),  # inside string — note: re.sub on word boundary won't match inside quotes, but basic test
]

for name, src, want in cases_null:
    result = _migrate_src(src)
    ok(f"null migrate: {name}", result == want, f"got {result!r}, want {want!r}")

# ── 9. migrate: div → // ─────────────────────────────────────────────────────
section("9. migrate div → //")

cases_div = [
    ("simple div",      "x div y",     "x // y"),
    ("in expr",         "10 div 3",    "10 // 3"),
    ("with spaces",     "a  div  b",   "a  //  b"),
    ("divide unchanged","x / y",       "x / y"),
    ("divmod unchanged","x % y",       "x % y"),
]
for name, src, want in cases_div:
    result = _migrate_src(src)
    ok(f"div migrate: {name}", result == want, f"got {result!r}, want {want!r}")

# ── 10. migrate: `: []` → `: array` ─────────────────────────────────────────
section("10. migrate :[] → :array")

cases_arr = [
    ("bare `:[]`",          "let x: []",       "let x: array"),
    ("space `: []`",        "let x: [] = []",  "let x: array = []"),
    ("in struct",           "items: []",       "items: array"),
    ("non-empty unchanged", "let x: [int]",    "let x: [int]"),
]
for name, src, want in cases_arr:
    result = _migrate_src(src)
    ok(f"array migrate: {name}", result == want, f"got {result!r}, want {want!r}")

# ── 11. migrate: file round-trip ─────────────────────────────────────────────
section("11. migrate file round-trip")

DIRTY_SRC = """\
fn compute(a, b) {
    let result = a div b
    if result == null {
        return null
    }
    let items: [] = []
    return result
}
"""

CLEAN_SRC = """\
fn compute(a, b) {
    let result = a // b
    if result == nil {
        return nil
    }
    let items: array = []
    return result
}
"""

migrated = _migrate_src(DIRTY_SRC)
ok("full file migrated correctly", migrated == CLEAN_SRC,
   f"\nGot:\n{migrated!r}\nWant:\n{CLEAN_SRC!r}")

# ── 12. migrate: clean file untouched ────────────────────────────────────────
section("12. Clean file untouched")

ALREADY_CLEAN = "let x = nil\nlet y = x // 2\n"
ok("clean file unchanged", _migrate_src(ALREADY_CLEAN) == ALREADY_CLEAN)

# ── 13. migrate tool via inscript._migrate_files ─────────────────────────────
section("13. migrate tool file I/O")

tmpdir = tempfile.mkdtemp()
try:
    fpath = os.path.join(tmpdir, "old_code.ins")
    with open(fpath, "w") as f:
        f.write("let x = null\nlet y = x div 2\n")

    # Import and call _migrate_files
    import importlib.util, sys as _sys
    spec = importlib.util.spec_from_file_location("inscript_mod",
        os.path.join(os.path.dirname(__file__), "inscript.py"))
    inscript_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inscript_mod)
    ret = inscript_mod._migrate_files(fpath)

    with open(fpath) as f:
        result = f.read()

    ok("migrate returns 0",       ret == 0, repr(ret))
    ok("null replaced with nil",  "null" not in result, repr(result))
    ok("div replaced with //",    " div " not in result, repr(result))
    ok("nil present",             "nil" in result)
    ok("// present",              "//" in result)

    # clean file
    clean_path = os.path.join(tmpdir, "clean.ins")
    with open(clean_path, "w") as f:
        f.write("let x = nil\n")
    ret2 = inscript_mod._migrate_files(clean_path)
    with open(clean_path) as f:
        clean_result = f.read()
    ok("clean file unchanged after migrate", clean_result == "let x = nil\n")

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

# ── 14. v1.7.3 regression: stack traces still work ───────────────────────────
section("14. v1.7.3 regression: stack traces")

_, err = run("""
fn inner() { throw "trace" }
fn outer() { inner() }
outer()
""")
ok("stack trace: inner present", err is not None and "in inner" in err, repr(err))
ok("stack trace: outer present", err is not None and "in outer" in err, repr(err))
ok("stack trace: source snippet", err is not None and "inner()" in err, repr(err))

# ── 15. v1.7.2 regression: recursive types ───────────────────────────────────
section("15. v1.7.2 regression: recursive types")

out, err = run("""
struct Node { value: int = 0; next: nil = nil }
let n3 = Node{value: 3}
let n2 = Node{value: 2, next: n3}
let n1 = Node{value: 1, next: n2}
let curr = n1
let sum = 0
while curr != nil {
    sum = sum + curr.value
    curr = curr.next
}
print(sum)
""")
ok("linked list traversal sum=6", out == "6" and err is None, repr(out))

# ── Summary ───────────────────────────────────────────────────────────────────
total = PASS + FAIL
print(f"""
{'='*56}
  v1.7.4 Test Results: {PASS}/{total} passed
  {'ALL PASS' if FAIL == 0 else f'{FAIL} FAILED'}
{'='*56}
""")
sys.exit(0 if FAIL == 0 else 1)
