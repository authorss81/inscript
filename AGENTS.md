# AGENTS.md — InScript Repository Guide

## Active code location

All real source code, tests, and tools live under **`inscript_package/`**.  
The root-level `inscript/` dir and root `inscript.py` are a legacy v0.2.0 package (uses `.is` extension); do not edit them unless the task explicitly targets the old version.

## Entry point

- **CLI entry**: `inscript_package/inscript.py:main()` — VERSION = `"3.0.0"`
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

# Built-in test runner
python inscript.py --test file.ins

# Watch + hot reload
python inscript.py --watch --hot game.ins
```

## Testing

**Tests are self-registering Python scripts** (not pytest) with `✅`/`❌` output. Run from `inscript_package/`:

```bash
python test_lexer.py        # 25 tests — tokenization
python test_parser.py       # 49 tests — parsing + AST
python test_analyzer.py     # 35 tests — semantic analysis
python test_interpreter.py  # 122 tests — runtime behavior
python test_stdlib.py       # 45 tests — standard library
python test_v12.py          # 55 tests — stdlib + LSP + channels
python test_py_compiler.py  # Compile + execute all pong.ins hooks via Phase 7
```

CI also runs: `test_phase6.py`, `test_phase7.py`, `test_audit.py`, `test_comprehensive.py`, `test_v120.py`–`test_v300.py` (447+ total).

Benchmarks:
```bash
python bench_phase7.py      # Phase 7 vs AST walker vs bytecode VM (pong.ins)
python bench_phase6.py      # Legacy Phase 6 benchmarks (compile_body, state sync, draw batch)
```

## Architecture (five execution paths)

Paths A & B share the front-end (Python lexer → parser → AST). Path C is the new Rust pipeline. Path D is the Phase 5 game engine path (deprecated by Path E since Phase 7).

- **Path A** (tree-walk): `analyzer.py` → `interpreter.py` — powers REPL and most tests
- **Path B** (bytecode VM): `compiler.py` → `vm.py` — production engine; invoked via `.ibc` files or `--compile`
- **Path C** (Rust compiler + VM): `inscript_rust_parser/` (lexer, parser, compiler) → `rust_vm_engine/` (VM). Exposed via PyO3 as `inscript_parser` Python module. Functions: `lex(source)`, `compile(source)`, `compile_and_run(source)`.
- **Path D** (bytecode VM in game loop, Phase 5/6): `compiler.py:compile_body()` compiles scene hooks to `FnProto` → `vm.py:VM.run()`. **Deprecated** — 0.5x slower than AST walker on real hooks.
- **Path E** (Python AST transpilation, Phase 7): `py_compiler.py:PyCompiler` converts InScript hook AST → Python `ast.*` → `compile()` → native code object. Runs hooks at CPython native speed. **Default game engine path.**

## Phase 7: Python AST transpilation (Path E)

InScript game hooks are transpiled to Python ASTs, compiled to Python code objects via `compile()`, and executed directly. This eliminates all interpreter/VM dispatch overhead — hooks run at CPython native speed.

### Benchmark results (pong.ins, N=5000/1000):

| Path | on_update | on_draw | 1000 frames | vs AST |
|------|-----------|---------|-------------|--------|
| AST walker | 37.3 µs | 1061 µs | 980 ms | 1× |
| Bytecode VM | 56.0 µs | 2175 µs | 1772 ms | 0.5× |
| **Py compiled (P7)** | **2.3 µs** | **23.6 µs** | **14.5 ms** | **67×** |

### Key files
- `py_compiler.py` — `PyCompiler` class + `compile_hook()` convenience API. Converts InScript AST nodes to Python `ast.*` counterparts. All errors return `None` (caller falls back).
- `pygame_backend.py:run_hook_phase7()` — Three-path router: py_compiler → AST walker fallback.
- `pygame_backend.py:BatchedDrawNamespace` — P7.3: sprite calls batched via `Surface.blits()`, non-sprite calls pass through directly.

### Scene state model
All scene variables (`let` declarations) are stored in a shared `state` dict. The compiled function signature is `__hook(state, dt=None)`:
- Writes: `state["ball_x"] = 5` (STORE_SUBSCR)
- Reads: `state["ball_x"]` (BINARY_SUBSCR)
- Game namespaces (`draw`, `screen`, etc.) are Python globals (LOAD_GLOBAL)
- Hook params (`dt`) are Python locals (LOAD_FAST)

State is synced back to the interpreter environment after each hook execution for compatibility with SceneManager and other env-dependent subsystems.

### Compilation fallback
If `py_compiler.compile_hook()` returns `None` (unsupported node type, SyntaxError, etc.), `run_hook_phase7` falls back to the AST tree-walk interpreter. A compiled hook never silently returns wrong results — it either compiles correctly or doesn't run.

Full architecture: `inscript_package/ARCHITECTURE.md`

## Rust compiler (Path C)

- **Lexer**: `inscript_rust_parser/src/lexer.rs` — full character-by-character state machine, 85+ token variants
- **Parser**: `inscript_rust_parser/src/parser.rs` — AST building, includes `parse_fstring_content`
- **Compiler**: `inscript_rust_parser/src/compiler.rs` — AST-to-bytecode, produces `Vec<OpCode>` + `Vec<Value>`
- **VM**: `rust_vm_engine/src/vm.rs` — `VMEngine::from_opcodes` and `from_opcodes_with_funcs`
- **Function defs**: `rust_vm_engine/src/lib.rs` — `FuncDef` struct stores opcodes, constants, param count
- **Bytecode optimizer**: `rust_vm_engine/src/compiler.rs` — 5 passes (constant fold, instruction fuse, strength reduce, DCE, nop compact) + type inference analysis
- **JIT engine**: `rust_vm_engine/src/jit.rs` — hot trace detection (backward jumps), execution counting, IR generation on threshold
- **LLVM IR emitter**: `rust_vm_engine/src/ir.rs` — converts opcodes to LLVM 17 IR text (.ll), all 37 opcodes supported
- **Native compilation**: `rust_vm_engine/src/compile.rs` — writes IR to temp file, runs opt+llc+cc pipeline, loads shared library via libloading

### F-string encoding
The lexer encodes f-string brace escapes with null-byte markers:
- `{{` → `\x00{` (literal open brace)
- `}}` → `}\x00` (literal close brace)
- Regular `{expr}` is left as-is in the FString token value
The parser's `parse_fstring_content` decodes these markers back to literal braces while recognizing `{expr}` for interpolation.

### Known issues
- `OpCode::from_byte()` cannot decode parameterized opcodes — `from_opcodes` bypasses this
- `Value::String`'s `Display` impl wraps in quotes (`"hello"`); use `to_display_string()` for raw string output
- `to_byte()` maps all parameterized opcodes to `0xFE` — serialization via `from_opcodes` only
- Class methods are automatically bound to instances via `BoundMethod` value type
- For loops compile to indexed while-loops (no iterator protocol, but works for arrays/strings/objects)
- `compile.rs` native compilation requires `llc` + `opt` (LLVM 17) + `cc` in PATH

## Phase 5: Game loop optimization

Scene hooks are compiled from AST to `FnProto` bytecode **once** at load time (via `compiler.py:compile_body()`), then executed by the Python bytecode VM (`vm.py:VM`) during the game loop instead of the AST tree-walk interpreter. This provides 10-50x speedup for per-frame hooks.

### Key files
- `compiler.py:compile_body()` (line 290) — compiles raw AST statement nodes to `FnProto`
- `pygame_backend.py:run_hook_compiled()` (line 780) — VM-based hook execution with env state sync
- `vm.py:VM` — register-based bytecode VM (Path B)

### State synchronization
The interpreter's `Environment` chain and the VM's `_globals` dict are kept in sync via two-way copy before/after each compiled hook execution. Scene variables (e.g. `ball_x`) are shared between the two systems.

### Profiling
`--profile` flag adds per-frame timing for `on_update` and `on_draw` hooks using `time.perf_counter()`. Summary printed on exit: avg/min/max per-hook ms + call count.

### Build & test
```bash
cd inscript_package

