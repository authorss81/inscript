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
    _widget_type = "Widget"

    def __init__(self, x: float, y: float, w: float, h: float):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.visible = True
        self.size_policy_w = SIZE_FILL
        self.size_policy_h = SIZE_FILL
        self._z = 0
        self.tab_index = -1
        self._focused = False
        self.disabled = False
        self.shadow = None
        self.rounded_radius = 0
        self.theme = None

    def _init_theme(self):
        if self.theme is None:
            g = globals()
            dt = g.get("default_theme")
            if dt is not None:
                self.theme = dt
        if self.theme is not None:
            self.theme.apply_to(self)

    def contains(self, px: float, py: float) -> bool:
        return self.visible and not self.disabled and (self.x <= px <= self.x + self.w and
                                                       self.y <= py <= self.y + self.h)

    def set_attr(self, name: str, val):
        if name == "x": self.x = val
        elif name == "y": self.y = val
        elif name == "w": self.w = val
        elif name == "h": self.h = val
        elif name == "visible": self.visible = bool(val)
        elif name == "disabled": self.disabled = bool(val)
        elif name == "size_policy_w": self.size_policy_w = int(val)
        elif name == "size_policy_h": self.size_policy_h = int(val)
        elif name == "tab_index": self.tab_index = int(val)
        elif name == "rounded_radius": self.rounded_radius = float(val)
        elif name == "shadow": self.shadow = val if isinstance(val, dict) else None
        else:
            raise AttributeError(f"_Widget has no settable attribute '{name}'")

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False

    def toggle_visible(self):
        self.visible = not self.visible

    def enable(self):
        self.disabled = False

    def disable(self):
        self.disabled = True

    def _draw_shadow(self, draw_ns):
        if self.shadow is None or not hasattr(draw_ns, "rect"):
            return
        sx = self.shadow.get("offset_x", 3)
        sy = self.shadow.get("offset_y", 3)
        size = self.shadow.get("size", 4)
        color = self.shadow.get("color", _color_dict(0, 0, 0, 0.3))
        for i in range(size):
            a = 1.0 - (i / max(1, size)) * 0.8
            sc = _color_dict(color["r"], color["g"], color["b"], color.get("a", 0.3) * a)
            draw_ns.rect(self.x + sx + i, self.y + sy + i, self.w, self.h, sc, True)

    def update(self, input_ns=None):
        raise NotImplementedError

    def draw(self, draw_ns):
        raise NotImplementedError


class Button(_Widget):
    _widget_type = "Button"

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
        self.icon = ""
        self._on_click = None
        self._on_hover = None
        self._init_theme()

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
        self._draw_shadow(draw_ns)
        if self.disabled:
            color = _color_dict(0.2, 0.2, 0.22)
            tc = _color_dict(0.5, 0.5, 0.5)
        else:
            color = self.pressed_color if self.pressed else (
                self.hover_color if self.hovered else self.bg_color)
            tc = self.text_color
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        rr = max(0, int(self.rounded_radius))
        if hasattr(draw_ns, "rounded_rect") and rr > 0:
            draw_ns.rounded_rect(self.x, self.y, self.w, self.h, color, rr, True)
        elif hasattr(draw_ns, "rect"):
            draw_ns.rect(self.x, self.y, self.w, self.h, color, True)
        text_x = self.x
        if self.icon and hasattr(draw_ns, "sprite"):
            draw_ns.sprite(self.x + 4, self.y + 2, self.icon, 255)
            text_x = self.x + 24
        if self.text and hasattr(draw_ns, "text_centered"):
            if self.icon:
                draw_ns.text(text_x + 4, cy - self.font_size / 2, self.text, tc, self.font_size)
            else:
                draw_ns.text_centered(cx, cy, self.text, tc, self.font_size)
        elif self.text and hasattr(draw_ns, "text"):
            draw_ns.text(text_x + 4, cy - self.font_size / 2, self.text, tc, self.font_size)

    def set_attr(self, name: str, val):
        if name == "icon": self.icon = str(val)
        else: super().set_attr(name, val)


class Label(_Widget):
    _widget_type = "Label"

    def __init__(self, x: float, y: float, text: str = "", font_size: int = 16):
        super().__init__(x, y, 0, 0)
        self.text = text
        self.font_size = font_size
        self.color = _color_dict(1.0, 1.0, 1.0)
        self.bg_color = None
        self.wrap = False
        self.wrap_width = 200.0
        self._init_theme()

    def _wrap_lines(self):
        if not self.wrap or not self.text:
            return [self.text]
        char_w = self.font_size * 0.6
        max_chars = max(1, int(self.wrap_width / char_w))
        words = self.text.split(" ")
        lines = []
        current = ""
        for word in words:
            candidate = (current + " " + word).strip()
            if len(candidate) <= max_chars or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def draw(self, draw_ns):
        if not self.visible:
            return
        lines = self._wrap_lines()
        lh = self.font_size + 4
        total_h = len(lines) * lh
        if self.bg_color and hasattr(draw_ns, "rect"):
            max_w = max((len(l) * self.font_size * 0.6 for l in lines), default=0)
            draw_ns.rect(self.x - 2, self.y - 2, max_w + 4, total_h + 4, self.bg_color, True)
        for i, line in enumerate(lines):
            if line and hasattr(draw_ns, "text"):
                draw_ns.text(self.x, self.y + i * lh, line, self.color, self.font_size)
            elif line and hasattr(draw_ns, "text_centered"):
                draw_ns.text_centered(self.x, self.y + i * lh + lh / 2, line, self.color, self.font_size)

    def update(self, input_ns=None):
        pass

    def set_attr(self, name: str, val):
        if name == "wrap": self.wrap = bool(val)
        elif name == "wrap_width": self.wrap_width = float(val)
        else: super().set_attr(name, val)


