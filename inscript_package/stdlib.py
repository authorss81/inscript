# inscript/stdlib.py  — Phase 5: Standard Library
#
# Registers all built-in modules that InScript programs can import:
#
#   import "math"         → Math functions beyond the built-ins
#   import "string"       → String utilities
#   import "array"        → Extra array algorithms
#   import "io"           → File I/O (read/write text files)
#   import "json"         → JSON encode/decode
#   import "random"       → Random number generators, noise
#   import "time"         → Timing, FPS measurement
#   import "color"        → Color manipulation helpers
#   import "vec"          → Vector math helpers
#   import "physics2d"    → Simple 2D physics stub (Phase 7 replaces this)
#   import "events"       → Observer/event-bus system
#   import "tween"        → Tweening/easing functions
#   import "grid"         → Grid/tilemap utilities
#   import "debug"        → Debug printing, assertions
#
# Each module is a plain Python dict of {name: callable}.
# The interpreter's module loader calls load_module(name) to retrieve it.

from __future__ import annotations
import math, random, time, json, os
from typing import Any, Dict, Callable

def _call_fn(fn, *args):
    """Call either a Python callable or an InScriptFunction from stdlib."""
    from stdlib_values import InScriptFunction
    if isinstance(fn, InScriptFunction):
        # We need an interpreter instance — use a lightweight one
        from interpreter import Interpreter
        i = Interpreter()
        return i._call_function(fn, list(args), [None]*len(args), 0)
    return fn(*args)

from stdlib_values import Vec2, Vec3, Color, Rect, InScriptInstance


# ─────────────────────────────────────────────────────────────────────────────
# MODULE REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

_MODULES: Dict[str, Dict[str, Any]] = {}

def register_module(name: str, exports: Dict[str, Any]):
    _MODULES[name] = exports

def load_module(name: str) -> Dict[str, Any]:
    if name in _MODULES:
        return _MODULES[name]
    raise ImportError(f"Module '{name}' not found. Available: {list(_MODULES.keys())}")


# ─────────────────────────────────────────────────────────────────────────────
# math  — extended math functions
# ─────────────────────────────────────────────────────────────────────────────

register_module("math", {
    "PI":     math.pi,
    "TAU":    math.tau,
    "E":      math.e,
    "INF":    math.inf,
    "NAN":    math.nan,

    "sin":    math.sin,      "cos":    math.cos,      "tan":    math.tan,
    "asin":   math.asin,     "acos":   math.acos,     "atan":   math.atan,
    "atan2":  math.atan2,    "sinh":   math.sinh,     "cosh":   math.cosh,
    "tanh":   math.tanh,     "sqrt":   math.sqrt,     "cbrt":   lambda x: x**(1/3),
    "exp":    math.exp,      "log":    math.log,      "log2":   math.log2,
    "log10":  math.log10,    "pow":    math.pow,
    "floor":  math.floor,    "ceil":   math.ceil,     "round":  round,
    "abs":    abs,           "sign":   lambda x: (1 if x>0 else -1 if x<0 else 0),
    "clamp":  lambda v,lo,hi: max(lo, min(hi, v)),
    "lerp":   lambda a,b,t: a + (b-a)*t,
    "smoothstep": lambda e0,e1,x: (lambda t: t*t*(3-2*t))((max(0,min(1,(x-e0)/(e1-e0))) if e1!=e0 else 0)),
    "map":    lambda v,a1,b1,a2,b2: a2 + (v-a1)/(b1-a1)*(b2-a2) if b1!=a1 else a2,
    "is_nan": math.isnan,    "is_inf": math.isinf,
    "degrees": math.degrees, "radians": math.radians,
    "min":    min,           "max":    max,
    "gcd":    math.gcd,
    "hypot":  math.hypot,    "dist":   math.dist,
    "factorial": math.factorial,
})


# ─────────────────────────────────────────────────────────────────────────────
# string  — string utilities
# ─────────────────────────────────────────────────────────────────────────────

def _str_format(template: str, *args) -> str:
    """Simple positional format: format("Hello {}", name)"""
    result = template
    for arg in args:
        result = result.replace("{}", str(arg), 1)
    return result

def _str_pad_left(s: str, width: int, char: str = " ") -> str:
    return str(s).rjust(int(width), char)

def _str_pad_right(s: str, width: int, char: str = " ") -> str:
    return str(s).ljust(int(width), char)

def _str_repeat(s: str, n: int) -> str:
    return str(s) * int(n)

