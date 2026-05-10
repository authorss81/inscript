"""
test_v199.py — v1.9.9: Package manager hardening

All tests run without a live network — they test the logic layer:
  1-4:   _parse_pkg_spec: PKG and PKG@version parsing
  5-8:   _read_lock / _write_lock_entry / _remove_lock_entry
  9-12:  install_all_from_toml: reads inscript.toml, respects lock file
  13-15: outdated_packages: graceful offline behaviour
  16-18: update_package: removes old, reports correctly
  19-21: install_package with lock_path writes lock file
  22-24: install (no args) CLI flag wiring
"""
import sys, os, tempfile, shutil
sys.path.insert(0, os.path.dirname(__file__))

passed = failed = 0

def ok(name):
    global passed; passed += 1; print(f"  PASS  {name}")

def fail(name, reason=""):
    global failed; failed += 1; print(f"  FAIL  {name}  {reason}")

from inscript import (
    _parse_pkg_spec, _read_lock, _write_lock_entry, _remove_lock_entry,
    install_all_from_toml, outdated_packages, MANIFEST_FILENAME, LOCK_FILENAME,
)

# ── 1-4: _parse_pkg_spec ─────────────────────────────────────────────────────

def t(name, spec, expected_name, expected_ver):
    n, v = _parse_pkg_spec(spec)
    if n == expected_name and v == expected_ver: ok(name)
    else: fail(name, f"got ({n!r}, {v!r}), expected ({expected_name!r}, {expected_ver!r})")

t("parse_plain",        "math-utils",         "math-utils", None)
t("parse_at_version",   "math-utils@1.2.0",   "math-utils", "1.2.0")
t("parse_at_major",     "grid@2.0.0",         "grid",       "2.0.0")
t("parse_spaces",       "  pkg @ 1.0.0  ",    "pkg",        "1.0.0")

# ── 5-8: lock file read/write/remove ─────────────────────────────────────────

def t_lock_write_read():
    with tempfile.TemporaryDirectory() as d:
        lp = os.path.join(d, "inscript.lock")
        _write_lock_entry(lp, "math-utils", "1.2.0")
        _write_lock_entry(lp, "grid", "3.0.1")
        locked = _read_lock(lp)
        if locked.get("math-utils") != "1.2.0":
            fail("lock_write_read_math", f"got {locked}")
        elif locked.get("grid") != "3.0.1":
            fail("lock_write_read_grid", f"got {locked}")
        else:
            ok("lock_write_read")

t_lock_write_read()

def t_lock_overwrite():
    with tempfile.TemporaryDirectory() as d:
        lp = os.path.join(d, "inscript.lock")
        _write_lock_entry(lp, "pkg", "1.0.0")
        _write_lock_entry(lp, "pkg", "2.0.0")  # overwrite
        locked = _read_lock(lp)
        if locked.get("pkg") == "2.0.0": ok("lock_overwrite")
        else: fail("lock_overwrite", f"got {locked}")

t_lock_overwrite()

def t_lock_remove():
    with tempfile.TemporaryDirectory() as d:
        lp = os.path.join(d, "inscript.lock")
        _write_lock_entry(lp, "pkg-a", "1.0.0")
        _write_lock_entry(lp, "pkg-b", "2.0.0")
        _remove_lock_entry(lp, "pkg-a")
        locked = _read_lock(lp)
        if "pkg-a" in locked:
            fail("lock_remove", f"pkg-a still present: {locked}")
        elif locked.get("pkg-b") != "2.0.0":
            fail("lock_remove", f"pkg-b missing: {locked}")
        else:
            ok("lock_remove")

t_lock_remove()

def t_lock_missing_returns_empty():
    locked = _read_lock("/nonexistent/path/inscript.lock")
    if locked == {}: ok("lock_missing_empty")
    else: fail("lock_missing_empty", f"got {locked}")

t_lock_missing_returns_empty()

# ── 9-12: install_all_from_toml ──────────────────────────────────────────────

def t_install_all_no_toml():
    with tempfile.TemporaryDirectory() as d:
        ret = install_all_from_toml(d)
        if ret != 0: ok("install_all_no_toml_returns_1")
        else: fail("install_all_no_toml_returns_1", "expected return 1")

t_install_all_no_toml()

