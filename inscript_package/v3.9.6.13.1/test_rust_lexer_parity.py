# v3.9.6.13.1 — Rust lexer parity: scene/type/compound-assign keywords + error wrapping
# Tests that the Rust lexer now matches the Python lexer's output.
# Run with: python v3.9.6.13.1/test_rust_lexer_parity.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

from lexer import tokenize, TT

PASS, FAIL = 0, 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  {chr(0x2705)} {name}")
        PASS += 1
    else:
        print(f"  {chr(0x274C)} {name}  {detail}")
        FAIL += 1

# ── 1. Scene lifecycle keywords ────────────────────────────
def test_scene_lifecycle():
    toks = tokenize("on_start on_update on_draw on_exit")
    types = [t.type for t in toks if t.type != TT.EOF]
    expected = [TT.ON_START, TT.ON_UPDATE, TT.ON_DRAW, TT.ON_EXIT]
    check("scene lifecycle keywords got correct tokens", types == expected,
          f"got {types}")
test_scene_lifecycle()

# ── 2. Type keywords ───────────────────────────────────────
def test_type_keywords():
    toks = tokenize("int float bool string void")
    types = [t.type for t in toks if t.type != TT.EOF]
    expected = [TT.INT_TYPE, TT.FLOAT_TYPE, TT.BOOL_TYPE, TT.STRING_TYPE, TT.VOID_TYPE]
    check("type keywords got correct tokens", types == expected,
          f"got {types}")
test_type_keywords()

# ── 3. Type keywords in function signatures ─────────────────
def test_type_in_sig():
    toks = tokenize("fn add(a: int, b: int) -> int { return a + b }")
    types = [t.type for t in toks if t.type != TT.EOF]
    assert TT.FN in types
    count_int = types.count(TT.INT_TYPE)
    check("INT_TYPE appears in function signature", count_int == 3,
          f"expected 3 INT_TYPE, got {count_int}")
test_type_in_sig()

# ── 4. Compound assignment operators ──────────────────────
def test_compound_assign():
    src = "= += -= *= /= %= **= &= |= ^= <<= >>="
    toks = tokenize(src)
    types = [t.type for t in toks if t.type != TT.EOF]
    expected = [TT.ASSIGN, TT.PLUS_EQ, TT.MINUS_EQ, TT.STAR_EQ,
                TT.SLASH_EQ, TT.PERCENT_EQ, TT.POWER_EQ,
                TT.AMP_EQ, TT.PIPE_EQ, TT.CARET_EQ,
                TT.LSHIFT_EQ, TT.RSHIFT_EQ]
    check("compound assignment operators get correct tokens", types == expected,
          f"got {types}")
test_compound_assign()

# ── 5. Compound assign in real code ────────────────────────
def test_compound_in_code():
    toks = tokenize("x += 1; y -= 2; z *= 3; w /= 4")
    types = [t.type for t in toks if t.type != TT.EOF]
    check("+= in code", TT.PLUS_EQ in types, f"got {types}")
    check("-= in code", TT.MINUS_EQ in types)
    check("*= in code", TT.STAR_EQ in types)
    check("/= in code", TT.SLASH_EQ in types)
test_compound_in_code()

# ── 6. Error: unterminated string raises LexerError ─────────
def test_rust_error_wrapping():
    from errors import LexerError
    try:
        tokenize('"hello')
        check("unterminated string raises LexerError", False)
    except LexerError as e:
        check("unterminated string raises LexerError", "Unterminated" in str(e) or "Unterminated" in e.message)
    except Exception as e:
        check("unterminated string raises LexerError", False, f"got {type(e).__name__}: {e}")
test_rust_error_wrapping()

# ── 7. Error: unexpected character raises LexerError ────────
def test_unexpected_char_error():
    from errors import LexerError
    try:
        tokenize("let x = `5")
        check("unexpected backtick raises LexerError", False)
    except LexerError as e:
        check("unexpected backtick raises LexerError", "Unexpected" in str(e) or "Unexpected" in e.message)
    except Exception as e:
        check("unexpected backtick raises LexerError", False, f"got {type(e).__name__}: {e}")
test_unexpected_char_error()

# ── 8. Node lifecycle keywords ─────────────────────────────
def test_node_lifecycle():
    toks = tokenize("node _ready _update _draw")
    types = [t.type for t in toks if t.type != TT.EOF]
    expected = [TT.NODE, TT.ON_READY, TT.ON_NODE_UPDATE, TT.ON_NODE_DRAW]
    check("node lifecycle keywords got correct tokens", types == expected,
          f"got {types}")
test_node_lifecycle()

# ── 9. Keywords that should still be Identifiers ────────────
def test_soft_keywords():
    toks = tokenize("import from as")
    types = [t.type for t in toks if t.type != TT.EOF]
    check("import is still IDENT", all(t == TT.IDENT for t in types),
          f"got {types}")
test_soft_keywords()

# ── 10. && || ! still work ─────────────────────────────────
def test_logical_operators():
    toks = tokenize("a && b || !c")
    types = [t.type for t in toks if t.type != TT.EOF]
    check("&& is AND", TT.AND in types)
    check("|| is OR", TT.OR in types)
    check("! is NOT", TT.NOT in types)
test_logical_operators()

# ── 11. Arithmetic operators still work ─────────────────────
def test_arithmetic():
    toks = tokenize("1 + 2 - 3 * 4 / 5 % 6 ** 7")
    types = [t.type for t in toks if t.type != TT.EOF]
    for op, name in [(TT.PLUS, "+"), (TT.MINUS, "-"), (TT.STAR, "*"),
                     (TT.SLASH, "/"), (TT.PERCENT, "%"), (TT.POWER, "**")]:
        check(f"{name} arithmetic operator", op in types)
test_arithmetic()

# ── 12. ++ and // ──────────────────────────────────────────
def test_pp_slash():
    toks = tokenize('"hello" ++ "world" ; 10 // 3')
    types = [t.type for t in toks if t.type != TT.EOF]
    check("++ is PLUSPLUS", TT.PLUSPLUS in types)
    check("// is SLASH_SLASH", TT.SLASH_SLASH in types)
test_pp_slash()

# ── 13. Mixed type + assign in real code ────────────────────
def test_full_real_code():
    src = """
    let score: int = 0
    fn add(a: int, b: int) -> int { return a + b }
    score += 10
    """
    toks = tokenize(src)
    types = [t.type for t in toks if t.type != TT.EOF]
    check("let keyword", TT.LET in types)
    check("colon", TT.COLON in types)
    check("int type in full snippet", TT.INT_TYPE in types)
    check("fn keyword", TT.FN in types)
    check("arrow in full snippet", TT.ARROW in types)
    check("return keyword", TT.RETURN in types)
    check("+ operator in full snippet", TT.PLUS in types)
    check("plus_eq in full snippet", TT.PLUS_EQ in types)
    check("assign = in full snippet", TT.ASSIGN in types)
test_full_real_code()

# ── RESULTS ────────────────────────────────────────────────
print()
print("=" * 55)
print("  v3.9.6.13.1 — Rust Lexer Parity Tests")
print("=" * 55)
print(f"  {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 55)
if FAIL > 0:
    sys.exit(1)
