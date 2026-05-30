# -*- coding: utf-8 -*-
"""
export_pipeline.py — InScript v2.11.0  Export Pipeline
================================================================
`inscript build --target <target> [project_dir]`

Supported targets
─────────────────
  desktop   → self-contained directory + launch script
              (embeds Python + inscript runtime + all assets)
  web       → index.html + Pyodide WASM bundle + assets
  android   → APK via BeeWare Briefcase (requires: pip install briefcase)
  ibc       → ahead-of-time bytecode compilation (pre-existing, improved)

`inscript new <name>` → scaffold a standard project layout:
  <name>/
    inscript.toml          project manifest
    src/
      main.ins             entry-point scene
    assets/
      sprites/  sfx/  fonts/  maps/
    scenes/
      main.inscene         root scene file
    build/                 (gitignored output dir)

Build manifest
──────────────
`build/build.toml` is written after every successful build, recording:
  target, version, entry_point, asset_hashes, timestamp.
"""

from __future__ import annotations
import os, sys, shutil, json, hashlib, datetime, textwrap, zipfile
from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

BUILD_DIR      = "build"
MANIFEST_FILE  = "inscript.toml"
ENTRY_DEFAULT  = os.path.join("src", "main.ins")
BUILD_MANIFEST = "build.toml"

VALID_TARGETS  = ("desktop", "web", "android", "ios", "ibc")

# Pyodide CDN base used in web builds
PYODIDE_CDN    = "https://cdn.jsdelivr.net/pyodide/v0.27.0/full/"

# ─────────────────────────────────────────────────────────────────────────────
# BuildResult
# ─────────────────────────────────────────────────────────────────────────────

class BuildResult:
    def __init__(self, target: str, success: bool, output_dir: str,
                 artifacts: List[str], errors: List[str], elapsed_ms: float):
        self.target      = target
        self.success     = success
        self.output_dir  = output_dir
        self.artifacts   = artifacts   # paths of produced files
        self.errors      = errors
        self.elapsed_ms  = elapsed_ms

    def __repr__(self):
        status = "OK" if self.success else "ERR"
        return (f"<BuildResult {self.target} {status} "
                f"artifacts={len(self.artifacts)} {self.elapsed_ms:.0f}ms>")


# ─────────────────────────────────────────────────────────────────────────────
# Project layout helpers
# ─────────────────────────────────────────────────────────────────────────────

def _read_manifest(project_dir: str) -> dict:
    path = os.path.join(project_dir, MANIFEST_FILE)
    if not os.path.isfile(path):
        return {}
    try:
        from inscript import _parse_toml_simple
        with open(path, encoding="utf-8") as f:
            return _parse_toml_simple(f.read())
    except Exception:
        return {}


def _entry_point(project_dir: str, manifest: dict) -> str:
    """Resolve the .ins entry-point from manifest or default."""
    ep = manifest.get("package", {}).get("entry", ENTRY_DEFAULT)
    return os.path.join(project_dir, ep)


def _collect_assets(project_dir: str) -> List[str]:
    """Walk assets/ and scenes/ and return all file paths (relative to project_dir)."""
    assets = []
    for sub in ("assets", "scenes"):
        base = os.path.join(project_dir, sub)
        if not os.path.isdir(base):
            continue
        for root, _, files in os.walk(base):
            for fn in files:
                full = os.path.join(root, fn)
                assets.append(os.path.relpath(full, project_dir))
    return sorted(assets)


def _collect_sources(project_dir: str) -> List[str]:
    """Return all .ins files (relative to project_dir)."""
    sources = []
    for root, _, files in os.walk(project_dir):
        for fn in files:
            if fn.endswith(".ins"):
                full = os.path.join(root, fn)
                rel  = os.path.relpath(full, project_dir)
                if not rel.startswith("build" + os.sep):
                    sources.append(rel)
    return sorted(sources)


