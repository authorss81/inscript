# InScript v1.0.23 — Game-Focused Scripting Language

> **839 tests passing** · **59 stdlib modules** · **Python 3.10+** · **Audit 9.5/10**  
> Available on PyPI: **`pip install inscript-lang`** · First stable: **v1.1.0 (Q2 2026)**

InScript is a statically-typed scripting language for 2D games. v1.0.23 adds the test runner and PyPI package config — one session from the first stable release.

---

## Install

```bash
# From PyPI (when v1.0.23 is uploaded)
pip install inscript-lang

# Or from source
git clone https://github.com/authorss81/inscript
cd inscript/inscript_package
pip install -e .

# Start
inscript --repl
inscript examples/platformer.ins
inscript --version   # InScript 1.0.23
```

---

## Developer Workflow

```bash
# Run a file
inscript game.ins

# Format code
inscript --fmt game.ins           # format in place
inscript --fmt-check game.ins     # CI check

# Watch mode — auto-rerun on save
inscript --watch game.ins

# Run tests
inscript --test                   # discover test_*.ins
inscript --test --verbose         # show each test name
inscript --test --fail-fast       # stop on first failure
```

**Test file format:**
```inscript
// test_physics.ins
test "collision detection" {
    import "physics2d" as P
    let r1 = P.Rect(0, 0, 10, 10)
    let r2 = P.Rect(5, 5, 10, 10)
    assert(r1.overlaps(r2), "rects should overlap")
}

test "gravity" {
    let body = physics2d.RigidBody(mass: 1.0)
    body.update(0.1)
    assert(body.vel_y > 0.0, "should fall")
}
```

---

## Language Features

```inscript
// Arrow functions
let evens  = [1,2,3,4,5].filter(fn(x) => x % 2 == 0)
let scores = students.map(fn(s) => s.score).filter(fn(n) => n >= 60)

// Nullable + union types
fn greet(name: string?) { print("Hi " ++ (name ?? "stranger")) }
fn parse(x: int|string) -> float { return float(string(x)) }

// Pattern matching with ranges and guards
match level {
    case 1..=5   { print("beginner") }
    case 6..=10  { print("intermediate") }
    case n if n > 10 { print("expert") }
}

// Result type chaining
fn load(path: string) -> Result {
    return try { Ok(read_file(path)) } catch e { Err(e) }
}
load("data.json")
    .map(fn(s) => parse_json(s))
    .unwrap_or({})
```

---

## Feature Completeness

| Category | Status |
|----------|--------|
| Core language (all features) | ✅ Complete |
| Bytecode VM parity | ✅ Complete (v1.0.13-18) |
| `inscript fmt` formatter | ✅ v1.0.19 |
| `inscript --watch` | ✅ v1.0.19 |
| `inscript --test` test runner | ✅ v1.0.23 |
| `pyproject.toml` for PyPI | ✅ v1.0.23 |
| 59 stdlib modules | ✅ Complete |
| LSP + VS Code extension | ✅ Complete |
| Docs site | 🔧 v1.0.22 |
| Web playground | 🔧 v1.0.23 |
| **v1.1.0 stable** | **Q2 2026** |

---

## Tests

```bash
python test_phase6.py         # 145/145 VM
python test_phase7.py         # 32/32  operators
python test_audit.py          # 54/54  audit
python test_comprehensive.py  # 335/335 features
```

---

## Upgrading from v0.6

Syntax is **fully backward compatible**. Just upgrade:
```bash
pip install --upgrade inscript-lang
```
All v0.6 programs run unchanged. New features are additive.

---

MIT License · [GitHub](https://github.com/authorss81/inscript) · [Audit (9.5/10)](InScript_Language_Audit.md) · [Roadmap](ROADMAP.md)
