# InScript v1.0.19 — Game-Focused Scripting Language

> **839 tests passing** · **59 stdlib modules** · **Python 3.10+** · **Audit score: 9.0/10**
> Pre-stable — first stable release: **v1.1.0 (Q2 2026)**

InScript is a statically-typed scripting language for 2D games. v1.0.19 adds the formatter, arrow functions, and rest destructuring. One session away from v1.1.0.

---

## Quick Start

```bash
pip install pygame pygls
git clone https://github.com/authorss81/inscript
cd inscript/inscript_package
python inscript.py --repl
python inscript.py examples/platformer.ins
python inscript.py --version   # InScript 1.0.19
```

---

## New in v1.0.19

```inscript
// Arrow functions — cleaner lambdas
let double = fn(x) => x * 2
let evens  = [1,2,3,4,5].filter(fn(x) => x % 2 == 0)
let names  = users.map(fn(u) => u.name).filter(fn(n) => n.len() > 3)

// Chained method calls work in VM now (was broken)
let result = data
    .filter(fn(x) => x.score > 50)
    .map(fn(x) => x.name)
    .sorted()

// Rest destructuring
let [first, second, ...rest] = [1, 2, 3, 4, 5]
print(first)   // 1
print(rest)    // [3, 4, 5]

fn log(level, ...messages) {
    for msg in messages { print(f"[{level}] {msg}") }
}
```

```bash
# Formatter — built in
inscript --fmt game.ins             # format in place
inscript --fmt-check game.ins       # exit 1 if not formatted (CI)
inscript --fmt-dry-run game.ins     # print without writing

# Watch mode — rerun on file change
inscript --watch game.ins
```

---

## Feature Status

| Feature | Status |
|---------|--------|
| Arrow functions `fn(x) => x*2` | ✅ v1.0.19 — interpreter + VM |
| Rest destructuring `[a,...rest]` | ✅ v1.0.19 |
| `inscript --fmt` formatter | ✅ v1.0.19 |
| `inscript --watch` watch mode | ✅ v1.0.19 |
| VM chained method calls fixed | ✅ v1.0.19 |
| `int?` nullable, `int\|string` union | ✅ v1.0.17 |
| `type ID = int` type aliases | ✅ v1.0.17 |
| VM mixin, str.is_upper/lower | ✅ v1.0.18 |
| VM decorator, priv, super | ✅ v1.0.16 |
| Pattern matching (ranges, guards, ADT) | ✅ v1.0.15-17 |
| 59 stdlib modules | ✅ Complete |
| `inscript check` static analysis | ✅ Complete |
| Web playground (basic `--web`) | ✅ Complete |

## Path to v1.1.0

| Version | What | Status |
|---------|------|--------|
| v1.0.19 | `inscript fmt` + arrow fn + rest + watch | ✅ **Done** |
| v1.0.20 | `inscript test` runner | 🔧 Next |
| v1.0.21 | **PyPI upgrade** — `pip install inscript-lang` (you have v0.6 on PyPI) | 🔧 Next |
| v1.0.22 | Docs site + E0XXX error pages | 🔧 Next |
| v1.0.23 | Web playground with Pyodide | 🔧 Next |
| **v1.1.0** | **FIRST STABLE** | Q2 2026 |

---

## Tests

```bash
python test_phase6.py         # 145/145
python test_phase7.py         # 32/32
python test_audit.py          # 54/54
python test_comprehensive.py  # 335/335
```

---

MIT License · [GitHub](https://github.com/authorss81/inscript) · [Audit (9.0/10)](InScript_Language_Audit.md) · [Roadmap](ROADMAP.md)