register_module("string", {
    "format":     _str_format,
    "pad_left":   _str_pad_left,
    "pad_right":  _str_pad_right,
    "repeat":     _str_repeat,
    "reverse":    lambda s: s[::-1],
    "is_digit":   lambda s: s.isdigit(),
    "is_alpha":   lambda s: s.isalpha(),
    "is_alnum":   lambda s: s.isalnum(),
    "is_space":   lambda s: s.isspace(),
    "is_upper":   lambda s: s.isupper(),
    "is_lower":   lambda s: s.islower(),
    "char_code":  lambda s: ord(s[0]) if s else 0,
    "from_code":  lambda n: chr(int(n)),
    "count":      lambda s, sub: s.count(sub),
    "find":       lambda s, sub: s.find(sub),
    "title":      lambda s: s.title(),
    "upper":      lambda s: s.upper(),
    "lower":      lambda s: s.lower(),
    "trim":       lambda s: s.strip(),
    "split":      lambda s, sep=None: s.split(sep),
    "join":       lambda sep, lst: sep.join(str(x) for x in lst),
    "replace":    lambda s, old, new: s.replace(old, new),
    "starts_with":lambda s, p: s.startswith(p),
    "ends_with":  lambda s, p: s.endswith(p),
    "contains":   lambda s, sub: sub in s,
    "to_int":     lambda s: int(s),
    "to_float":   lambda s: float(s),
    "substring":  lambda s, a, b: s[int(a):int(b)],
})


# ─────────────────────────────────────────────────────────────────────────────
# array  — extra array algorithms
# ─────────────────────────────────────────────────────────────────────────────

def _arr_sort(lst, key_fn=None):
    if key_fn is None:
        return sorted(lst)
    from stdlib_values import InScriptFunction
    return sorted(lst, key=lambda x: key_fn(x) if callable(key_fn) else x)

def _arr_unique(lst):
    seen = []
    for x in lst:
        if x not in seen:
            seen.append(x)
    return seen

def _arr_flatten(lst):
    result = []
    for x in lst:
        if isinstance(x, list):
            result.extend(_arr_flatten(x))
        else:
            result.append(x)
    return result

def _arr_zip(*arrays):
    return [list(row) for row in zip(*arrays)]

def _arr_chunk(lst, size):
    size = int(size)
    return [lst[i:i+size] for i in range(0, len(lst), size)]

def _arr_sum(lst):
    return sum(lst)

def _arr_product(lst):
    p = 1
    for x in lst: p *= x
    return p

def _arr_average(lst):
    return sum(lst) / len(lst) if lst else 0

def _arr_min(lst):
    return min(lst) if lst else None

def _arr_max(lst):
    return max(lst) if lst else None

def _arr_range(start, stop=None, step=1):
    if stop is None: start, stop = 0, start
    return list(range(int(start), int(stop), int(step)))

register_module("array", {
    "sort":     _arr_sort,
    "unique":   _arr_unique,
    "flatten":  _arr_flatten,
    "zip":      _arr_zip,
    "chunk":    _arr_chunk,
    "sum":      _arr_sum,
    "product":  _arr_product,
    "average":  _arr_average,
    "min":      _arr_min,
    "max":      _arr_max,
    "range":    _arr_range,
    "reverse":  lambda lst: lst[::-1],
    # fill(n, val) → new array of n copies of val
    # fill(arr, val) → fill existing array in-place with val, return it
    "fill":     lambda a, b: ([b] * int(a)) if isinstance(a, int) else (a.__setitem__(slice(None), [b]*len(a)) or a),
    "repeat":   lambda lst, n: lst * int(n),
    "count":    lambda lst, val: lst.count(val),
    "index_of": lambda lst, val: lst.index(val) if val in lst else -1,
    "includes": lambda lst, val: val in lst,
    # push/pop as free functions (BUG-18: previously method-only)
    "push":     lambda lst, val: lst.append(val) or lst,
    "pop":      lambda lst: lst.pop() if lst else None,
    "any":      lambda lst, fn: any(_call_fn(fn, x) for x in lst),
    "all":      lambda lst, fn: all(_call_fn(fn, x) for x in lst),
    "none":     lambda lst, fn: not any(_call_fn(fn, x) for x in lst),
    "take":     lambda lst, n: lst[:int(n)],
    "skip":     lambda lst, n: lst[int(n):],
    "last":      lambda lst: lst[-1] if lst else None,
    "first":     lambda lst: lst[0]  if lst else None,
    "shuffle":   lambda arr: (lambda a: (__import__("random").shuffle(a), a)[1])(list(arr)),
    "binary_search": lambda arr, val: next((i for i,x in enumerate(arr) if x==val), -1),
    "zip_with":  lambda a, b, fn: [fn(x,y) for x,y in zip(a,b)],
    "rotate":    lambda arr, n=1: (list(arr)[int(n)%len(arr):]+list(arr)[:int(n)%len(arr)]) if arr else [],
    "frequencies": lambda arr: (lambda d: [d.__setitem__(x,d.get(x,0)+1) for x in arr] and d)({}),
    "flatten_deep": lambda arr: (lambda f,a: [item for x in a for item in (f(f,x) if isinstance(x,list) else [x])])(lambda f,a: [item for x in a for item in (f(f,x) if isinstance(x,list) else [x])], arr),
    "partition": lambda arr, fn: ([x for x in arr if fn(x)],[x for x in arr if not fn(x)]),
    "interleave": lambda a, b: [x for pair in zip(a,b) for x in pair],
})


