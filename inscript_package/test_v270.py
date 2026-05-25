"""
test_v270.py — InScript v2.7.0
================================================================
Scene System tests:
  • `node` keyword: lexing, parsing, NodeDecl AST
  • NodeBlueprint instantiation
  • NodeInstance: _ready / _update / _draw lifecycle
  • Scene tree: add_child, remove_child, get_node, child_count
  • Lifecycle propagation depth-first through tree
  • SceneTree: start / update / draw / stop
  • SceneManager: switch_to, push, pop, apply_pending
  • .inscene: save_inscene / load_inscene round-trip
  • Backward compat: existing `scene` declarations still work

All tests are headless — no pygame required.
"""
import sys, os, tempfile, shutil
sys.path.insert(0, os.path.dirname(__file__))

from lexer        import Lexer, TT
from parser       import Parser
from ast_nodes    import NodeDecl, NodeLifecycleHook, SceneDecl
from interpreter  import Interpreter
from scene_tree   import (NodeBlueprint, NodeInstance, SceneTree,
                          SceneManager, save_inscene, load_inscene, INSCENE_EXT)

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

def run_inscript(source: str) -> Interpreter:
    interp = Interpreter(source.splitlines())
    interp.execute(source)
    return interp


# ─────────────────────────────────────────────────────────────────────────────
# 1. Lexer — node / _ready / _update / _draw keywords
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 1. Lexer — node keyword tokens ────────────────────────────────────")

src = "node _ready _update _draw"
tokens = Lexer(src).tokenize()
types = [t.type for t in tokens if t.type != TT.EOF]
check("'node' lexed as TT.NODE",          TT.NODE           in types, True)
check("'_ready' lexed as TT.ON_READY",    TT.ON_READY       in types, True)
check("'_update' lexed as TT.ON_NODE_UPDATE", TT.ON_NODE_UPDATE in types, True)
check("'_draw' lexed as TT.ON_NODE_DRAW",     TT.ON_NODE_DRAW   in types, True)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Parser — NodeDecl AST
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 2. Parser — NodeDecl AST ───────────────────────────────────────────")

node_src = """
node PlayerNode {
    let hp: int = 100
    _ready() { }
    _update(dt) { }
    _draw() { }
    fn shoot() { }
}
"""
tokens2 = Lexer(node_src).tokenize()
prog    = Parser(tokens2, node_src).parse()
decl    = next((s for s in prog.body if isinstance(s, NodeDecl)), None)
check_true("NodeDecl parsed",                  decl is not None)
check("NodeDecl name",                         decl.name,               "PlayerNode")
check("NodeDecl vars count",                   len(decl.vars),          1)
check("NodeDecl hooks count",                  len(decl.hooks),         3)
check("NodeDecl methods count",                len(decl.methods),       1)
hook_types = sorted(h.hook_type for h in decl.hooks)
check("hook types",                            hook_types,
      sorted(["_ready", "_update", "_draw"]))
_upd_hook = next(h for h in decl.hooks if h.hook_type == "_update")
check("_update has dt param",                  len(_upd_hook.params),   1)

# ─────────────────────────────────────────────────────────────────────────────
# 3. NodeBlueprint instantiation (no lifecycle bodies needed)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 3. NodeBlueprint instantiation ────────────────────────────────────")

_interp = Interpreter([])  # bare interpreter for blueprint tests

bp = NodeBlueprint(
    name    = "TestNode",
    vars    = [],
    hooks   = [],
    methods = [],
    interp  = _interp,
)
check("blueprint name",  bp.name, "TestNode")
inst = bp.instantiate("inst1")
check_true("instantiate returns NodeInstance", isinstance(inst, NodeInstance))
check("instance name",   inst.name,            "inst1")
check("instance blueprint ref", inst.blueprint, bp)

# ─────────────────────────────────────────────────────────────────────────────
# 4. NodeInstance — lifecycle execution
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 4. NodeInstance — lifecycle ────────────────────────────────────────")

lifecycle_src = """
node LifeNode {
    let ready_called: bool = false
    let update_count: int  = 0
    let draw_count:   int  = 0

    _ready()  { ready_called = true }
    _update(dt) { update_count = update_count + 1 }
    _draw()   { draw_count = draw_count + 1 }
}
"""
interp_lc = Interpreter([])
interp_lc.execute(lifecycle_src)
bp_lc = interp_lc._env.get("LifeNode")
check_true("LifeNode blueprint registered", isinstance(bp_lc, NodeBlueprint))

