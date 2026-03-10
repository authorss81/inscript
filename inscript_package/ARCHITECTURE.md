# InScript Architecture

> Last updated: 2026-03-09 · v1.0.1 · Phase 7 complete (447 tests passing)

This document describes how the InScript implementation is structured — from source text to execution — so contributors can navigate the codebase quickly.

---

## Overview

InScript has two independent execution paths that share the front-end (lexer → parser → AST):

```
Source (.ins)
    │
    ▼
 Lexer          lexer.py          (559 lines)
    │
    ▼
 Tokens
    │
    ▼
 Parser         parser.py         (2 204 lines)
    │
    ▼
 AST            ast_nodes.py      ( 671 lines)
    │
    ├──────────────────────────────────────────────┐
    │  Path A (tree-walk)                          │  Path B (bytecode VM)
    ▼                                              ▼
 Analyzer       analyzer.py       (1 079 lines)   Compiler     compiler.py  (845 lines)
    │                                              │
    ▼                                              ▼
 Interpreter    interpreter.py    (2 265 lines)   FnProto (bytecode)
    │                                              │
    └──────────── stdlib_values.py (295 lines)    ▼
                  stdlib.py        (869 lines)    VM           vm.py        (789 lines)
                  stdlib_extended.py (758 lines)
                  stdlib_extended_2.py (1 510 lines)
```

Path A (tree-walk interpreter) powers the REPL and the test suite for Phases 1–5.
Path B (bytecode VM) is the production execution engine tested in Phases 6–7.

---

## Front-End

### Lexer (`lexer.py`, 559 lines)

Single-pass scanner. Produces a flat `Token` list. Key points:

- Handles f-strings: emits `F_STRING_START`, `F_STRING_PART`, `F_STRING_END` tokens so the parser can reconstruct the interpolation tree.
- Keywords are resolved at lex time; identifiers left as `IDENT`.
- Tracks `line` / `col` on every token for error messages.

### Parser (`parser.py`, 2 204 lines)

Recursive-descent, hand-written. Produces an `AST` made of nodes from `ast_nodes.py`. Notable patterns:

- `parse_expr()` uses Pratt parsing (precedence climbing) for all infix/prefix operators.
- `parse_stmt()` dispatches on the current token to statement sub-parsers.
- Error recovery: `ParseError` is raised immediately; no error-recovery mode yet.
- `FStringExpr` nodes carry a `parts` list of alternating `str` and `Expr` nodes.

### AST Nodes (`ast_nodes.py`, 671 lines)

Plain Python dataclasses / named tuples, no visitor pattern. Every node carries its source `line` for error reporting. Key node families:

| Family | Examples |
|--------|---------|
| Literals | `IntLit`, `FloatLit`, `StringLit`, `BoolLit`, `NilLit` |
| Expressions | `BinOp`, `UnaryOp`, `CallExpr`, `IndexExpr`, `FieldExpr` |
| Statements | `LetStmt`, `AssignStmt`, `IfStmt`, `WhileStmt`, `ForStmt` |
| Declarations | `FnDecl`, `StructDecl`, `EnumDecl`, `InterfaceDecl` |
| Special | `FStringExpr`, `MatchStmt`, `TryCatchStmt`, `YieldExpr` |

---

## Path A — Tree-Walk Interpreter

### Analyzer (`analyzer.py`, 1 079 lines)

Single-pass semantic checker. Walks the AST before interpretation and reports:

- Undefined variables (with scope tracking).
- Type mismatches where inferable without full type inference.
- Abstract method violations.
- `implements` interface conformance.

The analyzer does **not** transform the AST; it only validates it.

### Interpreter (`interpreter.py`, 2 265 lines)

Recursive tree-walker. Maintains an `Environment` stack (linked scopes). Return / break / continue are implemented via Python exceptions (`ReturnSignal`, `BreakSignal`, etc.).

Runtime values are plain Python objects:

| InScript type | Python representation |
|---------------|-----------------------|
| `nil` | `None` |
| `bool` | `bool` |
| `int` | `int` |
| `float` | `float` |
| `string` | `str` |
| `array` | `list` |
| `dict` | `dict` (no `_name` key) |
| struct instance | `dict` with `_name`, `_fields`, `_methods` |
| enum variant | `dict` with `_enum`, `_variant`, `_fields` |
| function | `InScriptFunction` |
| closure | `InScriptClosure` |

### Standard Library

Split across four files to keep individual files manageable:

| File | Contents |
|------|---------|
| `stdlib_values.py` (295 lines) | `InScriptFunction`, `InScriptClosure`, `InScriptStruct`, helper `_inscript_str()` |
| `stdlib.py` (869 lines) | Built-in functions: `print`, `len`, `range`, `push`, `pop`, type casts, math, string ops, array ops, dict ops, `typeof`, `Ok`/`Err`, channels, comptime |
| `stdlib_extended.py` (758 lines) | Modules: `math`, `string`, `array`, `io`, `json`, `random`, `time`, `color`, `tween` |
| `stdlib_extended_2.py` (1 510 lines) | Modules: `grid`, `events`, `debug`, `http`, `path`, `regex`, `csv`, `uuid`, `crypto` |

