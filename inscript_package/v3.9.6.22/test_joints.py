# v3.9.6.22 — Physics joints (.py tests)
# Run: python v3.9.6.22/test_joints.py

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

# ── 1. Joint constants ──────────────────────────────
try:
    from physics_engine import (
        JOINT_DISTANCE, JOINT_REVOLUTE, JOINT_PRISMATIC, JOINT_WELD, JOINT_MOUSE
    )
    check("JOINT_DISTANCE == 0", JOINT_DISTANCE == 0)
    check("JOINT_REVOLUTE == 1", JOINT_REVOLUTE == 1)
    check("JOINT_PRISMATIC == 2", JOINT_PRISMATIC == 2)
    check("JOINT_WELD == 3", JOINT_WELD == 3)
    check("JOINT_MOUSE == 4", JOINT_MOUSE == 4)
except Exception as e:
    check("Joint constants", False, str(e))

# ── 2. Distance joint creation ──────────────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC, JOINT_DISTANCE
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, "a", 0, 0)
    b = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, "b", 100, 0)
    j = w.create_joint(JOINT_DISTANCE, a, b, length=100.0, stiffness=1.0, damping=0.1)
    check("joint created", j is not None)
    check("joint type", j.joint_type == JOINT_DISTANCE)
    check("joint length", j.length == 100.0)
    check("joint stiffness", j.stiffness == 1.0)
except Exception as e:
    check("Distance joint creation", False, str(e))

# ── 3. Distance joint applies force ─────────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC, JOINT_DISTANCE
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 10.0, "a", 0, 0)
    b = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 10.0, "b", 100, 0)
    j = w.create_joint(JOINT_DISTANCE, a, b, length=50.0, stiffness=5.0, damping=0.1)
    w.step(0.016)
    # Bodies should be pulled together
    dist_before = abs(a.x - b.x)
    w.step(0.016)
    w.step(0.016)
    dist_after = abs(a.x - b.x)
    check("distance joint pulls bodies together", dist_after < dist_before)
except Exception as e:
    check("Distance joint force", False, str(e))

# ── 4. Revolute joint creation ──────────────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC, JOINT_REVOLUTE
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, "a", 0, 0)
    b = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, "b", 50, 0)
    j = w.create_joint(JOINT_REVOLUTE, a, b,
                       anchor_x=0.0, anchor_y=0.0,
                       lower_angle=-1.0, upper_angle=1.0,
                       enable_motor=False)
    check("revolute joint created", j is not None)
    check("revolute joint type", j.joint_type == JOINT_REVOLUTE)
except Exception as e:
    check("Revolute joint", False, str(e))

# ── 5. Prismatic joint creation ─────────────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC, JOINT_PRISMATIC
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, "a", 0, 0)
    b = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, "b", 0, 50)
    j = w.create_joint(JOINT_PRISMATIC, a, b,
                       axis_x=0.0, axis_y=1.0,
                       lower_limit=0.0, upper_limit=100.0)
    check("prismatic joint created", j is not None)
    check("prismatic joint type", j.joint_type == JOINT_PRISMATIC)
except Exception as e:
    check("Prismatic joint", False, str(e))

# ── 6. Weld joint creation ─────────────────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC, JOINT_WELD
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, "a", 0, 0)
    b = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, "b", 0, 50)
    j = w.create_joint(JOINT_WELD, a, b, stiffness=10.0, damping=0.5)
    check("weld joint created", j is not None)
    check("weld joint type", j.joint_type == JOINT_WELD)
except Exception as e:
    check("Weld joint", False, str(e))

# ── 7. Mouse joint creation ────────────────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC, JOINT_MOUSE
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, "anchor", 0, 0)
    b = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, "target", 100, 0)
    j = w.create_joint(JOINT_MOUSE, a, b,
                       stiffness=10.0, damping=1.0, max_force=100.0)
    check("mouse joint created", j is not None)
    check("mouse joint type", j.joint_type == JOINT_MOUSE)
except Exception as e:
    check("Mouse joint", False, str(e))

# ── 8. Destroy joint ───────────────────────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC, JOINT_DISTANCE
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, "a", 0, 0)
    b = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, "b", 100, 0)
    j = w.create_joint(JOINT_DISTANCE, a, b, length=100.0)
    w.destroy_joint(j)
    check("joint destroyed", j not in w._joints)
except Exception as e:
    check("Destroy joint", False, str(e))

# ── 9. Joint get_attr ──────────────────────────────
try:
    from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC, JOINT_DISTANCE
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, "a", 0, 0)
    b = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, "b", 100, 0)
    j = w.create_joint(JOINT_DISTANCE, a, b, length=80.0, stiffness=2.0, damping=0.1)
    check("get_attr joint_type", j.get_attr("joint_type") == JOINT_DISTANCE)
    check("get_attr length", j.get_attr("length") == 80.0)
    check("get_attr stiffness", j.get_attr("stiffness") == 2.0)
    check("get_attr body_a", j.get_attr("body_a") is a)
    check("get_attr body_b", j.get_attr("body_b") is b)
except Exception as e:
    check("Joint get_attr", False, str(e))

# ── 10. physics_engine.py compiles ─────────────────
try:
    import py_compile
    py_compile.compile(os.path.join(os.path.dirname(__file__), "..", "physics_engine.py"), doraise=True)
    check("physics_engine.py compiles", True)
except Exception as e:
    check("physics_engine.py compiles", False, str(e))

# ── 11. interpreter.py compiles ─────────────────────
try:
    import py_compile
    py_compile.compile(os.path.join(os.path.dirname(__file__), "..", "interpreter.py"), doraise=True)
    check("interpreter.py compiles", True)
except Exception as e:
    check("interpreter.py compiles", False, str(e))

# ── RESULTS ──────────────────────────────────────────
print()
print("=" * 55)
print("  v3.9.6.22 — Physics Joints")
print("=" * 55)
print(f"  {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 55)
if FAIL > 0:
    sys.exit(1)
