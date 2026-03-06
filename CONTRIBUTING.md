# Contributing to InScript

Thank you for your interest in contributing to InScript — a game-first scripting language.

## How to Report Bugs

Open a GitHub Issue with:
- Your OS and Python version (`python --version`)
- The `.ins` file that caused the error
- The full error message including line/column
- What you expected to happen vs what actually happened

## How to Request Features

Open a GitHub Issue labelled `enhancement`. Describe:
- What the feature does
- Why it belongs in InScript specifically
- An example of the syntax you propose

## Setting Up for Development
```powershell
git clone https://github.com/authorss81/inscript
cd inscript\inscript_package
python inscript.py --help
```

Run the full test suite:
```powershell
cd inscript_package
python test_lexer.py
python test_parser.py
python test_analyzer.py
python test_interpreter.py
python test_stdlib.py
python test_v12.py
```

All six must pass before you submit a pull request.

## Code Structure

| File | Purpose |
|---|---|
| `lexer.py` | Tokenizer — add new token types here |
| `parser.py` | AST builder — add new syntax here |
| `ast_nodes.py` | AST node definitions |
| `analyzer.py` | Semantic analysis and type checking |
| `interpreter.py` | Tree-walk interpreter |
| `stdlib.py` | Standard library (18 built-in modules) |
| `stdlib_values.py` | Built-in types: Vec2, Vec3, Color, Rect |
| `errors.py` | Error classes |
| `repl.py` | Interactive REPL |

## Pull Request Rules

1. Fork the repo, create a branch: `git checkout -b fix/your-fix-name`
2. Every new stdlib function needs a test in `test_stdlib.py`
3. Every new language feature needs a test in `test_interpreter.py`
4. Run all six test files — all must pass
5. Write a clear PR description: what changed and why

## Language Design Principles

1. **Game-first** — if a feature helps game developers, it gets priority
2. **Readable** — code should be obvious to a beginner
3. **Honest** — do not add syntax that does nothing (no stubs in the language itself)

## Code of Conduct

Be respectful. Provide constructive feedback. Keep discussions professional.