---

## Path B — Bytecode VM

### Compiler (`compiler.py`, 845 lines)

Transforms the AST into register-based bytecode (Lua 5.4–style). Outputs `FnProto` objects.

#### `FnProto`

A function prototype holds everything needed to execute one function:

```
FnProto
  .name          str
  .params        List[str]
  .n_locals      int                — total register slots needed
  .code          List[Instr]        — instruction stream
  .consts        List[Any]          — constant pool (strings, floats, nested FnProtos)
  .names         List[str]          — global / field name pool
  .protos        List[FnProto]      — nested function prototypes
  .upval_descs   List[UpvalDesc]    — upvalue capture descriptions
  .n_upvals      int
  .source_name   str
  .is_method     bool
```

#### Instruction encoding

```
Instr(op: Op, a: int, b: int, c: int)
```

All four fields are 16-bit unsigned integers. Meaning of `a`/`b`/`c` is opcode-dependent; the common conventions are documented in `compiler.py` near the `Op` definition.

#### Opcode set (53 opcodes)

| Category | Opcodes |
|----------|---------|
| Loads | `LOAD_NIL`, `LOAD_TRUE`, `LOAD_FALSE`, `LOAD_INT`, `LOAD_CONST` |
| Globals | `LOAD_GLOBAL`, `STORE_GLOBAL` |
| Upvalues | `LOAD_UPVAL`, `STORE_UPVAL` |
| Registers | `MOVE` |
| Arithmetic | `ADD`, `SUB`, `MUL`, `DIV`, `MOD`, `POW`, `IDIV`, `NEG` |
| Comparison | `EQ`, `NEQ`, `LT`, `LTE`, `GT`, `GTE` |
| Logic | `NOT` |
| Strings | `CONCAT`, `INTERP` |
| Jumps | `JUMP`, `JUMP_IF_FALSE`, `JUMP_IF_TRUE`, `JUMP_IF_NIL` |
| Calls | `CALL`, `CALL_METHOD`, `RETURN` |
| Closures | `MAKE_CLOSURE`, `CAPTURE_UPVAL` |
| Collections | `MAKE_ARRAY`, `MAKE_DICT`, `MAKE_RANGE` |
| Indexing | `GET_INDEX`, `SET_INDEX` |
| Fields | `GET_FIELD`, `SET_FIELD` |
| OOP | `MAKE_INSTANCE` |
| Iteration | `ITER_START`, `ITER_NEXT` |
| Modules | `IMPORT` |
| Exceptions | `THROW`, `PUSH_HANDLER`, `POP_HANDLER` |
| I/O | `PRINT` |
| Types | `CAST`, `IS_TYPE` |
| Operators | `OP_CALL` (Phase 7 — operator overload dispatch) |
| Meta | `LINE`, `NOP` |

#### Register allocation

The `Scope` class inside the compiler tracks locals and temporaries in a single flat register array per call frame. Key conventions (documented in `JOURNAL.md`):

- `_alloc()` / `_free(r)` — LIFO only; never free a register that has a live reference below it.
- Struct init: `dst` allocated first; field value pairs at `dst+1`, `dst+2`, …
- `CALL_METHOD` args at `a+1`, `a+2`, …
- `MAKE_RANGE`: `c = end_reg | 0x8000` for inclusive ranges.
- List comprehensions: return `res` with `n_regs = res+1`; do **not** free + realloc `res`.

#### IBC serialization

`Compiler.save_ibc(proto, path)` / `Compiler.load_ibc(path)` — round-trips a `FnProto` tree through `pickle`, prefixed with a magic header and version stamp. Files use the `.ibc` extension.

### VM (`vm.py`, 789 lines)

Single-function dispatch loop (`VM.execute(proto, ...)`). Each call frame is:

```python
Frame:
  regs        list          — register array (pre-allocated to proto.n_locals)
  pc          int           — program counter
  proto       FnProto
  handlers    list          — exception handler stack (PUSH_HANDLER / POP_HANDLER)
  upvals      list[UpvalCell]
```

The main loop is a `while True` / `if ins.op == Op.X: ...` dispatch chain.

#### Runtime types (VM-only)

| Class | Purpose |
|-------|---------|
| `UpvalCell` | Mutable cell shared between closure and enclosing frame |
| `VMClosure` | Callable wrapping a `FnProto` + captured `UpvalCell` list |
| `VMInstance` | Struct instance with `_desc` (descriptor) + `_fields` dict |
| `VMEnum` / `VMVariant` | ADT enum type and variant instance |
| `VMModule` | Module namespace returned by `IMPORT` |
| `VMIterator` | Iterator state for `ITER_START` / `ITER_NEXT` |

#### Operator overloading (Phase 7)

