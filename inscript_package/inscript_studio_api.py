# -*- coding: utf-8 -*-
"""
inscript_studio_api.py — InScript v2.12.0  Studio Plugin API
================================================================
Stable extension points that InScript Studio (Electron) and third-party
plugins use to integrate with the runtime.

StudioPlugin   — base class for plugins; override hook methods
StudioAPI      — registry; emit events to all registered plugins
project_inspect — static analysis → JSON scene/node/fn/asset list
error_stream    — format errors as newline-delimited JSON for the IDE panel
"""

from __future__ import annotations
import os, re, json
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Plugin base class
# ─────────────────────────────────────────────────────────────────────────────

class StudioPlugin:
    """
    Base class for Studio plugins.  Override any hook you care about.

    Plugins are registered with the global StudioAPI singleton:
        from inscript_studio_api import get_api
        get_api().register(MyPlugin())
    """
    name: str = "unnamed_plugin"

    def on_scene_save(self, scene_path: str, tree) -> None:
        """Called when a .inscene file is saved from the editor."""

    def on_asset_import(self, handle) -> None:
        """Called when an AssetHandle is registered in the AssetRegistry."""

    def on_error(self, error: dict) -> None:
        """Called when the interpreter raises an InScriptError.
        error is a dict matching InScriptError.to_dict()."""

    def on_breakpoint(self, file: str, line: int, env: dict) -> None:
        """Called when a breakpoint is hit (DAP integration)."""

    def on_reload(self, result) -> None:
        """Called after every successful hot reload."""

    def on_build(self, target: str, output_dir: str, success: bool) -> None:
        """Called after inscript build completes."""

    def __repr__(self):
        return f"<StudioPlugin {self.name}>"


# ─────────────────────────────────────────────────────────────────────────────
# StudioAPI registry
# ─────────────────────────────────────────────────────────────────────────────

class StudioAPI:
    """
    Central registry for Studio plugins.  Emits lifecycle events to all
    registered plugins.  Singleton — use get_api() rather than instantiating.
    """
    def __init__(self):
        self._plugins: List[StudioPlugin] = []

    def register(self, plugin: StudioPlugin) -> "StudioAPI":
        if plugin not in self._plugins:
            self._plugins.append(plugin)
        return self

    def unregister(self, plugin: StudioPlugin) -> bool:
        if plugin in self._plugins:
            self._plugins.remove(plugin)
            return True
        return False

    def plugin_count(self) -> int:
        return len(self._plugins)

    def emit(self, event: str, *args, **kwargs) -> List[Any]:
        """
        Emit an event to all registered plugins.
        Returns list of return values (Nones filtered out).
        """
        results = []
        for plugin in list(self._plugins):
            handler = getattr(plugin, event, None)
            if handler is None:
                continue
            try:
                rv = handler(*args, **kwargs)
                if rv is not None:
                    results.append(rv)
            except Exception as e:
                print(f"[StudioAPI] Plugin '{plugin.name}' error in {event}: {e}")
        return results

    # Convenience emitters matching StudioPlugin hooks
    def emit_scene_save(self, scene_path: str, tree) -> None:
        self.emit("on_scene_save", scene_path, tree)

    def emit_asset_import(self, handle) -> None:
        self.emit("on_asset_import", handle)

    def emit_error(self, error: dict) -> None:
        self.emit("on_error", error)

    def emit_breakpoint(self, file: str, line: int, env: dict) -> None:
        self.emit("on_breakpoint", file, line, env)

    def emit_reload(self, result) -> None:
        self.emit("on_reload", result)

    def emit_build(self, target: str, output_dir: str, success: bool) -> None:
        self.emit("on_build", target, output_dir, success)

    def __repr__(self):
        return f"<StudioAPI plugins={len(self._plugins)}>"


# Module-level singleton
_GLOBAL_API = StudioAPI()

def get_api() -> StudioAPI:
    return _GLOBAL_API


# ─────────────────────────────────────────────────────────────────────────────
# Project introspection — static analysis without running the interpreter
# ─────────────────────────────────────────────────────────────────────────────

# Patterns for extracting declarations from .ins source (fast, no full parse)
_RE_NODE     = re.compile(r'^\s*node\s+(\w+)\s*\{', re.MULTILINE)
_RE_SCENE    = re.compile(r'^\s*scene\s+(\w+)\s*\{', re.MULTILINE)
_RE_STRUCT   = re.compile(r'^\s*struct\s+(\w+)\s*\{', re.MULTILINE)
_RE_FN       = re.compile(r'^\s*(?:export\s+)?fn\s+(\w+)\s*\(', re.MULTILINE)
_RE_TEXTURE  = re.compile(r'@texture\s*\(\s*["\']([^"\']+)["\']', re.MULTILINE)
_RE_SOUND    = re.compile(r'@sound\s*\(\s*["\']([^"\']+)["\']', re.MULTILINE)
_RE_TILEMAP  = re.compile(r'@tilemap\s*\(\s*["\']([^"\']+)["\']', re.MULTILINE)
_RE_FONT     = re.compile(r'@font\s*\(\s*["\']([^"\']+)["\']', re.MULTILINE)
_RE_IMPORT   = re.compile(r'^\s*import\s+["\']([^"\']+)["\']', re.MULTILINE)


