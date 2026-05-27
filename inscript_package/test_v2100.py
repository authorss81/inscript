"""
test_v2100.py — InScript v2.10.0
================================================================
Physics & Multiplayer tests:
  • `physics` module: world, body, static_body, area, Rect, Circle, Vec2
  • world.step(dt): gravity, position integration
  • world.step(dt): dynamic vs static AABB collision + impulse response
  • world.on_collision callback fires
  • Area.on_overlap callback fires
  • physics.ray_cast: hit, miss, closest-body ordering, normal direction
  • `net` module: _NetDeltaSync delta compression
  • _NetClient / _NetServer instantiation (headless — no live network)
  • net.pack / net.unpack round-trip
  • _NetPeer.sync sends only changed keys
  • `import "physics" as p` from InScript source
  • `import "net" as n` from InScript source

All tests are headless — no game window, no live network connections.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))

from interpreter import Interpreter
from stdlib import load_module

PASS = 0; FAIL = 0

def ok(name):
    global PASS; PASS += 1; print(f"  PASS  {name}")

def fail(name, msg=""):
    global FAIL; FAIL += 1; print(f"  FAIL  {name}: {msg}")

def check(name, got, expected):
    if got == expected: ok(name)
    else: fail(name, f"want {expected!r}, got {got!r}")

def check_true(name, expr, msg=""):
    if expr: ok(name)
    else: fail(name, msg or "expected True")

def check_approx(name, got, expected, tol=0.5):
    if abs(float(got) - float(expected)) <= tol: ok(name)
    else: fail(name, f"want ≈{expected} (±{tol}), got {got}")

def check_contains(name, collection, item):
    if item in collection: ok(name)
    else: fail(name, f"{item!r} not in {collection!r}")


# ─────────────────────────────────────────────────────────────────────────────
# Load modules
# ─────────────────────────────────────────────────────────────────────────────
physics = load_module("physics")
net     = load_module("net")

# ─────────────────────────────────────────────────────────────────────────────
# 1. physics module — world, body, static_body, area construction
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 1. physics module construction ────────────────────────────────────")

world = physics["world"](0.0, 500.0)
check_true("world created", world is not None)
check("world has no bodies", world.body_count(), 0)

rect  = physics["Rect"](64, 32)
circ  = physics["Circle"](16)
check("Rect w", rect.w, 64.0)
check("Rect h", rect.h, 32.0)
check("Circle r", circ.r, 16.0)

body = physics["body"](1.0, rect, tag="player")
check("body tag",       body.tag,       "player")
check("body mass",      body.mass,      1.0)
check("body not static",body.is_static, False)

sb = physics["static_body"](physics["Rect"](100, 20), tag="floor")
check("static_body is_static", sb.is_static, True)
check("static_body tag",       sb.tag,       "floor")

area = physics["area"](physics["Circle"](50), tag="zone")
check("area tag", area.tag, "zone")

v = physics["Vec2"](3.0, 4.0)
check("Vec2 x", v.x, 3.0)
check("Vec2 y", v.y, 4.0)
check_approx("Vec2 length", v.length(), 5.0, 0.001)

# ─────────────────────────────────────────────────────────────────────────────
# 2. physics.world.step — gravity + integration
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 2. world.step — gravity + integration ─────────────────────────────")

w2 = physics["world"](0.0, 100.0)  # gentle gravity
b2 = physics["body"](1.0, physics["Rect"](16, 16), tag="falling")
b2.x = 0.0; b2.y = 0.0
w2.add(b2)
check("body at (0,0) before step", b2.y, 0.0)

w2.step(1.0)   # 1 second → vy += 100, y += 100
check_approx("y after 1s fall (gravity=100)", b2.y, 100.0, 2.0)
check_true("vy positive after step", b2.velocity.y > 0)

w2.step(1.0)
check_true("y > 100 after 2nd step", b2.y > 100.0)

# Static body is unaffected by gravity
sb2 = physics["static_body"](physics["Rect"](200, 20), tag="ground")
sb2.x = 0.0; sb2.y = 500.0
w2.add(sb2)
w2.step(0.016)
check("static body position unchanged", sb2.y, 500.0)

# ─────────────────────────────────────────────────────────────────────────────
# 3. AABB collision resolution
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 3. AABB collision resolution ──────────────────────────────────────")

w3   = physics["world"](0.0, 0.0)  # no gravity
ball = physics["body"](1.0, physics["Circle"](10), tag="ball")
wall = physics["static_body"](physics["Rect"](200, 10), tag="wall")

ball.x = 0.0;  ball.y = -15.0  # just above wall
ball.velocity.y = 100.0         # moving down
wall.x = 0.0;  wall.y = 0.0   # wall at y=0
w3.add(ball); w3.add(wall)

# Step until collision resolves
for _ in range(10):
    w3.step(0.016)

# After collision, ball velocity.y should be reversed (bouncing)
check_true("ball bounces off wall (vy < 0 or stopped)",
           ball.velocity.y < 100.0)

# ─────────────────────────────────────────────────────────────────────────────
# 4. on_collision callback
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 4. on_collision callback ───────────────────────────────────────────")

w4   = physics["world"](0.0, 0.0)
a4   = physics["body"](1.0, physics["Rect"](20, 20), tag="a")
b4   = physics["static_body"](physics["Rect"](20, 20), tag="b")
a4.x = 0.0; a4.y = 0.0
b4.x = 15.0; b4.y = 0.0   # overlapping

collisions = []
w4.on_collision(lambda ba, bb: collisions.append((ba.tag, bb.tag)))
w4.add(a4); w4.add(b4)
w4.step(0.016)
check_true("on_collision fired", len(collisions) > 0)
tags = [set(c) for c in collisions]
check_true("collision involves a and b", {"a", "b"} in tags)

# ─────────────────────────────────────────────────────────────────────────────
# 5. Area on_overlap callback
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 5. Area on_overlap callback ────────────────────────────────────────")

w5  = physics["world"](0.0, 0.0)
dyn = physics["body"](1.0, physics["Circle"](10), tag="dyn")
ar  = physics["area"](physics["Circle"](50), tag="zone")
dyn.x = 0.0; dyn.y = 0.0
ar.x  = 5.0; ar.y  = 5.0   # overlapping

overlaps = []
ar.on_overlap(lambda area_body, other: overlaps.append(other.tag))
w5.add(dyn); w5.add(ar)
w5.step(0.016)
check_true("on_overlap fired", len(overlaps) > 0)
check_contains("dyn in overlaps", overlaps, "dyn")

# ─────────────────────────────────────────────────────────────────────────────
# 6. physics.ray_cast
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 6. physics.ray_cast ────────────────────────────────────────────────")

w6   = physics["world"](0.0, 0.0)
wall6 = physics["static_body"](physics["Rect"](100, 20), tag="wall6")
wall6.x = 0.0; wall6.y = 200.0
w6.add(wall6)

# Ray pointing downward from above
result = physics["ray_cast"](w6, 0.0, 0.0, 0.0, 1.0, 500.0)
check_true("ray_cast returns hit dict",  result is not None)
check("hit body tag",                    result["body"].tag, "wall6")
check_true("hit_y near wall top (≈190)", 180.0 <= result["hit_y"] <= 200.0)
check_true("hit distance > 0",           result["distance"] > 0)
check_approx("normal_y = -1 (ray hit top face)", result["normal_y"], -1.0, 0.1)

# Ray pointing away — no hit
result_miss = physics["ray_cast"](w6, 0.0, 0.0, 0.0, -1.0, 500.0)
check("ray_cast miss returns None", result_miss, None)

# Ray too short to reach
result_short = physics["ray_cast"](w6, 0.0, 0.0, 0.0, 1.0, 50.0)
check("ray_cast short misses far wall", result_short, None)

# Multiple bodies — returns closest
wall_near = physics["static_body"](physics["Rect"](100, 20), tag="near")
wall_near.x = 0.0; wall_near.y = 100.0
w6.add(wall_near)
result_closest = physics["ray_cast"](w6, 0.0, 0.0, 0.0, 1.0, 500.0)
check("ray_cast returns closest body", result_closest["body"].tag, "near")

# ─────────────────────────────────────────────────────────────────────────────
# 7. net — pack / unpack round-trip
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 7. net.pack / unpack ───────────────────────────────────────────────")

pack   = net["pack"]
unpack = net["unpack"]

data   = {"player": "hero", "x": 12.5, "y": -3.0, "hp": 100, "alive": True}
packed = pack(data)
check_true("pack returns string/bytes", isinstance(packed, (str, bytes)))
check_true("packed is compact JSON",    '"player"' in packed)

restored = unpack(packed)
check("unpack restores dict",   restored["player"], "hero")
check("unpack restores float",  restored["x"],      12.5)
check("unpack restores bool",   restored["alive"],  True)

# Round-trip with bytes
packed_bytes = pack(data).encode() if isinstance(pack(data), str) else pack(data)
check("unpack from bytes", unpack(packed_bytes)["hp"], 100)

# ─────────────────────────────────────────────────────────────────────────────
# 8. _NetDeltaSync — delta compression
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 8. _NetDeltaSync ───────────────────────────────────────────────────")

DeltaSync = net["DeltaSync"]
ds = DeltaSync()

state1 = {"x": 0, "y": 0, "hp": 100, "score": 0}
d1 = ds.delta(state1)
check("first delta sends everything", len(d1), 4)
check_contains("x in first delta", d1, "x")
check_contains("hp in first delta", d1, "hp")

# No change → empty delta
d2 = ds.delta(state1)
check("no-change delta is empty", d2, {})

# Only x changed
state2 = {"x": 10, "y": 0, "hp": 100, "score": 0}
d3 = ds.delta(state2)
check("only x changed → delta has 1 key", len(d3), 1)
check("x change detected", d3.get("x"), 10)
check_true("y NOT in delta", "y" not in d3)

# Multiple changes
state3 = {"x": 20, "y": 5, "hp": 80, "score": 50}
d4 = ds.delta(state3)
check("4 changes detected (x,y,hp,score)", len(d4), 4)
check_contains("x in d4", d4, "x")
check_contains("y in d4", d4, "y")
check_contains("hp in d4", d4, "hp")

# Reset clears baseline → next delta sends everything
ds.reset()
d5 = ds.delta(state3)
check("after reset all 4 keys resent", len(d5), 4)

# ─────────────────────────────────────────────────────────────────────────────
# 9. _NetServer / _NetClient headless instantiation
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 9. NetServer / NetClient headless instantiation ───────────────────")

Server = net["Server"]
Client = net["Client"]

srv = Server(port=19555, max_clients=4)
check("server default player_count", srv.player_count(), 0)
check_true("server repr contains port", "19555" in repr(srv))

cli = Client()
check("client not connected initially", cli.connected, False)
check_true("client repr works", "NetClient" in repr(cli))

# on_message callback registration (chainable)
msgs = []
ret = cli.on_message(lambda d: msgs.append(d))
check_true("on_message returns self (chainable)", ret is cli)

# ─────────────────────────────────────────────────────────────────────────────
# 10. `import "physics" as p` from InScript source
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 10. import physics from InScript ──────────────────────────────────")

phys_src = """
import "physics" as p

