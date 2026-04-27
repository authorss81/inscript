#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# inscript.py  — InScript Language Entry Point
#
# Usage:
#   python inscript.py mygame.ins              # run a file
#   python inscript.py --repl                  # interactive REPL
#   python inscript.py --check mygame.ins      # type-check only (no run)
#   python inscript.py --ast mygame.ins        # print AST
#   python inscript.py --tokens mygame.ins     # print tokens
#   python inscript.py --version               # print version

import os as _os_env; _os_env.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import sys, os, argparse

# Make sure local modules are found regardless of cwd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer    import tokenize
from parser   import parse
from analyzer import analyze
from interpreter import Interpreter
from errors   import (InScriptError, LexerError, ParseError,
                       SemanticError, InScriptRuntimeError,
                       MultiError, InScriptWarning)

VERSION = "1.4.0"
LANG    = "InScript"
PACKAGES_DIR = os.path.join(os.path.expanduser("~"), ".inscript", "packages")
REGISTRY_URL = "https://raw.githubusercontent.com/authorss81/inscript-packages/main/registry.json"


# ─────────────────────────────────────────────────────────────────────────────
# RUN A FILE
# ─────────────────────────────────────────────────────────────────────────────

def install_package(pkg_name: str) -> int:
    """Download and install an InScript package to ~/.inscript/packages/"""
    import urllib.request, json as _json, zipfile, io

    os.makedirs(PACKAGES_DIR, exist_ok=True)
    pkg_dir = os.path.join(PACKAGES_DIR, pkg_name)

    if os.path.exists(pkg_dir):
        print(f"[InScript] Package '{pkg_name}' is already installed at {pkg_dir}")
        return 0

    print(f"[InScript] Fetching registry...")
    try:
        with urllib.request.urlopen(REGISTRY_URL, timeout=10) as resp:
            registry = _json.loads(resp.read().decode())
    except Exception as e:
        print(f"[InScript] Could not reach package registry: {e}", file=sys.stderr)
        print(f"[InScript] Tip: you can also install manually by placing .ins files in {PACKAGES_DIR}/",
              file=sys.stderr)
        return 1

    if pkg_name not in registry:
        available = list(registry.keys())
        print(f"[InScript] Package '{pkg_name}' not found in registry.", file=sys.stderr)
        print(f"[InScript] Available packages: {available}", file=sys.stderr)
        return 1

    pkg_info = registry[pkg_name]
    zip_url  = pkg_info.get("url")
    version  = pkg_info.get("version", "?")

    print(f"[InScript] Installing {pkg_name}@{version}...")
    try:
        with urllib.request.urlopen(zip_url, timeout=30) as resp:
            data = resp.read()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(PACKAGES_DIR)
        print(f"[InScript] ✅ {pkg_name}@{version} installed to {pkg_dir}")
        return 0
    except Exception as e:
        print(f"[InScript] Install failed: {e}", file=sys.stderr)
        return 1


def list_packages() -> int:
    """List installed packages."""
    if not os.path.exists(PACKAGES_DIR):
        print("[InScript] No packages installed yet.")
        print(f"[InScript] Install packages with: inscript install <name>")
        return 0
    pkgs = [d for d in os.listdir(PACKAGES_DIR)
            if os.path.isdir(os.path.join(PACKAGES_DIR, d))]
    if not pkgs:
        print("[InScript] No packages installed yet.")
        print(f"[InScript] Try: inscript install math-utils")
    else:
        print(f"[InScript] Installed packages ({len(pkgs)}):")
        for p in sorted(pkgs):
            pkg_json = os.path.join(PACKAGES_DIR, p, "package.json")
            version = ""
            if os.path.exists(pkg_json):
                import json as _j
                try:
                    info = _j.loads(open(pkg_json).read())
                    version = f"@{info.get('version','?')}"
                except Exception:
                    pass
            print(f"  • {p}{version}")
    return 0


def remove_package(pkg_name: str) -> int:
    """Uninstall an InScript package."""
    import shutil
    pkg_dir = os.path.join(PACKAGES_DIR, pkg_name)
    if not os.path.exists(pkg_dir):
        print(f"[InScript] Package '{pkg_name}' is not installed.", file=sys.stderr)
        return 1
    shutil.rmtree(pkg_dir)
    print(f"[InScript] ✅ Removed {pkg_name}")
    return 0