def _scan_ins_file(file_path: str) -> dict:
    """
    Scan a single .ins file and return a summary dict:
      {file, nodes, scenes, structs, functions, assets, imports}
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            src = f.read()
    except OSError:
        return {}

    rel = file_path  # caller normalises

    assets = []
    for kind, pat in (("texture", _RE_TEXTURE), ("sound", _RE_SOUND),
                      ("tilemap", _RE_TILEMAP), ("font", _RE_FONT)):
        for m in pat.finditer(src):
            assets.append({"type": kind, "path": m.group(1)})

    return {
        "file":      rel,
        "nodes":     [m.group(1) for m in _RE_NODE.finditer(src)],
        "scenes":    [m.group(1) for m in _RE_SCENE.finditer(src)],
        "structs":   [m.group(1) for m in _RE_STRUCT.finditer(src)],
        "functions": [m.group(1) for m in _RE_FN.finditer(src)],
        "assets":    assets,
        "imports":   [m.group(1) for m in _RE_IMPORT.finditer(src)],
    }


def _scan_inscene_file(file_path: str) -> Optional[dict]:
    """Read a .inscene file and return {file, scene_name, root, nodes}."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return None

    name_m = re.search(r'^name\s*=\s*"([^"]+)"', content, re.MULTILINE)
    root_m = re.search(r'^root\s*=\s*"([^"]+)"', content, re.MULTILINE)
    nodes  = re.findall(r'^type\s*=\s*"([^"]+)"', content, re.MULTILINE)

    return {
        "file":       file_path,
        "scene_name": name_m.group(1) if name_m else "",
        "root":       root_m.group(1) if root_m else "",
        "nodes":      nodes,
    }


def project_inspect(project_dir: str = ".") -> dict:
    """
    Statically analyse a project directory and return a JSON-serialisable
    summary of all declarations.  Used by the Studio scene panel, node
    inspector, and asset browser.

    Returns:
      {
        "project_dir": str,
        "version":     str,            # inscript.VERSION
        "sources":     [...],          # per-file scan results
        "scenes":      [...],          # merged list of scene names
        "nodes":       [...],          # merged list of node names
        "structs":     [...],
        "functions":   [...],
        "assets":      [...],
        "scene_files": [...],          # .inscene file summaries
        "imports":     [...],
      }
    """
    from inscript import VERSION

    project_dir = os.path.abspath(project_dir)
    sources = []
    scene_files = []

    all_scenes    = []
    all_nodes     = []
    all_structs   = []
    all_functions = []
    all_assets    = []
    all_imports   = set()

    # Walk the project for .ins and .inscene files
    for root, dirs, files in os.walk(project_dir):
        # Skip build output and hidden dirs
        dirs[:] = [d for d in dirs
                   if d not in ("build", "__pycache__", "inscript_runtime")
                   and not d.startswith(".")]
        for fn in sorted(files):
            full = os.path.join(root, fn)
            rel  = os.path.relpath(full, project_dir)
            if fn.endswith(".ins"):
                scan = _scan_ins_file(full)
                scan["file"] = rel
                sources.append(scan)
                all_scenes    += [{"name": n, "file": rel} for n in scan["nodes"]]
                all_nodes     += [{"name": n, "file": rel} for n in scan["nodes"]]
                all_structs   += [{"name": n, "file": rel} for n in scan["structs"]]
                all_functions += [{"name": n, "file": rel} for n in scan["functions"]]
                all_assets    += [dict(a, file=rel) for a in scan["assets"]]
                all_imports   |= set(scan["imports"])
            elif fn.endswith(".inscene"):
                sf = _scan_inscene_file(full)
                if sf:
                    sf["file"] = rel
                    scene_files.append(sf)
                    all_scenes.append({"name": sf["scene_name"], "file": rel,
                                       "root": sf["root"]})

    return {
        "project_dir": project_dir,
        "version":     VERSION,
        "sources":     sources,
        "scenes":      all_scenes,
        "nodes":       all_nodes,
        "structs":     all_structs,
        "functions":   all_functions,
        "assets":      all_assets,
        "scene_files": scene_files,
        "imports":     sorted(all_imports),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Error stream — newline-delimited JSON for IDE panels
# ─────────────────────────────────────────────────────────────────────────────

def error_stream(errors: list, file=None) -> None:
    """
    Write errors as newline-delimited JSON to `file` (default: sys.stderr).
    Each line is a self-contained JSON object.

    Format:
      {"type":"error","code":"E0042","message":"...","line":5,"col":3}
      {"type":"error","code":"E0001","message":"...","line":12,"col":1}
    """
    import sys as _sys
    out = file or _sys.stderr
    for err in errors:
        if hasattr(err, "to_dict"):
            d = err.to_dict()
        elif isinstance(err, dict):
            d = err
        else:
            d = {"type": "error", "code": "E0000",
                 "class": type(err).__name__, "message": str(err),
                 "line": 0, "col": 0}
        out.write(json.dumps(d, separators=(",", ":")) + "\n")
    out.flush()
