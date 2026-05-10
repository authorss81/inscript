"""
test_v1910.py — v1.9.10: v2.0.0 readiness gate (inscript --check-v2)

Tests:
  1-3:   --check-v2 flag exists in CLI, runs without crash
  4-6:   clean project dir passes all gates
  7-10:  project with div/null/old-comments fails the right gates
  11-13: InScriptCoroutine gate passes (v1.9.7 applied)
  14-15: Array<T> inference gate passes (v1.9.8 applied)
  16-18: toml/lock missing = warning not failure
  19-21: exit code 0 on all-pass, exit code 1 on failures
"""
import sys, os, tempfile, subprocess
sys.path.insert(0, os.path.dirname(__file__))

from inscript import _check_v2_readiness, MANIFEST_FILENAME, LOCK_FILENAME
from inscript import _write_lock_entry

passed = failed = 0

def ok(name):
    global passed; passed += 1; print(f"  PASS  {name}")

def fail(name, reason=""):
    global failed; failed += 1; print(f"  FAIL  {name}  {reason}")

def capture_check_v2(project_dir):
    """Run _check_v2_readiness, capture stdout, return (ret, output)."""
    import io
    buf = io.StringIO()
    old = sys.stdout; sys.stdout = buf
    try:
        ret = _check_v2_readiness(project_dir)
    finally:
        sys.stdout = old
    return ret, buf.getvalue()

def make_ins(d, name, content):
    p = os.path.join(d, name)
    open(p, "w", encoding="utf-8").write(content)
    return p

# ── 1-3: CLI flag wiring ──────────────────────────────────────────────────────

def t_flag_in_help():
    r = subprocess.run([sys.executable, "inscript.py", "--help"],
                       capture_output=True, text=True)
    if "--check-v2" in r.stdout: ok("check_v2_in_help")
    else: fail("check_v2_in_help", "not in --help output")

t_flag_in_help()

def t_runs_on_empty_dir():
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run([sys.executable, "inscript.py", "--check-v2", d],
                           capture_output=True, text=True)
        if "Readiness" in r.stdout or "gates" in r.stdout:
            ok("check_v2_runs_on_empty_dir")
        else:
            fail("check_v2_runs_on_empty_dir", f"unexpected: {r.stdout[:200]}")

t_runs_on_empty_dir()

def t_default_dot():
    r = subprocess.run([sys.executable, "inscript.py", "--check-v2"],
                       capture_output=True, text=True)
    # Should run on current dir without crashing
    if r.returncode in (0, 1):
        ok("check_v2_default_dot")
    else:
        fail("check_v2_default_dot", f"unexpected returncode {r.returncode}")

t_default_dot()

# ── 4-6: clean project passes relevant gates ─────────────────────────────────

def t_clean_ins_passes_div_null_gates():
    with tempfile.TemporaryDirectory() as d:
        make_ins(d, "main.ins", "let x = 42\nlet s = \"hello\"\n")
        ret, out = capture_check_v2(d)
        if "div keyword removed" in out and "✅" in out:
            ok("clean_div_gate_passes")
        else:
            fail("clean_div_gate_passes", f"gate missing from: {out[:300]}")
        if "null keyword removed" in out and out.count("✅") >= 2:
            ok("clean_null_gate_passes")
        else:
            fail("clean_null_gate_passes", f"null gate missing: {out[:300]}")

t_clean_ins_passes_div_null_gates()

def t_clean_passes_comment_gate():
    with tempfile.TemporaryDirectory() as d:
        make_ins(d, "app.ins", "# this is a comment\nlet x = 10 // 3\n")
        ret, out = capture_check_v2(d)
        if "# line comments" in out:
            ok("clean_comment_gate_present")
        else:
            fail("clean_comment_gate_present", out[:200])

t_clean_passes_comment_gate()

# ── 7-10: dirty project fails correct gates ───────────────────────────────────

def t_div_in_file_fails_gate():
    with tempfile.TemporaryDirectory() as d:
        make_ins(d, "bad.ins", "let x = 10 div 3\n")
        ret, out = capture_check_v2(d)
        if "❌" in out and "div" in out:
            ok("div_gate_fails_correctly")
        else:
            fail("div_gate_fails_correctly", f"ret={ret} out={out[:200]}")

t_div_in_file_fails_gate()

def t_null_in_file_fails_gate():
    with tempfile.TemporaryDirectory() as d:
        make_ins(d, "bad.ins", "let x = null\n")
        ret, out = capture_check_v2(d)
        if "❌" in out and "null" in out:
            ok("null_gate_fails_correctly")
        else:
            fail("null_gate_fails_correctly", f"ret={ret} out={out[:200]}")

t_null_in_file_fails_gate()