class Panel(_Widget):
    _widget_type = "Panel"

    def __init__(self, x: float, y: float, w: float, h: float):
        super().__init__(x, y, w, h)
        self.children: List[_Widget] = []
        self.bg_color = None
        self.border_color = None
        self.border_width = 0
        self._init_theme()

    def add(self, widget):
        if widget.theme is None and self.theme is not None:
            widget.theme = self.theme
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
        _tab_cycle_focus(self.children, input_ns)

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
    _widget_type = "Image"

    def __init__(self, x: float, y: float, path: str = ""):
        super().__init__(x, y, 0, 0)
        self.path = path
        self.alpha = 255
        self.scale = 1.0
        self.angle = 0.0
        self.mode = "stretch"
        self._init_theme()

    def draw(self, draw_ns):
        if not self.visible or not self.path:
            return
        sp = getattr(draw_ns, "sprite", None)
        sp_ex = getattr(draw_ns, "sprite_ex", None)
        if sp_ex is not None:
            if self.mode == "fit":
                s = min(self.w / max(1, self.w), self.h / max(1, self.h))
                cx = self.x + (self.w - self.w * s) / 2
                cy = self.y + (self.h - self.h * s) / 2
                sp_ex(cx, cy, self.path, self.angle, s, False, False, self.alpha)
            elif self.mode == "tile":
                tw = max(1, int(self.w / max(1, self.scale)))
                th = max(1, int(self.h / max(1, self.scale)))
                for ty in range(th):
                    for tx in range(tw):
                        sp_ex(self.x + tx * self.w / max(1, tw),
                              self.y + ty * self.h / max(1, th),
                              self.path, 0, 1.0, False, False, self.alpha)
            else:
                sp_ex(self.x, self.y, self.path, self.angle, self.scale,
                      False, False, self.alpha)
        elif sp is not None:
            if self.mode == "tile":
                tw = max(1, int(self.w / 32))
                th = max(1, int(self.h / 32))
                for ty in range(th):
                    for tx in range(tw):
                        sp(self.x + tx * 32, self.y + ty * 32, self.path, self.alpha)
            else:
                sp(self.x, self.y, self.path, self.alpha)

    def update(self, input_ns=None):
        pass

    def set_attr(self, name: str, val):
        if name == "mode": self.mode = str(val)
        elif name == "path": self.path = str(val)
        elif name == "alpha": self.alpha = int(val)
        elif name == "scale": self.scale = float(val)
        elif name == "angle": self.angle = float(val)
        else: super().set_attr(name, val)


# ─────────────────────────────────────────────────────────────────────────────
# HBox — Horizontal Box Layout
# ─────────────────────────────────────────────────────────────────────────────

class HBox(Panel):
    _widget_type = "HBox"

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
    _widget_type = "VBox"

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
    _widget_type = "Grid"

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
    _widget_type = "Checkbox"

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
        self._init_theme()

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
    _widget_type = "Slider"

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
        self._init_theme()

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
    _widget_type = "TextInput"

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
        self.required = False
        self.min_length = 0
        self.max_length = 0
        self.pattern = ""
        self._error = ""
        self._on_submit = None
        self._on_change = None
        self._init_theme()

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

    def validate(self) -> bool:
        if self.required and not self.text:
            self._error = "Required"
            return False
        if self.min_length > 0 and len(self.text) < self.min_length:
            self._error = f"Min {self.min_length} chars"
            return False
        if self.max_length > 0 and len(self.text) > self.max_length:
            self._error = f"Max {self.max_length} chars"
            return False
        if self.pattern:
            import re
            if not re.match(self.pattern, self.text):
                self._error = "Invalid format"
                return False
        self._error = ""
        return True

    def set_attr(self, name: str, val):
        if name == "text": self.text = str(val)
        elif name == "placeholder": self.placeholder = str(val)
        elif name == "focused": self.focused = bool(val)
        elif name == "font_size": self.font_size = int(val)
        elif name == "required": self.required = bool(val)
        elif name == "min_length": self.min_length = int(val)
        elif name == "max_length": self.max_length = int(val)
        elif name == "pattern": self.pattern = str(val) if val else ""
        else: super().set_attr(name, val)


# ─────────────────────────────────────────────────────────────────────────────
# Dropdown
# ─────────────────────────────────────────────────────────────────────────────

class Dropdown(_Widget):
    _widget_type = "Dropdown"

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
        self._init_theme()

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
# Focus navigation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _set_focused(widget, value):
    widget._focused = value
    if hasattr(widget, 'focused'):
        widget.focused = value


def _tab_cycle_focus(children, input_ns):
    if not children or input_ns is None:
        return
    kp = getattr(input_ns, "key_pressed", None)
    if kp is None or not kp("tab"):
        return
    focusable = [(c.tab_index, i, c) for i, c in enumerate(children)
                 if c.visible and c.tab_index >= 0]
    if not focusable:
        return
    focusable.sort(key=lambda x: (x[0], x[1]))
    shift = getattr(input_ns, "key_down", None)
    shift_held = shift is not None and (shift("lshift") or shift("rshift"))
    cur = -1
    for i, (_, _, c) in enumerate(focusable):
        if c._focused:
            cur = i
            break
    if shift_held:
        cur = cur - 1 if cur > 0 else len(focusable) - 1
    else:
        cur = cur + 1 if cur >= 0 and cur < len(focusable) - 1 else 0
    for _, _, c in focusable:
        _set_focused(c, False)
    _set_focused(focusable[cur][2], True)


# ─────────────────────────────────────────────────────────────────────────────
# ScrollView — scrollable content area
# ─────────────────────────────────────────────────────────────────────────────

