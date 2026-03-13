# inscript/stdlib_values.py
# Runtime representations of InScript's built-in game types.
# These are plain Python objects the interpreter works with at runtime.

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional


# ─── Vec2 ──────────────────────────────────────────────────────────────────

class Vec2:
    __slots__ = ("x", "y")
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x); self.y = float(y)

    def __add__(self, o):
        if isinstance(o, Vec2): return Vec2(self.x+o.x, self.y+o.y)
        return Vec2(self.x+o, self.y+o)
    def __radd__(self, o): return self.__add__(o)
    def __sub__(self, o):
        if isinstance(o, Vec2): return Vec2(self.x-o.x, self.y-o.y)
        return Vec2(self.x-o, self.y-o)
    def __rsub__(self, o): return Vec2(o-self.x, o-self.y)
    def __mul__(self, o):
        if isinstance(o, Vec2): return Vec2(self.x*o.x, self.y*o.y)
        return Vec2(self.x*o, self.y*o)
    def __rmul__(self, o): return self.__mul__(o)
    def __truediv__(self, o):
        if isinstance(o, Vec2): return Vec2(self.x/o.x, self.y/o.y)
        return Vec2(self.x/o, self.y/o)
    def __neg__(self): return Vec2(-self.x, -self.y)
    def __eq__(self, o): return isinstance(o, Vec2) and self.x==o.x and self.y==o.y
    def __repr__(self): return f"Vec2({self.x}, {self.y})"

    def length(self): return math.sqrt(self.x**2 + self.y**2)
    def length_squared(self): return self.x**2 + self.y**2
    def normalized(self):
        l = self.length()
        return Vec2(self.x/l, self.y/l) if l != 0 else Vec2(0, 0)
    def dot(self, o): return self.x*o.x + self.y*o.y
    def cross(self, o): return self.x*o.y - self.y*o.x
    def angle(self): return math.atan2(self.y, self.x)
    def lerp(self, o, t): return Vec2(self.x+(o.x-self.x)*t, self.y+(o.y-self.y)*t)
    def distance_to(self, o): return (self-o).length()
    def reflect(self, normal):
        d = 2 * self.dot(normal)
        return Vec2(self.x - d*normal.x, self.y - d*normal.y)
    def rotated(self, angle):
        c, s = math.cos(angle), math.sin(angle)
        return Vec2(self.x*c - self.y*s, self.x*s + self.y*c)
    def abs(self): return Vec2(abs(self.x), abs(self.y))
    def get_attr(self, name):
        if name == "x": return self.x
        if name == "y": return self.y
        # Properties (no parens needed)
        if name == "length_value": return self.length()
        if name == "angle_value":  return self.angle()
        # Methods (return callables)
        if name == "length":     return self.length
        if name == "normalized": return self.normalized
        if name == "normalize":  return self.normalized
        if name == "dot":        return self.dot
        if name == "cross":      return self.cross
        if name == "lerp":       return self.lerp
        if name == "distance_to":return self.distance_to
        if name == "reflect":    return self.reflect
        if name == "rotated":    return self.rotated
        if name == "abs":        return self.abs
        raise AttributeError(f"Vec2 has no attribute '{name}'")
    def set_attr(self, name, val):
        if name == "x": self.x = float(val)
        elif name == "y": self.y = float(val)
        else: raise AttributeError(f"Vec2 has no settable attribute '{name}'")

    ZERO    = None  # set below
    ONE     = None
    UP      = None
    DOWN    = None
    LEFT    = None
    RIGHT   = None

Vec2.ZERO  = Vec2(0, 0)
Vec2.ONE   = Vec2(1, 1)
Vec2.UP    = Vec2(0, -1)
Vec2.DOWN  = Vec2(0, 1)
Vec2.LEFT  = Vec2(-1, 0)
Vec2.RIGHT = Vec2(1, 0)


# ─── Vec3 ──────────────────────────────────────────────────────────────────

