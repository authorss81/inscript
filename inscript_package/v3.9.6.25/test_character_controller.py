# v3.9.6.25 — Physics: character controller (.py tests)
# Run: python v3.9.6.25/test_character_controller.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC, BODY_STATIC, CharacterBody

PASS, FAIL = 0, 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  {chr(0x2705)} {name}")
        PASS += 1
    else:
        print(f"  {chr(0x274C)} {name}  {detail}")
        FAIL += 1

# ── 1. CharacterBody creatable ────────────────────
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(16, 32), BODY_DYNAMIC, 1.0, "p", 0, 0)
    c = CharacterBody(w, b)
    check("CharacterBody creatable", isinstance(c, CharacterBody))
except Exception as e:
    check("CharacterBody creatable", False, str(e))

# ── 2. is_on_floor standing on ground ─────────────
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(16, 32), BODY_DYNAMIC, 1.0, "p", 100, 80)
    w.create_body(Shape.rect(200, 20), BODY_STATIC, 0.0, "floor", 100, 100)
    c = CharacterBody(w, b)
    c.move_and_slide(0, 0, 0.016)
    check("is_on_floor standing on ground", c.is_on_floor())
except Exception as e:
    check("is_on_floor", False, str(e))

# ── 3. is_on_floor false when airborne ────────────
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(16, 32), BODY_DYNAMIC, 1.0, "p", 100, 0)
    c = CharacterBody(w, b)
    c.move_and_slide(0, 0, 0.016)
    check("is_on_floor false when airborne", not c.is_on_floor())
except Exception as e:
    check("is_on_floor airborne", False, str(e))

# ── 4. is_on_wall when sliding into wall ─────────
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(16, 32), BODY_DYNAMIC, 1.0, "p", 150, 80)
    w.create_body(Shape.rect(200, 20), BODY_STATIC, 0.0, "floor", 100, 100)
    w.create_body(Shape.rect(20, 100), BODY_STATIC, 0.0, "wall", 200, 50)
    c = CharacterBody(w, b)
    # Simulate multiple frames to reach wall
    for _ in range(6):
        c.move_and_slide(500, 0, 0.016)
    check("is_on_wall true on wall collision", c.is_on_wall())
except Exception as e:
    check("is_on_wall", False, str(e))

# ── 5. wall_side returns correct direction ───────
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(16, 32), BODY_DYNAMIC, 1.0, "p", 150, 80)
    w.create_body(Shape.rect(200, 20), BODY_STATIC, 0.0, "floor", 100, 100)
    w.create_body(Shape.rect(20, 100), BODY_STATIC, 0.0, "wall", 200, 50)
    c = CharacterBody(w, b)
    for _ in range(6):
        c.move_and_slide(500, 0, 0.016)
    check("wall_side = 1 (right wall)", c.get_wall_side() == 1)
except Exception as e:
    check("wall_side", False, str(e))

# ── 6. is_on_ceiling when jumping into ceiling ───
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(16, 32), BODY_DYNAMIC, 1.0, "p", 100, 50)
    w.create_body(Shape.rect(200, 20), BODY_STATIC, 0.0, "ceil", 100, 20)
    c = CharacterBody(w, b)
    c.move_and_slide(0, -500, 0.016)
    check("is_on_ceiling true on ceiling collision", c.is_on_ceiling())
except Exception as e:
    check("is_on_ceiling", False, str(e))

# ── 7. apply_knockback moves character ──────────
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(16, 32), BODY_DYNAMIC, 1.0, "p", 100, 0)
    c = CharacterBody(w, b)
    c.apply_knockback(-50, 0)
    c.move_and_slide(0, 0, 0.016)
    check("knockback moves character left", b.x < 100)
except Exception as e:
    check("apply_knockback", False, str(e))

