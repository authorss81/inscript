# v3.9.6.20 — Physics Box2D binding (.py tests)
# Run: python v3.9.6.20/test_physics_binding.py

import sys, os, math
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

# ── 1. PhysicsWorld constructible ─────────────────────
try:
    from physics_engine import PhysicsWorld
    w = PhysicsWorld(0, 100)
    check("PhysicsWorld(0, 100)", True)
    check("gravity_x is 0", w.gravity_x == 0)
    check("gravity_y is 100", w.gravity_y == 100)
except Exception as e:
    check("PhysicsWorld constructible", False, str(e))

# ── 2. PhysicsWorld default gravity ──────────────────
try:
    from physics_engine import PhysicsWorld
    w = PhysicsWorld()
    check("default gravity_x is 0", w.gravity_x == 0)
    check("default gravity_y is 500", w.gravity_y == 500)
except Exception as e:
    check("default gravity", False, str(e))

# ── 3. Shape.rect and Shape.circle ───────────────────
try:
    from physics_engine import Shape, SHAPE_RECT, SHAPE_CIRCLE
    r = Shape.rect(32, 48)
    c = Shape.circle(16)
    check("rect shape_type", r.shape_type == SHAPE_RECT)
    check("rect width", r.width == 32)
    check("rect height", r.height == 48)
    check("circle shape_type", c.shape_type == SHAPE_CIRCLE)
    check("circle radius", c.radius == 16)
except Exception as e:
    check("Shape creation", False, str(e))

# ── 4. Body creation with create_body ────────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC, BODY_STATIC
    w = PhysicsWorld()
    s = Shape.rect(32, 32)
    b = w.create_body(s, BODY_DYNAMIC, 1.0, "player", 100, 200)
    check("body x", b.x == 100)
    check("body y", b.y == 200)
    check("body mass", b.mass == 1.0)
    check("body tag", b.tag == "player")
    check("body is_dynamic", b.is_dynamic)
    check("body inertia", b.invmass == 1.0)
except Exception as e:
    check("Body creation", False, str(e))

# ── 5. Static body ──────────────────────────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_STATIC
    w = PhysicsWorld()
    s = Shape.rect(32, 32)
    b = w.create_body(s, BODY_STATIC, 0.0, "wall", 400, 300)
    check("static x", b.x == 400)
    check("static y", b.y == 300)
    check("static mass", b.mass == 0.0)
    check("static invmass", b.invmass == 0.0)
    check("is_static", b.is_static)
except Exception as e:
    check("Static body", False, str(e))

# ── 6. Body attribute get/set ───────────────────────
try:
    from physics_engine import Body, Shape, BODY_DYNAMIC
    s = Shape.rect(32, 32)
    b = Body(s, BODY_DYNAMIC, 1.0)
    b.x = 50
    b.y = 100
    b.vx = 5
    b.vy = -3
    b.restitution = 0.8
    b.friction = 0.3
    check("get_attr x", b.get_attr("x") == 50)
    check("set_attr y", b.y == 100)
    check("get_attr vx", b.get_attr("vx") == 5)
    check("get_attr restitution", b.get_attr("restitution") == 0.8)
    check("set_attr friction", b.friction == 0.3)
except Exception as e:
    check("Body attr", False, str(e))

# ── 7. Body methods ─────────────────────────────────
try:
    from physics_engine import Body, Shape, BODY_DYNAMIC
    s = Shape.rect(32, 32)
    b = Body(s, BODY_DYNAMIC, 2.0)
    b.apply_impulse(10, 0)
    check("apply_impulse vx", abs(b.vx - 5.0) < 0.001)
    b.apply_force(0, -20)
    check("apply_force vy", abs(b.vy - (-10.0)) < 0.001)
    pos = b.get_position()
    check("get_position", pos[0] == 0 and pos[1] == 0)
    b.set_position(300, 400)
    b.set_velocity(1, 2)
    check("set_position x", b.x == 300)
    check("set_velocity vy", b.vy == 2)
except Exception as e:
    check("Body methods", False, str(e))