class Vec3:
    __slots__ = ("x","y","z")
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x=float(x); self.y=float(y); self.z=float(z)

    def __add__(self, o):
        if isinstance(o, Vec3): return Vec3(self.x+o.x, self.y+o.y, self.z+o.z)
        return Vec3(self.x+o, self.y+o, self.z+o)
    def __sub__(self, o):
        if isinstance(o, Vec3): return Vec3(self.x-o.x, self.y-o.y, self.z-o.z)
        return Vec3(self.x-o, self.y-o, self.z-o)
    def __mul__(self, o):
        if isinstance(o, Vec3): return Vec3(self.x*o.x, self.y*o.y, self.z*o.z)
        return Vec3(self.x*o, self.y*o, self.z*o)
    def __rmul__(self, o): return self.__mul__(o)
    def __truediv__(self, o):
        if isinstance(o, Vec3): return Vec3(self.x/o.x, self.y/o.y, self.z/o.z)
        return Vec3(self.x/o, self.y/o, self.z/o)
    def __neg__(self): return Vec3(-self.x, -self.y, -self.z)
    def __eq__(self, o): return isinstance(o,Vec3) and self.x==o.x and self.y==o.y and self.z==o.z
    def __repr__(self): return f"Vec3({self.x}, {self.y}, {self.z})"

    def length(self): return math.sqrt(self.x**2+self.y**2+self.z**2)
    def normalized(self):
        l=self.length()
        return Vec3(self.x/l,self.y/l,self.z/l) if l!=0 else Vec3()
    def dot(self,o): return self.x*o.x+self.y*o.y+self.z*o.z
    def cross(self,o): return Vec3(self.y*o.z-self.z*o.y, self.z*o.x-self.x*o.z, self.x*o.y-self.y*o.x)
    def lerp(self,o,t): return Vec3(self.x+(o.x-self.x)*t, self.y+(o.y-self.y)*t, self.z+(o.z-self.z)*t)
    def distance_to(self,o): return (self-o).length()
    def get_attr(self, name):
        if name in ("x","y","z"): return getattr(self, name)
        if name == "length":     return self.length
        if name == "normalized": return self.normalized
        if name == "normalize":  return self.normalized
        if name == "dot":        return self.dot
        if name == "cross":      return self.cross
        if name == "lerp":       return self.lerp
        if name == "distance_to":return self.distance_to
        raise AttributeError(f"Vec3 has no attribute '{name}'")
    def set_attr(self, name, val):
        if name in ("x","y","z"): setattr(self, name, float(val))
        else: raise AttributeError(f"Vec3 has no settable attribute '{name}'")

    ZERO = None; ONE = None; UP = None; FORWARD = None; RIGHT = None
Vec3.ZERO    = Vec3(0,0,0)
Vec3.ONE     = Vec3(1,1,1)
Vec3.UP      = Vec3(0,1,0)
Vec3.FORWARD = Vec3(0,0,-1)
Vec3.RIGHT   = Vec3(1,0,0)


# ─── Color ──────────────────────────────────────────────────────────────────

class Color:
    __slots__ = ("r","g","b","a")
    def __init__(self, r=1.0, g=1.0, b=1.0, a=1.0):
        self.r=float(r); self.g=float(g)
        self.b=float(b); self.a=float(a)

    def __repr__(self): return f"Color({self.r}, {self.g}, {self.b}, {self.a})"
    def __eq__(self, o): return isinstance(o,Color) and (self.r,self.g,self.b,self.a)==(o.r,o.g,o.b,o.a)

    def lerp(self, o, t):
        return Color(self.r+(o.r-self.r)*t, self.g+(o.g-self.g)*t,
                     self.b+(o.b-self.b)*t, self.a+(o.a-self.a)*t)
    def to_hex(self):
        return "#{:02x}{:02x}{:02x}".format(
            int(self.r*255), int(self.g*255), int(self.b*255))
    def to_rgba_int(self):
        return (int(self.r*255), int(self.g*255), int(self.b*255), int(self.a*255))

    @staticmethod
    def from_hex(h):
        h = h.lstrip("#")
        r,g,b = int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255
        return Color(r,g,b)
    @staticmethod
    def from_hsv(h, s, v):
        import colorsys
        r,g,b = colorsys.hsv_to_rgb(h,s,v)
        return Color(r,g,b)

    def get_attr(self, name):
        if name in ("r","g","b","a"): return getattr(self, name)
        raise AttributeError(f"Color has no attribute '{name}'")
    def set_attr(self, name, val):
        if name in ("r","g","b","a"): setattr(self, name, float(val))

    RED     = None; GREEN  = None; BLUE   = None; WHITE  = None
    BLACK   = None; YELLOW = None; CYAN   = None; MAGENTA= None
    TRANSPARENT = None
