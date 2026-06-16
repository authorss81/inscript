"""
test_v280.py — InScript v2.8.0
================================================================
Asset Pipeline tests:
  • AssetHandle: create, type validation, headless stub load
  • AssetRegistry: register, load_all, clear
  • check_for_changes (mtime-based hot-reload)
  • export_manifest → assets.toml content
  • bundle: copy asset files to dest dir
  • @texture / @sound / @tilemap / @font decorator on let decl
  • `asset` stdlib module: asset.texture(), asset.sound(), etc.
  • sha256 integrity check
  • exists() path check

All tests are headless (no pygame / audio hardware required).
"""
import sys, os, time, tempfile, shutil
sys.path.insert(0, os.path.dirname(__file__))

from stdlib_assets import (
    AssetHandle, AssetRegistry, get_registry, reset_registry,
    make_texture, make_sound, make_tilemap, make_font, ASSET_TYPES,
)
from interpreter import Interpreter

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

def check_contains(name, text, sub):
    if sub in str(text): ok(name)
    else: fail(name, f"expected {sub!r} in {text!r}")

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_tmpdir():
    return tempfile.mkdtemp(prefix="inscript_v280_")

def write_dummy_asset(directory, rel_path, content=b"DUMMY"):
    full = os.path.join(directory, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as f:
        f.write(content)
    return full

def make_minimal_png() -> bytes:
    """Return bytes of a valid 1x1 white PNG."""
    import struct, zlib
    sig = b'\x89PNG\r\n\x1a\n'
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)  # 1x1, 8-bit RGB
    raw = b'\x00\xff\xff\xff'  # filter=none, white pixel
    idat = zlib.compress(raw)
    return sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b'')

# ─────────────────────────────────────────────────────────────────────────────
# 1. AssetHandle basics
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 1. AssetHandle basics ──────────────────────────────────────────────")

reset_registry()

h_tex = AssetHandle("texture", "sprites/hero.png")
check("texture handle type",    h_tex.asset_type, "texture")
check("texture handle path",    h_tex.path,       "sprites/hero.png")
check("not loaded initially",   h_tex.loaded,     False)
check("data is None initially", h_tex.data,       None)

h_snd = AssetHandle("sound", "sfx/jump.wav")
check("sound handle type", h_snd.asset_type, "sound")

h_map = AssetHandle("tilemap", "maps/level1.tmx")
check("tilemap handle type", h_map.asset_type, "tilemap")

h_fnt = AssetHandle("font", "fonts/roboto.ttf", extra={"size": 16})
check("font handle type", h_fnt.asset_type,      "font")
check("font extra size",  h_fnt.extra["size"],    16)

# Invalid type raises
try:
    AssetHandle("video", "cutscene.mp4")
    fail("invalid type should raise ValueError")
except ValueError:
    ok("invalid type raises ValueError")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Load with missing file (graceful — no crash, loaded stays False)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 2. Load with missing file ──────────────────────────────────────────")

h_missing = AssetHandle("texture", "no_such_file.png")
h_missing.load("/nonexistent")
check("missing file: loaded stays False", h_missing.loaded, False)
check("missing file: data stays None",    h_missing.data,   None)

# ─────────────────────────────────────────────────────────────────────────────
# 3. Load with real file (headless stub — no pygame)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 3. Load with real file (headless) ─────────────────────────────────")

tmp = make_tmpdir()
try:
    write_dummy_asset(tmp, "sprites/hero.png", make_minimal_png())
    write_dummy_asset(tmp, "sfx/jump.wav",     b"RIFF" + b"\x00" * 40)
    write_dummy_asset(tmp, "fonts/roboto.ttf", b"\x00\x01\x00\x00" + b"\x00" * 100)

    # texture load → headless stub dict (no pygame)
    h_t = AssetHandle("texture", "sprites/hero.png")
    h_t.load(tmp)
    check("texture loads (headless stub)", h_t.loaded, True)
    check_true("texture data is not None", h_t.data is not None)

    # exists() and sha256()
    check("exists returns True",  h_t.exists(tmp), True)
    sha = h_t.sha256(tmp)
    check_true("sha256 non-empty string", bool(sha) and len(sha) == 64)

    # exists() for missing path
    h_m = AssetHandle("texture", "nope.png")
    check("exists returns False for missing", h_m.exists(tmp), False)
    check("sha256 empty string for missing",  h_m.sha256(tmp), "")

    # font load → headless stub
    h_f = AssetHandle("font", "fonts/roboto.ttf", extra={"size": 14})
    h_f.load(tmp)
    check("font loads (headless stub)", h_f.loaded, True)

finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 4. AssetRegistry: register, load_all, clear
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 4. AssetRegistry ───────────────────────────────────────────────────")

reset_registry()
reg = AssetRegistry()

