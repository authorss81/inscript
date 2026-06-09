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
```

CI also runs: `test_phase6.py`, `test_phase7.py`, `test_audit.py`, `test_comprehensive.py`, `test_v120.py`–`test_v300.py` (447+ total).

## Architecture (three execution paths)

Paths A & B share the front-end (Python lexer → parser → AST). Path C is the new Rust pipeline.

- **Path A** (tree-walk): `analyzer.py` → `interpreter.py` — powers REPL and most tests
- **Path B** (bytecode VM): `compiler.py` → `vm.py` — production engine; invoked via `.ibc` files or `--compile`
- **Path C** (Rust compiler + VM): `inscript_rust_parser/` (lexer, parser, compiler) → `rust_vm_engine/` (VM). Exposed via PyO3 as `inscript_parser` Python module. Functions: `lex(source)`, `compile(source)`, `compile_and_run(source)`.

Full architecture: `inscript_package/ARCHITECTURE.md`

## Rust compiler (Path C)

- **Lexer**: `inscript_rust_parser/src/lexer.rs` — full character-by-character state machine, 85+ token variants
- **Parser**: `inscript_rust_parser/src/parser.rs` — AST building, includes `parse_fstring_content`
- **Compiler**: `inscript_rust_parser/src/compiler.rs` — AST-to-bytecode, produces `Vec<OpCode>` + `Vec<Value>`
- **VM**: `rust_vm_engine/src/vm.rs` — `VMEngine::from_opcodes` and `from_opcodes_with_funcs`
- **Function defs**: `rust_vm_engine/src/lib.rs` — `FuncDef` struct stores opcodes, constants, param count

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

# Use via --rust flag
python inscript.py --rust file.ins
```

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
