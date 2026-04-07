# -*- coding: utf-8 -*-
"""
inscript_test.py — InScript Test Runner v1.0.20
=================================================
Discovers and runs test_*.ins files (or specific files).

Test syntax in .ins files:
    test "name" {
        assert(1+1 == 2, "addition works")
        assert(len([1,2,3]) == 3)
    }

    // Or just bare asserts (counted as anonymous test)
    assert("hello".upper() == "HELLO")

Usage:
    python inscript_test.py                  # discover test_*.ins
    python inscript_test.py test_math.ins    # specific file
    python inscript_test.py --verbose        # show all test names
    python inscript_test.py --fail-fast      # stop on first failure

Integrated in CLI:
    inscript --test                          # run all tests
    inscript --test test_math.ins           # specific file
"""
from __future__ import annotations
import sys, os, time, argparse, re as _re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# ── ANSI helpers ─────────────────────────────────────────────────────────────
def _c(code, s):
    return f"\033[{code}m{s}\033[0m" if sys.stdout.isatty() else s

GREEN  = lambda s: _c("32", s)
RED    = lambda s: _c("31", s)
YELLOW = lambda s: _c("33", s)
CYAN   = lambda s: _c("36", s)
BOLD   = lambda s: _c("1",  s)
DIM    = lambda s: _c("2",  s)


class TestResult:
    def __init__(self, name, passed, error=None, ms=0.0):
        self.name   = name
        self.passed = passed
        self.error  = error
        self.ms     = ms


def _run_inscript(source: str, path: str = "<test>") -> tuple[str, str]:
    """Run InScript source, return (stdout, error_message)."""
    import io as _io
    old_stdout = sys.stdout
    sys.stdout = _io.StringIO()
    err_msg = ""
    try:
        # Use the EnhancedREPL to evaluate multi-statement source
        from repl import EnhancedREPL
        r = EnhancedREPL()
        # Split into statements and evaluate
        _, err, _ = r._eval(source)
        if err:
            err_msg = str(err)
    except Exception as e:
        err_msg = str(e)
    finally:
        out = sys.stdout.getvalue()
        sys.stdout = old_stdout
    return out, err_msg


def _extract_tests(source: str) -> list[dict]:
    """
    Extract named test blocks from source.
    Returns list of {"name": str, "body": str, "line": int}
    Also extracts anonymous top-level asserts as a single test.
    """
    tests = []
    # Match: test "name" { ... } blocks (possibly multiline)
    pattern = _re.compile(
        r'test\s+"([^"]+)"\s*\{(.*?)\}',
        _re.DOTALL
    )
    for m in pattern.finditer(source):
        tests.append({
            "name": m.group(1),
            "body": m.group(2).strip(),
            "line": source[:m.start()].count('\n') + 1
        })
    # Remaining source without test blocks = anonymous asserts
    anon = pattern.sub('', source).strip()
    if anon:
        tests.append({
            "name": "(top-level)",
            "body": anon,
            "line": 1
        })
    return tests


def run_file(path: Path, verbose: bool = False, fail_fast: bool = False) -> list[TestResult]:
    """Run all tests in a single .ins file."""
    results = []
    try:
        source = path.read_text(encoding='utf-8')
    except Exception as e:
        return [TestResult(str(path), False, f"Cannot read file: {e}")]

    tests = _extract_tests(source)

    if not tests:
        # File has no tests / no asserts — just run it and see if it errors
        t0 = time.perf_counter()
        _, err = _run_inscript(source, str(path))
        ms = (time.perf_counter() - t0) * 1000
        passed = not err
        results.append(TestResult("(run)", passed, err if err else None, ms))
        return results

    for test in tests:
        name = test["name"]
        body = test["body"]
        t0   = time.perf_counter()
        _, err = _run_inscript(body, str(path))
        ms   = (time.perf_counter() - t0) * 1000

        if err:
            # Clean up the error message
            clean_err = _re.sub(r'\033\[[0-9;]*m', '', err)  # strip ANSI
            clean_err = _re.sub(r'See: https://.*', '', clean_err).strip()
            results.append(TestResult(name, False, clean_err, ms))
            if fail_fast:
                return results
        else:
            results.append(TestResult(name, True, None, ms))

    return results