inst_lc = bp_lc.instantiate("LifeNode")
check("ready_called before _ready is false", inst_lc["ready_called"], False)
inst_lc.call_ready()
check("ready_called after _ready is true",   inst_lc["ready_called"], True)
inst_lc.call_update(0.016)
inst_lc.call_update(0.016)
check("update_count after 2 updates",        inst_lc["update_count"], 2)
inst_lc.call_draw()
check("draw_count after 1 draw",             inst_lc["draw_count"],   1)

# _ready not called twice
inst_lc.call_ready()
check("_ready idempotent (ready_called stays true)", inst_lc["ready_called"], True)

# ─────────────────────────────────────────────────────────────────────────────
# 5. Scene tree operations
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 5. Scene tree operations ───────────────────────────────────────────")

_bp = lambda name: NodeBlueprint(name=name, vars=[], hooks=[], methods=[], interp=_interp)

root   = _bp("Root").instantiate("Root")
child1 = _bp("Child").instantiate("C1")
child2 = _bp("Child").instantiate("C2")
grand  = _bp("Grand").instantiate("G1")

root.add_child(child1)
root.add_child(child2)
child1.add_child(grand)

check("root child_count",          root.child_count(),   2)
check("child1 child_count",        child1.child_count(), 1)
check("get_node finds grandchild", root.get_node("G1"),  grand)
check("get_node returns None for unknown", root.get_node("NoNode"), None)
check("parent reference set",     child1._parent,       root)

# remove_child
root.remove_child(child2)
check("child_count after remove",  root.child_count(),   1)
check("parent cleared after remove", child2._parent,     None)

# get_children
children = root.get_children()
check("get_children returns list", children, [child1])

# reparenting
root2 = _bp("Root2").instantiate("Root2")
root2.add_child(child1)  # child1 already belonged to root
check("root child_count after reparent", root.child_count(),  0)
check("root2 has reparented child",      root2.child_count(), 1)

# ─────────────────────────────────────────────────────────────────────────────
# 6. Lifecycle propagation through tree
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 6. Lifecycle propagation ───────────────────────────────────────────")

counter_src = """
node CounterNode {
    let updates: int = 0
    let draws:   int = 0
    _update(dt) { updates = updates + 1 }
    _draw()     { draws   = draws   + 1 }
}
"""
interp_cnt = Interpreter([])
interp_cnt.execute(counter_src)
bp_cnt = interp_cnt._env.get("CounterNode")

root_cnt  = bp_cnt.instantiate("root")
child_cnt = bp_cnt.instantiate("child")
root_cnt.add_child(child_cnt)

tree = SceneTree(root_cnt)
tree.start()
tree.update(0.016)
tree.update(0.016)
tree.draw()

check("root updates propagated",  root_cnt["updates"],  2)
check("child updates propagated", child_cnt["updates"], 2)
check("root draws propagated",    root_cnt["draws"],    1)
check("child draws propagated",   child_cnt["draws"],   1)

# ─────────────────────────────────────────────────────────────────────────────
# 7. SceneManager
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 7. SceneManager ────────────────────────────────────────────────────")

sm_src = """
node MenuScene {
    let active: bool = false
    _ready() { active = true }
}
node GameScene {
    let score: int = 0
    _update(dt) { score = score + 1 }
}
"""
interp_sm = Interpreter([])
interp_sm.execute(sm_src)
sm = SceneManager(interp_sm)

check("no current scene initially", sm.current, None)

sm.switch_to("MenuScene")
sm.apply_pending()
check_true("current scene after switch_to", sm.current is not None)
check("stack depth after switch_to",        len(sm._stack), 1)

sm.push("GameScene")
sm.apply_pending()
check("stack depth after push",             len(sm._stack), 2)
check_true("current is GameScene",          sm.current.root.blueprint.name == "GameScene")

sm.pop()
sm.apply_pending()
check("stack depth after pop",              len(sm._stack), 1)
check_true("current is MenuScene again",    sm.current.root.blueprint.name == "MenuScene")

