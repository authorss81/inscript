# InScript Language Roadmap — Detailed

> **Current version:** v1.0.18 (April 2026)
> **Tests:** 839 total (145 VM + 32 operators + 54 audit + 335 comprehensive + 273 core) — all passing
> **Stdlib:** 59 modules
> **Audit score:** 8.8/10
> **Assessment:** Language feature-complete. VM at full parity. Pre-stable: missing formatter, PyPI v1.x, docs site.

---

## ✅ Completed — v1.0.0 through v1.0.18

### Core Language — ALL DONE ✅
- [x] `let` / `const` with type annotations and inference
- [x] All primitive types: `int` `float` `string` `bool` `nil`
- [x] All operators: arithmetic, bitwise, comparison, logical, `in`/`not in`, `|>`, `??`, `?.`
- [x] String concat `++`, array concat `++`
- [x] Float division by zero → `Infinity`; int/0 throws
- [x] Functions: defaults, named args, variadics `*args`, closures
- [x] Arrow function `fn(x) => x*2` — PENDING v1.0.19
- [x] Structs: inheritance, mixins, interfaces, operator overloading
- [x] `priv`/`pub` field access control (VM + interpreter, `_current_self` tracking)
- [x] `super` keyword (VM + interpreter)
- [x] Static fields and methods on structs (VM + interpreter)
- [x] Generic structs `struct Stack<T>` (syntax only)
- [x] ADT Enums with data fields: `enum Shape { Circle(r: float) }`
- [x] Pattern matching: guards, ADT bindings, ranges `case 1..=5`, Ok/Err, binding
- [x] Non-exhaustive match warning
- [x] Array/tuple/struct destructuring
- [x] Array comprehensions, dict comprehensions
- [x] Generators `fn*` / `yield`
- [x] Decorators `@name` (VM + interpreter, local binding updated)
- [x] Error propagation `?` with `Ok` / `Err` / `Result`
- [x] `try/catch/finally` as expression
- [x] Typed catch `catch e:int`
- [x] `assert` / `panic` / `unreachable` — catch gets message directly
- [x] `do-while`, `for-else`, `while-else`, labeled `break`/`continue`
- [x] Multi-variable for `for k,v in entries(d)`
- [x] Range `0..5` / `0..=5` / `range(start,end,step)`
- [x] F-strings with format specs, ternaries, dict key access
- [x] `comptime{}` block — variables leak to outer scope
- [x] `type ID = int` type aliases
- [x] `int?` nullable type annotations
- [x] `int|string` union type annotations

### Type System — ALL DONE ✅
- [x] `typeof(v)` returns clean names
- [x] `x is T` type check
- [x] `x as T` cast
- [x] Type mismatch warns in REPL (literals at call sites)
- [x] Missing return in typed functions warns
- [x] Arg-count mismatch warns

### Array Methods — ALL DONE ✅ (50+)
Core, functional, FP extras, ordering, slicing, set-like, query, structural.
**v1.0.17 additions:** `take_while` `drop_while` `window` `partition` `none` `index_where` `last_where`

### String Methods — ALL DONE ✅ (35+)
Case, trim, search, transform, pad, extract, convert, check, format.
**v1.0.18 additions:** `is_upper` `is_lower` `swapcase` `is_space` `is_digit` `zfill`

### Dict Methods — ALL DONE ✅ (25+)
Including `filter(fn)` `map_values(fn)` `map_keys(fn)` `each(fn)` `any_value` `all_values` `count_values`

### VM (Bytecode Engine) — ALL DONE ✅
- [x] Full parity with interpreter
- [x] `match` as expression, `try` as expression
- [x] ADT patterns, range patterns, match guards + ADT bindings (v1.0.15-17)
- [x] Decorators compile correctly — local variable updated after wrapping (v1.0.16)
- [x] `priv` field enforcement with `_current_self` tracking (v1.0.16)
- [x] `super.method()` working (v1.0.15)
- [x] `try-finally` (v1.0.15)
- [x] Static fields and methods (v1.0.13)
- [x] Variadic `fn(*args)` (v1.0.13)
- [x] Mixin expansion in compiler (v1.0.18)
- [x] `throw struct` — catch binds actual struct (v1.0.14)
- [x] `arr ++ arr` concat (v1.0.14)
- [x] `1.0/0.0 = Infinity` (v1.0.13)
- [x] All dict/string methods via `_do_method` fallback (v1.0.13-14)