# ── 8. apply_knockback with vertical component ───
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(16, 32), BODY_DYNAMIC, 1.0, "p", 100, 0)
    c = CharacterBody(w, b)
    c.apply_knockback(0, -100)
    c.move_and_slide(0, 0, 0.016)
    check("knockback moves character up", b.y < 0)
except Exception as e:
    check("apply_knockback vertical", False, str(e))

# ── 9. move_and_collide returns hit info ────────
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(16, 32), BODY_DYNAMIC, 1.0, "p", 100, 80)
    w.create_body(Shape.rect(200, 20), BODY_STATIC, 0.0, "floor", 100, 100)
    c = CharacterBody(w, b)
    r = c.move_and_collide(0, 0, 0.016)
    check("move_and_collide returns dict", isinstance(r, dict))
    if r:
        check("move_and_collide has body key", "body" in r)
        check("move_and_collide has normal_x/y", "normal_x" in r and "normal_y" in r)
        check("move_and_collide body is floor", r["body"].tag == "floor")
except Exception as e:
    check("move_and_collide", False, str(e))

# ── 10. move_and_collide no hit when airborne ──
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(16, 32), BODY_DYNAMIC, 1.0, "p", 100, 0)
    c = CharacterBody(w, b)
    r = c.move_and_collide(0, 0, 0.016)
    check("move_and_collide returns None when airborne", r is None)
except Exception as e:
    check("move_and_collide airborne", False, str(e))

# ── 11. get_floor_normal returns correct normal ─
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(16, 32), BODY_DYNAMIC, 1.0, "p", 100, 80)
    w.create_body(Shape.rect(200, 20), BODY_STATIC, 0.0, "floor", 100, 100)
    c = CharacterBody(w, b)
    c.move_and_slide(0, 0, 0.016)
    nx, ny = c.get_floor_normal()
    check("get_floor_normal returns (0,-1)", nx == 0.0 and ny == -1.0)
except Exception as e:
    check("get_floor_normal", False, str(e))

# ── 12. PhysicsWorld.get_attr('create_character_body') exists
try:
    w = PhysicsWorld(0, 0)
    check("world.get_attr('create_character_body')", w.get_attr("create_character_body") is not None)
except Exception as e:
    check("get_attr create_character_body", False, str(e))

# ── 13. world.create_character_body convenience ──
try:
    w = PhysicsWorld(0, 0)
    char = w.create_character_body(Shape.rect(16, 32), "hero", 100, 100)
    check("create_character_body returns CharacterBody", isinstance(char, CharacterBody))
    check("create_character_body body tag", char.body.tag == "hero")
except Exception as e:
    check("create_character_body", False, str(e))

# ── 14. One-way platform: pass through from below
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(16, 32), BODY_DYNAMIC, 1.0, "p", 100, 50)
    plat = w.create_body(Shape.rect(200, 10), BODY_STATIC, 0.0, "plat", 100, 100)
    c = CharacterBody(w, b, one_way_platforms=True)
    c.set_platforms([plat])
    # Jump up into platform from below
    y_before = b.y
    c.move_and_slide(0, -500, 0.016)
    check("one-way platform: passes through from below", b.y < 80)
except Exception as e:
    check("one-way platform below", False, str(e))

# ── 15. One-way platform: stands on from above ───
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(16, 32), BODY_DYNAMIC, 1.0, "p", 100, 87)
    plat = w.create_body(Shape.rect(200, 10), BODY_STATIC, 0.0, "plat", 100, 100)
    c = CharacterBody(w, b, one_way_platforms=True)
    c.set_platforms([plat])
    c.move_and_slide(0, 0, 0.016)
    check("one-way platform: stands on from above", c.is_on_floor())
except Exception as e:
    check("one-way platform above", False, str(e))

# ── RESULTS ──────────────────────────────────────────
print()
print("=" * 55)
print("  v3.9.6.25 — Physics: character controller")
print("=" * 55)
print(f"  {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 55)
if FAIL > 0:
    sys.exit(1)