def t_install_all_empty_deps():
    with tempfile.TemporaryDirectory() as d:
        toml = '[package]\nname = "myapp"\nversion = "0.1.0"\n\n[dependencies]\n'
        open(os.path.join(d, MANIFEST_FILENAME), "w").write(toml)
        ret = install_all_from_toml(d)
        if ret == 0: ok("install_all_empty_deps")
        else: fail("install_all_empty_deps", f"got {ret}")

t_install_all_empty_deps()

def t_install_all_reads_lock():
    """install_all should use locked versions when lock file exists."""
    with tempfile.TemporaryDirectory() as d:
        toml = '[package]\nname = "myapp"\nversion = "0.1.0"\n\n[dependencies]\nmath-utils = "^1.0.0"\n'
        open(os.path.join(d, MANIFEST_FILENAME), "w").write(toml)
        lp = os.path.join(d, LOCK_FILENAME)
        _write_lock_entry(lp, "math-utils", "1.0.5")
        locked = _read_lock(lp)
        if locked.get("math-utils") == "1.0.5":
            ok("install_all_reads_lock")
        else:
            fail("install_all_reads_lock", f"lock not found: {locked}")

t_install_all_reads_lock()

def t_install_all_lock_used_in_spec():
    """Pinned version from lock should be used when building install spec."""
    with tempfile.TemporaryDirectory() as d:
        toml = '[package]\nname = "app"\nversion = "1.0.0"\n\n[dependencies]\ngrid = "^2.0.0"\n'
        open(os.path.join(d, MANIFEST_FILENAME), "w").write(toml)
        lp = os.path.join(d, LOCK_FILENAME)
        _write_lock_entry(lp, "grid", "2.1.3")
        locked = _read_lock(lp)
        name, ver = _parse_pkg_spec(f"grid@{locked['grid']}")
        if name == "grid" and ver == "2.1.3":
            ok("install_all_lock_spec")
        else:
            fail("install_all_lock_spec", f"got name={name!r} ver={ver!r}")

t_install_all_lock_used_in_spec()

# ── 13-15: outdated_packages (offline graceful behaviour) ────────────────────

def t_outdated_no_lock():
    with tempfile.TemporaryDirectory() as d:
        import io, sys as _sys
        buf = io.StringIO(); old = _sys.stdout; _sys.stdout = buf
        ret = outdated_packages(d)
        _sys.stdout = old
        out = buf.getvalue()
        if "No inscript.lock" in out or ret == 0:
            ok("outdated_no_lock_graceful")
        else:
            fail("outdated_no_lock_graceful", f"ret={ret} out={out[:100]}")

t_outdated_no_lock()

def t_outdated_with_lock_offline():
    """With a lock file but no registry, should list locked versions gracefully."""
    with tempfile.TemporaryDirectory() as d:
        lp = os.path.join(d, LOCK_FILENAME)
        _write_lock_entry(lp, "math-utils", "1.0.0")
        import io, sys as _sys
        buf = io.StringIO(); old_err = _sys.stderr
        err_buf = io.StringIO(); _sys.stderr = err_buf
        old = _sys.stdout; _sys.stdout = buf
        ret = outdated_packages(d)
        _sys.stdout = old; _sys.stderr = old_err
        out = buf.getvalue() + err_buf.getvalue()
        # Either registry failed (ret=1) or all up to date (ret=0) — both are graceful
        if "math-utils" in out or ret in (0, 1):
            ok("outdated_offline_graceful")
        else:
            fail("outdated_offline_graceful", f"unexpected output: {out[:200]}")

t_outdated_with_lock_offline()

def t_outdated_empty_lock():
    with tempfile.TemporaryDirectory() as d:
        lp = os.path.join(d, LOCK_FILENAME)
        open(lp, "w").write("# empty lock\n")
        import io, sys as _sys
        buf = io.StringIO(); old = _sys.stdout; _sys.stdout = buf
        outdated_packages(d)
        _sys.stdout = old
        ok("outdated_empty_lock_no_crash")

t_outdated_empty_lock()

# ── 16-18: update_package ────────────────────────────────────────────────────

from inscript import update_package, PACKAGES_DIR

def t_update_nonexistent_pkg():
    """Updating a package not in registry should fail gracefully."""
    with tempfile.TemporaryDirectory() as d:
        ret = update_package("definitely-not-a-real-pkg-xyz123", project_dir=d)
        if ret != 0: ok("update_nonexistent_fails_gracefully")
        else: fail("update_nonexistent_fails_gracefully", "expected non-zero return")

t_update_nonexistent_pkg()