# ─────────────────────────────────────────────────────────────────────────────
# io  — file I/O
# ─────────────────────────────────────────────────────────────────────────────

def _read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except IOError as e:
        raise Exception(f"io.read_file: {e}")

def _write_file(path: str, content: str) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(content))
    except IOError as e:
        raise Exception(f"io.write_file: {e}")

def _append_file(path: str, content: str) -> None:
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(str(content))
    except IOError as e:
        raise Exception(f"io.append_file: {e}")

def _read_lines(path: str):
    return _read_file(path).splitlines()

register_module("io", {
    "read_file":   _read_file,
    "write_file":  _write_file,
    "append_file": _append_file,
    "read_lines":  _read_lines,
    "exists":      os.path.exists,
    "delete":      os.remove,
    "cwd":         os.getcwd,
    "list_dir":    lambda p=".": os.listdir(p),
    "join_path":   os.path.join,
    "basename":    os.path.basename,
    "dirname":     os.path.dirname,
})


# ─────────────────────────────────────────────────────────────────────────────
# json  — JSON encode/decode
# ─────────────────────────────────────────────────────────────────────────────

def _json_encode(val, indent=None) -> str:
    def to_py(v):
        if isinstance(v, InScriptInstance):
            return {k: to_py(fv) for k, fv in v.fields.items()
                    if not callable(fv)}
        if isinstance(v, (list, tuple)):
            return [to_py(x) for x in v]
        if isinstance(v, dict):
            return {str(k): to_py(dv) for k, dv in v.items()}
        if isinstance(v, Vec2):
            return {"x": v.x, "y": v.y}
        if isinstance(v, Color):
            return {"r": v.r, "g": v.g, "b": v.b, "a": v.a}
        return v
    return json.dumps(to_py(val), indent=indent)

def _json_decode(s: str):
    return json.loads(s)

register_module("json", {
    "encode":    _json_encode,
    "decode":    _json_decode,
    "parse":     _json_decode,
    "stringify": _json_encode,
})


# ─────────────────────────────────────────────────────────────────────────────
# random  — random numbers and procedural noise
# ─────────────────────────────────────────────────────────────────────────────

def _perlin_1d(x: float, seed: int = 0) -> float:
    """Very simple pseudo-Perlin noise in 1D (not real Perlin, but good enough for games)."""
    def fade(t): return t*t*t*(t*(t*6-15)+10)
    def grad(h, x): return x if h & 1 == 0 else -x
    X = int(math.floor(x)) & 255
    x -= math.floor(x)
    u = fade(x)
    rng = random.Random(seed)
    p = list(range(256))
    rng.shuffle(p)
    p = p + p
    a, b = p[X], p[X+1]
    return 1.0 * (u * grad(p[a], x) + (1-u) * grad(p[b], x-1))

register_module("random", {
    # float()         → random float in [0.0, 1.0]
    # float(lo, hi)   → random float in [lo, hi]
    "float":       lambda lo=None, hi=None: (random.random() if lo is None else random.uniform(float(lo), float(hi))),
    "range":       lambda lo, hi: random.uniform(lo, hi),
    "int":         lambda lo, hi: random.randint(int(lo), int(hi)),
    "bool":        lambda p=0.5: random.random() < p,
    "choice":      lambda lst: random.choice(lst) if lst else None,
    "choices":     lambda lst, k=1: random.choices(lst, k=int(k)),
    "shuffle":     lambda lst: (random.shuffle(lst), lst)[1],
    "sample":      lambda lst, k: random.sample(lst, int(k)),
    "seed":        lambda s: random.seed(s),
    "vec2":        lambda mag=1.0: Vec2(random.uniform(-mag, mag), random.uniform(-mag, mag)),
    "direction":   lambda: (lambda a: Vec2(math.cos(a), math.sin(a)))(random.uniform(0, math.tau)),
    "color":       lambda: Color(random.random(), random.random(), random.random()),
    "noise1d":     _perlin_1d,
    "gaussian":    lambda mu=0.0, sigma=1.0: random.gauss(mu, sigma),
    "exponential": lambda lam=1.0: random.expovariate(lam),
})


# ─────────────────────────────────────────────────────────────────────────────
# time  — timing and FPS
# ─────────────────────────────────────────────────────────────────────────────

_time_start = time.time()
_frame_times = []

