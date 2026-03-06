# inscript/test_stdlib.py  — Phase 5: Standard Library Tests
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from interpreter import run, Interpreter
from parser import parse
import stdlib

PASS, FAIL = "✅", "❌"
results = []

def test(name, fn):
    try: fn(); results.append((PASS, name))
    except Exception as e: results.append((FAIL, name, str(e)[:100]))

def R(src):
    prog = parse(src)
    i = Interpreter(src.splitlines())
    i.run(prog)
    return i

# ── math module ────────────────────────────────────────────────────────────
def t_math_import():
    i = R('import "math"\nlet pi = PI')
    assert abs(i._env.get("pi") - 3.14159) < 0.001
test("import math → PI accessible", t_math_import)

def t_math_as():
    i = R('import "math" as M\nlet pi = M["PI"]')
    assert abs(i._env.get("pi") - 3.14159) < 0.001
test("import math as M → M[PI]", t_math_as)

def t_math_from():
    i = R('from "math" import sin\nlet s = sin(0)')
    assert abs(i._env.get("s")) < 1e-9
test('from "math" import sin', t_math_from)

def t_math_smoothstep():
    i = R('from "math" import smoothstep\nlet v = smoothstep(0.0, 1.0, 0.5)')
    assert abs(i._env.get("v") - 0.5) < 0.01
test("math.smoothstep(0,1,0.5) ≈ 0.5", t_math_smoothstep)

def t_math_clamp():
    i = R('import "math"\nlet v = clamp(15.0, 0.0, 10.0)')
    assert i._env.get("v") == 10.0
test("math.clamp(15,0,10)=10", t_math_clamp)

# ── string module ──────────────────────────────────────────────────────────
def t_string_format():
    i = R('import "string"\nlet s = format("Hello {}!", "World")')
    assert i._env.get("s") == "Hello World!"
test("string.format", t_string_format)

def t_string_pad_left():
    i = R('import "string"\nlet s = pad_left("42", 5, "0")')
    assert i._env.get("s") == "00042"
test("string.pad_left", t_string_pad_left)

def t_string_reverse():
    i = R('import "string"\nlet s = reverse("hello")')
    assert i._env.get("s") == "olleh"
test("string.reverse", t_string_reverse)

def t_string_char_code():
    i = R('import "string"\nlet c = char_code("A")')
    assert i._env.get("c") == 65
test("string.char_code", t_string_char_code)

def t_from_code():
    i = R('import "string"\nlet c = from_code(65)')
    assert i._env.get("c") == "A"
test("string.from_code", t_from_code)

# ── array module ───────────────────────────────────────────────────────────
def t_array_sort():
    i = R('import "array"\nlet a = sort([3,1,4,1,5,9,2,6])')
    assert i._env.get("a") == [1,1,2,3,4,5,6,9]
test("array.sort", t_array_sort)

def t_array_unique():
    i = R('import "array"\nlet a = unique([1,2,2,3,1,4])')
    assert i._env.get("a") == [1,2,3,4]
test("array.unique", t_array_unique)

def t_array_flatten():
    i = R('import "array"\nlet a = flatten([[1,2],[3,[4,5]]])')
    assert i._env.get("a") == [1,2,3,4,5]
test("array.flatten", t_array_flatten)

def t_array_sum():
    i = R('import "array"\nlet s = sum([1,2,3,4,5])')
    assert i._env.get("s") == 15
test("array.sum", t_array_sum)

def t_array_average():
    i = R('import "array"\nlet v = average([1.0,2.0,3.0])')
    assert abs(i._env.get("v") - 2.0) < 1e-9
test("array.average", t_array_average)

def t_array_chunk():
    i = R('import "array"\nlet c = chunk([1,2,3,4,5,6], 2)')
    assert i._env.get("c") == [[1,2],[3,4],[5,6]]
test("array.chunk", t_array_chunk)

def t_array_range():
    i = R('import "array"\nlet a = range(5)')
    assert i._env.get("a") == [0,1,2,3,4]
test("array.range(5)", t_array_range)