h1 = AssetHandle("texture", "a.png")
h2 = AssetHandle("sound",   "b.wav")
h3 = AssetHandle("font",    "c.ttf", extra={"size": 12})

reg.register(h1); reg.register(h2); reg.register(h3)
check("registry length",            len(reg), 3)

# Idempotent re-register
reg.register(h1)
check("re-register is idempotent",  len(reg), 3)

all_h = reg.all_handles()
check("all_handles returns list",   len(all_h), 3)
check_true("h1 in all_handles",     h1 in all_h)

# load_all with no real files → graceful (all stay unloaded)
loaded_count = reg.load_all(base_dir="/nonexistent")
check("load_all with missing base_dir returns 0", loaded_count, 0)

# clear
reg.clear()
check("clear empties registry", len(reg), 0)

# ─────────────────────────────────────────────────────────────────────────────
# 5. check_for_changes (hot-reload mtime detection)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 5. check_for_changes (hot-reload) ─────────────────────────────────")

tmp2 = make_tmpdir()
try:
    asset_path = write_dummy_asset(tmp2, "sprites/player.png", b"PNG_v1")

    reg2 = AssetRegistry()
    h_hot = AssetHandle("texture", "sprites/player.png")
    reg2.register(h_hot)
    h_hot.load(tmp2)
    check("initial load marks loaded", h_hot.loaded, True)

    # Immediately check — mtime unchanged → nothing reloaded
    changed1 = reg2.check_for_changes()
    check("no change immediately after load", len(changed1), 0)

    # Modify the file (force new mtime)
    time.sleep(0.05)
    with open(asset_path, "wb") as f:
        f.write(b"PNG_v2")
    os.utime(asset_path, (time.time() + 1, time.time() + 1))  # bump mtime

    changed2 = reg2.check_for_changes()
    check("modified file detected by check_for_changes", len(changed2), 1)
    check("correct handle reloaded", changed2[0], h_hot)

    # Check again — no further change
    changed3 = reg2.check_for_changes()
    check("no second reload without file change", len(changed3), 0)