class ScrollView(Panel):
    _widget_type = "ScrollView"

    def __init__(self, x: float = 0, y: float = 0, w: float = 300, h: float = 200):
        super().__init__(x, y, w, h)
        self.scroll_x = 0.0
        self.scroll_y = 0.0
        self.scrollbar_size = 12
        self.track_color = _color_dict(0.2, 0.2, 0.22)
        self.thumb_color = _color_dict(0.45, 0.45, 0.5)
        self.thumb_hover_color = _color_dict(0.55, 0.55, 0.6)
        self._content_w = w
        self._content_h = h
        self._drag_v = False
        self._drag_h = False
        self._thumb_hover_v = False
        self._thumb_hover_h = False

    def _recalc_content(self):
        if not self.children:
            self._content_w = self.w
            self._content_h = self.h
            return
        min_x = min(c.x for c in self.children)
        min_y = min(c.y for c in self.children)
        max_x = max(c.x + c.w for c in self.children)
        max_y = max(c.y + c.h for c in self.children)
        self._content_w = max(self.w, max_x - min_x)
        self._content_h = max(self.h, max_y - min_y)

    def _has_v_scroll(self):
        return self._content_h > self.h

    def _has_h_scroll(self):
        return self._content_w > self.w

    def _v_thumb_size(self):
        if not self._has_v_scroll():
            return self.h
        ratio = self.h / self._content_h
        return max(20, ratio * self.h)

    def _h_thumb_size(self):
        if not self._has_h_scroll():
            return self.w
        ratio = self.w / self._content_w
        return max(20, ratio * self.w)

    def _v_thumb_y(self):
        avail = self.h - self._v_thumb_size() - self.scrollbar_size if self._has_h_scroll() else self.h - self._v_thumb_size()
        ratio = self.scroll_y / max(1, self._content_h - self.h)
        return self.y + ratio * avail

    def _h_thumb_x(self):
        avail = self.w - self._h_thumb_size() - self.scrollbar_size if self._has_v_scroll() else self.w - self._h_thumb_size()
        ratio = self.scroll_x / max(1, self._content_w - self.w)
        return self.x + ratio * avail

    def update(self, input_ns=None):
        if not self.visible or input_ns is None:
            self._drag_v = False
            self._drag_h = False
            return
        self._recalc_content()
        mx = getattr(input_ns, "mouse_x", 0)
        my = getattr(input_ns, "mouse_y", 0)
        mp = getattr(input_ns, "mouse_pressed", None)
        mdown = getattr(input_ns, "mouse_down", None)
        mw = getattr(input_ns, "mouse_wheel", 0)
        # Scrollbar drag state machine
        v_bar_x = self.x + self.w - self.scrollbar_size
        h_bar_y = self.y + self.h - self.scrollbar_size
        if self._drag_v:
            if mdown is not None and not mdown(0):
                self._drag_v = False
            else:
                bar_avail = (self.h - self._v_thumb_size() -
                             (self.scrollbar_size if self._has_h_scroll() else 0))
                rel = (my - self.y) / max(1, bar_avail)
                self.scroll_y = max(0, min(self._content_h - self.h, rel * (self._content_h - self.h)))
        elif self._drag_h:
            if mdown is not None and not mdown(0):
                self._drag_h = False
            else:
                bar_avail = (self.w - self._h_thumb_size() -
                             (self.scrollbar_size if self._has_v_scroll() else 0))
                rel = (mx - self.x) / max(1, bar_avail)
                self.scroll_x = max(0, min(self._content_w - self.w, rel * (self._content_w - self.w)))
        # Mouse wheel
        if self.contains(mx, my) and mw != 0:
            self.scroll_y = max(0, min(self._content_h - self.h,
                                       self.scroll_y - mw * 30))
        # Thumb hover
        self._thumb_hover_v = (self._has_v_scroll() and
                               v_bar_x <= mx <= v_bar_x + self.scrollbar_size and
                               self._v_thumb_y() <= my <= self._v_thumb_y() + self._v_thumb_size())
        self._thumb_hover_h = (self._has_h_scroll() and
                               h_bar_y <= my <= h_bar_y + self.scrollbar_size and
                               self._h_thumb_x() <= mx <= self._h_thumb_x() + self._h_thumb_size())
        # Start drag on thumb click
        if mp is not None and mp(0):
            if self._thumb_hover_v:
                self._drag_v = True
            elif self._thumb_hover_h:
                self._drag_h = True
            elif self._has_v_scroll() and v_bar_x <= mx <= v_bar_x + self.scrollbar_size and self.y <= my <= self.y + self.h:
                rel = (my - self.y) / max(1, self.h)
                self.scroll_y = max(0, min(self._content_h - self.h, rel * self._content_h))
                self._drag_v = True
            elif self._has_h_scroll() and h_bar_y <= my <= h_bar_y + self.scrollbar_size and self.x <= mx <= self.x + self.w:
                rel = (mx - self.x) / max(1, self.w)
                self.scroll_x = max(0, min(self._content_w - self.w, rel * self._content_w))
                self._drag_h = True
        # Transform input for children (add scroll offset to mouse coords)
        class _ScrolledInput:
            def __init__(self, ns, sx, sy, sv):
                self._ns = ns
                self._sx = sx
                self._sy = sy
                self._sv = sv
            @property
            def mouse_x(self):
                return getattr(self._ns, "mouse_x", 0) + self._sx
            @property
            def mouse_y(self):
                return getattr(self._ns, "mouse_y", 0) + self._sy
            def __getattr__(self, name):
                return getattr(self._ns, name)
        scroll_ns = _ScrolledInput(input_ns, self.scroll_x, self.scroll_y, self.scrollbar_size)
        # Filter out children not in viewport
        for child in self.children:
            child_vx = child.x - self.scroll_x
            child_vy = child.y - self.scroll_y
            if child_vx + child.w < self.x or child_vx > self.x + self.w:
                continue
            if child_vy + child.h < self.y or child_vy > self.y + self.h:
                continue
            child.update(scroll_ns)

    def draw(self, draw_ns):
        if not self.visible:
            return
        if self.bg_color and hasattr(draw_ns, "rect"):
            draw_ns.rect(self.x, self.y, self.w, self.h, self.bg_color, True)
        if self.border_color and self.border_width > 0 and hasattr(draw_ns, "rect"):
            draw_ns.rect(self.x, self.y, self.w, self.h, self.border_color, False, self.border_width)
        # Draw visible children with scroll offset
        for child in sorted(self.children, key=lambda c: c._z):
            child_x = child.x - self.scroll_x
            child_y = child.y - self.scroll_y
            if child_x + child.w < self.x or child_x > self.x + self.w:
                continue
            if child_y + child.h < self.y or child_y > self.y + self.h:
                continue
            orig_x, orig_y = child.x, child.y
            child.x = child_x
            child.y = child_y
            child.draw(draw_ns)
            child.x, child.y = orig_x, orig_y
        # Draw scrollbars
        sb = self.scrollbar_size
        if self._has_v_scroll() and hasattr(draw_ns, "rect"):
            bx = self.x + self.w - sb
            draw_ns.rect(bx, self.y, sb, self.h - (sb if self._has_h_scroll() else 0),
                         self.track_color, True)
            thumb_c = self.thumb_hover_color if self._thumb_hover_v else self.thumb_color
            ty = self._v_thumb_y()
            th = self._v_thumb_size()
            draw_ns.rect(bx, ty, sb, th, thumb_c, True)
        if self._has_h_scroll() and hasattr(draw_ns, "rect"):
            by = self.y + self.h - sb
            draw_ns.rect(self.x, by, self.w - (sb if self._has_v_scroll() else 0), sb,
                         self.track_color, True)
            thumb_c = self.thumb_hover_color if self._thumb_hover_h else self.thumb_color
            tx = self._h_thumb_x()
            tw = self._h_thumb_size()
            draw_ns.rect(tx, by, tw, sb, thumb_c, True)

    def set_attr(self, name: str, val):
        if name == "scroll_x": self.scroll_x = float(val)
        elif name == "scroll_y": self.scroll_y = float(val)
        elif name == "scrollbar_size": self.scrollbar_size = float(val)
        else: super().set_attr(name, val)


