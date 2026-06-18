# v3.9.6.23 — Physics: triggers + sensors (.py tests)
# Uses _P2DWorld / _P2DArea from stdlib_game directly.
# Run: python v3.9.6.23/test_triggers_sensors.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

# Load the stdlib modules (register physics2d, physics)
import stdlib  # noqa: F401

from stdlib_game import _P2DWorld, _P2DArea, _P2DRect, _P2DCircle, _P2DBody

PASS, FAIL = 0, 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  {chr(0x2705)} {name}")
        PASS += 1
    else:
        print(f"  {chr(0x274C)} {name}  {detail}")
        FAIL += 1

# ── 1. Area on_overlap callback (backward compat) ──
try:
    w = _P2DWorld(0, 0)
    area = _P2DArea(_P2DRect(50, 50), "zone")
    area.x, area.y = 0, 0
    body = _P2DBody(_P2DRect(16, 16), 1.0, "box")
    body.x, body.y = 25, 25
    w.add(area)
    w.add(body)
    hits = []
    area.on_overlap(lambda a, b: hits.append((a.tag, b.tag)))
    w.step(0.016)
    check("on_overlap fired on overlap", len(hits) > 0)
    check("on_overlap passed correct tags", hits[0] == ("zone", "box"))
except Exception as e:
    check("Area on_overlap", False, str(e))

# ── 2. Area on_trigger_enter fires on entry ─────────
try:
    w = _P2DWorld(0, 0)
    area = _P2DArea(_P2DRect(50, 50), "zone")
    area.x, area.y = 0, 0
    body = _P2DBody(_P2DRect(16, 16), 1.0, "box")
    body.x, body.y = 100, 100  # Outside
    w.add(area)
    w.add(body)
    enters = []
    exits = []
    area.on_trigger_enter(lambda a, b: enters.append((a.tag, b.tag)))
    area.on_trigger_exit(lambda a, b: exits.append((a.tag, b.tag)))
    w.step(0.016)
    check("trigger_enter not called when outside", len(enters) == 0)
    body.x, body.y = 10, 10  # Move inside
    w.step(0.016)
    check("trigger_enter called on entry", len(enters) == 1)
    check("trigger_enter correct tag", enters[0] == ("zone", "box"))
except Exception as e:
    check("Area on_trigger_enter", False, str(e))

# ── 3. Area on_trigger_exit fires on exit ──────────
try:
    w = _P2DWorld(0, 0)
    area = _P2DArea(_P2DRect(50, 50), "zone")
    area.x, area.y = 0, 0
    body = _P2DBody(_P2DRect(16, 16), 1.0, "box")
    body.x, body.y = 10, 10  # Inside
    w.add(area)
    w.add(body)
    enters = []
    exits = []
    area.on_trigger_enter(lambda a, b: enters.append((a.tag, b.tag)))
    area.on_trigger_exit(lambda a, b: exits.append((a.tag, b.tag)))
    w.step(0.016)
    check("trigger_enter called on initial overlap", len(enters) == 1)
    check("exit not yet called", len(exits) == 0)
    body.x, body.y = 100, 100  # Move outside
    w.step(0.016)
    check("trigger_exit called on exit", len(exits) == 1)
    check("trigger_exit correct tag", exits[0] == ("zone", "box"))
except Exception as e:
    check("Area on_trigger_exit", False, str(e))

# ── 4. world.query_area returns overlapping bodies ──
try:
    w = _P2DWorld(0, 0)
    area = _P2DArea(_P2DRect(50, 50), "zone")
    area.x, area.y = 0, 0
    body = _P2DBody(_P2DRect(16, 16), 1.0, "box")
    body.x, body.y = 10, 10
    w.add(area)
    w.add(body)
    result = w.query_area(area)
    check("query_area finds overlapping body", len(result) == 1)
    check("query_area returns correct body", result[0].tag == "box")
    body.x, body.y = 100, 100
    result2 = w.query_area(area)
    check("query_area returns empty after exit", len(result2) == 0)
except Exception as e:
    check("query_area", False, str(e))

# ── 5. query_area with multiple bodies ──────────────
try:
    w = _P2DWorld(0, 0)
    area = _P2DArea(_P2DRect(50, 50), "zone")
    area.x, area.y = 0, 0
    for i in range(5):
        b = _P2DBody(_P2DRect(16, 16), 1.0, f"box{i}")
        b.x, b.y = 10 + i * 5, 10
        w.add(b)
    w.add(area)
    result = w.query_area(area)
    check("query_area finds all overlapping, len=5", len(result) == 5)
except Exception as e:
    check("query_area multiple", False, str(e))