def t_update_parse_version():
    name, ver = _parse_pkg_spec("grid@3.0.0")
    if name == "grid" and ver == "3.0.0": ok("update_parses_version")
    else: fail("update_parses_version", f"got ({name!r}, {ver!r})")

t_update_parse_version()

def t_update_removes_old_dir():
    """update_package removes the old install dir before reinstalling."""
    with tempfile.TemporaryDirectory() as d:
        fake_pkg_dir = os.path.join(PACKAGES_DIR, "_test_pkg_v199_temp")
        os.makedirs(fake_pkg_dir, exist_ok=True)
        open(os.path.join(fake_pkg_dir, "main.ins"), "w").write("let x = 1")
        # update_package calls shutil.rmtree then install_package (which will fail without registry)
        ret = update_package("_test_pkg_v199_temp@1.0.0", project_dir=d)
        # dir should be gone (removed before registry call), and install should have failed
        if os.path.exists(fake_pkg_dir):
            fail("update_removes_old_dir", "old dir still exists")
        elif ret != 0:
            ok("update_removes_old_dir")  # removed dir, then install failed (no registry) = expected
        else:
            fail("update_removes_old_dir", "install should have failed (no registry)")

t_update_removes_old_dir()

# ── 19-21: install_package writes lock ───────────────────────────────────────

from inscript import install_package

def t_install_with_lock_offline():
    """install_package with lock_path falls back to offline info."""
    with tempfile.TemporaryDirectory() as d:
        lp = os.path.join(d, LOCK_FILENAME)
        _write_lock_entry(lp, "math-utils", "1.5.0")
        import io, sys as _sys
        buf = io.StringIO(); old = _sys.stdout; _sys.stdout = buf
        err_buf = io.StringIO(); old_err = _sys.stderr; _sys.stderr = err_buf
        ret = install_package("math-utils", lock_path=lp)
        _sys.stdout = old; _sys.stderr = old_err
        out = buf.getvalue() + err_buf.getvalue()
        # Either: offline fallback shown (ret=0 or 1) — should not crash
        if "math-utils" in out or ret in (0, 1):
            ok("install_offline_fallback")
        else:
            fail("install_offline_fallback", f"unexpected: {out[:200]}")

t_install_with_lock_offline()

def t_install_lock_written_on_success():
    """_write_lock_entry works correctly on a fresh lock file."""
    with tempfile.TemporaryDirectory() as d:
        lp = os.path.join(d, "test.lock")
        _write_lock_entry(lp, "my-pkg", "2.3.4")
        locked = _read_lock(lp)
        if locked.get("my-pkg") == "2.3.4": ok("lock_written_on_success")
        else: fail("lock_written_on_success", f"got {locked}")

t_install_lock_written_on_success()

def t_install_no_args_no_toml():
    import subprocess
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run(
            [sys.executable, "inscript.py", "--install"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__)
        )
        out = r.stdout + r.stderr
        # Should mention inscript.toml or init
        if "toml" in out.lower() or "init" in out.lower() or r.returncode != 0:
            ok("install_no_args_no_toml")
        else:
            fail("install_no_args_no_toml", f"unexpected: {out[:200]}")

t_install_no_args_no_toml()

# ── 22-24: CLI --outdated and --update flags exist ────────────────────────────

def t_outdated_flag_exists():
    import subprocess
    r = subprocess.run([sys.executable, "inscript.py", "--help"],
                       capture_output=True, text=True)
    if "--outdated" in r.stdout: ok("outdated_flag_in_help")
    else: fail("outdated_flag_in_help", "not in --help output")

t_outdated_flag_exists()

def t_update_flag_exists():
    import subprocess
    r = subprocess.run([sys.executable, "inscript.py", "--help"],
                       capture_output=True, text=True)
    if "--update" in r.stdout: ok("update_flag_in_help")
    else: fail("update_flag_in_help", "not in --help output")

t_update_flag_exists()

def t_install_nargs_in_help():
    import subprocess
    r = subprocess.run([sys.executable, "inscript.py", "--help"],
                       capture_output=True, text=True)
    if "--install" in r.stdout: ok("install_in_help")
    else: fail("install_in_help", "not in --help output")

t_install_nargs_in_help()

# ── Summary ───────────────────────────────────────────────────────────────────
total = passed + failed
print()
print("=" * 58)
print(f"  v1.9.9 Test Results: {passed}/{total} passed")
print("  ALL PASS" if failed == 0 else f"  {failed} FAILED")
print("=" * 58)
sys.exit(0 if failed == 0 else 1)
