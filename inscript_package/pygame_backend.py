"""
pygame_backend.py — Phase 2: Complete pygame rendering backend for InScript
=============================================================================
Namespaces exposed to InScript: screen, draw, input, audio, font, math2d,
                                 Color, clock

Usage:
    python inscript.py --game examples/pong.ins
    python inscript.py --game examples/pong.ins --width 1280 --height 720

Or directly:
    python pygame_backend.py examples/pong.ins
    python pygame_backend.py              # runs built-in Pong demo

Install pygame first:  pip install pygame
"""

import sys, os, math

try:
    import pygame
    import pygame.freetype
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

# Bootstrap: find inscript_package on the path
_here = os.path.dirname(os.path.abspath(__file__))
for _c in [_here,
           os.path.join(_here, "inscript_package"),
           os.path.join(os.path.dirname(_here), "inscript_package")]:
    if os.path.isdir(_c) and os.path.exists(os.path.join(_c, "interpreter.py")):
        sys.path.insert(0, _c)
        break


# ─────────────────────────────────────────────────────────────────────────────
# Colour helper
# ─────────────────────────────────────────────────────────────────────────────
def _color(c):
    """Convert InScript color value → pygame.Color."""
    if c is None:
        return pygame.Color(255, 255, 255)
    if isinstance(c, dict):
        r = max(0, min(255, int(c.get("r", 0) * 255)))
        g = max(0, min(255, int(c.get("g", 0) * 255)))
        b = max(0, min(255, int(c.get("b", 0) * 255)))
        a = max(0, min(255, int(c.get("a", 1.0) * 255)))
        return pygame.Color(r, g, b, a)
    if isinstance(c, (list, tuple)):
        if len(c) >= 4:
            return pygame.Color(int(c[0]), int(c[1]), int(c[2]), int(c[3]))
        if len(c) >= 3:
            return pygame.Color(int(c[0]), int(c[1]), int(c[2]))
    if isinstance(c, str):
        try:
            return pygame.Color(c)
        except Exception:
            return pygame.Color(255, 255, 255)
    return pygame.Color(255, 255, 255)


# ─────────────────────────────────────────────────────────────────────────────
# Mixin: expose namespace methods as both ns.foo() and ns["foo"]()
# ─────────────────────────────────────────────────────────────────────────────
class _NS:
    def __getitem__(self, k):
        return getattr(self, k, None)
    def __call__(self, *a, **kw):
        pass  # swallow accidental ns() calls


# ─────────────────────────────────────────────────────────────────────────────
# ScreenNamespace
# ─────────────────────────────────────────────────────────────────────────────
class ScreenNamespace(_NS):
    def __init__(self, surface, pg_clock):
        self._surf   = surface
        self._clock  = pg_clock
        self._bg     = pygame.Color(20, 20, 30)

    @property
    def width(self):    return self._surf.get_width()
    @property
    def height(self):   return self._surf.get_height()
    @property
    def fps(self):      return round(self._clock.get_fps(), 1)
    @property
    def center_x(self): return self._surf.get_width() // 2
    @property
    def center_y(self): return self._surf.get_height() // 2

    def clear(self, color=None):
        self._surf.fill(_color(color) if color is not None else self._bg)

    def set_title(self, title):        pygame.display.set_caption(str(title))
    def set_background(self, color):   self._bg = _color(color)
    def flip(self):                    pygame.display.flip()
    def screenshot(self, path="screenshot.png"):
        pygame.image.save(self._surf, str(path)); return str(path)

    def fade(self, alpha):
        """Overlay a semi-transparent black — useful for fade-in/out."""
        ov = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        ov.fill((0, 0, 0, max(0, min(255, int(alpha)))))
        self._surf.blit(ov, (0, 0))


