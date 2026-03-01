#!/usr/bin/env python3
# inscript.py  — InScript Language Entry Point
#
# Usage:
#   python inscript.py mygame.ins              # run a file
#   python inscript.py --repl                  # interactive REPL
#   python inscript.py --check mygame.ins      # type-check only (no run)
#   python inscript.py --ast mygame.ins        # print AST
#   python inscript.py --tokens mygame.ins     # print tokens
#   python inscript.py --version               # print version

import sys, os, argparse

# Make sure local modules are found regardless of cwd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer    import tokenize
from parser   import parse
from analyzer import analyze
from interpreter import Interpreter
from errors   import (InScriptError, LexerError, ParseError,
                       SemanticError, InScriptRuntimeError)

VERSION = "0.5.0"
LANG    = "InScript"


# ─────────────────────────────────────────────────────────────────────────────
# RUN A FILE
# ─────────────────────────────────────────────────────────────────────────────

def run_file(path: str, type_check: bool = True) -> int:
    """Load and execute an InScript source file. Returns exit code."""
    if not os.path.exists(path):
        print(f"[InScript] Error: file not found: '{path}'", file=sys.stderr)
        return 1
    if not path.endswith(".ins"):
        print(f"[InScript] Warning: expected .ins extension, got '{path}'", file=sys.stderr)

    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    return run_source(source, filename=path, type_check=type_check)


