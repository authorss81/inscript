# AGENTS.md — InScript Repository Guide

## Active code location

All real source code, tests, and tools live under **`inscript_package/`**.  
The root-level `inscript/` dir and root `inscript.py` are a legacy v0.2.0 package (uses `.is` extension); do not edit them unless the task explicitly targets the old version.

## Entry point

- **CLI entry**: `inscript_package/inscript.py:main()` — VERSION = `"3.9.6"`
- **Version source**: `inscript.py` line 27 is the single source; `_version.py` reads it dynamically. All Python modules import VERSION from `_version.py`. Current: 3.9.6.5.
- **Package install**: `pip install inscript-lang` → console script `inscript`
- **Direct run**: `python inscript_package/inscript.py file.ins`

## Developer commands (run from `inscript_package/`)

```bash
# Run a file
python inscript.py mygame.ins

# REPL
python inscript.py --repl

# Type-check only
python inscript.py --check file.ins

# Format code
python inscript.py --fmt file.ins

# Format check (CI)
python inscript.py --fmt-check file.ins

# Built-in test runner (for .ins files with #[test])
python inscript.py --test file.ins

# Watch + hot reload
python inscript.py --watch --hot game.ins

# Game mode (bypasses Rust VM fast path, required for scene files)
python inscript.py --game examples/pong.ins
```

## Testing

**Tests are self-registering Python scripts** (not pytest) with `✅`/`❌` output. Run from `inscript_package/`:

```bash
# Core tests (run in CI)
python test_lexer.py
python test_parser.py
python test_analyzer.py
python test_interpreter.py
python test_v12.py

# Extended test suite (run in CI as separate job)
python test_phase6.py
python test_phase7.py
python test_audit.py
python test_comprehensive.py
python test_v120.py

# Phase 7 py_compiler tests
python test_py_compiler.py

# Rust bridge tests
python test_compiler.py
python test_fstring.py
python test_rust_parser.py
python test_rust_pipeline.py
```

Benchmarks:
```bash
python bench_phase7.py      # Phase 7 vs AST walker vs bytecode VM (pong.ins)
python bench_phase6.py      # Legacy Phase 6 benchmarks
python bench_lexers.py      # Python lexer vs Rust lexer throughput
python bench_pipeline.py    # End-to-end pipeline throughput
```

## Execution paths

### Path A (tree-walk interpreter) — REPL, most tests, fallback
`analyzer.py` → `interpreter.py`

### Path B (Python bytecode VM) — `.ibc` files, `--compile`
`compiler.py` → `vm.py`. Not used in game loop (see Path E).

### Path C (Rust compiler + VM via PyO3) — standalone `.ins` scripts
`inscript_rust_parser/` (lexer, parser, compiler) → `rust_vm_engine/` (VM).  
Default for `python inscript.py file.ins`. Exposed as `inscript_parser` Python module with functions `lex(source)`, `compile(source)`, `compile_and_run(source)`.

### Path E (Phase 7: Python AST transpilation) — **DEFAULT game engine path**
`py_compiler.py:PyCompiler` converts InScript hook AST → Python `ast.*` → `compile()` → native code object. Runs hooks at CPython native speed. **67× faster than AST walker** on pong.ins.

`--rust-vm` flag exists but is **dead code** — game hooks always use Phase 7 regardless.

## Phase 7: Python AST transpilation

### Scene state model
All scene variables (`let` declarations) are stored in a shared `state` dict. The compiled function signature is `__hook(state, dt=None)`:
- Writes: `state["ball_x"] = 5` (STORE_SUBSCR)
- Reads: `state["ball_x"]` (BINARY_SUBSCR)
- Game namespaces (`draw`, `screen`, etc.) are Python globals (LOAD_GLOBAL)
- Hook params (`dt`) are Python locals (LOAD_FAST)

### Key files
- `py_compiler.py` — `PyCompiler` class + `compile_hook()`. Converts InScript AST to Python `ast.*`. Returns `None` on failure (caller falls back to AST walker).
- `pygame_backend.py:run_hook_phase7()` — Three-path router: py_compiler → AST walker fallback. State sync via `_sync_state_to_env()`.
- `pygame_backend.py:BatchedDrawNamespace` — Sprite calls batched via `Surface.blits()`, non-sprite calls pass through directly.

### Benchmark results (pong.ins, N=5000/1000)

| Path | on_update | on_draw | 1000 frames | vs AST |
|------|-----------|---------|-------------|--------|
| AST walker | 37.3 µs | 1061 µs | 980 ms | 1× |
| Bytecode VM | 56.0 µs | 2175 µs | 1772 ms | 0.5× |
| **Py compiled (P7)** | **2.3 µs** | **23.6 µs** | **14.5 ms** | **67×** |

