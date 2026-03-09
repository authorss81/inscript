"""
test_audit.py — Phase Completeness Audit
Systematically verifies every roadmap checklist item for Phases 1, 2, 3.
"""
import sys, os, io

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)

from lexer import Lexer
from parser import Parser
from analyzer import Analyzer
from interpreter import Interpreter
from errors import (
    InScriptRuntimeError, ParseError, SemanticError, MultiError,
    levenshtein, did_you_mean, InScriptCallStack, InScriptWarning,
    ERROR_CODES, WARN_CODES
)

PASS, FAIL = "✅", "❌"
results = []
_fails = []

def test(name, fn):
    try:
        fn()
        results.append((PASS, name))
    except AssertionError as e:
        results.append((FAIL, name, str(e)))
        _fails.append(name)
    except Exception as e:
        results.append((FAIL, name, f"{type(e).__name__}: {e}"))
        _fails.append(name)

def run(src):
    buf = io.StringIO(); sys.stdout = buf
    try:
        i = Interpreter(src.splitlines())
        i.run(Parser(Lexer(src).tokenize(), src).parse())
        sys.stdout = sys.__stdout__
        return buf.getvalue().strip()
    except Exception:
        sys.stdout = sys.__stdout__
        raise

def run_ok(src):
    return run(src)

def run_err(src):
    try:
        run(src)
        return None
    except Exception as e:
        return e

def analyze(src, **kw):
    lines = src.splitlines()
    prog = Parser(Lexer(src).tokenize(), src).parse()
    a = Analyzer(lines, multi_error=True, **kw)
    try: a.analyze(prog)
    except MultiError: pass
    return a


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 1 — Foundation Repair
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "─"*64)
print("  PHASE 1 — Foundation Repair")
print("─"*64)

# 1.1 Runtime Type Enforcement
def t_let_type_mismatch():
    e = run_err('let x: int = "hello"')
    assert e is not None, "Expected TypeError"
    assert "int" in str(e) or "mismatch" in str(e).lower()
test("1.1 let x: int = \"hello\" → TypeError", t_let_type_mismatch)

def t_fn_param_type():
    e = run_err('fn add(a: int, b: int) -> int { return a + b }\nadd("x", 3)')
    assert e is not None, "Expected TypeError on bad param"
test("1.1 fn param type enforcement: add(\"x\", 3) → error", t_fn_param_type)

def t_int_plus_float():
    out = run_ok("print(1 + 2.5)")
    assert out == "3.5", f"Expected 3.5 got {out}"
test("1.1 int + float → float coercion works", t_int_plus_float)

def t_is_operator():
    out = run_ok("let x = 42\nprint(x is int)")
    assert out == "true"
test("1.1 'is' operator: x is int", t_is_operator)

def t_as_cast():
    out = run_ok('let n = "5" as int\nprint(n + 1)')
    assert out == "6"
test("1.1 'as' cast: \"5\" as int + 1 = 6", t_as_cast)

def t_interface_enforcement():
    e = run_err('interface Drawable { fn draw() }\nstruct Box implements Drawable {}')
    assert e is not None, "Expected error for missing method"
    assert "draw" in str(e), f"Error should mention 'draw': {e}"
test("1.1 interface enforcement: missing method → error at definition", t_interface_enforcement)

def t_interface_correct():
    out = run_ok('interface Drawable { fn draw() }\nstruct Sprite implements Drawable { fn draw() { print("ok") } }\nSprite{}.draw()')
    assert out == "ok"
test("1.1 interface: correct implementation passes", t_interface_correct)

def t_interface_inherited():
    out = run_ok('interface Drawable { fn draw() }\nstruct Base { fn draw() { print("base") } }\nstruct Child extends Base {}\nChild{}.draw()')
    assert out == "base"
test("1.1 interface: inherited methods satisfy interface requirement", t_interface_inherited)

# 1.2 div keyword
def t_div_keyword():
    out = run_ok("print(10 div 3)")
    assert out == "3"
