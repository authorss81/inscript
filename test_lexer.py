# inscript/test_lexer.py
# Comprehensive tests for the InScript Lexer (Phase 1)
# Run with: python test_lexer.py

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from lexer import Lexer, TT, tokenize
from errors import LexerError

PASS = "✅"
FAIL = "❌"
results = []

def test(name: str, fn):
    try:
        fn()
        results.append((PASS, name))
    except Exception as e:
        results.append((FAIL, name, str(e)))

# ─── Helper ────────────────────────────────────
def tokens_of(src: str):
    """Returns list of (type, value) excluding EOF."""
    toks = tokenize(src)
    return [(t.type, t.value) for t in toks if t.type != TT.EOF]

def types_of(src: str):
    return [t.type for t in tokenize(src) if t.type != TT.EOF]


# ─── Test: Integer literals ────────────────────
def test_integers():
    ts = tokens_of("42 0 1_000_000")
    assert ts == [(TT.INT, 42), (TT.INT, 0), (TT.INT, 1_000_000)], f"Got {ts}"
test("Integer literals", test_integers)

# ─── Test: Float literals ──────────────────────
def test_floats():
    ts = tokens_of("3.14 0.5 1.0e3 2.5e-2")
    assert ts[0] == (TT.FLOAT, 3.14)
    assert ts[1] == (TT.FLOAT, 0.5)
    assert ts[2] == (TT.FLOAT, 1000.0)
    assert abs(ts[3][1] - 0.025) < 1e-10
test("Float literals", test_floats)

# ─── Test: String literals ──────────────────────
def test_strings():
    ts = tokens_of('"hello" "world"')
    assert ts == [(TT.STRING, "hello"), (TT.STRING, "world")]
test("String double-quoted", test_strings)

def test_string_single():
    ts = tokens_of("'inscript'")
    assert ts == [(TT.STRING, "inscript")]
test("String single-quoted", test_string_single)

def test_string_escapes():
    ts = tokens_of(r'"line1\nline2"')
    assert ts[0][1] == "line1\nline2"
test("String escape sequences", test_string_escapes)

# ─── Test: Boolean and null ────────────────────
def test_bools():
    ts = tokens_of("true false null")
    assert ts[0] == (TT.BOOL, True)
    assert ts[1] == (TT.BOOL, False)
    assert ts[2] == (TT.NULL, None)
test("Boolean and null literals", test_bools)

# ─── Test: Keywords ────────────────────────────
def test_keywords():
    src = "let const fn return if else while for in break continue struct scene"
    expected = [
        TT.LET, TT.CONST, TT.FN, TT.RETURN,
        TT.IF, TT.ELSE, TT.WHILE, TT.FOR, TT.IN,
        TT.BREAK, TT.CONTINUE, TT.STRUCT, TT.SCENE
    ]
    assert types_of(src) == expected
test("Keywords recognized", test_keywords)

def test_scene_lifecycle():
    src = "on_start on_update on_draw on_exit"
    expected = [TT.ON_START, TT.ON_UPDATE, TT.ON_DRAW, TT.ON_EXIT]
    assert types_of(src) == expected
test("Scene lifecycle keywords", test_scene_lifecycle)

def test_type_keywords():
    src = "int float bool string void"
    expected = [TT.INT_TYPE, TT.FLOAT_TYPE, TT.BOOL_TYPE, TT.STRING_TYPE, TT.VOID_TYPE]
    assert types_of(src) == expected
test("Type keywords", test_type_keywords)

# ─── Test: Identifiers ────────────────────────
def test_identifiers():
    ts = tokens_of("playerSpeed _private myVar123")
    assert ts == [
        (TT.IDENT, "playerSpeed"),
        (TT.IDENT, "_private"),
        (TT.IDENT, "myVar123"),
    ]
test("Identifiers", test_identifiers)

# ─── Test: Arithmetic operators ───────────────
def test_arithmetic():
    src = "+ - * / % **"
    expected = [TT.PLUS, TT.MINUS, TT.STAR, TT.SLASH, TT.PERCENT, TT.POWER]
    assert types_of(src) == expected
test("Arithmetic operators", test_arithmetic)

# ─── Test: Comparison operators ───────────────
def test_comparison():
    src = "== != < > <= >="
    expected = [TT.EQ, TT.NEQ, TT.LT, TT.GT, TT.LTE, TT.GTE]
    assert types_of(src) == expected
test("Comparison operators", test_comparison)

# ─── Test: Logical operators ──────────────────
def test_logical():
    src = "&& || !"
    assert types_of(src) == [TT.AND, TT.OR, TT.NOT]
test("Logical operators", test_logical)

# ─── Test: Assignment operators ───────────────
def test_assignment():
    src = "= += -= *= /="
    expected = [TT.ASSIGN, TT.PLUS_EQ, TT.MINUS_EQ, TT.STAR_EQ, TT.SLASH_EQ]
    assert types_of(src) == expected
