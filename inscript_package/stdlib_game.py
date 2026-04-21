# -*- coding: utf-8 -*-
# stdlib_game.py — Phase 4 remainder + Phase 5: Game-Specific Standard Library
#
# Modules in this file:
#   Phase 4 (remainder):
#     ssl          — HTTPS wrap, ssl context
#
#   Phase 5 (game-specific, 16 modules):
#     image        — load/save/resize/crop/pixel ops  (Pillow, graceful fallback)
#     atlas        — sprite atlas load/pack (TexturePacker JSON)
#     animation    — Clip + Animator state machine
#     physics2d    — RigidBody/StaticBody/World (pure-Python AABB + impulse, pymunk optional)
#     tilemap      — Tiled .tmx loader + layer draw
#     camera2d     — smooth follow camera with shake + zoom
#     particle     — Emitter with burst/start/stop/update/draw
#     pathfind     — A*, Dijkstra, flow-field on a Grid
#     ecs          — Entity Component System (World/spawn/add/query)
#     input        — remappable actions (wraps pygame; graceful fallback)
#     fsm          — Finite State Machine with on_enter/on_exit/guards
#     save         — JSON slot save/load with schema
#     localize     — i18n key lookup with variable interpolation
#     net_game     — UDP game networking stub (GameServer / GameClient)
#     shader       — GLSL shader stub (OpenGL required for real use)
#     audio        — full audio system (wraps pygame.mixer; graceful fallback)

from __future__ import annotations
import os as _os_pygame; _os_pygame.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
from stdlib import register_module

import functools as _functools

def _guard(module_name: str, fn):
    """Wrap fn so any Python exception becomes a clean [module] Error: message."""
    @_functools.wraps(fn)
    def _wrap(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:
            msg = str(e)
            if msg.startswith(f"[{module_name}]"):
                raise
            raise Exception(f"[{module_name}] {type(e).__name__}: {msg}") from None
    return _wrap

def _wrapmod(d: dict, name: str) -> dict:
    return {k: (_guard(name, v) if callable(v) else v) for k, v in d.items()}

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 4 REMAINDER — ssl
# ═══════════════════════════════════════════════════════════════════════════

def _ssl_wrap(sock, hostname="", certfile=None, keyfile=None, verify=True):
    import ssl as _ssl
    ctx = _ssl.create_default_context() if verify else _ssl.SSLContext(_ssl.PROTOCOL_TLS_CLIENT)
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE
    if certfile:
        ctx.load_cert_chain(certfile, keyfile)
    return ctx.wrap_socket(sock, server_hostname=hostname or None)

def _ssl_https_get(url, timeout=10, verify=True):
    import urllib.request, ssl as _ssl
    ctx = _ssl.create_default_context() if verify else _ssl.SSLContext(_ssl.PROTOCOL_TLS_CLIENT)
    if not verify:
        ctx.check_hostname = False; ctx.verify_mode = _ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "InScript/1.1"})
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as r:
        body = r.read().decode("utf-8", errors="replace")
        return {"status": r.status, "headers": dict(r.headers), "body": body}

def _ssl_create_context(verify=True, certfile=None, keyfile=None, cafile=None):
    import ssl as _ssl
    if verify:
        ctx = _ssl.create_default_context(cafile=cafile)
    else:
        ctx = _ssl.SSLContext(_ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False; ctx.verify_mode = _ssl.CERT_NONE
    if certfile:
        ctx.load_cert_chain(certfile, keyfile)
    return ctx

register_module("ssl", _wrapmod({
    "wrap":           _ssl_wrap,
    "https_get":      _ssl_https_get,
    "create_context": _ssl_create_context,
}, "ssl"))

# ═══════════════════════════════════════════════════════════════════════════
# 5.1 — image module
# ═══════════════════════════════════════════════════════════════════════════

class _Image:
    def __init__(self, pil_img):
        self._img = pil_img
    @property
    def width(self):  return self._img.width
    @property
    def height(self): return self._img.height
    @property
    def size(self):   return {"width": self._img.width, "height": self._img.height}
    def __repr__(self): return f"<Image {self._img.width}x{self._img.height} {self._img.mode}>"

def _img_load(path):
    try:
        from PIL import Image as PILImg
        return _Image(PILImg.open(str(path)).convert("RGBA"))
    except ImportError:
        raise RuntimeError("image.load requires Pillow — run: pip install Pillow")

def _img_new(width, height, color=None):
    try:
        from PIL import Image as PILImg
        c = (0, 0, 0, 0) if color is None else (
            int(color.get("r", 0)), int(color.get("g", 0)),
            int(color.get("b", 0)), int(color.get("a", 255)))
        return _Image(PILImg.new("RGBA", (int(width), int(height)), c))
    except ImportError:
        raise RuntimeError("image.new requires Pillow — run: pip install Pillow")

def _img_save(img, path):
    if not isinstance(img, _Image):
        raise TypeError("Expected an Image object")
    img._img.save(str(path))

def _img_resize(img, width, height, resample="lanczos"):
    from PIL import Image as PILImg
    methods = {"lanczos": PILImg.LANCZOS, "bilinear": PILImg.BILINEAR,
               "nearest": PILImg.NEAREST, "bicubic": PILImg.BICUBIC}
    return _Image(img._img.resize((int(width), int(height)),
                                   methods.get(resample, PILImg.LANCZOS)))

def _img_crop(img, x, y, w, h):
    return _Image(img._img.crop((int(x), int(y), int(x+w), int(y+h))))

def _img_flip_h(img):
    from PIL import ImageOps
    return _Image(ImageOps.mirror(img._img))

def _img_flip_v(img):
    from PIL import ImageOps
    return _Image(ImageOps.flip(img._img))

def _img_rotate(img, degrees, expand=False):
    return _Image(img._img.rotate(float(degrees), expand=expand))

def _img_grayscale(img):
    from PIL import ImageOps
    return _Image(ImageOps.grayscale(img._img).convert("RGBA"))

def _img_tint(img, color):
    from PIL import Image as PILImg, ImageEnhance
    r = int(color.get("r", 255)); g = int(color.get("g", 255))
    b = int(color.get("b", 255)); a = int(color.get("a", 255))
    overlay = PILImg.new("RGBA", img._img.size, (r, g, b, a))
    result = PILImg.blend(img._img, overlay, alpha=0.5)
    return _Image(result)

def _img_get_pixel(img, x, y):
    px = img._img.getpixel((int(x), int(y)))
    return {"r": px[0], "g": px[1], "b": px[2], "a": px[3] if len(px) > 3 else 255}

def _img_set_pixel(img, x, y, color):
    r, g, b = int(color.get("r", 0)), int(color.get("g", 0)), int(color.get("b", 0))
    a = int(color.get("a", 255))
    img._img.putpixel((int(x), int(y)), (r, g, b, a))

def _img_blit(dst, src, dx=0, dy=0):
    from PIL import Image as PILImg
    dst._img.paste(src._img, (int(dx), int(dy)), src._img)

def _img_premultiply_alpha(img):
    from PIL import Image as PILImg
    import numpy
    arr = numpy.array(img._img, dtype=float)
    alpha = arr[..., 3:] / 255.0
    arr[..., :3] = (arr[..., :3] * alpha).clip(0, 255)
    return _Image(PILImg.fromarray(arr.astype('uint8'), 'RGBA'))

def _img_to_bytes(img, fmt="PNG"):
    import io
    buf = io.BytesIO()
    img._img.save(buf, format=fmt)
    return buf.getvalue()

register_module("image", _wrapmod({
    "load":              _img_load,
    "new":               _img_new,
    "save":              _img_save,
    "resize":            _img_resize,
    "crop":              _img_crop,
    "flip_h":            _img_flip_h,
    "flip_v":            _img_flip_v,
    "rotate":            _img_rotate,
    "grayscale":         _img_grayscale,
    "tint":              _img_tint,
    "get_pixel":         _img_get_pixel,
    "set_pixel":         _img_set_pixel,
    "blit":              _img_blit,
    "premultiply_alpha": _img_premultiply_alpha,
    "to_bytes":          _img_to_bytes,
    "Image":             _Image,
}, "image"))

# ═══════════════════════════════════════════════════════════════════════════
# 5.2 — atlas module
# ═══════════════════════════════════════════════════════════════════════════

class _Atlas:
    def __init__(self, texture_path, frames):
        self.texture_path = texture_path
        self._frames = frames  # {name: {x,y,w,h,pivot_x,pivot_y}}

    def get(self, name):
        if name not in self._frames:
            raise KeyError(f"atlas.get: frame '{name}' not found")
        return dict(self._frames[name])

    def frames_matching(self, prefix):
        return sorted([k for k in self._frames if k.startswith(prefix)])

    def frame_names(self):
        return list(self._frames.keys())

    def has(self, name):
        return name in self._frames

    def __repr__(self): return f"<Atlas {len(self._frames)} frames>"

def _atlas_load(texture_path, json_path):
    import json, os
    with open(str(json_path), encoding="utf-8") as f:
        data = json.load(f)

    frames = {}
    # TexturePacker hash format: {"frames": {"name": {"frame":{x,y,w,h}, "pivot":{x,y}}}}
    if isinstance(data.get("frames"), dict):
        for name, info in data["frames"].items():
            fr = info.get("frame", info)
            piv = info.get("pivot", {"x": 0.5, "y": 0.5})
            frames[name] = {
                "x": fr["x"], "y": fr["y"], "w": fr["w"], "h": fr["h"],
                "pivot_x": piv.get("x", 0.5), "pivot_y": piv.get("y", 0.5)
            }
    # TexturePacker array format: {"frames": [{"filename": "...", "frame": {...}}]}
    elif isinstance(data.get("frames"), list):
        for item in data["frames"]:
            name = os.path.splitext(item.get("filename", ""))[0]
            fr = item.get("frame", {})
            piv = item.get("pivot", {"x": 0.5, "y": 0.5})
            frames[name] = {
                "x": fr.get("x", 0), "y": fr.get("y", 0),
                "w": fr.get("w", 0), "h": fr.get("h", 0),
                "pivot_x": piv.get("x", 0.5), "pivot_y": piv.get("y", 0.5)
            }
    return _Atlas(str(texture_path), frames)

def _atlas_pack(source_dir, out_texture, out_json, padding=1, max_size=2048):
    """Simple shelf packing algorithm — no external deps needed."""
    import json, os
    try:
        from PIL import Image as PILImg
    except ImportError:
        raise RuntimeError("atlas.pack requires Pillow — run: pip install Pillow")

    exts = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
    items = []
    for fname in sorted(os.listdir(str(source_dir))):
        if os.path.splitext(fname)[1].lower() in exts:
            path = os.path.join(str(source_dir), fname)
            img = PILImg.open(path).convert("RGBA")
            items.append((os.path.splitext(fname)[0], img))

    # Simple shelf packing
    items.sort(key=lambda x: -x[1].height)
    atlas = PILImg.new("RGBA", (int(max_size), int(max_size)), (0, 0, 0, 0))
    frames = {}
    x, y, row_h = 0, 0, 0

    for name, img in items:
        w, h = img.size
        if x + w + padding > max_size:
            x = 0; y += row_h + padding; row_h = 0
        if y + h + padding > max_size:
            raise RuntimeError("atlas.pack: images don't fit in max_size")
        atlas.paste(img, (x, y))
        frames[name] = {"frame": {"x": x, "y": y, "w": w, "h": h},
                        "pivot": {"x": 0.5, "y": 0.5}}
        row_h = max(row_h, h)
        x += w + padding

    atlas.save(str(out_texture))
    with open(str(out_json), "w", encoding="utf-8") as f:
        json.dump({"frames": frames, "meta": {"image": str(out_texture)}}, f, indent=2)
    return _Atlas(str(out_texture), {
        k: {"x": v["frame"]["x"], "y": v["frame"]["y"],
            "w": v["frame"]["w"], "h": v["frame"]["h"],
            "pivot_x": 0.5, "pivot_y": 0.5}
        for k, v in frames.items()
    })

register_module("atlas", _wrapmod({
    "load":  _atlas_load,
    "pack":  _atlas_pack,
    "Atlas": _Atlas,
}, "atlas"))

# ═══════════════════════════════════════════════════════════════════════════
# 5.3 — animation module
# ═══════════════════════════════════════════════════════════════════════════

class _Clip:
    def __init__(self, name, frame_names, fps=12, loop=True):
        self.name = name
        self.frame_names = list(frame_names)
        self.fps = float(fps)
        self.loop = bool(loop)
        self.duration = len(frame_names) / max(fps, 0.001)
    def __repr__(self):
        return f"<Clip '{self.name}' {len(self.frame_names)} frames @{self.fps}fps loop={self.loop}>"

class _Animator:
    def __init__(self):
        self._clips = {}
        self._current = None
        self._t = 0.0
        self._frame_idx = 0
        self._done = False

    def add_clip(self, clip):
        self._clips[clip.name] = clip

    def play(self, name):
        if name not in self._clips:
            raise KeyError(f"Animator: clip '{name}' not found")
        if self._current != name:
            self._current = name
            self._t = 0.0
            self._frame_idx = 0
            self._done = False

    def update(self, dt):
        if self._current is None: return
        clip = self._clips[self._current]
        self._t += float(dt)
        total = clip.duration
        if self._t >= total:
            if clip.loop:
                self._t %= total
            else:
                self._t = total
                self._done = True
        frame_count = len(clip.frame_names)
        self._frame_idx = min(
            int(self._t * clip.fps), frame_count - 1)

    def current_frame(self):
        if self._current is None: return None
        clip = self._clips[self._current]
        return clip.frame_names[self._frame_idx]

    def current(self): return self._current
    def finished(self): return self._done
    def frame_index(self): return self._frame_idx
    def progress(self):
        if self._current is None: return 0.0
        clip = self._clips[self._current]
        return min(self._t / clip.duration, 1.0) if clip.duration > 0 else 1.0

    def __repr__(self): return f"<Animator clip={self._current!r} frame={self._frame_idx} done={self._done}>"

register_module("animation", _wrapmod({
    "Clip":     lambda name, frame_names, fps=12, loop=True: _Clip(name, frame_names, fps, loop),
    "Animator": _Animator,
}, "animation"))

# ═══════════════════════════════════════════════════════════════════════════
# 5.4 — physics2d module  (pure-Python AABB + impulse; pymunk optional)
# ═══════════════════════════════════════════════════════════════════════════

class _Vec2:
    __slots__ = ("x", "y")
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x); self.y = float(y)
    def __add__(self, o): return _Vec2(self.x+o.x, self.y+o.y)
    def __sub__(self, o): return _Vec2(self.x-o.x, self.y-o.y)
    def __mul__(self, s): return _Vec2(self.x*s, self.y*s)
    def __repr__(self): return f"Vec2({self.x:.2f},{self.y:.2f})"
    def length(self):
        import math; return math.hypot(self.x, self.y)
    def normalized(self):
        l = self.length()
        if l == 0: return _Vec2(0,0)
        return _Vec2(self.x/l, self.y/l)

