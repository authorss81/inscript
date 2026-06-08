# Maximum Speed Plan — InScript Rust Engine

**Goal:** 10–20× end-to-end speedup over pure Python by moving the entire pipeline into Rust.

| Phase | Component | Effort | Speedup (cumulative) |
|-------|-----------|--------|----------------------|
| 1 | Rust lexer | 1–2 days | ~3–4× |
| 2 | Rust compiler (AST → bytecode) | 1 week | ~5–8× |
| 3 | Fill VM opcode gaps | 2–3 weeks | ~8–12× |
| 4 | Direct pipeline integration | 1 week | ~10–20× |
| 5 | JIT backend (stretch) | months | marginal for game scripts |

JIT is excluded (see reasoning below). The phases focus on what gives real, measurable wins for InScript's use case.

---

## Phase 1 — Rust Lexer (1–2 days)

**Bottleneck attacked:** Python lexer (2.44ms) is 69% of current frontend time (3.56ms).

**File:** Create `inscript_package/inscript_rust_parser/src/lexer.rs`

### What to build

A character-by-character state machine that produces `Vec<TokenInfo>` — exactly what the existing Rust parser already consumes. No AST, no complex data structures.

### Token types to support

All tokens from the Python lexer's `TT` enum — ~80 token types:

```rust
pub enum Token {
    // Literals
    Int(i64), Float(f64), String(String), Ident(String),
    // Keywords (45+)
    Let, Const, Fn, If, Else, While, For, In,
    Return, Break, Continue, Switch, Case, Default,
    True, False, Nil,
    Try, Catch, Finally, Throw,
    Async, Await, Yield,
    Struct, Enum, Class, Match,
    OnStart, OnUpdate, OnDraw, OnExit,
    Import, From, As, Export,
    // Operators
    Plus, Minus, Star, Slash, Percent, Power,
    Assign, PlusEq, MinusEq, StarEq, SlashEq,
    Eq, Neq, Lt, Lte, Gt, Gte,
    And, Or, Not,
    // Delimiters
    LeftParen, RightParen, LeftBrace, RightBrace,
    LeftBracket, RightBracket, Comma, Dot, Semicolon, Colon,
    Arrow, FatArrow, Question, QuestionDot,
    // Special
    Eof,
}
```

### Key implementation details

- **Built on the existing `token.rs`** — add missing variants rather than creating a new module
- **Expose via PyO3** as a `#[pyfunction] fn lex(source: &str) -> Vec<PyDict>` returning the same dict format (token_type, value, line, column) that `test_rust_parser.py` already constructs
- **Handle InScript-specific syntax:**
  - `fn*` generator marker → two tokens `Fn` `Star`
  - `#` comments → skip to newline
  - `?.` optional chaining
  - `->` arrow return type
  - `=>` fat arrow (closures)
  - `+=`, `-=`, etc. compound assignment
  - `//` floor division vs. `#` comment
  - `**` power vs. `*` multiply
  - String escaping and interpolation markers
  - Multi-line strings (if supported)

### Integration test

```python
import inscript_rust_parser
tokens = inscript_rust_parser.lex(source)
# tokens is a list of dicts with token_type/value/line/column
```

### Verification

```
Phase 1:  Rust Lexer (~0.3ms) → Rust Parser (0.56ms) → Python VM
End-to-end: ~0.9ms  (current: 3.56ms → 3–4× faster)
```

### Files to modify

| File | Change |
|------|--------|
| `inscript_rust_parser/src/token.rs` | Add missing token variants |
| `inscript_rust_parser/src/lexer.rs` | **New file** — lexer implementation |
| `inscript_rust_parser/src/lib.rs` | Add `lex` `#[pyfunction]`, register in module |
| `test_rust_parser.py` | Add `lex()` test + benchmark |

---

## Phase 2 — Rust Compiler: AST → Stack Bytecode (1 week)

**Bottleneck attacked:** Python compiler (`compiler.py`, ~1–2ms) and the architectural mismatch between register-based Python VM and stack-based Rust VM.

**File:** Create `inscript_rust_parser/src/compiler.rs`

### Why not bridge Python's register bytecode

The Python VM uses `Instr(op, a, b, c)` — register-based. The Rust VM is stack-based. Translating between them requires a register-allocation pass that's as complex as writing a compiler from scratch. Instead, compile directly from the Rust parser's AST to Rust VM bytecode — no intermediate format.

### What to build

A `Compiler` struct that walks the Rust AST and emits `Vec<OpCode>`:

```rust
pub struct Compiler {
    opcodes: Vec<OpCode>,
    constants: Vec<Arc<Value>>,  // pooled literals
    scopes: Vec<Scope>,
}

impl Compiler {
    pub fn compile(program: &Program) -> (Vec<OpCode>, Vec<Arc<Value>>);
    fn stmt(&mut self, stmt: &Stmt);
    fn expr(&mut self, expr: &Expr) -> usize;  // returns register/stack depth
}
```

