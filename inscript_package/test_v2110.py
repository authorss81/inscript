"""
test_v2110.py — InScript v2.11.0
================================================================
Export Pipeline tests:
  • scaffold_project: directory layout, inscript.toml, main.ins, .gitignore
  • build_desktop: output dir, run.py/sh/bat, runtime copy, asset copy, build.toml
  • build_web: index.html content, inscript_runtime copy, asset copy, build.toml
  • build_android: pyproject.toml, app.py, build.toml (briefcase not required)
  • _read_manifest: parses inscript.toml correctly
  • _collect_assets: finds assets under assets/ and scenes/
  • _collect_sources: finds .ins files recursively
  • _write_build_manifest: creates build.toml with correct fields
  • run_build: routes correctly, returns 0/1
  • Unknown target returns 1

All tests are headless — no pygame, no briefcase, no network.
"""
import sys, os, tempfile, shutil
sys.path.insert(0, os.path.dirname(__file__))

from export_pipeline import (
    scaffold_project, build_desktop, build_web, build_android,
    _read_manifest, _collect_assets, _collect_sources,
    _write_build_manifest, run_build, BuildResult,
    MANIFEST_FILE, BUILD_DIR, BUILD_MANIFEST,
)

PASS = 0; FAIL = 0

def ok(name):
    global PASS; PASS += 1; print(f"  PASS  {name}")

def fail(name, msg=""):
    global FAIL; FAIL += 1; print(f"  FAIL  {name}: {msg}")

def check(name, got, expected):
    if got == expected: ok(name)
    else: fail(name, f"want {expected!r}, got {got!r}")

def check_true(name, expr, msg=""):
    if expr: ok(name)
    else: fail(name, msg or "expected True")

def check_contains(name, text, sub):
    if sub in str(text): ok(name)
    else: fail(name, f"expected {sub!r} in {text!r}")

def make_tmpdir():
    return tempfile.mkdtemp(prefix="inscript_v2110_")

def make_project(name="testgame"):
    """Create a minimal test project in a temp dir. Returns (tmpdir, proj_dir)."""
    tmp = make_tmpdir()
    root = os.path.join(tmp, name)
    os.makedirs(os.path.join(root, "src"))
    os.makedirs(os.path.join(root, "assets", "sprites"))
    os.makedirs(os.path.join(root, "assets", "sfx"))
    os.makedirs(os.path.join(root, "scenes"))
    # inscript.toml
    with open(os.path.join(root, MANIFEST_FILE), "w") as f:
        f.write('[package]\nname = "testgame"\nversion = "1.2.3"\nentry = "src/main.ins"\n')
    # src/main.ins
    with open(os.path.join(root, "src", "main.ins"), "w") as f:
        f.write('let x = 42\n')
    # Assets
    with open(os.path.join(root, "assets", "sprites", "hero.png"), "wb") as f:
        f.write(b"FAKE_PNG")
    with open(os.path.join(root, "assets", "sfx", "jump.wav"), "wb") as f:
        f.write(b"FAKE_WAV")
    with open(os.path.join(root, "scenes", "main.inscene"), "w") as f:
        f.write('[scene]\nname = "main"\nroot = "MainScene"\n')
    return tmp, root

# ─────────────────────────────────────────────────────────────────────────────
# 1. scaffold_project
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 1. scaffold_project ────────────────────────────────────────────────")

tmp1 = make_tmpdir()
try:
    root1 = scaffold_project("mygame", dest_dir=tmp1)

    check_true("project root created",    os.path.isdir(root1))
    check_true("src/ created",            os.path.isdir(os.path.join(root1, "src")))
    check_true("assets/sprites/ created", os.path.isdir(os.path.join(root1, "assets", "sprites")))
    check_true("assets/sfx/ created",     os.path.isdir(os.path.join(root1, "assets", "sfx")))
    check_true("assets/fonts/ created",   os.path.isdir(os.path.join(root1, "assets", "fonts")))
    check_true("assets/maps/ created",    os.path.isdir(os.path.join(root1, "assets", "maps")))
    check_true("scenes/ created",         os.path.isdir(os.path.join(root1, "scenes")))
    check_true("build/ created",          os.path.isdir(os.path.join(root1, "build")))
    check_true("inscript.toml created",   os.path.isfile(os.path.join(root1, MANIFEST_FILE)))
    check_true("src/main.ins created",    os.path.isfile(os.path.join(root1, "src", "main.ins")))
    check_true("scenes/main.inscene",     os.path.isfile(os.path.join(root1, "scenes", "main.inscene")))
    check_true(".gitignore created",      os.path.isfile(os.path.join(root1, ".gitignore")))
    check_true("README.md created",       os.path.isfile(os.path.join(root1, "README.md")))

    toml  = open(os.path.join(root1, MANIFEST_FILE)).read()
    check_contains("toml has name",    toml, 'name        = "mygame"')
    check_contains("toml has entry",   toml, 'entry       = "src/main.ins"')
    check_contains("toml has stdlib",  toml, "stdlib")

    main_ins = open(os.path.join(root1, "src", "main.ins")).read()
    check_contains("main.ins has node", main_ins, "node MainScene")
    check_contains("main.ins has _ready", main_ins, "_ready()")

    git = open(os.path.join(root1, ".gitignore")).read()
    check_contains(".gitignore has build/", git, "build/")
    check_contains(".gitignore has *.ibc",  git, "*.ibc")

    # FileExistsError on duplicate
    try:
        scaffold_project("mygame", dest_dir=tmp1)
        fail("duplicate project should raise FileExistsError")
    except FileExistsError:
        ok("duplicate project raises FileExistsError")