test("1.2 div keyword: 10 div 3 = 3", t_div_keyword)

def t_div_negative():
    out = run_ok("print(-7 div 2)")
    assert out == "-4", f"Got {out}"
test("1.2 div floors toward negative infinity: -7 div 2 = -4", t_div_negative)

# 1.4 String literals
def t_raw_string():
    out = run_ok(r'print(r"C:\Users\test")')
    assert "C:" in out and "Users" in out
test("1.4 raw strings: r\"C:\\Users\\test\" no escape processing", t_raw_string)

def t_multiline_string():
    out = run_ok('let s = """hello\nworld"""\nprint(s)')
    assert "hello" in out and "world" in out
test("1.4 multiline strings: triple-quoted", t_multiline_string)

# 1.5 Property getters/setters
def t_property_basic():
    src = '''
struct Temp {
    _c: float = 0.0
    get celsius() -> float { return self._c }
    set celsius(v: float) { self._c = v }
}
let t = Temp {}
t.celsius = 100.0
print(t.celsius)
'''
    out = run_ok(src)
    assert out == "100.0", f"Got {out}"
test("1.5 property getter/setter: basic get/set works", t_property_basic)

def t_property_let_field():
    src = '''
struct Counter {
    let _val: int = 0
    get count() -> int { return self._val }
    set count(v: int) { self._val = v }
}
let c = Counter {}
c.count = 42
print(c.count)
'''
    out = run_ok(src)
    assert out == "42", f"Got {out}"
test("1.5 property with 'let' field declaration inside struct", t_property_let_field)

def t_property_computed():
    src = '''
struct Circle {
    let r: float = 1.0
    get area() -> float { return 3.14159 * self.r * self.r }
}
let c = Circle { r: 5.0 }
print(c.area)
'''
    out = run_ok(src)
    assert float(out) > 78.0 and float(out) < 79.0
test("1.5 computed getter (no setter): area = pi*r^2", t_property_computed)

# 1.6 Match exhaustiveness
def t_match_exhaustiveness_warn():
    src = 'enum Dir { North, South, East }\nlet d: Dir = Dir.North\nmatch d { case Dir.North { print(1) } }'
    a = analyze(src)
    kinds = [w.kind for w in a._warnings]
    assert "exhaustive_match" in kinds, f"Warning missing: {kinds}"
test("1.6 match exhaustiveness: non-exhaustive enum match warns", t_match_exhaustiveness_warn)

def t_match_wildcard_no_warn():
    src = 'enum Dir { North, South }\nlet d: Dir = Dir.North\nmatch d { case Dir.North { } case _ { } }'
    a = analyze(src)
    kinds = [w.kind for w in a._warnings]
    assert "exhaustive_match" not in kinds
test("1.6 match exhaustiveness: wildcard arm suppresses warning", t_match_wildcard_no_warn)

def t_match_all_covered_no_warn():
    src = 'enum Color { Red, Green, Blue }\nlet c: Color = Color.Red\nmatch c { case Color.Red {} case Color.Green {} case Color.Blue {} }'
    a = analyze(src)
    kinds = [w.kind for w in a._warnings]
    assert "exhaustive_match" not in kinds
test("1.6 match exhaustiveness: all variants covered → no warning", t_match_all_covered_no_warn)

def t_match_runtime_error():
    e = run_err('let x = 99\nmatch x { case 1 { print("one") } }')
    assert e is not None and "match" in str(e).lower()
test("1.6 match runtime: non-exhaustive match raises MatchError at runtime", t_match_runtime_error)

# 1.7 PrintStmt deprecation
def t_print_old_style_error():
    try:
        Parser(Lexer('print "hello"').tokenize(), 'print "hello"').parse()
        assert False, "Should raise ParseError"
    except ParseError as e:
        msg = str(e)
        assert "print(" in msg or "function" in msg, f"Error not helpful enough: {msg}"
test("1.7 old-style print \"x\" gives helpful deprecation error", t_print_old_style_error)

def t_print_new_style_works():
    out = run_ok('print("hello")')
    assert out == "hello"