class _P2DShape:
    pass

class _P2DRect(_P2DShape):
    def __init__(self, w, h): self.w = float(w); self.h = float(h)

class _P2DCircle(_P2DShape):
    def __init__(self, r): self.r = float(r)

class _P2DBody:
    def __init__(self, shape, mass=1.0, tag=""):
        self.shape = shape
        self.mass = float(mass)
        self.tag = str(tag)
        self.position = _Vec2(0, 0)
        self.velocity = _Vec2(0, 0)
        self.is_static = False
        self.restitution = 0.3  # bounciness
        self.friction = 0.8
        self._alive = True

    @property
    def x(self): return self.position.x
    @x.setter
    def x(self, v): self.position.x = float(v)

    @property
    def y(self): return self.position.y
    @y.setter
    def y(self, v): self.position.y = float(v)

    def apply_impulse(self, ix, iy):
        if not self.is_static and self.mass > 0:
            self.velocity.x += ix / self.mass
            self.velocity.y += iy / self.mass

    def __repr__(self): return f"<Body tag={self.tag!r} pos={self.position}>"

class _P2DArea(_P2DBody):
    def __init__(self, shape, tag=""):
        super().__init__(shape, mass=0.0, tag=tag)
        self.is_static = True
        self.on_overlap_cb = None

    def on_overlap(self, fn):
        self.on_overlap_cb = fn

class _P2DWorld:
    def __init__(self, gravity_x=0.0, gravity_y=500.0):
        self._gx = float(gravity_x)
        self._gy = float(gravity_y)
        self._bodies = []
        self._on_collision_cb = None

    def add(self, body): self._bodies.append(body)
    def remove(self, body):
        if body in self._bodies: self._bodies.remove(body)

    def on_collision(self, fn): self._on_collision_cb = fn

    def step(self, dt):
        dt = float(dt)
        dynamics = [b for b in self._bodies if not b.is_static and b._alive]
        statics = [b for b in self._bodies if b.is_static and b._alive]

        # Gravity + integrate
        for b in dynamics:
            b.velocity.x += self._gx * dt
            b.velocity.y += self._gy * dt
            b.position.x += b.velocity.x * dt
            b.position.y += b.velocity.y * dt

        # AABB collision resolution
        def _aabb(body):
            if isinstance(body.shape, _P2DRect):
                hw, hh = body.shape.w/2, body.shape.h/2
                return (body.x - hw, body.y - hh, body.x + hw, body.y + hh)
            elif isinstance(body.shape, _P2DCircle):
                r = body.shape.r
                return (body.x - r, body.y - r, body.x + r, body.y + r)
            return (body.x, body.y, body.x, body.y)

        def _overlap(a, b):
            ax1,ay1,ax2,ay2 = _aabb(a); bx1,by1,bx2,by2 = _aabb(b)
            return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1

        for d in dynamics:
            for s in statics:
                if _overlap(d, s):
                    ax1,ay1,ax2,ay2 = _aabb(d); bx1,by1,bx2,by2 = _aabb(s)
                    # penetration depths
                    overlap_x = min(ax2-bx1, bx2-ax1)
                    overlap_y = min(ay2-by1, by2-ay1)
                    if isinstance(s, _P2DArea):
                        if s.on_overlap_cb: s.on_overlap_cb(s, d)
                    else:
                        if overlap_x < overlap_y:
                            push = overlap_x if d.x < (bx1+bx2)/2 else -overlap_x
                            d.position.x -= push
                            d.velocity.x *= -(d.restitution)
                        else:
                            push = overlap_y if d.y < (by1+by2)/2 else -overlap_y
                            d.position.y -= push
                            d.velocity.y *= -(d.restitution)
                        if self._on_collision_cb: self._on_collision_cb(d, s)

        # Dynamic vs dynamic
        for i in range(len(dynamics)):
            for j in range(i+1, len(dynamics)):
                a, b = dynamics[i], dynamics[j]
                if _overlap(a, b):
                    if self._on_collision_cb: self._on_collision_cb(a, b)
                    # Simple separation
                    dx = b.x - a.x; dy = b.y - a.y
                    import math
                    dist = max(math.hypot(dx, dy), 0.001)
                    nx, ny = dx/dist, dy/dist
                    rel_vx = b.velocity.x - a.velocity.x
                    rel_vy = b.velocity.y - a.velocity.y
                    vel_along = rel_vx*nx + rel_vy*ny
                    if vel_along < 0:
                        e = (a.restitution + b.restitution) * 0.5
                        j_val = -(1+e)*vel_along / (1/a.mass + 1/b.mass)
                        a.velocity.x -= j_val/a.mass * nx
                        a.velocity.y -= j_val/a.mass * ny
                        b.velocity.x += j_val/b.mass * nx
                        b.velocity.y += j_val/b.mass * ny

    def body_count(self): return len(self._bodies)
    def __repr__(self): return f"<Physics2D.World bodies={len(self._bodies)} gravity=({self._gx},{self._gy})>"