`OP_CALL` opcode: `a` = result register, `b` = name-table index (operator key), `c` = RHS register (or `NIL_REG` for unary).

Operator keys stored in `VMInstance._desc.__operators__`:

| InScript syntax | Key |
|-----------------|-----|
| `operator + (rhs)` | `"+"` |
| `operator - ()` | `"-u"` (unary) |
| `operator == (o)` | `"=="` |
| `operator != (o)` | Falls back to negating `==` if `!=` not defined |
| `operator str ()` | `"str"` |
| `operator len ()` | `"len"` |
| `operator [] (i)` | `"[]"` |

---

## Tooling

### REPL (`repl.py`)

Two modes:

- **Terminal REPL** (`EnhancedREPL`) — readline + tab completion + syntax highlighting + dot-commands.
- **Web playground** (`run_playground`) — minimal HTTP server serving a single-page HTML playground that POSTs code to `/run`.

Key dot-commands: `.vars`, `.fns`, `.types`, `.bytecode [expr]`, `.asm [expr]`, `.time <expr>`, `.save`, `.load`, `.modules`.

`.bytecode` compiles the expression via Path B and prints a compact opcode listing.
`.asm` shows the full annotated assembly with constants table, names table, and upvalue descriptors — including recursively nested function prototypes.

### LSP Server (`lsp/`)

Four files implementing the Language Server Protocol (JSON-RPC over stdio):

| File | Feature |
|------|---------|
| `lsp/server.py` | JSON-RPC loop, request dispatcher |
| `lsp/diagnostics.py` | Publish diagnostics (calls Lexer + Parser + Analyzer) |
| `lsp/completions.py` | Keyword + symbol completion |
| `lsp/hover.py` | Type / doc hover |

### Package Manager (`inscript.py`)

The `inscript` CLI (`inscript.py`) handles: `run`, `compile`, `exec` (IBC), `repl`, `--install`, `--remove`, `--search`, `--list`, `--info`. Packages are stored in `~/.inscript/packages/`.

---

## Test Suite

| File | Phase | Count | Covers |
|------|-------|-------|--------|
| `test_phase5.py` | 5 | 270 | Tree-walk interpreter end-to-end |
| `test_phase6.py` | 6 | 145 | Bytecode compiler + VM |
| `test_phase7.py` | 7 | 32 | Operator overloading via VM |
| `test_lexer.py` | — | — | Lexer token output |
| `test_parser.py` | — | — | Parser AST shape |
| `test_interpreter.py` | — | — | Interpreter (legacy) |
| `test_stdlib.py` | — | — | Standard library functions |
| `test_analyzer.py` | — | — | Static analyzer diagnostics |

Run all phases: `python test_phase5.py && python test_phase6.py && python test_phase7.py`

---

## Performance Notes

Measured on CPython 3.12, typical laptop:

| Benchmark | Time |
|-----------|------|
| `fib(20)` (tree-walk) | ~200 ms |
| `fib(20)` (bytecode VM) | ~650 ms* |
| 100 000-iteration loop (VM) | ~490 ms |

\* The bytecode VM is currently slower than the tree-walk interpreter because the dispatch loop itself is pure Python. Planned Phase 6.2 will add a C extension (`inscript_vm.c`) that should bring hot-loop speed to near-Lua (5–15× faster than CPython).

For context:
- **GDScript** (Godot): comparable to current Python VM tier.
- **Lua 5.4**: ~10–50× faster than CPython for hot loops.
- **C#/Unity, C++/Unreal**: compiled, orders of magnitude faster.

---

## File Inventory

```
inscript_package/
├── lexer.py             (559 lines)   — tokeniser
├── parser.py          (2 204 lines)   — recursive-descent parser
├── ast_nodes.py         (671 lines)   — AST node dataclasses
├── analyzer.py        (1 079 lines)   — static semantic checker
├── interpreter.py     (2 265 lines)   — tree-walk interpreter (Path A)
├── compiler.py          (845 lines)   — AST → bytecode compiler (Path B)
├── vm.py                (789 lines)   — bytecode VM (Path B)
├── stdlib_values.py     (295 lines)   — runtime value types + helpers
├── stdlib.py            (869 lines)   — built-in functions
├── stdlib_extended.py   (758 lines)   — stdlib modules 1–9
├── stdlib_extended_2.py(1 510 lines)  — stdlib modules 10–18
├── stdlib_game.py                     — pygame game bindings
├── pygame_backend.py                  — pygame rendering backend
├── environment.py                     — Environment / scope chain (Path A)
├── errors.py                          — InScriptError hierarchy
├── repl.py                            — enhanced REPL + web playground
├── inscript.py                        — CLI entry point
├── setup.py                           — package metadata
├── lsp/                               — Language Server Protocol
│   ├── server.py
│   ├── diagnostics.py
│   ├── completions.py
│   └── hover.py
├── examples/                          — example .ins programs
└── test_phase5/6/7.py                 — primary test suites
```