# ── 8. PhysicsWorld step applies gravity ────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC
    w = PhysicsWorld(0, 100)
    s = Shape.rect(8, 8)
    b = w.create_body(s, BODY_DYNAMIC, 1.0, "fall", 0, 0)
    w.step(0.016)
    check("gravity vy>0", b.vy > 0)
    check("gravity y moved", b.y > 0)
    w.step(0.016)
    check("vy increased", b.vy > 0.5)
except Exception as e:
    check("Gravity step", False, str(e))

# ── 9. Static body does not move ────────────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_STATIC, BODY_DYNAMIC
    w = PhysicsWorld(0, 100)
    wall = w.create_body(Shape.rect(32, 32), BODY_STATIC, 0.0, "wall", 400, 300)
    w.step(0.016)
    check("static x unchanged", wall.x == 400)
    check("static y unchanged", wall.y == 300)
except Exception as e:
    check("Static no move", False, str(e))

# ── 10. Collision detection (two bodies overlapping) ─
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(32, 32), BODY_DYNAMIC, 1.0, "a", 0, 0)
    b = w.create_body(Shape.rect(32, 32), BODY_DYNAMIC, 1.0, "b", 10, 0)
    contacted = []
    w.on_begin_contact(lambda a_, b_, c: contacted.append((a_.tag, b_.tag)))
    w.step(0.016)
    check("contact detected", len(contacted) > 0)
    if contacted:
        check("contact has tags", contacted[0] == ("a", "b") or contacted[0] == ("b", "a"))
except Exception as e:
    check("Collision detection", False, str(e))

# ── 11. Body count ──────────────────────────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC
    w = PhysicsWorld()
    w.create_body(Shape.rect(8, 8), BODY_DYNAMIC, 1.0)
    w.create_body(Shape.rect(8, 8), BODY_DYNAMIC, 1.0)
    check("body_count", w.body_count() == 2)
except Exception as e:
    check("Body count", False, str(e))

# ── 12. find_body_by_tag ────────────────────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC
    w = PhysicsWorld()
    b = w.create_body(Shape.rect(8, 8), BODY_DYNAMIC, 1.0, "target")
    found = w.find_body_by_tag("target")
    check("find body by tag", found is b)
    check("not found", w.find_body_by_tag("nope") is None)
except Exception as e:
    check("find_body_by_tag", False, str(e))

# ── 13. Destroy body ────────────────────────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC
    w = PhysicsWorld()
    b = w.create_body(Shape.rect(8, 8), BODY_DYNAMIC, 1.0)
    check("body alive before destroy", b._alive)
    w.destroy_body(b)
    check("body removed from world", w.body_count() == 0)
    check("body marked dead", not b._alive)
except Exception as e:
    check("Destroy body", False, str(e))

# ── 14. get_bodies ──────────────────────────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC
    w = PhysicsWorld()
    w.create_body(Shape.rect(8, 8), BODY_DYNAMIC, 1.0, "a")
    w.create_body(Shape.rect(8, 8), BODY_DYNAMIC, 1.0, "b")
    bodies = w.get_bodies()
    check("get_bodies count", len(bodies) == 2)
except Exception as e:
    check("get_bodies", False, str(e))

# ── 15. PhysicsWorld get_attr/set_attr ──────────────
try:
    from physics_engine import PhysicsWorld
    w = PhysicsWorld(0, 500)
    check("get_attr gravity_x", w.get_attr("gravity_x") == 0)
    check("get_attr gravity_y", w.get_attr("gravity_y") == 500)
    w.set_attr("gravity_x", 100)
    check("set_attr gravity_x", w.gravity_x == 100)
except Exception as e:
    check("World get_attr/set_attr", False, str(e))

# ── 16. debugger.py and interpreter.py compile ──────
try:
    import py_compile
    py_compile.compile(os.path.join(os.path.dirname(__file__), "..", "physics_engine.py"), doraise=True)
    check("physics_engine.py compiles", True)
except Exception as e:
    check("physics_engine.py compiles", False, str(e))

# ── RESULTS ──────────────────────────────────────────
print()
print("=" * 55)
print("  v3.9.6.20 — Physics Box2D Binding")
print("=" * 55)
print(f"  {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 55)
if FAIL > 0:
    sys.exit(1)
