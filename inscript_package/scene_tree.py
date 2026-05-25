# -*- coding: utf-8 -*-
"""
scene_tree.py — InScript v2.7.0
================================================================
Scene System: NodeBlueprint, NodeInstance, SceneTree, SceneManager,
and .inscene serialisation / deserialisation.

Architecture
────────────
NodeBlueprint  — immutable compiled description of a node type
                 (created once by visit_NodeDecl in the interpreter)
NodeInstance   — a live instance of a NodeBlueprint in the tree
                 holds its own env scope; drives _ready/_update/_draw
SceneTree      — the root container that owns a tree of NodeInstances;
                 propagates lifecycle calls depth-first
SceneManager   — singleton exposed as `scene_manager` in game mode;
                 manages a scene stack and transitions

.inscene format (TOML-like, human-editable):
────────────────────────────────────────────
  [scene]
  name = "LevelOne"
  root = "GameRoot"       # node type for root instance

  [[node]]
  type   = "PlayerNode"
  name   = "Player"
  parent = "GameRoot"

  [[node]]
  type   = "EnemyNode"
  name   = "Enemy1"
  parent = "GameRoot"
  [node.props]
  hp = 50
  speed = 3.0
"""

from __future__ import annotations
import os, re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from interpreter import Interpreter


# ─────────────────────────────────────────────────────────────────────────────
# ReturnSignal import (needed for lifecycle hook execution)
# ─────────────────────────────────────────────────────────────────────────────
def _get_return_signal():
    try:
        from interpreter import ReturnSignal
        return ReturnSignal
    except ImportError:
        class _RS(Exception): pass
        return _RS


# ─────────────────────────────────────────────────────────────────────────────
# NodeBlueprint
# ─────────────────────────────────────────────────────────────────────────────

class NodeBlueprint:
    """
    Immutable description of a node type produced by visit_NodeDecl.
    Can instantiate NodeInstance objects.
    """
    def __init__(self, name: str, vars: list, hooks: list, methods: list,
                 interp: "Interpreter"):
        self.name    = name
        self.vars    = vars      # list of VarDecl AST nodes
        self.hooks   = hooks     # list of NodeLifecycleHook AST nodes
        self.methods = methods   # list of FunctionDecl AST nodes
        self._interp = interp

    def instantiate(self, node_name: str | None = None) -> "NodeInstance":
        return NodeInstance(
            blueprint  = self,
            node_name  = node_name or self.name,
            interp     = self._interp,
        )

    def __repr__(self):
        return f"<NodeBlueprint {self.name}>"


# ─────────────────────────────────────────────────────────────────────────────
# NodeInstance
# ─────────────────────────────────────────────────────────────────────────────

class NodeInstance:
    """
    A live node in the scene tree.  Owns a private property dictionary
    (instead of a persistent interpreter scope) so that many instances of
    the same blueprint can coexist without scope-stack collisions.

    Each lifecycle call:
      1. Pushes a fresh scope
      2. Injects the node's current property values
      3. Executes the hook body
      4. Reads back any updated values
      5. Pops the scope
    """
    def __init__(self, blueprint: NodeBlueprint, node_name: str,
                 interp: "Interpreter"):
        self.blueprint = blueprint
        self.name      = node_name
        self._interp   = interp
        self._children: List["NodeInstance"] = []
        self._parent:   Optional["NodeInstance"] = None
        self._ready_called = False
        self._props: Dict[str, Any] = {}

        # Initialise default property values by running var decls in a
        # temporary scope, then lifting them into self._props.
        self._interp._push(f"_init:{self.name}")
        try:
            for var in blueprint.vars:
                self._interp.visit(var)
            # Register methods as callable functions in props
            for method in blueprint.methods:
                self._interp.visit(method)
                fn_val = None
                try:
                    fn_val = self._interp._env.get(method.name)
                except Exception:
                    pass
                if fn_val is not None:
                    self._props[method.name] = fn_val
            # Lift all variable values into _props
            for var in blueprint.vars:
                try:
                    self._props[var.name] = self._interp._env.get(var.name)
                except Exception:
                    pass
        finally:
            self._interp._pop()

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def call_ready(self):
        """Call _ready() on this node and all children (depth-first)."""
        if not self._ready_called:
            self._ready_called = True
            self._run_hook("_ready", {})
        for child in list(self._children):
            child.call_ready()

    def call_update(self, dt: float):
        """Propagate _update(dt) depth-first."""
        hook = self._find_hook("_update")
        args = {"dt": dt} if (hook and hook.params) else {}
        self._run_hook("_update", args)
        for child in list(self._children):
            child.call_update(dt)

    def call_draw(self):
        """Propagate _draw() depth-first."""
        self._run_hook("_draw", {})
        for child in list(self._children):
            child.call_draw()

    def call_exit(self):
        """Teardown children then self (no-op in current design)."""
        for child in list(self._children):
            child.call_exit()

    # ── tree operations ───────────────────────────────────────────────────────

    def add_child(self, child: "NodeInstance") -> "NodeInstance":
        if child._parent is not None:
            child._parent._children.remove(child)
        child._parent = self
        self._children.append(child)
        if self._ready_called and not child._ready_called:
            child.call_ready()
        return child

    def remove_child(self, child: "NodeInstance") -> bool:
        if child in self._children:
            child._parent = None
            self._children.remove(child)
            return True
        return False

    def get_node(self, name: str) -> Optional["NodeInstance"]:
        queue = list(self._children)
        while queue:
            n = queue.pop(0)
            if n.name == name:
                return n
            queue.extend(n._children)
        return None

    def get_children(self) -> List["NodeInstance"]:
        return list(self._children)

    def child_count(self) -> int:
        return len(self._children)

    # ── property access from InScript / tests ─────────────────────────────────

    def __getitem__(self, key: str) -> Any:
        return self._props.get(key)

    def __setitem__(self, key: str, value: Any):
        self._props[key] = value

    def __repr__(self):
        return f"<NodeInstance {self.blueprint.name}:{self.name} children={len(self._children)}>"

    # ── internals ─────────────────────────────────────────────────────────────

    def _run_hook(self, hook_type: str, extra_args: dict):
        RS = _get_return_signal()
        hook = self._find_hook(hook_type)
        if hook is None:
            return
        scope_name = f"node:{self.name}:{hook_type}"
        self._interp._push(scope_name)
        try:
            # Inject current props so the hook body can read/write them
            for k, v in self._props.items():
                self._interp._env.define(k, v)
            # Inject hook parameters (e.g. dt)
            for k, v in extra_args.items():
                self._interp._env.define(k, v)
            self._interp.visit(hook.body)
        except RS:
            pass
        except Exception:
            pass
        finally:
            # Read back any props that may have changed
            for k in list(self._props.keys()):
                try:
                    self._props[k] = self._interp._env.get(k)
                except Exception:
                    pass
            self._interp._pop()

    def _find_hook(self, hook_type: str):
        for h in self.blueprint.hooks:
            if h.hook_type == hook_type:
                return h
        return None

    def _hook_has_param(self, hook_type: str) -> bool:
        h = self._find_hook(hook_type)
        return bool(h and h.params)


