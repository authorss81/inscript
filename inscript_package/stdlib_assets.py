# -*- coding: utf-8 -*-
"""
stdlib_assets.py — InScript v2.8.0  Asset Pipeline
================================================================
Provides:
  • AssetHandle   — lazy-loading descriptor for a single asset
  • AssetRegistry — global registry; drives load_all, hot-reload,
                    manifest export, and bundling
  • `asset` stdlib module: asset.texture(), asset.sound(),
                           asset.tilemap(), asset.font()
  • @texture / @sound / @tilemap / @font decorator support via
    visit_DecoratedDecl (special-cased in interpreter.py)

Usage from .ins source
──────────────────────
  import "asset" as asset

  let hero_tex  = asset.texture("sprites/hero.png")
  let jump_sfx  = asset.sound("sfx/jump.wav")
  let level_map = asset.tilemap("maps/level1.tmx")
  let ui_font   = asset.font("fonts/roboto.ttf", 16)

  # Or annotation form (sets the let var to the handle):
  @texture("sprites/hero.png")
  let hero_tex

Usage from Python (game backend)
─────────────────────────────────
  from stdlib_assets import get_registry, AssetHandle

  registry = get_registry()
  registry.load_all(base_dir="project/")
  registry.export_manifest("project/assets.toml")
  registry.bundle("project/", "dist/")

  # Hot-reload check (call every frame or on --watch save):
  changed = registry.check_for_changes()
  # changed → list of AssetHandle objects that were reloaded
"""

from __future__ import annotations
import os, time, hashlib, shutil
from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# AssetHandle
# ─────────────────────────────────────────────────────────────────────────────

ASSET_TYPES = frozenset({"texture", "sound", "tilemap", "font"})