def t_array_zip():
    i = R('import "array"\nlet z = zip([1,2,3], [4,5,6])')
    assert i._env.get("z") == [[1,4],[2,5],[3,6]]
test("array.zip", t_array_zip)

def t_array_take():
    i = R('import "array"\nlet a = take([1,2,3,4,5], 3)')
    assert i._env.get("a") == [1,2,3]
test("array.take", t_array_take)

def t_array_all():
    i = R('import "array"\nlet v = all([2,4,6], |x| x % 2 == 0)')
    assert i._env.get("v") is True
test("array.all with lambda", t_array_all)

def t_array_any():
    i = R('import "array"\nlet v = any([1,3,4], |x| x % 2 == 0)')
    assert i._env.get("v") is True
test("array.any with lambda", t_array_any)

# ── io module ──────────────────────────────────────────────────────────────
def t_io_write_read():
    import tempfile
    path = tempfile.mktemp(suffix=".txt").replace("\\", "/")
    src = f'import "io"\nwrite_file("{path}", "hello inscript")\nlet content = read_file("{path}")'
    i = R(src)
    assert i._env.get("content") == "hello inscript"
    os.unlink(path)
test("io.write_file + read_file", t_io_write_read)

def t_io_read_lines():
    import tempfile
    path = tempfile.mktemp(suffix=".txt").replace("\\", "/")
    with open(path, "w") as f: f.write("line1\nline2\nline3")
    src = f'import "io"\nlet lines = read_lines("{path}")'
    i = R(src)
    assert i._env.get("lines") == ["line1","line2","line3"]
    os.unlink(path)
test("io.read_lines", t_io_read_lines)

# ── json module ────────────────────────────────────────────────────────────
def t_json_encode():
    i = R('import "json"\nlet s = encode({"name": "Alice", "age": 30})')
    import json
    d = json.loads(i._env.get("s"))
    assert d["name"] == "Alice" and d["age"] == 30
test("json.encode", t_json_encode)

def t_json_decode():
    i = R('import "json"\nlet d = decode("{\\\"x\\\": 42}")')
    assert i._env.get("d")["x"] == 42
test("json.decode", t_json_decode)

# ── random module ──────────────────────────────────────────────────────────
def t_random_float():
    i = R('import "random"\nlet r = float()')
    v = i._env.get("r")
    assert 0.0 <= v <= 1.0
test("random.float() in [0,1]", t_random_float)

def t_random_int():
    i = R('import "random"\nlet r = int(1, 10)')
    v = i._env.get("r")
    assert 1 <= v <= 10
test("random.int(1,10) in range", t_random_int)

def t_random_choice():
    i = R('import "random"\nlet r = choice([1,2,3,4,5])')
    v = i._env.get("r")
    assert v in [1,2,3,4,5]
test("random.choice", t_random_choice)

def t_random_shuffle():
    i = R('import "random"\nlet a = [1,2,3,4,5]\nlet b = shuffle(a)')
    v = i._env.get("b")
    assert sorted(v) == [1,2,3,4,5]
test("random.shuffle", t_random_shuffle)

# ── color module ───────────────────────────────────────────────────────────
def t_color_rgb():
    from stdlib_values import Color
    i = R('import "color"\nlet c = rgb(1.0, 0.0, 0.0)')
    c = i._env.get("c")
    assert c.r == 1.0 and c.g == 0.0
test("color.rgb", t_color_rgb)

def t_color_hsv():
    from stdlib_values import Color
    i = R('import "color"\nlet c = hsv(0.0, 1.0, 1.0)')
    c = i._env.get("c")
    assert c.r > 0.9  # red
test("color.hsv(0,1,1) = red", t_color_hsv)

def t_color_invert():
    from stdlib_values import Color
    i = R('import "color"\nlet c = invert(WHITE)')
    c = i._env.get("c")
    assert c.r < 0.01  # inverted white = black
test("color.invert(WHITE) = black", t_color_invert)

def t_color_hex():
    i = R('import "color"\nlet h = to_hex(RED)')
    assert i._env.get("h") == "#ff0000"
