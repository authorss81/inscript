# v3.9.6.26 — Physics: world queries (.py tests)
# Run: python v3.9.6.26/test_world_queries.py

import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC, BODY_STATIC, Contact

PASS, FAIL = 0, 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  {chr(0x2705)} {name}")
        PASS += 1
    else:
        print(f"  {chr(0x274C)} {name}  {detail}")
        FAIL += 1

# ── Setup: world with several bodies ────────────────────
w = PhysicsWorld(0, 500)
w.create_body(Shape.rect(40, 40), BODY_STATIC, 0.0, "box_a", 100, 100)
w.create_body(Shape.rect(40, 40), BODY_STATIC, 0.0, "box_b", 200, 100)
w.create_body(Shape.rect(40, 40), BODY_STATIC, 0.0, "box_c", 300, 100)
w.create_body(Shape.circle(20),    BODY_STATIC, 0.0, "circle_a", 400, 100)

# ── 1. query_aabb — finds overlapping bodies ──────────
try:
    results = w.query_aabb(100, 100, 30, 30)
    tags = sorted(b.tag for b in results)
    check("query_aabb finds box_a", "box_a" in tags)
    check("query_aabb does not find far bodies", "box_c" not in tags)
except Exception as e:
    check("query_aabb basic", False, str(e))

# ── 2. query_aabb — empty area ────────────────────────
try:
    results = w.query_aabb(0, 0, 10, 10)
    check("query_aabb empty returns []", len(results) == 0)
except Exception as e:
    check("query_aabb empty", False, str(e))

# ── 3. query_aabb — large query finds all ─────────────
try:
    results = w.query_aabb(250, 100, 500, 500)
    check("query_aabb large finds 4 bodies", len(results) == 4)
except Exception as e:
    check("query_aabb all", False, str(e))

# ── 4. query_circle — finds overlapping bodies ────────
try:
    results = w.query_circle(100, 100, 30)
    tags = sorted(b.tag for b in results)
    check("query_circle finds box_a", "box_a" in tags)
    check("query_circle does not find far bodies", "box_c" not in tags)
except Exception as e:
    check("query_circle basic", False, str(e))

# ── 5. query_circle — circle-to-rect corner overlap ──
try:
    results = w.query_circle(120, 120, 30)
    check("query_circle corner overlap finds box_a",
          any(b.tag == "box_a" for b in results))
except Exception as e:
    check("query_circle corner", False, str(e))

# ── 6. query_circle — finds circle body ───────────────
try:
    results = w.query_circle(400, 100, 25)
    check("query_circle finds circle_a",
          any(b.tag == "circle_a" for b in results))
except Exception as e:
    check("query_circle circle body", False, str(e))

# ── 7. ray_cast — closest hit ─────────────────────────
try:
    hit = w.ray_cast(0, 100, 1, 0, 500)
    check("ray_cast returns hit dict", isinstance(hit, dict))
    if hit:
        check("ray_cast closest is box_a", hit["body"].tag == "box_a")
        check("ray_cast has hit_x/hit_y", "hit_x" in hit and "hit_y" in hit)
        check("ray_cast has normal", "normal_x" in hit and "normal_y" in hit)
        check("ray_cast distance positive", hit["distance"] > 0)
except Exception as e:
    check("ray_cast basic", False, str(e))

# ── 8. ray_cast — miss ────────────────────────────────
try:
    hit = w.ray_cast(0, 0, 1, 0, 500)
    check("ray_cast miss returns None", hit is None)
except Exception as e:
    check("ray_cast miss", False, str(e))

# ── 9. ray_cast_all — all hits sorted ────────────────
try:
    hits = w.ray_cast_all(0, 100, 1, 0, 500)
    check("ray_cast_all returns list", isinstance(hits, list))
    check("ray_cast_all has multiple hits", len(hits) >= 2)
    if len(hits) >= 2:
        check("ray_cast_all sorted by distance",
              hits[0]["distance"] <= hits[1]["distance"])
except Exception as e:
    check("ray_cast_all basic", False, str(e))

# ── 10. ray_cast_all — vertical ray ──────────────────
try:
    hits = w.ray_cast_all(100, 0, 0, 1, 500)
    check("ray_cast_all vertical finds box_a",
          any(h["body"].tag == "box_a" for h in hits))
except Exception as e:
    check("ray_cast_all vertical", False, str(e))

# ── 11. ray_cast_all — no hits ───────────────────────
try:
    hits = w.ray_cast_all(0, 0, 1, 0, 5)
    check("ray_cast_all short ray returns []", len(hits) == 0)
except Exception as e:
    check("ray_cast_all short", False, str(e))

# ── 12. contact_points — with dynamic body ────────────
try:
    w2 = PhysicsWorld(0, 500)
    a = w2.create_body(Shape.rect(40, 40), BODY_DYNAMIC, 1.0, "dyn", 100, 85)
    b = w2.create_body(Shape.rect(200, 20), BODY_STATIC, 0.0, "floor", 100, 100)
    # Run enough frames for body to reach floor
    for _ in range(5):
        w2.step(0.016)
    contacts = w2.contact_points(a)
    check("contact_points returns list", isinstance(contacts, list))
    check("contact_points finds floor contact", len(contacts) > 0)
    if contacts:
        check("contact_points has body", "body" in contacts[0])
        check("contact_points has normal_y", "normal_y" in contacts[0])
        check("contact_points floor normal_y", contacts[0]["normal_y"] < 0)
except Exception as e:
    check("contact_points basic", False, str(e))

# ── 13. contact_points — no contacts ──────────────────
try:
    w3 = PhysicsWorld(0, 500)
    a = w3.create_body(Shape.rect(40, 40), BODY_DYNAMIC, 1.0, "dyn", 100, 0)
    contacts = w3.contact_points(a)
    check("contact_points airborne returns []", len(contacts) == 0)
except Exception as e:
    check("contact_points no contact", False, str(e))

# ── 14. get_attr exposes query methods ────────────────
try:
    check("world.get_attr('query_aabb')", w.get_attr("query_aabb") is not None)
    check("world.get_attr('query_circle')", w.get_attr("query_circle") is not None)
    check("world.get_attr('contact_points')", w.get_attr("contact_points") is not None)
    check("world.get_attr('ray_cast')", w.get_attr("ray_cast") is not None)
    check("world.get_attr('ray_cast_all')", w.get_attr("ray_cast_all") is not None)
except Exception as e:
    check("get_attr queries", False, str(e))

# ── 15. ray_cast from negative x ───────────────────────
try:
    hits = w.ray_cast_all(-100, 100, 1, 0, 1000)
    check("ray_cast_all from negative x finds bodies", len(hits) > 0)
except Exception as e:
    check("ray_cast_all negative origin", False, str(e))

# ── 16. ray_cast_all — circle body intersection ─────
try:
    hits = w.ray_cast_all(380, 100, 1, 0, 50)
    check("ray_cast_all hits circle_a",
          any(h["body"].tag == "circle_a" for h in hits))
except Exception as e:
    check("ray_cast_all circle", False, str(e))

# ── RESULTS ──────────────────────────────────────────
print()
print("=" * 55)
print("  v3.9.6.26 — Physics: world queries")
print("=" * 55)
print(f"  {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 55)
if FAIL > 0:
    sys.exit(1)