finally:
    shutil.rmtree(tmp1, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 2. _read_manifest
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 2. _read_manifest ──────────────────────────────────────────────────")

tmp2 = make_tmpdir()
try:
    with open(os.path.join(tmp2, MANIFEST_FILE), "w") as f:
        f.write('[package]\nname = "demo"\nversion = "2.0.0"\nentry = "src/game.ins"\n')
    m = _read_manifest(tmp2)
    check("name",    m.get("package", {}).get("name"),    "demo")
    check("version", m.get("package", {}).get("version"), "2.0.0")
    check("entry",   m.get("package", {}).get("entry"),   "src/game.ins")

    # Missing manifest → empty dict
    m2 = _read_manifest("/nonexistent_path_xyz")
    check("missing manifest returns empty dict", m2, {})
finally:
    shutil.rmtree(tmp2, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 3. _collect_assets / _collect_sources
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 3. _collect_assets / _collect_sources ──────────────────────────────")

tmp3, root3 = make_project()
try:
    assets = _collect_assets(root3)
    check("2 assets under assets/",  len([a for a in assets if a.startswith("assets")]), 2)
    check_true("hero.png in assets", any("hero.png" in a for a in assets))
    check_true("jump.wav in assets", any("jump.wav" in a for a in assets))
    check_true("inscene in assets",  any(".inscene" in a for a in assets))

    sources = _collect_sources(root3)
    check_true("main.ins in sources", any("main.ins" in s for s in sources))
    check_true("no build/ in sources", not any("build" + os.sep in s for s in sources))
finally:
    shutil.rmtree(tmp3, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 4. _write_build_manifest
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 4. _write_build_manifest ───────────────────────────────────────────")

tmp4 = make_tmpdir()
try:
    bm_path = _write_build_manifest(tmp4, {
        "target": "desktop", "version": "1.0.0",
        "entry": "src/main.ins", "inscript_version": "2.11.0",
        "artifacts": {"run_py": "run.py"},
        "asset_hashes": {"assets/hero.png": "abc123"},
    })
    check_true("build.toml created",     os.path.isfile(bm_path))
    content = open(bm_path).read()
    check_contains("target in manifest",  content, 'target     = "desktop"')
    check_contains("version in manifest", content, 'version    = "1.0.0"')
    check_contains("entry in manifest",   content, 'entry      = "src/main.ins"')
    check_contains("artifact in manifest",content, 'run_py = "run.py"')
    check_contains("asset hash",          content, "abc123")
finally:
    shutil.rmtree(tmp4, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 5. build_desktop
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 5. build_desktop ───────────────────────────────────────────────────")

tmp5, root5 = make_project()
try:
    result = build_desktop(root5)
    out    = os.path.join(root5, BUILD_DIR, "desktop")

    check("BuildResult type",          type(result).__name__, "BuildResult")
    check("target=desktop",            result.target,         "desktop")
    check("success=True",              result.success,        True)
    check_true("output_dir exists",    os.path.isdir(result.output_dir))

    check_true("run.py created",       os.path.isfile(os.path.join(out, "run.py")))
    check_true("run.sh created",       os.path.isfile(os.path.join(out, "run.sh")))
    check_true("run.bat created",      os.path.isfile(os.path.join(out, "run.bat")))
    check_true("build.toml created",   os.path.isfile(os.path.join(out, BUILD_MANIFEST)))
    check_true("runtime dir created",  os.path.isdir(os.path.join(out, "inscript_runtime")))
    check_true("inscript.py in runtime", os.path.isfile(
        os.path.join(out, "inscript_runtime", "inscript.py")))
    check_true("src/ copied",          os.path.isdir(os.path.join(out, "src")))
    check_true("main.ins in src",      os.path.isfile(os.path.join(out, "src", "main.ins")))
    check_true("assets/ copied",       os.path.isdir(os.path.join(out, "assets")))

    run_py = open(os.path.join(out, "run.py")).read()
    check_contains("run.py has sys.path insert", run_py, "inscript_runtime")
    check_contains("run.py has entry point",     run_py, "src/main.ins")

    bm_content = open(os.path.join(out, BUILD_MANIFEST)).read()
    check_contains("build.toml target=desktop", bm_content, 'target     = "desktop"')
    check_contains("build.toml version",        bm_content, 'version    = "1.2.3"')

    check_true("artifacts non-empty",  len(result.artifacts) >= 3)

finally:
    shutil.rmtree(tmp5, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 6. build_web
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 6. build_web ───────────────────────────────────────────────────────")

tmp6, root6 = make_project()
try:
    result6 = build_web(root6)
    out6    = os.path.join(root6, BUILD_DIR, "web")

    check("web target",         result6.target,  "web")
    check("web success",        result6.success, True)
    check_true("index.html",    os.path.isfile(os.path.join(out6, "index.html")))
    check_true("runtime dir",   os.path.isdir(os.path.join(out6, "inscript_runtime")))
    check_true("assets copied", os.path.isdir(os.path.join(out6, "assets")))
    check_true("src copied",    os.path.isdir(os.path.join(out6, "src")))
    check_true("build.toml",    os.path.isfile(os.path.join(out6, BUILD_MANIFEST)))

    html = open(os.path.join(out6, "index.html")).read()
    check_contains("html has pyodide script",  html, "pyodide.js")
    check_contains("html has canvas",          html, "<canvas")
    check_contains("html has title",           html, "testgame")
    check_contains("html loads entry point",   html, "src/main.ins")
    check_contains("html has inscript_runtime",html, "inscript_runtime")

    bm6 = open(os.path.join(out6, BUILD_MANIFEST)).read()
    check_contains("web build.toml target", bm6, 'target     = "web"')

finally:
    shutil.rmtree(tmp6, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 7. build_android (briefcase not required — checks scaffold only)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 7. build_android (scaffold) ────────────────────────────────────────")

tmp7, root7 = make_project()
try:
    result7 = build_android(root7)
    out7    = os.path.join(root7, BUILD_DIR, "android")

    check_true("android out_dir created",    os.path.isdir(out7))
    check_true("pyproject.toml created",     os.path.isfile(os.path.join(out7, "pyproject.toml")))
    check_true("app.py created",             os.path.isfile(os.path.join(out7, "app.py")))
    check_true("build.toml created",         os.path.isfile(os.path.join(out7, BUILD_MANIFEST)))

    pyproj = open(os.path.join(out7, "pyproject.toml")).read()
    check_contains("pyproject has project_name", pyproj, 'project_name = "testgame"')
    check_contains("pyproject has version",      pyproj, 'version      = "1.2.3"')
    check_contains("pyproject has inscript-lang",pyproj, "inscript-lang")

    app_py = open(os.path.join(out7, "app.py")).read()
    check_contains("app.py imports inscript",    app_py, "import inscript")
    check_contains("app.py has entry",           app_py, "src/main.ins")

    # Without briefcase, should return errors (not crash)
    check_true("android: artifacts generated",   len(result7.artifacts) >= 2)

finally:
    shutil.rmtree(tmp7, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 8. run_build routing
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 8. run_build routing ───────────────────────────────────────────────")

tmp8, root8 = make_project()
try:
    ret_desktop = run_build("desktop", root8)
    check("run_build desktop returns 0", ret_desktop, 0)

    ret_web = run_build("web", root8)
    check("run_build web returns 0",     ret_web,     0)

    ret_bad = run_build("playstation5", root8)
    check("unknown target returns 1",    ret_bad,     1)

finally:
    shutil.rmtree(tmp8, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 9. BuildResult fields
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 9. BuildResult fields ──────────────────────────────────────────────")

br = BuildResult("desktop", True, "/out", ["run.py", "build.toml"], [], 42.0)
check("target",       br.target,      "desktop")
check("success",      br.success,     True)
check("output_dir",   br.output_dir,  "/out")
check("artifacts",    br.artifacts,   ["run.py", "build.toml"])
check("errors",       br.errors,      [])
check("elapsed_ms",   br.elapsed_ms,  42.0)
check_true("repr OK", "desktop" in repr(br))

# ─────────────────────────────────────────────────────────────────────────────
# 10. build idempotency — second build overwrites cleanly
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 10. Build idempotency ──────────────────────────────────────────────")

tmp10, root10 = make_project()
try:
    r1 = build_desktop(root10)
    r2 = build_desktop(root10)   # second run — should overwrite, not crash
    check("second desktop build success", r2.success, True)
    check_true("run.py still exists", os.path.isfile(
        os.path.join(root10, BUILD_DIR, "desktop", "run.py")))
finally:
    shutil.rmtree(tmp10, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
total = PASS + FAIL
print(f"InScript v2.11.0  —  {PASS}/{total} tests passed", end="")
if FAIL:
    print(f"  ❌ {FAIL} FAILED")
    sys.exit(1)
else:
    print("  ✅ ALL PASS")
    sys.exit(0)