register_module("time", {
    "now":         time.time,
    "elapsed":     lambda: time.time() - _time_start,
    "sleep":       time.sleep,
    "reset":       lambda: globals().update({"_time_start": time.time()}),
    "fps":         lambda dt: 1.0 / dt if dt > 0 else 0,
})


# ─────────────────────────────────────────────────────────────────────────────
# color  — color manipulation
# ─────────────────────────────────────────────────────────────────────────────

import colorsys

def _hsv(h, s, v, a=1.0):
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return Color(r, g, b, a)

def _hsl(h, s, l, a=1.0):
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return Color(r, g, b, a)

def _mix(a: Color, b: Color, t: float) -> Color:
    return a.lerp(b, t)

def _from_hex(h: str) -> Color:
    return Color.from_hex(h)

def _to_hex(c: Color) -> str:
    return c.to_hex()

def _darken(c: Color, amount: float) -> Color:
    h, s, v = colorsys.rgb_to_hsv(c.r, c.g, c.b)
    return _hsv(h, s, max(0, v - amount), c.a)

def _lighten(c: Color, amount: float) -> Color:
    h, s, v = colorsys.rgb_to_hsv(c.r, c.g, c.b)
    return _hsv(h, s, min(1, v + amount), c.a)

def _saturate(c: Color, amount: float) -> Color:
    h, s, v = colorsys.rgb_to_hsv(c.r, c.g, c.b)
    return _hsv(h, min(1, s + amount), v, c.a)

def _invert(c: Color) -> Color:
    return Color(1-c.r, 1-c.g, 1-c.b, c.a)

def _grayscale(c: Color) -> Color:
    g = 0.299*c.r + 0.587*c.g + 0.114*c.b
    return Color(g, g, g, c.a)

register_module("color", {
    # rgb() uses 0.0–1.0 scale (same as from_hex, mix, darken, lighten)
    "rgb":       lambda r, g, b, a=1.0: Color(float(r), float(g), float(b), float(a)),
    # rgb255() for users who prefer 0-255 integer scale
    "rgb255":    lambda r, g, b, a=255: Color(r/255.0, g/255.0, b/255.0, a/255.0),
    "hsv":       _hsv,
    "hsl":       _hsl,
    "from_hex":  _from_hex,
    "to_hex":    _to_hex,
    "mix":       _mix,
    "lerp":      _mix,
    "darken":    _darken,
    "lighten":   _lighten,
    "saturate":  _saturate,
    "invert":    _invert,
    "grayscale": _grayscale,
    "alpha":     lambda c, a: Color(c.r, c.g, c.b, a),
    # Palette
    "RED":     Color.RED,   "GREEN":  Color.GREEN,  "BLUE":  Color.BLUE,
    "WHITE":   Color.WHITE, "BLACK":  Color.BLACK,  "YELLOW":Color.YELLOW,
    "CYAN":    Color.CYAN,  "MAGENTA":Color.MAGENTA,"ORANGE":Color(1,0.5,0),
    "PURPLE":  Color(0.5,0,1), "PINK": Color(1,0.4,0.7),
    "GRAY":    Color(0.5,0.5,0.5), "DARK_GRAY": Color(0.2,0.2,0.2),
    "TRANSPARENT": Color.TRANSPARENT,
})


# ─────────────────────────────────────────────────────────────────────────────
# tween  — easing and interpolation
# ─────────────────────────────────────────────────────────────────────────────

def _ease_in_quad(t):  return t*t
def _ease_out_quad(t): return t*(2-t)
def _ease_io_quad(t):  return 2*t*t if t<0.5 else -1+(4-2*t)*t
def _ease_in_cubic(t): return t*t*t
def _ease_out_cubic(t):p=t-1; return p*p*p+1
def _ease_io_cubic(t): return 4*t*t*t if t<0.5 else (t-1)*(2*t-2)*(2*t-2)+1
def _ease_in_sine(t):  return 1-math.cos((t*math.pi)/2)
def _ease_out_sine(t): return math.sin((t*math.pi)/2)
def _ease_io_sine(t):  return -(math.cos(math.pi*t)-1)/2
def _ease_in_expo(t):  return 0 if t==0 else 2**(10*t-10)
def _ease_out_expo(t): return 1 if t==1 else 1-2**(-10*t)
def _ease_in_bounce(t):return 1-_ease_out_bounce(1-t)
def _ease_out_bounce(t):
    n1, d1 = 7.5625, 2.75
    if t < 1/d1: return n1*t*t
    if t < 2/d1: t -= 1.5/d1; return n1*t*t+0.75
    if t < 2.5/d1: t -= 2.25/d1; return n1*t*t+0.9375
    t -= 2.625/d1; return n1*t*t+0.984375
