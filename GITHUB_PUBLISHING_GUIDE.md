# InScript — GitHub Publishing Guide & VS Code Setup

> **Short answer:** Do NOT delete the old repo. Use `git` to replace files and push a new version tag. This preserves your commit history, stars, forks, and issues. It takes about 10 minutes.

---

## Part 1 — GitHub Publishing Strategy

### Should you delete the old files?

**No.** Here's why and what to do instead:

| Approach | Pros | Cons |
|---|---|---|
| ❌ Delete repo, create new | Fresh start | Lose stars, forks, issue history, SEO ranking, any existing cloners |
| ✅ Push to existing repo with new files | Keep history, stars, forks | None — this is exactly what git is for |
| ✅ Force push a clean commit | History starts fresh but repo is preserved | Lose old commits (fine for a solo project) |

**Recommended: Option 2 (regular push).** Replace all files, commit with a clear version message.

---

## Part 2 — Step-by-Step: Publishing to GitHub

### Prerequisites

- Git installed: `git --version`
- GitHub account with your repo already created (or create one at github.com/new)

---

### Step 1 — Download your new files from Claude

Download all the files Claude produced. You need these:

```
ast_nodes.py
environment.py
errors.py
inscript.py
interpreter.py
lexer.py
parser.py
repl.py
setup.py
stdlib.py
stdlib_values.py
analyzer.py
README.md
test_interpreter.py
test_parser.py
test_lexer.py
test_analyzer.py
test_stdlib.py
examples/asteroid_blaster.ins
.vscode/tasks.json
.vscode/launch.json
.gitignore
InScript_Language_Audit.md
```

---

### Step 2 — Clone your existing repo (or initialize fresh)

**If you already have a GitHub repo:**
```bash
git clone https://github.com/YOUR_USERNAME/inscript.git
cd inscript
```

**If starting fresh:**
```bash
mkdir inscript && cd inscript
git init
git remote add origin https://github.com/YOUR_USERNAME/inscript.git
```

---

### Step 3 — Replace all files

Copy all the new files you downloaded into the repo folder. Then verify:

```bash
ls -la
# Should show: inscript.py, interpreter.py, README.md, etc.

# Also make the example folder
mkdir -p examples
# Copy asteroid_blaster.ins into examples/
```

---

### Step 4 — Stage, commit, push

```bash
# Stage everything
git add -A

# Check what's changing
git status

# Commit with a clear message
git commit -m "v0.6.0: 122 tests passing — generics, ADT enums, error propagation, properties, comptime, pipe chaining fixes"

# Push to GitHub
git push origin main
```

> If your branch is called `master` instead of `main`, use `git push origin master`.

---

### Step 5 — Create a version tag (recommended)

Tags make it easy to reference specific versions and trigger releases:

```bash
git tag -a v0.6.0 -m "InScript 0.6.0 — Phase 33 complete, 122/122 tests"
git push origin v0.6.0
```

You'll now see the tag in GitHub under **Releases**. Click it and add release notes.

---

### Step 6 — Create a GitHub Release (optional but professional)

1. Go to your GitHub repo
2. Click **Releases** (right side panel) → **Draft a new release**
3. Choose tag: `v0.6.0`
4. Title: `InScript 0.6.0 — Full Language Runtime`
5. Description (paste this):

```markdown
## What's New in 0.6.0

### New Features
- ✅ Generics: `struct Stack<T>`, `T[]`, `Stack<int> {}`
- ✅ Error propagation `?` with `Ok(v)`, `Err(e)`, `unwrap()`, `unwrap_or()`
- ✅ `comptime { }` block evaluation
- ✅ Pipe operator chaining: `x |> f |> g |> h`
- ✅ ADT enum destructuring: `case Circle(r) { ... }`
- ✅ Properties `get`/`set` with correct setter binding
- ✅ Labeled `break`/`continue` propagation fixed
- ✅ Float display: `4.0` stays `"4.0"` not `"4"`

### Tests
122 tests passing, 0 failures.

### Run the demo
```bash
git clone https://github.com/YOUR_USERNAME/inscript.git
cd inscript
python inscript.py examples/asteroid_blaster.ins
```
```

6. Click **Publish release**

---

## Part 3 — Running in VS Code (After Cloning)

### Step 1 — Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/inscript.git
cd inscript
code .
```

### Step 2 — Select Python interpreter

- Press `Ctrl+Shift+P`
- Type: `Python: Select Interpreter`
- Choose Python 3.10 or higher

### Step 3 — Run the demo with Ctrl+Shift+B

The `.vscode/tasks.json` is already in the repo. Press:

- **`Ctrl+Shift+B`** → Runs the currently open `.ins` file
- **`Ctrl+Shift+P`** → `Tasks: Run Task` → `Run example: Asteroid Blaster`
- **`Ctrl+Shift+P`** → `Tasks: Run Task` → `InScript REPL`

### Step 4 — Or press F5

The `.vscode/launch.json` is also included. With any `.ins` file open, press **F5** to run it immediately through the InScript interpreter.

---

## Part 4 — Recommended Repo Structure on GitHub

After pushing, your repo should look like this:

```
inscript/
├── README.md                    ← Auto-displayed on GitHub homepage
├── .gitignore
├── setup.py                     ← For pip install inscript-lang
├── InScript_Language_Audit.md   ← Full language audit
│
├── inscript.py                  ← Entry point
├── lexer.py
├── parser.py
├── ast_nodes.py
├── interpreter.py               ← Core (122 tests)
├── analyzer.py
├── environment.py
├── errors.py
├── stdlib.py
├── stdlib_values.py
├── repl.py
│
├── examples/
│   └── asteroid_blaster.ins     ← Demo: shows 15+ language features
│
├── .vscode/
│   ├── tasks.json               ← Ctrl+Shift+B to run
│   └── launch.json              ← F5 to run
│
└── tests/
    ├── test_interpreter.py      ← 122 tests
    ├── test_parser.py
    ├── test_lexer.py
    ├── test_analyzer.py
    └── test_stdlib.py
```

---

## Part 5 — Common Git Issues & Fixes

### "Permission denied" when pushing
```bash
# Use HTTPS with a personal access token
# Go to: github.com → Settings → Developer Settings → Personal access tokens
git remote set-url origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/inscript.git
git push origin main
```

### "Rejected — non-fast-forward"
```bash
# Your local is behind — pull first, then push
git pull origin main --rebase
git push origin main
```

### "Branch 'main' not found" (repo uses 'master')
```bash
git push origin master
# Or rename your local branch:
git branch -M main
git push -u origin main
```

### Want to completely replace history (start fresh but keep the repo)
```bash
git checkout --orphan fresh
git add -A
git commit -m "v0.6.0: fresh start"
git branch -D main         # delete old main
git branch -M fresh main   # rename fresh to main
git push origin main --force
```

---

## Summary: The 4-Command Publish

```bash
git clone https://github.com/YOUR_USERNAME/inscript.git && cd inscript
# ... copy all new files into this folder ...
git add -A && git commit -m "v0.6.0: 122 tests, full language runtime"
git push origin main
git tag v0.6.0 && git push origin v0.6.0
```

Done. Your repo is live with all new files.
