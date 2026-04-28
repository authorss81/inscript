# -*- coding: utf-8 -*-
# inscript/repl.py  —  Enhanced REPL v2
#
# Terminal features:
#   * Tab-completion: keywords, builtins, user symbols, member access after "."
#   * Persistent history  (~/.inscript/history)
#   * Multi-line smart detection (balanced braces; backslash continuation)
#   * Line-numbered continuation prompts  (... 2   ... 3 )
#   * Syntax highlighting (ANSI)
#   * Auto-print: bare expressions show their value like Python REPL
#   * Source context in error messages (offending line + caret)
#   * !! repeats last command
#
# Commands:
#   .help / .vars / .fns / .types / .env / .inspect <e> / .type <e>
#   .doc <module> / .clear / .reset / .save <f> / .load <f> / .run <f>
#   .export [f] / .time <e> / .bench <e> / .bytecode [src] / .asm [src]
#   .vm  (toggle VM vs interpreter)  / .history [n] / .modules / .packages
#
# Web playground:
#   python -m inscript.repl --web [--port 8080]

from __future__ import annotations
import os, sys, json, time, math, atexit, re as _re

# Python 3.11+ limits integer-to-string conversion; raise limit for large numbers
if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(100_000)

try:
    import readline
    _HAS_READLINE = True
except ImportError:
    readline = None          # Windows — readline not available; tab/history still work via fallback
    _HAS_READLINE = False
from pathlib import Path
from typing import List, Optional, Any, Tuple

sys.path.insert(0, str(Path(__file__).parent))

HISTORY_FILE = Path.home() / ".inscript" / "history"
HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
VERSION = "1.5.0"

# ── ANSI colours ──────────────────────────────────────────────────────────────
def _c(code, text):
    if not sys.stdout.isatty(): return text
    return f"\033[{code}m{text}\033[0m"

CYAN    = lambda t: _c("36",       t)
GREEN   = lambda t: _c("32",       t)
YELLOW  = lambda t: _c("33",       t)
MAGENTA = lambda t: _c("35",       t)
RED     = lambda t: _c("31",       t)
BOLD    = lambda t: _c("1",        t)
DIM     = lambda t: _c("2",        t)
BLUE    = lambda t: _c("34",       t)
ORANGE  = lambda t: _c("38;5;214", t)

def _make_banner():
    """Build the Gemini-style InScript REPL banner with pixel-art logo."""
    RST  = "\033[0m"
    BOLD = "\033[1m"
    DIM_  = "\033[2m"

    # Gradient: cyan → magenta across 57-char logo width
    # ANSI 256-colour horizontal gradient: 51(cyan) → 45 → 39 → 33 → 57 → 93 → 129(magenta)
    GRAD = [51, 51, 45, 45, 45, 39, 39, 39, 33, 33, 33, 27, 27, 57, 57, 57,
            93, 93, 93, 99, 99, 129, 129, 129, 135, 135, 171, 171, 171,
            171, 207, 207, 207, 213, 213, 213, 219, 219, 219, 225, 225,
            225, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231,
            231, 231, 231, 231]

    def grad_line(text):
        """Colour each character of text with the gradient."""
        out = []
        ci = 0
        for ch in text:
            if ch in ' \t':
                out.append(ch)
            else:
                c = GRAD[ci % len(GRAD)]
                out.append(f"\033[38;5;{c}m{ch}{RST}")
            ci += 1
        return "".join(out)

    LOGO_LINES = [
        r" ██╗███╗   ██╗███████╗ ██████╗██████╗ ██╗██████╗ ████████╗",
        r" ██║████╗  ██║██╔════╝██╔════╝██╔══██╗██║██╔══██╗╚══██╔══╝",
        r" ██║██╔██╗ ██║███████╗██║     ██████╔╝██║██████╔╝   ██║   ",
        r" ██║██║╚██╗██║╚════██║██║     ██╔══██╗██║██╔═══╝    ██║   ",
        r" ██║██║ ╚████║███████║╚██████╗██║  ██║██║██║        ██║   ",
        r" ╚═╝╚═╝  ╚═══╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝╚═╝        ╚═╝  ",
    ]

    W = 62
    logo_sep = f"\033[38;5;57m{'━' * W}{RST}"   # coloured bar above/below logo

    # ╔═══╗ box around the info block (matches old v1.0.1 style)
    TC = "\033[36m"                               # cyan for box lines
    box_top = f"{TC}╔{'═' * W}╗{RST}"
    box_bot = f"{TC}╚{'═' * W}╝{RST}"
    box_mid = f"{TC}╠{'═' * W}╣{RST}"

    def box_row(content):
        import re, unicodedata
        plain = re.sub(r'\033\[[0-9;]*m', '', content)
        # Use display width so box aligns on Windows (handles ambiguous-width chars)
        dw = sum(2 if unicodedata.east_asian_width(ch) in ('W', 'F') else 1 for ch in plain)
        pad = max(0, W - dw)
        return f"{TC}║{RST}{content}{' ' * pad}{TC}║{RST}"

    tagline = f" \033[38;5;51m>>\033[0m  \033[1mA scripting language for game development\033[0m  \033[2mv{VERSION}\033[0m"
    stats   = f" \033[2m59 stdlib modules  ·  527 tests  ·  Python 3.10+\033[0m"
    tips    = f" \033[33m.help\033[0m  commands  ·  \033[33m.modules\033[0m  stdlib  ·  \033[33mexit\033[0m  quit"

    lines = [""]
    lines.append(logo_sep)
    lines.append("")
    for row in LOGO_LINES:
        lines.append(grad_line(row))
    lines.append("")
    lines.append(box_top)
    lines.append(box_row(tagline))
    lines.append(box_mid)
    lines.append(box_row(stats))
    lines.append(box_mid)
    lines.append(box_row(tips))
    lines.append(box_bot)
    lines.append("")

    return "\n".join(lines)

BANNER = _make_banner()

def _make_help():
    RST  = "\033[0m"
    CY   = "\033[36m"
    YEL  = "\033[33m"
    GRN  = "\033[32m"
    MAG  = "\033[35m"
    DM   = "\033[2m"
    BLD  = "\033[1m"
    sep  = f"\033[38;5;57m{'━' * 58}{RST}"
    dim  = f"{DM}{'─' * 58}{RST}"

    def cmd(name, desc):
        return f"  {YEL}{name:<24}{RST}{desc}"

    def section(title):
        return f"\n  {BLD}{CY}{title}{RST}"

    lines = [
        "",
        sep,
        f"  {BLD}{'InScript REPL  —  Commands':^58}{RST}",
        sep,
        section("── Inspection ───────────────────────────────────────"),
        cmd(".help",               "Show this help"),
        cmd(".vars",               "List all defined variables"),
        cmd(".fns",                "List all defined functions"),
        cmd(".types",              "List struct / enum types"),
        cmd(".env",                "Show full environment tree"),
        cmd(".inspect <expr>",     "Deep field / method inspection"),
        cmd(".type <expr>",        "Show type of an expression"),
        cmd(".doc <module>",       "Show module exports"),
        cmd(".modules",            "Browse all 59 stdlib modules"),
        section("── Session ──────────────────────────────────────────"),
        cmd(".clear",              "Reset session variables"),
        cmd(".reset",              "Full reset (interpreter + history)"),
        cmd(".save <file>",        "Save session to .ins file"),
        cmd(".load / .run <file>", "Load and run a .ins file"),
        cmd(".export [file]",      "Export session as Markdown"),
        cmd(".history [n]",        "Show last n commands (default 20)"),
        section("── Analysis ─────────────────────────────────────────"),
        cmd(".time <expr>",        "Measure execution time (10 runs)"),
        cmd(".bench <expr>",       "Statistical benchmark (100 runs)"),
        cmd(".bytecode [expr]",    "Compact bytecode listing"),
        cmd(".asm [expr]",         "Full annotated assembly"),
        cmd(".vm",                 "Toggle VM / interpreter mode"),
        section("── General ──────────────────────────────────────────"),
        cmd(".packages",           "List installed packages"),
        cmd("exit / quit",         "Leave the REPL"),
        "",
        sep,
        f"  {BLD}Shortcuts{RST}",
        f"  {DM}Up/Down{RST}  Navigate history      {DM}Tab{RST}  Auto-complete",
        f"  {DM}!!{RST}       Repeat last command   {DM}Ctrl+C{RST}  Cancel / interrupt",
        "",
        f"  {BLD}Multi-line input{RST}",
        f"  Open a {CY}{{{RST} and press Enter — REPL continues until balanced",
        f"  End a line with {YEL}\\{RST} to force continuation",
        "",
        f"  {BLD}Auto-print{RST}",
        f"  {DM}Bare expressions print their value:{RST}",
        f"    {CY}>>>{RST} 2 ** 10",
        f"      {GRN}→{RST}  1024",
        sep,
        "",
    ]
    return "\n".join(lines)

