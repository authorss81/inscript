"""
test_v196.py — v1.9.6: # line comments; // always floor division

Breaking changes verified:
  - # is the line-comment character
  - // is ALWAYS floor division, spaces allowed: 10 // 3 == 3
  - inscript migrate converts // comments → # comments
"""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(__file__))

from lexer import Lexer, TT
from parser import Parser
from interpreter import Interpreter
from environment import Environment

passed = failed = 0

def ok(name):
    global passed; passed += 1; print(f"  PASS  {name}")

def fail(name, reason=""):
    global failed; failed += 1; print(f"  FAIL  {name}  {reason}")

def run(src):
    lx = Lexer(src); tokens = lx.tokenize()
    pr = Parser(tokens); tree = pr.parse()
    interp = Interpreter(); interp._env = Environment()
    return interp.visit(tree)

def expect_value(name, src, expected):
    try:
        result = run(src)
        if result == expected: ok(name)
        else: fail(name, f"got {result!r}, expected {expected!r}")
    except Exception as e:
        fail(name, f"raised {e}")

def expect_parse_error(name, src, fragment=""):
    try:
        Lexer(src).tokenize()
        Parser(Lexer(src).tokenize()).parse()
        fail(name, "expected error but none raised")
    except Exception as e:
        msg = str(e)
        if fragment and fragment not in msg: fail(name, f"'{fragment}' not in: {msg[:100]}")
        else: ok(name)

def tokens_of(src):
    return [(t.type, t.value) for t in Lexer(src).tokenize()]

# ── 1-8: // is ALWAYS floor division (spaces allowed) ────────────────────────

expect_value("floor_div_no_spaces",       "10//3",          3)
expect_value("floor_div_with_spaces",     "10 // 3",        3)
expect_value("floor_div_mixed_spaces",    "10  //  3",      3)
expect_value("floor_div_negative",        "-10 // 3",       -4)
expect_value("floor_div_vars",            "let a=10\nlet b=3\na // b", 3)
expect_value("floor_div_in_expr",         "2 + 10 // 3",    5)
expect_value("floor_div_chained",         "100 // 3 // 2",  16)
expect_value("floor_div_in_fn",
    "fn half(n: int) -> int { return n // 2 }\nhalf(11)", 5)

# ── 9-14: # is the line comment ──────────────────────────────────────────────

expect_value("hash_comment_standalone",
    "# this whole line is a comment\nlet x = 42\nx", 42)

expect_value("hash_comment_inline",
    "let x = 99 # inline comment\nx", 99)

expect_value("hash_comment_after_expr",
    "let a = 5\nlet b = 3\nlet c = a + b # sum\nc", 8)

expect_value("hash_comment_does_not_affect_value",
    "let x = 10 // 2 # this divides ten by two\nx", 5)

expect_value("hash_comment_multiple_lines",
    "# first comment\nlet x = 1\n# second comment\nlet y = 2\nx + y", 3)

expect_value("hash_comment_in_fn",
    "fn add(a: int, b: int) -> int {\n    # add two numbers\n    return a + b # result\n}\nadd(3, 4)", 7)

# ── 15-18: // with spaces is floor division (not comment) ────────────────────

def t_slash_slash_token():
    """// must always tokenise as SLASH_SLASH, never be skipped."""
    tts = [t for t, _ in tokens_of("10 // 3")]
    if TT.SLASH_SLASH not in tts:
        fail("slash_slash_token", f"SLASH_SLASH missing from {tts}")
    else:
        ok("slash_slash_token")

t_slash_slash_token()

def t_no_slash_slash_in_comment():
    """# comment must not produce any tokens after the #."""
    tts = [t for t, _ in tokens_of("let x = 5 # note\nlet y = 10")]
    idents = [v for t, v in tokens_of("let x = 5 # note\nlet y = 10")
              if t == TT.IDENT]
    if "note" in idents:
        fail("hash_no_token_after", f"comment content appeared as token: {idents}")
    else:
        ok("hash_no_token_after")

t_no_slash_slash_in_comment()

expect_value("spaced_floor_div_in_array", "[10 // 3, 20 // 4]", [3, 5])
expect_value("spaced_floor_div_in_loop",
    "let s = 0\nfor i in [2, 4, 6] { s = s + i // 2 }\ns", 6)

# ── 19-24: inscript migrate converts // comments → # ─────────────────────────

import re as _re

def migrate(src: str) -> str:
    """Mirror of inscript._migrate_files logic — comment rules BEFORE div→//."""
    # v1.9.6: comment rules first so div→// doesn't get re-converted to #
    src = _re.sub(r'^(\s*)//', r'\1#', src, flags=_re.MULTILINE)
    src = _re.sub(r'(\s)//(\s+[A-Za-z_])', r'\1#\2', src)
    src = _re.sub(r'\bnull\b', 'nil', src)
    src = _re.sub(r'\bdiv\b', '//', src)
    src = _re.sub(r':\s*\[\]', ': array', src)
    return src
def t_migrate(name, src, expected):
    result = migrate(src)
    if result == expected: ok(f"migrate_{name}")
    else: fail(f"migrate_{name}", f"got {result!r}, want {expected!r}")

t_migrate("standalone_comment",
    "// this is a comment\nlet x = 1\n",
    "# this is a comment\nlet x = 1\n")

t_migrate("inline_word_comment",
    "let x = 5 // note\nprint(x)\n",
    "let x = 5 # note\nprint(x)\n")

t_migrate("floor_div_number_unchanged",
    "let x = 10 // 3\n",
    "let x = 10 // 3\n")  # digit after // → NOT a comment → unchanged

t_migrate("floor_div_nospace_unchanged",
    "let x = 10//3\n",
    "let x = 10//3\n")

t_migrate("mixed_file",
    "// header comment\nlet x = 10 // 3\nlet y = x // note\n",
    "# header comment\nlet x = 10 // 3\nlet y = x # note\n")

t_migrate("indented_comment",
    "fn f() {\n    // body comment\n    return 1\n}\n",
    "fn f() {\n    # body comment\n    return 1\n}\n")

# ── 25-26: /* */ block comments still work ───────────────────────────────────

expect_value("block_comment_still_works",
    "let x = /* this is ignored */ 42\nx", 42)

expect_value("block_comment_multiline",
    "let x = 1\n/* multi\nline\ncomment */\nlet y = 2\nx + y", 3)

# ── Summary ───────────────────────────────────────────────────────────────────

total = passed + failed
print()
print("=" * 58)
print(f"  v1.9.6 Test Results: {passed}/{total} passed")
print("  ALL PASS" if failed == 0 else f"  {failed} FAILED")
print("=" * 58)
sys.exit(0 if failed == 0 else 1)