register_module("physics2d", _wrapmod({
    "World":      lambda gravity=None: _P2DWorld(
                      *(gravity.values() if hasattr(gravity, 'values') else (0.0, 500.0))
                      if gravity and hasattr(gravity, 'values') else
                      ((gravity.x, gravity.y) if gravity and hasattr(gravity, 'x') else (0.0, 500.0))),
    "RigidBody":  lambda shape, mass=1.0, tag="": _P2DBody(shape, mass, tag),
    "StaticBody": lambda shape, tag="": _make_static(shape, tag),
    "Area":       lambda shape, tag="": _P2DArea(shape, tag),
    "Rect":       lambda w, h: _P2DRect(w, h),
    "Circle":     lambda r: _P2DCircle(r),
    "Vec2":       lambda x=0.0, y=0.0: _Vec2(x, y),
}, "physics2d"))

def _make_static(shape, tag=""):
    b = _P2DBody(shape, mass=0.0, tag=tag)
    b.is_static = True
    return b

# ═══════════════════════════════════════════════════════════════════════════
# 5.5 — tilemap module  (Tiled .tmx XML format)
# ═══════════════════════════════════════════════════════════════════════════

class _Tilemap:
    def __init__(self, width, height, tile_w, tile_h, layers, tilesets, objects):
        self.width = width          # in tiles
        self.height = height
        self.tile_width = tile_w
        self.tile_height = tile_h
        self._layers = {l["name"]: l for l in layers}
        self._tilesets = tilesets
        self._objects = objects     # list of {name, type, x, y, w, h, props}

    def get_layer(self, name):
        if name not in self._layers:
            raise KeyError(f"tilemap: layer '{name}' not found. Available: {list(self._layers)}")
        return self._layers[name]

    def layer_names(self): return list(self._layers.keys())

    def get_tile(self, layer, col, row):
        data = layer.get("data", [])
        idx = row * self.width + col
        if idx < 0 or idx >= len(data): return None
        gid = data[idx]
        if gid == 0: return None
        return {"gid": gid, "col": col, "row": row}

    def get_objects(self, group=None):
        if group:
            return [o for o in self._objects if o.get("layer") == group]
        return list(self._objects)

    def draw_layer(self, layer, cam_x=0, cam_y=0, renderer=None):
        # When called from InScript game code, renderer is the pygame draw namespace
        # If not provided, this is a no-op (headless)
        pass

    def __repr__(self): return f"<Tilemap {self.width}x{self.height} tiles={self.tile_width}x{self.tile_height} layers={list(self._layers)}>"

def _tilemap_load(path):
    import xml.etree.ElementTree as ET, base64, zlib
    tree = ET.parse(str(path))
    root = tree.getroot()

    map_w = int(root.get("width", 0))
    map_h = int(root.get("height", 0))
    tile_w = int(root.get("tilewidth", 32))
    tile_h = int(root.get("tileheight", 32))

    tilesets = []
    for ts in root.findall("tileset"):
        tilesets.append({
            "firstgid": int(ts.get("firstgid", 1)),
            "name":     ts.get("name", ""),
            "source":   ts.get("source", ""),
        })

    layers = []
    for layer in root.findall(".//layer"):
        data_el = layer.find("data")
        tiles = []
        if data_el is not None:
            enc = data_el.get("encoding", "csv")
            comp = data_el.get("compression", "")
            raw = (data_el.text or "").strip()
            if enc == "base64":
                decoded = base64.b64decode(raw)
                if comp == "zlib":
                    decoded = zlib.decompress(decoded)
                elif comp == "gzip":
                    import gzip
                    decoded = gzip.decompress(decoded)
                import struct
                tiles = list(struct.unpack(f"<{len(decoded)//4}I", decoded))
            else:  # csv
                tiles = [int(x.strip()) for x in raw.split(",") if x.strip()]
        props = {}
        for prop in layer.findall(".//property"):
            props[prop.get("name", "")] = prop.get("value", "")
        layers.append({
            "name":   layer.get("name", ""),
            "width":  int(layer.get("width", map_w)),
            "height": int(layer.get("height", map_h)),
            "data":   tiles,
            "props":  props,
        })

    objects = []
    for og in root.findall(".//objectgroup"):
        layer_name = og.get("name", "")
        for obj in og.findall("object"):
            props = {}
            for prop in obj.findall(".//property"):
                props[prop.get("name", "")] = prop.get("value", "")
            objects.append({
                "id":    int(obj.get("id", 0)),
                "name":  obj.get("name", ""),
                "type":  obj.get("type", obj.get("class", "")),
                "x":     float(obj.get("x", 0)),
                "y":     float(obj.get("y", 0)),
                "w":     float(obj.get("width", 0)),
                "h":     float(obj.get("height", 0)),
                "layer": layer_name,
                "props": props,
            })

    return _Tilemap(map_w, map_h, tile_w, tile_h, layers, tilesets, objects)

def _tilemap_get_layer(tmap, name): return tmap.get_layer(name)
def _tilemap_get_tile(tmap, layer, col, row): return tmap.get_tile(layer, col, row)
def _tilemap_get_objects(tmap, group=None): return tmap.get_objects(group)
def _tilemap_draw_layer(layer, cam_x=0, cam_y=0): pass  # no-op without renderer

register_module("tilemap", _wrapmod({
    "load":        _tilemap_load,
    "get_layer":   _tilemap_get_layer,
    "get_tile":    _tilemap_get_tile,
    "get_objects": _tilemap_get_objects,
    "draw_layer":  _tilemap_draw_layer,
    "Tilemap":     _Tilemap,
}, "tilemap"))

# ═══════════════════════════════════════════════════════════════════════════
# 5.6 — camera2d module
# ═══════════════════════════════════════════════════════════════════════════

class _Camera2D:
    def __init__(self):
        self.target_x = 0.0
        self.target_y = 0.0
        self._x = 0.0
        self._y = 0.0
        self.zoom = 1.0
        self.follow_speed = 6.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        # Bounds: (min_x, min_y, max_x, max_y) or None
        self.bounds = None
        # Shake
        self._shake_t = 0.0
        self._shake_dur = 0.0
        self._shake_intensity = 0.0
        self._shake_x = 0.0
        self._shake_y = 0.0

    @property
    def x(self): return self._x + self._shake_x
    @property
    def y(self): return self._y + self._shake_y

    def set_target(self, x, y):
        self.target_x = float(x); self.target_y = float(y)

    def snap(self, x, y):
        self._x = float(x); self._y = float(y)

    def follow(self, x, y):
        self.target_x = float(x); self.target_y = float(y)

    def shake(self, intensity=8.0, duration=0.3):
        self._shake_intensity = float(intensity)
        self._shake_dur = float(duration)
        self._shake_t = float(duration)

    def update(self, dt):
        import math, random
        dt = float(dt)
        # Smooth follow
        alpha = min(1.0, self.follow_speed * dt)
        tx = self.target_x - self.offset_x
        ty = self.target_y - self.offset_y
        self._x += (tx - self._x) * alpha
        self._y += (ty - self._y) * alpha
        # Bounds clamp
        if self.bounds:
            bx, by, bw, bh = (self.bounds.get("x", 0), self.bounds.get("y", 0),
                               self.bounds.get("w", 99999), self.bounds.get("h", 99999))
            self._x = max(bx, min(self._x, bx + bw))
            self._y = max(by, min(self._y, by + bh))
        # Shake decay
        if self._shake_t > 0:
            self._shake_t -= dt
            frac = max(self._shake_t / max(self._shake_dur, 0.001), 0.0)
            amp = self._shake_intensity * frac
            self._shake_x = random.uniform(-amp, amp)
            self._shake_y = random.uniform(-amp, amp)
        else:
            self._shake_x = 0.0; self._shake_y = 0.0

    def world_to_screen(self, wx, wy):
        return {"x": (float(wx) - self._x) * self.zoom + self.offset_x,
                "y": (float(wy) - self._y) * self.zoom + self.offset_y}

    def screen_to_world(self, sx, sy):
        return {"x": (float(sx) - self.offset_x) / self.zoom + self._x,
                "y": (float(sy) - self.offset_y) / self.zoom + self._y}

    def begin(self): pass  # hooks for pygame integration
    def end(self):   pass

    def __repr__(self):
        return f"<Camera2D pos=({self._x:.1f},{self._y:.1f}) zoom={self.zoom}>"

register_module("camera2d", _wrapmod({
    "Camera2D":        _Camera2D,
    "update":          lambda c, dt: c.update(dt),
    "follow":          lambda c, x, y: c.follow(x, y),
    "set_target":      lambda c, x, y: c.set_target(x, y),
    "shake":           lambda c, intensity=5.0, duration=0.3: c.shake(intensity, duration),
    "snap":            lambda c: c.snap(),
    "begin":           lambda c: c.begin(),
    "end":             lambda c: c.end(),
    "world_to_screen": lambda c, x, y: c.world_to_screen(x, y),
    "screen_to_world": lambda c, x, y: c.screen_to_world(x, y),
    "bounds":          lambda c: c.bounds(),
    "zoom":            lambda c: c.zoom(),
    "set_zoom":        lambda c, v: c.set_zoom(v) if hasattr(c,'set_zoom') else setattr(c,'_zoom',float(v)),
}, "camera2d"))