HELP_TEXT = _make_help()


# All 59 stdlib modules, grouped by category
STDLIB_MODULES = [
    # Core
    "math","string","array","json","io","random","time","debug",
    # Data
    "csv","regex","xml","toml","yaml","url","base64","uuid",
    # Format / Iteration
    "format","iter","template","argparse",
    # Networking & Crypto
    "http","ssl","crypto","hash","net",
    # File System & Process
    "path","fs","process","compress","log",
    # Date & Collections
    "datetime","collections","database",
    # Threading & Bench
    "thread","bench",
    # Game: Visual
    "color","tween","image","atlas","animation","shader",
    # Game: Input / Audio
    "input","audio",
    # Game: World
    "physics2d","tilemap","camera2d","particle","pathfind",
    # Game: Systems
    "grid","events","ecs","fsm","save","localize","net_game",
    # Utilities
    "signal","vec","pool",
]

STDLIB_CATEGORIES = {
    "Core":             ["math","string","array","json","io","random","time","debug"],
    "Data":             ["csv","regex","xml","toml","yaml","url","base64","uuid"],
    "Format/Iter":      ["format","iter","template","argparse"],
    "Net/Crypto":       ["http","ssl","crypto","hash","net"],
    "FS/Process":       ["path","fs","process","compress","log"],
    "Date/Collections": ["datetime","collections","database"],
    "Async/Bench":      ["thread","bench"],
    "Game: Visual":     ["color","tween","image","atlas","animation","shader"],
    "Game: I/O":        ["input","audio"],
    "Game: World":      ["physics2d","tilemap","camera2d","particle","pathfind"],
    "Game: Systems":    ["grid","events","ecs","fsm","save","localize","net_game"],
    "Utilities":        ["signal","vec","pool"],
}

STDLIB_DOCS = {
    "math":   ["sin(x)","cos(x)","tan(x)","sqrt(x)","pow(x,y)","abs(x)","floor(x)",
               "ceil(x)","round(x)","log(x)","log2(x)","exp(x)","PI","E","TAU","INF","NAN"],
    "string": ["len(s)","upper(s)","lower(s)","trim(s)","split(s,sep)","join(a,sep)",
               "replace(s,old,new)","contains(s,sub)","starts_with(s,p)","ends_with(s,p)",
               "substring(s,a,b)","repeat(s,n)","pad_start(s,n,c)","index_of(s,sub)"],
    "array":  ["len(a)","push(a,v)","pop(a)","insert(a,i,v)","remove(a,i)","contains(a,v)",
               "sort(a)","reverse(a)","map(a,fn)","filter(a,fn)","reduce(a,fn,i)",
               "zip(a,b)","enumerate(a)","unique(a)","chunk(a,n)","take(a,n)","skip(a,n)",
               "sum(a)","min(a)","max(a)","any(a,fn)","all(a,fn)"],
    "random": ["int(min,max)","float(min,max)","bool()","choice(arr)","shuffle(arr)","seed(n)"],
    "json":   ["parse(s)","stringify(v)","stringify_pretty(v)"],
    "io":     ["read_file(p)","write_file(p,s)","append_file(p,s)","read_lines(p)",
               "file_exists(p)","delete_file(p)","list_dir(p)","input(prompt)"],
    "time":   ["now()","sleep(ms)","format(t,fmt)"],
    "regex":  ["match(pat,s)","find(pat,s)","find_all(pat,s)","replace(pat,s,r)","test(pat,s)"],
    "path":   ["join(...)","exists(p)","dir(p)","base(p)","ext(p)","absolute(p)"],
    "color":  ["rgb(r,g,b)","rgba(r,g,b,a)","hsv(h,s,v)","lerp(a,b,t)",
               "from_hex(s)","to_hex(c)","BLACK","WHITE","RED","GREEN","BLUE"],
}

KEYWORDS = [
    "let","const","fn","struct","enum","interface","mixin","impl","extends","implements",
    "if","else","while","for","in","return","break","continue","match","case",
    "import","from","export","async","await","yield","try","catch","finally","throw",
    "abstract","select","true","false","nil","self","super","operator","static",
    "print","len","string","int","float","bool","typeof","range",
    "push","pop","contains","sort","reverse","map","filter","reduce","zip","enumerate",
    "flatten","unique","chunk","take","skip","sum","min","max","abs","sqrt",
    "floor","ceil","round","pow","split","join","trim","upper","lower","replace",
    "starts_with","ends_with","substring","has_key","keys","values","entries",
    "is_nil","is_int","is_float","is_str","is_bool","is_array","is_dict","Ok","Err",
]

# ── SYNTAX HIGHLIGHTER ────────────────────────────────────────────────────────
_KW_RE  = _re.compile(r'\b(let|const|fn|struct|enum|interface|if|else|while|for|in|return|'
                      r'break|continue|match|case|import|from|export|async|await|yield|try|'
                      r'catch|finally|throw|true|false|nil|self|super|operator|static)\b')
_NUM_RE = _re.compile(r'\b\d+\.?\d*\b')
_STR_RE = _re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"')
_CMT_RE = _re.compile(r'//.*$')
_FN_RE  = _re.compile(r'\b([a-z_]\w*)\s*(?=\()')
_TY_RE  = _re.compile(r'\b([A-Z]\w*)\b')

def highlight(line):
    if not sys.stdout.isatty(): return line
    r = line
    r = _STR_RE.sub(lambda m: GREEN(m.group()), r)
    r = _CMT_RE.sub(lambda m: DIM(m.group()), r)
    r = _KW_RE.sub(lambda m: CYAN(m.group()), r)
    r = _NUM_RE.sub(lambda m: MAGENTA(m.group()), r)
    r = _TY_RE.sub(lambda m: YELLOW(m.group()), r)
    r = _FN_RE.sub(lambda m: BLUE(m.group(1)), r)
    return r

# ── TAB COMPLETER ─────────────────────────────────────────────────────────────
class InScriptCompleter:
    def __init__(self, repl):
        self._repl = repl
        self._matches = []

    def _user_names(self):
        try:
            return [k for k in self._repl._interp._env._store if not k.startswith("_")]
        except: return []

    def _member_names(self, obj_name):
        try:
            obj = self._repl._interp._env._store.get(obj_name)
            if obj is None: return []
            if isinstance(obj, dict):
                return [str(k) for k in obj if not str(k).startswith("_")]
            return [a for a in dir(obj) if not a.startswith("_")]
        except: return []

    def complete(self, text, state):
        if state == 0:
            buf = readline.get_line_buffer() if _HAS_READLINE else text
            dot_match = _re.match(r'.*?(\w+)\.([\w]*)$', buf)
            if dot_match:
                obj_name = dot_match.group(1)
                prefix   = dot_match.group(2)
                members  = self._member_names(obj_name)
                self._matches = [m for m in members if m.startswith(prefix)]
            else:
                candidates = list(KEYWORDS) + self._user_names() + STDLIB_MODULES
                self._matches = [c for c in sorted(set(candidates)) if c.startswith(text)]
        try:    return self._matches[state]
        except: return None

