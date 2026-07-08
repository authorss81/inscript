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

# ═══════════════════════════════════════════════════════════════════════════
# 5.3 — animation module (continued): v3.9.6.43 Animation Player
# ═══════════════════════════════════════════════════════════════════════════

import math as _anim_math

def _anim_ease_linear(t):
    return t

def _anim_ease_in_quad(t):
    return t * t

def _anim_ease_out_quad(t):
    return t * (2 - t)

def _anim_ease_io_quad(t):
    return 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t

def _anim_ease_in_cubic(t):
    return t * t * t

def _anim_ease_out_cubic(t):
    p = t - 1
    return p * p * p + 1

def _anim_ease_out_bounce(t):
    n1, d1 = 7.5625, 2.75
    if t < 1 / d1:
        return n1 * t * t
    if t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375

def _anim_ease_in_bounce(t):
    return 1 - _anim_ease_out_bounce(1 - t)

def _anim_ease_out_elastic(t):
    c4 = (2 * _anim_math.pi) / 3
    if t == 0:
        return 0
    if t == 1:
        return 1
    return 2 ** (-10 * t) * _anim_math.sin((t * 10 - 0.75) * c4) + 1

def _anim_ease_in_elastic(t):
    c4 = (2 * _anim_math.pi) / 3
    if t == 0:
        return 0
    if t == 1:
        return 1
    return -(2 ** (10 * t - 10)) * _anim_math.sin((t * 10 - 10.75) * c4)

_EASING_FUNCS = {
    "linear":       _anim_ease_linear,
    "ease_in":      _anim_ease_in_quad,
    "ease_out":     _anim_ease_out_quad,
    "ease_in_out":  _anim_ease_io_quad,
    "ease_in_quad": _anim_ease_in_quad,
    "ease_out_quad":_anim_ease_out_quad,
    "ease_in_cubic":_anim_ease_in_cubic,
    "ease_out_cubic":_anim_ease_out_cubic,
    "ease_in_bounce":_anim_ease_in_bounce,
    "ease_out_bounce":_anim_ease_out_bounce,
    "ease_in_elastic":_anim_ease_in_elastic,
    "ease_out_elastic":_anim_ease_out_elastic,
}

def _lerp_val(a, b, t):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + (b - a) * t
    if isinstance(a, dict) and isinstance(b, dict) and "x" in a and "y" in a:
        return {"x": a["x"] + (b["x"] - a["x"]) * t, "y": a["y"] + (b["y"] - a["y"]) * t}
    if isinstance(a, dict) and isinstance(b, dict) and "r" in a:
        return {"r": a["r"] + (b["r"] - a["r"]) * t,
                "g": a["g"] + (b["g"] - a["g"]) * t,
                "b": a["b"] + (b["b"] - a["b"]) * t,
                "a": (a.get("a", 1) + (b.get("a", 1) - a.get("a", 1))) * t}
    return b if t >= 0.5 else a

class _Keyframe:
    def __init__(self, time, value, easing="linear"):
        self.time = float(time)
        self.value = value
        self.easing = easing if easing in _EASING_FUNCS else "linear"

    def __repr__(self):
        return f"<Keyframe t={self.time} val={self.value!r} ease={self.easing}>"

class _Track:
    def __init__(self, name, keyframes=None, mode="parallel"):
        self.name = name
        self.keyframes = list(keyframes or [])
        self.mode = mode
        if self.keyframes:
            self.keyframes.sort(key=lambda kf: kf.time)
        self._duration = max((kf.time for kf in self.keyframes), default=0.0)

    def add_keyframe(self, kf):
        self.keyframes.append(kf)
        self.keyframes.sort(key=lambda kf: kf.time)
        self._duration = max(kf.time, self._duration)

    def duration(self):
        return self._duration

    def sample(self, t):
        if not self.keyframes:
            return None
        if t <= self.keyframes[0].time:
            return self.keyframes[0].value
        if t >= self.keyframes[-1].time:
            return self.keyframes[-1].value
        for i in range(len(self.keyframes) - 1):
            a = self.keyframes[i]
            b = self.keyframes[i + 1]
            if a.time <= t < b.time:
                span = b.time - a.time
                local_t = (t - a.time) / span if span > 0 else 0.0
                easing_fn = _EASING_FUNCS.get(a.easing, _anim_ease_linear)
                et = easing_fn(max(0.0, min(1.0, local_t)))
                return _lerp_val(a.value, b.value, et)
        return self.keyframes[-1].value

    def __repr__(self):
        return f"<Track '{self.name}' {len(self.keyframes)} kf dur={self._duration:.2f}s>"

class _AnimationPlayer:
    def __init__(self):
        self._tracks = {}
        self._playing = False
        self._paused = False
        self._time = 0.0
        self._speed = 1.0
        self._loop = False
        self._duration = 0.0
        self._done = False
        self._order = []

    def add_track(self, name, keyframes=None, mode="parallel"):
        if isinstance(name, _Track):
            track = name
            name = track.name
        else:
            track = _Track(str(name), keyframes, mode)
        self._tracks[name] = track
        if name not in self._order:
            self._order.append(name)
        self._rebuild_duration()
        return track

    def remove_track(self, name):
        self._tracks.pop(str(name), None)
        self._order = [n for n in self._order if n != str(name)]
        self._rebuild_duration()

    def _rebuild_duration(self):
        dur = 0.0
        sequential_offset = 0.0
        for name in self._order:
            t = self._tracks[name]
            if t.mode == "parallel":
                dur = max(dur, sequential_offset + t.duration())
            else:
                sequential_offset += t.duration()
                dur = max(dur, sequential_offset)
        self._duration = dur

    def play(self, loop=False):
        self._playing = True
        self._paused = False
        self._loop = bool(loop)
        if self._done:
            self._time = 0.0
            self._done = False

    def set_loop(self, v):
        self._loop = bool(v)

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def stop(self):
        self._playing = False
        self._paused = False
        self._time = 0.0
        self._done = False

    def seek(self, t):
        self._time = max(0.0, float(t))

    def set_speed(self, v):
        self._speed = max(0.0, float(v))

    def update(self, dt):
        if not self._playing or self._paused or self._done:
            return
        self._time += float(dt) * self._speed
        if self._time >= self._duration:
            if self._loop:
                self._time %= self._duration
            else:
                self._time = self._duration
                self._done = True
                self._playing = False

    def value(self, name):
        track = self._tracks.get(str(name))
        if track is None:
            return None
        t = self._time
        sequential_offset = 0.0
        for n in self._order:
            tr = self._tracks[n]
            if n == str(name):
                sample_t = t - sequential_offset if tr.mode == "sequential" else t
                return tr.sample(sample_t)
            if tr.mode == "sequential":
                sequential_offset += tr.duration()
        return None

    def values(self):
        result = {}
        for name in self._tracks:
            result[name] = self.value(name)
        return result

    @property
    def time(self):
        return self._time

    @property
    def speed(self):
        return self._speed

    @speed.setter
    def speed(self, v):
        self._speed = max(0.0, float(v))

    @property
    def playing(self):
        return self._playing

    @property
    def done(self):
        return self._done

    @property
    def duration(self):
        return self._duration

    @property
    def progress(self):
        return min(self._time / self._duration, 1.0) if self._duration > 0 else 0.0

    def __repr__(self):
        return f"<AnimationPlayer {len(self._tracks)} tracks t={self._time:.2f}/{self._duration:.2f}s playing={self._playing}>"