def _sha256_file(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_build_manifest(output_dir: str, meta: dict) -> str:
    """Write build/build.toml and return its path."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, BUILD_MANIFEST)
    lines = [
        "# InScript Build Manifest — auto-generated\n",
        f'generated  = "{datetime.datetime.utcnow().isoformat()}Z"\n',
        f'target     = "{meta.get("target", "unknown")}"\n',
        f'version    = "{meta.get("version", "0.0.0")}"\n',
        f'entry      = "{meta.get("entry", "")}"\n',
        f'inscript   = "{meta.get("inscript_version", "")}"\n\n',
        "[artifacts]\n",
    ]
    for k, v in meta.get("artifacts", {}).items():
        lines.append(f'{k} = "{v}"\n')
    lines.append("\n[asset_hashes]\n")
    for k, v in meta.get("asset_hashes", {}).items():
        safe_k = k.replace("\\", "/").replace('"', "")
        lines.append(f'"{safe_k}" = "{v}"\n')
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Target: desktop
# ─────────────────────────────────────────────────────────────────────────────

def build_desktop(project_dir: str = ".") -> BuildResult:
    """
    Build a self-contained desktop distribution.

    Output layout:
      build/desktop/
        run.py             — launcher that invokes inscript on main.ins
        run.sh             — Unix launcher
        run.bat            — Windows launcher
        inscript_runtime/  — copy of the InScript runtime (.py files)
        assets/            — copy of project assets/
        scenes/            — copy of project scenes/
        src/               — copy of .ins source files
        build.toml         — build manifest
    """
    import time
    t0 = time.perf_counter()
    errors: List[str] = []
    artifacts: List[str] = []

    manifest      = _read_manifest(project_dir)
    pkg           = manifest.get("package", {})
    version       = pkg.get("version", "0.0.0")
    name          = pkg.get("name", os.path.basename(os.path.abspath(project_dir)))
    entry_rel     = pkg.get("entry", ENTRY_DEFAULT)
    entry_abs     = os.path.join(project_dir, entry_rel)

    out_dir       = os.path.join(project_dir, BUILD_DIR, "desktop")
    os.makedirs(out_dir, exist_ok=True)

    # ── Copy runtime .py files ───────────────────────────────────────────────
    runtime_src = os.path.dirname(os.path.abspath(__file__))
    runtime_dst = os.path.join(out_dir, "inscript_runtime")
    os.makedirs(runtime_dst, exist_ok=True)
    runtime_modules = [
        "inscript.py", "lexer.py", "parser.py", "interpreter.py",
        "compiler.py", "vm.py", "analyzer.py", "errors.py",
        "environment.py", "ast_nodes.py",
        "stdlib.py", "stdlib_extended.py", "stdlib_extended_2.py",
        "stdlib_game.py", "stdlib_values.py", "stdlib_assets.py",
        "scene_tree.py", "hot_reload.py", "pygame_backend.py",
    ]
    for mod in runtime_modules:
        src = os.path.join(runtime_src, mod)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(runtime_dst, mod))

    # ── Copy source + assets ─────────────────────────────────────────────────
    for sub in ("src", "assets", "scenes"):
        src = os.path.join(project_dir, sub)
        dst = os.path.join(out_dir, sub)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    # ── Write launchers ──────────────────────────────────────────────────────
    run_py = os.path.join(out_dir, "run.py")
    with open(run_py, "w") as f:
        f.write(textwrap.dedent(f"""\
            #!/usr/bin/env python3
            # InScript Desktop Launcher — {name} v{version}
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "inscript_runtime"))
            import inscript
            sys.exit(inscript.main(["{entry_rel}"]))
        """))
    artifacts.append(run_py)

    run_sh = os.path.join(out_dir, "run.sh")
    with open(run_sh, "w") as f:
        f.write(f"#!/bin/sh\ncd \"$(dirname \"$0\")\"\npython3 run.py \"$@\"\n")
    try:
        os.chmod(run_sh, 0o755)
    except Exception:
        pass
    artifacts.append(run_sh)

    run_bat = os.path.join(out_dir, "run.bat")
    with open(run_bat, "w") as f:
        f.write(f"@echo off\ncd /d \"%~dp0\"\npython run.py %*\n")
    artifacts.append(run_bat)

    # ── Compute asset hashes ─────────────────────────────────────────────────
    asset_hashes = {}
    for rel in _collect_assets(project_dir):
        full = os.path.join(project_dir, rel)
        asset_hashes[rel] = _sha256_file(full)

    # ── Write build manifest ─────────────────────────────────────────────────
    from inscript import VERSION as _IV
    bm = _write_build_manifest(out_dir, {
        "target": "desktop", "version": version, "entry": entry_rel,
        "inscript_version": _IV,
        "artifacts": {"run_py": "run.py", "run_sh": "run.sh", "run_bat": "run.bat"},
        "asset_hashes": asset_hashes,
    })
    artifacts.append(bm)

    elapsed = (time.perf_counter() - t0) * 1000
    print(f"[build:desktop] ✅ {name} v{version} → {out_dir}  ({elapsed:.0f}ms)")
    return BuildResult("desktop", True, out_dir, artifacts, errors, elapsed)


# ─────────────────────────────────────────────────────────────────────────────
# Target: web
# ─────────────────────────────────────────────────────────────────────────────

_WEB_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name}</title>
  <style>
    body {{ margin:0; background:#111; display:flex; flex-direction:column;
           align-items:center; justify-content:center; height:100vh;
           font-family:monospace; color:#ccc; }}
    #canvas {{ border:2px solid #333; }}
    #status  {{ margin-top:8px; font-size:12px; }}
  </style>
</head>
<body>
  <canvas id="canvas" width="{width}" height="{height}"></canvas>
  <div id="status">Loading InScript runtime…</div>
  <script src="{pyodide_cdn}pyodide.js"></script>
  <script type="module">
    const status = document.getElementById("status");

    async function main() {{
      status.textContent = "Loading Pyodide…";
      const pyodide = await loadPyodide({{ indexURL: "{pyodide_cdn}" }});
      status.textContent = "Loading InScript runtime…";

      // Fetch and exec inscript runtime
      const r = await fetch("inscript_runtime/inscript.py");
      const src = await r.text();
      pyodide.runPython(src);

      // Fetch and run entry point
      const e = await fetch("{entry}");
      const game = await e.text();
      status.textContent = "Running {name}…";
      pyodide.runPython(game);
    }}

    main().catch(err => {{
      status.textContent = "Error: " + err.message;
      console.error(err);
    }});
  </script>
</body>
</html>
"""

