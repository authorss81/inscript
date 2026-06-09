"""Test f-string interpolation."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "target/release")
from inscript_parser import compile_and_run

tests = [
    ("f-string prefix", 'let name = "World"\nprint(f"Hello {name}")'),
    ("dollar-string", 'let a = 1\nlet b = 2\nprint($"a={a} b={b} sum={a + b}")'),
    ("expr in fstring", 'print($"2 + 2 = {2 + 2}")'),
    ("plain string no interp", 'print("Hello {name}")'),
    ("nested braces", 'print($"{{escaped}}")'),
]

for name, src in tests:
    print(f"--- {name} ---")
    print(repr(compile_and_run(src)))
