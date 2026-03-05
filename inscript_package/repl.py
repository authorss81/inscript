# inscript/repl.py  —  Phase 28: Enhanced REPL + Playground
#
# Features beyond the basic REPL in inscript.py:
#   • Tab-completion for keywords, built-ins, user-defined symbols
#   • Persistent history across sessions (~/.inscript/history)
#   • Multi-line smart detection (auto-continues on open braces)
#   • Syntax highlighting in terminal (ANSI colours)
#   • .help  .vars  .fns  .clear  .save  .load  .time  .bytecode commands
#   • Session recording: .save session.ins writes current session to file
#   • :time expression  — measure execution time
#   • Web playground server: python -m inscript.repl --web [--port 8080]
#
# Usage:
#   python -m inscript.repl              # enhanced terminal REPL
#   python -m inscript.repl --web        # open browser playground
#   python -m inscript.repl --web --port 8080

from __future__ import annotations
import os, sys, json, time, readline, atexit, textwrap
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent))

HISTORY_FILE = Path.home() / ".inscript" / "history"
HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

# ── ANSI colours ─────────────────────────────────────────────────────────────
def _c(code: str, text: str) -> str:
    if not sys.stdout.isatty(): return text
    return f"\033[{code}m{text}\033[0m"

CYAN    = lambda t: _c("36",   t)
GREEN   = lambda t: _c("32",   t)
YELLOW  = lambda t: _c("33",   t)
MAGENTA = lambda t: _c("35",   t)
RED     = lambda t: _c("31",   t)
BOLD    = lambda t: _c("1",    t)
DIM     = lambda t: _c("2",    t)
BLUE    = lambda t: _c("34",   t)

BANNER = f"""
{BOLD(CYAN('  ___       ____            _       _   '))}
{BOLD(CYAN(' |_ _|_ __ / ___|  ___ _ __(_)_ __ | |_ '))}
{BOLD(CYAN('  | || `_ \\\\___ \\ / __| `__| | `_ \\| __|'))}
{BOLD(CYAN('  | || | | |___) | (__| |  | | |_) | |_ '))}
{BOLD(CYAN(' |___|_| |_|____/ \\___|_|  |_| .__/ \\__|'))}
{BOLD(CYAN('                             |_|        '))}
  {GREEN('InScript v1.0.0')} — Interactive Shell
  Type {YELLOW('.help')} for commands, {YELLOW('exit')} to quit
"""

HELP_TEXT = f"""
{BOLD('REPL Commands:')}
  {YELLOW('.help')}              Show this help
  {YELLOW('.vars')}              List all defined variables
  {YELLOW('.fns')}               List all defined functions
  {YELLOW('.types')}             List all defined structs
  {YELLOW('.clear')}             Clear session (reset all variables)
  {YELLOW('.save')} <file>       Save session to .ins file
  {YELLOW('.load')} <file>       Load and run a .ins file
  {YELLOW('.time')} <expr>       Measure execution time of expression
  {YELLOW('.bytecode')}          Show bytecode for last expression
  {YELLOW('.history')}           Show command history
  {YELLOW('.reset')}             Full reset (interpreter + history)
  {YELLOW('.type')} <expr>       Show the type of an expression
  {YELLOW('.modules')}           List all importable stdlib modules
  {YELLOW('.packages')}          List installed packages
  {YELLOW('exit')} / {YELLOW('quit')}       Exit the REPL

{BOLD('Keyboard shortcuts:')}
  {YELLOW('↑ / ↓')}             Navigate history
  {YELLOW('Tab')}               Auto-complete
  {YELLOW('Ctrl+C')}            Cancel current input
  {YELLOW('Ctrl+D')}            Exit

{BOLD('Multi-line input:')}
  Open a brace {{'}} and press Enter — REPL continues until balanced
  Or end a line with \\ to continue on next line

{BOLD('Examples:')}
  >>> let x = 42
  >>> fn square(n) {{ return n * n }}
  >>> square(x)
    → 1764
  >>> for i in range(5) {{
  ...     print(i * i)
  ... }}
"""