# ─────────────────────────────────────────────────────────────────────────────
# TextArea — Multi-line text input
# ─────────────────────────────────────────────────────────────────────────────

class TextArea(ScrollView):
    _widget_type = "TextArea"

    def __init__(self, x: float = 0, y: float = 0, w: float = 300, h: float = 150,
                 font_size: int = 14):
        super().__init__(x, y, w, h)
        self.text = ""
        self.font_size = font_size
        self._line_h = font_size + 4
        self.focused = False
        self.placeholder = ""
        self.bg_color = _color_dict(0.12, 0.12, 0.15)
        self.border_color = _color_dict(0.4, 0.4, 0.5)
        self.focus_border_color = _color_dict(0.3, 0.6, 1.0)
        self.text_color = _color_dict(1.0, 1.0, 1.0)
        self.placeholder_color = _color_dict(0.4, 0.4, 0.45)
        self.cursor_color = _color_dict(0.8, 0.8, 0.8)
        self._on_change = None

    def _text_lines(self):
        return self.text.split("\n") if self.text else [""]

    def on_change(self, fn):
        self._on_change = fn

    def update(self, input_ns=None):
        if not self.visible or input_ns is None:
            return
        mx = getattr(input_ns, "mouse_x", 0)
        my = getattr(input_ns, "mouse_y", 0)
        mp = getattr(input_ns, "mouse_pressed", None)
        if mp is not None and mp(0):
            self.focused = self.contains(mx, my)
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
        if kp("enter") or kp("return"):
            self.text += "\n"
            self.scroll_y = max(0, self._content_h - self.h)
        if kp("backspace"):
            self.text = self.text[:-1]
        if old_text != self.text and self._on_change:
            _call_user_fn(self._on_change, self.text)
        lines = self._text_lines()
        self._content_h = max(self.h, len(lines) * self._line_h + 8)
        self._content_w = self.w

    def draw(self, draw_ns):
        if not self.visible:
            return
        if hasattr(draw_ns, "rect"):
            draw_ns.rect(self.x, self.y, self.w, self.h, self.bg_color, True)
            draw_ns.rect(self.x, self.y, self.w, self.h, self.border_color, False, 2)
            if self.focused:
                draw_ns.rect(self.x, self.y, self.w, self.h, self.focus_border_color, False, 2)
        lines = self._text_lines()
        display_lines = lines if self.text else ([self.placeholder] if self.placeholder else [""])
        disp_color = self.text_color if self.text else self.placeholder_color
        for i, line in enumerate(display_lines):
            ly = self.y + 4 + i * self._line_h - self.scroll_y
            if ly + self._line_h < self.y or ly > self.y + self.h:
                continue
            if hasattr(draw_ns, "text"):
                draw_ns.text(self.x + 4, ly, line, disp_color, self.font_size)
        if self.focused and hasattr(draw_ns, "rect"):
            cursor_y = self.y + 4 + (len(lines) - 1) * self._line_h - self.scroll_y
            cursor_x = self.x + 4 + len(lines[-1]) * int(self.font_size * 0.5) if lines else self.x + 4
            if self.y <= cursor_y <= self.y + self.h - 4:
                draw_ns.rect(cursor_x, cursor_y, 2, self._line_h, self.cursor_color, True)

    def set_attr(self, name: str, val):
        if name == "text": self.text = str(val)
        elif name == "placeholder": self.placeholder = str(val)
        elif name == "focused": self.focused = bool(val)
        elif name == "font_size": self.font_size = int(val)
        else: super().set_attr(name, val)


# ─────────────────────────────────────────────────────────────────────────────
# TabContainer — tabbed panels
# ─────────────────────────────────────────────────────────────────────────────

