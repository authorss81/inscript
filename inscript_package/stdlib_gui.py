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
# Checkbox
# ─────────────────────────────────────────────────────────────────────────────

class Checkbox(_Widget):
    def __init__(self, x: float = 0, y: float = 0, text: str = "", font_size: int = 16):
        super().__init__(x, y, 20, 20)
        self.text = text
        self.font_size = font_size
        self.checked = False
        self.box_color = _color_dict(0.5, 0.5, 0.5)
        self.check_color = _color_dict(0.2, 0.8, 0.2)
        self.text_color = _color_dict(1.0, 1.0, 1.0)
        self.hover_color = _color_dict(0.6, 0.6, 0.6)
        self.hovered = False
        self._on_change = None

    def on_change(self, fn):
        self._on_change = fn

    def update(self, input_ns=None):
        if not self.visible or input_ns is None:
            return
        mx = getattr(input_ns, "mouse_x", 0)
        my = getattr(input_ns, "mouse_y", 0)
        self.hovered = self.contains(mx, my)
        if self.hovered:
            mp = getattr(input_ns, "mouse_pressed", None)
            if mp is not None and mp(0):
                self.checked = not self.checked
                if self._on_change:
                    _call_user_fn(self._on_change, self.checked)

    def draw(self, draw_ns):
        if not self.visible:
            return
        box_color = self.hover_color if self.hovered else self.box_color
        if hasattr(draw_ns, "rect"):
            draw_ns.rect(self.x, self.y, 18, 18, box_color, True)
            draw_ns.rect(self.x, self.y, 18, 18, _color_dict(0.3, 0.3, 0.3), False, 2)
        if self.checked and hasattr(draw_ns, "line"):
            draw_ns.line(self.x + 3, self.y + 9, self.x + 7, self.y + 14, self.check_color, 2)
            draw_ns.line(self.x + 7, self.y + 14, self.x + 15, self.y + 4, self.check_color, 2)
        if self.text and hasattr(draw_ns, "text"):
            draw_ns.text(self.x + 24, self.y + 2, self.text, self.text_color, self.font_size)
        elif self.text and hasattr(draw_ns, "text_centered"):
            draw_ns.text_centered(self.x + 24, self.y + 10, self.text, self.text_color, self.font_size)

    def set_attr(self, name: str, val):
        if name == "checked": self.checked = bool(val)
        elif name == "text": self.text = str(val)
        elif name == "font_size": self.font_size = int(val)
        else: super().set_attr(name, val)


# ─────────────────────────────────────────────────────────────────────────────
# Slider
# ─────────────────────────────────────────────────────────────────────────────