# ═══════════════════════════════════════════════════════════════════════════
# 5.3 — animation module (continued): v3.9.6.44 State Machine
# ═══════════════════════════════════════════════════════════════════════════

class _SMState:
    def __init__(self, name, on_enter=None, on_leave=None, on_update=None):
        self.name = str(name)
        self.on_enter = on_enter
        self.on_leave = on_leave
        self.on_update = on_update
    def __repr__(self):
        return f"<SMState '{self.name}'>"

class _SMTransition:
    def __init__(self, from_state, to_state, condition=None, event=None):
        self.from_state = str(from_state)
        self.to_state = str(to_state)
        self.condition = condition
        self.event = str(event) if event else None
    def __repr__(self):
        return f"<SMTransition {self.from_state} -> {self.to_state}>"

class _StateMachine:
    def __init__(self):
        self._states = {}
        self._transitions = []
        self._current = None
        self._previous = None
        self._time_in_state = 0.0
        self._history = []

    def add_state(self, name, on_enter=None, on_leave=None, on_update=None):
        s = _SMState(name, on_enter, on_leave, on_update)
        self._states[name] = s

    def add_transition(self, from_state, to_state, event_or_condition=None):
        if event_or_condition is None:
            tr = _SMTransition(from_state, to_state)
        elif isinstance(event_or_condition, str):
            tr = _SMTransition(from_state, to_state, event=event_or_condition)
        else:
            tr = _SMTransition(from_state, to_state, condition=event_or_condition)
        self._transitions.append(tr)

    def start(self, name):
        if name not in self._states:
            raise KeyError(f"StateMachine: state '{name}' not found")
        self._current = name
        self._previous = None
        self._time_in_state = 0.0
        self._history = []
        s = self._states[name]
        if s.on_enter:
            s.on_enter()

    def trigger(self, event):
        if self._current is None:
            return
        for tr in self._transitions:
            if tr.from_state == self._current and tr.event == str(event):
                self._change_state(tr.to_state)
                return

    def update(self, dt):
        if self._current is None:
            return
        self._time_in_state += float(dt)
        s = self._states[self._current]
        if s.on_update:
            s.on_update(dt)
        for tr in self._transitions:
            if tr.from_state == self._current and tr.event is None:
                if tr.condition and tr.condition():
                    self._change_state(tr.to_state)
                    return

    def _change_state(self, new_name):
        old = self._states.get(self._current)
        if old and old.on_leave:
            old.on_leave()
        self._previous = self._current
        self._current = new_name
        self._time_in_state = 0.0
        self._history.append((self._previous, new_name))
        s = self._states.get(new_name)
        if s and s.on_enter:
            s.on_enter()

    @property
    def current(self):
        return self._current

    @property
    def previous(self):
        return self._previous

    @property
    def time_in_state(self):
        return self._time_in_state

    @property
    def history(self):
        return self._history

    def __repr__(self):
        return f"<StateMachine states={list(self._states.keys())} current={self._current}>"

