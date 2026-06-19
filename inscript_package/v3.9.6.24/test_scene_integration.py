# v3.9.6.24 — Physics: scene integration (.py tests)
# Run: python v3.9.6.24/test_scene_integration.py

import sys, os, tempfile, json, math
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

# ── 1. Density property on Body ────────────────────
from physics_engine import PhysicsWorld, Shape, Body, BODY_DYNAMIC, BODY_STATIC

try:
    b = Body(Shape.rect(10, 10), BODY_DYNAMIC, 1.0)
    check("Body has density attribute", hasattr(b, 'density'))
    check("Body default density == 1.0", b.density == 1.0)
except Exception as e:
    check("Body density property", False, str(e))

# ── 2. create_body with density parameter ─────────
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(10, 10), BODY_DYNAMIC, 1.0, "test", 0, 0, density=2.5)
    check("create_body density stored", b.density == 2.5)
except Exception as e:
    check("create_body density", False, str(e))

# ── 3. Friction stored and accessible ─────────────
try:
    b = Body(Shape.rect(10, 10), BODY_DYNAMIC, 1.0)
    check("Body friction default == 0.5", b.friction == 0.5)
    b.friction = 0.9
    check("Body friction set to 0.9", b.friction == 0.9)
except Exception as e:
    check("Body friction", False, str(e))

# ── 4. Friction used in collision resolution ──────
try:
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(20, 20), BODY_DYNAMIC, 1.0, "a", 0, 0)
    b = w.create_body(Shape.rect(20, 20), BODY_STATIC, 0.0, "b", 15, 0)
    a.vx, a.vy = 10.0, 0.0
    w.step(0.016)
    check("Friction slows body on collision", a.vx < 10.0)
except Exception as e:
    check("Friction in collision", False, str(e))

# ── 5. Friction zero vs non-zero comparison ─────
try:
    w_slick = PhysicsWorld(0, 0)
    w_sticky = PhysicsWorld(0, 0)
    a_slick = w_slick.create_body(Shape.rect(20, 20), BODY_DYNAMIC, 1.0, "slick", 8, 0)
    a_slick.friction = 0.0
    wall_slick = w_slick.create_body(Shape.rect(20, 20), BODY_STATIC, 0.0, "wall", 0, 0)
    wall_slick.friction = 0.0
    a_sticky = w_sticky.create_body(Shape.rect(20, 20), BODY_DYNAMIC, 1.0, "sticky", 8, 0)
    a_sticky.friction = 1.0
    wall_sticky = w_sticky.create_body(Shape.rect(20, 20), BODY_STATIC, 0.0, "wall", 0, 0)
    wall_sticky.friction = 1.0
    a_slick.vx, a_slick.vy = -10.0, 5.0
    a_sticky.vx, a_sticky.vy = -10.0, 5.0
    w_slick.step(0.016)
    w_sticky.step(0.016)
    check("Zero friction preserves more tangential slide than high friction",
          abs(a_slick.vy) > abs(a_sticky.vy))
except Exception as e:
    check("Friction comparison", False, str(e))

# ── 6. get_attr/set_attr density ─────────────────
try:
    b = Body(Shape.rect(10, 10), BODY_DYNAMIC, 1.0)
    check("get_attr density", b.get_attr("density") == 1.0)
    b.set_attr("density", 3.0)
    check("set_attr density", b.get_attr("density") == 3.0)
except Exception as e:
    check("get/set_attr density", False, str(e))

# ── 7. get_attr/set_attr friction ─────────────────
try:
    b = Body(Shape.rect(10, 10), BODY_DYNAMIC, 1.0)
    check("get_attr friction", b.get_attr("friction") == 0.5)
    b.set_attr("friction", 0.1)
    check("set_attr friction", b.get_attr("friction") == 0.1)
except Exception as e:
    check("get/set_attr friction", False, str(e))

# ── 8. World.to_dict serialization ───────────────
try:
    w = PhysicsWorld(0, 500)
    w.create_body(Shape.rect(32, 32), BODY_DYNAMIC, 2.0, "player", 100, 200, density=1.5)
    w.create_body(Shape.rect(16, 16), BODY_STATIC, 0.0, "wall", 300, 200)
    d = w.to_dict()
    check("to_dict gravity_x", d["gravity_x"] == 0.0)
    check("to_dict gravity_y", d["gravity_y"] == 500.0)
    check("to_dict 2 bodies", len(d["bodies"]) == 2)
    check("to_dict body.tag player", d["bodies"][0]["tag"] == "player")
    check("to_dict body.density 1.5", d["bodies"][0]["density"] == 1.5)
    check("to_dict body.shape rect", d["bodies"][0]["shape"]["type"] == "rect")
    check("to_dict body.x 100", d["bodies"][0]["x"] == 100.0)
    check("to_dict body.vx 0", d["bodies"][0]["vx"] == 0.0)