### Opcode mapping (27 directly mappable)

| AST node | Rust VM opcodes |
|----------|----------------|
| `Literal(Int(n))` | `Push(n)` |
| `Literal(Float(f))` | `Push(f)` (via constant pool) |
| `Literal(String(s))` | `Push(s)` (via constant pool) |
| `Literal(Bool(b))` | `Push(1/0)` |
| `Literal(Nil)` | `Push(0)` |
| `Identifier(name)` | `LoadGlobal(idx)` / `LoadReg(idx)` |
| `Binary(Add/Sub/... )` | `Add` / `Sub` / ... |
| `Call { callee, args }` | `...exprs`, `Call(n)` |
| `If { cond, then, else }` | `...cond`, `JumpIfFalse`, `...then`, `Jump`, `...else` |
| `While { cond, body }` | `JumpIfFalse`, `...body`, `Jump` (loop) |
| `For { target, iter, body }` | `...iter`, `ITER_START`, `ITER_NEXT`, loop |
| `Return(expr)` | `...expr`, `Return` |
| `VarDecl { name, init }` | `...init`, `StoreGlobal(idx)` |

### 37 missing features → runtime helper calls (Phase 3 target)

For features the Rust VM doesn't have opcodes for (closures, exceptions, structs), compile to:

```
Push(args...) → Call(runtime_function_index)
```

Where `runtime_function_index` points to a Python-provided or Rust-stub function. This means Phase 2 works **today** without implementing all opcodes — slow paths fall back to helpers. In Phase 3, each helper is replaced with native opcodes.

### Verification

After Phase 2, this pipeline works end-to-end:

```
Source → Rust Lexer → Rust Parser → Rust Compiler → Rust VM bytes
```

Test with programs that avoid the 37 unimplemented features (simple math, loops, conditionals, function calls, variables).

### Files to create/modify

| File | Change |
|------|--------|
| `inscript_rust_parser/src/compiler.rs` | **New file** — AST-to-bytecode compiler |
| `inscript_rust_parser/src/lib.rs` | Add `compile` `#[pyfunction]`, register in module |
| `test_rust_parser.py` | Add compiler tests |

---

## Phase 3 — Fill Rust VM Opcode Gaps (2–3 weeks)

**Bottleneck attacked:** The 37 opcodes where the Rust VM falls back to runtime helpers.

**File:** `rust_vm_engine/src/vm.rs`

### Priority list (highest-impact first)

#### Priority 1: Exception handling (2–3 days)

```
THROW, PUSH_HANDLER, POP_HANDLER
```

**Why first:** Every `try`/`catch`/`throw` program is broken without these. Game scripts use error handling.

**Implementation:**

```rust
PUSH_HANDLER(addr)  // Push try block address onto handler stack
POP_HANDLER         // Pop handler
THROW               // Pop value, search handler stack, jump to catch
```

- Add a `handler_stack: Vec<HandlerFrame>` to `VMEngine`
- `HandlerFrame { catch_addr: usize, finally_addr: Option<usize> }`
- `THROW` unwinds the stack and register state to the handler

**Test:** `try { throw "err" } catch(e) { print(e) }`

#### Priority 2: Iteration (2–3 days)

```
ITER_START, ITER_NEXT
```

**Why next:** Every `for` loop depends on these. Most InScript code uses loops.

**Implementation:**

```rust
ITER_START          // Top of stack is iterable → push iterator object
ITER_NEXT           // Advance iterator, push next value (or nil if done)
```

- Use Python's iterator protocol via FFI, or implement iterators natively
- Native iterators for arrays: pointer + length on stack
- Python FFI fallback for custom iterator objects

**Test:** `for i in range(10) { print(i) }`

#### Priority 3: Struct/field operations (2–3 days)

```
GET_FIELD, SET_FIELD, MAKE_INSTANCE
```

**Why:** Structs and field access are fundamental to InScript game code (scenes, entities).

**Implementation:**

```rust
MAKE_INSTANCE(n)    // Pop n field values, create object, push
GET_FIELD           // Stack: object field_name → push value
SET_FIELD           // Stack: object field_name value → mutate
```

- `MAKE_INSTANCE` creates a `Value::Object(HashMap)` with field name/value pairs
- Fields are interned strings for fast comparison

**Test:** `scene Player { let x: float = 0 }`

#### Priority 4: Closures and generators (3–4 days)

```
LOAD_UPVAL, STORE_UPVAL, MAKE_CLOSURE, CAPTURE_UPVAL
```

**Why:** Generators (`fn*`) and closures enable coroutine-style game logic.

**Implementation:**

- Upvalue capture via `Vec<Arc<Value>>` stored in `CallFrame`
- `MAKE_CLOSURE` creates a closure object with captured upvalue list
- `fn*` generators use a suspended call frame with yield/resume

