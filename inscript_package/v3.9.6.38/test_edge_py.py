import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import stdlib_gui as gui

# ── ListModel Python-level edge cases ────────────────────────────────────────

# 1. Verify ListModel class exists and is callable
lm = gui.ListModel()
assert lm.len() == 0
assert isinstance(lm.get(), list)
assert lm.get() == []

# 2. None items
lm2 = gui.ListModel(None)
assert lm2.len() == 0
assert lm2.get() == []

# 3. set_attr with items_json (valid JSON)
lm3 = gui.ListModel()
lm3.set_attr("items_json", '[1, 2, 3]')
assert lm3.len() == 3
assert lm3.get() == [1, 2, 3]

# 4. set_attr with items_json (invalid JSON — silently ignored)
lm4 = gui.ListModel(["keep"])
lm4.set_attr("items_json", "not-json")
assert lm4.len() == 1  # unchanged since parsing failed
assert lm4.get_at(0) == "keep"

# 5. set_attr with items_json (non-string)
lm5 = gui.ListModel()
lm5.set_attr("items_json", [5, 6])
assert lm5.len() == 2
assert lm5.get() == [5, 6]

# 6. Multiple on_change callbacks fire in order
lm6 = gui.ListModel(["x"])
order = []
lm6.on_change(lambda items: order.append("a"))
lm6.on_change(lambda items: order.append("b"))
lm6.add("y")
assert order == ["a", "b"], f"order={order}"

# 7. Removing from empty model is no-op
lm7 = gui.ListModel()
lm7.remove("x")  # should not raise
lm7.remove_at(0)  # should not raise
lm7.clear()  # should not raise

# 8. filter with predicate returning wrong type
lm8 = gui.ListModel([1, 2, 3])
try:
    lm8.filter(lambda x: "hello")  # truthy string, all pass
    assert lm8.len() == 3
except Exception:
    assert False, "filter with string predicate should not raise"

# 9. map returning None transforms item to None
lm9 = gui.ListModel([1, 2, 3])
lm9.map(lambda x: None if x == 2 else x)
assert lm9.len() == 3
assert lm9.get_at(0) == 1
assert lm9.get_at(1) is None
assert lm9.get_at(2) == 3

# ── file_picker Python-level edge cases ──────────────────────────────────────

# 10. file_picker exists and is callable
assert callable(gui.file_picker)

# 11. color_picker exists and is callable
assert callable(gui.color_picker)

# 12. Verify default parameters
import inspect
sig = inspect.signature(gui.file_picker)
defaults = {
    k: v.default
    for k, v in sig.parameters.items()
    if v.default is not inspect.Parameter.empty
}
assert defaults.get("title") == "Open File"
assert defaults.get("mode") == "open"

sig2 = inspect.signature(gui.color_picker)
defaults2 = {
    k: v.default
    for k, v in sig2.parameters.items()
    if v.default is not inspect.Parameter.empty
}
assert defaults2.get("title") == "Pick Color"
assert defaults2.get("initial_color") is None

# ── to_dropdown_options Python edge cases ─────────────────────────────────────

# 13. Dict items pass through unchanged
lm13 = gui.ListModel([{"label": "A", "value": 1}, {"label": "B", "value": 2}])
opts = lm13.to_dropdown_options()
assert opts == [{"label": "A", "value": 1}, {"label": "B", "value": 2}]

# 14. Non-dict items get wrapped with label/value
lm14 = gui.ListModel([42, "hello", True])
opts14 = lm14.to_dropdown_options()
assert opts14 == [
    {"label": "42", "value": 42},
    {"label": "hello", "value": "hello"},
    {"label": "True", "value": True},
]

# 15. Empty model to_dropdown_options
lm15 = gui.ListModel()
assert lm15.to_dropdown_options() == []

# ── set_attr error cases ──────────────────────────────────────────────────────

# 16. ListModel set_attr with unknown attr raises
try:
    lm16 = gui.ListModel()
    lm16.set_attr("nonexistent", 42)
    assert False, "should have raised"
except AttributeError as e:
    assert "ListModel has no settable attribute" in str(e)

# 17. ObservableValue set_attr with unknown attr raises
try:
    ov = gui.ObservableValue(42)
    ov.set_attr("nonexistent", 42)
    assert False, "should have raised"
except AttributeError as e:
    assert "ObservableValue has no settable attribute" in str(e)

# 18. Bind function works with ListModel
lm18 = gui.ListModel(["hello"])
captured = []
lm18.on_change(lambda v: captured.append(True))
gui.bind(lm18, "value", gui.ObservableValue("world"))
# bind does a set on the observable which doesn't affect listmodel directly
# but listmodel's on_change should fire when listmodel itself changes
lm18.add("world2")
assert len(captured) == 1


print("All 18 Python-level edge case tests passed")