### Standard Library — ALL DONE ✅
59 modules across Core, Data, Format/Iter, Net/Crypto, FS/Process, Date/Collections,
Threading/Bench, Game Visual, Game IO, Game World, Game Systems, Utilities.

### Tooling — PARTIALLY DONE
- [x] Enhanced REPL — pixel-art banner, 30+ commands, tab completion, history
- [x] `.doc <module>` — live docs for all 59 modules
- [x] LSP server + VS Code extension
- [x] Bytecode `.ibc` save/load
- [x] `inscript check` — static analysis
- [x] Web playground (basic, in repl.py `--web`)
- [ ] `inscript fmt` — formatter (v1.0.19)
- [ ] `inscript --watch` — watch mode (v1.0.20)
- [ ] `inscript test` — `.ins` test runner (v1.0.21)
- [ ] `pyproject.toml` + PyPI v1.x release (v1.0.22)
- [ ] Docs site (v1.0.23)

---

## 🔧 v1.0.19 — Formatter + Arrow Functions + Rest Destructuring

**Goal:** Polish + missing syntax. 1–2 sessions.

### `inscript fmt` — Token-based formatter
- [ ] `inscript fmt file.ins` — formats in place
- [ ] `inscript fmt --check file.ins` — exits 1 if not formatted (for CI)
- [ ] `inscript fmt --dry-run` — print without writing
- [ ] Rules: 2-space indent, spaces around operators, trailing newline
- [ ] Max line length 100 (break long fn signatures)
- [ ] Trailing comma in multi-line arrays/dicts/params
- [ ] Implementation: ~250 lines using existing `Lexer` token stream

### Arrow function syntax `=>`
- [ ] `let f = fn(x) => x*2` — single expression, no braces needed
- [ ] `let f = fn(x, y) => x + y`
- [ ] Works in interpreter and VM
- [ ] Chaining: `[1,2,3].map(fn(x) => x*2).filter(fn(x) => x>2)`

### Rest destructuring `...rest`
- [ ] `let [a, b, ...rest] = [1,2,3,4,5]` → `rest = [3,4,5]`
- [ ] In function params: `fn f(first, ...rest)` (already works as `*args` — add `...` syntax alias)
- [ ] Spread in array literals: `let c = [...a, ...b]`

