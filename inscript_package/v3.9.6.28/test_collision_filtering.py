# v3.9.6.28 — Physics: collision filtering (.py tests)
# Run: python v3.9.6.28/test_collision_filtering.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

from physics_engine import (
    PhysicsWorld, Shape, BODY_DYNAMIC, BODY_STATIC, BODY_KINEMATIC,
    COLLISION_GROUP_ALL,
)

PASS, FAIL = 0, 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  {chr(0x2705)} {name}")
        PASS += 1
    else:
        print(f"  {chr(0x274C)} {name}  {detail}")
        FAIL += 1

# ── Constants for testing ────────────────────────────
GROUP_PLAYER = 1
GROUP_ENEMY  = 2
GROUP_WALL   = 4
GROUP_PICKUP = 8
GROUP_BULLET = 16

# ── 1. Default group/mask is ALL ────────────────────
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(10, 10), BODY_DYNAMIC, 1.0, "a", 0, 0)
    check("default collision_group == ALL", b.collision_group == COLLISION_GROUP_ALL)
    check("default collision_mask == ALL", b.collision_mask == COLLISION_GROUP_ALL)
except Exception as e:
    check("default group/mask", False, str(e))

# ── 2. Same mask — collision occurs ─────────────────
try:
    w = PhysicsWorld(0, 500)
    a = w.create_body(Shape.rect(40, 40), BODY_DYNAMIC, 1.0, "dyn", 100, 80)
    b = w.create_body(Shape.rect(200, 20), BODY_STATIC, 0.0, "floor", 100, 100)
    w.step(0.016)
    check("default mask: collision detected", len(w.contact_points(a)) > 0)
except Exception as e:
    check("same mask collision", False, str(e))

# ── 3. Non-overlapping mask — no collision ──────────
try:
    w = PhysicsWorld(0, 500)
    a = w.create_body(Shape.rect(40, 40), BODY_DYNAMIC, 1.0, "dyn", 100, 80)
    a.collision_group = GROUP_PLAYER
    a.collision_mask  = GROUP_ENEMY  # Only collides with GROUP_ENEMY
    b = w.create_body(Shape.rect(200, 20), BODY_STATIC, 0.0, "floor", 100, 100)
    b.collision_group = GROUP_WALL
    b.collision_mask  = COLLISION_GROUP_ALL    # Can be hit by anything
    w.step(0.016)
    # a.group = PLAYER, b.mask = ALL → PLAYER & ALL = PLAYER ≠ 0 → OK
    # b.group = WALL, a.mask = ENEMY → WALL & ENEMY = 0 → NO
    # So collision should be filtered out
    check("non-overlapping mask: no collision", len(w.contact_points(a)) == 0)
except Exception as e:
    check("non-overlapping mask", False, str(e))

# ── 4. Overlapping mask — collision occurs ──────────
try:
    w = PhysicsWorld(0, 500)
    a = w.create_body(Shape.rect(40, 40), BODY_DYNAMIC, 1.0, "dyn", 100, 80)
    a.collision_group = GROUP_PLAYER
    a.collision_mask  = GROUP_WALL | GROUP_ENEMY  # Collides with walls and enemies
    b = w.create_body(Shape.rect(200, 20), BODY_STATIC, 0.0, "floor", 100, 100)
    b.collision_group = GROUP_WALL
    b.collision_mask  = COLLISION_GROUP_ALL
    w.step(0.016)
    check("overlapping mask: collision detected", len(w.contact_points(a)) > 0)
except Exception as e:
    check("overlapping mask", False, str(e))

# ── 5. Dynamic-dynamic filtering ────────────────────
try:
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(20, 20), BODY_DYNAMIC, 1.0, "player", 100, 50)
    a.collision_group = GROUP_PLAYER
    a.collision_mask  = GROUP_WALL  # Player only collides with walls
    b = w.create_body(Shape.rect(20, 20), BODY_DYNAMIC, 1.0, "enemy", 120, 50)
    b.collision_group = GROUP_ENEMY
    b.collision_mask  = GROUP_PLAYER  # Enemy collides with players
    # a.mask=WALL, b.group=ENEMY → WALL & ENEMY = 0 → no collision
    w.step(0.016)
    check("dynamic-dynamic filtered out",
          all(c["body"].tag != "enemy" for c in w.contact_points(a)))