class Slider(_Widget):
    def __init__(self, x: float = 0, y: float = 0, w: float = 200, h: float = 20,
                 min_val: float = 0.0, max_val: float = 100.0, initial: float = 50.0):
        super().__init__(x, y, w, h)
        self.min_val = float(min_val)
        self.max_val = float(max_val)
        if self.max_val <= self.min_val:
            self.max_val = self.min_val + 1.0
        self.value = max(self.min_val, min(self.max_val, float(initial)))
        self.step = 0.0
        self.track_color = _color_dict(0.3, 0.3, 0.35)
        self.fill_color = _color_dict(0.2, 0.6, 0.9)
        self.thumb_color = _color_dict(0.9, 0.9, 0.9)
        self.text_color = _color_dict(1.0, 1.0, 1.0)
        self._dragging = False
        self._on_change = None

    def on_change(self, fn):
        self._on_change = fn

    def _value_from_x(self, mx):
        track_w = max(1, self.w - 20)
        rel = (mx - (self.x + 10)) / track_w
        rel = max(0.0, min(1.0, rel))
        v = self.min_val + rel * (self.max_val - self.min_val)
        if self.step > 0:
            v = round(v / self.step) * self.step
            v = max(self.min_val, min(self.max_val, v))
        return v

    def update(self, input_ns=None):
        if not self.visible or input_ns is None:
            self._dragging = False
            return
        mx = getattr(input_ns, "mouse_x", 0)
        my = getattr(input_ns, "mouse_y", 0)
        mp = getattr(input_ns, "mouse_pressed", None)
        mdown = getattr(input_ns, "mouse_down", None)
        if self._dragging:
            if mdown is not None and not mdown(0):
                self._dragging = False
            else:
                old_val = self.value
                self.value = self._value_from_x(mx)
                if old_val != self.value and self._on_change:
                    _call_user_fn(self._on_change, self.value)
        elif self.contains(mx, my):
            if mp is not None and mp(0):
                self._dragging = True
                old_val = self.value
                self.value = self._value_from_x(mx)
                if old_val != self.value and self._on_change:
                    _call_user_fn(self._on_change, self.value)

    def draw(self, draw_ns):
        if not self.visible:
            return
        track_y = self.y + self.h / 2 - 4
        tc = _to_pg_color(self.track_color)
        fc = _to_pg_color(self.fill_color)
        thumb_c = _to_pg_color(self.thumb_color)
        ratio = (self.value - self.min_val) / (self.max_val - self.min_val)
        thumb_x = self.x + 10 + ratio * max(0, self.w - 20)
        thumb_y = self.y + self.h / 2
        if hasattr(draw_ns, "rect"):
            draw_ns.rect(self.x, track_y, self.w, 8, self.track_color, True)
            fill_w = max(0, thumb_x - self.x)
            draw_ns.rect(self.x, track_y, fill_w, 8, self.fill_color, True)
            draw_ns.rect(round(thumb_x) - 6, round(thumb_y) - 8, 12, 16, self.thumb_color, True)
            draw_ns.rect(round(thumb_x) - 6, round(thumb_y) - 8, 12, 16, _color_dict(0.1, 0.1, 0.1), False, 1)
        value_str = f"{self.value:.1f}"
        if self.step > 0 and self.step >= 1:
            value_str = str(int(self.value))
        if hasattr(draw_ns, "text_right"):
            draw_ns.text_right(self.x + self.w - 4, self.y + 2, value_str, self.text_color, 12)
        elif hasattr(draw_ns, "text"):
            draw_ns.text(self.x + self.w - len(value_str) * 6, self.y + 2, value_str, self.text_color, 12)

    def set_attr(self, name: str, val):
        if name == "value":
            self.value = max(self.min_val, min(self.max_val, float(val)))
        elif name == "min_val": self.min_val = float(val)
        elif name == "max_val":
            self.max_val = float(val)
            if self.max_val <= self.min_val:
                self.max_val = self.min_val + 1.0
            self.value = max(self.min_val, min(self.max_val, self.value))
        elif name == "step": self.step = float(val)
        else: super().set_attr(name, val)


# ─────────────────────────────────────────────────────────────────────────────
# TextInput — Single-line text entry
# ─────────────────────────────────────────────────────────────────────────────

_ALPHANUM = "abcdefghijklmnopqrstuvwxyz0123456789"