class TabContainer(Panel):
    _widget_type = "TabContainer"

    def __init__(self, x: float = 0, y: float = 0, w: float = 400, h: float = 300,
                 tab_height: int = 28):
        super().__init__(x, y, w, h)
        self.tab_height = tab_height
        self._tabs = []
        self.active_tab = -1

    def set_attr(self, name: str, val):
        if name == "active_tab":
            idx = int(val)
            if 0 <= idx < len(self._tabs):
                self.active_tab = idx
        elif name == "tab_height": self.tab_height = int(val)
        else: super().set_attr(name, val)
        self.tab_bg_color = _color_dict(0.2, 0.2, 0.22)
        self.active_tab_color = _color_dict(0.3, 0.3, 0.35)
        self.tab_hover_color = _color_dict(0.25, 0.25, 0.3)
        self.tab_text_color = _color_dict(0.7, 0.7, 0.7)
        self.active_text_color = _color_dict(1.0, 1.0, 1.0)
        self._hovered_tab = -1

    def add_tab(self, title: str, panel: Panel):
        self._tabs.append({"title": title, "panel": panel})
        panel.x = self.x
        panel.y = self.y + self.tab_height
        panel.w = self.w
        panel.h = self.h - self.tab_height
        self.add(panel)
        if self.active_tab < 0:
            self.active_tab = 0

    def remove_tab(self, index: int):
        if 0 <= index < len(self._tabs):
            self.remove(self._tabs[index]["panel"])
            self._tabs.pop(index)
            if self.active_tab >= len(self._tabs):
                self.active_tab = len(self._tabs) - 1

    def clear_tabs(self):
        for t in self._tabs:
            self.remove(t["panel"])
        self._tabs.clear()
        self.active_tab = -1

    def _tab_width_at(self, index):
        title = self._tabs[index]["title"]
        return max(60, len(title) * 9 + 20)

    def update(self, input_ns=None):
        if not self.visible or input_ns is None:
            return
        mx = getattr(input_ns, "mouse_x", 0)
        my = getattr(input_ns, "mouse_y", 0)
        mp = getattr(input_ns, "mouse_pressed", None)
        self._hovered_tab = -1
        tx = self.x + 2
        for i in range(len(self._tabs)):
            tw = self._tab_width_at(i)
            if tx <= mx <= tx + tw and self.y <= my <= self.y + self.tab_height:
                self._hovered_tab = i
                if mp is not None and mp(0):
                    self.active_tab = i
                break
            tx += tw
        # Update active tab only
        if 0 <= self.active_tab < len(self._tabs):
            self._tabs[self.active_tab]["panel"].update(input_ns)
        # Tab key to switch tabs
        kp = getattr(input_ns, "key_pressed", None)
        if kp is not None and self._focused:
            if kp("left") and self.active_tab > 0:
                self.active_tab -= 1
            elif kp("right") and self.active_tab < len(self._tabs) - 1:
                self.active_tab += 1

    def draw(self, draw_ns):
        if not self.visible:
            return
        # Draw tab headers
        tx = self.x + 2
        for i, tab in enumerate(self._tabs):
            tw = self._tab_width_at(i)
            bg = self.active_tab_color if i == self.active_tab else (
                self.tab_hover_color if i == self._hovered_tab else self.tab_bg_color)
            tc = self.active_text_color if i == self.active_tab else self.tab_text_color
            if hasattr(draw_ns, "rect"):
                draw_ns.rect(tx, self.y, tw, self.tab_height, bg, True)
                if i == self.active_tab and hasattr(draw_ns, "line"):
                    draw_ns.line(tx, self.y + self.tab_height, tx + tw, self.y + self.tab_height,
                                 bg, 2)
            if hasattr(draw_ns, "text_centered"):
                draw_ns.text_centered(tx + tw / 2, self.y + self.tab_height / 2,
                                      tab["title"], tc, 12)
            elif hasattr(draw_ns, "text"):
                draw_ns.text(tx + 4, self.y + 4, tab["title"], tc, 12)
            tx += tw
        # Draw content area background
        if hasattr(draw_ns, "rect"):
            draw_ns.rect(self.x, self.y + self.tab_height, self.w,
                         self.h - self.tab_height, self.bg_color or _color_dict(0.15, 0.15, 0.18), True)
        # Draw active tab content
        if 0 <= self.active_tab < len(self._tabs):
            self._tabs[self.active_tab]["panel"].draw(draw_ns)


# ─────────────────────────────────────────────────────────────────────────────
# Splitter — resizable split panes
# ─────────────────────────────────────────────────────────────────────────────