def search_packages(query: str) -> int:
    """Search the registry for packages matching a query."""
    import urllib.request, json as _json
    print(f"[InScript] Searching registry for '{query}'...")
    try:
        with urllib.request.urlopen(REGISTRY_URL, timeout=10) as resp:
            registry = _json.loads(resp.read().decode())
    except Exception as e:
        print(f"[InScript] Could not reach registry: {e}", file=sys.stderr)
        return 1
    query_lower = query.lower()
    matches = [
        (name, info) for name, info in registry.items()
        if query_lower in name.lower()
        or query_lower in info.get("description","").lower()
        or query_lower in " ".join(info.get("tags",[]))
    ]
    if not matches:
        print(f"[InScript] No packages found matching '{query}'.")
    else:
        print(f"[InScript] Found {len(matches)} package(s):")
        for name, info in sorted(matches):
            desc = info.get("description", "")
            ver  = info.get("version", "?")
            print(f"  • {name}@{ver} — {desc}")
    return 0


def info_package(pkg_name: str) -> int:
    """Show information about a package."""
    import urllib.request, json as _json
    try:
        with urllib.request.urlopen(REGISTRY_URL, timeout=10) as resp:
            registry = _json.loads(resp.read().decode())
    except Exception as e:
        print(f"[InScript] Could not reach registry: {e}", file=sys.stderr)
        return 1
    if pkg_name not in registry:
        print(f"[InScript] Package '{pkg_name}' not found.", file=sys.stderr)
        return 1
    info = registry[pkg_name]
    installed = os.path.exists(os.path.join(PACKAGES_DIR, pkg_name))
    print(f"  Name:        {pkg_name}")
    print(f"  Version:     {info.get('version', '?')}")
    print(f"  Description: {info.get('description', '')}")
    print(f"  Tags:        {', '.join(info.get('tags', []))}")
    print(f"  Repo:        {info.get('repo', '')}")
    print(f"  Installed:   {'yes' if installed else 'no'}")
    return 0


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


def _print_inscript_profile(pr, filename: str = "<script>"):
    """v1.3.0: Print a human-readable InScript-level profile from a cProfile result."""
    import pstats, io as _io
    s = _io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('tottime')
    ps.print_stats()
    raw = s.getvalue()

    # Extract lines that reference interpreter visit_ / _call_function
    rows = []
    for line in raw.split('\n'):
        if 'visit_' in line or '_call_function' in line or 'visit_BinaryExpr' in line:
            parts = line.split()
            if len(parts) >= 6:
                try:
                    ncalls  = parts[0].split('/')[0]
                    tottime = float(parts[1])
                    name    = parts[-1]
                    # prettify: visit_CallExpr → CallExpr
                    label = name.replace('visit_', '').replace('_call_function', 'fn_dispatch')
                    rows.append((tottime, int(ncalls), label))
                except (ValueError, IndexError):
                    pass

    if not rows:
        print("[InScript --profile] No hotspot data found.", file=sys.stderr)
        return

    rows.sort(reverse=True)
    total_time = sum(t for t, _, _ in rows)
    print(f"\n[InScript --profile] {filename}")
    print(f"{'-'*58}")
    print(f"  {'calls':>10}  {'time(s)':>8}  {'%':>5}  node/operation")
    print(f"{'-'*58}")
    for t, n, label in rows[:15]:
        pct = (t / total_time * 100) if total_time > 0 else 0
        print(f"  {n:>10,}  {t:>8.3f}  {pct:>4.1f}%  {label}")
    print(f"{'-'*58}")
    print(f"  {'':>10}  {total_time:>8.3f}  100.0%  TOTAL (hotspots)\n")