### Compilation fallback
If `compile_hook()` returns `None` (unsupported node type, SyntaxError, etc.), `run_hook_phase7` falls back to the AST tree-walk interpreter. A compiled hook never silently returns wrong results.

### Known compilation gaps (fallback triggers)
- MatchStmt, ForExpr (comprehensions), FunctionDecl, StructDecl, ClassDecl → raise CompileError, fallback used
- F-strings, lambdas → planned for v3.9.6.x microversions

## Rust compiler details (Path C)

- **Lexer**: `inscript_rust_parser/src/lexer.rs` — character-by-character state machine, 85+ token variants
- **Parser**: `inscript_rust_parser/src/parser.rs` — AST building, `parse_fstring_content`
- **Compiler**: `inscript_rust_parser/src/compiler.rs` — AST-to-bytecode, `Vec<OpCode>` + `Vec<Value>`
- **VM**: `rust_vm_engine/src/vm.rs` — `VMEngine::from_opcodes` / `from_opcodes_with_funcs`
- **Optimizer**: `rust_vm_engine/src/compiler.rs` — 5 passes (constant fold, instruction fuse, strength reduce, DCE, nop compact)
- **JIT**: `rust_vm_engine/src/jit.rs` — trace-detection stub (backward jumps → execution counting → IR generation). **Never swapped into execution loop** — effectively a no-op.
- **LLVM IR**: `rust_vm_engine/src/ir.rs` — all 37 opcodes supported. Uses **tagged `i64`** (16-bit type tag), not native types.
- **Native compilation**: `rust_vm_engine/src/compile.rs` — writes .ll → opt + llc + cc → libloading. Requires `llc` + `opt` (LLVM 17) + `cc` in PATH.

### Rust known issues
- `OpCode::from_byte()` cannot decode parameterized opcodes; `from_opcodes` bypasses this
- `Value::String`'s `Display` impl wraps in quotes; use `to_display_string()` for raw output
- `to_byte()` maps all parameterized opcodes to `0xFE`; serialization via `from_opcodes` only
- `compile.rs` native compilation requires `llc` + `opt` (LLVM 17) + `cc` in PATH

### Build Rust extension
```bash
cd inscript_package
cargo build --release -p inscript-parser
Copy-Item target/release/inscript_parser.dll target/release/inscript_parser.pyd -Force
```

## Profiling

`--profile` flag adds per-frame timing for `on_update` and `on_draw` hooks using `time.perf_counter()`. Summary printed on exit: avg/min/max per-hook ms + call count.

## Language conventions

- File extension: `.ins`
- Comments: `#` only (not `//` — that's floor division)
- Null: `nil` (not `null`; `null` raises E0055 since v1.7.4)
- CLI flags use `--` (e.g. `--repl`, `--check`, `--fmt`)

## Version bump procedure

1. Edit VERSION in `inscript_package/inscript.py` (line 27, `VERSION = "x.y.z"`)
2. Run `python tools/sync_versions.py` to patch Cargo.toml, package.json, README badges
3. Update ROADME.md (version badge, current version)

## Publishing to PyPI

```bash
# Tag and push to trigger publish workflow
git tag -a v3.9.6 -m "InScript v3.9.6"
git push origin v3.9.6
```

The workflow at `.github/workflows/publish.yml`:
1. Installs Rust toolchain + setuptools-rust
2. Builds the Rust `inscript_parser` extension via `cargo build --release -p inscript-parser`
3. Runs the full test suite (Python + Rust tests)
4. Builds wheel/sdist with `python -m build`
5. Uploads to PyPI via `pypa/gh-action-pypi-publish`

**Pre-requisite**: `PYPI_API_TOKEN` secret must be set in GitHub repo settings.

## Important notes

- Tests **must be run from `inscript_package/`** — they use `sys.path.insert(0, os.path.dirname(__file__))`
- Optional deps: `pygame` (game features), `pygls` (LSP server, pin to 1.x: `pip install "pygls<2"`)
- Legacy root-level files (`inscript.py`, `inscript/`, `tests/test_interpreter.py`) are the old v0.2.0 interpreter and shouldn't be modified
- No Python linter/formatter config — just Python 3.10+ is required
- Full architecture: `inscript_package/ARCHITECTURE.md`
- Production roadmap: `ROADMAP.md` (v3.9.6.x microversion plan through v3.10.0)