test("Assignment operators", test_assignment)

# ─── Test: Delimiters ─────────────────────────
def test_delimiters():
    src = "( ) { } [ ] , . : ; -> ::"
    expected = [
        TT.LPAREN, TT.RPAREN,
        TT.LBRACE, TT.RBRACE,
        TT.LBRACKET, TT.RBRACKET,
        TT.COMMA, TT.DOT, TT.COLON, TT.SEMICOLON,
        TT.ARROW, TT.DOUBLE_COLON,
    ]
    assert types_of(src) == expected
test("Delimiters", test_delimiters)

# ─── Test: Line/column tracking ───────────────
def test_positions():
    src = "let\n  x"
    toks = [t for t in tokenize(src) if t.type != TT.EOF]
    assert toks[0].line == 1 and toks[0].col == 1,  f"let at {toks[0].line}:{toks[0].col}"
    assert toks[1].line == 2 and toks[1].col == 3,  f"x at {toks[1].line}:{toks[1].col}"
test("Line and column tracking", test_positions)

# ─── Test: Line comments ──────────────────────
def test_line_comments():
    src = "let x = 5 // this is a comment\nlet y = 10"
    ts = tokens_of(src)
    # Should have let, x, =, 5, let, y, =, 10 — no comment content
    tts = [t for t, _ in ts]
    assert TT.IDENT not in tts or "this" not in [v for _, v in ts]
    assert (TT.INT, 5)  in ts
    assert (TT.INT, 10) in ts
test("Single-line comments skipped", test_line_comments)

# ─── Test: Block comments ─────────────────────
def test_block_comments():
    src = "let /* this is a\nmultiline comment */ x = 1"
    ts = tokens_of(src)
    tts = [t for t, _ in ts]
    assert TT.LET in tts
    assert TT.IDENT in tts
    assert (TT.INT, 1) in ts
    # comment content should not appear
    assert "this" not in [v for _, v in ts]
test("Block comments skipped", test_block_comments)

# ─── Test: Nested block comments ──────────────
def test_nested_block_comments():
    src = "x /* outer /* inner */ still outer */ y"
    ts = tokens_of(src)
    vals = [v for _, v in ts]
    assert "x" in vals and "y" in vals
    assert "outer" not in vals and "inner" not in vals
test("Nested block comments", test_nested_block_comments)

# ─── Test: Full code snippet ──────────────────
def test_full_snippet():
    src = """
    let score: int = 0
    fn add(a: int, b: int) -> int {
        return a + b
    }
    """
    tts = types_of(src)
    assert TT.LET        in tts
    assert TT.COLON      in tts
    assert TT.INT_TYPE   in tts
    assert TT.ASSIGN     in tts
    assert TT.FN         in tts
    assert TT.ARROW      in tts
    assert TT.LBRACE     in tts
    assert TT.RETURN     in tts
    assert TT.PLUS       in tts
    assert TT.RBRACE     in tts
test("Full code snippet tokenizes correctly", test_full_snippet)

# ─── Test: Error — unterminated string ────────
def test_unterminated_string():
    try:
        tokenize('"hello')
        assert False, "Should have raised LexerError"
    except LexerError as e:
        assert "Unterminated" in e.message
test("Error: unterminated string", test_unterminated_string)

# ─── Test: Error — unexpected character ───────
def test_unexpected_char():
    try:
        tokenize("let x = @5")
        assert False, "Should have raised LexerError"
    except LexerError as e:
        assert "Unexpected character" in e.message
test("Error: unexpected character '@'", test_unexpected_char)

# ─── Test: Error — single & ───────────────────
def test_single_ampersand():
    try:
        tokenize("x & y")
        assert False
    except LexerError as e:
        assert "&&" in e.message
test("Error: single '&' gives helpful message", test_single_ampersand)

# ─── Test: EOF token always present ───────────
def test_eof():
    toks = tokenize("")
    assert toks[-1].type == TT.EOF
    toks2 = tokenize("let x = 1")
    assert toks2[-1].type == TT.EOF
test("EOF token always appended", test_eof)

# ─── Test: Number underscore separator ────────
def test_number_separator():
    ts = tokens_of("1_000_000")
    assert ts == [(TT.INT, 1_000_000)]
test("Number underscore separators", test_number_separator)

# ─────────────────────────────────────────────
# RESULTS
# ─────────────────────────────────────────────

print("\n" + "="*55)
print("  InScript Lexer — Test Results")
print("="*55)

passed = 0
failed = 0
for r in results:
    if r[0] == PASS:
        print(f"  {r[0]} {r[1]}")
        passed += 1
    else:
        print(f"  {r[0]} {r[1]}")
        print(f"       Error: {r[2]}")
        failed += 1

print("="*55)
print(f"  {passed} passed, {failed} failed out of {len(results)} tests")
print("="*55 + "\n")

if failed > 0:
    sys.exit(1)
