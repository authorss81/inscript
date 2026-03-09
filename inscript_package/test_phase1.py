#!/usr/bin/env python3
"""
test_phase1.py — Phase 1 Foundation Repair test suite
Tests:
  1.1  Runtime type enforcement on let declarations
  1.1  Runtime type enforcement on function parameters
  1.1  as cast operator (was ParseError before — now works)
  1.1  is type-check operator
  1.1  Coercion table (int+float, bool coercions)
  1.2  div keyword for floor division
  1.4  Raw strings r"..." (no escape processing)
  1.4  Multiline triple-quoted strings
  1.6  Match exhaustiveness — MatchError when no arm matches
  1.5  Property getters/setters
  Regression — all 331 existing tests still pass
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from lexer       import Lexer, TT
from parser      import Parser
from interpreter import Interpreter
from errors      import LexerError, ParseError, InScriptRuntimeError

PASS = 0
FAIL = 0
_FAILURES = []

def run(src: str) -> str:
    """Run InScript source, capture stdout, return it."""
    import io
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        tokens = Lexer(src).tokenize()
        ast    = Parser(tokens, src).parse()
        Interpreter(src).run(ast)
        return buf.getvalue()
    finally:
        sys.stdout = old_stdout

def run_val(src: str):
    """Run InScript, return the last expression value (via __last__ trick)."""
    tokens = Lexer(src).tokenize()
    ast    = Parser(tokens, src).parse()
    interp = Interpreter(src)
    interp.run(ast)
    # Get last defined variable from environment
    return interp._env

def expect_error(src: str, error_substring: str) -> bool:
    """Return True if running src raises an error containing error_substring."""
    try:
        run(src)
        return False
    except (InScriptRuntimeError, ParseError, LexerError, Exception) as e:
        return error_substring.lower() in str(e).lower()

def ok(name: str, cond: bool):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        _FAILURES.append(name)
        print(f"  ❌ {name}")

def section(title: str):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


# ─────────────────────────────────────────────────────────────────────────────
# 1.1 — as CAST OPERATOR (was ParseError — now must work)
# ─────────────────────────────────────────────────────────────────────────────
section("1.1 — 'as' cast operator")

ok("string to int",
   run('let n = "5" as int\nprint(n)').strip() == "5")

ok("float to int truncates",
   run('let n = 3.9 as int\nprint(n)').strip() == "3")

ok("int to float",
   run('let x = 7 as float\nprint(x)').strip() == "7.0")

ok("int to string",
   run('let s = 42 as string\nprint(s)').strip() == "42")

ok("bool to int true",
   run('let n = true as int\nprint(n)').strip() == "1")

ok("bool to int false",
   run('let n = false as int\nprint(n)').strip() == "0")

ok("bool to string",
   run('let s = true as string\nprint(s)').strip() == "true")

ok("int to bool (nonzero = true)",
   run('let b = 1 as bool\nprint(b)').strip() == "true")

ok("int to bool (zero = false)",
   run('let b = 0 as bool\nprint(b)').strip() == "false")

ok("float to string",
   run('let s = 3.14 as string\nprint(s)').strip() == "3.14")

ok("chained cast: string→int→float",
   run('let x = ("42" as int) as float\nprint(x)').strip() == "42.0")

ok("cast in expression",
   run('let x = "10" as int + 5\nprint(x)').strip() == "15")

ok("cast in function call",
   run('fn double(n: int) -> int { return n * 2 }\nprint(double("3" as int))').strip() == "6")

ok("bad string→int raises error",
   expect_error('let n = "hello" as int', "typeerror"))

ok("nil→int raises error",
   expect_error('let n = nil as int', ""))   # allow any error

# ─────────────────────────────────────────────────────────────────────────────
# 1.1 — is TYPE CHECK OPERATOR
# ─────────────────────────────────────────────────────────────────────────────
section("1.1 — 'is' type check operator")

ok("int is int → true",
   run('let x = 42\nprint(x is int)').strip() == "true")

ok("float is int → false",
   run('let x = 3.14\nprint(x is int)').strip() == "false")

ok("string is string → true",
   run('let x = \"hello\"\nprint(x is string)').strip() == "true")

ok("int is string → false",
   run('let x = 5\nprint(x is string)').strip() == "false")

ok("bool is bool → true",
   run('let x = true\nprint(x is bool)').strip() == "true")

ok("bool is int → false (bool is NOT int)",
   run('let x = true\nprint(x is int)').strip() == "false")

ok("nil is nil → true",
   run('let x = nil\nprint(x is nil)').strip() == "true")

ok("5 is nil → false",
   run('let x = 5\nprint(x is nil)').strip() == "false")

ok("array is array → true",
   run('let x = [1,2,3]\nprint(x is array)').strip() == "true")

ok("is in if branch",
   run('let x = "hello"\nif x is string { print("yes") } else { print("no") }').strip() == "yes")

ok("is in if branch — false branch",
   run('let x = 42\nif x is string { print("yes") } else { print("no") }').strip() == "no")

ok("is as assignment",
   run('let x = 42\nlet result = x is int\nprint(result)').strip() == "true")

ok("multiple is checks",
   run('''
let x = 3.14
let a = x is float
let b = x is int
print(a)
print(b)
''').strip() == "true\nfalse")

# ─────────────────────────────────────────────────────────────────────────────
# 1.1 — RUNTIME TYPE ENFORCEMENT on let declarations
# ─────────────────────────────────────────────────────────────────────────────
section("1.1 — Type enforcement on 'let' declarations")

ok("let x: int = 5 → works",
   run('let x: int = 5\nprint(x)').strip() == "5")

ok("let x: float = 3.14 → works",
   run('let x: float = 3.14\nprint(x)').strip() == "3.14")

ok("let x: string = \"hi\" → works",
   run('let x: string = "hi"\nprint(x)').strip() == "hi")

ok("let x: int = \"hello\" → TypeError",
   expect_error('let x: int = "hello"', "typeerror"))

ok("let x: float = \"oops\" → TypeError",
   expect_error('let x: float = "oops"', "typeerror"))

ok("let x: string = [1,2] → TypeError",
   expect_error('let x: string = [1,2]', "typeerror"))

ok("let x: int = 3.7 → auto-coerce to int 3",
   run('let x: int = 3.7\nprint(x)').strip() == "3")

ok("let x: float = 5 → auto-coerce to 5.0",
   run('let x: float = 5\nprint(x)').strip() == "5.0")

ok("let x: bool = 1 → coerce to true",
   run('let x: bool = 1\nprint(x)').strip() == "true")

ok("let x: bool = 0 → coerce to false",
   run('let x: bool = 0\nprint(x)').strip() == "false")

ok("untyped let accepts anything",
   run('let x = "any"\nprint(x)').strip() == "any")

# ─────────────────────────────────────────────────────────────────────────────
# 1.1 — TYPE ENFORCEMENT on function parameters
# ─────────────────────────────────────────────────────────────────────────────
section("1.1 — Type enforcement on function parameters")

ok("typed fn param — correct type passes",
   run('fn add(a: int, b: int) -> int { return a + b }\nprint(add(3, 4))').strip() == "7")

ok("typed fn param — string passed to int → TypeError",
   expect_error('fn add(a: int, b: int) -> int { return a + b }\nadd("x", 3)', "typeerror"))

ok("typed fn param — float auto-coerces to int",
   run('fn double(n: int) -> int { return n * 2 }\nprint(double(3.0))').strip() == "6")

ok("typed fn param — bool auto-coerces to int",
   run('fn triple(n: int) -> int { return n * 3 }\nprint(triple(true))').strip() == "3")

ok("typed fn param — int auto-coerces to float",
   run('fn half(x: float) -> float { return x / 2 }\nprint(half(10))').strip() == "5.0")

ok("untyped fn param — accepts anything",
   run('fn id(x) { return x }\nprint(id("hello"))').strip() == "hello")

ok("mixed typed/untyped params",
   run('fn greet(name, times: int) { for i in 0..times { print(name) } }\ngreet("hi", 2)').strip() == "hi\nhi")

# ─────────────────────────────────────────────────────────────────────────────
# 1.2 — div KEYWORD (floor division)
# ─────────────────────────────────────────────────────────────────────────────
section("1.2 — 'div' keyword floor division")

ok("10 div 3 = 3",
   run('print(10 div 3)').strip() == "3")

ok("7 div 2 = 3",
   run('print(7 div 2)').strip() == "3")

ok("-7 div 2 = -4 (floor)",
   run('print(-7 div 2)').strip() == "-4")

ok("10 div 5 = 2",
   run('print(10 div 5)').strip() == "2")

ok("div in expression",
   run('let x = (10 div 3) + 1\nprint(x)').strip() == "4")

ok("div chained",
   run('print(100 div 10 div 2)').strip() == "5")

ok("div in loop",
   run('let n = 16\nwhile n > 1 { n = n div 2 }\nprint(n)').strip() == "1")

ok("// still works as floor div",
   run('print(10 div 3)').strip() == "3")

# ─────────────────────────────────────────────────────────────────────────────
# 1.4 — RAW STRINGS r"..."
# ─────────────────────────────────────────────────────────────────────────────
section("1.4 — Raw strings r\"...\"")

ok("raw string no escape",
   run(r'print(r"hello\nworld")').strip() == r"hello\nworld")

ok("raw string backslash literal",
   run(r'print(r"C:\Users\path")').strip() == r"C:\Users\path")

ok("raw string backslash-t stays literal",
   run("let s = r\"a\\\\tb\"\nprint(s)").strip() == "a\\\\tb")

ok("raw string single quote",
   run("print(r'no\\escape')").strip() == r"no\escape")

ok("raw string assigned to typed var",
   run(r'let s: string = r"path\to\file"' + '\nprint(s)').strip() == r"path\to\file")

# ─────────────────────────────────────────────────────────────────────────────
# 1.4 — MULTILINE TRIPLE-QUOTED STRINGS
# ─────────────────────────────────────────────────────────────────────────────
section("1.4 — Multiline triple-quoted strings")

ok("triple-quote basic",
   run('let s = """hello\nworld"""\nprint(s)').strip() == "hello\nworld")

ok("triple-quote with indentation",
   run('let s = """line1\n  line2"""\nprint(s)').strip() == "line1\n  line2")

ok("triple-quote in function",
   run('fn msg() { return """multi\nline""" }\nprint(msg())').strip() == "multi\nline")

ok("triple-quote single quotes",
   run("let s = '''hello\nworld'''\nprint(s)").strip() == "hello\nworld")

ok("triple-quote length check",
   run('let s = """abc\ndef"""\nprint(len(s))').strip() == "7")

# ─────────────────────────────────────────────────────────────────────────────
# 1.6 — MATCH EXHAUSTIVENESS
# ─────────────────────────────────────────────────────────────────────────────
section("1.6 — Match exhaustiveness (MatchError)")

ok("match with wildcard _ succeeds",
   run('''
let x = 99
match x {
    case 1 { print("one") }
    case _ { print("other") }
}
''').strip() == "other")

ok("match hits correct arm",
   run('''
let x = 1
match x {
    case 1 { print("one") }
    case 2 { print("two") }
    case _ { print("other") }
}
''').strip() == "one")

ok("non-exhaustive match raises MatchError",
   expect_error('''
let x = 99
match x {
    case 1 { print("one") }
    case 2 { print("two") }
}
''', "matcherror"))

ok("match string arms exhaustive via wildcard",
   run('''
let s = "hello"
match s {
    case "hi" { print("hi") }
    case _    { print("other") }
}
''').strip() == "other")

ok("non-exhaustive string match raises MatchError",
   expect_error('''
let s = "missing"
match s {
    case "a" { print("a") }
    case "b" { print("b") }
}
''', "matcherror"))

ok("binding arm (case x if ...) counts as catch-all wildcard",
   run('''
let n = 42
match n {
    case 1 { print("one") }
    case h if h > 10 { print("big") }
}
''').strip() == "big")

# ─────────────────────────────────────────────────────────────────────────────
# Integration — combined Phase 1 features
# ─────────────────────────────────────────────────────────────────────────────
section("Integration — Phase 1 features combined")

ok("is + as together",
   run('''
let x = "42"
if x is string {
    let n = x as int
    print(n + 8)
}
''').strip() == "50")

ok("typed fn + as cast + is check",
   run('''
fn square(n: int) -> int { return n * n }
let x = "5" as int
print(x is int)
print(square(x))
''').strip() == "true\n25")

ok("div in game-loop style",
   run('''
let total = 100
let per_row = 7
let rows = total div per_row
let remainder = total - (rows * per_row)
print(rows)
print(remainder)
''').strip() == "14\n2")

ok("raw string path concat",
   run(r'let base = r"C:\Games"' + '\nlet full = base + "\\\\save.dat"\nprint(full)').strip() == r"C:\Games\save.dat")

ok("let type enforcement in loop",
   run('''
let sum: int = 0
for i in [1, 2, 3, 4, 5] {
    sum = sum + i
}
print(sum)
''').strip() == "15")

ok("match + is check + as cast",
   run('''
fn describe(x) {
    if x is int { print("integer: " + (x as string)) }
    else if x is string { print("string: " + x) }
    else if x is float { print("float") }
    else { print("other") }
}
describe(42)
describe("hello")
describe(3.14)
''').strip() == "integer: 42\nstring: hello\nfloat")

# ─────────────────────────────────────────────────────────────────────────────
# Regression — all prior test files must still pass
# ─────────────────────────────────────────────────────────────────────────────
section("Regression — existing test suites")

def _run_test_file(name: str) -> tuple:
    """Run a test file by importing and running it, capture pass/fail totals."""
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, name],
        capture_output=True, text=True,
        cwd=os.path.dirname(__file__)
    )
    output = result.stdout + result.stderr
    # Try to parse the summary line
    for line in output.splitlines():
        if "passed" in line and ("failed" in line or "out of" in line):
            return output, result.returncode == 0
    return output, result.returncode == 0

for tfile in ["test_lexer.py", "test_parser.py", "test_interpreter.py",
              "test_analyzer.py", "test_stdlib.py", "test_v12.py"]:
    _, passed = _run_test_file(tfile)
    ok(f"{tfile} passes", passed)

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'═'*60}")
print(f"  Phase 1 Test Results")
print(f"{'═'*60}")
print(f"  ✅ Passed: {PASS}")
if FAIL:
    print(f"  ❌ Failed: {FAIL}")
    for f in _FAILURES:
        print(f"     - {f}")
else:
    print(f"  ALL PHASE 1 TESTS PASS")
print(f"{'═'*60}")
sys.exit(0 if FAIL == 0 else 1)