class TextInput(_Widget):
    def __init__(self, x: float = 0, y: float = 0, w: float = 200, h: float = 30,
                 placeholder: str = "", font_size: int = 16):
        super().__init__(x, y, w, h)
        self.text = ""
        self.placeholder = placeholder
        self.font_size = font_size
        self.focused = False
        self.bg_color = _color_dict(0.15, 0.15, 0.18)
        self.text_color = _color_dict(1.0, 1.0, 1.0)
        self.placeholder_color = _color_dict(0.4, 0.4, 0.45)
        self.cursor_color = _color_dict(0.8, 0.8, 0.8)
        self.border_color = _color_dict(0.4, 0.4, 0.5)
        self.focus_border_color = _color_dict(0.3, 0.6, 1.0)
        self._on_submit = None
        self._on_change = None

    def on_submit(self, fn):
        self._on_submit = fn

    def on_change(self, fn):
        self._on_change = fn

    def update(self, input_ns=None):
        if not self.visible or input_ns is None:
            return
        mx = getattr(input_ns, "mouse_x", 0)
        my = getattr(input_ns, "mouse_y", 0)
        mp = getattr(input_ns, "mouse_pressed", None)
        if mp is not None and mp(0):
            if self.contains(mx, my):
                self.focused = True
            else:
                self.focused = False
        if not self.focused:
            return
        old_text = self.text
        shift = False
        kd = getattr(input_ns, "key_down", None)
        if kd is not None:
            shift = kd("lshift") or kd("rshift")
        kp = getattr(input_ns, "key_pressed", None)
        if kp is None:
            return
        for ch in _ALPHANUM:
            if kp(ch):
                self.text += ch.upper() if shift else ch
        if kp("space"):
            self.text += " "
        if kp("backspace"):
            self.text = self.text[:-1]
        if kp("enter") or kp("return"):
            if self._on_submit:
                _call_user_fn(self._on_submit, self.text)
        if old_text != self.text and self._on_change:
            _call_user_fn(self._on_change, self.text)

    def draw(self, draw_ns):
        if not self.visible:
            return
        bc = _to_pg_color(self.focus_border_color if self.focused else self.border_color)
        bg = _to_pg_color(self.bg_color)
        tc = _to_pg_color(self.text_color)
        pc = _to_pg_color(self.placeholder_color)
        cc = _to_pg_color(self.cursor_color)
        if hasattr(draw_ns, "rect"):
            draw_ns.rect(self.x, self.y, self.w, self.h, self.bg_color, True)
            draw_ns.rect(self.x, self.y, self.w, self.h, self.border_color, False, 2)
        display_text = self.text if self.text else self.placeholder
        display_color = self.text_color if self.text else self.placeholder_color
        if hasattr(draw_ns, "rect") and self.focused:
            draw_ns.rect(self.x, self.y, self.w, self.h, self.focus_border_color, False, 2)
        if hasattr(draw_ns, "text"):
            draw_ns.text(self.x + 4, self.y + 4, display_text, display_color, self.font_size)
        if self.focused and hasattr(draw_ns, "rect"):
            cursor_x = self.x + 4 + len(self.text) * int(self.font_size * 0.5)
            draw_ns.rect(cursor_x, self.y + 4, 2, self.font_size, self.cursor_color, True)

    def set_attr(self, name: str, val):
        if name == "text": self.text = str(val)
        elif name == "placeholder": self.placeholder = str(val)
        elif name == "focused": self.focused = bool(val)
        elif name == "font_size": self.font_size = int(val)
        else: super().set_attr(name, val)


# ─────────────────────────────────────────────────────────────────────────────
# Dropdown
# ─────────────────────────────────────────────────────────────────────────────

