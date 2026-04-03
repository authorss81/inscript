# InScript v1.0.18 — Game-Focused Scripting Language

> **839 tests passing** · **59 stdlib modules** · **Python 3.10+** · **Audit score: 8.8/10**
> Pre-stable — first stable release: **v1.1.0 (Q2 2026)**

InScript is a statically-typed scripting language for 2D games. It has a near-complete bytecode VM, 59 game modules, and now supports nullable types, union types, and type aliases.

---

## Quick Start

```bash
pip install pygame pygls
git clone https://github.com/authorss81/inscript
cd inscript/inscript_package
python inscript.py --repl
python inscript.py examples/platformer.ins
python inscript.py --version   # InScript 1.0.18
```

---

## Language — What's New in v1.0.18

```inscript
// Nullable types, union types, type aliases
type PlayerID = int
type Name = string

fn greet(name: Name?) {
    print("Hello, " ++ (name ?? "stranger"))
}

fn show(x: int|string) -> string {
    return match x {
        case int   { "number: " ++ string(x) }
        case _     { "text: " ++ x }
    }
}

// Richer array methods
let nums = [1, 2, 3, 4, 5, 6, 7, 8]

let small = nums.take_while(fn(x) { return x < 5 })    // [1, 2, 3, 4]
let big   = nums.drop_while(fn(x) { return x < 5 })    // [5, 6, 7, 8]
let pairs = nums.window(2)                               // [[1,2],[2,3],...]
let split = nums.partition(fn(x) { return x % 2 == 0}) // [[2,4,6,8],[1,3,5,7]]
let idx   = nums.index_where(fn(x) { return x > 5 })   // 5
let last  = nums.last_where(fn(x) { return x % 2 == 0})// 8

// comptime constants — available at runtime
comptime {
    const MAX_PLAYERS = 4
    const GRAVITY     = 9.8
}
print(MAX_PLAYERS)   // 4
print(GRAVITY)       // 9.8

// VM match with guards
match score {
    case 90..=100  { print("A") }
    case 80..=89   { print("B") }
    case n if n >= 0 { print("F") }
}

// thread.run — quick parallel work
import "thread" as T
let result = T.run(fn() { return heavy_compute() })
```

---

## Full Feature Table

| Feature | Status |
|---------|--------|
| `int?` nullable types | ✅ v1.0.18 |
| `int\|string` union type params | ✅ v1.0.18 |
| `type ID = int` type aliases | ✅ v1.0.18 |
| `comptime{}` leaks to outer scope | ✅ v1.0.18 |
| `arr.take_while/drop_while/window/partition` | ✅ v1.0.18 (both paths) |
| `arr.none/index_where/last_where` | ✅ v1.0.18 |
| `thread.run(fn)` sync convenience | ✅ v1.0.18 |
| VM match guards `case n if n>5` | ✅ v1.0.18 |
| VM match ADT bindings | ✅ v1.0.18 |
| VM decorator `@name` | ✅ v1.0.16 |
| VM `priv` field enforcement | ✅ v1.0.16 |
| VM `super.method()` | ✅ v1.0.15 |
| VM `try-finally` | ✅ v1.0.15 |
| Pattern matching: ranges, guards, ADTs | ✅ v1.0.15-17 |
| 59 stdlib modules | ✅ Complete |

## Missing (v1.1 targets)

- `inscript fmt` — formatter
- Debugger
- `pip install inscript-lang`
- `docs.inscript.dev`

---

## Tests

```bash
python test_phase6.py         # 145/145
python test_phase7.py         # 32/32
python test_audit.py          # 54/54
python test_comprehensive.py  # 335/335
```

---

MIT License · [GitHub](https://github.com/authorss81/inscript) · [Audit (8.8/10)](InScript_Language_Audit.md) · [Roadmap](ROADMAP.md)
