# InScript VS Code Extension

Language support for [InScript](https://github.com/authorss81/inscript) — a game-focused scripting language.

## Features

- **Syntax highlighting** — keywords, types, strings, `$"..."` interpolation, `///` doc comments
- **Diagnostics** — parse and type errors shown inline as you type
- **Completions** — keywords, built-ins, variables, functions, dot-completions for arrays/strings/structs
- **Hover docs** — documentation for built-in functions and your own `fn`, `let`, `struct`, `enum` symbols

## Requirements

```bash
pip install inscript-lang pygls
```

## Installation

### From VSIX (recommended)
1. Download `inscript-lang-2.1.0.vsix`
2. In VS Code: Extensions → `...` → Install from VSIX

### From source
```bash
cd vscode-extension
npm install
npm run package   # produces inscript-lang-2.1.0.vsix
```

## Settings

| Setting | Default | Description |
|---|---|---|
| `inscript.pythonPath` | `python3` | Python interpreter used to run the LSP server |
| `inscript.serverPath` | `""` | Path to `inscript_package/` directory (leave empty to auto-detect) |
| `inscript.trace.server` | `off` | LSP trace level (`off`, `messages`, `verbose`) |

## How it works

The extension launches `python3 -m inscript_package.lsp.server` as a subprocess and communicates over stdio using the Language Server Protocol. The server uses InScript's own lexer, parser, and analyzer — so diagnostics are exact and completions are accurate.

## Language features (InScript v2.1.0)

```inscript
# Variables, functions, structs
let score: int = 0
fn greet(name: string) -> string { return $"Hello, {name}!" }

struct Player { x: float = 0.0; y: float = 0.0; health: int = 100 }

# Range loops with step
for i in 0..10 step 2 { score = score + i }

# Match expression
let grade = match score { case 0..60 { "F" } case 60..80 { "C" } case _ { "A" } }

# Spread operator
let merged = [...team_a, ...team_b]
```