class Splitter(_Widget):
    _widget_type = "Splitter"

    def __init__(self, x: float = 0, y: float = 0, w: float = 400, h: float = 300,
                 orientation: str = "horizontal", split: float = 0.5):
        super().__init__(x, y, w, h)
        self.orientation = orientation
        self.split = max(0.05, min(0.95, float(split)))
        self.divider_size = 6
        self.divider_color = _color_dict(0.3, 0.3, 0.35)
        self.divider_hover_color = _color_dict(0.5, 0.5, 0.55)
        self._dragging = False
        self._hovered = False
        self.panel1 = Panel(0, 0, 0, 0)
        self.panel2 = Panel(0, 0, 0, 0)
        self.panel1._z = self._z + 1
        self.panel2._z = self._z + 1
        self._init_theme()

    def set_attr(self, name: str, val):
        if name == "split":
            self.split = max(0.05, min(0.95, float(val)))
        elif name == "orientation":
            self.orientation = str(val)
        elif name == "divider_size":
            self.divider_size = float(val)
        else:
            super().set_attr(name, val)

    def _layout(self):
        if self.orientation == "horizontal":
            div = self.divider_size
            p1w = max(0, int((self.w - div) * self.split))
            p2w = max(0, self.w - div - p1w)
            self.panel1.x = self.x
            self.panel1.y = self.y
            self.panel1.w = p1w
            self.panel1.h = self.h
            self.panel2.x = self.x + p1w + div
            self.panel2.y = self.y
            self.panel2.w = p2w
            self.panel2.h = self.h
        else:
            div = self.divider_size
            p1h = max(0, int((self.h - div) * self.split))
            p2h = max(0, self.h - div - p1h)
            self.panel1.x = self.x
            self.panel1.y = self.y
            self.panel1.w = self.w
            self.panel1.h = p1h
            self.panel2.x = self.x
            self.panel2.y = self.y + p1h + div
            self.panel2.w = self.w
            self.panel2.h = p2h

    def _divider_rect(self):
        self._layout()
        if self.orientation == "horizontal":
            px = self.panel1.x + self.panel1.w
            return (px, self.y, self.divider_size, self.h)
        else:
            py = self.panel1.y + self.panel1.h
            return (self.x, py, self.w, self.divider_size)

    def update(self, input_ns=None):
        if not self.visible or input_ns is None:
            self._dragging = False
            return
        self._layout()
        mx = getattr(input_ns, "mouse_x", 0)
        my = getattr(input_ns, "mouse_y", 0)
        mp = getattr(input_ns, "mouse_pressed", None)
        mdown = getattr(input_ns, "mouse_down", None)
        dx, dy, dw, dh = self._divider_rect()
        self._hovered = (dx <= mx <= dx + dw and dy <= my <= dy + dh)
        if self._dragging:
            if mdown is not None and not mdown(0):
                self._dragging = False
            else:
                if self.orientation == "horizontal":
                    rel = (mx - self.x) / max(1, self.w - self.divider_size)
                else:
                    rel = (my - self.y) / max(1, self.h - self.divider_size)
                self.split = max(0.05, min(0.95, rel))
                self._layout()
        elif self._hovered and mp is not None and mp(0):
            self._dragging = True
        self.panel1.update(input_ns)
        self.panel2.update(input_ns)

    def draw(self, draw_ns):
        if not self.visible:
            return
        self._layout()
        self.panel1.draw(draw_ns)
        self.panel2.draw(draw_ns)
        dx, dy, dw, dh = self._divider_rect()
        dc = self.divider_hover_color if (self._hovered or self._dragging) else self.divider_color
        if hasattr(draw_ns, "rect"):
            draw_ns.rect(dx, dy, dw, dh, dc, True)


# ─────────────────────────────────────────────────────────────────────────────
# MenuItem, Menu, MenuBar — dropdown menu system
# ─────────────────────────────────────────────────────────────────────────────

class MenuItem:
    def __init__(self, label: str = "", on_click=None, submenu: list = None):
        self.label = label
        self.on_click = on_click
        self.submenu = list(submenu) if submenu else None


class Menu:
    def __init__(self, title: str = ""):
        self.title = title
        self.items: list[MenuItem] = []

    def add_item(self, item: MenuItem):
        self.items.append(item)

    def add(self, label: str, on_click=None):
        self.items.append(MenuItem(label, on_click))

    def add_submenu(self, label: str, items: list):
        self.items.append(MenuItem(label, submenu=items))