# ── 6. physics.ray_cast (smoke) ─────────────────────
try:
    from stdlib_game import _physics_ray_cast
    w = _P2DWorld(0, 0)
    b = _P2DBody(_P2DRect(20, 20), 0.0, "wall")
    b.x, b.y = 0, 100
    b.is_static = True
    w.add(b)
    result = _physics_ray_cast(w, 0.0, 0.0, 0.0, 1.0, 500.0)
    check("ray_cast hits", result is not None)
    check("ray_cast body tag", result["body"].tag == "wall")
    miss = _physics_ray_cast(w, 0.0, 0.0, 0.0, -1.0, 500.0)
    check("ray_cast miss returns None", miss is None)
except Exception as e:
    check("ray_cast", False, str(e))

# ── 7. physics.shape_cast ──────────────────────────
try:
    from stdlib_game import _physics_shape_cast, _P2DRect
    w = _P2DWorld(0, 0)
    b = _P2DBody(_P2DRect(20, 20), 0.0, "wall")
    b.x, b.y = 0, 100
    b.is_static = True
    w.add(b)
    shape = _P2DRect(10, 10)
    result = _physics_shape_cast(w, shape, 0.0, 0.0, 0.0, 1.0, 500.0)
    check("shape_cast hits", result is not None)
    if result:
        check("shape_cast body tag", result["body"].tag == "wall")
    miss = _physics_shape_cast(w, shape, 0.0, 0.0, 0.0, -1.0, 500.0)
    check("shape_cast miss returns None", miss is None)
except Exception as e:
    check("shape_cast", False, str(e))

# ── 8. shape_cast with circle shape ────────────────
try:
    from stdlib_game import _physics_shape_cast, _P2DCircle
    w = _P2DWorld(0, 0)
    b = _P2DBody(_P2DRect(20, 20), 0.0, "wall")
    b.x, b.y = 0, 100
    b.is_static = True
    w.add(b)
    shape = _P2DCircle(5)
    result = _physics_shape_cast(w, shape, 0.0, 0.0, 0.0, 1.0, 500.0)
    check("circle shape_cast hits", result is not None)
    if result:
        check("circle shape_cast body tag", result["body"].tag == "wall")
except Exception as e:
    check("circle shape_cast", False, str(e))

# ── 9. Physics2D module Area still works ────────────
try:
    from stdlib_game import _P2DWorld, _P2DArea, _P2DRect, _P2DBody
    w2 = _P2DWorld()
    a = _P2DArea(_P2DRect(50, 50), "trigger")
    r = _P2DBody(_P2DRect(16, 16), 1.0, "ball")
    a.x, a.y = 0, 0
    r.x, r.y = 10, 10
    w2.add(a)
    w2.add(r)
    hits = []
    a.on_overlap(lambda *args: hits.append(1))
    w2.step(0.016)
    check("Area on_overlap still works", len(hits) > 0)
except Exception as e:
    check("Area compat", False, str(e))

# ── 10. Area does not collide (sensor property) ────
try:
    w = _P2DWorld(0, 0)
    area = _P2DArea(_P2DRect(50, 50), "zone")
    area.x, area.y = 0, 0
    body = _P2DBody(_P2DRect(16, 16), 1.0, "box")
    body.x, body.y = 25, 25
    body.velocity.x, body.velocity.y = 100, 0
    w.add(area)
    w.add(body)
    pos_before = body.x
    w.step(0.016)
    # Body should pass through area without stopping (sensor)
    moved = abs(body.x - pos_before)
    check("body moves through area (sensor)", moved > 0)
except Exception as e:
    check("Area sensor property", False, str(e))

# ── 11. Dynamic body entering/exiting area ─────────
try:
    w = _P2DWorld(0, 0)
    area = _P2DArea(_P2DRect(40, 40), "zone")
    area.x, area.y = 0, 0
    body = _P2DBody(_P2DRect(16, 16), 1.0, "ball")
    body.x, body.y = -60, 0
    body.velocity.x = 50
    w.add(area)
    w.add(body)
    enters = []
    area.on_trigger_enter(lambda a, b: enters.append(b.tag))
    # Step until entering area
    for _ in range(60):
        w.step(0.016)
    entered = len(enters) > 0
    check("dynamic body triggers enter", entered)
except Exception as e:
    check("dynamic body enter", False, str(e))

# ── RESULTS ──────────────────────────────────────────
print()
print("=" * 55)
print("  v3.9.6.23 — Physics: triggers + sensors")
print("=" * 55)
print(f"  {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 55)
if FAIL > 0:
    sys.exit(1)