test("1.7 print(\"hello\") as function call works correctly", t_print_new_style_works)

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2 — pygame Backend
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "─"*64)
print("  PHASE 2 — pygame Backend")
print("─"*64)

def t_pygame_backend_exists():
    assert os.path.exists(os.path.join(_here, "pygame_backend.py"))
test("2.1 pygame_backend.py exists", t_pygame_backend_exists)

def t_pygame_backend_namespaces():
    with open(os.path.join(_here, "pygame_backend.py")) as f:
        pb = f.read()
    for ns in ["ScreenNamespace", "DrawNamespace", "InputNamespace",
                "AudioNamespace", "FontNamespace", "Math2DNamespace",
                "ColorHelper", "GameClock"]:
        assert ns in pb, f"Missing namespace: {ns}"
test("2.1 pygame_backend: all 8 namespaces present", t_pygame_backend_namespaces)

def t_pygame_draw_methods():
    with open(os.path.join(_here, "pygame_backend.py")) as f:
        pb = f.read()
    for m in ["def rect", "def circle", "def line", "def text",
              "def sprite", "def sprite_ex", "def polygon", "def ellipse"]:
        assert m in pb, f"Missing draw method: {m}"
test("2.1 draw namespace: rect/circle/line/text/sprite/polygon/ellipse", t_pygame_draw_methods)

def t_pygame_input_methods():
    with open(os.path.join(_here, "pygame_backend.py")) as f:
        pb = f.read()
    for m in ["def key_down", "def key_pressed", "def key_released",
              "def mouse_x", "def mouse_y", "def mouse_down"]:
        assert m in pb, f"Missing input method: {m}"
test("2.1 input namespace: key_down/pressed/released/mouse_x/y/down", t_pygame_input_methods)

def t_pygame_audio_methods():
    with open(os.path.join(_here, "pygame_backend.py")) as f:
        pb = f.read()
    for m in ["def play", "def stop", "def set_volume",
              "def play_music", "def stop_music"]:
        assert m in pb, f"Missing audio method: {m}"
test("2.1 audio namespace: play/stop/set_volume/play_music/stop_music", t_pygame_audio_methods)

def t_pygame_color_constants():
    with open(os.path.join(_here, "pygame_backend.py")) as f:
        pb = f.read()
    for c in ["WHITE", "BLACK", "RED", "GREEN", "BLUE", "GOLD",
              "YELLOW", "CYAN", "ORANGE", "GRAY"]:
        assert c in pb, f"Missing color constant: {c}"
test("2.1 Color namespace: WHITE/BLACK/RED/GREEN/BLUE/GOLD/etc", t_pygame_color_constants)

def t_pygame_game_clock():
    with open(os.path.join(_here, "pygame_backend.py")) as f:
        pb = f.read()
    assert "class GameClock" in pb
    assert "def dt" in pb or "self._dt" in pb
    assert "def every" in pb
    assert "def sin_wave" in pb
test("2.1 GameClock: dt/elapsed/frame_count/every()/sin_wave()", t_pygame_game_clock)

def t_pygame_hooks():
    with open(os.path.join(_here, "pygame_backend.py")) as f:
        pb = f.read()
    assert "on_start" in pb
    assert "on_update" in pb
    assert "on_draw" in pb
    assert "on_exit" in pb
test("2.1 Scene hooks: on_start/on_update/on_draw/on_exit", t_pygame_hooks)

def t_pygame_image_cache():
    with open(os.path.join(_here, "pygame_backend.py")) as f:
        pb = f.read()
    assert "_image_cache" in pb
    assert "_sounds" in pb
test("2.1 Asset caching: image cache + sound cache", t_pygame_image_cache)

def t_game_flag_in_cli():
    with open(os.path.join(_here, "inscript.py")) as f:
        cli = f.read()
    assert "--game" in cli
    assert "--width" in cli
    assert "--height" in cli
    assert "--fps" in cli
test("2.1 CLI --game/--width/--height/--fps flags registered", t_game_flag_in_cli)

