"""Test Rust compiler: lex → parse → compile → execute (pure Rust pipeline)."""
import sys, os, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "target", "release"))

from inscript_parser import compile_and_run

tests = [
    ("push int", "42"),
    ("add", "1 + 2"),
    ("sub", "10 - 3"),
    ("mul", "4 * 5"),
    ("div", "20 / 4"),
    ("vars", "let x = 10; let y = 20; x + y"),
    ("if true", "if true { 1 } else { 2 }"),
    ("if false", "if false { 1 } else { 2 }"),
    ("comparison", "10 > 5"),
    ("equality", "10 == 10"),
    ("while loop", "let i = 0\nwhile i < 3 {\n  i = i + 1\n}\ni"),
    ("function call", "let x = 42\nprint(x)"),
    ("nested expr", "let x = (1 + 2) * 3\nx"),
    ("bool lit", "true"),
    ("nil lit", "nil"),
    ("float", "3.14"),
]

passed = 0
failed = 0

for name, src in tests:
    try:
        result = compile_and_run(src)
        print(f"  {name:20s}: {result}")
        passed += 1
    except Exception as e:
        print(f"  {name:20s}: FAIL - {e}")
        failed += 1

print(f"\n{passed} passed, {failed} failed")