KEYWORDS = [
    # Control flow
    "let","const","fn","struct","enum","interface","mixin","impl","extends",
    "implements","if","else","while","for","in","return","break","continue",
    "match","case","import","from","export","async","await","yield",
    "try","catch","throw","abstract","select","true","false","nil","self",
    # Built-in functions
    "print","len","string","int","float","bool","typeof","range",
    "push","pop","contains","sort","reverse","map","filter","reduce",
    "zip","enumerate","flatten","unique","chunk","take","skip",
    "sum","min","max","abs","sqrt","floor","ceil","round","pow",
    "split","join","trim","upper","lower","replace","starts_with","ends_with",
    "substring","char_code","from_code","parse_int","parse_float",
    "has_key","keys","values","entries","delete","merge",
    "is_nil","is_int","is_float","is_str","is_bool","is_array","is_dict",
    "Ok","Err","thread","chan_send","chan_recv","sleep","implements","fields_of",
]

STDLIB_MODULES = [
    "math","string","array","io","json","random","time","color","tween",
    "grid","events","debug","http","path","regex","csv","uuid","crypto",
]


# ─────────────────────────────────────────────────────────────────────────────
# SYNTAX HIGHLIGHTER (terminal)
# ─────────────────────────────────────────────────────────────────────────────

import re as _re

_KW_RE  = _re.compile(r'\b(let|const|fn|struct|scene|ai|state|if|else|while|for|in|return|break|continue|match|true|false|null|self)\b')
_NUM_RE = _re.compile(r'\b\d+\.?\d*\b')
_STR_RE = _re.compile(r'"[^"]*"')
_CMT_RE = _re.compile(r'//.*$')
_FN_RE  = _re.compile(r'\b([a-z_]\w*)\s*(?=\()')
_TY_RE  = _re.compile(r'\b([A-Z]\w*)\b')