def run_source(source: str, filename: str = "<stdin>",
               type_check: bool = True,
               no_warn: bool = False,
               no_warn_unused: bool = False,
               warn_as_error: bool = False,
               profile: bool = False) -> int:
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

    # ── 3. Analyze (optional) — Phase 3: multi-error + warnings ──────────
    if type_check:
        from analyzer import Analyzer
        _analyzer = Analyzer(
            source.splitlines(),
            multi_error=True,
            warn_as_error=warn_as_error,
            no_warn=no_warn,
            no_warn_unused=no_warn_unused,
        )
        try:
            _analyzer.analyze(program)
        except MultiError as me:
            print(me, file=sys.stderr)
            return 1
        except SemanticError as e:
            print(e, file=sys.stderr)
            return 1

        # Print warnings
        if not no_warn and _analyzer._warnings:
            for w in _analyzer._warnings:
                print(w.format(), file=sys.stderr)
            n = len(_analyzer._warnings)
            print(f"[InScript] {n} warning{'s' if n != 1 else ''}", file=sys.stderr)

    # ── 4. Interpret — Phase 3: Python-leak guard ─────────────────────────
    try:
        interp = Interpreter(source.splitlines(), filename=filename)
        if profile:
            import cProfile, pstats, io as _io
            pr = cProfile.Profile()
            pr.enable()
            interp.run(program)
            pr.disable()
            _print_inscript_profile(pr, filename)
        else:
            interp.run(program)
        return 0
    except InScriptError as e:
        print(e, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n[InScript] Interrupted.", file=sys.stderr)
        return 130
    except Exception as e:
        # Phase 3.3: Zero Python leaking
        print(
            f"\n[InScript Internal Error] An unexpected error occurred.\n"
            f"  {type(e).__name__}: {e}\n"
            f"  Please report at: https://github.com/inscript-language/inscript/issues",
            file=sys.stderr
        )
        return 1


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
    try:
        from repl import EnhancedREPL
        EnhancedREPL().run()
        return
    except Exception:
        pass

    # Fallback simple REPL
    print(REPL_BANNER)
    interp  = Interpreter()
    buf     = []

    def show_result(val):
        if val is None: return
        from interpreter import _inscript_str
        print(f"  → {_inscript_str(val)}")

    def handle_dot_cmd(cmd):
        """Handle .help .vars .modules .type .clear .exit etc."""
        parts   = cmd.strip().split(None, 1)
        command = parts[0].lower()
        arg     = parts[1] if len(parts) > 1 else ""

        if command in (".help", "help"):
            print(REPL_HELP); return True
        if command in (".exit", ".quit", "exit", "quit"):
            print("[InScript] Goodbye!"); raise SystemExit(0)
        if command == ".clear":
            nonlocal interp, buf
            interp = Interpreter(); buf = []
            print("  (session cleared)"); return True
        if command == ".vars":
            items = {k: v for k, v in interp._env._store.items()
                     if not k.startswith("_")}
            if not items:
                print("  (no variables defined)")
            else:
                from interpreter import _inscript_str
                for k, v in sorted(items.items()):
                    try:    vs = _inscript_str(v)
                    except: vs = repr(v)
                    print(f"  {k} = {vs}")
            return True
        if command == ".modules":
            try:
                from stdlib import _MODULE_REGISTRY
                for name in sorted(_MODULE_REGISTRY.keys()):
                    print(f"  {name}")
            except Exception:
                mods = ["math","string","array","io","json","random","time",
                        "color","tween","grid","events","debug","http",
                        "path","regex","csv","uuid","crypto"]
                for m in mods: print(f"  {m}")
            return True
        if command == ".type":
            if not arg:
                print("  Usage: .type <expression>"); return True
            try:
                prog = parse(arg, "<repl>")
                from ast_nodes import ExprStmt
                if prog.body and isinstance(prog.body[-1], ExprStmt):
                    val = interp.visit(prog.body[-1].expr)
                    print(f"  {type(val).__name__}")
            except Exception as e:
                print(f"  Error: {e}")
            return True
        if command == ".fns":
            from stdlib_values import InScriptFunction
            fns = {k: v for k, v in interp._env._store.items()
                   if isinstance(v, InScriptFunction) and not k.startswith("_")}
            if not fns:
                print("  (no functions defined)")
            else:
                for k in sorted(fns): print(f"  fn {k}()")
            return True
        if command == ".history":
            print("  (history not available in fallback REPL)"); return True
        if command == ".reset":
            interp = Interpreter(); buf = []
            print("  (interpreter reset)"); return True
        return False

    while True:
        prompt = ">>> " if not buf else "... "
        try:
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\n[InScript] Goodbye!")
            break

        stripped = line.strip()
        if not stripped:
            continue

        # Dot commands
        if stripped.startswith(".") or stripped in ("exit","quit","help"):
            try:
                if handle_dot_cmd(stripped):
                    continue
            except SystemExit:
                break

        # Multiline continuation
        if line.endswith("\\"):
            buf.append(line[:-1]); continue
        buf.append(line)
        source = "\n".join(buf)
        buf = []

        try:
            prog = parse(source, "<repl>")
            interp.run(prog)
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
    parser.add_argument("--no-warn", action="store_true",
                        help="Suppress all warnings")
    parser.add_argument("--no-warn-unused", action="store_true",
                        help="Suppress unused-variable warnings only")
    parser.add_argument("--warn-as-error", action="store_true",
                        help="Treat any warning as an error (CI strictness)")
    parser.add_argument("--profile", action="store_true",
                        help="Print per-function call count and timing after execution")
    parser.add_argument("--fmt",     action="store_true",
                        help="Format .ins files: inscript --fmt file.ins")
    parser.add_argument("--fmt-check", action="store_true",
                        help="Check formatting without writing (exit 1 if unformatted)")
    parser.add_argument("--fmt-dry-run", action="store_true",
                        help="Print formatted output without writing")
    parser.add_argument("--test",    action="store_true",
                        help="Run test_*.ins files: inscript --test [file.ins]")
    parser.add_argument("--test-verbose", action="store_true",
                        help="Verbose test output")
    parser.add_argument("--test-fail-fast", action="store_true",
                        help="Stop tests on first failure")
    parser.add_argument("--watch",   action="store_true",
                        help="Watch file for changes and rerun: inscript --watch game.ins")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument("--install", metavar="PKG",
                        help="Install a package: inscript install math-utils")
    parser.add_argument("--remove", metavar="PKG",
                        help="Remove a package: inscript --remove math-utils")
    parser.add_argument("--packages", action="store_true",
                        help="List installed packages")
    parser.add_argument("--search", metavar="QUERY",
                        help="Search the registry: inscript --search math")
    parser.add_argument("--info", metavar="PKG",
                        help="Show package info: inscript --info math-utils")
    parser.add_argument("--lsp", action="store_true",
                        help="Start the Language Server (requires: pip install pygls)")
    parser.add_argument("--game", action="store_true",
                        help="Run .ins file in pygame window (requires: pip install pygame)")
    parser.add_argument("--width",  type=int, default=800,
                        help="Window width for --game mode  (default: 800)")
    parser.add_argument("--height", type=int, default=600,
                        help="Window height for --game mode (default: 600)")
    parser.add_argument("--fps",    type=int, default=60,
                        help="Target FPS for --game mode   (default: 60)")
    args = parser.parse_args()

    if args.version:
        print(f"InScript {VERSION}")
        return

    # ── inscript --fmt / --fmt-check / --fmt-dry-run ─────────────────────────
    if args.fmt or args.fmt_check or args.fmt_dry_run:
        try:
            from inscript_fmt import main as fmt_main
        except ImportError:
            print("Error: inscript_fmt.py not found", file=sys.stderr); return
        fmt_argv = []
        if args.file: fmt_argv.append(args.file)
        if args.fmt_check: fmt_argv.append("--check")
        if args.fmt_dry_run: fmt_argv.append("--dry-run")
        import sys as _sys; _sys.exit(fmt_main(fmt_argv) or 0)

    # ── inscript --test ─────────────────────────────────────────────────────
    if args.test:
        try:
            from inscript_test import main as test_main
        except ImportError:
            print("Error: inscript_test.py not found", file=sys.stderr); return
        test_argv = []
        if args.file: test_argv.append(args.file)
        if args.test_verbose: test_argv.append("--verbose")
        if args.test_fail_fast: test_argv.append("--fail-fast")
        import sys as _sys; _sys.exit(test_main(test_argv) or 0)

    # ── inscript --watch ─────────────────────────────────────────────────────
    if args.watch:
        if not args.file:
            print("Usage: inscript --watch <file.ins>", file=sys.stderr); return
        import time as _time
        print(f"\033[36mWatching {args.file} — Ctrl+C to stop\033[0m")
        last_mtime = None
        while True:
            try:
                mtime = os.path.getmtime(args.file)
                if mtime != last_mtime:
                    last_mtime = mtime
                    if last_mtime is not None:
                        print(f"\033[2m--- reloading {args.file} ---\033[0m")
                    os.system(f"{sys.executable} {__file__} {args.file}")
                _time.sleep(0.5)
            except KeyboardInterrupt:
                print(f"\033[2m[watch] stopped\033[0m"); break
            except FileNotFoundError:
                print(f"\033[31mFile not found: {args.file}\033[0m"); break
        return 0

    if args.lsp:
        from inscript_package.lsp.server import main as lsp_main
        lsp_main()
        return 0

    if args.packages:
        return list_packages()

    if args.install:
        return install_package(args.install)

    if args.remove:
        return remove_package(args.remove)

    if args.search:
        return search_packages(args.search)

    if args.info:
        return info_package(args.info)

    # --game: launch pygame window
    if args.game:
        if not args.file:
            print("[InScript] --game requires a .ins file", file=sys.stderr)
            return 1
        if not os.path.exists(args.file):
            print(f"[InScript] file not found: '{args.file}'", file=sys.stderr)
            return 1
        try:
            _here = os.path.dirname(os.path.abspath(__file__))
            sys.path.insert(0, _here)
            from pygame_backend import run_scene
            run_scene(args.file,
                      width=args.width, height=args.height, fps=args.fps,
                      title=os.path.basename(args.file))
            return 0
        except ImportError:
            print("[InScript] pygame_backend not found next to inscript.py", file=sys.stderr)
            return 1

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
    type_check    = not args.no_typecheck
    no_warn       = getattr(args, "no_warn", False)
    no_warn_unused= getattr(args, "no_warn_unused", False)
    warn_as_error = getattr(args, "warn_as_error", False)
    profile       = getattr(args, "profile", False)

    with open(args.file, "r", encoding="utf-8") as _f:
        _source = _f.read()
    return run_source(_source, filename=args.file, type_check=type_check,
                      no_warn=no_warn, no_warn_unused=no_warn_unused,
                      warn_as_error=warn_as_error, profile=profile)


if __name__ == "__main__":
    sys.exit(main())