def build_web(project_dir: str = ".") -> BuildResult:
    """
    Build a Pyodide-based web export.

    Output layout:
      build/web/
        index.html             — shell page with Pyodide loader
        inscript_runtime/      — minimal runtime .py files
        assets/                — copied assets
        src/                   — .ins source files
        build.toml
    """
    import time
    t0 = time.perf_counter()
    errors: List[str] = []
    artifacts: List[str] = []

    manifest = _read_manifest(project_dir)
    pkg      = manifest.get("package", {})
    version  = pkg.get("version", "0.0.0")
    name     = pkg.get("name", os.path.basename(os.path.abspath(project_dir)))
    entry    = pkg.get("entry", ENTRY_DEFAULT)
    width    = int(pkg.get("window_width",  800))
    height   = int(pkg.get("window_height", 600))

    out_dir = os.path.join(project_dir, BUILD_DIR, "web")
    os.makedirs(out_dir, exist_ok=True)

    # Write index.html
    html_path = os.path.join(out_dir, "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(_WEB_TEMPLATE.format(
            name=name, width=width, height=height,
            pyodide_cdn=PYODIDE_CDN, entry=entry,
        ))
    artifacts.append(html_path)

    # Copy minimal runtime
    runtime_src = os.path.dirname(os.path.abspath(__file__))
    runtime_dst = os.path.join(out_dir, "inscript_runtime")
    os.makedirs(runtime_dst, exist_ok=True)
    web_runtime_modules = [
        "inscript.py", "lexer.py", "parser.py", "interpreter.py",
        "compiler.py", "vm.py", "analyzer.py", "errors.py",
        "environment.py", "ast_nodes.py",
        "stdlib.py", "stdlib_extended.py", "stdlib_extended_2.py",
        "stdlib_game.py", "stdlib_values.py", "stdlib_assets.py",
        "scene_tree.py", "hot_reload.py",
    ]
    for mod in web_runtime_modules:
        src = os.path.join(runtime_src, mod)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(runtime_dst, mod))

    # Copy assets and source
    for sub in ("assets", "src", "scenes"):
        s = os.path.join(project_dir, sub)
        d = os.path.join(out_dir, sub)
        if os.path.isdir(s):
            if os.path.exists(d):
                shutil.rmtree(d)
            shutil.copytree(s, d)

    # Compute asset hashes
    asset_hashes = {r: _sha256_file(os.path.join(project_dir, r))
                    for r in _collect_assets(project_dir)}

    from inscript import VERSION as _IV
    bm = _write_build_manifest(out_dir, {
        "target": "web", "version": version, "entry": entry,
        "inscript_version": _IV, "pyodide_cdn": PYODIDE_CDN,
        "artifacts": {"index": "index.html"},
        "asset_hashes": asset_hashes,
    })
    artifacts.append(bm)

    elapsed = (time.perf_counter() - t0) * 1000
    print(f"[build:web] ✅ {name} v{version} → {out_dir}  ({elapsed:.0f}ms)")
    print(f"[build:web] Serve with: python -m http.server 8080 --directory {out_dir}")
    return BuildResult("web", True, out_dir, artifacts, errors, elapsed)