# ═══════════════════════════════════════════════════════════════════════════
# 5.7 — particle module
# ═══════════════════════════════════════════════════════════════════════════

import random as _random
import math as _math

class _Particle:
    __slots__ = ("x","y","vx","vy","life","max_life",
                 "r0","g0","b0","a0","r1","g1","b1","a1",
                 "size","size_end","gx","gy")
    def __init__(self, x, y, vx, vy, life,
                 r0, g0, b0, a0, r1, g1, b1, a1,
                 size, size_end, gx, gy):
        self.x=x; self.y=y; self.vx=vx; self.vy=vy
        self.life=life; self.max_life=life
        self.r0=r0; self.g0=g0; self.b0=b0; self.a0=a0
        self.r1=r1; self.g1=g1; self.b1=b1; self.a1=a1
        self.size=size; self.size_end=size_end
        self.gx=gx; self.gy=gy

class _Emitter:
    def __init__(self, x=0, y=0):
        self.x = float(x); self.y = float(y)
        # Emission
        self.rate = 30.0          # particles per second
        self.lifetime = (0.5, 1.5)
        self.speed = (50.0, 150.0)
        self.angle = (0.0, 360.0)
        # Appearance
        self.color_start = {"r": 1.0, "g": 0.8, "b": 0.0, "a": 1.0}
        self.color_end   = {"r": 1.0, "g": 0.0, "b": 0.0, "a": 0.0}
        self.size_start = 6.0
        self.size_end   = 0.0
        self.gravity_x  = 0.0
        self.gravity_y  = 50.0
        # State
        self._particles = []
        self._running = False
        self._accumulator = 0.0

    def _spawn_one(self):
        angle = _random.uniform(*self.angle) * _math.pi / 180.0
        speed = _random.uniform(*self.speed)
        life  = _random.uniform(*self.lifetime)
        cs, ce = self.color_start, self.color_end
        return _Particle(
            self.x, self.y,
            _math.cos(angle)*speed, _math.sin(angle)*speed,
            life,
            cs.get("r",1)*255, cs.get("g",0)*255, cs.get("b",0)*255, cs.get("a",1)*255,
            ce.get("r",1)*255, ce.get("g",0)*255, ce.get("b",0)*255, ce.get("a",0)*255,
            self.size_start, self.size_end,
            self.gravity_x, self.gravity_y
        )

    def burst(self, count=20):
        for _ in range(int(count)): self._particles.append(self._spawn_one())

    def start(self): self._running = True
    def stop(self):  self._running = False

    def set_position(self, x, y): self.x = float(x); self.y = float(y)

    def update(self, dt):
        dt = float(dt)
        # Spawn new
        if self._running:
            self._accumulator += self.rate * dt
            while self._accumulator >= 1.0:
                self._particles.append(self._spawn_one())
                self._accumulator -= 1.0
        # Update existing
        alive = []
        for p in self._particles:
            p.life -= dt
            if p.life <= 0: continue
            p.vx += p.gx * dt; p.vy += p.gy * dt
            p.x  += p.vx * dt; p.y  += p.vy * dt
            alive.append(p)
        self._particles = alive

    def draw(self, renderer=None):
        # renderer is the pygame draw namespace when called from game code
        # Headless: no-op
        pass

    def particle_data(self):
        out = []
        for p in self._particles:
            t = 1.0 - p.life / max(p.max_life, 0.0001)
            lerp = lambda a, b: a + (b-a)*t
            out.append({
                "x": p.x, "y": p.y,
                "r": lerp(p.r0, p.r1), "g": lerp(p.g0, p.g1),
                "b": lerp(p.b0, p.b1), "a": lerp(p.a0, p.a1),
                "size": lerp(p.size, p.size_end),
            })
        return out

    @property
    def count(self): return len(self._particles)

    def __repr__(self): return f"<Emitter particles={len(self._particles)} running={self._running}>"

register_module("particle", _wrapmod({
    "Emitter":      lambda x=0, y=0: _Emitter(x, y),
    "start":        lambda e: e.start(),
    "stop":         lambda e: e.stop(),
    "update":       lambda e, dt: e.update(dt),
    "burst":        lambda e, n=None: e.burst(n),
    "set_position": lambda e, x, y: e.set_position(x, y),
    "rate":         lambda e, v: e.rate(v),
    "lifetime":     lambda e, v: e.lifetime(v),
    "speed":        lambda e, v: e.speed(v),
    "angle":        lambda e, v: e.angle(v),
    "count":        lambda e: e.count(),
    "color_start":  lambda e, r, g, b, a=1.0: e.color_start(r, g, b, a),
    "color_end":    lambda e, r, g, b, a=0.0: e.color_end(r, g, b, a),
    "size_start":   lambda e, v: e.size_start(v),
    "size_end":     lambda e, v: e.size_end(v),
    "gravity":      lambda e, x, y: (e.gravity_x(x), e.gravity_y(y)),
}, "particle"))

# ═══════════════════════════════════════════════════════════════════════════
# 5.8 — pathfind module
# ═══════════════════════════════════════════════════════════════════════════

class _PFGrid:
    def __init__(self, cols, rows, cell_size=16):
        self.cols = int(cols)
        self.rows = int(rows)
        self.cell_size = float(cell_size)
        self._walkable = [[True]*self.cols for _ in range(self.rows)]

    def set_walkable(self, col, row, walkable=True):
        if 0 <= col < self.cols and 0 <= row < self.rows:
            self._walkable[int(row)][int(col)] = bool(walkable)

    def set_walkable_rect(self, x, y, w, h, walkable=True):
        for r in range(int(y), int(y+h)):
            for c in range(int(x), int(x+w)):
                self.set_walkable(c, r, walkable)

    def is_walkable(self, col, row):
        if col < 0 or col >= self.cols or row < 0 or row >= self.rows:
            return False
        return self._walkable[int(row)][int(col)]

    def world_to_cell(self, wx, wy):
        return (int(wx / self.cell_size), int(wy / self.cell_size))

    def cell_to_world(self, col, row):
        cs = self.cell_size
        return {"x": col*cs + cs/2, "y": row*cs + cs/2}

    def __repr__(self): return f"<PFGrid {self.cols}x{self.rows} cell={self.cell_size}>"

def _pf_astar(grid, start, end):
    import heapq
    def _node(v): 
        if isinstance(v, dict): return (int(v.get("x",0)), int(v.get("y",0)))
        return (int(getattr(v,"x",0)), int(getattr(v,"y",0)))
    sc = grid.world_to_cell(*_node(start)); ec = grid.world_to_cell(*_node(end))
    sx, sy = sc; ex, ey = ec
    if not grid.is_walkable(sx, sy) or not grid.is_walkable(ex, ey): return []
    def h(a, b): return abs(a[0]-b[0]) + abs(a[1]-b[1])
    open_set = [(0, (sx, sy))]
    came_from = {}
    g = {(sx,sy): 0}
    while open_set:
        _, cur = heapq.heappop(open_set)
        if cur == (ex, ey):
            path = []
            while cur in came_from:
                w = grid.cell_to_world(cur[0], cur[1])
                path.append({"x": w["x"], "y": w["y"]})
                cur = came_from[cur]
            return list(reversed(path))
        cx, cy = cur
        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
            nc = (cx+dx, cy+dy)
            if not grid.is_walkable(nc[0], nc[1]): continue
            ng = g[cur] + (1.414 if dx and dy else 1.0)
            if ng < g.get(nc, 1e18):
                g[nc] = ng
                came_from[nc] = cur
                heapq.heappush(open_set, (ng + h(nc, (ex,ey)), nc))
    return []

def _pf_dijkstra(grid, source):
    import heapq
    def _node(v):
        if isinstance(v, dict): return (int(v.get("x",0)), int(v.get("y",0)))
        return (int(getattr(v,"x",0)), int(getattr(v,"y",0)))
    sc = grid.world_to_cell(*_node(source))
    dist = {sc: 0.0}
    pq = [(0.0, sc)]
    while pq:
        d, cur = heapq.heappop(pq)
        if d > dist.get(cur, 1e18): continue
        cx, cy = cur
        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
            nc = (cx+dx, cy+dy)
            if not grid.is_walkable(nc[0], nc[1]): continue
            nd = d + (1.414 if dx and dy else 1.0)
            if nd < dist.get(nc, 1e18):
                dist[nc] = nd; heapq.heappush(pq, (nd, nc))
    # Return as {(col,row): dist} — convert to list of dicts for InScript
    return {f"{k[0]},{k[1]}": v for k, v in dist.items()}

def _pf_flow_field(grid, target):
    """Build a flow-field (direction map) pointing toward target cell."""
    import heapq
    def _node(v):
        if isinstance(v, dict): return (int(v.get("x",0)), int(v.get("y",0)))
        return (int(getattr(v,"x",0)), int(getattr(v,"y",0)))
    tc = grid.world_to_cell(*_node(target))
    dist = {tc: 0.0}
    pq = [(0.0, tc)]
    while pq:
        d, cur = heapq.heappop(pq)
        if d > dist.get(cur, 1e18): continue
        cx, cy = cur
        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
            nc = (cx+dx, cy+dy)
            if not grid.is_walkable(nc[0], nc[1]): continue
            nd = d + (1.414 if dx and dy else 1.0)
            if nd < dist.get(nc, 1e18):
                dist[nc] = nd; heapq.heappush(pq, (nd, nc))
    # Build direction vectors
    flow = {}
    for (col, row) in dist:
        best, best_d = None, 1e18
        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
            nc = (col+dx, row+dy)
            d = dist.get(nc, 1e18)
            if d < best_d: best_d = d; best = (dx, dy)
        if best:
            length = _math.hypot(*best)
            flow[f"{col},{row}"] = {"x": best[0]/length, "y": best[1]/length}
    return flow

