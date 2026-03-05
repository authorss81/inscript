# InScript v1.0.0 — Publishing Handout

This document has everything you need to publish InScript to PyPI, VS Code Marketplace, and GitHub.

---

## What's In the Package

```
inscript_package/
├── inscript.py          ← CLI entry point (run files, REPL, package manager, LSP)
├── lexer.py             ← Tokenizer
├── parser.py            ← Recursive-descent parser
├── ast_nodes.py         ← AST dataclasses
├── interpreter.py       ← Tree-walk interpreter
├── analyzer.py          ← Static semantic analyzer
├── environment.py       ← Scope resolution
├── errors.py            ← Error / signal types
├── stdlib.py            ← 18 stdlib modules
├── stdlib_values.py     ← Vec2, Color, Rect, Range …
├── repl.py              ← Interactive shell + web playground
├── lsp/
│   ├── server.py        ← LSP server (pygls)
│   ├── diagnostics.py   ← Real-time error squiggles
│   ├── completions.py   ← Autocomplete
│   └── hover.py         ← Hover docs
└── examples/
    └── asteroid_blaster.ins
```

**Test suite:** 331 tests, all passing.

---

## Step 1 — Publish to PyPI

### Prerequisites
```bash
pip install build twine
```

### Build
```bash
# From the project root (where pyproject.toml lives)
python -m build
# Creates dist/inscript_lang-1.0.0-py3-none-any.whl
#         dist/inscript_lang-1.0.0.tar.gz
```

### Upload to Test PyPI first
```bash
twine upload --repository testpypi dist/*
# Username: __token__
# Password: <your testpypi API token>

# Test the install
pip install --index-url https://test.pypi.org/simple/ inscript-lang
inscript --version   # → InScript 1.0.0
```

### Upload to PyPI (production)
```bash
twine upload dist/*
# Username: __token__
# Password: <your pypi API token>
```

Get API tokens at https://pypi.org/manage/account/token/

---

## Step 2 — GitHub Release

### Tag the release
```bash
git add -A
git commit -m "chore: release v1.0.0"
git tag -a v1.0.0 -m "InScript v1.0.0 — stable release"
git push origin main --tags
```

### Create a GitHub Release
1. Go to **Releases → Draft a new release**
2. Tag: `v1.0.0`
3. Title: `InScript v1.0.0 — Stable Release`
4. Body: paste from `CHANGELOG.md` under `[1.0.0]`
5. Attach the built `.whl` and `.tar.gz` files
6. Click **Publish release**

---

## Step 3 — VS Code Extension

### Prerequisites
```bash
npm install -g @vscode/vsce
```

### Build the extension
```bash
cd dist/vscode/
vsce package
# Creates: inscript-1.0.0.vsix
```

### Publish to Marketplace
1. Get a Personal Access Token at https://dev.azure.com
   - Organization: your publisher org
   - Scope: **Marketplace (Publish)**
2. Login: `vsce login <publisher-name>`
3. Publish: `vsce publish`

Or upload the `.vsix` manually at https://marketplace.visualstudio.com/manage

---

## Step 4 — GitHub Pages (Documentation)

1. In repo **Settings → Pages**
2. Source: `Deploy from a branch`
3. Branch: `gh-pages` / root
4. Push a docs site or enable the default README rendering

---

## Step 5 — Binary Builds (optional)

Self-contained executables users can run without Python:

```bash
pip install pyinstaller
cd dist/binary/
pyinstaller inscript.spec

# Output: dist/inscript   (Linux/Mac)
#          dist/inscript.exe  (Windows via Wine or CI)
```

For a full cross-platform release, use GitHub Actions (the workflow is at `dist/github/.github/workflows/release.yml`).

---

## Verify the Published Package

```bash
pip install inscript-lang
inscript --version
# InScript 1.0.0

inscript --repl
# InScript v1.0.0 — Interactive Shell

echo 'print("Hello from InScript!")' > hello.ins
inscript hello.ins
# Hello from InScript!
```

---

## Enable the LSP (for VS Code)

```bash
pip install "inscript-lang[lsp]"
# or
pip install pygls
```

The VS Code extension will auto-detect the language server.

---

## Package Info Summary

| Item | Value |
|---|---|
| PyPI name | `inscript-lang` |
| Version | `1.0.0` |
| Python requirement | `>=3.10` |
| Runtime dependencies | **None** |
| Optional LSP dep | `pygls>=1.3` |
| License | MIT |
| Entry point | `inscript` |