except Exception as e:
    check("dynamic-dynamic filter", False, str(e))

# ── 6. Kinematic body respects filtering ────────────
try:
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(20, 20), BODY_DYNAMIC, 1.0, "player", 100, 50)
    a.collision_group = GROUP_PLAYER
    a.collision_mask  = GROUP_WALL
    k = w.create_body(Shape.rect(20, 20), BODY_KINEMATIC, 0.0, "platform", 100, 100)
    k.collision_group = GROUP_WALL
    k.collision_mask  = COLLISION_GROUP_ALL
    w.step(0.016)
    check("kinematic-body filtered by mask",
          all(c["body"].tag != "platform" for c in w.contact_points(a)))
except Exception as e:
    check("kinematic filter", False, str(e))

# ── 7. CCD respects collision filtering ──────────────
try:
    w = PhysicsWorld(0, 0)
    bullet = w.create_body(Shape.rect(4, 4), BODY_DYNAMIC, 1.0, "bullet", 50, 50)
    bullet.ccd_enabled = True
    bullet.collision_group = GROUP_BULLET
    bullet.collision_mask  = GROUP_ENEMY  # Only hits enemies
    wall = w.create_body(Shape.rect(4, 100), BODY_STATIC, 0.0, "wall", 105, 50)
    wall.collision_group = GROUP_WALL
    wall.collision_mask  = COLLISION_GROUP_ALL
    bullet.vx = 10000
    w.step(0.016)
    # bullet.mask=ENEMY, wall.group=WALL → ENEMY & WALL = 0 → no collision
    check("CCD respects filtering: bullet passes through wall", bullet.x >= 200)
except Exception as e:
    check("CCD filtering", False, str(e))

# ── 8. CCD with matching filter stops ────────────────
try:
    w = PhysicsWorld(0, 0)
    bullet = w.create_body(Shape.rect(4, 4), BODY_DYNAMIC, 1.0, "bullet", 50, 50)
    bullet.ccd_enabled = True
    bullet.collision_group = GROUP_BULLET
    bullet.collision_mask  = GROUP_WALL  # Hits walls
    wall = w.create_body(Shape.rect(4, 100), BODY_STATIC, 0.0, "wall", 105, 50)
    wall.collision_group = GROUP_WALL
    wall.collision_mask  = COLLISION_GROUP_ALL
    bullet.vx = 10000
    w.step(0.016)
    check("CCD matching filter stops at wall", bullet.x <= 105)
except Exception as e:
    check("CCD matching filter", False, str(e))

# ── 9. Group/Mask set_attr works ────────────────────
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(10, 10), BODY_DYNAMIC, 1.0, "test", 0, 0)
    b.collision_group = 0xFF
    b.collision_mask  = 0x0F
    check("collision_group set to 0xFF", b.collision_group == 0xFF)
    check("collision_mask set to 0x0F", b.collision_mask == 0x0F)
except Exception as e:
    check("group/mask set", False, str(e))

# ── 10. Zero group masks everything out ──────────────
try:
    w = PhysicsWorld(0, 500)
    a = w.create_body(Shape.rect(40, 40), BODY_DYNAMIC, 1.0, "dyn", 100, 80)
    a.collision_group = 0  # No group membership → no collisions
    a.collision_mask  = COLLISION_GROUP_ALL
    b = w.create_body(Shape.rect(200, 20), BODY_STATIC, 0.0, "floor", 100, 100)
    w.step(0.016)
    check("zero group: no collisions", len(w.contact_points(a)) == 0)
except Exception as e:
    check("zero group", False, str(e))

# ── RESULTS ──────────────────────────────────────────
print()
print("=" * 55)
print("  v3.9.6.28 — Physics: collision filtering")
print("=" * 55)
print(f"  {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 55)
if FAIL > 0:
    sys.exit(1)