def highlight(line: str) -> str:
    if not sys.stdout.isatty(): return line
    result = line
    # Order matters: strings first, then comments
    result = _STR_RE.sub(lambda m: GREEN(m.group()), result)
    result = _CMT_RE.sub(lambda m: DIM(m.group()), result)
    result = _KW_RE.sub(lambda m: CYAN(m.group()), result)
    result = _NUM_RE.sub(lambda m: MAGENTA(m.group()), result)
    result = _TY_RE.sub(lambda m: YELLOW(m.group()), result)
    result = _FN_RE.sub(lambda m: BLUE(m.group(1)), result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# TAB COMPLETER
# ─────────────────────────────────────────────────────────────────────────────

class InScriptCompleter:
    def __init__(self, interpreter):
        self._interp = interpreter
        self._matches: List[str] = []

    def _candidates(self) -> List[str]:
        candidates = list(KEYWORDS)
        # Add user symbols from interpreter environment
        try:
            env_vars = list(self._interp._env._vars.keys())
            candidates += [k for k in env_vars if not k.startswith("_")]
        except: pass
        return sorted(set(candidates))

    def complete(self, text: str, state: int) -> Optional[str]:
        if state == 0:
            self._matches = [c for c in self._candidates() if c.startswith(text)]
        try:
            return self._matches[state]
        except IndexError:
            return None


# ─────────────────────────────────────────────────────────────────────────────
# ENHANCED REPL
# ─────────────────────────────────────────────────────────────────────────────

class EnhancedREPL:

    def __init__(self):
        from interpreter import Interpreter
        self._interp   = Interpreter()
        self._history: List[str] = []
        self._session:  List[str] = []   # all executed lines for .save
        self._last_src: str = ""
        self._setup_readline()

    def _setup_readline(self):
        completer = InScriptCompleter(self._interp)
        readline.set_completer(completer.complete)
        readline.parse_and_bind("tab: complete")
        readline.set_completer_delims(" \t\n`~!@#$%^&*()-=+[{]}\\|;:'\",<>?/")

        # Load history
        if HISTORY_FILE.exists():
            try: readline.read_history_file(str(HISTORY_FILE))
            except: pass
        atexit.register(lambda: readline.write_history_file(str(HISTORY_FILE)))

    def _eval(self, source: str):
        """Evaluate InScript source, return (result, error, elapsed_ms)."""
        from lexer import Lexer
        from parser import Parser
        from analyzer import Analyzer
        from errors import InScriptError

        t0 = time.perf_counter()
        try:
            tokens  = Lexer(source).tokenize()
            program = Parser(tokens).parse()
            Analyzer(program).analyze()
            result  = self._interp.execute(program)
            elapsed = (time.perf_counter() - t0) * 1000
            return result, None, elapsed
        except InScriptError as e:
            elapsed = (time.perf_counter() - t0) * 1000
            return None, str(e), elapsed
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000
            return None, f"Internal error: {e}", elapsed

    def _format_result(self, val) -> str:
        """Pretty-print a result value."""
        if val is None: return ""
        try:
            from interpreter import _inscript_str
            s = _inscript_str(val)
        except:
            s = repr(val)
        return f"  {DIM('→')} {GREEN(s)}"

    def _is_complete(self, source: str) -> bool:
        """Check if braces/brackets are balanced (for multiline detection)."""
        depth = 0
        in_str = False
        for ch in source:
            if ch == '"' and not in_str: in_str = True
            elif ch == '"' and in_str:   in_str = False
            elif not in_str:
                if ch in "{[(": depth += 1
                elif ch in "}])": depth -= 1
        return depth <= 0

    def _handle_command(self, cmd: str) -> bool:
        """Handle dot-commands. Returns True if handled."""
        parts = cmd.strip().split(None, 1)
        if not parts: return False
        command = parts[0].lower()
        arg     = parts[1] if len(parts) > 1 else ""

        if command in (".help", "help"):
            print(HELP_TEXT)

        elif command == ".vars":
            try:
                vars_ = {k: v for k, v in self._interp._env._vars.items()
                         if not k.startswith("_")}
                if not vars_:
                    print(DIM("  (no variables defined)"))
                else:
                    for name, val in sorted(vars_.items()):
                        try:
                            from interpreter import _inscript_str
                            vs = _inscript_str(val)
                        except: vs = repr(val)
                        print(f"  {CYAN(name)} = {GREEN(vs)}")
            except Exception as e:
                print(DIM(f"  (error reading vars: {e})"))

        elif command == ".fns":
            try:
                from stdlib_values import InScriptFunction
                fns = {k: v for k, v in self._interp._env._vars.items()
                       if isinstance(v, InScriptFunction)}
                if not fns:
                    print(DIM("  (no functions defined)"))
                else:
                    for name, fn in sorted(fns.items()):
                        params = ", ".join(getattr(fn, 'params', []))
                        print(f"  {BLUE('fn')} {CYAN(name)}({params})")
            except: print(DIM("  (error reading functions)"))

        elif command == ".clear":
            from interpreter import Interpreter
            self._interp = Interpreter()
            self._session.clear()
            print(DIM("  (session cleared — all variables reset)"))

        elif command == ".save":
            if not arg:
                print(RED("  Usage: .save <filename.ins>"))
            else:
                path = Path(arg)
                path.write_text("\n".join(self._session))
                print(GREEN(f"  Saved {len(self._session)} lines → {path}"))

        elif command == ".load":
            if not arg:
                print(RED("  Usage: .load <filename.ins>"))
            else:
                path = Path(arg)
                if not path.exists():
                    print(RED(f"  File not found: {path}"))
                else:
                    source = path.read_text()
                    print(DIM(f"  Loading {path}…"))
                    result, err, ms = self._eval(source)
                    if err: print(RED(f"  Error: {err}"))
                    else:   print(GREEN(f"  Loaded in {ms:.1f}ms"))

        elif command == ".time":
            if not arg:
                print(RED("  Usage: .time <expression>"))
            else:
                # Run multiple times for accuracy
                times = []
                for _ in range(10):
                    _, _, ms = self._eval(arg)
                    times.append(ms)
                avg = sum(times) / len(times)
                mn  = min(times); mx = max(times)
                print(f"  avg {CYAN(f'{avg:.2f}ms')}  "
                      f"min {GREEN(f'{mn:.2f}ms')}  "
                      f"max {YELLOW(f'{mx:.2f}ms')}  (10 runs)")

        elif command == ".bytecode":
            if not self._last_src:
                print(DIM("  (no expression yet)"))
            else:
                try:
                    from compiler.bytecode import BytecodeCompiler, disassemble_proto
                    proto = BytecodeCompiler().compile_source(self._last_src)
                    print(DIM(disassemble_proto(proto)))
                except Exception as e:
                    print(RED(f"  Bytecode error: {e}"))

        elif command == ".history":
            for i, h in enumerate(self._history[-20:], 1):
                print(f"  {DIM(str(i)):>4}  {h}")

        elif command == ".reset":
            from interpreter import Interpreter
            self._interp = Interpreter()
            self._session.clear()
            self._history.clear()
            readline.clear_history()
            print(DIM("  (full reset)"))

        elif command.startswith(".type"):
            parts = command.split(None, 1)
            if len(parts) < 2:
                print(RED("  Usage: .type <expression>"))
            else:
                expr = parts[1]
                import io as _io, contextlib as _ctx
                buf = _io.StringIO()
                with _ctx.redirect_stdout(buf):
                    try:
                        val = self._interp.execute(f"let __type_tmp__ = {expr}")
                        env_val = self._interp._env.get("__type_tmp__", 0)
                        # Use built-in typeof logic
                        if env_val is None:       tname = "nil"
                        elif isinstance(env_val, bool): tname = "bool"
                        elif isinstance(env_val, int):  tname = "int"
                        elif isinstance(env_val, float):tname = "float"
                        elif isinstance(env_val, str):  tname = "str"
                        elif isinstance(env_val, list): tname = "array"
                        elif isinstance(env_val, dict): tname = env_val.get("_enum","dict") if "_enum" in env_val or "_variant" in env_val else env_val.get("_name", "dict")
                        else: tname = type(env_val).__name__
                        print(YELLOW(f"  type: {tname}"))
                        print(CYAN(f"  value: {env_val}"))
                    except Exception as e:
                        print(RED(f"  Error: {e}"))

        elif command == ".modules":
            mods = [
                "math","string","array","io","json","random","time","color",
                "tween","grid","events","debug","http","path","regex","csv","uuid","crypto"
            ]
            print(BOLD("  Importable stdlib modules:"))
            for i in range(0, len(mods), 4):
                row = mods[i:i+4]
                print("    " + "  ".join(CYAN(m.ljust(10)) for m in row))
            print(f"  Usage: {YELLOW('import "math"')} or {YELLOW('from "math" import sin, cos')}")

        elif command == ".packages":
            import os as _os
            pkg_dir = _os.path.join(_os.path.expanduser("~"), ".inscript", "packages")
            if not _os.path.exists(pkg_dir):
                print(DIM("  No packages installed."))
                print(f"  Install with: {YELLOW('inscript --install <name>')}")
            else:
                pkgs = [d for d in _os.listdir(pkg_dir) if _os.path.isdir(_os.path.join(pkg_dir,d))]
                if not pkgs:
                    print(DIM("  No packages installed."))
                else:
                    print(BOLD(f"  Installed packages ({len(pkgs)}):"))
                    for p in sorted(pkgs):
                        print(f"    • {CYAN(p)}")

        else:
            return False
        return True

    def run(self):
        print(BANNER)
        buf = []

        while True:
            prompt = f"{CYAN('>>>')} " if not buf else f"{DIM('...')} "
            try:
                line = input(prompt)
            except KeyboardInterrupt:
                buf.clear()
                print()
                continue
            except EOFError:
                print(f"\n{DIM('[InScript] Goodbye!')}")
                break

            # Exit commands
            if line.strip() in ("exit", "quit", ".exit", ".quit"):
                print(DIM("[InScript] Goodbye!"))
                break

            # Dot-commands (only at top level)
            if not buf and line.strip().startswith("."):
                if self._handle_command(line.strip()):
                    continue

            # Backslash continuation
            if line.endswith("\\"):
                buf.append(line[:-1])
                continue

            buf.append(line)
            source = "\n".join(buf)

            # Check if we need more input (unbalanced braces)
            if not self._is_complete(source):
                continue

            buf.clear()

            if not source.strip():
                continue

            # Record history
            self._history.append(source.replace("\n", " "))
            self._last_src = source

            # Evaluate
            result, err, ms = self._eval(source)

            if err:
                print(RED(f"  ✗ {err}"))
            else:
                formatted = self._format_result(result)
                if formatted:
                    print(formatted)
                if ms > 100:
                    print(DIM(f"  ({ms:.0f}ms)"))
                self._session.append(source)


# ─────────────────────────────────────────────────────────────────────────────
# WEB PLAYGROUND
# ─────────────────────────────────────────────────────────────────────────────

PLAYGROUND_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>InScript Playground</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0d1117;--surface:#161b22;--border:#30363d;--text:#e6edf3;
      --text2:#8b949e;--primary:#58a6ff;--green:#3fb950;--red:#f85149;--yellow:#d29922}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
     background:var(--bg);color:var(--text);height:100vh;display:flex;flex-direction:column}