class AssetHandle:
    """
    Lazy reference to a game asset.  The asset is not loaded from disk until
    `.load(base_dir)` is called (or `AssetRegistry.load_all(base_dir)`).
    """
    def __init__(self, asset_type: str, path: str, extra: dict | None = None):
        if asset_type not in ASSET_TYPES:
            raise ValueError(f"Unknown asset type '{asset_type}'. "
                             f"Must be one of: {sorted(ASSET_TYPES)}")
        self.asset_type = asset_type
        self.path       = path
        self.extra      = extra or {}   # type-specific params (e.g. font size)
        self.loaded     = False
        self.data       = None          # pygame Surface / Sound / _Tilemap / Font
        self._mtime:    Optional[float] = None  # last-known mtime for hot-reload
        self._base_dir: Optional[str]   = None

    # ── loading ───────────────────────────────────────────────────────────────

    def load(self, base_dir: str = ".") -> "AssetHandle":
        """
        Load the asset from disk.  Safe to call multiple times; subsequent calls
        are no-ops unless `force=True` or `reload()` is used.
        """
        self._base_dir = base_dir
        full_path = self._resolve(base_dir)
        if not os.path.isfile(full_path):
            print(f"[asset] Warning: file not found: {full_path}")
            return self
        self._mtime = os.path.getmtime(full_path)
        self._do_load(full_path)
        self.loaded = True
        return self

    def reload(self) -> bool:
        """
        Reload from disk if the file has changed since last load.
        Returns True if the asset was actually reloaded.
        """
        if self._base_dir is None:
            return False
        full_path = self._resolve(self._base_dir)
        if not os.path.isfile(full_path):
            return False
        current_mtime = os.path.getmtime(full_path)
        if self._mtime is not None and current_mtime <= self._mtime:
            return False
        self._mtime = current_mtime
        self._do_load(full_path)
        self.loaded = True
        return True

    def _do_load(self, full_path: str):
        """Type-specific load implementation."""
        t = self.asset_type
        try:
            if t == "texture":
                try:
                    import pygame
                    surf = pygame.image.load(full_path)
                    try:
                        surf = surf.convert_alpha()
                    except pygame.error:
                        pass  # no display initialized; use unconverted surface
                    self.data = surf
                except ImportError:
                    self.data = {"path": full_path, "type": "texture"}  # headless stub
            elif t == "sound":
                try:
                    import pygame.mixer as _mix
                    if not _mix.get_init():
                        _mix.init()
                    self.data = _mix.Sound(full_path)
                except ImportError:
                    self.data = {"path": full_path, "type": "sound"}   # headless stub
            elif t == "tilemap":
                from stdlib_game import _tilemap_load
                self.data = _tilemap_load(full_path)
            elif t == "font":
                size = int(self.extra.get("size", 16))
                try:
                    import pygame.freetype as _ft
                    if not _ft.get_init():
                        _ft.init()
                    self.data = _ft.Font(full_path, size)
                except ImportError:
                    self.data = {"path": full_path, "type": "font", "size": size}
        except Exception as e:
            print(f"[asset] Failed to load {self.asset_type} '{full_path}': {e}")
            self.data = None

    # ── helpers ───────────────────────────────────────────────────────────────

    def _resolve(self, base_dir: str) -> str:
        if os.path.isabs(self.path):
            return self.path
        return os.path.join(base_dir, self.path)

    def sha256(self, base_dir: str = ".") -> str:
        """Compute SHA-256 of the asset file (for bundling integrity checks)."""
        full_path = self._resolve(base_dir)
        if not os.path.isfile(full_path):
            return ""
        h = hashlib.sha256()
        with open(full_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def exists(self, base_dir: str = ".") -> bool:
        return os.path.isfile(self._resolve(base_dir))

    # ── InScript property access ───────────────────────────────────────────────

    def __getattr__(self, name: str) -> Any:
        # Allow .get_tile(), .width, .height etc to proxy to .data when loaded
        if name.startswith("_") or name in ("asset_type", "path", "extra",
                                            "loaded", "data"):
            raise AttributeError(name)
        if self.data is not None:
            return getattr(self.data, name)
        raise AttributeError(f"Asset '{self.path}' not loaded yet; call load() first")

    def __repr__(self):
        status = "loaded" if self.loaded else "pending"
        return f"<AssetHandle {self.asset_type}:{self.path} [{status}]>"


# ─────────────────────────────────────────────────────────────────────────────
# AssetRegistry
# ─────────────────────────────────────────────────────────────────────────────

class AssetRegistry:
    """
    Global registry that tracks every AssetHandle created during script
    execution.  Drives bulk load, hot-reload, manifest export, and bundling.
    """
    def __init__(self):
        self._handles: List[AssetHandle] = []

    def register(self, handle: AssetHandle) -> AssetHandle:
        """Register a handle.  Idempotent — same handle registered twice is a no-op."""
        if handle not in self._handles:
            self._handles.append(handle)
        return handle

    def all_handles(self) -> List[AssetHandle]:
        return list(self._handles)

    def clear(self):
        """Clear the registry (used between test runs)."""
        self._handles.clear()

    # ── bulk operations ───────────────────────────────────────────────────────

    def load_all(self, base_dir: str = ".") -> int:
        """
        Load every registered handle.  Returns the count of successfully
        loaded assets.  Called once at game start.
        """
        loaded = 0
        for h in self._handles:
            h.load(base_dir)
            if h.loaded:
                loaded += 1
        print(f"[asset] Loaded {loaded}/{len(self._handles)} asset(s).")
        return loaded

    def check_for_changes(self) -> List[AssetHandle]:
        """
        Hot-reload: check every asset file's mtime.  Reload changed files.
        Returns list of handles that were reloaded.
        Called by --watch loop after each .ins file save.
        """
        reloaded = []
        for h in self._handles:
            if h.reload():
                reloaded.append(h)
        if reloaded:
            print(f"[asset] Hot-reloaded {len(reloaded)} asset(s): "
                  f"{[h.path for h in reloaded]}")
        return reloaded

    # ── manifest export ───────────────────────────────────────────────────────

    def export_manifest(self, output_path: str, base_dir: str = ".") -> str:
        """
        Write an assets.toml manifest listing every registered asset.
        Returns the written path.

        Format:
          [meta]
          generated = "2026-05-25T..."
          count = 3

          [[asset]]
          type   = "texture"
          path   = "sprites/hero.png"
          sha256 = "abc123..."

          [[asset]]
          ...
        """
        import datetime
        lines = [
            "# InScript Asset Manifest — auto-generated by inscript build\n",
            f'# Generated: {datetime.datetime.utcnow().isoformat()}Z\n\n',
            "[meta]\n",
            f'count     = {len(self._handles)}\n',
            f'base_dir  = "{base_dir}"\n\n',
        ]
        for h in self._handles:
            sha = h.sha256(base_dir)
            exists = h.exists(base_dir)
            lines.append("[[asset]]\n")
            lines.append(f'type   = "{h.asset_type}"\n')
            lines.append(f'path   = "{h.path}"\n')
            lines.append(f'sha256 = "{sha}"\n')
            lines.append(f'exists = {str(exists).lower()}\n')
            if h.extra:
                for k, v in h.extra.items():
                    lines.append(f'{k}     = {v!r}\n')
            lines.append("\n")
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"[asset] Manifest written to '{output_path}' ({len(self._handles)} asset(s))")
        return output_path

    # ── bundling ──────────────────────────────────────────────────────────────

    def bundle(self, src_base: str, dest_base: str,
               skip_missing: bool = False) -> dict:
        """
        Copy all referenced asset files from src_base into dest_base,
        preserving relative paths.

        Returns a summary dict:
          {"copied": N, "missing": N, "skipped": N}
        """
        os.makedirs(dest_base, exist_ok=True)
        copied = 0; missing = 0; skipped = 0
        for h in self._handles:
            src  = os.path.join(src_base, h.path)
            dest = os.path.join(dest_base, h.path)
            if not os.path.isfile(src):
                if skip_missing:
                    skipped += 1
                    continue
                print(f"[asset] Bundle: missing source '{src}'")
                missing += 1
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(src, dest)
            copied += 1
        summary = {"copied": copied, "missing": missing, "skipped": skipped}
        print(f"[asset] Bundle: {copied} copied, {missing} missing, {skipped} skipped → '{dest_base}'")
        return summary

    def __len__(self):
        return len(self._handles)

    def __repr__(self):
        return f"<AssetRegistry {len(self._handles)} handle(s)>"


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────────────────────

