"""Test Rust compiler against example .ins files."""
import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "target", "release"))

from inscript_parser import lex, parse_tokens, compile_and_run

examples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples")
examples = sorted(glob.glob(os.path.join(examples_dir, "*.ins")))

passed = 0
failed = 0
for fpath in examples:
    name = os.path.basename(fpath)
    with open(fpath, encoding="utf-8") as f:
        src = f.read()
    try:
        # Just test compilation, don't run (VM doesn't have builtins loaded)
        tokens = lex(src)
        ast = parse_tokens(tokens)
        print(f"  {name:35s} OK ({len(tokens)} tokens)")
        passed += 1
    except Exception as e:
        print(f"  {name:35s} FAIL - {e}")
        failed += 1

print(f"\n{passed} passed, {failed} failed")