def run_files(files: list[Path], verbose: bool = False,
              fail_fast: bool = False) -> tuple[int, int, float]:
    """
    Run multiple test files.
    Returns (passed_count, failed_count, total_ms).
    """
    total_pass = 0
    total_fail = 0
    total_ms   = 0.0
    failures   = []

    for f in files:
        rel = f.relative_to(Path.cwd()) if f.is_relative_to(Path.cwd()) else f
        file_pass = 0
        file_fail = 0
        t0 = time.perf_counter()
        results = run_file(f, verbose=verbose, fail_fast=fail_fast)
        file_ms = (time.perf_counter() - t0) * 1000

        for r in results:
            if r.passed:
                file_pass += 1
                if verbose:
                    print(f"  {GREEN('✓')} {DIM(r.name)}  {DIM(f'{r.ms:.0f}ms')}")
            else:
                file_fail += 1
                failures.append((rel, r))

        total_pass += file_pass
        total_fail += file_fail
        total_ms   += file_ms

        # Per-file summary line
        status = GREEN("PASS") if file_fail == 0 else RED("FAIL")
        count  = f"{file_pass}/{file_pass+file_fail}"
        print(f"  {status}  {rel}  {DIM(count)}  {DIM(f'{file_ms:.0f}ms')}")

        if fail_fast and file_fail > 0:
            break

    return total_pass, total_fail, total_ms, failures


def main(argv=None):
    p = argparse.ArgumentParser(
        prog='inscript test',
        description='InScript test runner — discovers and runs test_*.ins files'
    )
    p.add_argument('files', nargs='*',
                   help='Specific .ins files to run (default: discover test_*.ins)')
    p.add_argument('--verbose', '-v', action='store_true',
                   help='Show each test name')
    p.add_argument('--fail-fast', '-x', action='store_true',
                   help='Stop on first failure')
    p.add_argument('--no-recurse', action='store_true',
                   help='Do not recurse into subdirectories')
    args = p.parse_args(argv)

    # Discover test files
    if args.files:
        files = [Path(f) for f in args.files if Path(f).exists()]
        if not files:
            print(RED("No test files found.")); return 1
    else:
        if args.no_recurse:
            files = sorted(Path('.').glob('test_*.ins'))
        else:
            files = sorted(Path('.').glob('**/*.ins'))
            files = [f for f in files
                     if f.name.startswith('test_') and '.git' not in str(f)]
        if not files:
            print(DIM("No test_*.ins files found. Create a test_something.ins to start."))
            return 0

    # Header
    print()
    print(f"{BOLD('InScript Test Runner')}  {DIM(f'— {len(files)} file(s)')}")
    print(DIM("─" * 50))

    t_start = time.perf_counter()
    passed, failed, total_ms, failures = run_files(
        files, verbose=args.verbose, fail_fast=args.fail_fast
    )
    total_elapsed = (time.perf_counter() - t_start) * 1000

    print(DIM("─" * 50))

    # Failure details
    if failures:
        print()
        print(BOLD(RED("Failures:")))
        for (file_path, result) in failures:
            print(f"\n  {RED('✗')} {BOLD(result.name)}  {DIM(str(file_path))}")
            if result.error:
                for line in result.error.splitlines()[:6]:
                    print(f"    {DIM(line)}")

    # Summary
    total = passed + failed
    print()
    if failed == 0:
        print(f"  {GREEN('✅')} {BOLD(GREEN(f'{passed}/{total} tests passed'))}  "
              f"{DIM(f'{total_elapsed:.0f}ms')}")
    else:
        print(f"  {RED('❌')} {BOLD(RED(f'{failed} failed'))}, "
              f"{GREEN(f'{passed} passed')}  {DIM(f'{total_elapsed:.0f}ms')}")
    print()

    return 1 if failed > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