class Dropdown(_Widget):
    def __init__(self, x: float = 0, y: float = 0, w: float = 200, h: float = 30,
                 options: list = None, font_size: int = 16):
        super().__init__(x, y, w, h)
        self.options = list(options) if options else []
        self.selected_index = -1
        self.selected_text = ""
        self.selected_value = None
        self.font_size = font_size
        self._open = False
        self.bg_color = _color_dict(0.25, 0.25, 0.3)
        self.text_color = _color_dict(1.0, 1.0, 1.0)
        self.hover_color = _color_dict(0.35, 0.35, 0.4)
        self.option_bg_color = _color_dict(0.2, 0.2, 0.22)
        self.border_color = _color_dict(0.4, 0.4, 0.5)
        self._on_select = None
        self._option_rects = []
        self._hovered_option = -1

    def on_select(self, fn):
        self._on_select = fn

    def add_option(self, label: str):
        self.options.append(label)

    def remove_option(self, index: int):
        if 0 <= index < len(self.options):
            self.options.pop(index)
            if self.selected_index == index:
                self.selected_index = -1
                self.selected_text = ""
                self.selected_value = None
            elif self.selected_index > index:
                self.selected_index -= 1

    def clear_options(self):
        self.options.clear()
        self.selected_index = -1
        self.selected_text = ""
        self.selected_value = None

    def _get_option_label(self, opt) -> str:
        if isinstance(opt, dict):
            return str(opt.get("label", opt.get("value", str(opt))))
        return str(opt)

    def _get_option_value(self, opt):
        if isinstance(opt, dict):
            return opt.get("value", opt.get("label", opt))
        return opt

    def update(self, input_ns=None):
        if not self.visible or input_ns is None:
            self._open = False
            return
        mx = getattr(input_ns, "mouse_x", 0)
        my = getattr(input_ns, "mouse_y", 0)
        mp = getattr(input_ns, "mouse_pressed", None)
        if mp is None:
            return
        if self._open:
            self._hovered_option = -1
            for i, rect in enumerate(self._option_rects):
                if rect[0] <= mx <= rect[0] + rect[2] and rect[1] <= my <= rect[1] + rect[3]:
                    self._hovered_option = i
                    break
            if mp(0):
                clicked_on_option = False
                for i, rect in enumerate(self._option_rects):
                    if rect[0] <= mx <= rect[0] + rect[2] and rect[1] <= my <= rect[1] + rect[3]:
                        self.selected_index = i
                        self.selected_text = self._get_option_label(self.options[i])
                        self.selected_value = self._get_option_value(self.options[i])
                        self._open = False
                        clicked_on_option = True
                        if self._on_select:
                            _call_user_fn(self._on_select, self.selected_value)
                        break
                if not clicked_on_option:
                    if not (self.x <= mx <= self.x + self.w and self.y <= my <= self.y + self.h):
                        self._open = False
                    elif mp(0):
                        self._open = False
        else:
            if self.contains(mx, my) and mp(0):
                if len(self.options) > 0:
                    self._open = True
                    self._hovered_option = -1

    def draw(self, draw_ns):
        if not self.visible:
            return
        if hasattr(draw_ns, "rect"):
            draw_ns.rect(self.x, self.y, self.w, self.h, self.bg_color, True)
            draw_ns.rect(self.x, self.y, self.w, self.h, self.border_color, False, 2)
        display = self.selected_text if self.selected_text else "Select..."
        if hasattr(draw_ns, "text"):
            draw_ns.text(self.x + 4, self.y + 4, display, self.text_color, self.font_size)
        if hasattr(draw_ns, "text_centered") or hasattr(draw_ns, "text"):
            arrow = "▼"
            arrow_x = self.x + self.w - 16
            arrow_y = self.y + self.h / 2 - 6
            if hasattr(draw_ns, "text"):
                draw_ns.text(arrow_x, arrow_y, arrow, self.text_color, 12)
        if not self._open:
            return
        opt_h = max(20, self.font_size + 8)
        total_h = len(self.options) * opt_h
        self._option_rects.clear()
        if hasattr(draw_ns, "rect"):
            draw_ns.rect(self.x, self.y + self.h, self.w, total_h, self.option_bg_color, True)
            draw_ns.rect(self.x, self.y + self.h, self.w, total_h, self.border_color, False, 1)
        for i, opt in enumerate(self.options):
            ox = self.x
            oy = self.y + self.h + i * opt_h
            if hasattr(draw_ns, "rect") and self._hovered_option == i:
                draw_ns.rect(ox, oy, self.w, opt_h, self.hover_color, True)
            label = self._get_option_label(opt)
            if hasattr(draw_ns, "text"):
                draw_ns.text(ox + 4, oy + 2, label, self.text_color, self.font_size)
            self._option_rects.append((ox, oy, self.w, opt_h))

    def set_attr(self, name: str, val):
        if name == "options":
            self.options = list(val) if isinstance(val, (list, tuple)) else []
            self.selected_index = -1
            self.selected_text = ""
            self.selected_value = None
        elif name == "selected_index":
            idx = int(val)
            if 0 <= idx < len(self.options):
                self.selected_index = idx
                self.selected_text = self._get_option_label(self.options[idx])
                self.selected_value = self._get_option_value(self.options[idx])
        elif name == "font_size": self.font_size = int(val)
        else: super().set_attr(name, val)


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
    "Checkbox": Checkbox,
    "Slider": Slider,
    "TextInput": TextInput,
    "Dropdown": Dropdown,
    "SIZE_FIXED": SIZE_FIXED,
    "SIZE_FILL": SIZE_FILL,
})
