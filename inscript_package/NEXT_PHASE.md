# InScript — Next Phase (v1.1.0)

v1.0.0 is shipped. This document tracks what comes next.

---

## v1.1.0 — Developer Experience

**Target: Q3 2026**

### 1. Auto-formatter (`inscript fmt`)

Canonical style rules:
- 4-space indentation
- Braces on same line
- Spaces around operators
- Trailing commas in multi-line arrays/dicts

Implementation: post-parse pretty-printer from AST.

### 2. Doc Comments + Generator (`inscript doc`)

```inscript
/// Lerp between two values.
/// @param t  Must be in [0, 1]
fn lerp(a: float, b: float, t: float) -> float { ... }
```

`inscript doc src/ --out docs/` → generates a static HTML site.

### 3. Watch Mode

```bash
inscript --watch game.ins
```

Re-runs on every file save. Useful for rapid iteration.

### 4. Better Error Messages

Current: `ParseError: Expected expression at line 5`
Target:  `ParseError: Missing closing brace — opened at line 3:4`

Add "did you mean?" suggestions for common typos.

### 5. Source Maps

Stack traces currently show Python frames. Map them back to `.ins` lines.

---

## v1.2.0 — Type System Improvements

**Target: Q4 2026**

### Union Types

```inscript
type Shape = Circle | Rectangle | Triangle

fn area(s: Shape) -> float {
    match s {
        case Circle(r)    { return PI * r * r }
        case Rectangle(w, h) { return w * h }
    }
}
```

### Type Aliases

```inscript
type Point  = {x: float, y: float}
type Matrix = [[float]]
type ID     = string
```

### Generic Constraints

```inscript
fn sum<T: Numeric>(arr: [T]) -> T {
    return reduce(arr, |a, b| a + b, 0)
}
```

---

## v2.0.0 — Performance

**Target: 2027**

Current: tree-walk interpreter (~1M ops/sec on CPython)
Target:  bytecode VM (~10–50M ops/sec)

Steps:
1. Compile AST → bytecode (`LOAD`, `STORE`, `CALL`, `JUMP`, etc.)
2. Stack-based VM in Python (intermediate step)
3. Transpile to C extension via Cython (production)
4. WebAssembly target via Emscripten