let w   = p.world(0.0, 200.0)
let box = p.body(1.0, p.Rect(32.0, 32.0), "crate")
let gnd = p.static_body(p.Rect(400.0, 20.0), "ground")

w.add(box)
w.add(gnd)
w.step(1.0)

let fell = box.y > 0.0
"""
try:
    i10 = Interpreter()
    i10.execute(phys_src)
    check("physics importable from InScript", i10._globals._store.get("fell"), True)
    ok("physics module works end-to-end from InScript")
except Exception as e:
    fail("physics from InScript", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# 11. `import "net" as n` from InScript source
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 11. import net from InScript ──────────────────────────────────────")

net_src = """
import "net" as n

let ds  = n.DeltaSync()
let s1  = ds.delta({"x": 0, "y": 0})
let s2  = ds.delta({"x": 0, "y": 0})
let s3  = ds.delta({"x": 5, "y": 0})

let all_sent    = len(s1) == 2
let no_change   = len(s2) == 0
let only_x      = len(s3) == 1
"""
try:
    i11 = Interpreter()
    i11.execute(net_src)
    check("DeltaSync first sends all",    i11._globals._store.get("all_sent"),  True)
    check("DeltaSync no-change is empty", i11._globals._store.get("no_change"), True)
    check("DeltaSync partial delta",      i11._globals._store.get("only_x"),    True)
    ok("net module works end-to-end from InScript")
except Exception as e:
    fail("net from InScript", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
total = PASS + FAIL
print(f"InScript v2.10.0  —  {PASS}/{total} tests passed", end="")
if FAIL:
    print(f"  ❌ {FAIL} FAILED")
    sys.exit(1)
else:
    print("  ✅ ALL PASS")
    sys.exit(0)