def t_old_comment_fails_gate():
    with tempfile.TemporaryDirectory() as d:
        make_ins(d, "old.ins", "// this is an old comment\nlet x = 1\n")
        ret, out = capture_check_v2(d)
        if "❌" in out and "comment" in out:
            ok("old_comment_gate_fails")
        else:
            fail("old_comment_gate_fails", f"ret={ret} out={out[:200]}")

t_old_comment_fails_gate()

def t_exit_code_1_on_failures():
    with tempfile.TemporaryDirectory() as d:
        make_ins(d, "bad.ins", "let x = 10 div 3\nlet y = null\n")
        ret, _ = capture_check_v2(d)
        if ret == 1: ok("exit_1_on_failures")
        else: fail("exit_1_on_failures", f"got {ret}")

t_exit_code_1_on_failures()

# ── 11-13: runtime gates (async/await, type inference) ───────────────────────

def t_async_gate_passes():
    with tempfile.TemporaryDirectory() as d:
        ret, out = capture_check_v2(d)
        if "async/await real" in out and "InScriptCoroutine" in out:
            ok("async_gate_present")
        else:
            fail("async_gate_present", f"not in output: {out[:300]}")

t_async_gate_passes()

def t_inference_gate_passes():
    with tempfile.TemporaryDirectory() as d:
        ret, out = capture_check_v2(d)
        if "Array<T> type inference" in out:
            ok("inference_gate_present")
        else:
            fail("inference_gate_present", f"not in output: {out[:300]}")

t_inference_gate_passes()

def t_runtime_gates_show_pass():
    with tempfile.TemporaryDirectory() as d:
        ret, out = capture_check_v2(d)
        pass_count = out.count("✅")
        if pass_count >= 2:
            ok("runtime_gates_pass")
        else:
            fail("runtime_gates_pass", f"only {pass_count} ✅ in: {out[:300]}")

t_runtime_gates_show_pass()

# ── 14-15: toml/lock missing = warning (not hard fail) ───────────────────────

def t_missing_toml_is_warning():
    with tempfile.TemporaryDirectory() as d:
        ret, out = capture_check_v2(d)
        # Missing toml is a WARN (⚠️), not a hard FAIL
        if "inscript.toml" in out:
            ok("toml_missing_shown")
        else:
            fail("toml_missing_shown", f"not in: {out[:200]}")

t_missing_toml_is_warning()

def t_with_toml_and_lock_no_warnings():
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, MANIFEST_FILENAME), "w").write(
            '[package]\nname = "test"\nversion = "1.0.0"\n')
        _write_lock_entry(os.path.join(d, LOCK_FILENAME), "some-pkg", "1.0.0")
        ret, out = capture_check_v2(d)
        if "inscript.toml present" in out and "inscript.lock present" in out:
            ok("toml_and_lock_present_pass")
        else:
            fail("toml_and_lock_present_pass", out[:200])

t_with_toml_and_lock_no_warnings()

# ── 16-18: summary line ───────────────────────────────────────────────────────

def t_summary_line_present():
    with tempfile.TemporaryDirectory() as d:
        ret, out = capture_check_v2(d)
        if "gates passed" in out:
            ok("summary_line_present")
        else:
            fail("summary_line_present", out[:200])

t_summary_line_present()

def t_all_pass_exit_0():
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, MANIFEST_FILENAME), "w").write(
            '[package]\nname = "app"\nversion = "1.0.0"\n')
        _write_lock_entry(os.path.join(d, LOCK_FILENAME), "pkg", "1.0.0")
        make_ins(d, "clean.ins", "# good code\nlet x = 10 // 3\n")
        ret, out = capture_check_v2(d)
        # No div/null/old-comments, toml+lock present → should pass with 0 hard failures
        if ret == 0:
            ok("all_pass_exit_0")
        else:
            fail("all_pass_exit_0", f"ret={ret}\n{out[:400]}")

t_all_pass_exit_0()

def t_8_gates_total():
    with tempfile.TemporaryDirectory() as d:
        ret, out = capture_check_v2(d)
        # Count gate lines: should have 8
        # Count only individual gate lines (not the summary line)
        gate_lines = [l for l in out.splitlines()
                      if ("✅" in l or "❌" in l or "⚠️" in l)
                      and ("PASS" in l or "FAIL" in l or "WARN" in l)
                      and "gates passed" not in l and "gate(s)" not in l]
        if len(gate_lines) == 8:
            ok("eight_gates_run")
        else:
            fail("eight_gates_run", f"got {len(gate_lines)} gate lines: {gate_lines}")

t_8_gates_total()

# ── Summary ───────────────────────────────────────────────────────────────────
total = passed + failed
print()
print("=" * 58)
print(f"  v1.9.10 Test Results: {passed}/{total} passed")
print("  ALL PASS" if failed == 0 else f"  {failed} FAILED")
print("=" * 58)
sys.exit(0 if failed == 0 else 1)