# ── EXPRESSION DETECTOR ───────────────────────────────────────────────────────
_STMT_STARTS = (
    "let ","const ","fn ","struct ","enum ","interface ","mixin ","impl ",
    "import ","from ","export ","if ","while ","for ","return ","break",
    "continue","throw ","try","match ","print(","//",
)
_ASSIGN_RE = _re.compile(r'^[A-Za-z_]\w*\s*(\*\*=|<<=|>>=|&&=|\|\|=|[+\-*/%&|^]=|=)(?!=)\s*')
_BLOCK_RE  = _re.compile(r'^(fn|struct|enum|interface)\s+\w+')

def _is_expression(source):
    s = source.strip()
    if not s: return False
    if any(s.startswith(k) for k in _STMT_STARTS): return False
    if _ASSIGN_RE.match(s): return False
    if _BLOCK_RE.match(s): return False
    return True

# ── ERROR FORMATTER ───────────────────────────────────────────────────────────
def _format_error(err_str, source):
    lines = source.splitlines()
    m = _re.search(r'Line (\d+).*?Col (\d+)', err_str)
    if m and lines:
        ln  = int(m.group(1)) - 1
        col = int(m.group(2)) - 1
        if 0 <= ln < len(lines):
            src_line = lines[ln]
            caret    = " " * max(0, col) + "^"
            return f"{err_str}\n  {DIM(src_line)}\n  {RED(caret)}"
    return err_str

# ── TYPE HELPERS ──────────────────────────────────────────────────────────────
def _type_name(val):
    if val is None:           return "nil"
    if isinstance(val, bool): return "bool"
    if isinstance(val, int):  return "int"
    if isinstance(val, float):return "float"
    if isinstance(val, str):  return "string"
    if isinstance(val, list): return "array"
    if isinstance(val, dict):
        if "_enum" in val or "_variant" in val: return val.get("_enum","enum")
        if "_name" in val: return val["_name"]
        return "dict"
    return type(val).__name__

def _type_ann_str(node):
    if node is None: return "any"
    if isinstance(node, str): return node
    return getattr(node, 'name', None) or str(node)

def _val_preview(val, max_len=60):
    try:
        from interpreter import _inscript_str
        s = _inscript_str(val)
    except:
        s = repr(val)
    return s[:max_len] + ("…" if len(s) > max_len else "")

def _print_inspect(val, indent=0):
    pad = "  " * indent
    if isinstance(val, dict) and "_name" in val:
        sname = val["_name"]
        print(f"{pad}{BOLD(YELLOW(sname))} {{")
        for k, v in val.items():
            if str(k).startswith("_"): continue
            print(f"{pad}  {CYAN(k)}: {DIM(_type_name(v))} = {GREEN(_val_preview(v))}")
        print(f"{pad}}}")
    elif isinstance(val, dict):
        print(f"{pad}{BOLD('dict')} [{len(val)} entries] {{")
        for k, v in list(val.items())[:20]:
            if str(k).startswith("_"): continue
            print(f"{pad}  {GREEN(repr(k))}: {DIM(_type_name(v))} = {_val_preview(v)}")
        if len(val) > 20: print(f"{pad}  {DIM(f'... {len(val)-20} more')}")
        print(f"{pad}}}")
    elif isinstance(val, list):
        print(f"{pad}{BOLD('array')} [{len(val)} items]")
        for i, item in enumerate(val[:10]):
            print(f"{pad}  [{i}] {DIM(_type_name(item))} {GREEN(_val_preview(item))}")
        if len(val) > 10: print(f"{pad}  {DIM(f'... {len(val)-10} more')}")
    else:
        print(f"{pad}{YELLOW(_type_name(val))}: {GREEN(_val_preview(val))}")
        attrs = [a for a in dir(val) if not a.startswith("_") and callable(getattr(val, a, None))]
        if attrs:
            print(f"{pad}  {DIM('methods:')} {', '.join(BLUE(a) for a in attrs[:10])}")