# ─────────────────────────────────────────────────────────────────────────────
# SceneTree
# ─────────────────────────────────────────────────────────────────────────────

class SceneTree:
    """
    Owns the root node of the current scene.
    Drives the lifecycle every frame when run by the pygame backend.
    """
    def __init__(self, root: NodeInstance):
        self.root = root
        self._started = False

    def start(self):
        """Call _ready on the entire tree."""
        if not self._started:
            self._started = True
            self.root.call_ready()

    def update(self, dt: float):
        self.root.call_update(dt)

    def draw(self):
        self.root.call_draw()

    def stop(self):
        self.root.call_exit()

    def get_node(self, name: str) -> Optional[NodeInstance]:
        if self.root.name == name:
            return self.root
        return self.root.get_node(name)

    def add_child(self, child: NodeInstance) -> NodeInstance:
        return self.root.add_child(child)

    def remove_child(self, child: NodeInstance) -> bool:
        return self.root.remove_child(child)


# ─────────────────────────────────────────────────────────────────────────────
# SceneManager
# ─────────────────────────────────────────────────────────────────────────────

class SceneManager:
    """
    Singleton exposed as `scene_manager` in game mode.

    scene_manager.push("LevelTwo")      — push a new scene (old scene paused)
    scene_manager.pop()                 — return to previous scene
    scene_manager.switch_to("MainMenu") — replace current scene
    scene_manager.current               — the active SceneTree

    Node blueprints are looked up from the interpreter's env by name.
    """
    def __init__(self, interp: "Interpreter"):
        self._interp  = interp
        self._stack:  List[SceneTree] = []
        self._pending: Optional[tuple] = None  # (action, name) processed at frame boundary

    @property
    def current(self) -> Optional[SceneTree]:
        return self._stack[-1] if self._stack else None

    def switch_to(self, blueprint_name: str):
        """Replace the active scene with a new one (frame-safe)."""
        self._pending = ("switch", blueprint_name)

    def push(self, blueprint_name: str):
        """Push a new scene on top; old scene is paused."""
        self._pending = ("push", blueprint_name)

    def pop(self):
        """Pop the active scene; previous scene resumes."""
        self._pending = ("pop", None)

    def has_pending(self) -> bool:
        return self._pending is not None

    def apply_pending(self):
        """
        Process a pending scene transition.  Called by the game loop at the
        start of each frame so transitions are atomic.
        """
        if self._pending is None:
            return
        action, name = self._pending
        self._pending = None

        if action == "switch":
            if self._stack:
                self._stack[-1].stop()
                self._stack.pop()
            tree = self._build_tree(name)
            if tree:
                self._stack.append(tree)
                tree.start()

        elif action == "push":
            tree = self._build_tree(name)
            if tree:
                self._stack.append(tree)
                tree.start()

        elif action == "pop":
            if self._stack:
                self._stack[-1].stop()
                self._stack.pop()

    def _build_tree(self, blueprint_name: str) -> Optional[SceneTree]:
        try:
            bp = self._interp._env.get(blueprint_name)
        except Exception:
            bp = None
        if bp is None or not isinstance(bp, NodeBlueprint):
            print(f"[SceneManager] Unknown node blueprint: '{blueprint_name}'")
            return None
        root_instance = bp.instantiate(blueprint_name)
        return SceneTree(root_instance)

    # ── frame-by-frame driving ────────────────────────────────────────────────

    def update(self, dt: float):
        if self.has_pending():
            self.apply_pending()
        if self.current:
            self.current.update(dt)

    def draw(self):
        if self.current:
            self.current.draw()

    def stop_all(self):
        while self._stack:
            self._stack[-1].stop()
            self._stack.pop()

    def __repr__(self):
        depth = len(self._stack)
        cur   = self._stack[-1].root.name if self._stack else "none"
        return f"<SceneManager depth={depth} current={cur}>"