def run_source(source: str, filename: str = "<stdin>",
               type_check: bool = True) -> int:
    """Lex, parse, analyze, and interpret InScript source code."""
    # ── 1. Lex ────────────────────────────────────────────────────────────
    try:
        tokens = tokenize(source, filename)
    except LexerError as e:
        print(e, file=sys.stderr)
        return 1

    # ── 2. Parse ──────────────────────────────────────────────────────────
    try:
        program = parse(source, filename)
    except ParseError as e:
        print(e, file=sys.stderr)
        return 1

    # ── 3. Analyze (optional) ─────────────────────────────────────────────
    if type_check:
        try:
            analyze(program, source)
        except SemanticError as e:
            print(e, file=sys.stderr)
            return 1

    # ── 4. Interpret ──────────────────────────────────────────────────────
    try:
        interp = Interpreter(source.splitlines())
        interp.run(program)
        return 0
    except InScriptRuntimeError as e:
        print(e, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n[InScript] Interrupted.", file=sys.stderr)
        return 130


# ─────────────────────────────────────────────────────────────────────────────
# REPL
# ─────────────────────────────────────────────────────────────────────────────

REPL_BANNER = f"""
╔══════════════════════════════════════════════════════╗
║   InScript v{VERSION} — Interactive Shell                  ║
║   Type 'exit' or Ctrl+C to quit, 'help' for tips    ║
╚══════════════════════════════════════════════════════╝
"""

REPL_HELP = """
InScript REPL Tips:
  • Type any expression to evaluate it:   2 + 2
  • Declare variables:                    let x = 10
  • Define functions:                     fn add(a,b) { return a+b }
  • Import stdlib modules:                import "math"
  • Multiline input: end line with \\      let x = 1 + \\
  • .clear  — clear the current session
  • .vars   — list all defined variables
  • .exit   — quit
"""

def run_repl():
    """Interactive Read-Eval-Print Loop."""
    print(REPL_BANNER)
    interp   = Interpreter()
    history  = []
    buf      = []

    def show_result(val):
        if val is None: return
        from stdlib_values import (InScriptFunction, InScriptInstance,
                                    Vec2, Vec3, Color, Rect)
        from interpreter import _inscript_str
        print(f"  → {_inscript_str(val)}")

    while True:
        prompt = ">>> " if not buf else "... "
        try:
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\n[InScript] Goodbye!")
            break

        # REPL commands
        stripped = line.strip()
        if stripped in ("exit", ".exit", "quit"):
            print("[InScript] Goodbye!")
            break
        if stripped == "help":
            print(REPL_HELP); continue
        if stripped == ".clear":
            interp = Interpreter()
            buf = []
            print("  (session cleared)")
            continue
        if stripped == ".vars":
            for name, sym in sorted(interp._env._vars.items()):
                if not name.startswith("_"):
                    print(f"  {name} = {sym!r}")
            continue

        # Multiline continuation
        if line.endswith("\\"):
            buf.append(line[:-1])
            continue
        buf.append(line)
        source = "\n".join(buf)
        buf = []

        if not source.strip():
            continue

        # Try to eval
        try:
            prog = parse(source, "<repl>")
            history.append(source)

            # Run and show last expression value
            prev_count = len(interp._env._vars)
            interp.run(prog)

            # Show result of last expression statement
            from ast_nodes import ExprStmt
            if prog.body and isinstance(prog.body[-1], ExprStmt):
                val = interp.visit(prog.body[-1].expr)
                show_result(val)

        except (LexerError, ParseError, SemanticError, InScriptRuntimeError) as e:
            print(e)
        except Exception as e:
            print(f"[InScript Internal Error] {e}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="inscript",
        description=f"InScript {VERSION} — Game-focused programming language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python inscript.py mygame.ins          Run a game file
  python inscript.py --repl              Start interactive shell
  python inscript.py --check game.ins    Type-check without running
  python inscript.py --tokens game.ins   Print lexer tokens
  python inscript.py --ast game.ins      Print parsed AST
"""
    )
    parser.add_argument("file",     nargs="?", help=".ins source file to run")
    parser.add_argument("--repl",   action="store_true", help="Start interactive REPL")
    parser.add_argument("--check",  action="store_true", help="Type-check only, don't run")
    parser.add_argument("--tokens", action="store_true", help="Print lexer token stream")
    parser.add_argument("--ast",    action="store_true", help="Print parsed AST")
    parser.add_argument("--no-typecheck", action="store_true",
                        help="Skip semantic analysis (faster, less safe)")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    args = parser.parse_args()

    if args.version:
        print(f"InScript {VERSION}")
        return 0

    if args.repl:
        run_repl()
        return 0

    if not args.file:
        parser.print_help()
        return 0

    # Load source
    if not os.path.exists(args.file):
        print(f"[InScript] Error: file not found: '{args.file}'", file=sys.stderr)
        return 1

    with open(args.file, "r", encoding="utf-8") as f:
        source = f.read()

    # --tokens
    if args.tokens:
        try:
            tokens = tokenize(source, args.file)
            for tok in tokens:
                print(f"  {tok.type.name:15s} {tok.value!r:20s} L{tok.line}:C{tok.col}")
        except LexerError as e:
            print(e, file=sys.stderr); return 1
        return 0

    # --ast
    if args.ast:
        try:
            prog = parse(source, args.file)
            def _dump(node, indent=0):
                prefix = "  " * indent
                name = type(node).__name__
                if hasattr(node, "__dataclass_fields__"):
                    fields = {k: getattr(node, k) for k in node.__dataclass_fields__
                              if k not in ("line","col")}
                    simple = {k: v for k, v in fields.items()
                              if not hasattr(v, "__dataclass_fields__")
                              and not isinstance(v, list)}
                    print(f"{prefix}{name}({', '.join(f'{k}={v!r}' for k,v in simple.items())})")
                    for k, v in fields.items():
                        if isinstance(v, list):
                            if v:
                                print(f"{prefix}  {k}:")
                                for item in v:
                                    if hasattr(item, "__dataclass_fields__"):
                                        _dump(item, indent+2)
                        elif hasattr(v, "__dataclass_fields__"):
                            print(f"{prefix}  {k}:")
                            _dump(v, indent+2)
                else:
                    print(f"{prefix}{node!r}")
            _dump(prog)
        except (LexerError, ParseError) as e:
            print(e, file=sys.stderr); return 1
        return 0

    # --check
    if args.check:
        try:
            prog = parse(source, args.file)
            analyze(prog, source)
            print(f"✅ {args.file} — type check passed")
        except (LexerError, ParseError, SemanticError) as e:
            print(e, file=sys.stderr); return 1
        return 0

    # Normal run
    type_check = not args.no_typecheck
    return run_file(args.file, type_check=type_check)


if __name__ == "__main__":
    sys.exit(main())