header{padding:10px 20px;background:var(--surface);border-bottom:1px solid var(--border);
       display:flex;align-items:center;gap:16px}
.logo{font-weight:700;color:var(--primary);font-size:18px}
.subtitle{color:var(--text2);font-size:13px}
header .spacer{flex:1}
.run-btn{background:var(--green);color:#000;border:none;padding:8px 20px;
         border-radius:6px;font-weight:700;font-size:14px;cursor:pointer}
.run-btn:hover{opacity:.85}
.share-btn{background:var(--surface);border:1px solid var(--border);color:var(--text);
           padding:8px 16px;border-radius:6px;font-size:13px;cursor:pointer}
main{flex:1;display:grid;grid-template-columns:1fr 1fr;gap:0;overflow:hidden}
.pane{display:flex;flex-direction:column}
.pane-header{padding:8px 14px;background:var(--surface);border-bottom:1px solid var(--border);
             font-size:12px;font-weight:600;color:var(--text2);text-transform:uppercase;
             display:flex;align-items:center;gap:8px}
.pane-header .dot{width:8px;height:8px;border-radius:50%}
#editor{flex:1;border:none;resize:none;background:#0d1117;color:#e6edf3;
        padding:16px;font-family:"Cascadia Code","Fira Code","SF Mono",monospace;
        font-size:14px;line-height:1.7;outline:none;border-right:1px solid var(--border)}