# ─────────────────────────────────────────────────────────────────────────────
# Target: android
# ─────────────────────────────────────────────────────────────────────────────

def build_android(project_dir: str = ".") -> BuildResult:
    """
    Build an Android APK via BeeWare Briefcase.
    Requires: pip install briefcase

    Steps:
      1. Generate a Briefcase project layout in build/android/
      2. Run `briefcase create android` + `briefcase build android`
      3. APK lands in build/android/android/<name>-<ver>/
    """
    import time, subprocess
    t0 = time.perf_counter()
    errors: List[str] = []
    artifacts: List[str] = []

    # Check briefcase is available
    briefcase_ok = shutil.which("briefcase") is not None
    if not briefcase_ok:
        try:
            subprocess.run([sys.executable, "-m", "briefcase", "--version"],
                           check=True, capture_output=True)
            briefcase_ok = True
        except Exception:
            pass

    manifest = _read_manifest(project_dir)
    pkg      = manifest.get("package", {})
    version  = pkg.get("version", "0.0.0")
    name     = pkg.get("name", "mygame")
    entry    = pkg.get("entry", ENTRY_DEFAULT)
    bundle   = pkg.get("bundle", f"dev.inscript.{name}")

    out_dir  = os.path.join(project_dir, BUILD_DIR, "android")
    os.makedirs(out_dir, exist_ok=True)

    # Write pyproject.toml for Briefcase
    bp_path = os.path.join(out_dir, "pyproject.toml")
    with open(bp_path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(f"""\
            [tool.briefcase]
            project_name = "{name}"
            bundle       = "{bundle}"
            version      = "{version}"
            description  = "Built with InScript"
            license      = "MIT"
            url          = "https://github.com/authorss81/inscript"

            [tool.briefcase.app.{name}]
            formal_name  = "{name}"
            description  = "Built with InScript"
            sources      = ["."]
            requires     = ["inscript-lang"]

            [tool.briefcase.app.{name}.android]
            requires = ["toga-android"]
        """))
    artifacts.append(bp_path)

    # Copy source into build/android/
    for sub in ("src", "assets", "scenes"):
        s = os.path.join(project_dir, sub)
        d = os.path.join(out_dir, sub)
        if os.path.isdir(s):
            if os.path.exists(d): shutil.rmtree(d)
            shutil.copytree(s, d)

    # Main app entry
    app_py = os.path.join(out_dir, "app.py")
    with open(app_py, "w") as f:
        f.write(textwrap.dedent(f"""\
            # InScript Android entry — generated by inscript build --target android
            import sys, os
            try:
                import inscript
                inscript.main(["{entry}"])
            except Exception as e:
                print(f"InScript launch error: {{e}}", file=sys.stderr)
        """))
    artifacts.append(app_py)

    from inscript import VERSION as _IV
    bm = _write_build_manifest(out_dir, {
        "target": "android", "version": version, "entry": entry,
        "inscript_version": _IV, "bundle": bundle,
        "artifacts": {"pyproject": "pyproject.toml", "app": "app.py"},
        "asset_hashes": {},
    })
    artifacts.append(bm)

    if not briefcase_ok:
        msg = ("BeeWare Briefcase not installed. "
               "Install with: pip install briefcase  "
               "Then run from build/android/: briefcase create android && briefcase build android")
        print(f"[build:android] ⚠  {msg}")
        errors.append(msg)
        elapsed = (time.perf_counter() - t0) * 1000
        return BuildResult("android", False, out_dir, artifacts, errors, elapsed)

    # Run briefcase
    try:
        subprocess.run(
            [sys.executable, "-m", "briefcase", "create", "android"],
            cwd=out_dir, check=True
        )
        subprocess.run(
            [sys.executable, "-m", "briefcase", "build", "android"],
            cwd=out_dir, check=True
        )
        print(f"[build:android] ✅ APK built → {out_dir}")
    except subprocess.CalledProcessError as e:
        errors.append(f"briefcase failed: {e}")
        print(f"[build:android] ❌ briefcase error: {e}", file=sys.stderr)

    elapsed = (time.perf_counter() - t0) * 1000
    return BuildResult("android", len(errors) == 0, out_dir, artifacts, errors, elapsed)


