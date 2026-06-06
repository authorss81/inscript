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

## Architecture (two execution paths)

Both paths share the front-end (lexer → parser → AST).

- **Path A** (tree-walk): `analyzer.py` → `interpreter.py` — powers REPL and most tests
- **Path B** (bytecode VM): `compiler.py` → `vm.py` — production engine; invoked via `.ibc` files or `--compile`

Full architecture: `inscript_package/ARCHITECTURE.md`

## Language conventions

- File extension: `.ins`
- Comments: `#` only (not `//` — that's floor division)
- Null: `nil` (not `null`; `null` raises E0055 since v1.7.4)
- CLI flags use `--` (e.g. `--repl`, `--check`, `--fmt`)

## Important notes

- Tests **must be run from `inscript_package/`** — they use `sys.path.insert(0, os.path.dirname(__file__))`
- Optional deps: `pygame` (game features), `pygls` (LSP server)
- Legacy root-level files (`inscript.py`, `inscript/`, `tests/test_interpreter.py`) are the old v0.2.0 interpreter and shouldn't be modified
- No Python linter/formatter config — just Python 3.10+ is required
- Built-in `inscript_test.py` enables writing tests in `.ins` files themselves (run via `--test`)