#output{flex:1;padding:16px;font-family:monospace;font-size:13px;line-height:1.7;
        overflow-y:auto;background:#0a0e14}
#output::-webkit-scrollbar{width:6px}
#output::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
.out-line{color:var(--text)}
.out-err{color:var(--red)}
.out-ok{color:var(--green)}
.out-time{color:var(--text2);font-size:11px}
.examples{display:flex;gap:8px;padding:8px 14px;background:var(--surface);
          border-top:1px solid var(--border);flex-wrap:wrap}
.ex-btn{padding:4px 12px;background:var(--bg);border:1px solid var(--border);
        border-radius:14px;font-size:12px;cursor:pointer;color:var(--text2)}
.ex-btn:hover{border-color:var(--primary);color:var(--primary)}
.status{padding:4px 14px;font-size:11px;color:var(--text2);background:var(--surface);
        border-top:1px solid var(--border)}
</style>
</head>
<body>
<header>
  <span class="logo">🎮 InScript</span>
  <span class="subtitle">Interactive Playground</span>
  <div class="spacer"></div>
  <button class="share-btn" onclick="shareCode()">🔗 Share</button>
  <button class="run-btn" onclick="runCode()">▶ Run  <kbd style="opacity:.6;font-size:11px">Ctrl+Enter</kbd></button>
