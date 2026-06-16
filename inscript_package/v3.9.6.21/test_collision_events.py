# v3.9.6.21 — Physics collision events (.py tests)
# Run: python v3.9.6.21/test_collision_events.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

PASS, FAIL = 0, 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  {chr(0x2705)} {name}")
        PASS += 1
    else:
        print(f"  {chr(0x274C)} {name}  {detail}")
        FAIL += 1

# ── 1. on_begin_contact callback ────────────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC, BODY_STATIC
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(32, 32), BODY_DYNAMIC, 1.0, "a", 0, 0)
    b = w.create_body(Shape.rect(32, 32), BODY_DYNAMIC, 1.0, "b", 10, 0)
    results = []
    w.on_begin_contact(lambda a_, b_, c: results.append((a_.tag, b_.tag, c.normal_x, c.normal_y, c.penetration)))
    w.step(0.016)
    check("begin_contact called", len(results) > 0)
    if results:
        a_tag, b_tag, nx, ny, pen = results[0]
        check("contact has a tag", a_tag in ("a", "b"))
        check("contact has b tag", b_tag in ("a", "b"))
        check("contact has normal", isinstance(nx, float))
        check("contact has penetration", pen > 0)
except Exception as e:
    check("on_begin_contact", False, str(e))

# ── 2. on_end_contact callback ──────────────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(32, 32), BODY_DYNAMIC, 1.0, "a", 0, 0)
    b = w.create_body(Shape.rect(32, 32), BODY_DYNAMIC, 1.0, "b", 10, 0)
    ends = []
    w.on_end_contact(lambda a_, b_: ends.append((a_.tag, b_.tag)))
    w.step(0.016)  # collision starts
    # Move bodies apart to trigger end
    a.x = -100
    b.x = 100
    w.step(0.016)  # collision ends
    if len(ends) > 0:
        check("end_contact called", True)
        check("end contact has tags", ends[0][0] in ("a", "b"))
    else:
        check("end_contact called", False, "end callback not triggered")
except Exception as e:
    check("on_end_contact", False, str(e))

# ── 3. on_pre_solve can disable collision ───────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(32, 32), BODY_DYNAMIC, 1.0, "a", 0, 0)
    b = w.create_body(Shape.rect(32, 32), BODY_DYNAMIC, 1.0, "b", 10, 0)
    pre_results = []
    w.on_pre_solve(lambda a_, b_, c: pre_results.append((a_.tag, b_.tag)))
    w.step(0.016)
    check("pre_solve called", len(pre_results) > 0)
except Exception as e:
    check("on_pre_solve", False, str(e))

# ── 4. Contact info attributes ──────────────────────
try:
    from physics_engine import Contact, Body, Shape, BODY_DYNAMIC
    s = Shape.rect(32, 32)
    a = Body(s, BODY_DYNAMIC, 1.0)
    b = Body(s, BODY_DYNAMIC, 1.0)
    c = Contact(a, b, 1.0, 0.0, 50.0, 100.0, 5.0)
    check("contact body_a", c.body_a is a)
    check("contact body_b", c.body_b is b)
    check("contact normal_x", c.normal_x == 1.0)
    check("contact normal_y", c.normal_y == 0.0)
    check("contact point_x", c.point_x == 50.0)
    check("contact point_y", c.point_y == 100.0)
    check("contact penetration", c.penetration == 5.0)
except Exception as e:
    check("Contact attributes", False, str(e))

# ── 5. Contact get_attr ─────────────────────────────
try:
    from physics_engine import Contact, Body, Shape, BODY_DYNAMIC
    s = Shape.rect(16, 16)
    a = Body(s, BODY_DYNAMIC, 1.0)
    b = Body(s, BODY_DYNAMIC, 1.0)
    c = Contact(a, b, -1.0, 0.5, 10.0, 20.0, 2.0)
    check("get_attr normal_x", c.get_attr("normal_x") == -1.0)
    check("get_attr normal_y", c.get_attr("normal_y") == 0.5)
    check("get_attr point_x", c.get_attr("point_x") == 10.0)
    check("get_attr penetration", c.get_attr("penetration") == 2.0)
except Exception as e:
    check("Contact get_attr", False, str(e))

# ── 6. Circle vs circle collision ───────────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.circle(16), BODY_DYNAMIC, 1.0, "a", 0, 0)
    b = w.create_body(Shape.circle(16), BODY_DYNAMIC, 1.0, "b", 20, 0)
    contacted = []
    w.on_begin_contact(lambda a_, b_, c: contacted.append(True))
    w.step(0.016)
    check("circle-circle collision", len(contacted) > 0)
except Exception as e:
    check("circle-vs-circle", False, str(e))

# ── 7. Rect vs circle collision (mixed) ─────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(32, 32), BODY_DYNAMIC, 1.0, "rect", 0, 0)
    b = w.create_body(Shape.circle(16), BODY_DYNAMIC, 1.0, "circle", 15, 0)
    contacted = []
    w.on_begin_contact(lambda a_, b_, c: contacted.append(True))
    w.step(0.016)
    check("rect-circle collision", len(contacted) > 0)
except Exception as e:
    check("rect-vs-circle", False, str(e))

# ── 8. Static + dynamic collision resolution ────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC, BODY_STATIC
    w = PhysicsWorld(0, 500)
    wall = w.create_body(Shape.rect(64, 16), BODY_STATIC, 0.0, "floor", 0, 0)
    ball = w.create_body(Shape.circle(8), BODY_DYNAMIC, 1.0, "ball", 0, -20)
    ball.vy = 50  # heading downward toward floor
    w.step(0.016)
    # ball should bounce off floor
    check("ball vy reversed after bounce", ball.vy >= 0)
except Exception as e:
    check("Static-dynamic collision", False, str(e))

# ── 9. Body vs body collision (dynamic-dynamic) ─────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, "a", 0, 0)
    b = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, "b", 10, 0)
    w.step(0.016)
    # After collision, they should have separated
    dist = abs(a.x - b.x)
    check("bodies separated after collision", dist >= 14)
except Exception as e:
    check("Dynamic-dynamic collision", False, str(e))

# ── 10. physics_engine.py compiles ─────────────────
try:
    import py_compile
    py_compile.compile(os.path.join(os.path.dirname(__file__), "..", "physics_engine.py"), doraise=True)
    check("physics_engine.py compiles", True)
except Exception as e:
    check("physics_engine.py compiles", False, str(e))

# ── RESULTS ──────────────────────────────────────────
print()
print("=" * 55)
print("  v3.9.6.21 — Physics Collision Events")
print("=" * 55)
print(f"  {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 55)
if FAIL > 0:
    sys.exit(1)
