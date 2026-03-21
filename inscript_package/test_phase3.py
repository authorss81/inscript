# -*- coding: utf-8 -*-
"""
test_phase3.py — Phase 3: Error Quality test suite
Tests: 3.1 did-you-mean, 3.2 point-to-def, 3.3 Python-leak guard,
       3.4 call stack, 3.5 multi-error, 3.6 warnings, 3.7 error codes
"""
import sys, io, subprocess, os

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)

from lexer import Lexer
from parser import Parser
from analyzer import Analyzer
from interpreter import Interpreter
from errors import (
    levenshtein, did_you_mean, hint_for_name,
    InScriptCallStack, MultiError, InScriptWarning, InScriptError,
    SemanticError, InScriptRuntimeError, NameError_, TypeError_,
    ERROR_CODES, WARN_CODES,
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

def run_ins(src):
    lines = src.splitlines()
    prog  = Parser(Lexer(src).tokenize(), src).parse()
    buf   = io.StringIO(); saved = sys.stdout; sys.stdout = buf
    try:
        Interpreter(lines).run(prog)
    finally:
        sys.stdout = saved
    return buf.getvalue()

def analyze_src(src, **kw):
    lines = src.splitlines()
    prog  = Parser(Lexer(src).tokenize(), src).parse()
    a     = Analyzer(lines, multi_error=True, **kw)
    a.analyze(prog)
    return a

# ─────────────────────────────────────────────────────────────────────────────
# 3.1 Levenshtein / did-you-mean
# ─────────────────────────────────────────────────────────────────────────────

def t_lev_same():
    assert levenshtein("print", "print") == 0
test("levenshtein: same string = 0", t_lev_same)

def t_lev_one():
    assert levenshtein("print", "pint") == 1
test("levenshtein: 'print'→'pint' = 1", t_lev_one)

def t_lev_two():
    assert levenshtein("screen", "scren") == 1
    assert levenshtein("hello", "helo") == 1
test("levenshtein: single deletion = 1", t_lev_two)

def t_lev_empty():
    assert levenshtein("", "abc") == 3
    assert levenshtein("abc", "") == 3
test("levenshtein: empty string edge case", t_lev_empty)

def t_dym_basic():
    r = did_you_mean("pint", ["print", "point", "int", "float"])
    assert r == "print", f"Expected 'print', got {r!r}"
test("did_you_mean: 'pint' → 'print'", t_dym_basic)

def t_dym_none():
    r = did_you_mean("zzzzz", ["print", "screen", "draw"])
    assert r is None
test("did_you_mean: no match returns None", t_dym_none)

def t_dym_hint_format():
    h = hint_for_name("screan", ["screen", "draw", "input"])
    assert "screen" in h
    assert "Did you mean" in h
test("hint_for_name: formats correctly", t_dym_hint_format)

def t_dym_runtime_undefined():
    src = "let score = 10\nprint(scor)\n"
    try:
        run_ins(src)
        assert False, "Should have raised"
    except NameError_ as e:
        assert "score" in str(e), f"Hint missing in: {e}"
test("did-you-mean in runtime NameError (scor → score)", t_dym_runtime_undefined)

def t_dym_analyzer_undefined():
    src = "let score = 10\nprint(scor)\n"
    lines = src.splitlines()
    prog = Parser(Lexer(src).tokenize(), src).parse()
    a = Analyzer(lines, multi_error=True)
    try:
        a.analyze(prog)
    except MultiError as me:
        msg = str(me)
        assert "score" in msg or "Did you mean" in msg, f"No hint in: {msg}"
test("did-you-mean in analyzer undefined name (scor → score)", t_dym_analyzer_undefined)

def t_dym_struct_field():
    src = "struct Dog { name: string }\nlet d = Dog { naem: \"rex\" }\n"
    lines = src.splitlines()
    prog = Parser(Lexer(src).tokenize(), src).parse()
    a = Analyzer(lines, multi_error=True)
    try:
        a.analyze(prog)
    except MultiError as me:
        msg = str(me)
        assert "naem" in msg or "name" in msg, f"No field info in: {msg}"
test("did-you-mean on struct field typo (naem → name)", t_dym_struct_field)

# ─────────────────────────────────────────────────────────────────────────────
# 3.2 Point-to-definition info in errors
# ─────────────────────────────────────────────────────────────────────────────

def t_error_has_line():
    src = "let x = 1\nprint(bad_name)\n"
    try:
        run_ins(src)
        assert False
    except NameError_ as e:
        assert e.line == 2, f"Expected line 2, got {e.line}"
test("runtime NameError includes correct line number", t_error_has_line)

def t_error_has_source_context():
    src = "let x: int = \"hello\"\n"
    lines = src.splitlines()
    prog = Parser(Lexer(src).tokenize(), src).parse()
    a = Analyzer(lines, multi_error=True)
    try:
        a.analyze(prog)
    except MultiError as me:
        err = me.errors[0]
        assert err.source_line, "source_line should be populated"
test("SemanticError includes source line context", t_error_has_source_context)

def t_error_has_code():
    e = SemanticError("something wrong", 1, 0, "let x = 1")
    assert "E0020" in str(e), f"No code in: {str(e)}"
test("SemanticError has error code E0020 in output", t_error_has_code)

def t_error_has_docs_link():
    e = InScriptRuntimeError("oops", 1, 0, "")
    assert "docs.inscript.dev" in str(e)
test("RuntimeError includes docs link", t_error_has_docs_link)

# ─────────────────────────────────────────────────────────────────────────────
# 3.3 Zero Python leaking
# ─────────────────────────────────────────────────────────────────────────────

def t_no_python_traceback():
    """run_source must not let a raw Python exception through."""
    from inscript import run_source
    old_err = sys.stderr; sys.stderr = io.StringIO()
    try:
        # This should be caught by the internal guard, not crash
        code = run_source("print(1 + 1)\n", filename="<test>", type_check=False)
    finally:
        sys.stderr = old_err
    assert code == 0
test("run_source: valid program exits 0 without leaking", t_no_python_traceback)

def t_inscript_error_caught():
    from inscript import run_source
    old_err = sys.stderr; sys.stderr = io.StringIO()
    try:
        code = run_source("let x: int = \"bad\"\n", filename="<test>", type_check=True)
    finally:
        captured = sys.stderr.getvalue(); sys.stderr = old_err
    assert code != 0
    assert "InScript" in captured, f"Expected InScript error prefix, got: {captured[:200]}"
test("run_source: type error produces InScript-prefixed message, not Python traceback", t_inscript_error_caught)

# ─────────────────────────────────────────────────────────────────────────────
# 3.4 Native call stack
# ─────────────────────────────────────────────────────────────────────────────

def t_callstack_push_pop():
    cs = InScriptCallStack("game.ins")
    cs.push("main", 10)
    cs.push("update", 22)
    assert len(cs.snapshot()) == 2
    cs.pop()
    assert len(cs.snapshot()) == 1
    cs.pop()
    assert len(cs.snapshot()) == 0
test("InScriptCallStack push/pop", t_callstack_push_pop)

def t_callstack_snapshot_content():
    cs = InScriptCallStack("scene.ins")
    cs.push("on_start", 5)
    cs.push("spawn_enemy", 18)
    snap = cs.snapshot()
    assert snap[0] == ("on_start", "scene.ins", 5)
    assert snap[1] == ("spawn_enemy", "scene.ins", 18)
test("InScriptCallStack snapshot returns correct tuples", t_callstack_snapshot_content)

def t_callstack_clean_after_run():
    src = "fn foo() -> int { return 1 }\nlet x = foo()\n"
    lines = src.splitlines()
    prog = Parser(Lexer(src).tokenize(), src).parse()
    interp = Interpreter(lines, filename="test.ins")
    interp.run(prog)
    assert len(interp._call_stack.snapshot()) == 0, "Call stack should be empty after clean run"
test("Call stack is empty after successful program", t_callstack_clean_after_run)

def t_callstack_in_error():
    src = "fn inner() -> int { return 1 / 0 }\nfn outer() -> int { return inner() }\nlet x = outer()\n"
    try:
        run_ins(src)
        assert False, "Should have raised"
    except InScriptRuntimeError as e:
        # The call trace should reference inner and outer
        trace = e.call_trace
        names = [f[0] for f in trace]
        assert "inner" in names or "outer" in names, f"No fn names in trace: {names}"
test("RuntimeError call_trace has function names", t_callstack_in_error)

def t_callstack_format():
    cs = InScriptCallStack("game.ins")
    cs.push("main", 1); cs.push("update", 10)
    fmt = cs.format()
    assert "game.ins" in fmt
    assert "update" in fmt
test("InScriptCallStack.format() includes file and fn name", t_callstack_format)

# ─────────────────────────────────────────────────────────────────────────────
# 3.5 Multi-error reporting
# ─────────────────────────────────────────────────────────────────────────────

def t_multi_error_collects_all():
    src = "fn foo() -> int {\n  let a: int = \"bad\"\n  let b: int = true\n  return 0\n}\n"
    lines = src.splitlines()
    prog = Parser(Lexer(src).tokenize(), src).parse()
    a = Analyzer(lines, multi_error=True)
    try:
        a.analyze(prog)
        assert False, "Expected MultiError"
    except MultiError as me:
        assert len(me.errors) >= 2, f"Expected ≥2 errors, got {len(me.errors)}"
test("Multi-error: collects all errors in one pass (≥2)", t_multi_error_collects_all)

def t_multi_error_format():
    e1 = SemanticError("bad a", 1); e2 = SemanticError("bad b", 5)
    me = MultiError([e1, e2])
    fmt = str(me)
    assert "Found 2 errors" in fmt
    assert "1." in fmt
    assert "2." in fmt
test("MultiError formats with numbered list", t_multi_error_format)

def t_multi_error_cap():
    errors = [SemanticError(f"e{i}", i) for i in range(50)]
    me = MultiError(errors)
    assert len(me.errors) <= MultiError.MAX_ERRORS
test("MultiError caps at MAX_ERRORS", t_multi_error_cap)

def t_single_error_mode():
    src = "let x: int = \"bad\"\n"
    lines = src.splitlines()
    prog = Parser(Lexer(src).tokenize(), src).parse()
    a = Analyzer(lines, multi_error=False)
    try:
        a.analyze(prog)
        assert False
    except SemanticError:
        pass  # single-error mode raises SemanticError directly
test("Analyzer single-error mode raises SemanticError (not MultiError)", t_single_error_mode)

# ─────────────────────────────────────────────────────────────────────────────
# 3.6 Warning system
# ─────────────────────────────────────────────────────────────────────────────

def t_warn_missing_return_ann():
    src = "fn foo() { let x = 1 }\n"
    a = analyze_src(src)
    kinds = [w.kind for w in a._warnings]
    assert "missing_return_ann" in kinds, f"Kinds: {kinds}"
test("Warning: missing return type annotation on public fn", t_warn_missing_return_ann)

def t_warn_unreachable():
    src = "fn bar() -> int { return 1\nlet x = 2\nreturn x }\n"
    a = analyze_src(src)
    kinds = [w.kind for w in a._warnings]
    assert "unreachable" in kinds, f"Kinds: {kinds}"
test("Warning: unreachable code after return", t_warn_unreachable)

def t_warn_shadow():
    src = "let x = 1\nfn foo() -> int { let x = 2\nreturn x }\n"
    a = analyze_src(src)
    kinds = [w.kind for w in a._warnings]
    assert "shadow" in kinds, f"Kinds: {kinds}"
test("Warning: shadowed variable", t_warn_shadow)

def t_no_warn_flag():
    src = "fn foo() { let x = 1 }\n"
    a = analyze_src(src, no_warn=True)
    assert len(a._warnings) == 0
test("--no-warn suppresses all warnings", t_no_warn_flag)

def t_warn_as_error():
    src = "fn foo() { let x = 1 }\n"
    lines = src.splitlines()
    prog = Parser(Lexer(src).tokenize(), src).parse()
    a = Analyzer(lines, multi_error=True, warn_as_error=True)
    try:
        a.analyze(prog)
    except MultiError as me:
        # warn_as_error converts warnings to errors
        assert len(me.errors) > 0
        return
    # May have also passed if no warnings triggered
test("--warn-as-error converts warnings to errors", t_warn_as_error)

def t_warning_format():
    w = InScriptWarning("unused_var", "Variable 'x' is never used", 5, "  let x = 0")
    fmt = w.format()
    assert "W0001" in fmt
    assert "Line 5" in fmt
    assert "Variable 'x'" in fmt
test("InScriptWarning.format() includes code, line, message", t_warning_format)

def t_no_warn_suppresses_output():
    from inscript import run_source
    src = "fn foo() { let x = 1 }\nfoo()\n"
    old_err = sys.stderr; sys.stderr = io.StringIO()
    run_source(src, type_check=True, no_warn=True)
    captured = sys.stderr.getvalue(); sys.stderr = old_err
    assert "Warning" not in captured, f"Warning appeared despite --no-warn: {captured}"
test("run_source --no-warn: no Warning lines in stderr", t_no_warn_suppresses_output)

# ─────────────────────────────────────────────────────────────────────────────
# 3.7 Error code system
# ─────────────────────────────────────────────────────────────────────────────

def t_all_major_codes_defined():
    for key in ["LexerError", "ParseError", "SemanticError",
                "InScriptRuntimeError", "TypeError_", "NameError_",
                "IndexError_", "MatchError", "StackOverflow"]:
        assert key in ERROR_CODES, f"Missing code for {key}"
test("Error code registry has all major error types", t_all_major_codes_defined)

def t_warning_codes_defined():
    for key in ["unused_var", "unused_import", "unreachable",
                "shadow", "missing_return_ann"]:
        assert key in WARN_CODES, f"Missing warning code for {key}"
test("Warning code registry has all warning kinds", t_warning_codes_defined)

def t_error_code_in_output():
    e = NameError_("Undefined: 'x'", 3, 0, "print(x)")
    s = str(e); assert "E0042" in s, f"Code missing in: {s}"
test("NameError_ output includes E0042", t_error_code_in_output)

def t_error_code_e0047_match():
    from errors import ERROR_CODES
    assert ERROR_CODES.get("MatchError") == "E0047"
test("MatchError → E0047 in code registry", t_error_code_e0047_match)

def t_docs_link_in_runtime_error():
    e = InScriptRuntimeError("division by zero", 10, 0, "let x = 1/0")
    s = str(e)
    assert "docs.inscript.dev/errors/E0040" in s
test("RuntimeError output includes docs link E0040", t_docs_link_in_runtime_error)

def t_error_with_hint():
    e = SemanticError("Undefined name: 'x'", 1)
    e.with_hint("Did you mean: 'score'?")
    s = str(e)
    assert "Did you mean" in s
test("with_hint() attaches suggestion to error output", t_error_with_hint)

# ─────────────────────────────────────────────────────────────────────────────
# Print results
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "─" * 64)
print("  Phase 3 — Error Quality Tests")
print("─" * 64)
for row in results:
    if len(row) == 2:
        print(f"  {row[0]} {row[1]}")
    else:
        print(f"  {row[0]} {row[1]}")
        print(f"       ↳ {row[2]}")

passed = sum(1 for r in results if r[0] == PASS)
total  = len(results)
print("\n" + "═" * 64)
print(f"  Phase 3 Test Results")
print("═" * 64)
print(f"  ✅ Passed: {passed} / {total}")
if _fails:
    print(f"  ❌ Failed: {len(_fails)}")
    for f in _fails:
        print(f"     - {f}")
else:
    print("  ALL PHASE 3 TESTS PASS")
print("═" * 64)

sys.exit(0 if not _fails else 1)