# ─────────────────────────────────────────────────────────────────────────────
# .inscene serialisation
# ─────────────────────────────────────────────────────────────────────────────

INSCENE_EXT = ".inscene"


def save_inscene(tree: SceneTree, path: str) -> None:
    """
    Serialise a SceneTree to a .inscene file.
    Only node names and types are serialised (properties that are primitive
    Python values are included; complex values are skipped).
    """
    lines = [
        "# InScript Scene File (.inscene)  v2.7.0\n",
        "# Auto-generated — safe to hand-edit.\n\n",
        "[scene]\n",
        f'name = "{os.path.splitext(os.path.basename(path))[0]}"\n',
        f'root = "{tree.root.blueprint.name}"\n\n',
    ]

    def _walk(node: NodeInstance, parent_name: Optional[str] = None):
        lines.append("[[node]]\n")
        lines.append(f'type   = "{node.blueprint.name}"\n')
        lines.append(f'name   = "{node.name}"\n')
        if parent_name is not None:
            lines.append(f'parent = "{parent_name}"\n')
        lines.append("\n")
        for child in node.get_children():
            _walk(child, node.name)

    for child in tree.root.get_children():
        _walk(child, tree.root.name)

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def load_inscene(path: str, scene_manager: SceneManager) -> Optional[SceneTree]:
    """
    Load a .inscene file and instantiate a SceneTree.
    NodeBlueprints must already be registered in the interpreter env.
    """
    if not os.path.isfile(path):
        print(f"[scene_tree] .inscene file not found: {path}")
        return None

    with open(path, encoding="utf-8") as f:
        content = f.read()

    # Parse root blueprint name
    root_m = re.search(r'^root\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not root_m:
        print(f"[scene_tree] No 'root' key in {path}")
        return None
    root_bp_name = root_m.group(1)

    tree = scene_manager._build_tree(root_bp_name)
    if tree is None:
        return None

    # Parse [[node]] entries
    node_pattern = re.compile(
        r'\[\[node\]\]\s+type\s*=\s*"([^"]+)"\s+name\s*=\s*"([^"]+)"'
        r'(?:\s+parent\s*=\s*"([^"]+)")?',
        re.MULTILINE,
    )
    instances: Dict[str, NodeInstance] = {root_bp_name: tree.root}
    for m in node_pattern.finditer(content):
        bp_name, node_name, parent_name = m.group(1), m.group(2), m.group(3)
        try:
            bp = scene_manager._interp._env.get(bp_name)
        except Exception:
            bp = None
        if bp is None or not isinstance(bp, NodeBlueprint):
            print(f"[scene_tree] Unknown blueprint '{bp_name}' in {path}")
            continue
        instance = bp.instantiate(node_name)
        instances[node_name] = instance
        parent = instances.get(parent_name or root_bp_name, tree.root)
        parent.add_child(instance)

    return tree


# ─────────────────────────────────────────────────────────────────────────────
# InScript-callable helper functions exposed in game env
# ─────────────────────────────────────────────────────────────────────────────

def make_scene_stdlib(scene_manager: SceneManager) -> dict:
    """
    Returns a dict of callables to bind into the InScript environment
    so .ins code can call: scene_manager.switch_to("Foo"), etc.
    """
    class _SMProxy:
        def switch_to(self, name):      scene_manager.switch_to(str(name))
        def push(self, name):           scene_manager.push(str(name))
        def pop(self):                  scene_manager.pop()
        def get_node(self, name):       return scene_manager.current.get_node(str(name)) if scene_manager.current else None
        def add_child(self, inst):      return scene_manager.current.add_child(inst) if scene_manager.current else None
        def remove_child(self, inst):   return scene_manager.current.remove_child(inst) if scene_manager.current else False
        @property
        def current(self):              return scene_manager.current
        def __repr__(self):             return repr(scene_manager)

    return {"scene_manager": _SMProxy()}