def _ease_in_elastic(t):
    c4 = (2*math.pi)/3
    if t==0: return 0
    if t==1: return 1
    return -(2**(10*t-10))*math.sin((t*10-10.75)*c4)
def _ease_out_elastic(t):
    c4 = (2*math.pi)/3
    if t==0: return 0
    if t==1: return 1
    return 2**(-10*t)*math.sin((t*10-0.75)*c4)+1
def _ease_in_back(t):  c1=1.70158; return (c1+1)*t*t*t-c1*t*t
def _ease_out_back(t): c1=1.70158; p=t-1; return 1+(c1+1)*p*p*p+c1*p*p

def _tween(start, end, t, easing_fn):
    """Apply easing function and interpolate between start and end."""
    et = easing_fn(max(0.0, min(1.0, t)))
    if isinstance(start, Vec2):
        return start.lerp(end, et)
    if isinstance(start, Color):
        return start.lerp(end, et)
    return start + (end - start) * et

def _make_easing(raw_fn):
    """Wrap a raw 0-1 easing fn so it works as fn(t) OR fn(t, from_val, to_val)."""
    def wrapped(*args):
        if len(args) == 1:
            return raw_fn(max(0.0, min(1.0, float(args[0]))))
        elif len(args) == 3:
            t, a, b = float(args[0]), args[1], args[2]
            et = raw_fn(max(0.0, min(1.0, t)))
            if isinstance(a, Vec2) and isinstance(b, Vec2): return a.lerp(b, et)
            if isinstance(a, Color) and isinstance(b, Color): return a.lerp(b, et)
            return a + (b - a) * et
        else:
            raise TypeError(f"tween fn expects 1 or 3 args (t) or (t, from, to), got {len(args)}")
    return wrapped

_linear_raw = lambda t: t
register_module("tween", {
    "linear":        _make_easing(_linear_raw),
    "ease_in": _make_easing(_ease_in_quad),
    "ease_out": _make_easing(_ease_out_quad),
    "ease_in_out": _make_easing(_ease_io_quad),
    "ease_in_quad": _make_easing(_ease_in_quad),
    "ease_out_quad": _make_easing(_ease_out_quad),
    "ease_in_cubic": _make_easing(_ease_in_cubic),
    "ease_out_cubic":_ease_out_cubic,
    "ease_io_cubic": _make_easing(_ease_io_cubic),
    "ease_in_sine": _make_easing(_ease_in_sine),
    "ease_out_sine": _make_easing(_ease_out_sine),
    "ease_io_sine": _make_easing(_ease_io_sine),
    "ease_in_expo": _make_easing(_ease_in_expo),
    "ease_out_expo": _make_easing(_ease_out_expo),
    "ease_in_bounce":_ease_in_bounce,
    "ease_out_bounce":_ease_out_bounce,
    "ease_in_elastic":_ease_in_elastic,
    "ease_out_elastic":_ease_out_elastic,
    "ease_in_back": _make_easing(_ease_in_back),
    "ease_out_back": _make_easing(_ease_out_back),
    "tween":         _tween,
})


# ─────────────────────────────────────────────────────────────────────────────
# grid  — 2D grid / tilemap utilities
# ─────────────────────────────────────────────────────────────────────────────