except Exception as e:
    check("World to_dict", False, str(e))

# ── 9. World.save_scene / load_scene round-trip ──
try:
    w = PhysicsWorld(0, 500)
    w.create_body(Shape.rect(32, 32), BODY_DYNAMIC, 2.0, "player", 100, 200, density=1.5)
    w.create_body(Shape.circle(10), BODY_STATIC, 0.0, "ball", 400, 300)
    tmp = tempfile.mktemp(suffix=".json")
    w.save_scene(tmp)
    w2 = PhysicsWorld.load_scene(tmp)
    os.unlink(tmp)
    check("load gravity_x same", w2._gx == 0.0)
    check("load gravity_y same", w2._gy == 500.0)
    check("load 2 bodies", w2.body_count() == 2)
    tags = sorted(b.tag for b in w2._bodies)
    check("load tags correct", tags == ["ball", "player"])
    load_player = [b for b in w2._bodies if b.tag == "player"][0]
    check("load player x", load_player.x == 100.0)
    check("load player y", load_player.y == 200.0)
    check("load player density", load_player.density == 1.5)
    check("load player friction", load_player.friction == 0.5)
    load_ball = [b for b in w2._bodies if b.tag == "ball"][0]
    check("load ball circle radius", load_ball.shape.radius == 10.0)
except Exception as e:
    check("save/load round-trip", False, str(e))

# ── 10. World.save_scene with joints ─────────────
from physics_engine import JOINT_DISTANCE
try:
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, "a", 0, 0)
    b = w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, "b", 100, 0)
    j = w.create_joint(JOINT_DISTANCE, a, b, length=100.0, stiffness=2.0, damping=0.1)
    tmp = tempfile.mktemp(suffix=".json")
    w.save_scene(tmp)
    w2 = PhysicsWorld.load_scene(tmp)
    os.unlink(tmp)
    check("load with joints 2 bodies", w2.body_count() == 2)
    check("load with joints 1 joint", len(w2._joints) == 1)
    loaded_j = w2._joints[0]
    check("load joint length", loaded_j.length == 100.0)
    check("load joint stiffness", loaded_j.stiffness == 2.0)
except Exception as e:
    check("save/load with joints", False, str(e))

# ── 11. on_physics LifecycleHook type exists ─────
from ast_nodes import LifecycleHook
try:
    lh = LifecycleHook(hook_type="on_physics", params=[], body=None)
    check("LifecycleHook on_physics creatable", lh.hook_type == "on_physics")
except Exception as e:
    check("LifecycleHook on_physics", False, str(e))

# ── 12. PhysicsWorld.get_attr save_scene/load_scene/ to_dict ──
try:
    w = PhysicsWorld(0, 0)
    check("get_attr save_scene", w.get_attr("save_scene") is not None)
    check("get_attr load_scene", w.get_attr("load_scene") is not None)
    check("get_attr to_dict", w.get_attr("to_dict") is not None)
except Exception as e:
    check("World get_attr serialization methods", False, str(e))

# ── 13. Density auto-calculates mass from shape area ─
try:
    w = PhysicsWorld(0, 0)
    # Rect 10x20 = 200 area * 3 density = 600 mass
    b = w.create_body(Shape.rect(10, 20), BODY_DYNAMIC, 1.0, "dense", 0, 0, density=3.0)
    expected_mass = 10 * 20 * 3.0  # 600
    check("density auto mass rect", b.mass == expected_mass)
    # Circle r=5 = pi*25 area * 2 density = ~157 mass
    c = w.create_body(Shape.circle(5), BODY_DYNAMIC, 1.0, "circle_dense", 0, 0, density=2.0)
    expected_circle_mass = math.pi * 25 * 2.0
    check("density auto mass circle", abs(c.mass - expected_circle_mass) < 0.1)
except Exception as e:
    check("Density auto mass", False, str(e))

# ── 14. Debug draw function exists ───────────────
try:
    from pygame_backend import _draw_physics_debug, _register_physics_world, _PHYSICS_DEBUG_WORLDS
    check("_draw_physics_debug exists", callable(_draw_physics_debug))
    check("_register_physics_world exists", callable(_register_physics_world))
except Exception as e:
    check("Debug draw imports", False, str(e))

# ── RESULTS ──────────────────────────────────────────
print()
print("=" * 55)
print("  v3.9.6.24 — Physics: scene integration")
print("=" * 55)
print(f"  {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 55)
if FAIL > 0:
    sys.exit(1)