### Stdlib quick fixes
- [ ] `random.int(min, max)` — fix off-by-one (currently `R.int(1,6)` doesn't always work)
- [ ] `iter.range(start, end, step)` — fix to return list with step correctly
- [ ] `format.number(n)` — add comma-separated thousands (`1234567` → `"1,234,567"`)

---

## 🔧 v1.0.20 — Watch Mode + Test Runner + `inscript run`

**Goal:** Developer workflow tools. 1 session.

### `inscript --watch file.ins`
- [ ] Watch for file changes using `os.stat` polling (no `watchdog` dep — keep it stdlib-only)
- [ ] Clear terminal and rerun on change
- [ ] Show error location with colored output and file:line reference
- [ ] `Ctrl+C` to stop
- [ ] Also watch imported files

### `inscript test`
- [ ] Discovers and runs `test_*.ins` files in current directory
- [ ] Test format: `assert(expr, "message")` — any assert failure = test fail
- [ ] Named tests: `test "addition works" { assert(1+1==2) }`
- [ ] Output: colored pass/fail count, timing per test, total time
- [ ] `--verbose` flag shows all test names
- [ ] Exit code: 0 = all pass, 1 = any fail (CI compatible)

### `inscript run` improvements
- [ ] `inscript run file.ins --vm` — force VM mode
- [ ] `inscript run file.ins --profile` — print per-function timing
- [ ] Better error output: file path + line + source context + caret

---

## 🔧 v1.0.21 — PyPI Release (v1.0.x on PyPI)

**Goal:** `pip install inscript-lang` works. You already have a PyPI account with v0.6 published.

### `pyproject.toml`
- [ ] Replace or augment `setup.py` with `pyproject.toml`
- [ ] Package name: `inscript-lang` (matches your existing PyPI package)
- [ ] Version: `1.0.21`
- [ ] Entry point: `inscript` → `inscript.py:main`
- [ ] Dependencies: `pygame>=2.0` (optional), `pygls>=1.0` (optional)
- [ ] Python: `>=3.10`

### PyPI upload
- [ ] `python -m build` produces wheel + sdist
- [ ] `python -m twine upload dist/*` uploads to PyPI
- [ ] Test: `pip install inscript-lang==1.0.21` in a fresh venv works
- [ ] `inscript --version` prints `InScript 1.0.21`

### Upgrade from v0.6
- [ ] Note in README: "Upgrade from v0.6: `pip install --upgrade inscript-lang`"
- [ ] v0.6 → v1.0 migration guide (one paragraph — syntax is backward compatible)

---

## 🔧 v1.0.22 — Docs Site + Error Pages

**Goal:** All error links in error messages point to real content.

### GitHub Pages docs (authorss81.github.io/inscript)
- [ ] `/` — landing page (already updated with index.html)
- [ ] `/docs/` — language guide (Getting Started, Syntax, Types, Functions, Structs)
- [ ] `/docs/stdlib/` — stdlib reference (auto-generated from `STDLIB_DOCS` in `repl.py`)
- [ ] `/docs/errors/` — error code index
- [ ] `/docs/errors/E0040/` — one page per error code with example + fix
- [ ] Navigation menu, search (just browser Ctrl+F — no JS needed for v1)
- [ ] All written in Markdown, rendered by GitHub Pages (Jekyll or just HTML)

### Error codes covered
- [ ] E0001 — LexerError (unterminated string etc.)
- [ ] E0010 — ParseError
- [ ] E0040 — RuntimeError
- [ ] E0042 — NameError (undefined variable)
- [ ] E0050 — AssertionError
- [ ] E0051 — Panic
- [ ] All codes in `errors.py`

---

## 🔧 v1.0.23 — Web Playground (Pyodide)

**Goal:** Run InScript in the browser — no install needed.

### Implementation
- [ ] Host on `authorss81.github.io/inscript/playground`
- [ ] Use Pyodide (Python in WASM) to run InScript engine in browser
- [ ] Code editor: CodeMirror 6 (MIT, CDN)
- [ ] InScript syntax highlighting via CodeMirror language extension
- [ ] 10 built-in examples (fibonacci, fizzbuzz, sorting, struct demo, game loop)
- [ ] Share button (encode code in URL hash — no backend needed)
- [ ] Runs completely client-side — zero server costs

---

## 📋 v1.1.0 — First Stable Release (Q2 2026)

**Goal:** A developer can use InScript professionally. All tooling complete.
**Gate:** v1.0.19 through v1.0.23 must all be done. Zero breaking changes.

### Checklist (all must be ✅ before tagging v1.1.0)
- [ ] `inscript fmt` working and integrated in VS Code
- [ ] `inscript --watch` working
- [ ] `inscript test` working
- [ ] `pip install inscript-lang` installs current version from PyPI
- [ ] `inscript --version` prints `InScript 1.1.0`
- [ ] All error URLs (`https://docs.inscript.dev/errors/E0040`) return real pages
- [ ] GitHub Pages docs site has Getting Started, Language Guide, Stdlib Reference
- [ ] Web playground running at GitHub Pages URL
- [ ] All 839+ tests still passing
- [ ] README updated for v1.1.0

### What v1.1.0 does NOT change
- Language syntax (frozen — no new features in v1.1.0 itself)
- Standard library API (no breaking changes)
- VM/interpreter behavior
- All 839 existing tests pass unchanged

---

## 🔮 v1.2.0 — Type Safety (Q3 2026)

**Goal:** Add real type enforcement. May include minor breaking changes (announced 2 releases ahead).

- [ ] Generic enforcement: `Stack<int>` rejects non-int at push time
- [ ] Generic constraints: `fn sort<T: Comparable>(arr: [T]) -> [T]`
- [ ] Type narrowing in match arms
- [ ] Recursive types: linked list, tree nodes
- [ ] Type error messages show expected vs actual (not just a warning)
- [ ] `async/await` — wire to asyncio event loop OR formally remove + document
- [ ] `comptime` — restrict to compile-time expressions, error on runtime calls
- [ ] `@value struct Point` — copy-on-assign semantics
- [ ] Interface static methods
- [ ] `mat4` stdlib for 3D math (no NumPy)

---

## 🚀 v1.3.0 — Performance (Q4 2026)

**Goal:** Fast enough for real game loops. 5–15× speedup via C extension.

- [ ] Profile real game loop to find bottlenecks
- [ ] C extension for: env lookup, fn dispatch, integer arithmetic
- [ ] `cffi` or `ctypes` (no compile step for user)
- [ ] Tail call optimization (removes Python 1000-frame limit)
- [ ] Bytecode optimization: constant folding, dead code elimination
- [ ] Standalone binary via `pyinstaller` (one-click distribution)
- [ ] WASM exploration via Pyodide

---

## 🌐 v2.0.0 — Ecosystem (2027)

- [ ] Package registry at `inscript-lang.dev/packages`
- [ ] `inscript publish` / `inscript install <package>`
- [ ] InScript Studio IDE (Electron/Tauri)
- [ ] Godot plugin
- [ ] Native binary output via Cython/Nuitka
- [ ] Full WASM target (games in browser)
- [ ] iOS/Android via WASM + PWA wrapper

---

## Timeline

```
April 2026   v1.0.18   Current — VM complete, 839 tests, audit 8.8/10
             STATUS: Early adopter ready. Missing tooling for general use.

             v1.0.19   fmt + arrow fn + rest destructure + stdlib fixes
             v1.0.20   --watch + inscript test + run improvements
             v1.0.21   pip install inscript-lang (PyPI v1.0.x upgrade from v0.6)
             v1.0.22   docs site + all E0XXX error pages
             v1.0.23   web playground (Pyodide)

Q2 2026      v1.1.0    FIRST STABLE RELEASE
             STATUS: ✅ Ready for professional use

Q3 2026      v1.2.0    Type safety + generic enforcement

Q4 2026      v1.3.0    Performance (5-15× via C extension)

2027         v2.0.0    Ecosystem (registry, Studio IDE, WASM)
```

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| v0.6 | 2025 | **PyPI release** — initial public release on PyPI as `inscript-lang` |
| v1.0.0 | 2026-03-04 | Full language + 18 stdlib + VM + LSP |
| v1.0.1–11 | Mar 2026 | VM parity, 100+ bug fixes, 59 modules, 836 tests |
| v1.0.12 | Mar 2026 | VM arr++arr, throw struct, dict/str methods |
| v1.0.13 | Mar 2026 | VM variadic fn(*args), static fields/methods, int/float methods |
| v1.0.14 | Mar 2026 | VM dict.filter/map_values, str.lines/bytes/title, 1.0/0=Inf |
| v1.0.15 | Mar 2026 | match ranges case 1..=5, VM super, VM try-finally, arr.count(val) |
| v1.0.16 | Mar 2026 | VM @decorator, priv _current_self tracking, VMInstance slots fix |
| v1.0.17 | Apr 2026 | int? nullable, int\|string union, type alias, take_while/drop_while/partition |
| v1.0.18 | Apr 2026 | VM mixin, str.is_upper/lower/swapcase, 839 tests, audit 8.8/10 |
| **v1.0.19** | *next* | fmt, arrow fn =>, rest destructure [...rest], stdlib fixes |
| **v1.0.20** | *next* | --watch, inscript test runner |
| **v1.0.21** | *next* | **PyPI upgrade** — pip install inscript-lang (from v0.6 → v1.x) |
| **v1.0.22** | *next* | docs site + E0XXX error pages |
| **v1.0.23** | *next* | web playground (Pyodide) |
| **v1.1.0** | Q2 2026 | **FIRST STABLE** — all tooling complete |

---

## PyPI Notes

Your package `inscript-lang` exists on PyPI at v0.6.
To upgrade to v1.0.x: update `setup.py` or add `pyproject.toml`, then `twine upload`.
Migration from v0.6 to v1.0: syntax is **fully backward compatible** — no changes needed.

The package name stays `inscript-lang` (not `inscript` — already taken on PyPI by another project).
`pip install inscript-lang` is the install command. The CLI entry point is `inscript`.