</header>
<main>
  <div class="pane">
    <div class="pane-header">
      <span class="dot" style="background:#f85149"></span>
      <span class="dot" style="background:#d29922"></span>
      <span class="dot" style="background:#3fb950"></span>
      &nbsp; Editor — InScript
    </div>
    <textarea id="editor" spellcheck="false" placeholder="// Write InScript here…"></textarea>
    <div class="examples">
      <span style="font-size:11px;color:var(--text2);line-height:28px">Examples:</span>
      <button class="ex-btn" onclick="loadExample(\'hello\')">Hello World</button>
      <button class="ex-btn" onclick="loadExample(\'fibonacci\')">Fibonacci</button>
      <button class="ex-btn" onclick="loadExample(\'fizzbuzz\')">FizzBuzz</button>
      <button class="ex-btn" onclick="loadExample(\'struct\')">Structs</button>
      <button class="ex-btn" onclick="loadExample(\'closure\')">Closures</button>
      <button class="ex-btn" onclick="loadExample(\'game\')">Game Loop</button>
    </div>
  </div>
  <div class="pane">
    <div class="pane-header">
      <span class="dot" style="background:var(--primary)"></span>
      &nbsp; Output
      <button onclick="clearOutput()" style="margin-left:auto;font-size:11px;
        color:var(--text2);background:none;border:none;cursor:pointer">Clear</button>
    </div>
    <div id="output"><div class="out-ok">Ready. Press ▶ Run or Ctrl+Enter.</div></div>
    <div class="status" id="status">InScript v1.0.0 · Python 3.10+</div>
  </div>
</main>

<script>
const EXAMPLES = {
  hello: `// Hello, InScript!
let name = "World"
print("Hello, " + name + "!")

// Variables and types
let x: int   = 42
let pi: float = 3.14159
let flag: bool = true

print("x =", x, "pi =", pi)`,

  fibonacci: `// Fibonacci with recursion
fn fib(n: int) -> int {
    if n <= 1 { return n }
    return fib(n - 1) + fib(n - 2)
}

// Print first 12 Fibonacci numbers
for i in range(12) {
    print("fib(" + i + ") = " + fib(i))
}`,

  fizzbuzz: `// Classic FizzBuzz
for i in range(1, 31) {
    if i % 15 == 0      { print("FizzBuzz") }
    else if i % 3 == 0  { print("Fizz") }
    else if i % 5 == 0  { print("Buzz") }
    else                 { print(i) }
}`,

  struct: `// Structs with methods
struct Vector2 {
    x: float
    y: float

    fn length() -> float {
        return sqrt(self.x * self.x + self.y * self.y)
    }

    fn add(other: Vector2) -> Vector2 {
        return Vector2 { x: self.x + other.x, y: self.y + other.y }
    }

    fn to_string() -> string {
        return "(" + self.x + ", " + self.y + ")"
    }
}

let a = Vector2 { x: 3.0, y: 4.0 }
let b = Vector2 { x: 1.0, y: 2.0 }
let c = a.add(b)

print("a =", a.to_string())
print("b =", b.to_string())
print("a + b =", c.to_string())
print("Length of a:", a.length())`,

  closure: `// Closures and higher-order functions
fn make_counter(start: int) {
    let count = start
    return fn() {
        count += 1
        return count
    }
}

let counter = make_counter(0)
print(counter())   // 1
print(counter())   // 2
print(counter())   // 3

// Map equivalent
fn apply(arr: int[], f) -> int[] {
    let result: int[] = []
    for item in arr {
        result.push(f(item))
    }
    return result
}

let nums = [1, 2, 3, 4, 5]
let doubled = apply(nums, fn(x) { return x * 2 })
print(doubled)`,

  game: `// Mini game loop simulation
struct Player {
    x:      float = 400.0
    y:      float = 300.0
    speed:  float = 180.0
    health: int   = 100
    score:  int   = 0

    fn move(dx: float, dy: float, dt: float) {
        self.x += dx * self.speed * dt
        self.y += dy * self.speed * dt
    }

    fn take_damage(dmg: int) {
        self.health -= dmg
        if self.health < 0 { self.health = 0 }
    }

    fn status() -> string {
        return "Player @ (" + int(self.x) + "," + int(self.y) +
               ") HP:" + self.health + " Score:" + self.score
    }
}

let player = Player {}
let dt = 0.016   // ~60 FPS

// Simulate 5 frames
for frame in range(5) {
    player.move(1.0, 0.5, dt)
    if frame == 2 { player.take_damage(15) }
    player.score += 10
    print("Frame", frame + 1, "—", player.status())
}
print("Game over! Final score:", player.score)`
};

