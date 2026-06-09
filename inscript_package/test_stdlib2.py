"""Test extended stdlib."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "target/release")
from inscript_parser import compile_and_run

tests = [
    ("sqrt(144)", "print(sqrt(144))"),
    ("abs(-42)", "print(abs(-42))"),
    ("abs(-3.14)", "print(abs(-3.14))"),
    ("min(10, 20)", "print(min(10, 20))"),
    ("max(10, 20)", "print(max(10, 20))"),
    ("pow(2, 10)", "print(pow(2, 10))"),
    ('min("abc", "xyz")', 'print(min("abc", "xyz"))'),
]

for name, src in tests:
    print(f"--- {name} ---")
    print(compile_and_run(src))