class Grid:
    def __init__(self, cols, rows, default=None):
        self.cols = int(cols)
        self.rows = int(rows)
        self._data = [[default]*self.cols for _ in range(self.rows)]

    def get(self, x, y):
        x, y = int(x), int(y)
        if 0 <= x < self.cols and 0 <= y < self.rows:
            return self._data[y][x]
        return None

    def set(self, x, y, val):
        x, y = int(x), int(y)
        if 0 <= x < self.cols and 0 <= y < self.rows:
            self._data[y][x] = val

    def in_bounds(self, x, y):
        return 0 <= int(x) < self.cols and 0 <= int(y) < self.rows

    def fill(self, val):
        for y in range(self.rows):
            for x in range(self.cols):
                self._data[y][x] = val

    def neighbors_4(self, x, y):
        x, y = int(x), int(y)
        dirs = [(0,-1),(1,0),(0,1),(-1,0)]
        return [[nx, ny] for dx, dy in dirs
                for nx, ny in [(x+dx, y+dy)]
                if self.in_bounds(nx, ny)]

    def neighbors_8(self, x, y):
        x, y = int(x), int(y)
        dirs = [(-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)]
        return [[x+dx, y+dy] for dx, dy in dirs if self.in_bounds(x+dx, y+dy)]

    def to_world(self, x, y, tile_size):
        """Convert grid coords to world-space Vec2."""
        return Vec2(x * tile_size, y * tile_size)

    def to_grid(self, wx, wy, tile_size):
        """Convert world-space position to grid coords."""
        return [int(wx // tile_size), int(wy // tile_size)]

    def __repr__(self):
        return f"Grid({self.cols}x{self.rows})"


register_module("grid", {
    "Grid":        lambda cols, rows, default=None: Grid(cols, rows, default),
    "make":        lambda cols, rows, default=None: Grid(cols, rows, default),
    "to_index":    lambda x, y, cols: int(y)*int(cols) + int(x),
    "from_index":  lambda idx, cols: [int(idx) % int(cols), int(idx) // int(cols)],
    "manhattan":   lambda x1,y1,x2,y2: abs(x1-x2)+abs(y1-y2),
    "chebyshev":   lambda x1,y1,x2,y2: max(abs(x1-x2), abs(y1-y2)),
    "euclidean":   lambda x1,y1,x2,y2: math.sqrt((x1-x2)**2+(y1-y2)**2),
})


# ─────────────────────────────────────────────────────────────────────────────
# events  — observer / event bus
# ─────────────────────────────────────────────────────────────────────────────

def _call_inscript_fn(fn, args):
    """Call either a plain Python callable or an InScriptFunction through the interpreter."""
    from stdlib_values import InScriptFunction
    if isinstance(fn, InScriptFunction):
        raise RuntimeError("No active interpreter to call InScript event callback")
    return fn(*args)

class EventBus:
    def __init__(self):
        self._listeners = {}
        self._interp_ref = None   # set by interpreter on import

    def _set_interp(self, interp):
        self._interp_ref = interp

    def on(self, event: str, fn):
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(fn)

    def off(self, event: str, fn=None):
        if fn is None:
            self._listeners.pop(event, None)
        elif event in self._listeners:
            self._listeners[event] = [f for f in self._listeners[event] if f is not fn]

    def emit(self, event: str, *args):
        from stdlib_values import InScriptFunction
        for fn in list(self._listeners.get(event, [])):
            if isinstance(fn, InScriptFunction) and self._interp_ref is not None:
                self._interp_ref._call_function(fn, list(args), [None]*len(args), 0)
            else:
                fn(*args)

    def once(self, event: str, fn):
        def wrapper(*args):
            self.off(event, wrapper)
            from stdlib_values import InScriptFunction
            if isinstance(fn, InScriptFunction) and self._interp_ref is not None:
                self._interp_ref._call_function(fn, list(args), [None]*len(args), 0)
            else:
                fn(*args)
        self.on(event, wrapper)

    def clear(self):
        self._listeners.clear()


_global_bus = EventBus()

register_module("events", {
    "EventBus":  EventBus,
    "bus":       _global_bus,
    "on":        _global_bus.on,
    "off":       _global_bus.off,
    "emit":      _global_bus.emit,
    "once":      _global_bus.once,
    "clear":     _global_bus.clear,
})


# ─────────────────────────────────────────────────────────────────────────────
# debug  — debugging utilities
# ─────────────────────────────────────────────────────────────────────────────

_assertions_passed = 0
_assertions_failed = 0

def _assert(cond, msg="Assertion failed"):
    global _assertions_passed, _assertions_failed
    if not cond:
        _assertions_failed += 1
        raise Exception(f"[InScript Assert] {msg}")
    _assertions_passed += 1

def _assert_eq(a, b, msg=None):
    m = msg or f"Expected {b!r}, got {a!r}"
    _assert(a == b, m)

def _assert_near(a, b, tol=1e-6, msg=None):
    m = msg or f"Expected {a} ≈ {b} (tol={tol})"
    _assert(abs(a - b) <= tol, m)

register_module("debug", {
    "assert":      _assert,
    "assert_eq":   _assert_eq,
    "assert_near": _assert_near,
    "print_type":  lambda v: print(type(v).__name__),
    "inspect":     lambda v: print(repr(v)),
    "log":         lambda *args: print("[LOG]", *args),
    "warn":        lambda *args: print("[WARN]", *args),
    "error":       lambda *args: print("[ERROR]", *args),
    "trace":       lambda msg="": print(f"[TRACE] {msg}"),
    "stats":       lambda: {"assertions_passed": _assertions_passed,
                             "assertions_failed": _assertions_failed},
})

# ─────────────────────────────────────────────────────────────────────────────
# path  — File-path manipulation
# ─────────────────────────────────────────────────────────────────────────────
import os as _os
import os.path as _osp

register_module("path", {
    "join":       lambda *parts: _osp.join(*[str(p) for p in parts]).replace("\\", "/"),
    "dirname":    lambda p: _osp.dirname(str(p)),
    "basename":   lambda p: _osp.basename(str(p)),
    "stem":       lambda p: _osp.splitext(_osp.basename(str(p)))[0],
    "ext":        lambda p: _osp.splitext(str(p))[1],
    "exists":     lambda p: _osp.exists(str(p)),
    "is_file":    lambda p: _osp.isfile(str(p)),
    "is_dir":     lambda p: _osp.isdir(str(p)),
    "abs":        lambda p: _osp.abspath(str(p)),
    "resolve":    lambda p: _osp.realpath(str(p)),
    "relative":   lambda p, base=".": _osp.relpath(str(p), str(base)),
    "split":      lambda p: list(_osp.split(str(p))),
    "parts":      lambda p: [x for x in _osp.normpath(str(p)).split(_os.sep) if x],
    "home":       lambda: str(_os.path.expanduser("~")),
    "cwd":        lambda: str(_os.getcwd()),
    "mkdir":      lambda p, exist_ok=True: _os.makedirs(str(p), exist_ok=exist_ok) or None,
    "listdir":    lambda p=".": _os.listdir(str(p)),
    "glob":       lambda pattern: __import__("glob").glob(str(pattern)),
    "sep":        _os.sep,
})

# ─────────────────────────────────────────────────────────────────────────────
# regex  — Regular expressions
# ─────────────────────────────────────────────────────────────────────────────
import re as _re

# All regex functions take (text, pattern) — text first, pattern second.
# This matches user expectation: R.match("hello world", "h.*o")

def _re_match(text, pattern, flags=0):
    m = _re.match(str(pattern), str(text), int(flags))
    return {"matched": m is not None, "groups": list(m.groups()) if m else [], "span": list(m.span()) if m else [], "value": m.group(0) if m else None}

def _re_search(text, pattern):
    m = _re.search(str(pattern), str(text))
    return {"matched": m is not None, "groups": list(m.groups()) if m else [], "span": list(m.span()) if m else [], "value": m.group(0) if m else None}

def _re_find_all(text, pattern):
    return _re.findall(str(pattern), str(text))

def _re_sub(text, pattern, replacement, count=0):
    return _re.sub(str(pattern), str(replacement), str(text), count=int(count))

def _re_split(text, pattern):
    return _re.split(str(pattern), str(text))

def _re_escape(text):
    return _re.escape(str(text))

def _re_test(text, pattern):
    return bool(_re.search(str(pattern), str(text)))

register_module("regex", {
    "match":    _re_match,
    "search":   _re_search,
    "find_all": _re_find_all,
    "sub":      _re_sub,
    "replace":  _re_sub,
    "split":    _re_split,
    "escape":   _re_escape,
    "test":     _re_test,
    # Common pattern constants
    "DIGITS":   r"\d+",
    "WORD":     r"\w+",
    "EMAIL":    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    "URL":      r"https?://[^\s]+",
    "WHITESPACE": r"\s+",
})

# ─────────────────────────────────────────────────────────────────────────────
# csv  — CSV parsing and writing
# ─────────────────────────────────────────────────────────────────────────────
import csv as _csv
import io as _io

def _csv_parse(text, delimiter=",", has_header=True):
    reader = _csv.reader(_io.StringIO(str(text)), delimiter=str(delimiter))
    rows = [row for row in reader]
    if not rows:
        return {"headers": [], "rows": [], "data": []}
    if has_header:
        headers = rows[0]
        data = [dict(zip(headers, row)) for row in rows[1:]]
        return {"headers": headers, "rows": rows[1:], "data": data}
    return {"headers": [], "rows": rows, "data": rows}

def _csv_parse_file(path, delimiter=",", has_header=True):
    try:
        with open(str(path), encoding="utf-8") as f:
            return _csv_parse(f.read(), delimiter, has_header)
    except FileNotFoundError:
        raise Exception(f"CSV file not found: {path}")

def _csv_to_string(rows, headers=None, delimiter=","):
    buf = _io.StringIO()
    writer = _csv.writer(buf, delimiter=str(delimiter))
    if headers:
        writer.writerow(headers)
    for row in rows:
        if isinstance(row, dict):
            writer.writerow(list(row.values()))
        else:
            writer.writerow(row)
    return buf.getvalue()

def _csv_write_file(path, rows, headers=None, delimiter=","):
    with open(str(path), "w", encoding="utf-8", newline="") as f:
        writer = _csv.writer(f, delimiter=str(delimiter))
        if headers:
            writer.writerow(headers)
        for row in rows:
            writer.writerow(list(row.values()) if isinstance(row, dict) else row)

register_module("csv", {
    "parse":      _csv_parse,
    "parse_file": _csv_parse_file,
    "to_string":  _csv_to_string,
    "write_file": _csv_write_file,
    "from_dicts": lambda dicts, delimiter=",": _csv_to_string(dicts, list(dicts[0].keys()) if dicts else [], delimiter),
})

# ─────────────────────────────────────────────────────────────────────────────
# uuid  — UUID generation
# ─────────────────────────────────────────────────────────────────────────────
import uuid as _uuid

register_module("uuid", {
    "v4":       lambda: str(_uuid.uuid4()),
    "v1":       lambda: str(_uuid.uuid1()),
    "nil":      "00000000-0000-0000-0000-000000000000",
    "is_valid": lambda s: (lambda: True if _uuid.UUID(str(s)) else False)() if _try_uuid(str(s)) else False,
    "parse":    lambda s: str(_uuid.UUID(str(s))),
    "short":    lambda: str(_uuid.uuid4()).split("-")[0],  # 8-char prefix, not guaranteed unique
})

def _try_uuid(s):
    try: _uuid.UUID(s); return True
    except: return False

# ─────────────────────────────────────────────────────────────────────────────
# crypto  — Hashing and encoding
# ─────────────────────────────────────────────────────────────────────────────
import hashlib as _hashlib
import hmac as _hmac
import base64 as _b64

def _hash(text, algorithm="sha256"):
    algo = str(algorithm).lower()
    if algo not in ("md5","sha1","sha256","sha512","sha224","sha384"):
        raise Exception(f"Unsupported hash algorithm: {algorithm}")
    h = _hashlib.new(algo, str(text).encode())
    return h.hexdigest()

def _hmac_sign(key, message, algorithm="sha256"):
    k = str(key).encode()
    m = str(message).encode()
    algo = getattr(_hashlib, str(algorithm).lower(), _hashlib.sha256)
    return _hmac.new(k, m, algo).hexdigest()

def _hmac_verify(key, message, signature, algorithm="sha256"):
    expected = _hmac_sign(key, message, algorithm)
    return _hmac.compare_digest(expected, str(signature))

register_module("crypto", {
    "hash":         _hash,
    "md5":          lambda s: _hash(s, "md5"),
    "sha1":         lambda s: _hash(s, "sha1"),
    "sha256":       lambda s: _hash(s, "sha256"),
    "sha512":       lambda s: _hash(s, "sha512"),
    "hmac_sign":    _hmac_sign,
    "hmac_verify":  _hmac_verify,
    "b64_encode":   lambda s: _b64.b64encode(str(s).encode()).decode(),
    "b64_decode":   lambda s: _b64.b64decode(str(s).encode()).decode(),
    "url_encode":   lambda s: _b64.urlsafe_b64encode(str(s).encode()).decode(),
    "url_decode":   lambda s: _b64.urlsafe_b64decode(str(s).encode()).decode(),
    "random_bytes": lambda n=16: _hashlib.sha256(__import__("os").urandom(int(n))).hexdigest()[:int(n)*2],
    "constant_time_eq": lambda a, b: _hmac.compare_digest(str(a), str(b)),
})

# Also register http module if not already there
try:
    _MODULES["http"]
except KeyError:
    import urllib.request as _urlreq, json as _json_http

    def _http_get(url, headers=None):
        req = _urlreq.Request(str(url), headers=headers or {})
        try:
            with _urlreq.urlopen(req, timeout=10) as r:
                body = r.read().decode()
                return {"status": r.status, "body": body, "ok": r.status < 400}
        except Exception as e:
            return {"status": 0, "body": str(e), "ok": False}

    def _http_post(url, body=None, headers=None):
        h = {"Content-Type": "application/json", **(headers or {})}
        data = (_json_http.dumps(body) if not isinstance(body, str) else body).encode()
        req = _urlreq.Request(str(url), data=data, headers=h, method="POST")
        try:
            with _urlreq.urlopen(req, timeout=10) as r:
                resp_body = r.read().decode()
                return {"status": r.status, "body": resp_body, "ok": r.status < 400}
        except Exception as e:
            return {"status": 0, "body": str(e), "ok": False}

    register_module("http", {
        "get":  _http_get,
        "post": _http_post,
    })

# ── Extended stdlib (Part 1): collections, datetime, fs, process, log, test, compress
try:
    import stdlib_extended  # noqa: F401
except Exception as _e:
    import sys; print(f'[stdlib_extended load error] {_e}', file=sys.stderr)

# ── Extended stdlib (Part 2): iter, format, url, xml, toml, yaml, argparse, hash, base64, database, bench, template, net, thread
try:
    import stdlib_extended_2  # noqa: F401
except Exception as _e2:
    import sys; print(f'[stdlib_extended_2 load error] {_e2}', file=sys.stderr)

# ── Game stdlib (Phase 4 remainder + Phase 5): ssl, image, atlas, animation,
#    physics2d, tilemap, camera2d, particle, pathfind, ecs, input, fsm,
#    save, localize, net_game, shader, audio
try:
    import stdlib_game  # noqa: F401
except Exception as _e3:
    import sys; print(f'[stdlib_game load error] {_e3}', file=sys.stderr)