# ─────────────────────────────────────────────────────────────────────────────
# DrawNamespace
# ─────────────────────────────────────────────────────────────────────────────
class DrawNamespace(_NS):
    def __init__(self, surface):
        self._surf        = surface
        self._font_cache  = {}       # size (int) → freetype.Font
        self._file_fonts  = {}       # (path, size) → freetype.Font
        self._image_cache = {}       # path → Surface
        pygame.freetype.init()

    # ── font helpers ─────────────────────────────────────────────────────────
    def _sfont(self, size):
        size = max(6, int(size))
        if size not in self._font_cache:
            self._font_cache[size] = pygame.freetype.SysFont("monospace", size)
        return self._font_cache[size]

    def _get_font(self, size, path=None):
        if path:
            k = (str(path), int(size))
            if k not in self._file_fonts:
                try:    self._file_fonts[k] = pygame.freetype.Font(str(path), int(size))
                except: self._file_fonts[k] = self._sfont(size)
            return self._file_fonts[k]
        return self._sfont(size)

    # ── image cache ───────────────────────────────────────────────────────────
    def _img(self, path):
        path = str(path)
        if path not in self._image_cache:
            try:    surf = pygame.image.load(path).convert_alpha()
            except Exception as e:
                surf = pygame.Surface((32, 32), pygame.SRCALPHA)
                surf.fill((255, 0, 255, 200))
                print(f"[draw] Cannot load '{path}': {e}", file=sys.stderr)
            self._image_cache[path] = surf
        return self._image_cache[path]

    # ── primitives ────────────────────────────────────────────────────────────
    def rect(self, x, y, w, h, color, filled=True, thickness=1):
        c = _color(color)
        r = pygame.Rect(int(x), int(y), max(1, int(w)), max(1, int(h)))
        if filled: pygame.draw.rect(self._surf, c, r)
        else:      pygame.draw.rect(self._surf, c, r, max(1, int(thickness)))

    def rect_outline(self, x, y, w, h, color, thickness=1):
        self.rect(x, y, w, h, color, filled=False, thickness=thickness)

    def rounded_rect(self, x, y, w, h, color, radius=8, filled=True):
        c = _color(color)
        r = pygame.Rect(int(x), int(y), max(1, int(w)), max(1, int(h)))
        rad = min(int(radius), int(w)//2, int(h)//2)
        if filled: pygame.draw.rect(self._surf, c, r, border_radius=rad)
        else:      pygame.draw.rect(self._surf, c, r, 1, border_radius=rad)

    def circle(self, x, y, radius, color, filled=True, thickness=1):
        c = _color(color); rad = max(1, int(radius))
        if filled: pygame.draw.circle(self._surf, c, (int(x), int(y)), rad)
        else:      pygame.draw.circle(self._surf, c, (int(x), int(y)), rad, max(1, int(thickness)))

    def line(self, x1, y1, x2, y2, color, thickness=1):
        pygame.draw.line(self._surf, _color(color),
                         (int(x1), int(y1)), (int(x2), int(y2)), max(1, int(thickness)))

    def lines(self, points, color, closed=False, thickness=1):
        pts = [(int(p[0]), int(p[1])) for p in points]
        if len(pts) >= 2:
            pygame.draw.lines(self._surf, _color(color), bool(closed), pts, max(1, int(thickness)))

    def polygon(self, points, color, filled=True):
        pts = [(int(p[0]), int(p[1])) for p in points]
        if len(pts) >= 3:
            if filled: pygame.draw.polygon(self._surf, _color(color), pts)
            else:      pygame.draw.polygon(self._surf, _color(color), pts, 1)

    def ellipse(self, x, y, w, h, color, filled=True):
        c = _color(color); r = pygame.Rect(int(x), int(y), max(1, int(w)), max(1, int(h)))
        if filled: pygame.draw.ellipse(self._surf, c, r)
        else:      pygame.draw.ellipse(self._surf, c, r, 1)

    def arc(self, x, y, w, h, start_deg, end_deg, color, thickness=2):
        r  = pygame.Rect(int(x), int(y), max(1, int(w)), max(1, int(h)))
        pygame.draw.arc(self._surf, _color(color), r,
                        math.radians(float(start_deg)), math.radians(float(end_deg)),
                        max(1, int(thickness)))

    def pixel(self, x, y, color):
        self._surf.set_at((int(x), int(y)), _color(color))

    # ── text ──────────────────────────────────────────────────────────────────
    def text(self, x, y, text, color=None, size=16, bold=False, font_path=None):
        c = _color(color) if color is not None else pygame.Color(255, 255, 255)
        f = self._get_font(int(size), font_path); f.strong = bool(bold)
        f.render_to(self._surf, (int(x), int(y)), str(text), c)

    def text_centered(self, cx, cy, text, color=None, size=16, bold=False, font_path=None):
        c = _color(color) if color is not None else pygame.Color(255, 255, 255)
        f = self._get_font(int(size), font_path); f.strong = bool(bold)
        r, _ = f.get_rect(str(text))
        f.render_to(self._surf, (int(cx - r.width//2), int(cy - r.height//2)), str(text), c)

    def text_size(self, text, size=16, font_path=None):
        f = self._get_font(int(size), font_path)
        r, _ = f.get_rect(str(text)); return [r.width, r.height]

    # ── sprites ───────────────────────────────────────────────────────────────
    def sprite(self, x, y, path, alpha=255):
        """Draw image at (x,y). Loaded and cached on first call."""
        img = self._img(path)
        if int(alpha) != 255:
            img = img.copy(); img.set_alpha(max(0, min(255, int(alpha))))
        self._surf.blit(img, (int(x), int(y)))

    def sprite_ex(self, x, y, path, angle=0.0, scale=1.0,
                  flip_x=False, flip_y=False, alpha=255):
        """Sprite with rotation (degrees CW), scale, and flip. Pivots on centre."""
        img = self._img(path)
        if flip_x or flip_y:
            img = pygame.transform.flip(img, bool(flip_x), bool(flip_y))
        s = float(scale)
        if abs(s - 1.0) > 0.001:
            nw = max(1, int(img.get_width() * s))
            nh = max(1, int(img.get_height() * s))
            img = pygame.transform.smoothscale(img, (nw, nh))
        a = float(angle)
        if abs(a) > 0.001:
            img = pygame.transform.rotate(img, -a)   # pygame is CCW
        if int(alpha) != 255:
            img = img.copy(); img.set_alpha(max(0, min(255, int(alpha))))
        iw, ih = img.get_size()
        self._surf.blit(img, (int(x) - iw//2, int(y) - ih//2))

    def sprite_size(self, path):
        """Return [w, h] of image without drawing."""
        img = self._img(path); return [img.get_width(), img.get_height()]


# ─────────────────────────────────────────────────────────────────────────────
# InputNamespace
# ─────────────────────────────────────────────────────────────────────────────
class InputNamespace(_NS):
    _KEY_MAP = {}  # filled in _build_keymap() after pygame.init()

    @staticmethod
    def _build_keymap():
        return {
            "up": pygame.K_UP, "down": pygame.K_DOWN,
            "left": pygame.K_LEFT, "right": pygame.K_RIGHT,
            "space": pygame.K_SPACE, "enter": pygame.K_RETURN,
            "return": pygame.K_RETURN, "escape": pygame.K_ESCAPE,
            "backspace": pygame.K_BACKSPACE, "tab": pygame.K_TAB,
            "delete": pygame.K_DELETE, "home": pygame.K_HOME,
            "end": pygame.K_END, "pageup": pygame.K_PAGEUP,
            "pagedown": pygame.K_PAGEDOWN,
            "w": pygame.K_w, "a": pygame.K_a, "s": pygame.K_s, "d": pygame.K_d,
            "q": pygame.K_q, "e": pygame.K_e, "r": pygame.K_r, "f": pygame.K_f,
            "g": pygame.K_g, "h": pygame.K_h, "i": pygame.K_i, "j": pygame.K_j,
            "k": pygame.K_k, "l": pygame.K_l, "m": pygame.K_m, "n": pygame.K_n,
            "o": pygame.K_o, "p": pygame.K_p, "t": pygame.K_t, "u": pygame.K_u,
            "v": pygame.K_v, "x": pygame.K_x, "y": pygame.K_y, "z": pygame.K_z,
            "0": pygame.K_0, "1": pygame.K_1, "2": pygame.K_2,
            "3": pygame.K_3, "4": pygame.K_4, "5": pygame.K_5,
            "6": pygame.K_6, "7": pygame.K_7, "8": pygame.K_8, "9": pygame.K_9,
            "lshift": pygame.K_LSHIFT, "rshift": pygame.K_RSHIFT,
            "shift": pygame.K_LSHIFT,
            "lctrl": pygame.K_LCTRL,  "rctrl": pygame.K_RCTRL,
            "ctrl": pygame.K_LCTRL,
            "lalt": pygame.K_LALT,    "ralt": pygame.K_RALT,
            "alt": pygame.K_LALT,
            "f1": pygame.K_F1,  "f2": pygame.K_F2,  "f3": pygame.K_F3,
            "f4": pygame.K_F4,  "f5": pygame.K_F5,  "f6": pygame.K_F6,
            "f7": pygame.K_F7,  "f8": pygame.K_F8,  "f9": pygame.K_F9,
            "f10": pygame.K_F10,"f11": pygame.K_F11, "f12": pygame.K_F12,
        }

    def __init__(self):
        self._held     = set()
        self._pressed  = set()
        self._released = set()
        self._mbtn     = {}   # btn_int → bool (held)
        self._mpressed = {}   # btn_int → bool (just clicked this frame)
        self._mreleased= {}
        InputNamespace._KEY_MAP = self._build_keymap()

    def _update(self, events):
        self._pressed.clear(); self._released.clear()
        self._mpressed.clear(); self._mreleased.clear()
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                self._held.add(ev.key); self._pressed.add(ev.key)
            elif ev.type == pygame.KEYUP:
                self._held.discard(ev.key); self._released.add(ev.key)
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                self._mbtn[ev.button-1] = True; self._mpressed[ev.button-1] = True
            elif ev.type == pygame.MOUSEBUTTONUP:
                self._mbtn[ev.button-1] = False; self._mreleased[ev.button-1] = True

    def _key(self, name):
        k = self._KEY_MAP.get(str(name).lower())
        if k is None and len(name) == 1: k = ord(name.lower())
        return k

    def key_down(self, name):     k = self._key(name); return k in self._held     if k else False
    def key_pressed(self, name):  k = self._key(name); return k in self._pressed   if k else False
    def key_released(self, name): k = self._key(name); return k in self._released  if k else False
    def any_key(self):            return len(self._held) > 0
    def any_key_pressed(self):    return len(self._pressed) > 0

    @property
    def mouse_x(self):   return pygame.mouse.get_pos()[0]
    @property
    def mouse_y(self):   return pygame.mouse.get_pos()[1]
    @property
    def mouse_pos(self): return list(pygame.mouse.get_pos())

    def mouse_down(self, btn=0):     return self._mbtn.get(int(btn), False)
    def mouse_pressed(self, btn=0):  return self._mpressed.get(int(btn), False)
    def mouse_released(self, btn=0): return self._mreleased.get(int(btn), False)


# ─────────────────────────────────────────────────────────────────────────────
# AudioNamespace
# ─────────────────────────────────────────────────────────────────────────────
class AudioNamespace(_NS):
    def __init__(self):
        self._sounds = {}   # path → pygame.mixer.Sound
        self._chans  = {}   # path → Channel
        self._mvol   = 1.0
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._ok = True
        except Exception:
            self._ok = False

    def _snd(self, path):
        if not self._ok: return None
        path = str(path)
        if path not in self._sounds:
            try:    self._sounds[path] = pygame.mixer.Sound(path)
            except Exception as e:
                print(f"[audio] Cannot load '{path}': {e}", file=sys.stderr); return None
        return self._sounds[path]

    def play(self, path, loop=False, volume=1.0):
        snd = self._snd(path)
        if snd:
            snd.set_volume(float(volume) * self._mvol)
            self._chans[str(path)] = snd.play(-1 if loop else 0)

    def stop(self, path=None):
        if path is None: pygame.mixer.stop()
        else:
            ch = self._chans.get(str(path))
            if ch: ch.stop()

    def set_volume(self, vol, path=None):
        vol = max(0.0, min(1.0, float(vol)))
        if path is None:
            self._mvol = vol; pygame.mixer.music.set_volume(vol)
        else:
            snd = self._snd(path)
            if snd: snd.set_volume(vol * self._mvol)

    def play_music(self, path, loop=True, volume=1.0):
        if not self._ok: return
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(float(volume) * self._mvol)
            pygame.mixer.music.play(-1 if loop else 0)
        except Exception as e:
            print(f"[audio] Cannot load music '{path}': {e}", file=sys.stderr)

    def stop_music(self):    pygame.mixer.music.stop()
    def pause_music(self):   pygame.mixer.music.pause()
    def resume_music(self):  pygame.mixer.music.unpause()
    def music_volume(self, v): pygame.mixer.music.set_volume(max(0.0, min(1.0, float(v))))
    def is_music_playing(self): return pygame.mixer.music.get_busy()

    def preload(self, *paths):
        for p in paths: self._snd(p)


# ─────────────────────────────────────────────────────────────────────────────
# FontNamespace
# ─────────────────────────────────────────────────────────────────────────────
class FontNamespace(_NS):
    """font.load(path, size) → handle   font.render(handle, x, y, text, color)"""
    def __init__(self, draw: DrawNamespace):
        self._draw = draw

    def load(self, path, size=16):
        """Load TTF from disk. Returns an opaque handle for font.render()."""
        k = (str(path), int(size))
        if k not in self._draw._file_fonts:
            try:    self._draw._file_fonts[k] = pygame.freetype.Font(str(path), int(size))
            except Exception as e:
                print(f"[font] Cannot load '{path}': {e}", file=sys.stderr)
                self._draw._file_fonts[k] = self._draw._sfont(int(size))
        return k

    def sys(self, name="monospace", size=16):
        k = (f"__sys__{name}", int(size))
        if k not in self._draw._file_fonts:
            self._draw._file_fonts[k] = pygame.freetype.SysFont(str(name), int(size))
        return k

    def render(self, handle, x, y, text, color=None, bold=False):
        c = _color(color) if color is not None else pygame.Color(255, 255, 255)
        f = self._draw._file_fonts.get(handle) or self._draw._sfont(16)
        f.strong = bool(bold)
        f.render_to(self._draw._surf, (int(x), int(y)), str(text), c)

    def measure(self, handle, text):
        f = self._draw._file_fonts.get(handle) or self._draw._sfont(16)
        r, _ = f.get_rect(str(text)); return [r.width, r.height]


# ─────────────────────────────────────────────────────────────────────────────
# Math2DNamespace
# ─────────────────────────────────────────────────────────────────────────────
class Math2DNamespace(_NS):
    def lerp(self, a, b, t):
        return float(a) + (float(b)-float(a)) * max(0.0, min(1.0, float(t)))

    def lerp_unclamped(self, a, b, t):
        return float(a) + (float(b)-float(a)) * float(t)

    def clamp(self, v, lo, hi):
        return max(float(lo), min(float(hi), float(v)))

    def clamp_int(self, v, lo, hi):
        return max(int(lo), min(int(hi), int(v)))

    def distance(self, x1, y1, x2, y2):
        dx = float(x2)-float(x1); dy = float(y2)-float(y1)
        return math.sqrt(dx*dx + dy*dy)

    def distance_sq(self, x1, y1, x2, y2):
        dx = float(x2)-float(x1); dy = float(y2)-float(y1)
        return dx*dx + dy*dy

    def angle_between(self, x1, y1, x2, y2):
        return math.degrees(math.atan2(float(y2)-float(y1), float(x2)-float(x1)))

    def angle_to_vec(self, deg):
        r = math.radians(float(deg)); return [math.cos(r), math.sin(r)]

    def normalize(self, x, y):
        m = math.sqrt(float(x)**2 + float(y)**2)
        return [0.0, 0.0] if m < 1e-10 else [float(x)/m, float(y)/m]

    def magnitude(self, x, y):
        return math.sqrt(float(x)**2 + float(y)**2)

    def dot(self, x1, y1, x2, y2):
        return float(x1)*float(x2) + float(y1)*float(y2)

    def map_range(self, v, in_lo, in_hi, out_lo, out_hi):
        span = float(in_hi)-float(in_lo)
        if abs(span) < 1e-10: return float(out_lo)
        return float(out_lo) + (float(v)-float(in_lo))/span * (float(out_hi)-float(out_lo))

    def sign(self, v):
        v = float(v)
        return 1.0 if v > 0 else (-1.0 if v < 0 else 0.0)

    def approach(self, cur, tgt, step):
        d = float(tgt)-float(cur); s = float(step)
        return float(tgt) if abs(d) <= s else float(cur) + s*(1.0 if d>0 else -1.0)

    def smoothstep(self, e0, e1, x):
        t = self.clamp((float(x)-float(e0))/(float(e1)-float(e0)), 0.0, 1.0)
        return t*t*(3.0-2.0*t)

    def rect_overlap(self, ax, ay, aw, ah, bx, by, bw, bh):
        return (float(ax) < float(bx)+float(bw) and
                float(ax)+float(aw) > float(bx) and
                float(ay) < float(by)+float(bh) and
                float(ay)+float(ah) > float(by))

    def circle_overlap(self, ax, ay, ar, bx, by, br):
        dx = float(ax)-float(bx); dy = float(ay)-float(by)
        r  = float(ar)+float(br)
        return dx*dx + dy*dy <= r*r

    def vec2(self, x, y):           return [float(x), float(y)]
    def vec2_add(self, a, b):       return [float(a[0])+float(b[0]), float(a[1])+float(b[1])]
    def vec2_sub(self, a, b):       return [float(a[0])-float(b[0]), float(a[1])-float(b[1])]
    def vec2_scale(self, v, s):     return [float(v[0])*float(s), float(v[1])*float(s)]


# ─────────────────────────────────────────────────────────────────────────────
# GameClock  (exposed as `clock`)
# ─────────────────────────────────────────────────────────────────────────────
class GameClock(_NS):
    def __init__(self, fps=60):
        self._fps    = int(fps)
        self._dt     = 0.0
        self._elap   = 0.0
        self._frames = 0

    def _tick(self, dt):
        self._dt = dt; self._elap += dt; self._frames += 1

    @property
    def dt(self):           return self._dt
    @property
    def elapsed(self):      return self._elap
    @property
    def frame_count(self):  return self._frames
    @property
    def fps_target(self):   return self._fps

    def every(self, seconds):
        n = max(1, int(float(seconds) * self._fps))
        return self._frames % n == 0

    def sin_wave(self, period=1.0, amplitude=1.0, offset=0.0):
        return math.sin(self._elap / float(period) * 2*math.pi + float(offset)) * float(amplitude)


# ─────────────────────────────────────────────────────────────────────────────
# ColorHelper
# ─────────────────────────────────────────────────────────────────────────────
class ColorHelper(_NS):
    def rgb(self, r, g, b, a=255):
        return {"r": int(r)/255, "g": int(g)/255, "b": int(b)/255, "a": int(a)/255}

    def rgba(self, r, g, b, a):
        return {"r": int(r)/255, "g": int(g)/255, "b": int(b)/255, "a": int(a)/255}

    def hsv(self, h, s, v, a=1.0):
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(float(h)/360.0, float(s), float(v))
        return {"r": r, "g": g, "b": b, "a": float(a)}

    def hex(self, hex_str):
        h = str(hex_str).lstrip("#")
        return {"r": int(h[0:2],16)/255, "g": int(h[2:4],16)/255,
                "b": int(h[4:6],16)/255, "a": 1.0}

    def lerp(self, a, b, t):
        t = max(0.0, min(1.0, float(t)))
        return {k: a[k] + (b[k]-a[k])*t for k in ("r","g","b","a")
                if k in a and k in b}

    def with_alpha(self, c, alpha):
        return {**c, "a": max(0.0, min(1.0, float(alpha)))}

    @property
    def WHITE(self):      return {"r":1.0, "g":1.0, "b":1.0, "a":1.0}
    @property
    def BLACK(self):      return {"r":0.0, "g":0.0, "b":0.0, "a":1.0}
    @property
    def RED(self):        return {"r":1.0, "g":0.0, "b":0.0, "a":1.0}
    @property
    def GREEN(self):      return {"r":0.0, "g":1.0, "b":0.0, "a":1.0}
    @property
    def BLUE(self):       return {"r":0.0, "g":0.0, "b":1.0, "a":1.0}
    @property
    def YELLOW(self):     return {"r":1.0, "g":1.0, "b":0.0, "a":1.0}
    @property
    def CYAN(self):       return {"r":0.0, "g":1.0, "b":1.0, "a":1.0}
    @property
    def MAGENTA(self):    return {"r":1.0, "g":0.0, "b":1.0, "a":1.0}
    @property
    def ORANGE(self):     return {"r":1.0, "g":0.5, "b":0.0, "a":1.0}
    @property
    def GRAY(self):       return {"r":0.5, "g":0.5, "b":0.5, "a":1.0}
    @property
    def DARK_GRAY(self):  return {"r":0.2, "g":0.2, "b":0.2, "a":1.0}
    @property
    def LIGHT_GRAY(self): return {"r":0.8, "g":0.8, "b":0.8, "a":1.0}
    @property
    def PURPLE(self):     return {"r":0.6, "g":0.0, "b":0.8, "a":1.0}
    @property
    def PINK(self):       return {"r":1.0, "g":0.4, "b":0.7, "a":1.0}
    @property
    def BROWN(self):      return {"r":0.55,"g":0.27,"b":0.07,"a":1.0}
    @property
    def LIME(self):       return {"r":0.5, "g":1.0, "b":0.0, "a":1.0}
    @property
    def TEAL(self):       return {"r":0.0, "g":0.5, "b":0.5, "a":1.0}
    @property
    def NAVY(self):       return {"r":0.0, "g":0.0, "b":0.5, "a":1.0}
    @property
    def TRANSPARENT(self):return {"r":0.0, "g":0.0, "b":0.0, "a":0.0}
    @property
    def SKY(self):        return {"r":0.53,"g":0.81,"b":0.98,"a":1.0}
    @property
    def GOLD(self):       return {"r":1.0, "g":0.84,"b":0.0, "a":1.0}


# ─────────────────────────────────────────────────────────────────────────────
# run_scene — main entry point
# ─────────────────────────────────────────────────────────────────────────────
def run_scene(ins_file: str, width=800, height=600, fps=60, title=None):
    """
    Load an InScript .ins file containing a `scene` declaration and run it
    in a real-time pygame window at the requested FPS.

    Called by:  inscript.py --game examples/pong.ins
    """
    if not HAS_PYGAME:
        print("ERROR: pygame is not installed.\nInstall: pip install pygame",
              file=sys.stderr); sys.exit(1)

    from interpreter import Interpreter
    from lexer import Lexer
    from parser import Parser
    from ast_nodes import SceneDecl

    with open(str(ins_file), "r", encoding="utf-8") as f:
        source = f.read()

    # ── pygame init ───────────────────────────────────────────────────────
    pygame.init()
    surface  = pygame.display.set_mode((int(width), int(height)))
    pg_clock = pygame.time.Clock()
    pygame.display.set_caption(title or os.path.basename(str(ins_file)))

    # ── namespaces ────────────────────────────────────────────────────────
    screen_ns = ScreenNamespace(surface, pg_clock)
    draw_ns   = DrawNamespace(surface)
    input_ns  = InputNamespace()
    audio_ns  = AudioNamespace()
    font_ns   = FontNamespace(draw_ns)
    math2d_ns = Math2DNamespace()
    color_ns  = ColorHelper()
    game_clk  = GameClock(fps)

    # ── interpreter ───────────────────────────────────────────────────────
    interp = Interpreter(source.splitlines())
    env    = interp._env

    # Bind namespaces
    env.define("screen", screen_ns)
    env.define("draw",   draw_ns)
    env.define("input",  input_ns)
    env.define("audio",  audio_ns)
    env.define("font",   font_ns)
    env.define("math2d", math2d_ns)
    env.define("Color",  color_ns)
    env.define("clock",  game_clk)

    # Convenience colour constants at top level
    for _n in ["WHITE","BLACK","RED","GREEN","BLUE","YELLOW","CYAN","MAGENTA",
               "ORANGE","GRAY","DARK_GRAY","LIGHT_GRAY","PURPLE","PINK",
               "TEAL","NAVY","LIME","BROWN","SKY","GOLD","TRANSPARENT"]:
        env.define(_n, getattr(color_ns, _n))

    # ── parse ─────────────────────────────────────────────────────────────
    tokens = Lexer(source).tokenize()
    prog   = Parser(tokens, source).parse()

    # ── Intercept SceneDecl: run vars + methods, leave scope alive ────────
    #    Without this patch, visit_SceneDecl would pop the scene scope at
    #    the end of interp.run(), destroying all scene-level variables before
    #    the game loop starts.
    scene_ref = [None]

    def _game_mode_scene(node):
        scene_ref[0] = node
        interp._push("scene:" + node.name)
        for var in node.vars:    interp.visit(var)
        for meth in node.methods: interp.visit(meth)
        # intentionally NOT running hooks or popping the scope

    interp.visit_SceneDecl = _game_mode_scene
    interp.run(prog)

    scene_node = scene_ref[0]
    if scene_node is None:
        print(f"[pygame_backend] No scene found in '{ins_file}' — running as plain script.")
        pygame.quit(); return

    # ── hook runner ───────────────────────────────────────────────────────
    def run_hook(hook_type, *args):
        for hook in scene_node.hooks:
            if hook.hook_type == hook_type:
                interp._push(hook_type)
                try:
                    for i, param in enumerate(hook.params):
                        if i < len(args): env.define(param.name, args[i])
                    interp.visit(hook.body)
                except Exception:
                    pass
                finally:
                    interp._pop()
                return

    # ── on_start ──────────────────────────────────────────────────────────
    run_hook("on_start")

    # ── game loop ─────────────────────────────────────────────────────────
    running = True
    while running:
        events = pygame.event.get()
        for ev in events:
            if ev.type == pygame.QUIT:                       running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:                running = False

        if not running: break

        input_ns._update(events)
        raw_dt = pg_clock.tick(int(fps)) / 1000.0
        dt     = min(raw_dt, 0.05)          # cap at 50 ms
        game_clk._tick(dt)

        # Sync surface references in case display was updated
        screen_ns._surf = pygame.display.get_surface()
        draw_ns._surf   = screen_ns._surf

        run_hook("on_update", dt)
        run_hook("on_draw")
        pygame.display.flip()

    # ── on_exit ───────────────────────────────────────────────────────────
    run_hook("on_exit")
    pygame.quit()


# ─────────────────────────────────────────────────────────────────────────────
# Direct CLI
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse as _ap
    p = _ap.ArgumentParser(description="InScript pygame backend")
    p.add_argument("file", nargs="?")
    p.add_argument("--width",  type=int, default=800)
    p.add_argument("--height", type=int, default=600)
    p.add_argument("--fps",    type=int, default=60)
    p.add_argument("--title",  default=None)
    a = p.parse_args()

    if not HAS_PYGAME:
        print("pygame not installed.  pip install pygame"); sys.exit(1)

    if a.file:
        run_scene(a.file, a.width, a.height, a.fps, a.title)
    else:
        _ex = os.path.join(os.path.dirname(__file__), "..", "examples", "pong.ins")
        if os.path.exists(_ex):
            run_scene(_ex, 800, 600, 60, "Pong — InScript")
        else:
            print("Usage: python pygame_backend.py game.ins")