def _pf_sample_flow(flow, pos):
    if isinstance(pos, dict):
        x, y = pos.get("x", 0), pos.get("y", 0)
    else:
        x, y = getattr(pos, "x", 0), getattr(pos, "y", 0)
    # flow keys are "col,row" — can't look up without grid here, return raw
    return flow  # caller should use the flow dict directly

register_module("pathfind", _wrapmod({
    "Grid":        lambda cols, rows, cell_size=16: _PFGrid(cols, rows, cell_size),
    "astar":       _pf_astar,
    "dijkstra":    _pf_dijkstra,
    "flow_field":  _pf_flow_field,
    "sample_flow": _pf_sample_flow,
}, "pathfind"))

# ═══════════════════════════════════════════════════════════════════════════
# 5.9 — ecs module (Entity Component System)
# ═══════════════════════════════════════════════════════════════════════════

class _ECSWorld:
    def __init__(self):
        self._next_id = 1
        self._components = {}   # type_name -> {entity_id -> component}
        self._entities = set()
        self._dead = set()

    def spawn(self):
        eid = self._next_id; self._next_id += 1
        self._entities.add(eid)
        return eid

    def add(self, entity, component):
        type_name = type(component).__name__
        # Also handle dicts and InScriptInstance
        if hasattr(component, 'struct_name'):
            type_name = component.struct_name
        elif isinstance(component, dict):
            type_name = component.get("_type", "dict")
        if type_name not in self._components:
            self._components[type_name] = {}
        self._components[type_name][entity] = component
        return component

    def get(self, entity, component_type):
        tn = component_type if isinstance(component_type, str) else component_type.__name__
        return self._components.get(tn, {}).get(entity)

    def remove_component(self, entity, component_type):
        tn = component_type if isinstance(component_type, str) else component_type.__name__
        if tn in self._components:
            self._components[tn].pop(entity, None)

    def query(self, *component_types):
        """Yields [entity, comp1, comp2, ...] for entities with ALL given components."""
        if not component_types: return
        names = [ct if isinstance(ct, str) else ct.__name__ for ct in component_types]
        maps = [self._components.get(n, {}) for n in names]
        if not maps: return
        for eid in set(maps[0].keys()):
            if eid in self._dead: continue
            row = [eid]
            ok = True
            for m in maps:
                c = m.get(eid)
                if c is None: ok = False; break
                row.append(c)
            if ok: yield row

    def query_sorted(self, *component_types, by=""):
        rows = list(self.query(*component_types))
        if by:
            rows.sort(key=lambda r: getattr(r[-1], by, 0) if hasattr(r[-1], by)
                      else r[-1].get(by, 0) if isinstance(r[-1], dict) else 0)
        return iter(rows)

    def mark_dead(self, entity): self._dead.add(entity)
    def is_dead(self, entity): return entity in self._dead

    def remove_dead(self):
        for eid in self._dead:
            self._entities.discard(eid)
            for m in self._components.values():
                m.pop(eid, None)
        self._dead.clear()

    def entity_count(self): return len(self._entities)
    def alive_count(self): return len(self._entities - self._dead)

    def __repr__(self): return f"<ECS.World entities={len(self._entities)} components={list(self._components)}>"

register_module("ecs", _wrapmod({
    "World":             _ECSWorld,
    "spawn":             lambda world, comps=None: world.spawn(comps or {}),
    "get":               lambda world, eid, comp: world.get(eid, comp),
    "query":             lambda world, *comps: world.query(*comps),
    "query_sorted":      lambda world, comp, *comps: world.query_sorted(comp, *comps),
    "mark_dead":         lambda world, eid: world.mark_dead(eid),
    "remove_dead":       lambda world: world.remove_dead(),
    "remove_component":  lambda world, eid, comp: world.remove_component(eid, comp),
    "is_dead":           lambda world, eid: world.is_dead(eid),
    "entity_count":      lambda world: world.entity_count(),
    "alive_count":       lambda world: world.alive_count(),
}, "ecs"))

# ═══════════════════════════════════════════════════════════════════════════
# 5.10 — input module (rebindable action map)
# ═══════════════════════════════════════════════════════════════════════════

class _InputManager:
    def __init__(self):
        self._actions = {}   # action -> {keys, axes}
        self._key_state = {}  # key -> (pressed_this_frame, held, released_this_frame)
        self._mouse_x = 0.0; self._mouse_y = 0.0
        self._mouse_buttons = {}

    def map(self, action, keys=None, axes=None, gamepad=None, gamepad_axis=None):
        self._actions[action] = {
            "keys": list(keys or []),
            "axes": list(axes or []),
        }

    def _is_key_down(self, key):
        try:
            import pygame
            kmap = {
                "space": pygame.K_SPACE, "up": pygame.K_UP, "down": pygame.K_DOWN,
                "left": pygame.K_LEFT, "right": pygame.K_RIGHT,
                "enter": pygame.K_RETURN, "escape": pygame.K_ESCAPE,
                "left_ctrl": pygame.K_LCTRL, "right_ctrl": pygame.K_RCTRL,
                "left_shift": pygame.K_LSHIFT, "right_shift": pygame.K_RSHIFT,
            }
            k = kmap.get(key.lower(), getattr(pygame, f"K_{key.lower()}", None))
            if k is None and len(key) == 1:
                k = ord(key.lower())
            if k is None: return False
            keys_pressed = pygame.key.get_pressed()
            return bool(keys_pressed[k])
        except Exception:
            return False

    def pressed(self, action):
        """True only the first frame the action key is held."""
        return self._key_state.get(action, {}).get("pressed", False)

    def held(self, action):
        binding = self._actions.get(action, {})
        return any(self._is_key_down(k) for k in binding.get("keys", []))

    def released(self, action):
        return self._key_state.get(action, {}).get("released", False)

    def axis(self, action):
        binding = self._actions.get(action, {})
        value = 0.0
        for ax_spec in binding.get("axes", []):
            if ":" in ax_spec:
                key, sign = ax_spec.split(":")
                if self._is_key_down(key):
                    value += float(sign)
        return max(-1.0, min(1.0, value))

    def mouse_pos(self):
        try:
            import pygame; x, y = pygame.mouse.get_pos(); return {"x": float(x), "y": float(y)}
        except Exception:
            return {"x": self._mouse_x, "y": self._mouse_y}

    def mouse_pressed(self, button=0):
        try:
            import pygame; return bool(pygame.mouse.get_pressed()[int(button)])
        except Exception:
            return False

    def save_bindings(self, path):
        import json
        with open(str(path), "w", encoding="utf-8") as f:
            json.dump(self._actions, f, indent=2)

    def load_bindings(self, path):
        import json
        with open(str(path), encoding="utf-8") as f:
            self._actions = json.load(f)

    def __repr__(self): return f"<InputManager actions={list(self._actions)}>"

_INPUT_SINGLETON = _InputManager()

register_module("input", _wrapmod({
    "map":           _INPUT_SINGLETON.map,
    "pressed":       _INPUT_SINGLETON.pressed,
    "held":          _INPUT_SINGLETON.held,
    "released":      _INPUT_SINGLETON.released,
    "axis":          _INPUT_SINGLETON.axis,
    "mouse_pos":     _INPUT_SINGLETON.mouse_pos,
    "mouse_pressed": _INPUT_SINGLETON.mouse_pressed,
    "save_bindings": _INPUT_SINGLETON.save_bindings,
    "load_bindings": _INPUT_SINGLETON.load_bindings,
    "Manager":       _InputManager,
}, "input"))

# ═══════════════════════════════════════════════════════════════════════════
# 5.11 — fsm module (Finite State Machine)
# ═══════════════════════════════════════════════════════════════════════════

class _FSMachine:
    def __init__(self, initial="idle"):
        self._states = {}         # name -> {on_enter, on_exit, on_update}
        self._transitions = []    # (from, to, guard)
        self._current = None
        self._initial = str(initial)
        self._history = []

    def add_state(self, name, on_enter=None, on_exit=None, on_update=None):
        self._states[name] = {
            "on_enter":  on_enter,
            "on_exit":   on_exit,
            "on_update": on_update,
        }
        if self._current is None and name == self._initial:
            self._transition_to(name)

    def add_transition(self, from_state, to_state, guard=None):
        self._transitions.append((str(from_state), str(to_state), guard))

    def _transition_to(self, new_state):
        if new_state not in self._states:
            raise KeyError(f"FSM: state '{new_state}' not defined")
        # on_exit current
        if self._current and self._states.get(self._current, {}).get("on_exit"):
            try: self._states[self._current]["on_exit"]()
            except Exception: pass
        self._history.append(self._current)
        self._current = new_state
        # on_enter new
        if self._states.get(new_state, {}).get("on_enter"):
            try: self._states[new_state]["on_enter"]()
            except Exception: pass

    def update(self, dt=None):
        if self._current is None: return
        # Check transitions
        for (frm, to, guard) in self._transitions:
            if frm != "*" and frm != self._current: continue
            if to == self._current: continue
            should = True
            if guard:
                try: should = bool(guard())
                except Exception: should = False
            if should:
                self._transition_to(to)
                break
        # on_update
        if self._states.get(self._current, {}).get("on_update"):
            try:
                fn = self._states[self._current]["on_update"]
                fn(dt) if dt is not None else fn()
            except Exception: pass

    def current(self): return self._current
    def in_state(self, name): return self._current == name
    def previous(self): return self._history[-1] if self._history else None
    def history(self): return list(self._history)

    def trigger(self, to_state):
        """Force immediate transition regardless of guards."""
        self._transition_to(to_state)

    def __repr__(self): return f"<FSM state={self._current!r} states={list(self._states)}>"