**Test:** `fn* gen() { yield 1; yield 2 }`

#### Priority 5: Bitwise operations (1 day)

```
BAND, BOR, BXOR, BNOT, BLSHIFT, BRSHIFT
```

Straightforward — same pattern as existing `Add`/`Sub` but with `i64` bitwise operations.

**Test:** `let x = 0xFF & 0x0F`

#### Priority 6: Remaining operations (2–3 days)

```
IMPORT, PRINT, CAST, IS_TYPE, INTERP, LINE
```

- `IMPORT` → module loading via Python `importlib`
- `PRINT` → `print()` builtin
- `CAST` → `int()`, `float()`, `string()` type coercion
- `IS_TYPE` → `is` type check
- `INTERP` → f-string interpolation (`f"...{expr}..."`)
- `LINE` → debug info (skip during execution, used for stack traces)

### Verification

After Phase 3, the entire test suite (`test_interpreter.py`, 122 tests) should pass when compiled through the Rust pipeline and executed on the Rust VM.

---

## Phase 4 — Direct Rust Pipeline (1 week)

**Bottleneck attacked:** FFI overhead between Python and Rust at each stage.

### What to build

A single `#[pyfunction]` entry point:

```rust
#[pyfunction]
fn execute(source: &str, filename: &str) -> PyResult<String> {
    let tokens = lexer::lex(source);
    let program = parser::parse(tokens)?;
    let (bytecode, constants) = compiler::compile(&program);
    let mut vm = VMEngine::new(bytecode, constants);
    match vm.execute() {
        Ok(val) => Ok(val.to_string()),
        Err(e) => Ok(format!("Error: {}", e)),
    }
}
```

No Python intermediate steps. No token dict conversion. No AST dict conversion. The entire pipeline runs in one FFI call.

### Comparison

| | Phase 3 | Phase 4 |
|---|---|---|
| FFI calls per execution | 3 (lex + parse + execute) | 1 |
| Data crossing FFI | Token dicts + AST dicts + bytes | Nothing (all internal) |
| Speedup over Python | ~8–12× | ~10–20× |

### Integration

```python
import inscript_rust_parser as irp
result = irp.execute(source)  # single call, returns string
```

The old Python pipeline continues to work for debugging/comparison. The Rust path is the default with a fallback flag `--python`.

### Files to modify

| File | Change |
|------|--------|
| `inscript_rust_parser/src/lib.rs` | Add `execute` `#[pyfunction]` that wires lex+parse+compile+run |
| `inscript_rust_parser/Cargo.toml` | Add `rust_vm_engine` as dependency |
| `inscript_package/inscript.py` | Add `--rust` flag to use Rust pipeline |

---

## Phase 5 — JIT Backend (stretch goal, months)

### Not recommended for production

| Factor | InScript | Ideal JIT workload |
|--------|----------|-------------------|
| Script lifetime | ~1 frame to ~1 second | Hours-long server processes |
| Typical size | 50–500 lines | 10,000+ line hot loops |
| Execution model | One-shot per frame | Long-running tight loops |
| Warmup cost | High (JIT must compile) | Amortized over millions of iterations |

### What exists

The `rust_vm_engine` already has:

- `ir.rs` — LLVM 17 IR emitter (produces valid `.ll` module text)
- `jit.rs` — Hot-trace detection engine (tracks execution counts, identifies hot paths)
- `JitEngine.collect_hot_traces()` — returns `(trace_name, ir_text)` pairs

### What's missing

- LLVM C API or Cranelift backend to compile `.ll` → machine code
- Native function pointer trampoline to call compiled traces
- On-stack replacement (OSR) for cases where a loop becomes hot after partial execution

### Verdict

The existing JIT infrastructure is useful as a **research prototype**. The 5-pass compiler (constant folding, instruction fusion, strength reduction, DCE, nop compaction) already eliminates most of the overhead that JIT would target. For game scripts, the Phases 1–4 deliver 95% of the possible speedup with 10% of the effort.

---

## Summary Timeline

| Phase | Effort | Cumulative speedup | Go/no-go gate |
|-------|--------|-------------------|---------------|
| 1 — Rust lexer | 1–2 days | ~3–4× | All lexer tests pass |
| 2 — Rust compiler | 1 week | ~5–8× | Simple programs compile and run |
| 3 — Fill opcode gaps | 2–3 weeks | ~8–12× | Full test suite passes |
| 4 — Direct pipeline | 1 week | ~10–20× | `execute(source)` returns correct results |
| 5 — JIT | months | marginal | Blocked on real-world need |

**Total production effort:** 4–6 weeks
**Expected end-to-end speedup:** 10–20× over pure Python
**JIT:** Skip unless a specific workload demonstrates it's needed.