# ── ENHANCED REPL ─────────────────────────────────────────────────────────────
class EnhancedREPL:

    def __init__(self):
        from interpreter import Interpreter
        from vm import VM
        self._interp   = Interpreter()
        self._vm       = VM()          # persistent VM — keeps globals between calls
        self._use_vm   = False
        self._history: List[str] = []
        self._session: List[str] = []
        self._last_src: str = ""
        self._setup_readline()

    def _setup_readline(self):
        if not _HAS_READLINE:
            return          # Windows: readline not available; skip tab/history setup
        completer = InScriptCompleter(self)
        readline.set_completer(completer.complete)
        readline.parse_and_bind("tab: complete")
        readline.set_completer_delims(" \t\n`~!@#$%^&*()-=+[{]}\\|;:'\",<>?/")
        if HISTORY_FILE.exists():
            try: readline.read_history_file(str(HISTORY_FILE))
            except: pass
        atexit.register(lambda: readline.write_history_file(str(HISTORY_FILE)))

    # ── execution ─────────────────────────────────────────────────────────────
    def _eval(self, source) -> Tuple[Any, Optional[str], float]:
        # NOTE: We intentionally skip the full static Analyzer in REPL mode
        # (it has no memory of previous statements). But we do run a targeted
        # arg-count analysis pass using the interpreter's live environment.
        from lexer import Lexer
        from parser import Parser
        from errors import InScriptError
        t0 = time.perf_counter()
        try:
            tokens  = Lexer(source).tokenize()
            program = Parser(tokens).parse()

            # Quick arg-count pass: look for CallExprs with known functions
            try:
                self._check_arg_counts(program)
            except Exception:
                pass  # never block execution for analysis errors

            if self._use_vm:
                from compiler import Compiler
                result = self._vm.run(Compiler().compile(program))
            else:
                result = self._interp.run(program)
            return result, None, (time.perf_counter() - t0) * 1000
        except InScriptError as e:
            return None, _format_error(str(e), source), (time.perf_counter() - t0) * 1000
        except Exception as e:
            import traceback as _tb
            return None, f"Internal error: {e}\n{_tb.format_exc()}", (time.perf_counter() - t0) * 1000

    def _check_arg_counts(self, program):
        """Walk the AST looking for calls to known user-defined functions and warn on arity mismatches.
        Also checks for missing return statements in typed functions."""
        from ast_nodes import CallExpr, IdentExpr, FunctionDecl, ReturnStmt, IfStmt, MatchStmt
        from stdlib_values import InScriptFunction
        import sys as _sys

        def body_always_returns(block):
            stmts = getattr(block, 'body', [])
            for stmt in reversed(stmts):
                if isinstance(stmt, ReturnStmt):
                    return True
                if isinstance(stmt, IfStmt):
                    if (stmt.else_branch and
                            body_always_returns(stmt.then_branch) and
                            body_always_returns(stmt.else_branch)):
                        return True
            return False

        def walk(node):
            if node is None: return
            # Check function declarations for missing returns + async + duplicate names
            if isinstance(node, FunctionDecl):
                ret = getattr(node, 'return_type', None)
                if ret is not None and hasattr(ret, 'name') and ret.name not in ('void', 'nil', 'any', ''):
                    if node.body and not body_always_returns(node.body):
                        print(
                            f"\033[33m[InScript] Warning: '{node.name}' declares return type "
                            f"'{ret.name}' but not all paths return a value\033[0m",
                            file=_sys.stderr
                        )
                # Check async
                if getattr(node, 'is_async', False):
                    print(
                        f"\033[33m[InScript] Warning: 'async fn {node.name}' executes synchronously — "
                        f"use the 'thread' module for real concurrency\033[0m",
                        file=_sys.stderr
                    )
                # Check duplicate definition
                try:
                    existing = self._interp._env.get(node.name, 0)
                    if isinstance(existing, InScriptFunction) and not existing.is_native:
                        print(
                            f"\033[33m[InScript] Warning: '{node.name}' redefines an existing "
                            f"function (previous definition will be shadowed)\033[0m",
                            file=_sys.stderr
                        )
                except Exception:
                    pass
            # Check call arg counts + type mismatches
            if isinstance(node, CallExpr) and isinstance(node.callee, IdentExpr):
                fname = node.callee.name
                try:
                    fn = self._interp._env.get(fname, 0)
                except Exception:
                    fn = None
                if isinstance(fn, InScriptFunction) and not fn.is_native:
                    params = fn.params or []
                    n_args = len(node.args)
                    n_total = len(params)
                    n_required = sum(1 for p in params
                                     if not getattr(p, 'default', None)
                                     and not getattr(p, 'variadic', False))
                    has_variadic = any(getattr(p, 'variadic', False) for p in params)
                    if not has_variadic:
                        if n_args < n_required:
                            print(f"\033[33m[InScript] Warning: '{fname}' expects at least "
                                  f"{n_required} arg(s), got {n_args}\033[0m", file=_sys.stderr)
                        elif n_args > n_total:
                            print(f"\033[33m[InScript] Warning: '{fname}' expects at most "
                                  f"{n_total} arg(s), got {n_args}\033[0m", file=_sys.stderr)
                    # Type mismatch check: compare annotated param types with literal arg types
                    _TYPE_MAP = {
                        'IntLiteralExpr': 'int', 'FloatLiteralExpr': 'float',
                        'StringLiteralExpr': 'string', 'BoolLiteralExpr': 'bool',
                        'NullLiteralExpr': 'nil', 'ArrayLiteralExpr': 'array',
                        'DictLiteralExpr': 'dict',
                    }
                    for i, (arg, param) in enumerate(zip(node.args, params)):
                        ann = getattr(getattr(param, 'type_ann', None), 'name', None)
                        if not ann or ann in ('any', '', None):
                            continue
                        arg_type = _TYPE_MAP.get(type(arg.value).__name__)
                        if arg_type and arg_type != ann:
                            print(f"\033[33m[InScript] Warning: '{fname}' arg {i+1} expects "
                                  f"'{ann}' but got '{arg_type}'\033[0m", file=_sys.stderr)

            # Non-exhaustive match check
            from ast_nodes import MatchStmt as _MS, IdentExpr as _IE
            if isinstance(node, _MS):
                has_wildcard = any(
                    arm.pattern is None or (isinstance(arm.pattern, _IE) and arm.pattern.name == '_')
                    for arm in node.arms
                )
                if not has_wildcard:
                    print(f"\033[33m[InScript] Warning: match may not be exhaustive — "
                          f"add 'case _ {{ }}' to handle unmatched values\033[0m", file=_sys.stderr)

            # Recurse
            for attr in vars(node).values():
                if hasattr(attr, '__class__') and hasattr(attr, 'line'):
                    walk(attr)
                elif isinstance(attr, list):
                    for item in attr:
                        if hasattr(item, '__class__') and hasattr(item, 'line'):
                            walk(item)

        for stmt in (program.body or []):
            walk(stmt)

    def _eval_expr(self, source):
        """Evaluate source; if it looks like a bare expression, capture and
        return its value so the REPL can auto-print it.

        Strategy:
        - Always attempt value-capture via the interpreter (persistent env).
        - If interpreter returns an error AND we are in VM mode, the expression
          likely references a name defined in the VM's environment.  In that
          case silently fall back to _eval() (VM path) — no auto-print, but
          no error shown either.  This is a known limitation: auto-print for
          VM-mode user-defined calls is not supported.
        """
        if _is_expression(source):
            wrapped = f"let __repl_rv__ = ({source})"
            from lexer import Lexer
            from parser import Parser
            from errors import InScriptError
            import time as _t
            t0 = _t.perf_counter()
            try:
                tokens  = Lexer(wrapped).tokenize()
                program = Parser(tokens).parse()
                self._interp.run(program)
                result  = self._interp._env._store.get("__repl_rv__")
                self._interp._env._store.pop("__repl_rv__", None)
                return result, None, (_t.perf_counter() - t0) * 1000
            except (InScriptError, Exception):
                # Value capture failed — fall through to normal _eval().
                # In interpreter mode _eval returns a clean (None, err, ms).
                # In VM mode _eval runs the expression through the VM (no
                # auto-print, but correct side-effects and error reporting).
                pass
        return self._eval(source)

    def _fmt_result(self, val):
        if val is None: return ""
        try:
            from interpreter import _inscript_str
            s = _inscript_str(val)
        except:
            s = repr(val)
        if s in ("nil", "None", ""): return ""
        return f"  {DIM('→')} {GREEN(s)}"

    def _is_complete(self, source):
        depth = 0; in_str = False; esc = False
        for ch in source:
            if esc: esc = False; continue
            if ch == '\\' and in_str: esc = True; continue
            if ch == '"': in_str = not in_str; continue
            if in_str: continue
            if ch in "{[(": depth += 1
            elif ch in "}])": depth -= 1
        return depth <= 0

    # ── dot-commands ──────────────────────────────────────────────────────────
    def _handle_command(self, cmd):
        parts   = cmd.strip().split(None, 1)
        if not parts: return False
        c   = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if c in (".help","help"):
            print(HELP_TEXT)

        elif c == ".vars":
            from interpreter import _inscript_str
            from stdlib_values import InScriptFunction
            skip = {"__repl_rv__"}
            rows = {k: v for k, v in self._interp._env._store.items()
                    if not k.startswith("_") and k not in skip
                    and not isinstance(v, InScriptFunction)}
            if not rows:
                print(DIM("  (no variables defined)"))
            else:
                w = max(len(k) for k in rows) + 1
                for name, val in sorted(rows.items()):
                    try:   vs = _inscript_str(val)
                    except: vs = repr(val)
                    print(f"  {CYAN(name.ljust(w))} {DIM(f':{_type_name(val):<10}')} {GREEN(vs)}")

        elif c == ".fns":
            from stdlib_values import InScriptFunction
            fns = {k: v for k, v in self._interp._env._store.items()
                   if isinstance(v, InScriptFunction) and not k.startswith("_")}
            if not fns:
                print(DIM("  (no user functions defined)"))
            else:
                for name, fn in sorted(fns.items()):
                    params = []
                    for p in getattr(fn, 'params', []):
                        pname = getattr(p, 'name', str(p))
                        ptype = getattr(p, 'type_annotation', None)
                        pdef  = getattr(p, 'default', None)
                        s = pname
                        if ptype: s += f": {YELLOW(_type_ann_str(ptype))}"
                        if pdef is not None: s += DIM(" = ...")
                        params.append(s)
                    ret = ""
                    rtype = getattr(fn, 'return_type', None)
                    if rtype: ret = f" {DIM('->')} {YELLOW(_type_ann_str(rtype))}"
                    print(f"  {BLUE('fn')} {CYAN(name)}({', '.join(params)}){ret}")

        elif c == ".types":
            found = False
            for name, val in sorted(self._interp._env._store.items()):
                if name.startswith("_"): continue
                if isinstance(val, dict) and val.get("_kind") == "struct_decl":
                    found = True
                    decl = val.get("_decl")
                    fields  = [f"{CYAN(f.name)}: {YELLOW(_type_ann_str(f.type_annotation))}"
                                for f in getattr(decl, 'fields', []) if hasattr(f, 'name')]
                    methods = [f.name for f in getattr(decl, 'methods', [])]
                    print(f"  {BOLD('struct')} {YELLOW(name)}")
                    if fields:   print(f"    fields:  {', '.join(fields)}")
                    if methods:  print(f"    methods: {', '.join(BLUE(m) for m in methods)}")
                elif isinstance(val, dict) and val.get("_kind") == "enum_decl":
                    found = True
                    decl = val.get("_decl")
                    variants = list(getattr(decl, 'variants', {}).keys()) if decl else []
                    vstr = " { " + ", ".join(CYAN(v) for v in variants) + " }" if variants else ""
                    print(f"  {BOLD('enum')} {YELLOW(name)}{vstr}")
            if not found:
                print(DIM("  (no struct/enum types defined)"))

        elif c == ".env":
            from interpreter import _inscript_str
            from stdlib_values import InScriptFunction
            env = self._interp._env
            depth = 0; seen = set()
            while env is not None:
                label = getattr(env, 'name', f"scope {depth}")
                pad   = "  " * depth
                print(f"{pad}{BOLD(label)}:")
                store = getattr(env, '_store', {})
                shown = 0
                for k, v in sorted(store.items()):
                    if k.startswith("_") or k in seen: continue
                    seen.add(k)
                    try:   vs = _inscript_str(v)[:60]
                    except: vs = repr(v)[:60]
                    print(f"{pad}  {CYAN(k)}: {DIM(_type_name(v))} = {GREEN(vs)}")
                    shown += 1
                if not shown: print(f"{pad}  {DIM('(empty)')}")
                env = getattr(env, '_parent', None)
                depth += 1

        elif c == ".inspect":
            if not arg: print(RED("  Usage: .inspect <expression>")); return True
            val, err, _ = self._eval(arg)
            if err:
                val = self._interp._env._store.get(arg)
            if val is None and err:
                print(RED(f"  Error: {err}")); return True
            _print_inspect(val)

        elif c == ".type":
            if not arg: print(RED("  Usage: .type <expression>")); return True
            val, err, _ = self._eval_expr(arg)
            if err: print(RED(f"  Error: {err}")); return True
            print(f"  {YELLOW(_type_name(val))}  {DIM('→')}  {GREEN(_val_preview(val))}")

        elif c == ".doc":
            if not arg:
                print(f"  Usage: {YELLOW('.doc <module>')}  —  modules: {', '.join(STDLIB_MODULES)}")
                return True
            mod = arg.strip().strip("\"'")

            # Priority 1: hardcoded STDLIB_DOCS (rich signature strings)
            if mod in STDLIB_DOCS:
                fns = STDLIB_DOCS[mod]
                print(f"  {BOLD(CYAN(mod))} stdlib module ({len(fns)} exports):")
                for i in range(0, len(fns), 3):
                    row = fns[i:i+3]
                    print("    " + "  ".join(BLUE(f.ljust(24)) for f in row))
                return True

            # Priority 2: query stdlib._MODULES directly (works for ALL 59 modules)
            try:
                from stdlib import _MODULES
                if mod in _MODULES:
                    mod_dict = _MODULES[mod]
                    keys = sorted(k for k in mod_dict if not k.startswith("_"))
                    print(f"  {BOLD(CYAN(mod))} stdlib module ({len(keys)} exports):")
                    W = 62
                    col_w = 20
                    per_row = max(1, W // (col_w + 2))
                    for i in range(0, len(keys), per_row):
                        row = keys[i:i+per_row]
                        print("    " + "  ".join(CYAN(k.ljust(col_w)) for k in row))
                    print(f"  {DIM('Usage:')} import \"{mod}\" as {mod[0].upper()}")
                    return True
            except Exception:
                pass

            # Priority 3: try dynamic import as last resort
            try:
                from interpreter import Interpreter
                tmp = Interpreter()
                tmp.execute(f'import "{mod}" as _doc_tmp_')
                env_mod = tmp._env._store.get('_doc_tmp_')
                if isinstance(env_mod, dict):
                    keys = [k for k in sorted(env_mod) if not k.startswith("_")]
                    print(f"  {BOLD(CYAN(mod))} — {len(keys)} exports:")
                    for i in range(0, len(keys), 4):
                        row = keys[i:i+4]
                        print("    " + "  ".join(CYAN(k.ljust(16)) for k in row))
                else:
                    print(DIM(f"  Module '{mod}' not found."))
            except Exception as e:
                print(RED(f"  Cannot load '{mod}': {e}"))

        elif c == ".clear":
            from interpreter import Interpreter
            from vm import VM
            self._interp = Interpreter()
            self._vm     = VM()
            self._session.clear()
            print(DIM("  (session cleared)"))

        elif c == ".reset":
            from interpreter import Interpreter
            from vm import VM
            self._interp = Interpreter()
            self._vm     = VM()
            self._session.clear(); self._history.clear()
            if _HAS_READLINE: readline.clear_history()
            print(DIM("  (full reset — interpreter, session and history cleared)"))

        elif c == ".save":
            if not arg: print(RED("  Usage: .save <file.ins>")); return True
            p = Path(arg)
            p.write_text("\n".join(self._session))
            print(GREEN(f"  Saved {len(self._session)} lines → {p}"))

        elif c in (".load", ".run"):
            if not arg: print(RED(f"  Usage: {c} <file.ins>")); return True
            p = Path(arg)
            if not p.exists(): print(RED(f"  File not found: {p}")); return True
            source = p.read_text()
            print(DIM(f"  Loading {p}…"))
            result, err, ms = self._eval(source)
            if err: print(RED(f"  ✗ {err}"))
            else:
                fmt = self._fmt_result(result)
                if fmt: print(fmt)
                print(GREEN(f"  Done in {ms:.1f}ms"))
                self._session.append(f"// --- {p} ---\n" + source)

        elif c == ".export":
            lines = [f"# InScript Session\n\n*InScript v{VERSION}*\n"]
            for entry in self._session:
                lines.append("```inscript\n" + entry + "\n```\n")
            content = "\n".join(lines)
            if arg:
                Path(arg).write_text(content)
                print(GREEN(f"  Exported {len(self._session)} entries → {arg}"))
            else:
                print(content)

        elif c == ".time":
            if not arg: print(RED("  Usage: .time <expr>")); return True
            times = [self._eval(arg)[2] for _ in range(10)]
            avg = sum(times)/10
            print(f"  avg {CYAN(f'{avg:.2f}ms')}  min {GREEN(f'{min(times):.2f}ms')}  "
                  f"max {YELLOW(f'{max(times):.2f}ms')}  (10 runs)")

        elif c == ".bench":
            if not arg: print(RED("  Usage: .bench <expr>")); return True
            N = 100
            print(DIM(f"  Warming up (5 runs)…"))
            for _ in range(5): self._eval(arg)
            print(DIM(f"  Benchmarking ({N} runs)…"))
            times = [self._eval(arg)[2] for _ in range(N)]
            avg = sum(times)/N
            mn, mx = min(times), max(times)
            stddev = math.sqrt(sum((t-avg)**2 for t in times)/N)
            p50 = sorted(times)[N//2]
            p95 = sorted(times)[int(N*0.95)]
            print(f"  {BOLD('Benchmark')} ({N} runs):")
            print(f"    mean   {CYAN(f'{avg:.3f}ms')}   stddev {DIM(f'{stddev:.3f}ms')}")
            print(f"    min    {GREEN(f'{mn:.3f}ms')}   max    {YELLOW(f'{mx:.3f}ms')}")
            print(f"    p50    {DIM(f'{p50:.3f}ms')}   p95    {DIM(f'{p95:.3f}ms')}")

        elif c == ".bytecode":
            src = arg or self._last_src
            if not src: print(DIM("  (no expression yet)")); return True
            try:
                from compiler import compile_source
                for line in compile_source(src).disassemble().splitlines():
                    toks = line.split()
                    if line.startswith("==="): print(BOLD(CYAN(line)))
                    elif len(toks) >= 2 and toks[0].isdigit():
                        ops = "  ".join(f"{int(t):5}" for t in toks[2:5] if t.lstrip("-").isdigit())
                        print(f"  {DIM(toks[0]):>4}  {YELLOW(toks[1]):<22} {CYAN(ops)}")
                    else: print(DIM(line))
            except Exception as e: print(RED(f"  Bytecode error: {e}"))

        elif c == ".asm":
            src = arg or self._last_src
            if not src: print(DIM("  Usage: .asm <expression>")); return True
            try:
                from compiler import compile_source, FnProto, Op
                def _pp(p, ind=0):
                    pad = "  " * ind
                    print(f"{pad}{BOLD(CYAN(f'=== fn {p.name} ==='))}")
                    if p.consts:
                        print(f"{pad}  {DIM('Constants:')}")
                        for ci, cv in enumerate(p.consts):
                            lbl = f"<fn {cv.name}>" if isinstance(cv, FnProto) else repr(cv)
                            print(f"{pad}    [{ci}] {GREEN(lbl)}")
                    if p.names:
                        print(f"{pad}  {DIM('Names:')}")
                        for ni, nv in enumerate(p.names):
                            print(f"{pad}    [{ni}] {YELLOW(nv)}")
                    print(f"{pad}  {DIM(f'Code ({len(p.code)} instrs, {p.n_locals} locals):')}")
                    for idx, ins in enumerate(p.code):
                        ann = ""
                        if ins.op == Op.LOAD_CONST and ins.b < len(p.consts):
                            v = p.consts[ins.b]
                            ann = f"; <fn {v.name}>" if isinstance(v, FnProto) else f"; {v!r}"
                        elif ins.op in (Op.LOAD_GLOBAL, Op.STORE_GLOBAL):
                            ni = ins.b if ins.op == Op.LOAD_GLOBAL else ins.a
                            if ni < len(p.names): ann = f"; '{p.names[ni]}'"
                        elif ins.op in (Op.GET_FIELD, Op.SET_FIELD, Op.CALL_METHOD, Op.OP_CALL):
                            ni = ins.c if ins.op == Op.GET_FIELD else ins.b
                            if ni < len(p.names): ann = f"; '{p.names[ni]}'"
                        elif ins.op == Op.LOAD_INT: ann = f"; {ins.b}"
                        print(f"{pad}    {DIM(str(idx)):>4}  {YELLOW(ins.op.name):<22}"
                              f"  {CYAN(str(ins.a)):>5}  {CYAN(str(ins.b)):>5}  {CYAN(str(ins.c)):>5}"
                              f"  {DIM(ann)}")
                    for sp in getattr(p, 'protos', []):
                        print(); _pp(sp, ind+1)
                _pp(compile_source(src))
            except Exception as e:
                import traceback as _tb
                print(RED(f"  ASM error: {e}")); _tb.print_exc()

        elif c == ".vm":
            self._use_vm = not self._use_vm
            mode = ORANGE("VM (bytecode)") if self._use_vm else CYAN("Interpreter (tree-walk)")
            print(f"  Execution mode: {mode}")

        elif c == ".history":
            n = int(arg) if arg.isdigit() else 20
            shown = self._history[-n:]
            base  = len(self._history) - len(shown) + 1
            for i, h in enumerate(shown, base):
                print(f"  {DIM(str(i)):>5}  {h}")

        elif c == ".modules":
            RST = "\033[0m"; CY = "\033[36m"; YEL = "\033[33m"
            BLD = "\033[1m"; DM  = "\033[2m"; MAG = "\033[35m"
            sep = f"\033[38;5;57m{'━' * 58}{RST}"
            print(sep)
            print(f"  {BLD}{'InScript  —  56 Stdlib Modules':^58}{RST}")
            print(sep)
            for cat, mods in STDLIB_CATEGORIES.items():
                print(f"\n  {YEL}{cat}{RST}")
                for i in range(0, len(mods), 6):
                    row = mods[i:i+6]
                    print("    " + "  ".join(f"{CY}{m:<12}{RST}" for m in row))
            print(f"\n{sep}")
            total = sum(len(v) for v in STDLIB_CATEGORIES.values())
            print(f"  {DM}{total} modules total{RST}  ·  {YEL}import \"math\"{RST}  ·  {YEL}.doc <module>{RST} for details")
            print(sep)

        elif c == ".packages":
            pkg_dir = Path.home() / ".inscript" / "packages"
            if not pkg_dir.exists():
                print(DIM("  No packages installed."))
            else:
                pkgs = [d.name for d in pkg_dir.iterdir() if d.is_dir()]
                if not pkgs: print(DIM("  No packages installed."))
                else:
                    print(BOLD(f"  Installed packages ({len(pkgs)}):"))
                    for p in sorted(pkgs): print(f"    • {CYAN(p)}")

        else:
            return False
        return True

    # ── main loop ─────────────────────────────────────────────────────────────
    def run(self):
        print(BANNER)
        buf: List[str] = []

        while True:
            if not buf:
                mode_tag = ORANGE(" [VM]") if self._use_vm else ""
                prompt = f"{CYAN('>>>')}{mode_tag} "
            else:
                prompt = f"{DIM(f'...{len(buf)+1}')} "

            try:
                line = input(prompt)
            except KeyboardInterrupt:
                buf.clear(); print(); continue
            except EOFError:
                print(f"\n{DIM('[InScript] Goodbye!')}"); break

            stripped = line.strip()

            if stripped in ("exit","quit",".exit",".quit"):
                print(DIM("[InScript] Goodbye!")); break

            # !! — repeat last command
            if stripped == "!!" and self._history:
                line = self._history[-1]
                print(f"  {DIM('↑')} {line}")
                stripped = line.strip()

            # Dot-commands only at top level
            if not buf and stripped.startswith("."):
                if self._handle_command(stripped):
                    continue

            # Backslash continuation
            if line.endswith("\\"):
                buf.append(line[:-1]); continue

            buf.append(line)
            source = "\n".join(buf)

            if not self._is_complete(source): continue

            buf.clear()
            if not source.strip(): continue

            self._history.append(source.replace("\n", " "))
            self._last_src = source

            result, err, ms = self._eval_expr(source)

            if err:
                print(RED(f"  ✗ {err}"))
            else:
                fmt = self._fmt_result(result)
                if fmt: print(fmt)
                if ms > 100: print(DIM(f"  ({ms:.0f}ms)"))
                self._session.append(source)


# ─────────────────────────────────────────────────────────────────────────────
# WEB PLAYGROUND
# ─────────────────────────────────────────────────────────────────────────────

PLAYGROUND_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>InScript Playground</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0d1117;--sf:#161b22;--sf2:#21262d;--bd:#30363d;--tx:#e6edf3;
      --tx2:#8b949e;--tx3:#6e7681;--pr:#58a6ff;--gn:#3fb950;--rd:#f85149;
      --yl:#d29922;--or:#e3b341;--pu:#bc8cff}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
     background:var(--bg);color:var(--tx);height:100vh;display:flex;flex-direction:column;overflow:hidden}
header{padding:7px 16px;background:var(--sf);border-bottom:1px solid var(--bd);
       display:flex;align-items:center;gap:10px;flex-shrink:0}
.logo{font-weight:800;color:var(--pr);font-size:16px}
.logo span{color:var(--tx2);font-weight:400}
.vbadge{background:var(--sf2);border:1px solid var(--bd);color:var(--tx2);
        font-size:10px;padding:1px 7px;border-radius:10px}
.hactions{margin-left:auto;display:flex;gap:7px;align-items:center}
.btn{border:none;padding:5px 13px;border-radius:5px;font-size:12px;
     font-weight:600;cursor:pointer;transition:.15s opacity}
.btn:hover{opacity:.82}
.btn-run{background:var(--gn);color:#0d1117}
.btn-sec{background:var(--sf2);border:1px solid var(--bd);color:var(--tx)}
kbd{background:var(--sf2);border:1px solid var(--bd);border-radius:3px;
    padding:1px 4px;font-size:9px;color:var(--tx2)}
.toolbar{background:var(--sf);border-bottom:1px solid var(--bd);
         padding:4px 16px;display:flex;align-items:center;gap:7px;flex-shrink:0;flex-wrap:wrap}
.tl{font-size:10px;color:var(--tx3);font-weight:600;text-transform:uppercase;
    letter-spacing:.5px;margin-right:2px}
.pill{padding:2px 9px;background:var(--bg);border:1px solid var(--bd);border-radius:11px;
      font-size:11px;cursor:pointer;color:var(--tx2);transition:.15s all;white-space:nowrap}
.pill:hover,.pill.on{border-color:var(--pr);color:var(--pr);background:rgba(88,166,255,.08)}
.tsep{width:1px;height:16px;background:var(--bd);margin:0 3px}
.mtog{display:flex;background:var(--bg);border:1px solid var(--bd);border-radius:5px;overflow:hidden}
.mbtn{padding:2px 9px;font-size:10px;cursor:pointer;color:var(--tx2);border:none;background:none;font-weight:600}
.mbtn.on{background:var(--pr);color:#0d1117;font-weight:700}
main{flex:1;display:grid;grid-template-columns:1fr 1fr;overflow:hidden}
.pane{display:flex;flex-direction:column;overflow:hidden}
.ph{padding:5px 13px;background:var(--sf);border-bottom:1px solid var(--bd);
    font-size:10px;font-weight:600;color:var(--tx2);text-transform:uppercase;
    letter-spacing:.5px;display:flex;align-items:center;gap:7px;flex-shrink:0}
.dots{display:flex;gap:4px}
.dot{width:9px;height:9px;border-radius:50%}
#editor{flex:1;border:none;resize:none;background:#0d1117;color:#e6edf3;
        padding:14px;font-family:"Cascadia Code","Fira Code","JetBrains Mono","SF Mono",monospace;
        font-size:13px;line-height:1.75;outline:none;border-right:1px solid var(--bd);
        tab-size:4;-moz-tab-size:4}
#editor::selection{background:rgba(88,166,255,.25)}
#outwrap{flex:1;overflow-y:auto;background:#0a0e14;padding:13px 15px}
#outwrap::-webkit-scrollbar{width:4px}
#outwrap::-webkit-scrollbar-thumb{background:var(--bd);border-radius:2px}
.ol{color:var(--tx);font-family:monospace;font-size:12.5px;line-height:1.75;white-space:pre-wrap;word-break:break-all}
.oe{color:var(--rd);font-family:monospace;font-size:12.5px;line-height:1.75;white-space:pre-wrap}
.ok{color:var(--gn);font-family:monospace;font-size:12.5px;line-height:1.75}
.om{color:var(--tx3);font-size:10px;margin-top:3px;font-family:monospace}
.sep{border:none;border-top:1px solid var(--bd);margin:6px 0}
.spin{display:inline-block;width:10px;height:10px;border:2px solid var(--bd);
      border-top-color:var(--pr);border-radius:50%;animation:sp .7s linear infinite;
      margin-right:5px;vertical-align:middle}
@keyframes sp{to{transform:rotate(360deg)}}
.sb{background:var(--sf);border-top:1px solid var(--bd);padding:2px 16px;
    display:flex;gap:14px;font-size:10px;color:var(--tx3);flex-shrink:0}
.si{display:flex;align-items:center;gap:3px}
.s-ok{color:var(--gn)}.s-er{color:var(--rd)}.s-ac{color:var(--pr)}
</style>
</head>
<body>
<header>
  <div class="logo">&#127918; InScript <span>Playground</span></div>
  <span class="vbadge">v1.0.5</span>
  <div class="hactions">
    <button class="btn btn-sec" onclick="shareCode()">&#128279; Share</button>
    <button class="btn btn-sec" onclick="clearOutput()">Clear</button>
    <button class="btn btn-run" onclick="runCode()">&#9654; Run&nbsp;&nbsp;<kbd>Ctrl+&#8629;</kbd></button>
  </div>
</header>
<div class="toolbar">
  <span class="tl">Examples</span>
  <button class="pill on" id="ex-fibonacci" onclick="loadEx('fibonacci')">Fibonacci</button>
  <button class="pill" id="ex-hello"     onclick="loadEx('hello')">Hello</button>
  <button class="pill" id="ex-fizzbuzz"  onclick="loadEx('fizzbuzz')">FizzBuzz</button>
  <button class="pill" id="ex-struct"    onclick="loadEx('struct')">Structs</button>
  <button class="pill" id="ex-closure"   onclick="loadEx('closure')">Closures</button>
  <button class="pill" id="ex-match"     onclick="loadEx('match')">Match</button>
  <button class="pill" id="ex-error"     onclick="loadEx('error')">Try/Catch</button>
  <button class="pill" id="ex-game"      onclick="loadEx('game')">Game Loop</button>
  <div class="tsep"></div>
  <span class="tl">Mode</span>
  <div class="mtog">
    <button class="mbtn on" id="m-interp" onclick="setMode('interp')">Interpreter</button>
    <button class="mbtn"    id="m-vm"     onclick="setMode('vm')">VM</button>
  </div>
</div>
<main>
  <div class="pane">
    <div class="ph">
      <div class="dots">
        <div class="dot" style="background:#f85149"></div>
        <div class="dot" style="background:#d29922"></div>
        <div class="dot" style="background:#3fb950"></div>
      </div>
      Editor &mdash; InScript
    </div>
    <textarea id="editor" spellcheck="false" placeholder="// Write InScript here&hellip;"></textarea>
  </div>
  <div class="pane">
    <div class="ph"><div class="dot" style="background:var(--pr)"></div>Output</div>
    <div id="outwrap"><div class="ok">Ready. Press &#9654; Run or Ctrl+Enter.</div></div>
  </div>
</main>
<div class="sb">
  <span class="si" id="st-mode">Mode: <span class="s-ac">Interpreter</span></span>
  <span class="si" id="st-res"></span>
  <span style="flex:1"></span>
  <span class="si">InScript v1.0.5</span>
</div>
<script>
const EX = {
  fibonacci:`// Fibonacci — recursion vs iteration
fn fib_rec(n: int) -> int {
    if n <= 1 { return n }
    return fib_rec(n - 1) + fib_rec(n - 2)
}
fn fib_iter(n: int) -> int {
    let a = 0; let b = 1
    for _ in range(n) { let t = a + b; a = b; b = t }
    return a
}
for i in range(10) {
    print("fib(" + i + ") = " + fib_rec(i) + "  (iter: " + fib_iter(i) + ")")
}`,
  hello:`// Hello, InScript!
let name = "World"
print("Hello, " + name + "!")
let x: int = 42
let pi: float = 3.14159
let arr: int[] = [1, 2, 3, 4, 5]
print("x =", x, "  pi =", pi)
print("arr =", arr, "  sum =", sum(arr))`,
  fizzbuzz:`// Classic FizzBuzz
for i in range(1, 31) {
    if      i % 15 == 0 { print("FizzBuzz") }
    else if i % 3  == 0 { print("Fizz") }
    else if i % 5  == 0 { print("Buzz") }
    else                 { print(i) }
}`,
  struct:`// Structs with operator overloading
struct Vector2 {
    x: float
    y: float
    fn length() -> float { return sqrt(self.x*self.x + self.y*self.y) }
    fn to_string() -> string { return "(" + self.x + ", " + self.y + ")" }
    operator + (rhs) { return Vector2 { x: self.x+rhs.x, y: self.y+rhs.y } }
    operator == (rhs) { return self.x == rhs.x && self.y == rhs.y }
}
let a = Vector2 { x: 3.0, y: 4.0 }
let b = Vector2 { x: 1.0, y: 2.0 }
let c = a + b
print("a =", a.to_string(), "  |a| =", a.length())
print("c = a+b =", c.to_string())
print("a == b:", a == b)`,
  closure:`// Closures, pipes and higher-order functions
fn make_counter(start: int) {
    let count = start
    return fn() { count += 1; return count }
}
let c1 = make_counter(0); let c2 = make_counter(10)
print(c1(), c1(), c1())
print(c2(), c2())
fn double(x) { return x * 2 }
fn add_ten(x) { return x + 10 }
let result = 5 |> double |> add_ten
print("5 |> double |> add_ten =", result)
let evens   = filter([1,2,3,4,5,6,7,8,9,10], fn(x) { return x % 2 == 0 })
let squares = map(evens, fn(x) { return x * x })
print("even squares:", squares)`,
  match:`// Match + enums
enum Shape { Circle Rectangle Triangle }
fn describe(s) -> string {
    match s {
        case Shape.Circle    { return "a circle" }
        case Shape.Rectangle { return "a rectangle" }
        case Shape.Triangle  { return "a triangle" }
    }
    return "unknown"
}
let shapes = [Shape.Circle, Shape.Rectangle, Shape.Triangle]
for s in shapes { print("Shape is", describe(s)) }`,
  error:`// Try / catch / finally
fn divide(a: float, b: float) -> float {
    if b == 0.0 { throw "Division by zero!" }
    return a / b
}
fn safe_div(a: float, b: float) -> float {
    try {
        return divide(a, b)
    } catch err: string {
        print("Caught:", err)
        return 0.0
    } finally {
        print("(finally runs)")
    }
}
print(safe_div(10.0, 2.0))
print(safe_div(10.0, 0.0))`,
  game:`// Mini game loop
struct Player {
    x: float=400.0; y: float=300.0; speed: float=180.0
    health: int=100; score: int=0
    fn move(dx: float, dy: float, dt: float) {
        self.x += dx*self.speed*dt; self.y += dy*self.speed*dt
    }
    fn take_damage(d: int) { self.health -= d; if self.health<0{self.health=0} }
    fn is_alive() -> bool { return self.health > 0 }
    fn status() -> string {
        return "Player@(" + int(self.x) + "," + int(self.y) +
               ") HP:" + self.health + " Score:" + self.score
    }
}
let p = Player{}; let dt = 0.016
for frame in range(8) {
    p.move(1.0, 0.5, dt)
    if frame % 3 == 2 { p.take_damage(12) }
    p.score += 10
    print("Frame", frame+1, "--", p.status())
    if !p.is_alive() { print("GAME OVER"); break }
}`
};

let mode = 'interp';
function setMode(m){
  mode=m;
  document.getElementById('m-interp').classList.toggle('on',m==='interp');
  document.getElementById('m-vm').classList.toggle('on',m==='vm');
  document.getElementById('st-mode').innerHTML=
    'Mode: <span class="s-ac">'+(m==='vm'?'VM (bytecode)':'Interpreter')+'</span>';
}
function loadEx(name){
  document.getElementById('editor').value=EX[name]||'';
  document.querySelectorAll('.pill').forEach(b=>b.classList.remove('on'));
  const b=document.getElementById('ex-'+name);if(b)b.classList.add('on');
  document.getElementById('outwrap').innerHTML='<div class="ok">Example loaded: '+name+'</div>';
  document.getElementById('st-res').textContent='';
}
function clearOutput(){
  document.getElementById('outwrap').innerHTML='';
  document.getElementById('st-res').textContent='';
}
document.addEventListener('DOMContentLoaded',()=>{
  const ed=document.getElementById('editor');
  ed.addEventListener('keydown',e=>{
    if(e.key==='Tab'){e.preventDefault();
      const s=ed.selectionStart,end=ed.selectionEnd;
      ed.value=ed.value.substring(0,s)+'    '+ed.value.substring(end);
      ed.selectionStart=ed.selectionEnd=s+4;}
  });
});
async function runCode(){
  const code=document.getElementById('editor').value.trim();
  if(!code)return;
  const out=document.getElementById('outwrap');
  out.innerHTML='<div class="om"><span class="spin"></span>Running&hellip;</div>';
  const t0=performance.now();
  try{
    const r=await fetch('/run',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({source:code,mode:mode})});
    const data=await r.json();
    const ms=(performance.now()-t0).toFixed(1);
    out.innerHTML='';
    (data.output||[]).forEach(ln=>{
      const d=document.createElement('div');d.className='ol';d.textContent=ln;out.appendChild(d);});
    if((data.errors||[]).length){
      if((data.output||[]).length){const s=document.createElement('hr');s.className='sep';out.appendChild(s);}
      data.errors.forEach(e=>{
        const d=document.createElement('div');d.className='oe';d.textContent='✗ '+e;out.appendChild(d);});
      document.getElementById('st-res').innerHTML='<span class="s-er">Error</span>';
    }else if(!(data.output||[]).length){
      const d=document.createElement('div');d.className='ok';d.textContent='(no output)';out.appendChild(d);
      document.getElementById('st-res').innerHTML='<span class="s-ok">OK</span>';
    }else{
      document.getElementById('st-res').innerHTML='<span class="s-ok">OK</span>';
    }
    const td=document.createElement('div');td.className='om';td.textContent='Ran in '+ms+'ms';out.appendChild(td);
    out.scrollTop=out.scrollHeight;
  }catch(e){out.innerHTML='<div class="oe">Server error: '+e.message+'</div>';}
}
function shareCode(){
  const code=document.getElementById('editor').value;
  const url=location.origin+'/?code='+btoa(encodeURIComponent(code));
  navigator.clipboard.writeText(url).then(()=>{
    document.getElementById('st-res').innerHTML='<span class="s-ac">Share URL copied!</span>';
    setTimeout(()=>document.getElementById('st-res').textContent='',3000);
  });
}
const params=new URLSearchParams(location.search);
if(params.has('code')){
  try{document.getElementById('editor').value=decodeURIComponent(atob(params.get('code')));
      document.querySelectorAll('.pill').forEach(b=>b.classList.remove('on'));}catch{}
}else{loadEx('fibonacci');}
document.addEventListener('keydown',e=>{
  if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();runCode();}
});
</script>
</body>
</html>"""


def run_playground(port: int = 8080):
    """Launch the web playground in the browser."""
    import webbrowser, json, io as _io
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(PLAYGROUND_HTML.encode())

        def do_POST(self):
            if self.path != "/run":
                self.send_response(404); self.end_headers(); return
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length))
            source = body.get("source", "")
            mode   = body.get("mode", "interp")

            output = []; errors = []
            buf = _io.StringIO()
            orig = sys.stdout
            sys.stdout = buf
            try:
                from lexer import Lexer
                from parser import Parser
                from interpreter import Interpreter
                from errors import InScriptError

                tokens  = Lexer(source).tokenize()
                program = Parser(tokens).parse()
                if mode == "vm":
                    from compiler import Compiler
                    from vm import VM
                    VM().run(Compiler().compile(program))
                else:
                    Interpreter().execute(program)
            except Exception as e:
                errors = [str(e)]
            finally:
                sys.stdout = orig

            output = [ln for ln in buf.getvalue().splitlines()]
            resp = json.dumps({"output": output, "errors": errors}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(resp))
            self.end_headers()
            self.wfile.write(resp)

    url = f"http://localhost:{port}"
    print(f"InScript Playground → {url}")
    print(f"Press Ctrl+C to stop")
    webbrowser.open(url)
    try:
        HTTPServer(("", port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nPlayground stopped.")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    import argparse
    p = argparse.ArgumentParser(description=f"InScript v{VERSION} REPL + Playground")
    p.add_argument("--web",  action="store_true", help="Launch web playground")
    p.add_argument("--port", type=int, default=8080, help="Playground port (default: 8080)")
    p.add_argument("--vm",   action="store_true", help="Start in VM execution mode")
    args = p.parse_args()
    if args.web:
        run_playground(args.port)
    else:
        repl = EnhancedREPL()
        if args.vm: repl._use_vm = True
        repl.run()

if __name__ == "__main__":
    main()