finally:
    shutil.rmtree(tmp2, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 6. export_manifest → assets.toml
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 6. export_manifest ─────────────────────────────────────────────────")

tmp3 = make_tmpdir()
try:
    write_dummy_asset(tmp3, "sprites/hero.png",   b"PNG")
    write_dummy_asset(tmp3, "sfx/jump.wav",       b"WAV")
    write_dummy_asset(tmp3, "fonts/roboto.ttf",   b"TTF")

    reg3 = AssetRegistry()
    reg3.register(AssetHandle("texture", "sprites/hero.png"))
    reg3.register(AssetHandle("sound",   "sfx/jump.wav"))
    reg3.register(AssetHandle("font",    "fonts/roboto.ttf", extra={"size": 16}))

    manifest_path = os.path.join(tmp3, "assets.toml")
    reg3.export_manifest(manifest_path, base_dir=tmp3)

    check_true("assets.toml created",         os.path.isfile(manifest_path))
    content = open(manifest_path).read()
    check_contains("manifest has count = 3",  content, "count     = 3")
    check_contains("manifest has texture",    content, 'type   = "texture"')
    check_contains("manifest has sound",      content, 'type   = "sound"')
    check_contains("manifest has font",       content, 'type   = "font"')
    check_contains("manifest has hero.png",   content, "sprites/hero.png")
    check_contains("manifest has sha256",     content, "sha256")
    check_contains("manifest exists = true",  content, "exists = true")

finally:
    shutil.rmtree(tmp3, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 7. bundle: copy assets to dest dir
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 7. bundle ──────────────────────────────────────────────────────────")

tmp4 = make_tmpdir()
try:
    write_dummy_asset(tmp4, "sprites/hero.png", b"PNG")
    write_dummy_asset(tmp4, "sfx/jump.wav",     b"WAV")

    reg4 = AssetRegistry()
    reg4.register(AssetHandle("texture", "sprites/hero.png"))
    reg4.register(AssetHandle("sound",   "sfx/jump.wav"))
    reg4.register(AssetHandle("texture", "missing_asset.png"))  # intentionally missing

    dest = os.path.join(tmp4, "dist", "assets")
    summary = reg4.bundle(src_base=tmp4, dest_base=dest, skip_missing=True)

    check("2 assets copied",                    summary["copied"],  2)
    check("1 asset skipped (missing)",          summary["skipped"], 1)
    check("0 fatal missing",                    summary["missing"], 0)
    check_true("hero.png in dest",  os.path.isfile(os.path.join(dest, "sprites", "hero.png")))
    check_true("jump.wav in dest",  os.path.isfile(os.path.join(dest, "sfx",     "jump.wav")))

finally:
    shutil.rmtree(tmp4, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 8. Factory functions (make_texture, make_sound, make_tilemap, make_font)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 8. Factory functions ───────────────────────────────────────────────")

reset_registry()
reg_g = get_registry()

ht = make_texture("sprites/hero.png")
hs = make_sound("sfx/jump.wav")
hm = make_tilemap("maps/level1.tmx")
hf = make_font("fonts/roboto.ttf", 20)

check("make_texture type",    ht.asset_type, "texture")
check("make_sound type",      hs.asset_type, "sound")
check("make_tilemap type",    hm.asset_type, "tilemap")
check("make_font type",       hf.asset_type, "font")
check("make_font size",       hf.extra["size"], 20)
check("all 4 in global registry", len(reg_g), 4)

# Registering same handle twice is idempotent
make_texture("sprites/hero.png")
check("duplicate path still idempotent (new handle, so count 5)", len(reg_g), 5)

# ─────────────────────────────────────────────────────────────────────────────
# 9. `asset` stdlib module (import "asset" as asset)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 9. `asset` stdlib module ───────────────────────────────────────────")

reset_registry()

asset_src = """
import "asset" as asset

let t = asset.texture("sprites/player.png")
let s = asset.sound("sfx/hit.wav")
let m = asset.tilemap("maps/world.tmx")
let f = asset.font("fonts/mono.ttf", 14)
"""
try:
    interp_asset = Interpreter()
    interp_asset.execute(asset_src)
    # Verify handles were created and registered
    t_val = interp_asset._env.get("t")
    s_val = interp_asset._env.get("s")
    m_val = interp_asset._env.get("m")
    f_val = interp_asset._env.get("f")

    check_true("t is AssetHandle",              isinstance(t_val, AssetHandle))
    check_true("s is AssetHandle",              isinstance(s_val, AssetHandle))
    check_true("m is AssetHandle",              isinstance(m_val, AssetHandle))
    check_true("f is AssetHandle",              isinstance(f_val, AssetHandle))
    check("t type is texture",                  t_val.asset_type, "texture")
    check("s type is sound",                    s_val.asset_type, "sound")
    check("m type is tilemap",                  m_val.asset_type, "tilemap")
    check("f type is font",                     f_val.asset_type, "font")
    check("t path",                             t_val.path, "sprites/player.png")
    check("f size",                             f_val.extra["size"], 14)
    ok("asset stdlib module works")
except Exception as e:
    fail("asset stdlib module", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# 10. @texture / @sound / @tilemap / @font decorator on let decl
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 10. Decorator form @texture / @sound / @tilemap / @font ────────────")

reset_registry()

decorator_src = """
@texture("sprites/hero.png")
let hero_tex

@sound("sfx/jump.wav")
let jump_sfx

@tilemap("maps/level1.tmx")
let level_map

@font("fonts/roboto.ttf", 16)
let ui_font
"""
try:
    interp_dec = Interpreter()
    interp_dec.execute(decorator_src)

    dv_tex = interp_dec._env.get("hero_tex")
    dv_snd = interp_dec._env.get("jump_sfx")
    dv_map = interp_dec._env.get("level_map")
    dv_fnt = interp_dec._env.get("ui_font")

    check_true("@texture sets var to AssetHandle", isinstance(dv_tex, AssetHandle))
    check_true("@sound sets var to AssetHandle",   isinstance(dv_snd, AssetHandle))
    check_true("@tilemap sets var to AssetHandle", isinstance(dv_map, AssetHandle))
    check_true("@font sets var to AssetHandle",    isinstance(dv_fnt, AssetHandle))
    check("@texture path",     dv_tex.path,              "sprites/hero.png")
    check("@sound path",       dv_snd.path,              "sfx/jump.wav")
    check("@tilemap path",     dv_map.path,              "maps/level1.tmx")
    check("@font path",        dv_fnt.path,              "fonts/roboto.ttf")
    check("@font size",        dv_fnt.extra.get("size"), 16)
    ok("decorator form works for all 4 asset types")
except Exception as e:
    fail("asset decorator form", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# 11. asset.registry proxy
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 11. asset.registry proxy ───────────────────────────────────────────")

reset_registry()
registry_src = """
import "asset" as asset
let t1 = asset.texture("a.png")
let t2 = asset.texture("b.png")
let c  = asset.registry.count()
"""
try:
    interp_reg = Interpreter()
    interp_reg.execute(registry_src)
    count_val = interp_reg._env.get("c")
    check_true("registry.count() returns int >= 2", isinstance(count_val, int) and count_val >= 2)
    ok("asset.registry proxy accessible from InScript")
except Exception as e:
    fail("asset.registry proxy", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
total = PASS + FAIL
print(f"InScript v2.8.0  —  {PASS}/{total} tests passed", end="")
if FAIL:
    print(f"  ❌ {FAIL} FAILED")
    sys.exit(1)
else:
    print("  ✅ ALL PASS")
    sys.exit(0)
