import sys, os, tempfile, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import stdlib_gui as gui
from stdlib import load_module

# 1. Verify module registration
ns = load_module('gui')
assert 'Stylesheet' in ns
assert 'load_stylesheet' in ns

# 2. Stylesheet basic
ss = gui.Stylesheet()
ss.add_rule('Button', {'rounded_radius': 10, 'bg_color': {'r': 0.5, 'g': 0.5, 'b': 0.5}})
assert ss.get_rule('Button', 'rounded_radius') == 10

# 3. Stylesheet + no theme = stylesheet wins
btn = gui.Button(0, 0, 100, 30, 'test', 16)
btn.set_attr('theme', None)
btn.stylesheet = ss
btn._init_theme()
assert btn.rounded_radius == 10, f'expected 10 got {btn.rounded_radius}'
assert btn.bg_color == {'r': 0.5, 'g': 0.5, 'b': 0.5}

# 4. Stylesheet + theme = theme overrides
btn2 = gui.Button(0, 0, 100, 30, 'test2', 16)
btn2.set_attr('theme', None)
btn2.stylesheet = ss
theme = gui.Theme()
theme.set_style('Button', {'rounded_radius': 25, 'text_color': {'r': 1, 'g': 1, 'b': 1}})
btn2.theme = theme
btn2._init_theme()
assert btn2.rounded_radius == 25, f'theme should override stylesheet: {btn2.rounded_radius}'
assert btn2.bg_color == {'r': 0.5, 'g': 0.5, 'b': 0.5}

# 5. User-set attr = highest priority
btn3 = gui.Button(0, 0, 100, 30, 'test3', 16)
btn3.set_attr('rounded_radius', 99)
btn3.theme = theme
btn3.stylesheet = ss
btn3._init_theme()
assert btn3.rounded_radius == 99, f'user attr should override: {btn3.rounded_radius}'

# 6. Gradient attrs on Panel
pn = gui.Panel(0, 0, 200, 100)
assert pn.gradient_top is None
assert pn.gradient_bottom is None
pn.set_attr('gradient_top', {'r': 0.2, 'g': 0.3, 'b': 0.5})
pn.set_attr('gradient_bottom', {'r': 0.05, 'g': 0.1, 'b': 0.2})
assert pn.gradient_top == {'r': 0.2, 'g': 0.3, 'b': 0.5}
assert pn.gradient_bottom == {'r': 0.05, 'g': 0.1, 'b': 0.2}

# 7. Stylesheet apply_to theme
theme2 = gui.Theme()
ss2 = gui.Stylesheet()
ss2.add_rule('Panel', {'bg_color': {'r': 0.1, 'g': 0.1, 'b': 0.15}, 'border_width': 2})
ss2.apply_to(theme2)
assert theme2.get_style('Panel', 'bg_color') == {'r': 0.1, 'g': 0.1, 'b': 0.15}
assert theme2.get_style('Panel', 'border_width') == 2

# 8. File load
content = """Button {
    bg_color: {"r": 0.3, "g": 0.3, "b": 0.35};
    rounded_radius: 8;
}

Panel {
    bg_color: {"r": 0.1, "g": 0.1, "b": 0.15};
    gradient_top: {"r": 0.2, "g": 0.3, "b": 0.5};
    gradient_bottom: {"r": 0.05, "g": 0.1, "b": 0.2};
}
"""
with tempfile.NamedTemporaryFile(mode='w', suffix='.insstyle', delete=False, encoding='utf-8') as f:
    f.write(content)
    tmppath = f.name
ss3 = gui.load_stylesheet(tmppath)
assert ss3 is not None
rules = ss3.rules()
assert 'Button' in rules, f'missing Button: {list(rules.keys())}'
assert rules['Button']['rounded_radius'] == 8
assert 'Panel' in rules
assert rules['Panel']['gradient_top'] == {'r': 0.2, 'g': 0.3, 'b': 0.5}
assert rules['Panel']['gradient_bottom'] == {'r': 0.05, 'g': 0.1, 'b': 0.2}
os.unlink(tmppath)

# 9. load_stylesheet returns None for non-existent file
ss4 = gui.load_stylesheet('/nonexistent/path.style')
assert ss4 is None

# 10. Comment lines are ignored
content2 = """# This is a comment
// This is also a comment
Button {
    rounded_radius: 12;
}
"""
with tempfile.NamedTemporaryFile(mode='w', suffix='.insstyle', delete=False, encoding='utf-8') as f:
    f.write(content2)
    tmppath2 = f.name
ss5 = gui.load_stylesheet(tmppath2)
assert ss5 is not None
rules5 = ss5.rules()
assert 'Button' in rules5
assert rules5['Button']['rounded_radius'] == 12
os.unlink(tmppath2)

# 11. Empty file
with tempfile.NamedTemporaryFile(mode='w', suffix='.insstyle', delete=False, encoding='utf-8') as f:
    f.write("")
    tmppath3 = f.name
ss6 = gui.load_stylesheet(tmppath3)
assert ss6 is not None
assert ss6.rules() == {}
os.unlink(tmppath3)

# 12. gradient_rect exists on draw namespace
import pygame_backend
assert hasattr(pygame_backend.DrawNamespace, 'gradient_rect')
assert hasattr(pygame_backend.BatchedDrawNamespace, 'gradient_rect')

# 13. Theme.apply_to respects _user_attrs
theme3 = gui.Theme()
theme3.set_style('Button', {'bg_color': {'r': 1, 'g': 0, 'b': 0}, 'rounded_radius': 50})
btn4 = gui.Button(0, 0, 100, 30, 'test4', 16)
btn4.set_attr('rounded_radius', 77)
btn4.set_attr('theme', theme3)
btn4._init_theme()
assert btn4.rounded_radius == 77, f'user attr preserved: {btn4.rounded_radius}'
assert btn4.bg_color == {'r': 1, 'g': 0, 'b': 0}

print("All 13 v3.9.6.39 Python validations passed")