class MenuBar(_Widget):
    _widget_type = "MenuBar"

    def __init__(self, x: float = 0, y: float = 0, w: float = 640, h: float = 26):
        super().__init__(x, y, w, h)
        self.menus: list[Menu] = []
        self._open_index = -1
        self._hovered_menu = -1
        self.menu_bg_color = _color_dict(0.18, 0.18, 0.2)
        self.menu_text_color = _color_dict(0.85, 0.85, 0.85)
        self.menu_hover_color = _color_dict(0.3, 0.3, 0.35)
        self.dropdown_bg_color = _color_dict(0.2, 0.2, 0.22)
        self.dropdown_hover_color = _color_dict(0.3, 0.3, 0.35)
        self.dropdown_text_color = _color_dict(1.0, 1.0, 1.0)
        self.border_color = _color_dict(0.3, 0.3, 0.35)
        self._item_rects = []
        self._hovered_item = -1
        self._init_theme()

    def add_menu(self, menu: Menu):
        self.menus.append(menu)

    def _menu_x(self, index):
        x = self.x + 4
        for i in range(index):
            x += max(40, len(self.menus[i].title) * 9 + 16)
        return x

    def _menu_width(self, index):
        return max(40, len(self.menus[index].title) * 9 + 16)

    def close_all(self):
        self._open_index = -1
        self._item_rects.clear()

    def update(self, input_ns=None):
        if not self.visible or input_ns is None:
            self.close_all()
            return
        mx = getattr(input_ns, "mouse_x", 0)
        my = getattr(input_ns, "mouse_y", 0)
        mp = getattr(input_ns, "mouse_pressed", None)
        # Menu bar hover
        self._hovered_menu = -1
        for i in range(len(self.menus)):
            mx_pos = self._menu_x(i)
            mw = self._menu_width(i)
            if mx_pos <= mx <= mx_pos + mw and self.y <= my <= self.y + self.h:
                self._hovered_menu = i
                break
        # Click on menu bar
        if self._hovered_menu >= 0 and mp is not None and mp(0):
            if self._open_index == self._hovered_menu:
                self._open_index = -1
            else:
                self._open_index = self._hovered_menu
                self._item_rects.clear()
            return
        # Close if clicking outside
        if mp is not None and mp(0):
            clicked_menu = False
            for i in range(len(self.menus)):
                mx_pos = self._menu_x(i)
                mw = self._menu_width(i)
                if mx_pos <= mx <= mx_pos + mw and self.y <= my <= self.y + self.h:
                    clicked_menu = True
                    break
            if not clicked_menu and self._open_index >= 0:
                # Check if click is within dropdown
                in_dropdown = False
                for rx, ry, rw, rh in self._item_rects:
                    if rx <= mx <= rx + rw and ry <= my <= ry + rh:
                        in_dropdown = True
                        break
                if not in_dropdown:
                    self.close_all()
        # Open menu: hover + item selection
        if self._open_index >= 0 and self._open_index < len(self.menus):
            menu = self.menus[self._open_index]
            menu_x = self._menu_x(self._open_index)
            item_h = 24
            self._item_rects.clear()
            self._hovered_item = -1
            for i, item in enumerate(menu.items):
                ix = menu_x
                iy = self.y + self.h + i * item_h
                iw = max(120, len(item.label) * 9 + 24)
                self._item_rects.append((ix, iy, iw, item_h))
                if ix <= mx <= ix + iw and iy <= my <= iy + item_h:
                    self._hovered_item = i
            # Click on item
            if mp is not None and mp(0) and self._hovered_item >= 0:
                item = menu.items[self._hovered_item]
                if item.submenu:
                    pass  # submenus deferred for future enhancement
                elif item.on_click:
                    _call_user_fn(item.on_click, item.label)
                self.close_all()

    def draw(self, draw_ns):
        if not self.visible:
            return
        # Draw menu bar background
        if hasattr(draw_ns, "rect"):
            draw_ns.rect(self.x, self.y, self.w, self.h, self.menu_bg_color, True)
            draw_ns.rect(self.x, self.y, self.w, self.h, self.border_color, False, 1)
        # Draw menu titles
        for i, menu in enumerate(self.menus):
            mx_pos = self._menu_x(i)
            mw = self._menu_width(i)
            is_open = (i == self._open_index)
            is_hover = (i == self._hovered_menu)
            bg = self.menu_hover_color if (is_open or is_hover) else None
            if bg and hasattr(draw_ns, "rect"):
                draw_ns.rect(mx_pos, self.y, mw, self.h, bg, True)
            if hasattr(draw_ns, "text_centered"):
                draw_ns.text_centered(mx_pos + mw / 2, self.y + self.h / 2,
                                      menu.title, self.menu_text_color, 11)
            elif hasattr(draw_ns, "text"):
                draw_ns.text(mx_pos + 4, self.y + 4, menu.title, self.menu_text_color, 11)
        # Draw open dropdown
        if self._open_index >= 0 and self._open_index < len(self.menus):
            menu = self.menus[self._open_index]
            menu_x = self._menu_x(self._open_index)
            if not self._item_rects:
                item_h = 24
                for i in range(len(menu.items)):
                    iw = max(120, len(menu.items[i].label) * 9 + 24)
                    self._item_rects.append((menu_x, self.y + self.h + i * item_h, iw, item_h))
            total_h = len(menu.items) * 24
            max_w = max(rw for rw, _, _, _ in self._item_rects) if self._item_rects else 120
            if hasattr(draw_ns, "rect"):
                draw_ns.rect(menu_x, self.y + self.h, max_w, total_h, self.dropdown_bg_color, True)
                draw_ns.rect(menu_x, self.y + self.h, max_w, total_h, self.border_color, False, 1)
            for i, item in enumerate(menu.items):
                ix, iy, iw, ih = self._item_rects[i]
                if hasattr(draw_ns, "rect") and self._hovered_item == i:
                    draw_ns.rect(ix, iy, iw, ih, self.dropdown_hover_color, True)
                if hasattr(draw_ns, "text"):
                    draw_ns.text(ix + 6, iy + 3, item.label, self.dropdown_text_color, 12)

    def set_attr(self, name: str, val):
        if name == "menus":
            self.menus = list(val) if isinstance(val, (list, tuple)) else []
            self.close_all()
        else:
            super().set_attr(name, val)


# ─────────────────────────────────────────────────────────────────────────────
# Theme system
# ─────────────────────────────────────────────────────────────────────────────

_DISABLED_STYLE = {"disabled_text_color": _color_dict(0.5, 0.5, 0.5),
                   "disabled_bg_color": _color_dict(0.15, 0.15, 0.17)}
_DEFAULT_BUTTON = {"bg_color": _color_dict(0.3, 0.3, 0.35),
                   "text_color": _color_dict(1.0, 1.0, 1.0),
                   "hover_color": _color_dict(0.4, 0.4, 0.5),
                   "pressed_color": _color_dict(0.2, 0.2, 0.25),
                   "rounded_radius": 6}
_DEFAULT_LABEL = {"color": _color_dict(1.0, 1.0, 1.0)}
_DEFAULT_CHECKBOX = {"box_color": _color_dict(0.5, 0.5, 0.5),
                     "check_color": _color_dict(0.2, 0.8, 0.2),
                     "text_color": _color_dict(1.0, 1.0, 1.0),
                     "hover_color": _color_dict(0.6, 0.6, 0.6)}
_DEFAULT_SLIDER = {"track_color": _color_dict(0.3, 0.3, 0.35),
                   "fill_color": _color_dict(0.2, 0.6, 0.9),
                   "thumb_color": _color_dict(0.9, 0.9, 0.9),
                   "text_color": _color_dict(1.0, 1.0, 1.0)}
_DEFAULT_TEXTINPUT = {"bg_color": _color_dict(0.15, 0.15, 0.18),
                      "text_color": _color_dict(1.0, 1.0, 1.0),
                      "placeholder_color": _color_dict(0.4, 0.4, 0.45),
                      "border_color": _color_dict(0.4, 0.4, 0.5),
                      "focus_border_color": _color_dict(0.3, 0.6, 1.0)}
_DEFAULT_DROPDOWN = {"bg_color": _color_dict(0.25, 0.25, 0.3),
                     "text_color": _color_dict(1.0, 1.0, 1.0),
                     "hover_color": _color_dict(0.35, 0.35, 0.4),
                     "option_bg_color": _color_dict(0.2, 0.2, 0.22),
                     "border_color": _color_dict(0.4, 0.4, 0.5)}
_DEFAULT_TEXTAREA = {"bg_color": _color_dict(0.12, 0.12, 0.15),
                     "border_color": _color_dict(0.4, 0.4, 0.5),
                     "focus_border_color": _color_dict(0.3, 0.6, 1.0),
                     "text_color": _color_dict(1.0, 1.0, 1.0),
                     "placeholder_color": _color_dict(0.4, 0.4, 0.45),
                     "cursor_color": _color_dict(0.8, 0.8, 0.8)}