sm.switch_to("GameScene")
sm.apply_pending()
check("switch_to replaces (depth stays 1)", len(sm._stack), 1)
check_true("current is GameScene",          sm.current.root.blueprint.name == "GameScene")

sm.stop_all()
check("stop_all empties stack",             len(sm._stack), 0)
check("current is None after stop_all",     sm.current,     None)

# Unknown blueprint
sm.switch_to("NonExistentScene")
sm.apply_pending()
check("unknown blueprint doesn't crash", len(sm._stack), 0)

# ─────────────────────────────────────────────────────────────────────────────
# 8. .inscene save / load round-trip
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 8. .inscene save / load ────────────────────────────────────────────")

tmp = tempfile.mkdtemp(prefix="inscript_v270_")
try:
    inscene_path = os.path.join(tmp, "level1" + INSCENE_EXT)

    # Build a tree to save
    rt  = _bp("RootNode").instantiate("RootNode")
    n1  = _bp("PlayerNode").instantiate("Player")
    n2  = _bp("EnemyNode").instantiate("Enemy1")
    rt.add_child(n1)
    rt.add_child(n2)
    save_tree = SceneTree(rt)

    save_inscene(save_tree, inscene_path)
    check_true(".inscene file created", os.path.isfile(inscene_path))

    content = open(inscene_path).read()
    check_contains(".inscene contains root", content, 'root = "RootNode"')
    check_contains(".inscene contains PlayerNode type", content, 'type   = "PlayerNode"')
    check_contains(".inscene contains EnemyNode type",  content, 'type   = "EnemyNode"')
    check_contains(".inscene contains parent ref",       content, 'parent = "RootNode"')

    # Load it back
    sm_load_src = "node RootNode { }\nnode PlayerNode { }\nnode EnemyNode { }\n"
    interp_load = Interpreter([])
    interp_load.execute(sm_load_src)
    sm_load = SceneManager(interp_load)

    loaded_tree = load_inscene(inscene_path, sm_load)
    check_true("load_inscene returns SceneTree",  loaded_tree is not None)
    check("loaded root name",                     loaded_tree.root.name, "RootNode")
    check("loaded tree has 2 children",           loaded_tree.root.child_count(), 2)
    child_names = sorted(c.name for c in loaded_tree.root.get_children())
    check("loaded child names",                   child_names, ["Enemy1", "Player"])

    # load_inscene with missing file returns None
    result_missing = load_inscene(os.path.join(tmp, "missing.inscene"), sm_load)
    check("load_inscene missing file returns None", result_missing, None)

finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────────────
# 9. Backward compat — `scene` declarations still work
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 9. Backward compat — legacy `scene` declarations ───────────────────")

legacy_src = """
scene LegacyGame {
    let x: int = 0
    on_start()    { x = 10 }
    on_update(dt) { x = x + 1 }
    on_draw()     { }
}
"""
tokens_leg = Lexer(legacy_src).tokenize()
prog_leg   = Parser(tokens_leg, legacy_src).parse()
decl_leg   = next((s for s in prog_leg.body if isinstance(s, SceneDecl)), None)
check_true("SceneDecl still parses",            decl_leg is not None)
check("legacy scene name",                      decl_leg.name, "LegacyGame")

interp_leg = Interpreter([])
interp_leg.execute(legacy_src)  # should not raise
ok("legacy scene runs without crash")

# ─────────────────────────────────────────────────────────────────────────────
# 10. node + scene coexistence in same file
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 10. node + scene coexistence ───────────────────────────────────────")

mixed_src = """
node HUD {
    let visible: bool = true
    _ready() { visible = true }
}
scene MainGame {
    let running: bool = true
    on_start()    { running = true }
    on_update(dt) { }
    on_draw()     { }
}
"""
try:
    interp_mix = Interpreter([])
    interp_mix.execute(mixed_src)
    bp_hud = interp_mix._env.get("HUD")
    check_true("HUD blueprint registered in mixed file", isinstance(bp_hud, NodeBlueprint))
    ok("node + scene coexistence runs without crash")
except Exception as e:
    fail("node + scene coexistence", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
total = PASS + FAIL
print(f"InScript v2.7.0  —  {PASS}/{total} tests passed", end="")
if FAIL:
    print(f"  ❌ {FAIL} FAILED")
    sys.exit(1)
else:
    print("  ✅ ALL PASS")
    sys.exit(0)