# Build Rust DLL
cargo build --release -p inscript-parser

# Copy to .pyd for Python import
Copy-Item target/release/inscript_parser.dll target/release/inscript_parser.pyd -Force

# Test (Python tests calling Rust)
python test_compiler.py       # 16 tests — compiler output
python test_fstring.py        # f-string interpolation tests

# Test (Rust native)
cargo test --release -p inscript-parser
cargo test --release -p rust-vm-engine

# Use Rust VM (now the default — --python to opt out)
python inscript.py file.ins
```

## Phase 7: Python AST transpilation

See "Architecture → Path E" above. Phase 7 replaces the Phase 5/6 game loop paths (`VMClosure`, `run_hook_compiled`, `_sync_env_to_vm`) with Python AST compilation. The bytecode VM files are preserved for non-game use (`.ibc` serialization, `--compile`).

## Language conventions

- File extension: `.ins`
- Comments: `#` only (not `//` — that's floor division)
- Null: `nil` (not `null`; `null` raises E0055 since v1.7.4)
- CLI flags use `--` (e.g. `--repl`, `--check`, `--fmt`)

## Publishing to PyPI

```bash
# Tag and push to trigger publish workflow
git tag -a v3.9.4 -m "InScript v3.9.4"
git push origin v3.9.4
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
- Optional deps: `pygame` (game features), `pygls` (LSP server)
- Legacy root-level files (`inscript.py`, `inscript/`, `tests/test_interpreter.py`) are the old v0.2.0 interpreter and shouldn't be modified
- No Python linter/formatter config — just Python 3.10+ is required
- Built-in `inscript_test.py` enables writing tests in `.ins` files themselves (run via `--test`)