Color.RED       = Color(1,0,0)
Color.GREEN     = Color(0,1,0)
Color.BLUE      = Color(0,0,1)
Color.WHITE     = Color(1,1,1)
Color.BLACK     = Color(0,0,0)
Color.YELLOW    = Color(1,1,0)
Color.CYAN      = Color(0,1,1)
Color.MAGENTA   = Color(1,0,1)
Color.TRANSPARENT = Color(0,0,0,0)


# ─── Rect ───────────────────────────────────────────────────────────────────

class Rect:
    __slots__ = ("x","y","w","h")
    def __init__(self, x=0.0, y=0.0, w=0.0, h=0.0):
        self.x=float(x); self.y=float(y); self.w=float(w); self.h=float(h)
    def __repr__(self): return f"Rect({self.x}, {self.y}, {self.w}, {self.h})"

    def contains(self, px, py): return self.x<=px<=self.x+self.w and self.y<=py<=self.y+self.h
    def intersects(self, o):
        return not (o.x > self.x+self.w or o.x+o.w < self.x or
                    o.y > self.y+self.h or o.y+o.h < self.y)
    def center(self): return Vec2(self.x+self.w/2, self.y+self.h/2)
    def expand(self, amount): return Rect(self.x-amount,self.y-amount,self.w+2*amount,self.h+2*amount)
    def get_attr(self, name):
        if name in ("x","y","w","h"): return getattr(self, name)
        if name == "center": return self.center()
        raise AttributeError(f"Rect has no attribute '{name}'")
    def set_attr(self, name, val):
        if name in ("x","y","w","h"): setattr(self, name, float(val))


# ─── InScript callable / struct instance ───────────────────────────────────

class InScriptFunction:
    """A user-defined function or lambda at runtime."""
    def __init__(self, name, params, body, closure, is_native=False, native_fn=None, return_type=None):
        self.name        = name
        self.params      = params       # List[Param]  AST nodes
        self.body        = body         # BlockStmt AST node
        self.closure     = closure      # Environment (captured scope)
        self.is_native   = is_native
        self.native_fn   = native_fn    # Python callable for native fns
        self.return_type = return_type  # Optional type annotation
        self._interp     = None         # Set by interpreter so stdlib can call us

    def __repr__(self): return f"<fn {self.name}>"

    def __call__(self, *args):
        """Allow InScriptFunction to be called from Python (e.g. stdlib iter/map/filter)."""
        if self._interp is not None:
            return self._interp._call_function(self, list(args), [None]*len(args), 0)
        raise TypeError(f"InScriptFunction '{self.name}' cannot be called without an interpreter context")


class InScriptInstance:
    """An instance of a user-defined struct at runtime."""
    def __init__(self, struct_name: str, fields: Dict[str, Any]):
        self.struct_name = struct_name
        self.fields      = fields     # {field_name: value}

    def get(self, name: str):
        return self.fields.get(name)

    def set(self, name: str, val: Any):
        self.fields[name] = val

    def __repr__(self):
        pairs = ", ".join(f"{k}={v!r}" for k,v in list(self.fields.items())[:4])
        return f"{self.struct_name}{{ {pairs} }}"


class InScriptRange:
    """Runtime representation of range(n), range(a,b), range(a,b,step), or 0..10"""
    def __init__(self, start, end, step=1, inclusive=False):
        self.start     = int(start)
        self.end       = int(end)
        self.step      = int(step) if step else 1
        self.inclusive = inclusive

    def __iter__(self):
        stop = self.end + 1 if self.inclusive else self.end
        return iter(range(self.start, stop, self.step))

    def __len__(self):
        stop = self.end + 1 if self.inclusive else self.end
        return max(0, (stop - self.start + self.step - 1) // self.step)

    def __repr__(self):
        op = "..=" if self.inclusive else ".."
        return f"{self.start}{op}{self.end}"


class InScriptGenerator:
    """Runtime representation of a generator (fn* function) in InScript.
    Wraps a Python generator so the InScript runtime can iterate it."""

    def __init__(self, name: str, python_gen):
        self.name       = name
        self._gen       = python_gen
        self._done      = False
        self._current   = None

    def __iter__(self):
        return self._gen

    def __repr__(self):
        return f"<generator {self.name}>"

    def next(self):
        """Advance the generator and return the next yielded value, or None if done."""
        try:
            self._current = next(self._gen)
            return self._current
        except StopIteration:
            self._done = True
            return None