function loadExample(name) {
  document.getElementById("editor").value = EXAMPLES[name] || "";
  setStatus("Example loaded: " + name);
}

function clearOutput() {
  document.getElementById("output").innerHTML = "";
}

function setStatus(msg) {
  document.getElementById("status").textContent = msg;
}

async function runCode() {
  const code = document.getElementById("editor").value;
  const out  = document.getElementById("output");
  out.innerHTML = \'<div class="out-time">Running…</div>\';
  const t0 = performance.now();
  try {
    const resp = await fetch("/run", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({source: code})
    });
    const data = await resp.json();
    const ms   = (performance.now() - t0).toFixed(1);
    out.innerHTML = "";
    if (data.output && data.output.length) {
      data.output.forEach(line => {
        const d = document.createElement("div");
        d.className = "out-line"; d.textContent = line;
        out.appendChild(d);
      });
    }
    if (data.errors && data.errors.length) {
      data.errors.forEach(err => {
        const d = document.createElement("div");
        d.className = "out-err"; d.textContent = "✗ " + err;
        out.appendChild(d);
      });
    }
    if (!data.output?.length && !data.errors?.length) {
      const d = document.createElement("div");
      d.className = "out-ok"; d.textContent = "(no output)";
      out.appendChild(d);
    }
    const td = document.createElement("div");
    td.className = "out-time";
    td.textContent = `Executed in ${ms}ms`;
    out.appendChild(td);
    setStatus(`Done in ${ms}ms · InScript v1.0.0`);
  } catch(e) {
    out.innerHTML = `<div class="out-err">Server error: ${e.message}</div>`;
  }
}

function shareCode() {
  const code = document.getElementById("editor").value;
  const encoded = btoa(encodeURIComponent(code));
  const url = location.origin + "/?code=" + encoded;
  navigator.clipboard.writeText(url).then(() => {
    setStatus("Share URL copied to clipboard!");
  });
}

// Load from URL ?code=
const params = new URLSearchParams(location.search);
if (params.has("code")) {
  try {
    document.getElementById("editor").value = decodeURIComponent(atob(params.get("code")));
  } catch {}
}

// Load default example
if (!document.getElementById("editor").value) {
  loadExample("fibonacci");
}

// Ctrl+Enter to run
document.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault(); runCode();
  }
});
</script>
</body>
</html>'''


def run_playground(port: int = 8080):
    """Launch the web playground in the browser."""
    import webbrowser, json
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

            output = []; errors = []
            try:
                from lexer import Lexer
                from parser import Parser
                from interpreter import Interpreter
                from errors import InScriptError

                interp = Interpreter()
                captured = []
                original_print = interp._env._vars.get("print")

                # Capture print output
                def capture_print(*args):
                    captured.append(" ".join(str(a) for a in args))

                tokens  = Lexer(source).tokenize()
                program = Parser(tokens).parse()
                interp.execute(program)

                # Re-run capturing output (simpler approach)
                import io, contextlib
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    interp2 = Interpreter()
                    interp2.execute(Parser(Lexer(source).tokenize()).parse())
                output = [l for l in buf.getvalue().splitlines() if l is not None]

            except Exception as e:
                errors = [str(e)]

            resp = json.dumps({"output": output, "errors": errors}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(resp))
            self.end_headers()
            self.wfile.write(resp)

    url = f"http://localhost:{port}"
    print(f"✅ InScript Playground running at {url}")
    print(f"   Press Ctrl+C to stop")
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
    p = argparse.ArgumentParser(description="InScript REPL + Playground")
    p.add_argument("--web",  action="store_true", help="Launch web playground")
    p.add_argument("--port", type=int, default=8080, help="Playground port (default: 8080)")
    args = p.parse_args()

    if args.web:
        run_playground(args.port)
    else:
        EnhancedREPL().run()

if __name__ == "__main__":
    main()