register_module("fsm", _wrapmod({
    "Machine":        lambda initial="idle": _FSMachine(initial),
    "add_state":      lambda m, name, on_enter=None, on_exit=None, on_update=None: m.add_state(name, on_enter=on_enter, on_exit=on_exit, on_update=on_update),
    "add_transition": lambda m, frm, to, condition=None: m.add_transition(frm, to, condition),
    "trigger":        lambda m, event: m.trigger(event),
    "update":         lambda m, dt: m.update(dt),
    "current":        lambda m: m.current(),
    "previous":       lambda m: m.previous(),
    "in_state":       lambda m, name: m.in_state(name),
    "history":        lambda m: m.history(),
}, "fsm"))

# ═══════════════════════════════════════════════════════════════════════════
# 5.12 — save module
# ═══════════════════════════════════════════════════════════════════════════

class _SaveSlot:
    def __init__(self, path):
        self._path = str(path)
        self._data = {}

    def set(self, key, value):
        self._data[str(key)] = self._serialize(value)

    def get(self, key, default=None):
        raw = self._data.get(str(key))
        if raw is None: return default
        return self._deserialize(raw)

    def _serialize(self, v):
        if isinstance(v, (int, float, str, bool, type(None))): return v
        if isinstance(v, list): return [self._serialize(x) for x in v]
        if isinstance(v, dict): return {k: self._serialize(val) for k, val in v.items()}
        # InScriptInstance or object with fields
        if hasattr(v, 'fields'): return {k: self._serialize(val) for k, val in v.fields.items()}
        if hasattr(v, '__dict__'): return {k: self._serialize(val) for k, val in vars(v).items()
                                           if not k.startswith('_')}
        return str(v)

    def _deserialize(self, v): return v  # JSON round-trip preserves types

    def write(self):
        import json, os
        os.makedirs(os.path.dirname(os.path.abspath(self._path)), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump({"_version": 1, "data": self._data}, f, indent=2)

    def read(self):
        import json
        try:
            with open(self._path, encoding="utf-8") as f:
                raw = json.load(f)
            self._data = raw.get("data", raw)
        except FileNotFoundError:
            self._data = {}
        return self

    def has(self, key): return str(key) in self._data
    def delete(self, key): self._data.pop(str(key), None)
    def keys(self): return list(self._data.keys())
    def clear(self): self._data.clear()

    def __repr__(self): return f"<SaveSlot '{self._path}' keys={len(self._data)}>"

def _save_list_slots(directory=".", pattern="*.dat"):
    import glob, os
    return glob.glob(os.path.join(str(directory), pattern))

def _save_delete_slot(path):
    import os
    try: os.remove(str(path))
    except FileNotFoundError: pass

def _save_copy_slot(src, dst):
    import shutil; shutil.copy2(str(src), str(dst))

register_module("save", _wrapmod({
    "Slot":        lambda path: _SaveSlot(path),
    "list_slots":  _save_list_slots,
    "delete_slot": _save_delete_slot,
    "copy_slot":   _save_copy_slot,
}, "save"))

# ═══════════════════════════════════════════════════════════════════════════
# 5.13 — localize module (i18n)
# ═══════════════════════════════════════════════════════════════════════════

class _Localizer:
    def __init__(self):
        self._langs = {}      # lang_code -> {key: value}
        self._current = "en"
        self._fallback = "en"

    def load(self, path, lang_code=None):
        import json, os
        if lang_code is None:
            # infer from filename: locales/en.json -> "en"
            lang_code = os.path.splitext(os.path.basename(str(path)))[0]
        with open(str(path), encoding="utf-8") as f:
            data = json.load(f)
        # flatten nested keys: {"ui": {"play": "Play"}} -> {"ui.play": "Play"}
        def _flatten(d, prefix=""):
            out = {}
            for k, v in d.items():
                full = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict): out.update(_flatten(v, full))
                else: out[full] = str(v)
            return out
        self._langs[lang_code] = _flatten(data)

    def set_language(self, lang): self._current = str(lang)
    def set_fallback(self, lang): self._fallback = str(lang)
    def current_language(self): return self._current
    def available_languages(self): return list(self._langs.keys())

    def get(self, key, **kwargs):
        val = (self._langs.get(self._current, {}).get(key) or
               self._langs.get(self._fallback, {}).get(key) or
               key)
        if kwargs:
            for k, v in kwargs.items():
                val = val.replace(f"{{{k}}}", str(v))
        return val

    def has(self, key):
        return (key in self._langs.get(self._current, {}) or
                key in self._langs.get(self._fallback, {}))

    def load_dict(self, lang_code, mapping):
        self._langs[lang_code] = dict(mapping)

    def __repr__(self): return f"<Localizer lang={self._current!r} langs={list(self._langs)}>"

_LOCALIZER = _Localizer()

register_module("localize", _wrapmod({
    "load":                _LOCALIZER.load,
    "load_dict":           _LOCALIZER.load_dict,
    "set_language":        _LOCALIZER.set_language,
    "set_fallback":        _LOCALIZER.set_fallback,
    "current_language":    _LOCALIZER.current_language,
    "available_languages": _LOCALIZER.available_languages,
    "get":                 _LOCALIZER.get,
    "has":                 _LOCALIZER.has,
    "Localizer":           _Localizer,
}, "localize"))

# ═══════════════════════════════════════════════════════════════════════════
# 5.14 — net_game module (UDP game networking)
# ═══════════════════════════════════════════════════════════════════════════

import struct as _struct

def _ng_pack(data):
    """Pack a dict/list/scalar to bytes for sending."""
    import json
    return json.dumps(data, separators=(",", ":")).encode("utf-8")

def _ng_unpack(raw):
    """Unpack bytes back to Python value."""
    import json
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    return json.loads(raw)

class _GamePeer:
    def __init__(self, addr, sock):
        self._addr = addr
        self._sock = sock
        self.id = f"{addr[0]}:{addr[1]}"
        self.latency_ms = 0.0

    def send(self, data):
        try: self._sock.sendto(_ng_pack(data), self._addr)
        except Exception: pass

    def __repr__(self): return f"<Peer {self.id}>"

class _GameServer:
    def __init__(self, port=7777, max_players=4, tick_rate=20):
        import socket, threading
        self._port = int(port)
        self._max = int(max_players)
        self._tick_rate = float(tick_rate)
        self._peers = {}
        self._on_connect_cb = None
        self._on_disconnect_cb = None
        self._on_message_cb = None
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(("", self._port))
        self._sock.setblocking(False)
        self._running = False
        self._thread = None

    def on_connect(self, fn): self._on_connect_cb = fn
    def on_disconnect(self, fn): self._on_disconnect_cb = fn
    def on_message(self, fn): self._on_message_cb = fn

    def start(self):
        import threading
        self._running = True
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        try: self._sock.close()
        except Exception: pass

    def _recv_loop(self):
        import socket
        while self._running:
            try:
                data, addr = self._sock.recvfrom(65535)
            except Exception:
                import time; time.sleep(0.001); continue
            peer = self._peers.get(addr)
            if peer is None:
                if len(self._peers) < self._max:
                    peer = _GamePeer(addr, self._sock)
                    self._peers[addr] = peer
                    if self._on_connect_cb:
                        try: self._on_connect_cb(peer)
                        except Exception: pass
                else:
                    continue
            msg = _ng_unpack(data)
            if isinstance(msg, dict) and msg.get("_type") == "_disconnect":
                self._peers.pop(addr, None)
                if self._on_disconnect_cb:
                    try: self._on_disconnect_cb(peer)
                    except Exception: pass
            elif self._on_message_cb:
                try: self._on_message_cb(peer, msg)
                except Exception: pass

    def broadcast(self, data):
        raw = _ng_pack(data)
        for peer in list(self._peers.values()):
            try: self._sock.sendto(raw, peer._addr)
            except Exception: pass

    def player_count(self): return len(self._peers)
    def __repr__(self): return f"<GameServer port={self._port} players={len(self._peers)}>"

class _GameClient:
    def __init__(self):
        import socket
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setblocking(False)
        self._addr = None
        self._on_message_cb = None
        self._running = False
        self._thread = None
        self.connected = False

    def connect(self, host, port):
        import threading
        self._addr = (str(host), int(port))
        self._running = True
        self.connected = True
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()

    def disconnect(self):
        if self._addr:
            try: self._sock.sendto(_ng_pack({"_type": "_disconnect"}), self._addr)
            except Exception: pass
        self._running = False; self.connected = False

    def on_message(self, fn): self._on_message_cb = fn

    def send(self, data):
        if self._addr:
            try: self._sock.sendto(_ng_pack(data), self._addr)
            except Exception: pass

    def _recv_loop(self):
        while self._running:
            try:
                data, _ = self._sock.recvfrom(65535)
                if self._on_message_cb:
                    try: self._on_message_cb(_ng_unpack(data))
                    except Exception: pass
            except Exception:
                import time; time.sleep(0.001)

    def __repr__(self): return f"<GameClient connected={self.connected} addr={self._addr}>"

register_module("net_game", _wrapmod({
    "GameServer": lambda port=7777, max_players=4, tick_rate=20: _GameServer(port, max_players, tick_rate),
    "GameClient": _GameClient,
    "pack":       _ng_pack,
    "unpack":     _ng_unpack,
}, "net_game"))

# ═══════════════════════════════════════════════════════════════════════════
# 5.15 — shader module  (stub — requires OpenGL/Phase 8)
# ═══════════════════════════════════════════════════════════════════════════

class _ShaderStub:
    def __init__(self, name="<shader>"):
        self.name = name
        self._uniforms = {}

    def set_uniform(self, name, value): self._uniforms[str(name)] = value
    def get_uniform(self, name): return self._uniforms.get(str(name))
    def begin(self): pass   # no-op without OpenGL
    def end(self):   pass

    def __repr__(self): return f"<Shader '{self.name}' uniforms={list(self._uniforms)}>"