# ─────────────────────────────────────────────────────────────────────────────
# Project scaffold: `inscript new <name>`
# ─────────────────────────────────────────────────────────────────────────────

_MAIN_INS_TEMPLATE = """\
# {name} — main scene
# Created by InScript v{inscript_version}

import "asset" as asset

node MainScene {{
    let title: str = "{name}"

    _ready() {{
        print("Welcome to " + title)
    }}

    _update(dt) {{
        # game logic here
    }}

    _draw() {{
        # rendering here
    }}
}}
"""

_INSCRIPT_TOML_TEMPLATE = """\
[package]
name        = "{name}"
version     = "0.1.0"
description = "A game built with InScript"
entry       = "src/main.ins"
stdlib      = ">={inscript_version}"

[dependencies]
# add packages here: math-utils = "^1.0"

[build]
window_width  = 800
window_height = 600
"""

def scaffold_project(name: str, dest_dir: str = ".") -> str:
    """
    Create a standard InScript project layout.
    Returns the project root path.
    """
    from inscript import VERSION as _IV

    root = os.path.join(dest_dir, name)
    if os.path.exists(root):
        raise FileExistsError(f"Directory already exists: {root}")

    # Create directory structure
    for sub in ("src", "assets/sprites", "assets/sfx",
                "assets/fonts", "assets/maps", "scenes", "build"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)

    # inscript.toml
    with open(os.path.join(root, MANIFEST_FILE), "w") as f:
        f.write(_INSCRIPT_TOML_TEMPLATE.format(name=name, inscript_version=_IV))

    # src/main.ins
    with open(os.path.join(root, "src", "main.ins"), "w") as f:
        f.write(_MAIN_INS_TEMPLATE.format(name=name, inscript_version=_IV))

    # scenes/main.inscene
    with open(os.path.join(root, "scenes", "main.inscene"), "w") as f:
        f.write(f'# InScript Scene File\n\n[scene]\nname = "main"\nroot = "MainScene"\n')

    # .gitignore
    with open(os.path.join(root, ".gitignore"), "w") as f:
        f.write("build/\n*.ibc\n__pycache__/\n*.pyc\n.inscript/\n")

    # README.md
    with open(os.path.join(root, "README.md"), "w") as f:
        f.write(textwrap.dedent(f"""\
            # {name}

            Built with [InScript](https://github.com/authorss81/inscript) v{_IV}.

            ## Run
            ```
            inscript src/main.ins
            ```

            ## Build
            ```
            inscript build --target desktop
            inscript build --target web
            ```
        """))

    print(f"[inscript new] ✅ Created project '{name}' at {root}")
    print(f"[inscript new] Run:  cd {name} && inscript src/main.ins")
    return root


# ─────────────────────────────────────────────────────────────────────────────
# Top-level dispatcher called from inscript.py
# ─────────────────────────────────────────────────────────────────────────────

def run_build(target: str, project_dir: str = ".") -> int:
    """
    Entry point called by --build flag in inscript.py.
    Returns exit code (0 = success).
    """
    target = target.lower()
    if target not in VALID_TARGETS:
        print(f"[build] Unknown target '{target}'. Valid: {', '.join(VALID_TARGETS)}",
              file=sys.stderr)
        return 1

    if target == "desktop":
        r = build_desktop(project_dir)
    elif target == "web":
        r = build_web(project_dir)
    elif target == "android":
        r = build_android(project_dir)
    elif target == "ibc":
        # Delegate to existing compile pipeline
        from inscript import cmd_compile
        entry = _entry_point(project_dir, _read_manifest(project_dir))
        return cmd_compile(entry) if os.path.isfile(entry) else 1
    else:
        return 1

    if r.errors:
        for e in r.errors:
            print(f"[build] {e}", file=sys.stderr)
    return 0 if r.success else 1


