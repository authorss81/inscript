# -*- coding: utf-8 -*-
# stdlib_gui.py  — GUI system for InScript (Phase 11, v3.9.6.30)
#
# Widget types: Button, Label, Panel, Image
# Usage from .ins:
#   import "gui" as gui
#   let btn = gui.Button(100, 100, 200, 50, "Click", 18)
#   btn.on_click(fn(w) { print("clicked") })
#
# Each widget is a plain Python object. Rendering requires a
# DrawNamespace (game mode). Hit-testing (contains()) works standalone.

from typing import Any, Callable, List, Optional

_INSCRIPT_CALLBACKS = False
try:
    from stdlib_values import InScriptFunction
    _INSCRIPT_CALLBACKS = True
except Exception:
    pass


def _is_inscript_fn(fn):
    if not _INSCRIPT_CALLBACKS:
        return False
    return isinstance(fn, __import__("stdlib_values", fromlist=["InScriptFunction"]).InScriptFunction)


def _call_user_fn(fn, arg):
    if fn is None:
        return
    if _is_inscript_fn(fn):
        from interpreter import Interpreter
        i = Interpreter()
        try:
            i._call_function(fn, [arg], [None], 0)
        except Exception:
            pass
    elif callable(fn):
        try:
            fn(arg)
        except Exception:
            pass


def _to_pg_color(color) -> tuple:
    if isinstance(color, dict):
        return (
            int(color.get("r", 0) * 255),
            int(color.get("g", 0) * 255),
            int(color.get("b", 0) * 255),
            int(color.get("a", 1.0) * 255),
        )
    if isinstance(color, (list, tuple)) and len(color) >= 3:
        return tuple(int(c * 255) if isinstance(c, float) else c for c in color[:4])
    return color


def _color_dict(r, g, b, a=1.0):
    return {"r": r, "g": g, "b": b, "a": a}


SIZE_FIXED = 0
SIZE_FILL = 1


class _Widget:
    def __init__(self, x: float, y: float, w: float, h: float):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.visible = True
        self.size_policy_w = SIZE_FILL
        self.size_policy_h = SIZE_FILL
        self._z = 0

    def contains(self, px: float, py: float) -> bool:
        return self.visible and (self.x <= px <= self.x + self.w and
                                 self.y <= py <= self.y + self.h)

    def set_attr(self, name: str, val):
        if name == "x": self.x = val
        elif name == "y": self.y = val
        elif name == "w": self.w = val
        elif name == "h": self.h = val
        elif name == "visible": self.visible = bool(val)
        elif name == "size_policy_w": self.size_policy_w = int(val)
        elif name == "size_policy_h": self.size_policy_h = int(val)
        else:
            raise AttributeError(f"_Widget has no settable attribute '{name}'")

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False

    def toggle_visible(self):
        self.visible = not self.visible

    def update(self, input_ns=None):
        raise NotImplementedError

    def draw(self, draw_ns):
        raise NotImplementedError


class Button(_Widget):
    def __init__(self, x: float, y: float, w: float, h: float,
                 text: str = "", font_size: int = 16):
        super().__init__(x, y, w, h)
        self.text = text
        self.font_size = font_size
        self.bg_color = _color_dict(0.3, 0.3, 0.35)
        self.text_color = _color_dict(1.0, 1.0, 1.0)
        self.hover_color = _color_dict(0.4, 0.4, 0.5)
        self.pressed_color = _color_dict(0.2, 0.2, 0.25)
        self.hovered = False
        self.pressed = False
        self._on_click = None
        self._on_hover = None

    def on_click(self, fn):
        self._on_click = fn

    def on_hover(self, fn):
        self._on_hover = fn

    def update(self, input_ns=None):
        if not self.visible or input_ns is None:
            return
        mx = getattr(input_ns, "mouse_x", 0)
        my = getattr(input_ns, "mouse_y", 0)
        was_hovered = self.hovered
        self.hovered = self.contains(mx, my)
        if self.hovered and not was_hovered and self._on_hover:
            _call_user_fn(self._on_hover, self)
        if not self.hovered and was_hovered and self._on_hover:
            _call_user_fn(self._on_hover, None)
        if self.hovered:
            mp = getattr(input_ns, "mouse_pressed", None)
            if mp is not None and mp(0):
                self.pressed = True
                if self._on_click:
                    _call_user_fn(self._on_click, self)
            else:
                self.pressed = False

    def draw(self, draw_ns):
        if not self.visible:
            return
        color = self.pressed_color if self.pressed else (
            self.hover_color if self.hovered else self.bg_color)
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        if hasattr(draw_ns, "rounded_rect"):
            draw_ns.rounded_rect(self.x, self.y, self.w, self.h, color, 6, True)
        elif hasattr(draw_ns, "rect"):
            draw_ns.rect(self.x, self.y, self.w, self.h, color, True)
        if self.text and hasattr(draw_ns, "text_centered"):
            draw_ns.text_centered(cx, cy, self.text, self.text_color, self.font_size)
        elif self.text and hasattr(draw_ns, "text"):
            draw_ns.text(cx - len(self.text) * 4, cy - self.font_size / 2,
                         self.text, self.text_color, self.font_size)