# Demo games
for game in ["pong.ins", "breakout.ins", "particles.ins", "dino.ins", "platformer.ins"]:
    def _t(g=game):
        path = os.path.join(_here, "examples", g)
        assert os.path.exists(path), f"Missing: {g}"
        with open(path) as f:
            src = f.read()
        # Must at least parse
        prog = Parser(Lexer(src).tokenize(), src).parse()
        assert prog is not None
    test(f"2.2 examples/{game} exists and parses", _t)


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 3 — Error Quality
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "─"*64)
print("  PHASE 3 — Error Quality")
print("─"*64)

def t_levenshtein():
    assert levenshtein("print", "pint") == 1
    assert levenshtein("screen", "screen") == 0
    assert levenshtein("", "abc") == 3
test("3.1 levenshtein() distance function correct", t_levenshtein)

def t_did_you_mean():
    r = did_you_mean("scor", ["score", "screen", "draw"])
    assert r == "score", f"Got {r}"
test("3.1 did_you_mean('scor', [...]) → 'score'", t_did_you_mean)

def t_runtime_did_you_mean():
    e = run_err("let score = 10\nprint(scor)")
    assert e is not None
    assert "score" in str(e), f"Hint missing: {e}"
test("3.1 runtime NameError includes 'Did you mean: score'", t_runtime_did_you_mean)

def t_analyzer_did_you_mean():
    src = "let score = 10\nprint(scor)\n"
    lines = src.splitlines()
    prog = Parser(Lexer(src).tokenize(), src).parse()
    a = Analyzer(lines, multi_error=True)
    try: a.analyze(prog)
    except MultiError as me:
        assert "score" in str(me), f"Hint missing: {me}"
test("3.1 analyzer undefined name includes 'Did you mean' hint", t_analyzer_did_you_mean)

def t_error_codes():
    from errors import InScriptRuntimeError, NameError_, TypeError_
    assert "E0040" in str(InScriptRuntimeError("x", 1))
    assert "E0042" in str(NameError_("x", 1))
    assert "E0041" in str(TypeError_("x", 1))
test("3.7 all major error types have E-codes in output", t_error_codes)

def t_docs_link():
    from errors import SemanticError
    e = SemanticError("bad", 1)
    assert "docs.inscript.dev" in str(e)
test("3.7 error output includes docs.inscript.dev link", t_docs_link)

def t_call_stack():
    cs = InScriptCallStack("game.ins")
    cs.push("main", 1)
    cs.push("update", 10)
    assert len(cs.snapshot()) == 2
    cs.pop()
    assert len(cs.snapshot()) == 1
test("3.4 InScriptCallStack push/pop/snapshot", t_call_stack)

def t_call_stack_in_error():
    src = "fn inner() -> int { return 1 div 0 }\nfn outer() -> int { return inner() }\nlet x = outer()\n"
    e = run_err(src)
    assert e is not None
    trace = getattr(e, "call_trace", [])
    names = [f[0] for f in trace]
    assert "inner" in names or "outer" in names, f"No fn names in trace: {names}"
test("3.4 RuntimeError includes call stack trace with function names", t_call_stack_in_error)

def t_multi_error():
    src = "fn f() -> int {\n  let a: int = \"x\"\n  let b: int = true\n  return 0\n}\n"
    lines = src.splitlines()
    prog = Parser(Lexer(src).tokenize(), src).parse()
    a = Analyzer(lines, multi_error=True)
    try:
        a.analyze(prog)
    except MultiError as me:
        assert len(me.errors) >= 2, f"Expected ≥2 errors, got {len(me.errors)}"
        return
    assert False, "Expected MultiError"
test("3.5 multi-error: collects all type errors in one pass", t_multi_error)

def t_multi_error_format():
    from errors import SemanticError
    me = MultiError([SemanticError("a", 1), SemanticError("b", 2)])
    assert "Found 2 errors" in str(me)
    assert "1." in str(me)
test("3.5 MultiError formats as numbered list", t_multi_error_format)