register_module("animation", _wrapmod({
    "Clip":     lambda name, frame_names, fps=12, loop=True: _Clip(name, frame_names, fps, loop),
    "Animator": _Animator,
    # v43: Animation Player
    "keyframe":   _Keyframe,
    "Track":      _Track,
    "AnimationPlayer": _AnimationPlayer,
    # v44: State Machine
    "StateMachine":  _StateMachine,
    "SMState":       _SMState,
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
        self._overlapping = set()
        self._on_trigger_enter_cb = None
        self._on_trigger_exit_cb = None

    def on_overlap(self, fn):
        self.on_overlap_cb = fn

    def on_trigger_enter(self, fn):
        self._on_trigger_enter_cb = fn

    def on_trigger_exit(self, fn):
        self._on_trigger_exit_cb = fn

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
        areas = [b for b in self._bodies if isinstance(b, _P2DArea) and b._alive]

        # Gravity + integrate
        for b in dynamics:
            b.velocity.x += self._gx * dt
            b.velocity.y += self._gy * dt
            b.position.x += b.velocity.x * dt
            b.position.y += b.velocity.y * dt

        # AABB helpers
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

        # Collision resolution: dynamics vs statics
        for d in dynamics:
            for s in statics:
                if _overlap(d, s):
                    ax1,ay1,ax2,ay2 = _aabb(d); bx1,by1,bx2,by2 = _aabb(s)
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

        # Trigger enter/exit tracking for Areas
        for area in areas:
            now = {b for b in self._bodies if b is not area and b._alive and _overlap(area, b)}
            entered = now - area._overlapping
            exited  = area._overlapping - now
            for b in entered:
                if area._on_trigger_enter_cb:
                    area._on_trigger_enter_cb(area, b)
            for b in exited:
                if area._on_trigger_exit_cb:
                    area._on_trigger_exit_cb(area, b)
            area._overlapping = now

    def query_area(self, area):
        """Return list of bodies currently overlapping `area`."""
        return [b for b in self._bodies if b is not area and b._alive and self._overlap_bodies(area, b)]

    def _overlap_bodies(self, a, b):
        def _aabb(body):
            if isinstance(body.shape, _P2DRect):
                hw, hh = body.shape.w/2, body.shape.h/2
                return (body.x - hw, body.y - hh, body.x + hw, body.y + hh)
            elif isinstance(body.shape, _P2DCircle):
                r = body.shape.r
                return (body.x - r, body.y - r, body.x + r, body.y + r)
            return (body.x, body.y, body.x, body.y)
        ax1,ay1,ax2,ay2 = _aabb(a); bx1,by1,bx2,by2 = _aabb(b)
        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1

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
# 5.7 — particle module (v3.9.6.40-42: emission shapes, curves, advanced)
# ═══════════════════════════════════════════════════════════════════════════

import random as _random
import math as _math
from collections import namedtuple as _namedtuple

# ── v3.9.6.41: Curve class ─────────────────────────────────────────────────
class _Curve:
    """Keyframe-less curve: shape + interpolation between start/end over t∈[0,1]."""
    SHAPES = frozenset({"linear", "sine", "quadratic", "exponential", "bounce", "elastic"})
    __slots__ = ("shape", "start", "end")

    def __init__(self, shape="linear", start=0.0, end=1.0):
        self.shape = str(shape)
        self.start = float(start)
        self.end   = float(end)

    def evaluate(self, t):
        t = max(0.0, min(1.0, float(t)))
        s, e = self.start, self.end
        if self.shape == "linear":
            return s + (e - s) * t
        if self.shape == "sine":
            return s + (e - s) * _math.sin(t * _math.pi / 2.0)
        if self.shape == "quadratic":
            return s + (e - s) * t * t
        if self.shape == "exponential":
            return s + (e - s) * (1.0 - _math.exp(-t * 5.0))
        if self.shape == "bounce":
            if t < 0.5: return s + (e - s) * (2.0 * t * t)
            return s + (e - s) * (1.0 - (-2.0 * t * t + 4.0 * t - 1.0) / 2.0)
        if self.shape == "elastic":
            return s + (e - s) * _math.pow(2.0, -10.0 * t) * _math.sin((t - 0.075) * 2.0 * _math.pi / 0.3) + s
        return s

    def __repr__(self):
        return f"<_Curve({self.shape} {self.start}→{self.end})>"


# ── v3.9.6.42: Attractor zone ──────────────────────────────────────────────
class _AttractorZone:
    __slots__ = ("x", "y", "strength", "radius")
    def __init__(self, x, y, strength, radius):
        self.x = float(x); self.y = float(y)
        self.strength = float(strength)
        self.radius   = float(radius)

    def apply(self, p, dt):
        dx = self.x - p.x
        dy = self.y - p.y
        dist = _math.hypot(dx, dy)
        if dist < 0.001 or dist > self.radius:
            return
        force = self.strength * (1.0 - dist / self.radius) * dt
        p.vx += (dx / dist) * force
        p.vy += (dy / dist) * force


# ── v3.9.6.40: Enhanced _Particle with rotation, acceleration, trails ─────
class _Particle:
    __slots__ = ("x","y","vx","vy","ax","ay","life","max_life",
                 "r0","g0","b0","a0","r1","g1","b1","a1",
                 "size","size_end","rotation","rotation_speed","gx","gy",
                 "trail_x","trail_y","sub_triggered")
    def __init__(self, x, y, vx, vy, life,
                 r0, g0, b0, a0, r1, g1, b1, a1,
                 size, size_end, gx, gy, rotation=0.0, rotation_speed=0.0):
        self.x=x; self.y=y; self.vx=vx; self.vy=vy
        self.ax=0.0; self.ay=0.0
        self.life=life; self.max_life=life
        self.r0=r0; self.g0=g0; self.b0=b0; self.a0=a0
        self.r1=r1; self.g1=g1; self.b1=b1; self.a1=a1
        self.size=size; self.size_end=size_end
        self.rotation=rotation; self.rotation_speed=rotation_speed
        self.gx=gx; self.gy=gy
        self.trail_x=[]; self.trail_y=[]
        self.sub_triggered=False

    def _t(self):
        return 1.0 - self.life / max(self.max_life, 0.0001)


# ── v3.9.6.40-42: Full _Emitter (ParticleEmitter) ─────────────────────────
class _Emitter:
    def __init__(self, x=0, y=0):
        self.x = float(x); self.y = float(y)

        # Emission
        self.rate = 30.0
        self.lifetime = (0.5, 1.5)
        self.speed = (50.0, 150.0)
        self.angle = (0.0, 360.0)
        self.max_particles = 1000

        # v40: Rotation
        self.rotation_start = 0.0
        self.rotation_end = 0.0
        self.rotation_speed_range = (0.0, 0.0)

        # v40: Emission shapes
        self.emission_shape = "point"
        self.emission_radius = 0.0
        self.emission_width = 0.0
        self.emission_height = 0.0
        self.emission_angle = 0.0

        # v40: Modes
        self.one_shot = False
        self.local_space = False

        # v41: Curves
        self.size_curve = None
        self.alpha_curve = None
        self.velocity_curve = None
        self.rotation_curve = None

        # v41: Environment
        self.wind_x = 0.0
        self.wind_y = 0.0

        # v42: Sub-emitter
        self.sub_emitter = None

        # v42: Attractors
        self._attractors = []

        # v42: Trails
        self.trail_length = 0
        self.trail_spacing = 0.02

        # v42: Collision
        self.collision_enabled = False
        self.bounce_factor = 0.5
        self.collision_dampening = 0.5
        self.collision_bounds = None  # (x, y, w, h) or None

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
        self._trail_accum = 0.0

    # ── spawn position helpers for emission shapes ─────────────────────────
    def _spawn_pos(self):
        sx, sy = self.x, self.y
        shape = self.emission_shape
        if shape == "point":
            pass
        elif shape == "circle":
            a = _random.uniform(0.0, _math.pi * 2.0)
            r = _random.uniform(0.0, self.emission_radius)
            sx += _math.cos(a) * r
            sy += _math.sin(a) * r
        elif shape == "rectangle":
            sx += _random.uniform(-self.emission_width/2, self.emission_width/2)
            sy += _random.uniform(-self.emission_height/2, self.emission_height/2)
        elif shape == "cone":
            half = self.emission_angle / 2.0 * _math.pi / 180.0
            a = _random.uniform(-half, half)
            r = _random.uniform(0.0, self.emission_radius)
            sx += _math.cos(a) * r
            sy += _math.sin(a) * r
        return sx, sy

    def _spawn_one(self):
        angle = _random.uniform(*self.angle) * _math.pi / 180.0
        speed = _random.uniform(*self.speed)
        life  = _random.uniform(*self.lifetime)
        cs, ce = self.color_start, self.color_end
        sx, sy = self._spawn_pos()

        # Rotation
        if self.rotation_speed_range != (0.0, 0.0):
            rotspeed = _random.uniform(*self.rotation_speed_range)
        else:
            rotspeed = 0.0
        if self.rotation_start != 0.0 or self.rotation_end != 0.0:
            rot = _random.uniform(self.rotation_start, self.rotation_end)
        else:
            rot = 0.0

        return _Particle(
            sx, sy,
            _math.cos(angle)*speed, _math.sin(angle)*speed,
            life,
            cs.get("r",1)*255, cs.get("g",0)*255, cs.get("b",0)*255, cs.get("a",1)*255,
            ce.get("r",1)*255, ce.get("g",0)*255, ce.get("b",0)*255, ce.get("a",0)*255,
            self.size_start, self.size_end,
            self.gravity_x, self.gravity_y,
            rotation=rot, rotation_speed=rotspeed,
        )

    def burst(self, count=20):
        count = int(count)
        for _ in range(count):
            if len(self._particles) >= self.max_particles:
                break
            self._particles.append(self._spawn_one())

    def start(self):
        self._running = True
        if self.one_shot:
            self.burst(int(self.rate))
            self._running = False

    def stop(self):
        self._running = False

    def set_position(self, x, y):
        dx = float(x) - self.x
        dy = float(y) - self.y
        self.x = float(x)
        self.y = float(y)
        if self.local_space:
            for p in self._particles:
                p.x += dx
                p.y += dy

    # ── v41: Curve helpers ─────────────────────────────────────────────────
    def _apply_curves(self, p):
        t = p._t()
        if self.size_curve:
            p.size = self.size_curve.evaluate(t) * self.size_start
        else:
            p.size = p.size + (p.size_end - p.size) * t

        if self.alpha_curve:
            val = max(0.0, min(1.0, self.alpha_curve.evaluate(t)))
            p.a1 = val * 255
        if self.velocity_curve:
            mult = max(0.0, self.velocity_curve.evaluate(t))
            p.vx *= mult
            p.vy *= mult
        if self.rotation_curve:
            p.rotation = self.rotation_curve.evaluate(t)

    # ── v42: Collision ─────────────────────────────────────────────────────
    def _apply_collision(self, p, dt):
        if not self.collision_enabled or self.collision_bounds is None:
            return
        bx, by, bw, bh = self.collision_bounds
        if p.x - p.size < bx:
            p.x = bx + p.size
            p.vx = -p.vx * self.bounce_factor
            p.vy *= self.collision_dampening
        elif p.x + p.size > bx + bw:
            p.x = bx + bw - p.size
            p.vx = -p.vx * self.bounce_factor
            p.vy *= self.collision_dampening
        if p.y - p.size < by:
            p.y = by + p.size
            p.vy = -p.vy * self.bounce_factor
            p.vx *= self.collision_dampening
        elif p.y + p.size > by + bh:
            p.y = by + bh - p.size
            p.vy = -p.vy * self.bounce_factor
            p.vx *= self.collision_dampening

    # ── v42: Sub-emitter trigger ───────────────────────────────────────────
    def _trigger_sub(self, p):
        if self.sub_emitter is None or p.sub_triggered:
            return
        p.sub_triggered = True
        se = self.sub_emitter
        if isinstance(se, _Emitter):
            se.set_position(p.x, p.y)
            se.burst(int(se.rate * 0.5 + 1))

    # ── v42: Trail recording ───────────────────────────────────────────────
    def _record_trails(self, dt):
        if self.trail_length <= 0:
            return
        self._trail_accum += dt
        if self._trail_accum < self.trail_spacing:
            return
        self._trail_accum = 0.0
        for p in self._particles:
            if len(p.trail_x) >= self.trail_length:
                p.trail_x.pop(0)
                p.trail_y.pop(0)
            p.trail_x.append(p.x)
            p.trail_y.append(p.y)

    # ── Main update ────────────────────────────────────────────────────────
    def update(self, dt):
        dt = float(dt)

        # Spawn new (v40: respect max_particles)
        if self._running and not self.one_shot:
            self._accumulator += self.rate * dt
            while self._accumulator >= 1.0:
                if len(self._particles) >= self.max_particles:
                    self._accumulator = 0.0
                    break
                self._particles.append(self._spawn_one())
                self._accumulator -= 1.0
        elif self._running and self.one_shot:
            self._running = False

        # Update existing + apply attractors / wind / collision
        alive = []
        for p in self._particles:
            p.life -= dt
            if p.life <= 0:
                self._trigger_sub(p)
                continue

            # Gravity
            p.vx += p.gx * dt
            p.vy += p.gy * dt

            vx_curve = 1.0
            vy_curve = 1.0
            if self.velocity_curve:
                vc = max(0.0, self.velocity_curve.evaluate(p._t()))
                vx_curve = vc
                vy_curve = vc

            # Wind (v41)
            p.vx += self.wind_x * dt * vx_curve
            p.vy += self.wind_y * dt * vy_curve

            # Acceleration (from attractors)
            p.vx += p.ax * dt
            p.vy += p.ay * dt

            # Attractors (v42)
            for attr in self._attractors:
                attr.apply(p, dt)

            # Integrate position
            p.x += p.vx * dt * vx_curve
            p.y += p.vy * dt * vy_curve

            # Rotation
            p.rotation += p.rotation_speed * dt

            # Collision (v42)
            self._apply_collision(p, dt)

            # Curves (v41)
            self._apply_curves(p)

            alive.append(p)

        self._particles = alive

        # Trails (v42)
        self._record_trails(dt)

    # ── v40: GPU-batchable draw ────────────────────────────────────────────
    def draw(self, renderer=None):
        """Draw all particles. If renderer (DrawNamespace) is provided, draw
        directly via pygame circles. Otherwise no-op (headless)."""
        if renderer is None:
            return
        has_pygame = type(renderer).__module__.startswith("pygame_backend") or True
        if not has_pygame:
            return
        for p in self._particles:
            t = p._t()
            r = int(p.r0 + (p.r1 - p.r0) * t)
            g = int(p.g0 + (p.g1 - p.g0) * t)
            b = int(p.b0 + (p.b1 - p.b0) * t)
            a = int(p.a0 + (p.a1 - p.a0) * t)
            a = max(0, min(255, a))
            sz = max(0.5, p.size)
            renderer.circle(p.x, p.y, sz, {"r":r/255,"g":g/255,"b":b/255,"a":a/255})

    # ── v40: Return batched draw data as list of dicts ─────────────────────
    def draw_batch(self):
        """Return pre-computed particle data for efficient rendering.
        Each entry: {x, y, r, g, b, a, size, rotation}."""
        out = []
        for p in self._particles:
            t = p._t()
            r = int(p.r0 + (p.r1 - p.r0) * t)
            g = int(p.g0 + (p.g1 - p.g0) * t)
            b = int(p.b0 + (p.b1 - p.b0) * t)
            a = int(p.a0 + (p.a1 - p.a0) * t)
            sz = max(0.5, p.size)
            out.append({
                "x": p.x,
                "y": p.y,
                "r": r, "g": g, "b": b, "a": max(0, min(255, a)),
                "size": sz,
                "rotation": p.rotation,
            })
        return out

    # ── v40: particle_data (backward compat) ───────────────────────────────
    def particle_data(self):
        out = []
        for p in self._particles:
            t = p._t()
            lerp = lambda a, b: a + (b - a) * t
            out.append({
                "x": p.x,
                "y": p.y,
                "r": lerp(p.r0, p.r1),
                "g": lerp(p.g0, p.g1),
                "b": lerp(p.b0, p.b1),
                "a": lerp(p.a0, p.a1),
                "size": lerp(p.size, p.size_end),
            })
        return out

    # ── v42: Pre-warm ──────────────────────────────────────────────────────
    def pre_warm(self, duration):
        """Pre-simulate the emitter for `duration` seconds."""
        steps = int(duration / 0.016)  # ~60Hz
        for _ in range(steps):
            self.update(0.016)

    # ── v42: Attractor management ──────────────────────────────────────────
    def add_attractor(self, x, y, strength, radius):
        self._attractors.append(_AttractorZone(x, y, strength, radius))

    def clear_attractors(self):
        self._attractors.clear()

    # ── Properties ─────────────────────────────────────────────────────────
    @property
    def count(self):
        return len(self._particles)

    def __repr__(self):
        return f"<Emitter particles={len(self._particles)} running={self._running}>"


# ── Alias for public API ───────────────────────────────────────────────────
_ParticleEmitter = _Emitter


# ── Module registration ────────────────────────────────────────────────────
_particle_exports = {
    "Emitter":      lambda x=0, y=0: _Emitter(x, y),
    "ParticleEmitter": lambda x=0, y=0: _ParticleEmitter(x, y),
    "start":        lambda e: e.start(),
    "stop":         lambda e: e.stop(),
    "update":       lambda e, dt: e.update(dt),
    "burst":        lambda e, n=None: e.burst(n),
    "set_position": lambda e, x, y: e.set_position(x, y),
    "rate":         lambda e, v: setattr(e, "rate", float(v)),
    "lifetime":     lambda e, v: setattr(e, "lifetime", tuple(float(x) for x in v)),
    "speed":        lambda e, v: setattr(e, "speed", tuple(float(x) for x in v)),
    "angle":        lambda e, v: setattr(e, "angle", tuple(float(x) for x in v)),
    "count":        lambda e: e.count(),
    "color_start":  lambda e, r, g, b, a=1.0: _set_color(e, "color_start", r, g, b, a),
    "color_end":    lambda e, r, g, b, a=0.0: _set_color(e, "color_end", r, g, b, a),
    "size_start":   lambda e, v: setattr(e, "size_start", float(v)),
    "size_end":     lambda e, v: setattr(e, "size_end", float(v)),
    "gravity":      lambda e, x, y: (setattr(e, "gravity_x", x), setattr(e, "gravity_y", y)),
    # v40: Emission shapes
    "set_shape":    lambda e, shape, r=0, w=0, h=0, a=0: _set_shape(e, shape, r, w, h, a),
    "max_particles": lambda e, v: setattr(e, "max_particles", int(v)),
    "one_shot":     lambda e, v: setattr(e, "one_shot", bool(v)),
    "local_space":  lambda e, v: setattr(e, "local_space", bool(v)),
    "rotation_start": lambda e, v: setattr(e, "rotation_start", float(v)),
    "rotation_end":   lambda e, v: setattr(e, "rotation_end", float(v)),
    "rotation_speed": lambda e, lo, hi=None: _rotation_speed(e, lo, hi),
    "draw_batch":   lambda e: e.draw_batch(),
    "draw":         lambda e, r=None: e.draw(r),
    # v41: Curves
    "curve":        lambda shape="linear", start=0.0, end=1.0: _Curve(shape, start, end),
    "set_size_curve":     lambda e, c: setattr(e, "size_curve", c),
    "set_alpha_curve":    lambda e, c: setattr(e, "alpha_curve", c),
    "set_velocity_curve": lambda e, c: setattr(e, "velocity_curve", c),
    "set_rotation_curve": lambda e, c: setattr(e, "rotation_curve", c),
    "wind":         lambda e, x, y: _set_wind(e, x, y),
    # v42: Advanced
    "sub_emitter":  lambda e, child: setattr(e, "sub_emitter", child),
    "add_attractor": lambda e, x, y, s, r: e.add_attractor(x, y, s, r),
    "clear_attractors": lambda e: e.clear_attractors(),
    "set_collision": lambda e, enabled, bounds=None, bounce=0.5, damp=0.5: _set_collision(e, enabled, bounds, bounce, damp),
    "set_trail":    lambda e, length, spacing=0.02: _set_trail(e, length, spacing),
    "pre_warm":     lambda e, dur: e.pre_warm(dur),
}

def _set_shape(e, shape, r=0, w=0, h=0, a=0):
    e.emission_shape = str(shape)
    e.emission_radius = float(r)
    e.emission_width = float(w)
    e.emission_height = float(h)
    e.emission_angle = float(a)

def _rotation_speed(e, lo, hi=None):
    if hi is None:
        hi = lo
    e.rotation_speed_range = (float(lo), float(hi))

def _set_wind(e, x, y):
    e.wind_x = float(x)
    e.wind_y = float(y)

def _set_collision(e, enabled, bounds=None, bounce=0.5, damp=0.5):
    e.collision_enabled = bool(enabled)
    if bounds is not None:
        e.collision_bounds = tuple(float(v) for v in bounds)
    e.bounce_factor = float(bounce)
    e.collision_dampening = float(damp)

def _set_trail(e, length, spacing=0.02):
    e.trail_length = int(length)
    e.trail_spacing = float(spacing)

def _set_color(e, attr, r, g, b, a):
    getattr(e, attr).update({"r": float(r), "g": float(g), "b": float(b), "a": float(a)})

register_module("particle", _wrapmod(_particle_exports, "particle"))

# v40: Also register the `particles` alias
register_module("particles", _wrapmod(_particle_exports, "particles"))

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
        # v2.13.0: headless emulation — inject key/mouse state without pygame
        self._emulated_keys:    dict  = {}   # key_name -> bool (held)
        self._emulated_mouse:   tuple = (0.0, 0.0)
        self._emulated_buttons: dict  = {}
        self._headless          = False  # set True when pygame unavailable

    def _try_pygame(self) -> bool:
        try:
            import pygame
            return pygame.get_init()
        except Exception:
            return False

    # v2.13.0: headless injection API
    def emulate_key(self, key: str, held: bool = True):
        """Inject a key state for headless/Studio preview mode."""
        self._emulated_keys[key.lower()] = bool(held)
        self._headless = True

    def emulate_mouse(self, x: float, y: float, buttons: dict | None = None):
        """Inject mouse position and button state."""
        self._emulated_mouse   = (float(x), float(y))
        self._emulated_buttons = buttons or {}
        self._headless = True

    def clear_emulation(self):
        """Clear all emulated input state."""
        self._emulated_keys.clear()
        self._emulated_buttons.clear()
        self._headless = False

    def map(self, action, keys=None, axes=None, gamepad=None, gamepad_axis=None):
        self._actions[action] = {
            "keys": list(keys or []),
            "axes": list(axes or []),
        }

    def _is_key_down(self, key):
        # v2.13.0: headless emulation takes priority over pygame
        if self._headless or self._emulated_keys:
            return self._emulated_keys.get(key.lower(), False)
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
        # v2.13.0: headless emulation
        if self._headless or self._emulated_mouse != (0.0, 0.0):
            x, y = self._emulated_mouse
            return {"x": float(x), "y": float(y)}
        try:
            import pygame; x, y = pygame.mouse.get_pos(); return {"x": float(x), "y": float(y)}
        except Exception:
            return {"x": self._mouse_x, "y": self._mouse_y}

    def mouse_pressed(self, button=0):
        # v2.13.0: headless emulation
        if self._headless or self._emulated_buttons:
            return self._emulated_buttons.get(int(button), False)
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

# ═══════════════════════════════════════════════════════════════════════════
# v2.10.0 — `physics` module
# Unified physics API; wraps physics2d internals and adds ray_cast.
# ═══════════════════════════════════════════════════════════════════════════

def _physics_world(gravity_x=0.0, gravity_y=500.0):
    """Create a 2D physics world.  gravity is a Vec2 or (x,y) pair."""
    return _P2DWorld(float(gravity_x), float(gravity_y))

def _physics_body(mass=1.0, shape=None, tag=""):
    """Create a dynamic RigidBody.  shape defaults to a 32×32 rect."""
    s = shape if shape is not None else _P2DRect(32, 32)
    return _P2DBody(s, float(mass), str(tag))

def _physics_static(shape=None, tag=""):
    """Create a StaticBody (infinite mass)."""
    s = shape if shape is not None else _P2DRect(32, 32)
    b = _P2DBody(s, 0.0, str(tag))
    b.is_static = True
    return b

def _physics_area(shape=None, tag=""):
    """Create an Area (overlap detector, no physics response)."""
    s = shape if shape is not None else _P2DRect(32, 32)
    return _P2DArea(s, str(tag))

def _physics_ray_cast(world, ox, oy, dx, dy, distance=10000.0):
    """
    Cast a ray from (ox, oy) in direction (dx, dy) for up to `distance` units.
    Returns the first body hit and the hit point, or None.

    world    — a _P2DWorld
    ox, oy   — ray origin
    dx, dy   — ray direction (does NOT need to be normalised)
    distance — maximum travel distance

    Returns: {"body": <_P2DBody>, "hit_x": float, "hit_y": float,
              "distance": float, "normal_x": float, "normal_y": float}
    or None if no hit.
    """
    import math
    length = math.hypot(float(dx), float(dy))
    if length == 0:
        return None
    ndx, ndy = float(dx) / length, float(dy) / length
    ox, oy, dist = float(ox), float(oy), float(distance)

    best = None
    best_t = dist

    for body in world._bodies:
        if not body._alive:
            continue
        # AABB slab intersection
        if isinstance(body.shape, (_P2DRect, _P2DCircle)):
            if isinstance(body.shape, _P2DRect):
                hw, hh = body.shape.w / 2, body.shape.h / 2
                x1, y1, x2, y2 = (body.x - hw, body.y - hh,
                                   body.x + hw, body.y + hh)
            else:
                r = body.shape.r
                x1, y1, x2, y2 = (body.x - r, body.y - r,
                                   body.x + r, body.y + r)

            def _slab(origin, direction, lo, hi):
                if abs(direction) < 1e-9:
                    if origin < lo or origin > hi:
                        return float("inf"), float("-inf")
                    return float("-inf"), float("inf")
                t0 = (lo - origin) / direction
                t1 = (hi - origin) / direction
                return (t0, t1) if t0 <= t1 else (t1, t0)

            tx0, tx1 = _slab(ox, ndx, x1, x2)
            ty0, ty1 = _slab(oy, ndy, y1, y2)
            t_enter = max(tx0, ty0)
            t_exit  = min(tx1, ty1)
            if t_enter <= t_exit and t_exit >= 0:
                t_hit = max(t_enter, 0.0)
                if t_hit < best_t:
                    best_t = t_hit
                    # Approximate hit normal from which slab entered
                    nx, ny = 0.0, 0.0
                    if tx0 > ty0:
                        nx = -1.0 if ndx > 0 else 1.0
                    else:
                        ny = -1.0 if ndy > 0 else 1.0
                    best = {
                        "body":     body,
                        "hit_x":    ox + ndx * t_hit,
                        "hit_y":    oy + ndy * t_hit,
                        "distance": t_hit,
                        "normal_x": nx,
                        "normal_y": ny,
                    }

    return best


def _physics_shape_cast(world, shape, ox, oy, dx, dy, distance=10000.0):
    """
    Cast a shape along a ray.  shape is a _P2DRect or _P2DCircle.
    Returns first body hit dict or None.
    """
    import math
    length = math.hypot(float(dx), float(dy))
    if length == 0:
        return None
    ndx, ndy = float(dx) / length, float(dy) / length
    ox, oy, dist = float(ox), float(oy), float(distance)

    if isinstance(shape, _P2DRect):
        shw, shh = shape.w / 2, shape.h / 2
    else:
        sr = shape.r

    def _b_aabb(b):
        if isinstance(b.shape, _P2DRect):
            hw, hh = b.shape.w / 2, b.shape.h / 2
            return (b.x - hw, b.y - hh, b.x + hw, b.y + hh)
        r = b.shape.r
        return (b.x - r, b.y - r, b.x + r, b.y + r)

    best = None
    best_t = dist

    for b in world._bodies:
        if not b._alive or isinstance(b, _P2DArea):
            continue
        bx1, by1, bx2, by2 = _b_aabb(b)
        # Expand target AABB by shape extents to get Minkowski-sum AABB
        if isinstance(shape, _P2DRect):
            ex1, ey1, ex2, ey2 = bx1 - shw, by1 - shh, bx2 + shw, by2 + shh
        else:
            ex1, ey1, ex2, ey2 = bx1 - sr, by1 - sr, bx2 + sr, by2 + sr
        # Ray vs expanded AABB slab test
        def _slab(origin, direction, lo, hi):
            if abs(direction) < 1e-9:
                if origin < lo or origin > hi:
                    return float("inf"), float("-inf")
                return float("-inf"), float("inf")
            t0 = (lo - origin) / direction
            t1 = (hi - origin) / direction
            return (t0, t1) if t0 <= t1 else (t1, t0)
        tx0, tx1 = _slab(ox, ndx, ex1, ex2)
        ty0, ty1 = _slab(oy, ndy, ey1, ey2)
        t_enter = max(tx0, ty0)
        t_exit  = min(tx1, ty1)
        if t_enter <= t_exit and t_exit >= 0:
            t_hit = max(t_enter, 0.0)
            if t_hit < best_t:
                best_t = t_hit
                hx, hy = ox + ndx * t_hit, oy + ndy * t_hit
                # Check actual shape overlap at hit position
                if isinstance(shape, _P2DRect):
                    s1, s2, s3, s4 = hx - shw, hy - shh, hx + shw, hy + shh
                else:
                    s1, s2, s3, s4 = hx - sr, hy - sr, hx + sr, hy + sr
                if s1 <= bx2 and s3 >= bx1 and s2 <= by2 and s4 >= by1:
                    nx = -1.0 if ndx > 0 else 1.0 if ndx < 0 else 0.0
                    ny = -1.0 if ndy > 0 else 1.0 if ndy < 0 else 0.0
                    best = {
                        "body": b, "hit_x": hx, "hit_y": hy,
                        "distance": t_hit, "normal_x": nx, "normal_y": ny,
                    }
    return best


register_module("physics", _wrapmod({
    "world":        _physics_world,
    "body":         _physics_body,
    "static_body":  _physics_static,
    "area":         _physics_area,
    "ray_cast":     _physics_ray_cast,
    "shape_cast":   _physics_shape_cast,
    "Rect":         lambda w, h: _P2DRect(float(w), float(h)),
    "Circle":       lambda r:    _P2DCircle(float(r)),
    "Vec2":         lambda x=0.0, y=0.0: _Vec2(float(x), float(y)),
}, "physics"))


# ═══════════════════════════════════════════════════════════════════════════
# v2.10.0 — `net` module
# WebSocket-first game networking with delta-sync.
# Falls back to UDP (wrapping net_game) if websockets not installed.
# ═══════════════════════════════════════════════════════════════════════════

import json as _json
import threading as _threading
import copy as _copy

def _net_pack(data):
    return _json.dumps(data, separators=(",", ":"))

def _net_unpack(raw):
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    return _json.loads(raw)


class _NetDeltaSync:
    """
    Delta-compressor for net.sync(state_dict).
    Only transmits keys whose values changed since the last sync.
    """
    def __init__(self):
        self._last: dict = {}

    def delta(self, current: dict) -> dict:
        """Return only the changed entries."""
        changed = {}
        for k, v in current.items():
            if self._last.get(k) != v:
                changed[k] = v
        self._last = _copy.deepcopy(current)
        return changed

    def reset(self):
        self._last.clear()


class _NetPeer:
    """Represents a connected peer (server-side)."""
    def __init__(self, peer_id: str, send_fn):
        self.id      = peer_id
        self._send   = send_fn
        self.latency = 0.0
        self._sync   = _NetDeltaSync()

    def send(self, data):
        try:
            self._send(_net_pack(data))
        except Exception:
            pass

    def sync(self, state: dict):
        delta = self._sync.delta(state)
        if delta:
            self.send({"_sync": delta})

    def __repr__(self):
        return f"<NetPeer {self.id}>"


class _NetServer:
    """
    Simple game server.  Tries WebSocket (asyncio + websockets) first;
    falls back to UDP (_GameServer) if websockets not installed.
    """
    def __init__(self, port=7777, max_clients=16):
        self._port         = int(port)
        self._max          = int(max_clients)
        self._peers: dict  = {}   # id → _NetPeer
        self._on_connect_cb    = None
        self._on_disconnect_cb = None
        self._on_message_cb    = None
        self._running          = False
        self._thread           = None
        self._lock             = _threading.Lock()
        self._mode             = "unknown"
        self._udp_server       = None  # fallback

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def serve(self):
        """Start listening.  Non-blocking — spawns a daemon thread."""
        self._running = True
        self._thread  = _threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._running = False
        if self._udp_server:
            try: self._udp_server.stop()
            except Exception: pass

    # ── callbacks ─────────────────────────────────────────────────────────────

    def on_connect(self, fn):    self._on_connect_cb    = fn; return self
    def on_disconnect(self, fn): self._on_disconnect_cb = fn; return self
    def on_message(self, fn):    self._on_message_cb    = fn; return self

    # ── broadcast / sync ──────────────────────────────────────────────────────

    def broadcast(self, data):
        msg = _net_pack(data)
        with self._lock:
            for peer in list(self._peers.values()):
                peer._send(msg)

    def sync(self, state: dict):
        """Broadcast delta-compressed state to all peers."""
        with self._lock:
            for peer in list(self._peers.values()):
                peer.sync(state)

    def player_count(self) -> int:
        return len(self._peers)

    # ── internals ─────────────────────────────────────────────────────────────

    def _run(self):
        try:
            import asyncio, websockets  # noqa: F401
            self._mode = "ws"
            self._run_ws()
        except ImportError:
            self._mode = "udp"
            self._run_udp_fallback()

    def _run_ws(self):
        """WebSocket server loop (requires websockets package)."""
        import asyncio, websockets

        async def _handler(ws):
            pid = f"ws:{id(ws)}"
            def _send_fn(msg):
                asyncio.run_coroutine_threadsafe(ws.send(msg), loop)
            peer = _NetPeer(pid, _send_fn)
            with self._lock:
                if len(self._peers) >= self._max:
                    await ws.close(); return
                self._peers[pid] = peer
            if self._on_connect_cb:
                try: self._on_connect_cb(peer)
                except Exception: pass
            try:
                async for raw in ws:
                    data = _net_unpack(raw)
                    if self._on_message_cb:
                        try: self._on_message_cb(peer, data)
                        except Exception: pass
            except Exception:
                pass
            finally:
                with self._lock:
                    self._peers.pop(pid, None)
                if self._on_disconnect_cb:
                    try: self._on_disconnect_cb(peer)
                    except Exception: pass

        async def _serve():
            async with websockets.serve(_handler, "", self._port):
                while self._running:
                    await asyncio.sleep(0.1)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_serve())
        finally:
            loop.close()

    def _run_udp_fallback(self):
        """UDP fallback when websockets not installed."""
        self._udp_server = _GameServer(self._port, self._max)

        def _on_c(peer):
            np = _NetPeer(peer.id, lambda msg: peer.send(_net_unpack(msg)))
            with self._lock:
                self._peers[peer.id] = np
            if self._on_connect_cb:
                try: self._on_connect_cb(np)
                except Exception: pass

        def _on_d(peer):
            with self._lock:
                self._peers.pop(peer.id, None)
            if self._on_disconnect_cb:
                try: self._on_disconnect_cb(peer)
                except Exception: pass

        def _on_m(peer, data):
            np = self._peers.get(peer.id)
            if np and self._on_message_cb:
                try: self._on_message_cb(np, data)
                except Exception: pass

        self._udp_server.on_connect(_on_c)
        self._udp_server.on_disconnect(_on_d)
        self._udp_server.on_message(_on_m)
        self._udp_server.start()

        import time
        while self._running:
            time.sleep(0.1)

    def __repr__(self):
        return (f"<NetServer port={self._port} "
                f"mode={self._mode} peers={len(self._peers)}>")


class _NetClient:
    """
    Game network client.  Tries WebSocket first; falls back to UDP.
    """
    def __init__(self):
        self._on_message_cb = None
        self._running       = False
        self._thread        = None
        self.connected      = False
        self._url           = None
        self._ws            = None       # ws connection (async)
        self._udp           = None       # UDP fallback
        self._sync          = _NetDeltaSync()
        self._send_fn       = None
        self._loop          = None

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def connect(self, url: str):
        """
        Connect to a server.
        url examples:
          "ws://localhost:7777"
          "udp://localhost:7777"   (forced UDP)
          "localhost:7777"         (auto — tries WS first)
        """
        self._url     = url
        self._running = True
        self._thread  = _threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def disconnect(self):
        self._running  = False
        self.connected = False
        if self._udp:
            try: self._udp.disconnect()
            except Exception: pass

    # ── callbacks ─────────────────────────────────────────────────────────────

    def on_message(self, fn):
        self._on_message_cb = fn; return self

    # ── send / sync ───────────────────────────────────────────────────────────

    def send(self, data):
        if self._send_fn:
            try: self._send_fn(_net_pack(data))
            except Exception: pass

    def sync(self, state: dict):
        """Send only changed entries since last sync."""
        delta = self._sync.delta(state)
        if delta:
            self.send({"_sync": delta})

    # ── internals ─────────────────────────────────────────────────────────────

    def _run(self):
        url = self._url or ""
        if url.startswith("udp://"):
            self._run_udp(url[6:])
            return
        try:
            import websockets  # noqa: F401
            self._run_ws(url if "://" in url else f"ws://{url}")
        except ImportError:
            host_port = url.replace("ws://", "").replace("wss://", "")
            self._run_udp(host_port)

    def _run_ws(self, url: str):
        import asyncio, websockets

        async def _connect():
            try:
                async with websockets.connect(url) as ws:
                    self._ws = ws
                    self.connected = True

                    async def _sender(msg):
                        await ws.send(msg)

                    self._loop    = asyncio.get_event_loop()
                    self._send_fn = lambda msg: asyncio.run_coroutine_threadsafe(
                        _sender(msg), self._loop
                    )
                    async for raw in ws:
                        if not self._running:
                            break
                        data = _net_unpack(raw)
                        if self._on_message_cb:
                            try: self._on_message_cb(data)
                            except Exception: pass
            except Exception:
                self.connected = False

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_connect())
        finally:
            self.connected = False
            loop.close()

    def _run_udp(self, host_port: str):
        parts = host_port.rsplit(":", 1)
        host  = parts[0] if parts else "localhost"
        port  = int(parts[1]) if len(parts) > 1 else 7777
        self._udp = _GameClient()
        self._udp.on_message(lambda d: self._on_message_cb(d) if self._on_message_cb else None)
        self._send_fn = lambda msg: self._udp.send(_net_unpack(msg))
        self._udp.connect(host, port)
        self.connected = True
        import time
        while self._running:
            time.sleep(0.1)
        self.connected = False

    def __repr__(self):
        return f"<NetClient connected={self.connected} url={self._url}>"


def _net_serve(port=7777, max_clients=16):
    return _NetServer(int(port), int(max_clients))

def _net_connect(url="localhost:7777"):
    return _NetClient().connect(str(url))


register_module("net", _wrapmod({
    "serve":       _net_serve,
    "connect":     _net_connect,
    "Server":      _NetServer,
    "Client":      _NetClient,
    "DeltaSync":   _NetDeltaSync,
    "pack":        _net_pack,
    "unpack":      _net_unpack,
}, "net"))