_DEFAULT_SCROLLVIEW = {"track_color": _color_dict(0.2, 0.2, 0.22),
                       "thumb_color": _color_dict(0.45, 0.45, 0.5),
                       "thumb_hover_color": _color_dict(0.55, 0.55, 0.6)}
_DEFAULT_TABCONTAINER = {"tab_bg_color": _color_dict(0.2, 0.2, 0.22),
                         "active_tab_color": _color_dict(0.3, 0.3, 0.35),
                         "tab_hover_color": _color_dict(0.25, 0.25, 0.3),
                         "tab_text_color": _color_dict(0.7, 0.7, 0.7),
                         "active_text_color": _color_dict(1.0, 1.0, 1.0)}
_DEFAULT_SPLITTER = {"divider_color": _color_dict(0.3, 0.3, 0.35),
                     "divider_hover_color": _color_dict(0.5, 0.5, 0.55)}
_DEFAULT_MENUBAR = {"menu_bg_color": _color_dict(0.18, 0.18, 0.2),
                    "menu_text_color": _color_dict(0.85, 0.85, 0.85),
                    "menu_hover_color": _color_dict(0.3, 0.3, 0.35),
                    "dropdown_bg_color": _color_dict(0.2, 0.2, 0.22),
                    "dropdown_hover_color": _color_dict(0.3, 0.3, 0.35),
                    "dropdown_text_color": _color_dict(1.0, 1.0, 1.0),
                    "border_color": _color_dict(0.3, 0.3, 0.35)}


class Theme:
    def __init__(self):
        self._styles: dict[str, dict] = {}

    def set_style(self, widget_type: str, props: dict):
        self._styles[widget_type] = dict(props)

    def get_style(self, widget_type: str, attr: str, default=None):
        style = self._styles.get(widget_type, {})
        return style.get(attr, default)

    def apply_to(self, widget):
        wt = getattr(widget, "_widget_type", "Widget")
        style = self._styles.get(wt, {})
        for k, v in style.items():
            if hasattr(widget, k):
                setattr(widget, k, v)

    def set_shadow(self, widget_type: str, offset_x: float = 3, offset_y: float = 3,
                   size: int = 4, color: dict = None):
        self._styles.setdefault(widget_type, {})
        self._styles[widget_type]["shadow"] = {
            "offset_x": offset_x,
            "offset_y": offset_y,
            "size": size,
            "color": color or _color_dict(0, 0, 0, 0.3),
        }


default_theme = Theme()
default_theme.set_style("Button", _DEFAULT_BUTTON)
default_theme.set_style("Label", _DEFAULT_LABEL)
default_theme.set_style("Checkbox", _DEFAULT_CHECKBOX)
default_theme.set_style("Slider", _DEFAULT_SLIDER)
default_theme.set_style("TextInput", _DEFAULT_TEXTINPUT)
default_theme.set_style("Dropdown", _DEFAULT_DROPDOWN)
default_theme.set_style("ScrollView", _DEFAULT_SCROLLVIEW)
default_theme.set_style("TabContainer", _DEFAULT_TABCONTAINER)
default_theme.set_style("Splitter", _DEFAULT_SPLITTER)
default_theme.set_style("MenuBar", _DEFAULT_MENUBAR)
default_theme.set_style("TextArea", _DEFAULT_TEXTAREA)


# ─────────────────────────────────────────────────────────────────────────────
# Data binding (MVC)
# ─────────────────────────────────────────────────────────────────────────────

class ObservableValue:
    def __init__(self, initial=None):
        self._value = initial
        self._callbacks = []

    def get(self):
        return self._value

    def set(self, val):
        old = self._value
        self._value = val
        if old != val:
            for cb in self._callbacks:
                _call_user_fn(cb, val)

    def on_change(self, fn):
        if fn is not None:
            self._callbacks.append(fn)

    def set_attr(self, name: str, val):
        if name == "value": self.set(val)
        else: raise AttributeError(f"ObservableValue has no settable attribute '{name}'")


def bind(widget, attr, observable):
    observable.on_change(lambda val: setattr(widget, attr, str(val) if not isinstance(val, str) else val))
    init_val = observable.get()
    if init_val is not None:
        setattr(widget, attr, str(init_val) if not isinstance(init_val, str) else init_val)


# ─────────────────────────────────────────────────────────────────────────────
# Dialog system
# ─────────────────────────────────────────────────────────────────────────────

def message_box(title: str = "Message", text: str = "",
                button_text: str = "OK", on_close=None):
    w, h = 300, 150
    x = 170
    y = 165
    panel = Panel(x, y, w, h)
    panel.bg_color = _color_dict(0.2, 0.2, 0.25)
    panel.border_color = _color_dict(0.4, 0.4, 0.5)
    panel.border_width = 2
    tl = Label(10, 10, title, 14)
    tl.color = _color_dict(1.0, 1.0, 1.0)
    panel.add(tl)
    ml = Label(10, 40, text, 12)
    ml.color = _color_dict(0.8, 0.8, 0.8)
    panel.add(ml)
    btn = Button(w / 2 - 40, h - 40, 80, 30, button_text, 12)
    if on_close is not None:
        btn.on_click(lambda w: _call_user_fn(on_close, "OK"))
    panel.add(btn)
    return panel


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
    "TextArea": TextArea,
    "ScrollView": ScrollView,
    "TabContainer": TabContainer,
    "Splitter": Splitter,
    "MenuBar": MenuBar,
    "Menu": Menu,
    "MenuItem": MenuItem,
    "Theme": Theme,
    "default_theme": default_theme,
    "ObservableValue": ObservableValue,
    "bind": bind,
    "message_box": message_box,
    "SIZE_FIXED": SIZE_FIXED,
    "SIZE_FILL": SIZE_FILL,
})