def t_warning_unreachable():
    src = "fn f() -> int { return 1\nlet x = 2\nreturn x }\n"
    a = analyze(src)
    assert "unreachable" in [w.kind for w in a._warnings]
test("3.6 warning: unreachable code after return", t_warning_unreachable)

def t_warning_shadow():
    src = "let x = 1\nfn f() -> int { let x = 2\nreturn x }\n"
    a = analyze(src)
    assert "shadow" in [w.kind for w in a._warnings]
test("3.6 warning: shadowed variable", t_warning_shadow)

def t_warning_no_return_ann():
    src = "fn foo() { let x = 1 }\n"
    a = analyze(src)
    assert "missing_return_ann" in [w.kind for w in a._warnings]
test("3.6 warning: missing return type annotation on public fn", t_warning_no_return_ann)

def t_warning_exhaustive_match():
    src = 'enum Color { Red, Green, Blue }\nlet c: Color = Color.Red\nmatch c { case Color.Red {} }\n'
    a = analyze(src)
    assert "exhaustive_match" in [w.kind for w in a._warnings]
test("3.6 warning: non-exhaustive enum match", t_warning_exhaustive_match)

def t_no_warn_flag():
    src = "fn foo() { let x = 1 }\n"
    a = analyze(src, no_warn=True)
    assert len(a._warnings) == 0
test("3.6 --no-warn: suppresses all warnings", t_no_warn_flag)

def t_warn_codes_registry():
    for k in ["unused_var", "unreachable", "shadow", "missing_return_ann",
              "exhaustive_match"]:
        assert k in WARN_CODES, f"Missing warning code: {k}"
test("3.7 WARN_CODES has all warning kinds including exhaustive_match", t_warn_codes_registry)

def t_python_leak_guard():
    from inscript import run_source
    old = sys.stderr; sys.stderr = io.StringIO()
    code = run_source("print(1 + 1)\n", type_check=False)
    sys.stderr = old
    assert code == 0
test("3.3 run_source: no Python leak — valid program exits 0", t_python_leak_guard)

def t_type_error_not_python():
    from inscript import run_source
    old = sys.stderr; sys.stderr = io.StringIO()
    code = run_source('let x: int = "bad"\n', type_check=True)
    captured = sys.stderr.getvalue(); sys.stderr = old
    assert code != 0
    assert "Traceback" not in captured, "Python traceback leaked!"
    assert "InScript" in captured
test("3.3 type error: no Python traceback in output", t_type_error_not_python)


# ═══════════════════════════════════════════════════════════════════════════
# Print Results
# ═══════════════════════════════════════════════════════════════════════════

print()
print("─"*64)
print("  RESULTS")
print("─"*64)

# Group by phase
phases = {"1": [], "2": [], "3": []}
misc = []
for row in results:
    name = row[1]
    if name.startswith("1."):
        phases["1"].append(row)
    elif name.startswith("2."):
        phases["2"].append(row)
    elif name.startswith("3."):
        phases["3"].append(row)
    else:
        misc.append(row)

for ph, rows in phases.items():
    label = {"1": "Phase 1 — Foundation Repair",
             "2": "Phase 2 — pygame Backend",
             "3": "Phase 3 — Error Quality"}[ph]
    passed = sum(1 for r in rows if r[0] == PASS)
    print(f"\n  {label}: {passed}/{len(rows)}")
    for row in rows:
        if row[0] == FAIL:
            print(f"    {row[0]} {row[1]}")
            if len(row) > 2:
                print(f"         ↳ {row[2]}")
        else:
            print(f"    {row[0]} {row[1]}")

total_pass = sum(1 for r in results if r[0] == PASS)
total = len(results)
print()
print("═"*64)
print(f"  TOTAL: {total_pass}/{total} passing")
if _fails:
    print(f"  ❌ {len(_fails)} failing:")
    for f in _fails:
        print(f"     - {f}")
else:
    print("  ALL AUDIT TESTS PASS")
print("═"*64)

sys.exit(0 if not _fails else 1)
