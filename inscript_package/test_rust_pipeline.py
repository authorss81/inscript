"""Test Rust lexer + Rust parser pipeline end-to-end."""
import sys, os, glob, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "target", "release"))

from inscript_parser import lex as rust_lex, parse_tokens as rust_parse

examples = sorted(glob.glob(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "examples", "*.ins"
)))

if not examples:
    print("No example files found!")
    sys.exit(1)

# Warmup
_ = rust_lex("let x = 5")

passed = 0
failed = 0

for fpath in examples:
    fname = os.path.basename(fpath)
    with open(fpath, encoding="utf-8") as f:
        source = f.read()

    # 1) Rust lexer
    start = time.perf_counter()
    tokens = rust_lex(source)
    lex_time = time.perf_counter() - start
    print(f"  Lex: {lex_time*1000:.2f}ms ({len(tokens)} tokens)")

    # 2) Rust parser
    start = time.perf_counter()
    try:
        result = rust_parse(tokens)
        parse_time = time.perf_counter() - start
        print(f"  Parse: {parse_time*1000:.2f}ms")
        print(f"  PASS: {fname}")
        passed += 1
    except Exception as e:
        parse_time = time.perf_counter() - start
        print(f"  FAIL: {fname}: {e}")
        failed += 1

    print()

print(f"=== Results: {passed} passed, {failed} failed ===")
sys.exit(0 if failed == 0 else 1)