# ─────────────────────────────────────────────────────────────────────────────
# v2.13.0: Target: iOS
# ─────────────────────────────────────────────────────────────────────────────

def build_ios(project_dir: str = ".") -> BuildResult:
    """
    Build an iOS app via BeeWare Briefcase.
    Requires: macOS + Xcode + pip install briefcase

    Output layout:
      build/ios/
        pyproject.toml   — Briefcase config
        app.py           — InScript iOS entry point
        build.toml       — build manifest
    """
    import time, subprocess
    t0 = time.perf_counter()
    errors: List[str] = []
    artifacts: List[str] = []

    manifest = _read_manifest(project_dir)
    pkg      = manifest.get("package", {})
    version  = pkg.get("version", "0.0.0")
    name     = pkg.get("name", "mygame")
    entry    = pkg.get("entry", ENTRY_DEFAULT)
    bundle   = pkg.get("bundle", f"dev.inscript.{name}")

    out_dir = os.path.join(project_dir, BUILD_DIR, "ios")
    os.makedirs(out_dir, exist_ok=True)

    bp_path = os.path.join(out_dir, "pyproject.toml")
    with open(bp_path, "w") as f:
        f.write(textwrap.dedent(f"""\
            [tool.briefcase]
            project_name = "{name}"
            bundle       = "{bundle}"
            version      = "{version}"
            description  = "Built with InScript"
            license      = "MIT"

            [tool.briefcase.app.{name}]
            formal_name  = "{name}"
            description  = "Built with InScript"
            sources      = ["."]
            requires     = ["inscript-lang"]

            [tool.briefcase.app.{name}.iOS]
            requires = ["toga-iOS"]
        """))
    artifacts.append(bp_path)

    app_py = os.path.join(out_dir, "app.py")
    with open(app_py, "w") as f:
        f.write(textwrap.dedent(f"""\
            # InScript iOS entry — generated by inscript build --target ios
            import sys
            try:
                import inscript
                inscript.main(["{entry}"])
            except Exception as e:
                print(f"InScript launch error: {{e}}", file=sys.stderr)
        """))
    artifacts.append(app_py)

    for sub in ("src", "assets", "scenes"):
        s = os.path.join(project_dir, sub)
        d = os.path.join(out_dir, sub)
        if os.path.isdir(s):
            if os.path.exists(d): shutil.rmtree(d)
            shutil.copytree(s, d)

    from inscript import VERSION as _IV
    bm = _write_build_manifest(out_dir, {
        "target": "ios", "version": version, "entry": entry,
        "inscript_version": _IV, "bundle": bundle,
        "artifacts": {"pyproject": "pyproject.toml", "app": "app.py"},
        "asset_hashes": {},
    })
    artifacts.append(bm)

    # Check platform and briefcase
    if sys.platform != "darwin":
        msg = "iOS builds require macOS. Current platform: " + sys.platform
        errors.append(msg)
        print(f"[build:ios] ⚠  {msg}")
        elapsed = (time.perf_counter() - t0) * 1000
        return BuildResult("ios", False, out_dir, artifacts, errors, elapsed)

    briefcase_ok = shutil.which("briefcase") is not None
    if not briefcase_ok:
        msg = ("BeeWare Briefcase not installed. "
               "Install: pip install briefcase  "
               "Then: cd build/ios && briefcase create iOS && briefcase build iOS")
        errors.append(msg)
        print(f"[build:ios] ⚠  {msg}")
        elapsed = (time.perf_counter() - t0) * 1000
        return BuildResult("ios", False, out_dir, artifacts, errors, elapsed)

    try:
        subprocess.run([sys.executable, "-m", "briefcase", "create", "iOS"],
                       cwd=out_dir, check=True)
        subprocess.run([sys.executable, "-m", "briefcase", "build", "iOS"],
                       cwd=out_dir, check=True)
        print(f"[build:ios] ✅ iOS app built → {out_dir}")
    except subprocess.CalledProcessError as e:
        errors.append(f"briefcase failed: {e}")

    elapsed = (time.perf_counter() - t0) * 1000
    return BuildResult("ios", len(errors) == 0, out_dir, artifacts, errors, elapsed)