test("color.to_hex(RED) = #ff0000", t_color_hex)

# ── tween module ───────────────────────────────────────────────────────────
def t_tween_linear():
    i = R('import "tween"\nlet v = tween(0.0, 100.0, 0.5, linear)')
    assert abs(i._env.get("v") - 50.0) < 0.01
test("tween.linear 0→100 at t=0.5", t_tween_linear)

def t_tween_ease_out():
    i = R('import "tween"\nlet v = tween(0.0, 100.0, 0.5, ease_out)')
    v = i._env.get("v")
    assert v > 50.0  # ease_out accelerates early
test("tween.ease_out > 50 at t=0.5", t_tween_ease_out)

def t_tween_bounce():
    i = R('import "tween"\nlet t_val = ease_out_bounce(1.0)')
    assert abs(i._env.get("t_val") - 1.0) < 0.01
test("tween.ease_out_bounce(1.0)=1.0", t_tween_bounce)

# ── grid module ────────────────────────────────────────────────────────────
def t_grid_create():
    from stdlib import load_module
    grid_mod = load_module("grid")
    g = grid_mod["make"](10, 10, 0)
    assert g.cols == 10 and g.rows == 10
test("grid.make(10,10)", t_grid_create)

def t_grid_set_get():
    from stdlib import load_module
    grid_mod = load_module("grid")
    g = grid_mod["make"](5, 5, 0)
    g.set(2, 3, 42)
    assert g.get(2, 3) == 42
test("grid.set/get", t_grid_set_get)

def t_grid_neighbors():
    from stdlib import load_module
    grid_mod = load_module("grid")
    g = grid_mod["make"](5, 5, 0)
    n = g.neighbors_4(2, 2)
    assert len(n) == 4
test("grid.neighbors_4 = 4 neighbors", t_grid_neighbors)

def t_grid_manhattan():
    from stdlib import load_module
    grid_mod = load_module("grid")
    dist = grid_mod["manhattan"](0, 0, 3, 4)
    assert dist == 7
test("grid.manhattan(0,0,3,4)=7", t_grid_manhattan)

# ── events module ─────────────────────────────────────────────────────────
def t_events_on_emit():
    from stdlib import load_module
    ev = load_module("events")
    bus = ev["EventBus"]()
    results_list = []
    bus.on("jump", lambda h: results_list.append(h))
    bus.emit("jump", 200)
    assert results_list == [200]
test("events.EventBus on+emit", t_events_on_emit)

def t_events_once():
    from stdlib import load_module
    ev = load_module("events")
    bus = ev["EventBus"]()
    fired = []
    bus.once("hit", lambda dmg: fired.append(dmg))
    bus.emit("hit", 10)
    bus.emit("hit", 20)  # should not fire again
    assert fired == [10]
test("events.once fires only once", t_events_once)

# ── debug module ───────────────────────────────────────────────────────────
def t_debug_assert():
    from stdlib import load_module
    db = load_module("debug")
    db["assert"](True, "should pass")
test("debug.assert(True) passes", t_debug_assert)

def t_debug_assert_fail():
    from stdlib import load_module
    db = load_module("debug")
    try:
        db["assert"](False, "should fail")
        assert False, "should have raised"
    except Exception as e:
        assert "should fail" in str(e)
test("debug.assert(False) raises", t_debug_assert_fail)

def t_debug_assert_eq():
    from stdlib import load_module
    db = load_module("debug")
    db["assert_eq"](42, 42)
test("debug.assert_eq(42,42) passes", t_debug_assert_eq)


# ── Results ────────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("  InScript Standard Library — Test Results")
print("="*65)
passed = failed = 0
for r in results:
    if r[0] == PASS:
        print(f"  {r[0]} {r[1]}"); passed += 1
    else:
        print(f"  {r[0]} {r[1]}"); print(f"       └─ {r[2]}"); failed += 1
print("="*65)
print(f"  {passed} passed, {failed} failed out of {len(results)} tests")
print("="*65 + "\n")
if failed: sys.exit(1)