class Label(_Widget):
    def __init__(self, x: float, y: float, text: str = "", font_size: int = 16):
        super().__init__(x, y, 0, 0)
        self.text = text
        self.font_size = font_size
        self.color = _color_dict(1.0, 1.0, 1.0)
        self.bg_color = None

    def draw(self, draw_ns):
        if not self.visible:
            return
        if self.bg_color and hasattr(draw_ns, "rect"):
            tw = len(self.text) * self.font_size * 0.6 if self.text else 0
            draw_ns.rect(self.x - 2, self.y - 2, tw + 4, self.font_size + 4,
                         self.bg_color, True)
        if self.text and hasattr(draw_ns, "text"):
            draw_ns.text(self.x, self.y, self.text, self.color, self.font_size)
        elif self.text and hasattr(draw_ns, "text_centered"):
            draw_ns.text_centered(self.x, self.y, self.text, self.color, self.font_size)

    def update(self, input_ns=None):
        pass


class Panel(_Widget):
    def __init__(self, x: float, y: float, w: float, h: float):
        super().__init__(x, y, w, h)
        self.children: List[_Widget] = []
        self.bg_color = None
        self.border_color = None
        self.border_width = 0

    def add(self, widget):
        if widget not in self.children:
            self.children.append(widget)

    def remove(self, widget):
        if widget in self.children:
            self.children.remove(widget)

    def clear(self):
        self.children.clear()

    def update(self, input_ns=None):
        if not self.visible:
            return
        for child in self.children:
            child.update(input_ns)

    def draw(self, draw_ns):
        if not self.visible:
            return
        if self.bg_color and hasattr(draw_ns, "rect"):
            draw_ns.rect(self.x, self.y, self.w, self.h, self.bg_color, True)
        if self.border_color and self.border_width > 0 and hasattr(draw_ns, "rect"):
            draw_ns.rect(self.x, self.y, self.w, self.h, self.border_color,
                         False, self.border_width)
        for child in sorted(self.children, key=lambda c: c._z):
            child.draw(draw_ns)

    def get_widget(self, name: str):
        for child in self.children:
            if hasattr(child, "name") and child.name == name:
                return child
        return None


class Image(_Widget):
    def __init__(self, x: float, y: float, path: str = ""):
        super().__init__(x, y, 0, 0)
        self.path = path
        self.alpha = 255
        self.scale = 1.0
        self.angle = 0.0

    def draw(self, draw_ns):
        if not self.visible or not self.path:
            return
        sp = getattr(draw_ns, "sprite", None)
        sp_ex = getattr(draw_ns, "sprite_ex", None)
        if sp_ex is not None:
            sp_ex(self.x, self.y, self.path, self.angle, self.scale,
                  False, False, self.alpha)
        elif sp is not None:
            sp(self.x, self.y, self.path, self.alpha)

    def update(self, input_ns=None):
        pass


# ─────────────────────────────────────────────────────────────────────────────
# HBox — Horizontal Box Layout
# ─────────────────────────────────────────────────────────────────────────────

class HBox(Panel):
    def __init__(self, x: float = 0, y: float = 0, w: float = 400, h: float = 50,
                 spacing: float = 4, padding: float = 4):
        super().__init__(x, y, w, h)
        self.spacing = spacing
        self.padding = padding
        self._needs_layout = True

    def add(self, widget):
        super().add(widget)
        self._needs_layout = True

    def remove(self, widget):
        super().remove(widget)
        self._needs_layout = True

    def clear(self):
        super().clear()
        self._needs_layout = True

    def set_attr(self, name: str, val):
        if name == "spacing": self.spacing = val; self._needs_layout = True
        elif name == "padding": self.padding = val; self._needs_layout = True
        else: super().set_attr(name, val)

    def _do_layout(self):
        cx = self.x + self.padding
        cy = self.y + self.padding
        cw = max(0, self.w - 2 * self.padding)
        ch = max(0, self.h - 2 * self.padding)
        visible = [c for c in self.children if c.visible]
        if not visible:
            self._needs_layout = False
            return
        fill_count = 0
        fixed_total = 0
        for c in visible:
            sp = getattr(c, 'size_policy_w', SIZE_FILL)
            if sp == SIZE_FILL:
                fill_count += 1
            else:
                fixed_total += max(0, c.w)
        avail = max(0, cw - fixed_total - self.spacing * max(0, len(visible) - 1))
        fill_w = avail / max(fill_count, 1) if fill_count > 0 else 0
        for c in visible:
            c.x = cx
            c.y = cy
            sp = getattr(c, 'size_policy_w', SIZE_FILL)
            if sp == SIZE_FILL:
                c.w = fill_w
            c.h = ch
            c._z = self._z + 1
            cx = cx + c.w + self.spacing
        self._needs_layout = False

    def draw(self, draw_ns):
        if self._needs_layout:
            self._do_layout()
        super().draw(draw_ns)

    def update(self, input_ns=None):
        if self._needs_layout:
            self._do_layout()
        super().update(input_ns)