_GLOBAL_REGISTRY = AssetRegistry()


def get_registry() -> AssetRegistry:
    return _GLOBAL_REGISTRY


def reset_registry():
    """Clear registry — used between tests / game reloads."""
    _GLOBAL_REGISTRY.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Factory functions (exposed in `asset` stdlib module)
# ─────────────────────────────────────────────────────────────────────────────

def make_texture(path: str) -> AssetHandle:
    h = AssetHandle("texture", str(path))
    return _GLOBAL_REGISTRY.register(h)


def make_sound(path: str) -> AssetHandle:
    h = AssetHandle("sound", str(path))
    return _GLOBAL_REGISTRY.register(h)


def make_tilemap(path: str) -> AssetHandle:
    h = AssetHandle("tilemap", str(path))
    return _GLOBAL_REGISTRY.register(h)


def make_font(path: str, size: int = 16) -> AssetHandle:
    h = AssetHandle("font", str(path), extra={"size": int(size)})
    return _GLOBAL_REGISTRY.register(h)


# ─────────────────────────────────────────────────────────────────────────────
# Register `asset` stdlib module
# ─────────────────────────────────────────────────────────────────────────────

try:
    from stdlib import register_module as _reg

    class _RegistryProxy:
        """Exposed as `asset.registry` from InScript."""
        def load_all(self, base_dir="."):         return _GLOBAL_REGISTRY.load_all(str(base_dir))
        def check_for_changes(self):              return _GLOBAL_REGISTRY.check_for_changes()
        def export_manifest(self, path, base="."): return _GLOBAL_REGISTRY.export_manifest(str(path), str(base))
        def bundle(self, src, dest):              return _GLOBAL_REGISTRY.bundle(str(src), str(dest))
        def count(self):                          return len(_GLOBAL_REGISTRY)
        def all(self):                            return _GLOBAL_REGISTRY.all_handles()
        def clear(self):                          return reset_registry()
        def __repr__(self):                       return repr(_GLOBAL_REGISTRY)

    _reg("asset", {
        "texture":  make_texture,
        "sound":    make_sound,
        "tilemap":  make_tilemap,
        "font":     make_font,
        "registry": _RegistryProxy(),
        # Convenience: AssetHandle type
        "Handle":   AssetHandle,
    })
except ImportError:
    pass  # running standalone without stdlib
