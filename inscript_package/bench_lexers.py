"""Benchmark Python lexer vs Rust lexer."""
import sys, os, time, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "target", "release"))

from lexer import Lexer as PyLexer
from inscript_parser import lex as rust_lex

examples = sorted(glob.glob(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "examples", "*.ins"
)))

# Warmup
PyLexer("let x = 5").tokenize()
_ = rust_lex("let x = 5")

ITERATIONS = 100

print(f"{'File':30s} {'Python Lex':>12s} {'Rust Lex':>12s} {'Speedup':>10s}")
print("-" * 66)

total_py = 0.0
total_rust = 0.0
total_py_chars = 0

for fpath in examples:
    fname = os.path.basename(fpath)
    with open(fpath, encoding="utf-8") as f:
        source = f.read()

    char_count = len(source)

    # Python lexer benchmark
    py_start = time.perf_counter()
    for _ in range(ITERATIONS):
        PyLexer(source).tokenize()
    py_time = (time.perf_counter() - py_start) / ITERATIONS

    # Rust lexer benchmark
    rust_start = time.perf_counter()
    for _ in range(ITERATIONS):
        rust_lex(source)
    rust_time = (time.perf_counter() - rust_start) / ITERATIONS

    speedup = py_time / rust_time if rust_time > 0 else 0

    print(f"{fname:30s} {py_time*1000:9.3f}ms {rust_time*1000:9.3f}ms {speedup:7.2f}x")

    total_py += py_time
    total_rust += rust_time
    total_py_chars += char_count

print("-" * 66)
total_speedup = total_py / total_rust if total_rust > 0 else 0
print(f"{'TOTAL':30s} {total_py*1000:9.3f}ms {total_rust*1000:9.3f}ms {total_speedup:7.2f}x")