def _shader_load(path):
    return _ShaderStub(str(path))

def _shader_load_vert_frag(vert_path, frag_path):
    return _ShaderStub(f"{vert_path}+{frag_path}")

def _shader_screen_effect(path):
    return _ShaderStub(f"screen:{path}")

def _shader_screen_pass(shader): pass  # no-op

register_module("shader", _wrapmod({
    "load":            _shader_load,
    "load_vert_frag":  _shader_load_vert_frag,
    "screen_effect":   _shader_screen_effect,
    "screen_pass":     _shader_screen_pass,
    "STUB_NOTE": "shader module requires OpenGL backend (Phase 8). Current implementation is a stub.",
    "Shader":          _ShaderStub,
}, "shader"))

# ═══════════════════════════════════════════════════════════════════════════
# 5.16 — audio module (full audio via pygame.mixer; graceful fallback)
# ═══════════════════════════════════════════════════════════════════════════

class _AudioSound:
    def __init__(self, path, pygame_sound=None):
        self.path = str(path)
        self._snd = pygame_sound
        self._volume = 1.0
        self._channel = None

    def __repr__(self): return f"<Sound '{self.path}'>"

_AUDIO_ENABLED = False
try:
    import pygame as _pg
    if not _pg.get_init(): _pg.mixer.pre_init(44100, -16, 2, 512)
    _AUDIO_ENABLED = True
except Exception:
    pass

_audio_buses = {"master": 1.0, "sfx": 1.0, "music": 1.0}

def _audio_load(path):
    try:
        import pygame
        snd = pygame.mixer.Sound(str(path))
        return _AudioSound(path, snd)
    except Exception:
        return _AudioSound(path)

def _audio_play(sound, volume=1.0, pitch=1.0, bus="sfx"):
    if isinstance(sound, _AudioSound) and sound._snd:
        try:
            import pygame
            vol = float(volume) * _audio_buses.get(bus, 1.0) * _audio_buses.get("master", 1.0)
            sound._snd.set_volume(max(0.0, min(1.0, vol)))
            sound._channel = sound._snd.play()
        except Exception: pass

def _audio_stop(sound):
    if isinstance(sound, _AudioSound) and sound._snd:
        try: sound._snd.stop()
        except Exception: pass

def _audio_play_music(path, loop=True, volume=0.8, fade_in=0.0):
    try:
        import pygame
        pygame.mixer.music.load(str(path))
        vol = float(volume) * _audio_buses.get("music", 1.0) * _audio_buses.get("master", 1.0)
        pygame.mixer.music.set_volume(max(0.0, min(1.0, vol)))
        loops = -1 if loop else 0
        fade_ms = int(fade_in * 1000)
        pygame.mixer.music.play(loops, fade_ms=fade_ms)
    except Exception: pass

def _audio_pause_music():
    try:
        import pygame; pygame.mixer.music.pause()
    except Exception: pass

def _audio_resume_music():
    try:
        import pygame; pygame.mixer.music.unpause()
    except Exception: pass

def _audio_stop_music():
    try:
        import pygame; pygame.mixer.music.stop()
    except Exception: pass

def _audio_fade_out(duration=1.0):
    try:
        import pygame; pygame.mixer.music.fadeout(int(float(duration)*1000))
    except Exception: pass

def _audio_set_volume(bus, value):
    _audio_buses[str(bus)] = max(0.0, min(1.0, float(value)))
    # Apply master to music immediately
    try:
        import pygame
        vol = _audio_buses.get("music", 1.0) * _audio_buses.get("master", 1.0)
        pygame.mixer.music.set_volume(vol)
    except Exception: pass

def _audio_mute(bus, muted=True):
    _audio_buses[str(bus)] = 0.0 if muted else 1.0

def _audio_play_at(sound, pos=None, listener=None, max_dist=500.0):
    """Positional audio: attenuate by distance."""
    if pos and listener:
        px = pos.get("x", 0) if isinstance(pos, dict) else getattr(pos, "x", 0)
        py = pos.get("y", 0) if isinstance(pos, dict) else getattr(pos, "y", 0)
        lx = listener.get("x", 0) if isinstance(listener, dict) else getattr(listener, "x", 0)
        ly = listener.get("y", 0) if isinstance(listener, dict) else getattr(listener, "y", 0)
        dist = _math.hypot(px-lx, py-ly)
        vol = max(0.0, 1.0 - dist / float(max_dist))
    else:
        vol = 1.0
    _audio_play(sound, volume=vol)

def _audio_is_music_playing():
    try:
        import pygame; return pygame.mixer.music.get_busy()
    except Exception: return False

register_module("audio", _wrapmod({
    "load":              _audio_load,
    "play":              _audio_play,
    "stop":              _audio_stop,
    "play_music":        _audio_play_music,
    "pause_music":       _audio_pause_music,
    "resume_music":      _audio_resume_music,
    "stop_music":        _audio_stop_music,
    "fade_out":          _audio_fade_out,
    "set_volume":        _audio_set_volume,
    "mute":              _audio_mute,
    "play_at":           _audio_play_at,
    "is_music_playing":  _audio_is_music_playing,
    "Sound":             _AudioSound,
    "ENABLED":           _AUDIO_ENABLED,
}, "audio"))

# ═══════════════════════════════════════════════════════════════════════════
# mat4 — 4×4 column-major matrix for 3D transforms  (pure Python, no NumPy)
# ═══════════════════════════════════════════════════════════════════════════
import math as _math

class _Mat4:
    """Immutable 4×4 matrix stored as a flat 16-element list (column-major)."""
    __slots__ = ("_m",)

    def __init__(self, m):
        # Accept list[16], tuple[16], or another _Mat4
        if isinstance(m, _Mat4):
            self._m = list(m._m)
        else:
            if len(m) != 16:
                raise ValueError("mat4 requires exactly 16 values")
            self._m = [float(v) for v in m]

    # ── indexing ──────────────────────────────────────────────────────────
    def get(self, row, col):
        """Return element at (row, col). Both 0-indexed."""
        return self._m[col * 4 + row]

    def to_array(self):
        return list(self._m)

    def __repr__(self):
        r = self._m
        def fmt(v): return f"{v:8.4f}"
        rows = []
        for row in range(4):
            rows.append(" ".join(fmt(r[col*4+row]) for col in range(4)))
        return "mat4[\n  " + "\n  ".join(rows) + "\n]"

    # InScript wants dicts for attribute access — expose as a dict-like wrapper
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._m[key]
        raise KeyError(key)

    def __len__(self):
        return 16

    def __iter__(self):
        return iter(self._m)


def _mat4_identity():
    """Return the 4×4 identity matrix."""
    return _Mat4([
        1,0,0,0,
        0,1,0,0,
        0,0,1,0,
        0,0,0,1,
    ])

def _mat4_zero():
    return _Mat4([0.0]*16)

def _mat4_from_list(lst):
    """Create a mat4 from a 16-element array."""
    if isinstance(lst, list) and len(lst) == 16:
        return _Mat4(lst)
    raise ValueError("mat4.from_array expects a 16-element array")

def _mat4_mul(a, b):
    """Matrix multiply a × b."""
    r = [0.0]*16
    for col in range(4):
        for row in range(4):
            s = 0.0
            for k in range(4):
                s += a._m[k*4+row] * b._m[col*4+k]
            r[col*4+row] = s
    return _Mat4(r)

def _mat4_mul_vec4(m, v):
    """Multiply mat4 × vec4 (list of 4 floats). Returns list[4]."""
    if isinstance(v, dict):
        v = [v.get("x",0), v.get("y",0), v.get("z",0), v.get("w",1)]
    x,y,z,w = float(v[0]), float(v[1]), float(v[2]), float(v[3])
    def dot(col):
        return (m._m[col*4]*x + m._m[col*4+1]*y +
                m._m[col*4+2]*z + m._m[col*4+3]*w)
    # Row-vector transform
    out = [0.0]*4
    for row in range(4):
        out[row] = (m._m[row]*x + m._m[4+row]*y +
                    m._m[8+row]*z + m._m[12+row]*w)
    return out

def _mat4_translate(x=0.0, y=0.0, z=0.0):
    """Return a translation matrix."""
    m = list(_mat4_identity()._m)
    m[12] = float(x); m[13] = float(y); m[14] = float(z)
    return _Mat4(m)

def _mat4_scale(x=1.0, y=1.0, z=1.0):
    """Return a scale matrix."""
    return _Mat4([
        x,0,0,0,
        0,y,0,0,
        0,0,z,0,
        0,0,0,1,
    ])

def _mat4_rotate_x(angle_rad):
    """Rotation around X-axis (radians)."""
    c = _math.cos(angle_rad); s = _math.sin(angle_rad)
    return _Mat4([
        1, 0, 0, 0,
        0, c, s, 0,
        0,-s, c, 0,
        0, 0, 0, 1,
    ])

def _mat4_rotate_y(angle_rad):
    """Rotation around Y-axis (radians)."""
    c = _math.cos(angle_rad); s = _math.sin(angle_rad)
    return _Mat4([
        c, 0,-s, 0,
        0, 1, 0, 0,
        s, 0, c, 0,
        0, 0, 0, 1,
    ])

def _mat4_rotate_z(angle_rad):
    """Rotation around Z-axis (radians)."""
    c = _math.cos(angle_rad); s = _math.sin(angle_rad)
    return _Mat4([
        c, s, 0, 0,
       -s, c, 0, 0,
        0, 0, 1, 0,
        0, 0, 0, 1,
    ])

