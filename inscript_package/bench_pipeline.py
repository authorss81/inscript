"""Benchmark old (Python lex + Rust parse) vs new (Rust lex + Rust parse)."""
import sys, os, time, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "target", "release"))

from lexer import Lexer as PyLexer
from inscript_parser import lex as rust_lex, parse_tokens as rust_parse

examples = sorted(glob.glob(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "examples", "*.ins"
)))

# Warmup
_ = rust_lex("let x = 5")
PyLexer("let x = 5").tokenize()

ITERATIONS = 50

print(f"{'File':30s} {'Old Pipeline':>14s} {'New Pipeline':>14s} {'Speedup':>10s}")
print("-" * 70)

total_old = 0.0
total_new = 0.0

for fpath in examples:
    fname = os.path.basename(fpath)
    with open(fpath, encoding="utf-8") as f:
        source = f.read()

    # Old pipeline: Python lex → bridge → Rust parse
    old_start = time.perf_counter()
    for _ in range(ITERATIONS):
        tokens = PyLexer(source).tokenize()
        tok_list = []
        for t in tokens:
            tok_list.append({
                "token_type": t.type.name,
                "value": str(t.value) if t.value is not None else "",
                "line": t.line,
                "column": t.col,
            })
        rust_parse(tok_list)
    old_time = (time.perf_counter() - old_start) / ITERATIONS

    # New pipeline: Rust lex → Rust parse
    new_start = time.perf_counter()
    for _ in range(ITERATIONS):
        tokens = rust_lex(source)
        rust_parse(tokens)
    new_time = (time.perf_counter() - new_start) / ITERATIONS

    speedup = old_time / new_time if new_time > 0 else 0
    print(f"{fname:30s} {old_time*1000:10.3f}ms {new_time*1000:10.3f}ms {speedup:7.2f}x")

    total_old += old_time
    total_new += new_time

print("-" * 70)
print(f"{'TOTAL':30s} {total_old*1000:10.3f}ms {total_new*1000:10.3f}ms {total_old/total_new:7.2f}x")