# ─────────────────────────────────────────────────────────────────────────────
# VBox — Vertical Box Layout
# ─────────────────────────────────────────────────────────────────────────────

class VBox(Panel):
    def __init__(self, x: float = 0, y: float = 0, w: float = 200, h: float = 400,
                 spacing: float = 4, padding: float = 4):
        super().__init__(x, y, w, h)
        self.spacing = spacing
        self.padding = padding
        self._needs_layout = True

    def add(self, widget):
        super().add(widget)
        self._needs_layout = True

    def remove(self, widget):
        super().remove(widget)
        self._needs_layout = True

    def clear(self):
        super().clear()
        self._needs_layout = True

    def set_attr(self, name: str, val):
        if name == "spacing": self.spacing = val; self._needs_layout = True
        elif name == "padding": self.padding = val; self._needs_layout = True
        else: super().set_attr(name, val)

    def _do_layout(self):
        cx = self.x + self.padding
        cy = self.y + self.padding
        cw = max(0, self.w - 2 * self.padding)
        ch = max(0, self.h - 2 * self.padding)
        visible = [c for c in self.children if c.visible]
        if not visible:
            self._needs_layout = False
            return
        fill_count = 0
        fixed_total = 0
        for c in visible:
            sp = getattr(c, 'size_policy_h', SIZE_FILL)
            if sp == SIZE_FILL:
                fill_count += 1
            else:
                fixed_total += max(0, c.h)
        avail = max(0, ch - fixed_total - self.spacing * max(0, len(visible) - 1))
        fill_h = avail / max(fill_count, 1) if fill_count > 0 else 0
        for c in visible:
            c.x = cx
            c.y = cy
            c.w = cw
            sp = getattr(c, 'size_policy_h', SIZE_FILL)
            if sp == SIZE_FILL:
                c.h = fill_h
            c._z = self._z + 1
            cy = cy + c.h + self.spacing
        self._needs_layout = False

    def draw(self, draw_ns):
        if self._needs_layout:
            self._do_layout()
        super().draw(draw_ns)

    def update(self, input_ns=None):
        if self._needs_layout:
            self._do_layout()
        super().update(input_ns)


# ─────────────────────────────────────────────────────────────────────────────
# Grid — Row/Column Grid Layout
# ─────────────────────────────────────────────────────────────────────────────

class Grid(Panel):
    def __init__(self, x: float = 0, y: float = 0, w: float = 400, h: float = 400,
                 cols: int = 2, spacing: float = 4, padding: float = 4):
        super().__init__(x, y, w, h)
        self.cols = max(1, cols)
        self.spacing = spacing
        self.padding = padding
        self._needs_layout = True

    def add(self, widget):
        super().add(widget)
        self._needs_layout = True

    def remove(self, widget):
        super().remove(widget)
        self._needs_layout = True

    def clear(self):
        super().clear()
        self._needs_layout = True

    def set_attr(self, name: str, val):
        if name == "cols": self.cols = max(1, int(val)); self._needs_layout = True
        elif name == "spacing": self.spacing = val; self._needs_layout = True
        elif name == "padding": self.padding = val; self._needs_layout = True
        else: super().set_attr(name, val)

    def _do_layout(self):
        cx = self.x + self.padding
        cy = self.y + self.padding
        cw = max(0, self.w - 2 * self.padding)
        ch = max(0, self.h - 2 * self.padding)
        visible = [c for c in self.children if c.visible]
        if not visible:
            self._needs_layout = False
            return
        col_w = max(0, (cw - self.spacing * (self.cols - 1)) / self.cols)
        rows = max(1, (len(visible) + self.cols - 1) // self.cols)
        row_h = max(0, (ch - self.spacing * (rows - 1)) / rows)
        for i, c in enumerate(visible):
            col = i % self.cols
            row = i // self.cols
            c.x = cx + col * (col_w + self.spacing)
            c.y = cy + row * (row_h + self.spacing)
            c.w = col_w
            c.h = row_h
            c._z = self._z + 1
        self._needs_layout = False

    def draw(self, draw_ns):
        if self._needs_layout:
            self._do_layout()
        super().draw(draw_ns)

    def update(self, input_ns=None):
        if self._needs_layout:
            self._do_layout()
        super().update(input_ns)


# ─────────────────────────────────────────────────────────────────────────────
# Module registration
# ─────────────────────────────────────────────────────────────────────────────

from stdlib import register_module

register_module("gui", {
    "Button": Button,
    "Label": Label,
    "Panel": Panel,
    "Image": Image,
    "HBox": HBox,
    "VBox": VBox,
    "Grid": Grid,
    "SIZE_FIXED": SIZE_FIXED,
    "SIZE_FILL": SIZE_FILL,
})