def _mat4_rotate_axis(ax, ay, az, angle_rad):
    """Rotation around an arbitrary axis (ax,ay,az) by angle_rad."""
    # Normalise axis
    length = _math.sqrt(ax*ax + ay*ay + az*az)
    if length < 1e-10:
        return _mat4_identity()
    ax /= length; ay /= length; az /= length
    c = _math.cos(angle_rad); s = _math.sin(angle_rad); t = 1 - c
    return _Mat4([
        t*ax*ax+c,    t*ax*ay+s*az, t*ax*az-s*ay, 0,
        t*ax*ay-s*az, t*ay*ay+c,    t*ay*az+s*ax, 0,
        t*ax*az+s*ay, t*ay*az-s*ax, t*az*az+c,    0,
        0,            0,            0,            1,
    ])

def _mat4_perspective(fov_y_rad, aspect, near, far):
    """OpenGL-style perspective projection matrix."""
    f = 1.0 / _math.tan(fov_y_rad / 2.0)
    nf = 1.0 / (near - far)
    return _Mat4([
        f/aspect, 0,  0,                    0,
        0,        f,  0,                    0,
        0,        0,  (far+near)*nf,       -1,
        0,        0,  2*far*near*nf,        0,
    ])

def _mat4_ortho(left, right, bottom, top, near, far):
    """Orthographic projection matrix."""
    rl = 1.0/(right-left); tb = 1.0/(top-bottom); fn = 1.0/(far-near)
    return _Mat4([
        2*rl,       0,          0,      0,
        0,          2*tb,       0,      0,
        0,          0,         -2*fn,   0,
        -(right+left)*rl, -(top+bottom)*tb, -(far+near)*fn, 1,
    ])

def _mat4_look_at(ex, ey, ez, cx, cy, cz, ux, uy, uz):
    """View matrix: eye position, center target, up vector."""
    # Forward
    fx = cx-ex; fy = cy-ey; fz = cz-ez
    fl = _math.sqrt(fx*fx+fy*fy+fz*fz)
    if fl < 1e-10: return _mat4_identity()
    fx /= fl; fy /= fl; fz /= fl
    # Right = forward × up
    rx = fy*uz - fz*uy; ry = fz*ux - fx*uz; rz = fx*uy - fy*ux
    rl = _math.sqrt(rx*rx+ry*ry+rz*rz)
    if rl > 1e-10: rx /= rl; ry /= rl; rz /= rl
    # Up = right × forward
    ux2 = ry*fz - rz*fy; uy2 = rz*fx - rx*fz; uz2 = rx*fy - ry*fx
    return _Mat4([
        rx,   ux2,  -fx,  0,
        ry,   uy2,  -fy,  0,
        rz,   uz2,  -fz,  0,
        -(rx*ex+ry*ey+rz*ez), -(ux2*ex+uy2*ey+uz2*ez), (fx*ex+fy*ey+fz*ez), 1,
    ])

def _mat4_transpose(m):
    r = m._m
    return _Mat4([
        r[0], r[4], r[8],  r[12],
        r[1], r[5], r[9],  r[13],
        r[2], r[6], r[10], r[14],
        r[3], r[7], r[11], r[15],
    ])

def _mat4_inverse(m):
    """Return the inverse of m (raises ValueError if not invertible)."""
    # cofactor / adjugate method
    a = m._m
    b = [0.0]*16

    b[0]  =  a[5]*a[10]*a[15] - a[5]*a[11]*a[14] - a[9]*a[6]*a[15] + a[9]*a[7]*a[14] + a[13]*a[6]*a[11] - a[13]*a[7]*a[10]
    b[4]  = -a[4]*a[10]*a[15] + a[4]*a[11]*a[14] + a[8]*a[6]*a[15] - a[8]*a[7]*a[14] - a[12]*a[6]*a[11] + a[12]*a[7]*a[10]
    b[8]  =  a[4]*a[9]*a[15]  - a[4]*a[11]*a[13] - a[8]*a[5]*a[15] + a[8]*a[7]*a[13] + a[12]*a[5]*a[11] - a[12]*a[7]*a[9]
    b[12] = -a[4]*a[9]*a[14]  + a[4]*a[10]*a[13] + a[8]*a[5]*a[14] - a[8]*a[6]*a[13] - a[12]*a[5]*a[10] + a[12]*a[6]*a[9]

    det = a[0]*b[0] + a[1]*b[4] + a[2]*b[8] + a[3]*b[12]
    if abs(det) < 1e-15:
        raise ValueError("mat4.inverse: matrix is not invertible (det≈0)")
    inv = 1.0 / det

    b[1]  = (-a[1]*a[10]*a[15] + a[1]*a[11]*a[14] + a[9]*a[2]*a[15] - a[9]*a[3]*a[14] - a[13]*a[2]*a[11] + a[13]*a[3]*a[10]) * inv
    b[5]  = ( a[0]*a[10]*a[15] - a[0]*a[11]*a[14] - a[8]*a[2]*a[15] + a[8]*a[3]*a[14] + a[12]*a[2]*a[11] - a[12]*a[3]*a[10]) * inv
    b[9]  = (-a[0]*a[9]*a[15]  + a[0]*a[11]*a[13] + a[8]*a[1]*a[15] - a[8]*a[3]*a[13] - a[12]*a[1]*a[11] + a[12]*a[3]*a[9])  * inv
    b[13] = ( a[0]*a[9]*a[14]  - a[0]*a[10]*a[13] - a[8]*a[1]*a[14] + a[8]*a[2]*a[13] + a[12]*a[1]*a[10] - a[12]*a[2]*a[9])  * inv
    b[2]  = ( a[1]*a[6]*a[15]  - a[1]*a[7]*a[14]  - a[5]*a[2]*a[15] + a[5]*a[3]*a[14] + a[13]*a[2]*a[7]  - a[13]*a[3]*a[6])  * inv
    b[6]  = (-a[0]*a[6]*a[15]  + a[0]*a[7]*a[14]  + a[4]*a[2]*a[15] - a[4]*a[3]*a[14] - a[12]*a[2]*a[7]  + a[12]*a[3]*a[6])  * inv
    b[10] = ( a[0]*a[5]*a[15]  - a[0]*a[7]*a[13]  - a[4]*a[1]*a[15] + a[4]*a[3]*a[13] + a[12]*a[1]*a[7]  - a[12]*a[3]*a[5])  * inv
    b[14] = (-a[0]*a[5]*a[14]  + a[0]*a[6]*a[13]  + a[4]*a[1]*a[14] - a[4]*a[2]*a[13] - a[12]*a[1]*a[6]  + a[12]*a[2]*a[5])  * inv
    b[3]  = (-a[1]*a[6]*a[11]  + a[1]*a[7]*a[10]  + a[5]*a[2]*a[11] - a[5]*a[3]*a[10] - a[9]*a[2]*a[7]   + a[9]*a[3]*a[6])   * inv
    b[7]  = ( a[0]*a[6]*a[11]  - a[0]*a[7]*a[10]  - a[4]*a[2]*a[11] + a[4]*a[3]*a[10] + a[8]*a[2]*a[7]   - a[8]*a[3]*a[6])   * inv
    b[11] = (-a[0]*a[5]*a[11]  + a[0]*a[7]*a[9]   + a[4]*a[1]*a[11] - a[4]*a[3]*a[9]  - a[8]*a[1]*a[7]   + a[8]*a[3]*a[5])   * inv
    b[15] = ( a[0]*a[5]*a[10]  - a[0]*a[6]*a[9]   - a[4]*a[1]*a[10] + a[4]*a[2]*a[9]  + a[8]*a[1]*a[6]   - a[8]*a[2]*a[5])   * inv

    # Apply remaining inv factor to first row
    for i in (0,4,8,12):
        b[i] *= inv

    return _Mat4(b)

def _mat4_det(m):
    a = m._m
    cf0 =  a[5]*a[10]*a[15] - a[5]*a[11]*a[14] - a[9]*a[6]*a[15] + a[9]*a[7]*a[14] + a[13]*a[6]*a[11] - a[13]*a[7]*a[10]
    cf4 = -a[4]*a[10]*a[15] + a[4]*a[11]*a[14] + a[8]*a[6]*a[15] - a[8]*a[7]*a[14] - a[12]*a[6]*a[11] + a[12]*a[7]*a[10]
    cf8 =  a[4]*a[9]*a[15]  - a[4]*a[11]*a[13] - a[8]*a[5]*a[15] + a[8]*a[7]*a[13] + a[12]*a[5]*a[11] - a[12]*a[7]*a[9]
    cf12= -a[4]*a[9]*a[14]  + a[4]*a[10]*a[13] + a[8]*a[5]*a[14] - a[8]*a[6]*a[13] - a[12]*a[5]*a[10] + a[12]*a[6]*a[9]
    return a[0]*cf0 + a[1]*cf4 + a[2]*cf8 + a[3]*cf12

def _mat4_to_array(m):
    return list(m._m)

def _mat4_get(m, row, col):
    return m._m[int(col)*4 + int(row)]

register_module("mat4", _wrapmod({
    # Constructors
    "identity":    _mat4_identity,
    "zero":        _mat4_zero,
    "from_array":  _mat4_from_list,
    # Transforms
    "translate":   _mat4_translate,
    "scale":       _mat4_scale,
    "rotate_x":    _mat4_rotate_x,
    "rotate_y":    _mat4_rotate_y,
    "rotate_z":    _mat4_rotate_z,
    "rotate_axis": _mat4_rotate_axis,
    # Projections
    "perspective": _mat4_perspective,
    "ortho":       _mat4_ortho,
    "look_at":     _mat4_look_at,
    # Operations
    "mul":         _mat4_mul,
    "mul_vec4":    _mat4_mul_vec4,
    "transpose":   _mat4_transpose,
    "inverse":     _mat4_inverse,
    "det":         _mat4_det,
    "to_array":    _mat4_to_array,
    "get":         _mat4_get,
}, "mat4"))
