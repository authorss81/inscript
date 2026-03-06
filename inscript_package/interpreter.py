# inscript/interpreter.py  — Phase 4: Tree-Walking Interpreter
#
# Walks the AST and executes every node.
# After Lexer → Parser → Analyzer pass, this is what runs InScript programs.

from __future__ import annotations
import math, random, time
from typing import Any, Dict, List, Optional

from ast_nodes import *
from environment import Environment
from stdlib_values import (
    Vec2, Vec3, Color, Rect,
    InScriptFunction, InScriptInstance, InScriptRange, InScriptGenerator
)
import stdlib as _stdlib  # loads all built-in modules
from errors import (
    InScriptRuntimeError, NameError_, IndexError_,
    ReturnSignal, BreakSignal, ContinueSignal, YieldSignal, PropagateSignal
)


# ─────────────────────────────────────────────────────────────────────────────
# INTERPRETER
# ─────────────────────────────────────────────────────────────────────────────

class Interpreter(Visitor):
    """
    Tree-walking interpreter.  Visits each AST node and returns a Python value.
    """

    def __init__(self, source_lines: List[str] = None):
        self._src   = source_lines or []
        self._globals = Environment(name="global")
        self._env     = self._globals
        self._call_depth = 0
        self._MAX_CALL_DEPTH = 500

        self._register_builtins()

    # ── utilities ─────────────────────────────────────────────────────────────

    def _src_line(self, line: int) -> str:
        return self._src[line-1] if self._src and 0 < line <= len(self._src) else ""

    def _error(self, msg: str, line: int = 0):
        raise InScriptRuntimeError(msg, line, 0, self._src_line(line))

    def _push(self, name="block") -> Environment:
        self._env = Environment(parent=self._env, name=name)
        return self._env

    def _pop(self):
        self._env = self._env.parent

    # ── entry point ───────────────────────────────────────────────────────────

    def run(self, program: Program) -> Any:
        """Execute a full program."""
        return self.visit(program)

    def execute(self, source: str) -> Any:
        """Convenience: lex, parse, and run source code directly."""
        from parser import parse
        prog = parse(source)
        return self.run(prog)

    def _call_fn(self, fn, args: list):
        """Call an InScript function or Python callable with a list of args."""
        if callable(fn):
            return fn(*args)
        if isinstance(fn, InScriptFunction):
            return self._call_function(fn, args, [None]*len(args), 0, None)
        self._error(f"Cannot call {type(fn).__name__}")

    def _find_method(self, instance: InScriptInstance, method_name: str):
        """Search for a method (including inherited) on an InScriptInstance. Returns InScriptFunction or None."""
        try:
            decl = self._env.get(instance.struct_name, 0)
        except Exception:
            return None
        if not isinstance(decl, StructDecl):
            return None
        # Search instance methods + inherited chain
        current = decl
        while isinstance(current, StructDecl):
            for m in current.methods:
                if m.name == method_name:
                    fn = InScriptFunction(
                        name=m.name, params=m.params, body=m.body,
                        closure=self._env, return_type=m.return_type,
                    )
                    return fn
            current = getattr(current, '_resolved_parent', None)
        return None

    def _spawn_thread(self, fn, args: list):
        """Lightweight thread stub — runs fn in background thread."""
        import threading
        result = {"value": None, "done": False, "error": None}
        def _run():
            try:
                result["value"] = self._call_fn(fn, args)
            except Exception as e:
                result["error"] = str(e)
            finally:
                result["done"] = True
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        result["_thread"] = t
        return result

    # ── built-in functions ────────────────────────────────────────────────────

    def _register_builtins(self):
        """Populate the global scope with built-in callables and constants."""
        env = self._globals

        # ── I/O ──────────────────────────────────────────────────────────────
        def _print(*args):
            print(" ".join(_to_string(a) for a in args))
            return None

        def _input_fn(prompt=""):
            return input(prompt)

        # ── Math ─────────────────────────────────────────────────────────────
        def _clamp(v, lo, hi): return max(lo, min(hi, v))
        def _lerp(a, b, t): return a + (b - a) * t
        def _map_range(v, a1, b1, a2, b2):
            return a2 + (v - a1) / (b1 - a1) * (b2 - a2) if b1 != a1 else a2
        def _sign(v): return 1 if v > 0 else (-1 if v < 0 else 0)
        def _random_fn(*args):
            if len(args) == 0: return random.random()
            if len(args) == 1: return random.random() * args[0]
            return random.uniform(args[0], args[1])
        def _random_int(lo, hi): return random.randint(int(lo), int(hi))

        # ── Type conversions ─────────────────────────────────────────────────
        def _to_int(v):
            if isinstance(v, bool): return int(v)
            if isinstance(v, (int, float)): return int(v)
            if isinstance(v, str):
                try: return int(v)
                except ValueError: self._error(f"Cannot convert '{v}' to int")
            self._error(f"Cannot convert {type(v).__name__} to int")

        def _to_float(v):
            if isinstance(v, (int, float, bool)): return float(v)
            if isinstance(v, str):
                try: return float(v)
                except ValueError: self._error(f"Cannot convert '{v}' to float")
            self._error(f"Cannot convert {type(v).__name__} to float")

        def _to_string(v): return _inscript_str(v)
        def _to_bool(v):   return bool(v)

        # ── Game-type constructors ────────────────────────────────────────────
        def _vec2(*args):
            if len(args) == 0: return Vec2(0,0)
            if len(args) == 1: return Vec2(args[0], args[0])
            return Vec2(args[0], args[1])

        def _vec3(*args):
            if len(args) == 0: return Vec3(0,0,0)
            if len(args) == 3: return Vec3(*args)
            self._error("Vec3() takes 0 or 3 arguments")

        def _color(*args):
            if len(args) == 0: return Color(1,1,1,1)
            if len(args) == 3: return Color(args[0], args[1], args[2])
            if len(args) == 4: return Color(*args)
            self._error("Color() takes 0, 3, or 4 arguments")

        def _rect(*args):
            if len(args) == 4: return Rect(*args)
            self._error("Rect() takes 4 arguments (x, y, w, h)")

        # ── Array helpers ─────────────────────────────────────────────────────
        def _len(v):
            if isinstance(v, (list, str, dict)): return len(v)
            if isinstance(v, InScriptRange): return abs(v.end - v.start)
            self._error(f"len() does not support type {type(v).__name__}")

        # ── Time ──────────────────────────────────────────────────────────────
        def _time_now(): return time.time()

        # Register all
        native_fns = {
            "print":      _print,
            "input":      _input_fn,
            # math
            "sin":   math.sin,   "cos":  math.cos,   "tan":    math.tan,
            "asin":  math.asin,  "acos": math.acos,  "atan":   math.atan,
            "atan2": math.atan2, "sqrt": math.sqrt,  "log":    math.log,
            "log2":  math.log2,  "log10":math.log10, "exp":    math.exp,
            "abs":   abs,        "floor":math.floor, "ceil":   math.ceil,
            "round": round,      "pow":  pow,
            "clamp": _clamp,     "lerp": _lerp,
            "map_range": _map_range, "sign": _sign,
            "min":   min,        "max":  max,
            "random":      _random_fn,
            "random_int":  _random_int,
            # type conversion
            "int":    _to_int, "float": _to_float,
            "string": _to_string, "bool": _to_bool,
            # game types
            "Vec2":  _vec2, "Vec3":  _vec3,
            "Color": _color, "Rect": _rect,
            # array/string
            "len":   _len,
            # time
            "time":  _time_now,
            # ── Iteration helpers (range, map, filter, etc.) ──────────────────
            "range":      lambda *a: InScriptRange(
                              0 if len(a)==1 else int(a[0]),
                              int(a[0]) if len(a)==1 else int(a[1]),
                              int(a[2]) if len(a)>=3 else 1),
            "sort":       lambda lst, key=None: sorted(
                              lst, key=(lambda x: self._call_fn(key,[x]) if key else x)),
            "sorted":     lambda lst, key=None: sorted(
                              lst, key=(lambda x: self._call_fn(key,[x]) if key else x)),
            "map":        lambda lst, fn: [self._call_fn(fn, [x]) for x in lst],
            "filter":     lambda lst, fn: [x for x in lst if self._call_fn(fn, [x])],
            "reduce":     lambda lst, fn, init=None: (
                              __import__('functools').reduce(
                                  lambda a,b: self._call_fn(fn,[a,b]),
                                  lst, init) if init is not None
                              else __import__('functools').reduce(
                                  lambda a,b: self._call_fn(fn,[a,b]), lst)),
            "zip":        lambda *lists: [list(t) for t in zip(*lists)],
            "enumerate":  lambda lst, start=0: [[i+start, v] for i,v in enumerate(lst)],
            "reversed":   lambda lst: list(reversed(lst)),
            "sum":        sum,
            "any":        lambda lst, fn=None: any(self._call_fn(fn,[x]) for x in lst) if fn else any(lst),
            "all":        lambda lst, fn=None: all(self._call_fn(fn,[x]) for x in lst) if fn else all(lst),
            "flatten":    lambda lst: [x for sub in lst for x in (sub if isinstance(sub,list) else [sub])],
            "unique":     lambda lst: list(dict.fromkeys(lst)),
            "first":      lambda lst, fn=None: next((x for x in lst if (self._call_fn(fn,[x]) if fn else x)), None),
            "last":       lambda lst, fn=None: next((x for x in reversed(lst) if (self._call_fn(fn,[x]) if fn else x)), None),
            "count":      lambda lst, fn=None: sum(1 for x in lst if (self._call_fn(fn,[x]) if fn else x)),
            "chunk":      lambda lst, n: [lst[i:i+n] for i in range(0,len(lst),n)],
            "take":       lambda lst, n: lst[:n],
            "skip":       lambda lst, n: lst[n:],
            "find":       lambda lst, fn: next((x for x in lst if self._call_fn(fn,[x])), None),
            "includes":   lambda lst, v: v in lst,
            "index_of":   lambda lst, v: lst.index(v) if v in lst else -1,
            "fill":       lambda n, v: [v]*n,
            "repeat":     lambda v, n: [v]*n,
            # ── Dict global builtins ──────────────────────────────────────────
            "has_key":    lambda d, k: k in d,
            "keys":       lambda d: [k for k in d.keys() if not str(k).startswith("_")],
            "values":     lambda d: [v for k,v in d.items() if not str(k).startswith("_")],
            "dict_items": lambda d: [[k,v] for k,v in d.items() if not str(k).startswith("_")],
            "delete":     lambda d, k: d.pop(k, None),
            "merge":      lambda *dicts: {k:v for d in dicts for k,v in d.items()},
            # ── Dict helpers ──────────────────────────────────────────────────
            "has_key":    lambda d, k: k in d,
            "keys":       lambda d: [k for k in d.keys() if not str(k).startswith("_")],
            "values":     lambda d: [v for k,v in d.items() if not str(k).startswith("_")],
            "entries":    lambda d: [[k,v] for k,v in d.items() if not str(k).startswith("_")],
            "delete":     lambda d, k: d.pop(k, None),
            "merge":      lambda *dicts: {k:v for d in dicts for k,v in d.items()},
            # ── String helpers ────────────────────────────────────────────────
            "upper":      lambda s: str(s).upper(),
            "lower":      lambda s: str(s).lower(),
            "trim":       lambda s: str(s).strip(),
            "split":      lambda s, sep=" ": list(str(s)) if sep == "" else str(s).split(sep),
            "join":       lambda lst, sep="": sep.join(str(x) for x in lst),
            "replace":    lambda s, a, b: str(s).replace(a, b),
            "starts_with":lambda s, p: str(s).startswith(p),
            "ends_with":  lambda s, p: str(s).endswith(p),
            "contains":   lambda s, p: p in str(s),
            "substring":  lambda s, a, b=None: str(s)[a:b],
            "pad_left":   lambda s, n, c=" ": str(s).rjust(n, c),
            "pad_right":  lambda s, n, c=" ": str(s).ljust(n, c),
            "char_code":  lambda s: ord(s[0]) if s else 0,
            "from_code":  lambda n: chr(int(n)),
            "stringify":  _to_string,
            "parse_int":  lambda s: int(s),
            "parse_float":lambda s: float(s),
            "format":     lambda fmt, *a: fmt.format(*a),
            # ── Math extras ───────────────────────────────────────────────────
            "hypot":   math.hypot,
            "degrees": math.degrees,
            "radians": math.radians,
            "cbrt":    lambda x: x**(1/3) if x>=0 else -((-x)**(1/3)),
            "gcd":     math.gcd,
            "factorial":math.factorial,
            "is_nan":  math.isnan,
            "is_inf":  math.isinf,
            "log2":    math.log2,
            "log10":   math.log10,
            "sinh":    math.sinh,
            "cosh":    math.cosh,
            "tanh":    math.tanh,
            "smoothstep": lambda e0,e1,x: (lambda t: t*t*(3-2*t))(max(0,min(1,(x-e0)/(e1-e0) if e1!=e0 else 0))),
            # ── I/O helpers ───────────────────────────────────────────────────
            "read_file":   lambda p: open(p).read(),
            "write_file":  lambda p, s: open(p,'w').write(s) and None,
            "append_file": lambda p, s: open(p,'a').write(s) and None,
            "read_lines":  lambda p: open(p).read().splitlines(),
            "exists":      lambda p: __import__('os').path.exists(p),
            "cwd":         lambda: __import__('os').getcwd(),
            "list_dir":    lambda p=".": __import__('os').listdir(p),
            # ── Type introspection ─────────────────────────────────────────────
            "typeof":      lambda v: (v.struct_name if isinstance(v, InScriptInstance) else
                                      v.get("_enum", "enum") if isinstance(v, dict) and "_variant" in v else
                                      "nil"   if v is None else
                                      "bool"  if isinstance(v, bool) else
                                      "int"   if isinstance(v, int) else
                                      "float" if isinstance(v, float) else
                                      "str"   if isinstance(v, str) else
                                      "array" if isinstance(v, list) else
                                      "dict"  if isinstance(v, dict) else
                                      type(v).__name__),
            "implements":  lambda inst, iface_name: (
                               isinstance(inst, InScriptInstance) and
                               iface_name in getattr(
                                   self._env.get(inst.struct_name, 0) if inst.struct_name else {},
                                   '_implements', [])),
            "fields_of":   lambda v: (list(v.fields.keys()) if isinstance(v, InScriptInstance) else []),
            "methods_of":  lambda name: ([m.name for m in self._env.get(name, 0).methods]
                                          if isinstance(self._env.get(name, 0), StructDecl) else []),
            "is_null":     lambda v: v is None,
            "is_int":      lambda v: isinstance(v, int) and not isinstance(v, bool),
            "is_float":    lambda v: isinstance(v, float),
            "is_string":   lambda v: isinstance(v, str),
            "is_bool":     lambda v: isinstance(v, bool),
            "is_array":    lambda v: isinstance(v, list),
            "is_dict":     lambda v: isinstance(v, dict),
            # ── Concurrency (lightweight stubs, full impl via async/await) ─────
            "thread":      lambda fn, *args: self._spawn_thread(fn, list(args)),
            "channel":      lambda cap=0: {"_type":"channel","_channel":__import__("queue").SimpleQueue(),"_cap":int(cap)},
            "make_channel": lambda cap=0: {"_type":"channel","_channel":__import__("queue").SimpleQueue(),"_cap":int(cap)},
            "chan_send":    lambda ch, v: ch["_channel"].put(v) if isinstance(ch,dict) and "_channel" in ch else None,
            "chan_recv":    lambda ch: ch["_channel"].get(timeout=5) if isinstance(ch,dict) and "_channel" in ch else None,
            "sleep":       lambda s: __import__('time').sleep(s),
            # ── JSON ──────────────────────────────────────────────────────────
            "json_encode": lambda v: __import__('json').dumps(v),
            "json_decode": lambda s: __import__('json').loads(s),
            # ── Assertions ────────────────────────────────────────────────────
            "assert_eq":   lambda a, b, msg="": (None if a == b else self._error(f"assert_eq failed: {a!r} != {b!r}" + (f" — {msg}" if msg else ""))),
            "assert_true": lambda v, msg="": (None if v else self._error(f"assert_true failed" + (f" — {msg}" if msg else ""))),
            "inspect":     lambda v: print(repr(v)),
            # ── Generator helpers ──────────────────────────────────────────────
            "next":        lambda g: (g.next() if isinstance(g, InScriptGenerator)
                                      else next(iter(g), None)),
            "collect":     lambda g, n=None: (
                               [g.next() for _ in range(n)] if n is not None
                               else list(iter(g))),
            "is_done":     lambda g: g._done if isinstance(g, InScriptGenerator) else True,
            # ── Result type (Ok / Err / error propagation ?) ─────────────────
            "Ok":          lambda v=None: {"_ok": v, "value": v, "_type": "Result"},
            "Err":         lambda e="error": {"_err": e, "error": e, "_type": "Result"},
            "is_ok":       lambda r: isinstance(r, dict) and "_ok" in r,
            "is_err":      lambda r: isinstance(r, dict) and "_err" in r,
            "is_nil":      lambda v: v is None,
            "is_int":      lambda v: isinstance(v, int) and not isinstance(v, bool),
            "is_float":    lambda v: isinstance(v, float),
            "is_str":      lambda v: isinstance(v, str),
            "is_bool":     lambda v: isinstance(v, bool),
            "is_array":    lambda v: isinstance(v, list),
            "is_dict":     lambda v: isinstance(v, dict) and "_variant" not in v and "_ok" not in v and "_err" not in v,
            "unwrap":      lambda r: (r["_ok"] if (isinstance(r, dict) and "_ok" in r)
                                      else self._error(f"unwrap() called on Err: {r.get('_err', r)}")),
            "unwrap_or":   lambda r, default: (r["_ok"] if (isinstance(r, dict) and "_ok" in r)
                                               else default),
            "unwrap_err":  lambda r: (r["_err"] if (isinstance(r, dict) and "_err" in r)
                                      else self._error("unwrap_err() called on Ok value")),
        }
        for name, fn in native_fns.items():
            env.define(name, fn)

        # ── Namespace constants ───────────────────────────────────────────────
        color_ns = {
            "RED": Color.RED, "GREEN": Color.GREEN, "BLUE": Color.BLUE,
            "WHITE": Color.WHITE, "BLACK": Color.BLACK,
            "YELLOW": Color.YELLOW, "CYAN": Color.CYAN, "MAGENTA": Color.MAGENTA,
            "TRANSPARENT": Color.TRANSPARENT,
        }
        vec2_ns  = {
            "ZERO": Vec2.ZERO, "ONE": Vec2.ONE, "UP": Vec2.UP,
            "DOWN": Vec2.DOWN, "LEFT": Vec2.LEFT, "RIGHT": Vec2.RIGHT,
        }
        vec3_ns  = {
            "ZERO": Vec3.ZERO, "ONE": Vec3.ONE, "UP": Vec3.UP,
            "FORWARD": Vec3.FORWARD, "RIGHT": Vec3.RIGHT,
        }
        math_ns  = {
            "PI": math.pi, "TAU": math.tau, "E": math.e,
            "INF": math.inf, "NAN": math.nan,
        }
        env.define("_Color_ns",  color_ns)
        env.define("_Vec2_ns",   vec2_ns)
        env.define("_Vec3_ns",   vec3_ns)
        env.define("_Math_ns",   math_ns)

        # stub namespaces for game APIs (replaced by real renderers later)
        env.define("draw",    _StubNamespace("draw"))
        env.define("draw3d",  _StubNamespace("draw3d"))
        env.define("audio",   _StubNamespace("audio"))
        env.define("input",   _StubNamespace("input"))
        env.define("scene",   _StubNamespace("scene"))
        env.define("world",   _StubNamespace("world"))
        env.define("network", _StubNamespace("network"))
        env.define("physics", _StubNamespace("physics"))

    # ── Program & declarations ────────────────────────────────────────────────

    def visit_Program(self, node: Program) -> Any:
        result = None
        for stmt in node.body:
            result = self.visit(stmt)
        return result

    def visit_VarDecl(self, node: VarDecl) -> Any:
        value = self.visit(node.initializer) if node.initializer else None
        self._env.define(node.name, value, is_const=node.is_const)
        return value

    def visit_FunctionDecl(self, node: FunctionDecl) -> Any:
        fn = InScriptFunction(
            name    = node.name,
            params  = node.params,
            body    = node.body,
            closure = self._env,
        )
        self._env.define(node.name, fn)
        return fn

    def visit_GeneratorFnDecl(self, node) -> Any:
        """Register a generator function (fn*). Calling it returns a generator object.

        Key design: each generator call gets its OWN isolated Interpreter instance
        that shares globals (so user-defined functions/structs are visible) but has
        a completely separate _env stack. This means the generator thread never
        touches the main thread's _env, eliminating all scope corruption bugs.
        """
        main_interp = self

        def _make_generator(*arg_vals):
            import queue as _queue, threading as _threading

            value_q  = _queue.Queue(1)   # generator → caller: yielded values
            resume_q = _queue.Queue(1)   # caller → generator: resume signals
            _DONE    = object()          # exhaustion sentinel

            # Capture caller's env for closure access (read-only from generator)
            closure_env = main_interp._env

            def _thread_body():
                # --- Build an isolated interpreter for this generator ----------
                # Use object.__new__ to skip __init__ (avoids double-registering
                # builtins) then wire up only the fields _call_function etc. need.
                gen_interp = object.__new__(Interpreter)
                gen_interp._src           = main_interp._src
                gen_interp._globals       = main_interp._globals   # shared globals
                gen_interp._call_depth    = 0
                gen_interp._MAX_CALL_DEPTH = main_interp._MAX_CALL_DEPTH

                # Fresh scope for this generator's local variables,
                # chained to the caller's scope so closures work.
                gen_env = Environment(parent=closure_env, name=f"gen:{node.name}")
                gen_interp._env = gen_env

                # Bind parameters inside the generator scope
                for i, param in enumerate(node.params):
                    default_val = (gen_interp.visit(param.default)
                                   if param.default else None)
                    val = arg_vals[i] if i < len(arg_vals) else default_val
                    gen_env.define(param.name, val)

                # Patch yield: instead of raising YieldSignal, block the thread
                # and hand the value to the caller via the queue.
                def _yield_hook(n):
                    val = gen_interp.visit(n.value) if n.value else None
                    value_q.put(val)    # give value to caller; caller resumes
                    resume_q.get()      # wait until caller calls next() again

                gen_interp.visit_YieldStmt = _yield_hook

                try:
                    for stmt in node.body.body:
                        gen_interp.visit(stmt)
                except ReturnSignal:
                    pass
                except Exception:
                    pass
                finally:
                    value_q.put(_DONE)   # signal that the generator is exhausted

            t = _threading.Thread(target=_thread_body, daemon=True)
            t.start()

            def _py_gen():
                """Python generator that bridges the queue protocol."""
                while True:
                    val = value_q.get()
                    if val is _DONE:
                        return
                    yield val
                    resume_q.put(None)   # tell generator thread to resume

            return InScriptGenerator(name=node.name, python_gen=_py_gen())

        self._env.define(node.name, _make_generator)
        return None

    def visit_YieldStmt(self, node) -> Any:
        """Raise YieldSignal — caught by the generator trampoline."""
        val = self.visit(node.value) if node.value else None
        raise YieldSignal(val)

    def visit_StructDecl(self, node: StructDecl) -> Any:
        """Register the struct definition so instances can be created.
        Handles inheritance, static methods, interface impl, and mixins."""

        # Resolve parent for inheritance
        if node.parent_name:
            try:
                parent = self._env.get(node.parent_name, node.line)
                node._resolved_parent = parent
            except Exception:
                node._resolved_parent = None
        else:
            node._resolved_parent = None

        # Apply mixins: copy mixin methods into this struct
        for mixin_name in (node.mixins or []):
            try:
                mixin = self._env.get(mixin_name, node.line)
                if isinstance(mixin, dict) and mixin.get("_type") == "mixin":
                    for method in mixin["_methods"]:
                        if not any(m.name == method.name for m in node.methods):
                            node.methods.append(method)
            except Exception:
                pass  # mixin not yet defined — forward reference

        # Build static method namespace so M.sq(5) works
        static_ns = {}
        for sm in (node.static_methods or []):
            fn = InScriptFunction(
                name=sm.name, params=sm.params,
                body=sm.body, closure=self._env,
                return_type=sm.return_type,
            )
            static_ns[sm.name] = fn
        node._static_ns = static_ns

        # Track interface implementations
        if not hasattr(node, '_implements'):
            node._implements = list(node.interfaces or [])

        self._env.define(node.name, node)    # store the AST node as the "constructor"
        return None

    def visit_SceneDecl(self, node: SceneDecl) -> Any:
        """
        Executing a scene declaration runs on_start immediately,
        then simulates a few update + draw frames (headless mode).
        In full engine mode the renderer manages the loop.
        """
        self._push("scene:" + node.name)

        # Define scene-level vars
        for var in node.vars:
            self.visit(var)

        # Register scene methods
        for method in node.methods:
            self.visit(method)

        # Run on_start
        for hook in node.hooks:
            if hook.hook_type == "on_start":
                self._run_hook(hook, {})

        # Headless simulation: run on_update 1 frame at dt=1/60
        for hook in node.hooks:
            if hook.hook_type == "on_update":
                args = {}
                if hook.params:
                    args[hook.params[0].name] = 1.0/60.0
                self._run_hook(hook, args)

        # Run on_draw
        for hook in node.hooks:
            if hook.hook_type == "on_draw":
                self._run_hook(hook, {})

        self._pop()
        return None

    def _run_hook(self, hook: LifecycleHook, arg_vals: dict):
        self._push("hook:" + hook.hook_type)
        for name, val in arg_vals.items():
            self._env.define(name, val)
        try:
            self.visit(hook.body)
        except ReturnSignal:
            pass
        self._pop()

    def visit_ImportDecl(self, node: ImportDecl) -> Any:
        """
        import "math"             → bind all exports into current scope
        import "math" as M        → bind module dict as M
        from "math" import sin    → bind only listed names
        import "./utils.ins"      → load InScript file, bring exports into scope
        import "./utils.ins" as U → load file, bind exports as namespace U
        """
        path = node.path

        # ── File import: path starts with ./ ../ / or ends in .ins ──────────
        if path.startswith(("./", "../", "/")) or path.endswith(".ins"):
            mod = self._load_inscript_file(path, node.line)
        else:
            # ── Built-in stdlib module ────────────────────────────────────────
            try:
                mod = _stdlib.load_module(path)
            except ImportError:
                self._error(
                    f"Module not found: '{path}'\n"
                    f"  Built-in modules: {list(_stdlib._MODULES.keys())}\n"
                    f"  File imports: use a path starting with ./ or ending in .ins",
                    node.line)
                return None

        if node.alias:
            self._env.define(node.alias, mod)
        elif node.names:
            for name in node.names:
                if name not in mod:
                    self._error(f"Module '{path}' has no export '{name}'", node.line)
                self._env.define(name, mod[name])
        else:
            for name, val in mod.items():
                if not name.startswith("_"):
                    self._env.define(name, val)
        return None

    def _load_inscript_file(self, path: str, line: int) -> dict:
        """Load an InScript source file, run it in an isolated scope, return its exports."""
        import os
        # Module cache to avoid re-loading the same file twice
        if not hasattr(self, '_file_module_cache'):
            self._file_module_cache = {}

        # Resolve path relative to the current working directory
        abs_path = os.path.abspath(path)
        if not abs_path.endswith(".ins"):
            abs_path += ".ins"

        if abs_path in self._file_module_cache:
            return self._file_module_cache[abs_path]

        if not os.path.exists(abs_path):
            self._error(f"File not found: '{abs_path}'", line)

        with open(abs_path, "r", encoding="utf-8") as f:
            source = f.read()

        from parser import parse as _parse
        prog = _parse(source, abs_path)

        # Run the file in a fresh child environment; collect exports
        module_env = Environment(parent=self._globals, name=f"module:{path}")
        module_env.define("__file__", abs_path)
        module_env.define("__exports__", {})

        saved_env = self._env
        self._env = module_env
        try:
            for stmt in prog.body:
                self.visit(stmt)
        finally:
            self._env = saved_env

        # Exports: everything explicitly marked export, or all public names if none
        exports = module_env._store.get("__exports__", {})
        if not exports:
            # No explicit exports — export everything non-private (functions, structs, consts)
            exports = {k: v for k, v in module_env._store.items()
                       if not k.startswith("_") and k != "__exports__"}

        self._file_module_cache[abs_path] = exports
        return exports

    def visit_ExportDecl(self, node: ExportDecl) -> Any:
        """export fn foo() — execute the inner declaration and register it as an export."""
        result = self.visit(node.decl)
        # Register into __exports__ if it exists in the current environment
        try:
            exports = self._env.get("__exports__", 0)
            if isinstance(exports, dict):
                decl = node.decl
                name = getattr(decl, 'name', None)
                if name:
                    try:
                        exports[name] = self._env.get(name, 0)
                    except Exception:
                        pass
        except Exception:
            pass
        return result

    def visit_EnumDecl(self, node: EnumDecl) -> Any:
        """Enum with optional ADT variants: enum Shape { Circle(r: float), Rect(w,h) }"""
        counter = 0
        enum_vals = {"_name": node.name}  # tag for runtime type info
        for variant in node.variants:
            if variant.fields:
                # ADT variant: factory function that creates tagged dict
                field_names = [f[0] for f in variant.fields]
                vname = variant.name
                def _make_adt(*args, _vname=vname, _fnames=field_names, _ename=node.name):
                    d = {"_variant": _vname, "_enum": _ename}
                    for i, fname in enumerate(_fnames):
                        d[fname] = args[i] if i < len(args) else None
                    return d
                enum_vals[variant.name] = _make_adt
                self._env.define(vname, _make_adt)
            else:
                raw = self.visit(variant.value) if variant.value else counter
                # Wrap in a tagged dict so typeof() returns "enum" and matching works
                val = {"_variant": variant.name, "_enum": node.name, "_value": raw}
                enum_vals[variant.name] = val
                counter = raw + 1 if isinstance(raw, int) else counter + 1
        # Mark as iterable enum namespace — for v in MyEnum iterates all variants
        enum_vals["_enum_definition"] = True
        self._env.define(node.name, enum_vals)
        return enum_vals

    def visit_InterfaceDecl(self, node) -> Any:
        """Register interface definition for runtime conformance checks."""
        iface = {
            "_type": "interface",
            "_name": node.name,
            "_methods": {m.name: m for m in node.methods},
            "_parents": getattr(node, 'parents', []),
        }
        self._env.define(node.name, iface)
        return iface

    def visit_ImplDecl(self, node) -> Any:
        """impl Drawable for Sprite — attach methods to struct's runtime definition."""
        try:
            struct_decl = self._env.get(node.struct_name, node.line)
        except Exception:
            self._error(f"Struct '{node.struct_name}' not found for impl block", node.line)

        if not isinstance(struct_decl, StructDecl):
            self._error(f"'{node.struct_name}' is not a struct", node.line)

        # Register methods onto the struct (merge into methods list)
        for method in node.methods:
            # Remove any existing method with same name, then append new one
            struct_decl.methods = [m for m in struct_decl.methods if m.name != method.name]
            struct_decl.methods.append(method)

        # Track which interfaces this struct implements
        if not hasattr(struct_decl, '_implements'):
            struct_decl._implements = []
        struct_decl._implements.append(node.trait_name)
        return None

    def visit_MixinDecl(self, node) -> Any:
        """Register mixin — struct can pull it in with 'with MixinName'."""
        mixin_def = {"_type": "mixin", "_name": node.name, "_methods": node.methods}
        self._env.define(node.name, mixin_def)
        return mixin_def

    # ── Statements ────────────────────────────────────────────────────────────

    def visit_BlockStmt(self, node: BlockStmt) -> Any:
        self._push("block")
        result = None
        try:
            for stmt in node.body:
                result = self.visit(stmt)
        finally:
            self._pop()
        return result

    def visit_ExprStmt(self, node: ExprStmt) -> Any:
        return self.visit(node.expr)

    def visit_PrintStmt(self, node: PrintStmt) -> Any:
        parts = [_inscript_str(self.visit(a)) for a in node.args]
        print(" ".join(parts))
        return None

    def visit_ReturnStmt(self, node: ReturnStmt) -> Any:
        val = self.visit(node.value) if node.value else None
        raise ReturnSignal(val)

    def visit_BreakStmt(self, node: BreakStmt) -> Any:
        raise BreakSignal(label=getattr(node, 'label', None))

    def visit_ContinueStmt(self, node: ContinueStmt) -> Any:
        raise ContinueSignal(label=getattr(node, 'label', None))

    def visit_IfStmt(self, node: IfStmt) -> Any:
        if _is_truthy(self.visit(node.condition)):
            return self.visit(node.then_branch)
        elif node.else_branch:
            return self.visit(node.else_branch)
        return None

    def visit_WhileStmt(self, node: WhileStmt) -> Any:
        while _is_truthy(self.visit(node.condition)):
            try:
                self._exec_block_no_scope(node.body)
            except BreakSignal as sig:
                if sig.label:
                    raise  # labeled break — let LabeledStmt handle it
                break
            except ContinueSignal as sig:
                if sig.label:
                    raise
                continue
        return None

    def visit_ForInStmt(self, node: ForInStmt) -> Any:
        iterable = self.visit(node.iterable)
        # Enum namespace: for v in MyEnum iterates all variants
        if isinstance(iterable, dict) and iterable.get("_enum_definition"):
            variants = [v for k, v in iterable.items()
                        if not k.startswith("_")]
            iterable = variants
        # Support list, range, InScriptRange, string, dict, generator
        if isinstance(iterable, InScriptRange):
            it = iter(iterable)
        elif isinstance(iterable, InScriptGenerator):
            it = iter(iterable)
        elif isinstance(iterable, (list, str, dict)):
            it = iter(iterable)
        else:
            self._error(f"Cannot iterate over {type(iterable).__name__}", node.line)

        for item in it:
            self._push("for")
            self._env.define(node.var_name, item)
            try:
                self._exec_block_no_scope(node.body)
            except BreakSignal as sig:
                self._pop()
                if sig.label:
                    raise  # labeled break — let LabeledStmt handle it
                break
            except ContinueSignal as sig:
                self._pop()
                if sig.label:
                    raise
                continue
            self._pop()
        return None

    def _exec_block_no_scope(self, block: BlockStmt):
        """Execute block body without pushing a new scope (caller manages scope)."""
        for stmt in block.body:
            self.visit(stmt)

    def visit_MatchStmt(self, node: MatchStmt) -> Any:
        subject = self.visit(node.subject)
        for arm in node.arms:
            adt_bindings = {}

            # Determine if this arm's pattern matches
            if arm.binding:
                # Binding arm: `case h if h <= 0` — always matches (guard decides)
                matched = True
            elif arm.pattern is None:
                matched = True   # wildcard _
            else:
                # ── Special case: Ok(v) / Err(e) patterns for Result type ──────
                if (isinstance(arm.pattern, CallExpr)
                        and isinstance(arm.pattern.callee, IdentExpr)
                        and arm.pattern.callee.name in ("Ok", "Err")
                        and isinstance(subject, dict)):
                    pname = arm.pattern.callee.name
                    if pname == "Ok" and "_ok" in subject:
                        matched = True
                        if arm.pattern.args:
                            arg_node = arm.pattern.args[0].value
                            if isinstance(arg_node, IdentExpr):
                                adt_bindings[arg_node.name] = subject["_ok"]
                    elif pname == "Err" and "_err" in subject:
                        matched = True
                        if arm.pattern.args:
                            arg_node = arm.pattern.args[0].value
                            if isinstance(arg_node, IdentExpr):
                                adt_bindings[arg_node.name] = subject["_err"]
                    else:
                        matched = False
                # ── ADT destructuring pattern: case Circle(r) or case Rectangle(w, h) ──
                elif (isinstance(arm.pattern, CallExpr)
                        and isinstance(subject, dict) and "_variant" in subject):
                    callee_node = arm.pattern.callee
                    if isinstance(callee_node, IdentExpr):
                        variant_name = callee_node.name
                    elif isinstance(callee_node, NamespaceAccessExpr):
                        variant_name = callee_node.member
                    else:
                        variant_name = None
                    matched = variant_name == subject.get("_variant")
                    if matched:
                        # Bind each positional arg name to the corresponding field value
                        field_vals = [(k, v) for k, v in subject.items()
                                      if not k.startswith("_")]
                        for i, arg in enumerate(arm.pattern.args):
                            if isinstance(arg.value, IdentExpr) and i < len(field_vals):
                                adt_bindings[arg.value.name] = field_vals[i][1]
                else:
                    pattern_val = self.visit(arm.pattern)
                    # ADT variant matching: case Shape.Circle (no destructuring)
                    if (isinstance(subject, dict) and "_variant" in subject
                            and isinstance(pattern_val, dict) and "_variant" in pattern_val):
                        matched = subject["_variant"] == pattern_val["_variant"]
                    else:
                        matched = subject == pattern_val

            if not matched:
                continue

            # Evaluate optional guard in a scope where binding is defined
            if arm.guard or arm.binding:
                self._push("match_guard")
                if arm.binding:
                    self._env.define(arm.binding, subject)
                if arm.guard:
                    guard_val = _is_truthy(self.visit(arm.guard))
                    self._pop()
                    if not guard_val:
                        continue
                else:
                    self._pop()

            # Arm matched — execute body with bindings in scope
            self._push("match_arm")
            if arm.binding:
                self._env.define(arm.binding, subject)
            # Bind ADT destructuring names: case Circle(r) → r = radius value
            for bname, bval in adt_bindings.items():
                self._env.define(bname, bval)
            # Bind all ADT fields for wildcard arms
            if (isinstance(subject, dict) and "_variant" in subject
                    and arm.pattern is None and arm.binding is None):
                for k, v in subject.items():
                    if not k.startswith("_"):
                        self._env.define(k, v)
            try:
                result = self.visit(arm.body)
            finally:
                self._pop()
            return result
        return None

    def visit_ThrowStmt(self, node: ThrowStmt) -> Any:
        val = self.visit(node.value)
        raise InScriptRuntimeError(str(val), node.line)

    def visit_TryCatchStmt(self, node: TryCatchStmt) -> Any:
        try:
            self.visit(node.body)
        except InScriptRuntimeError as e:
            err_val = str(e.message)
            # Multi-catch: try each clause in order; match by type name if specified
            clauses = node.catch_clauses or ([{
                "var": node.catch_var, "type": node.catch_type, "handler": node.handler
            }] if node.catch_var or node.handler.body else [])
            handled = False
            for clause in clauses:
                c_type = clause.get("type")
                # If catch specifies a type, check it matches
                if c_type is not None:
                    type_name = c_type if isinstance(c_type, str) else getattr(c_type, 'name', None)
                    err_type  = getattr(e, 'error_type', None) or 'Error'
                    if type_name and err_type != type_name:
                        continue
                self._push("catch")
                if clause.get("var"):
                    self._env.define(clause["var"], err_val)
                self.visit(clause["handler"])
                self._pop()
                handled = True
                break
            if not handled:
                raise   # re-raise if no clause matched
        return None

    def visit_DecoratedDecl(self, node) -> Any:
        """@decorator fn foo() — evaluate target, then apply decorators in reverse."""
        # First define the target (fn/struct) normally
        self.visit(node.target)
        # Get the declared name
        target = node.target
        # Unwrap ExportDecl if needed
        inner = getattr(target, 'decl', target)
        name = getattr(inner, 'name', None)
        if name is None:
            return None  # anonymous or unsupported target
        fn_value = self._env.get(name, node.line)
        # Apply decorators outermost-first (reversed so innermost runs first)
        for dec_name, dec_args in reversed(node.decorators):
            try:
                decorator = self._env.get(dec_name, node.line)
            except Exception:
                self._error(f"Decorator '{dec_name}' is not defined", node.line)
            evaluated = [self.visit(a) for a in dec_args]
            fn_value = self._call_fn(decorator, evaluated + [fn_value])                        if evaluated else self._call_fn(decorator, [fn_value])
        self._env.set(name, fn_value)
        return None

    def visit_SelectStmt(self, node) -> Any:
        """select { case v = ch.recv() { } case ch.send(x) { } case timeout(t) { } }
        Tries each clause non-blockingly; runs the first ready one.
        Falls back to timeout clause if nothing is ready."""
        import threading as _threading
        timeout_clause = None
        recv_clauses   = []
        send_clauses   = []

        for cl in node.clauses:
            kind = cl.get("kind")
            if kind == "timeout":
                timeout_clause = cl
            elif kind == "recv":
                recv_clauses.append(cl)
            elif kind == "send":
                send_clauses.append(cl)

        import queue as _queue
        # Try recv channels non-blockingly first
        for cl in recv_clauses:
            # cl["channel"] may be a GetAttrExpr like ch.recv() — get the base object
            ch_node = cl["channel"]
            # unwrap method call: resolve the channel object from ch.recv() expression
            from ast_nodes import CallExpr, GetAttrExpr as GAE
            if isinstance(ch_node, CallExpr) and isinstance(ch_node.callee, GAE):
                ch = self.visit(ch_node.callee.obj)
            else:
                ch = self.visit(ch_node)
            if isinstance(ch, dict) and "_channel" in ch:
                q = ch["_channel"]
                try:
                    val = q.get_nowait()
                    self._push("select_recv")
                    if cl.get("var"):
                        # Try to update existing variable; fall back to define in new scope
                        try:
                            self._env.set(cl["var"], val, 0)
                        except Exception:
                            self._env.define(cl["var"], val)
                    self.visit(cl["body"])
                    self._pop()
                    return None
                except _queue.Empty:
                    pass  # channel empty, try next

        # Try send channels non-blockingly
        for cl in send_clauses:
            # send clause: the expression should be a call like ch.send(val)
            # We just execute it — if it would block we skip
            try:
                self.visit(cl["channel"])  # execute the send expression
                self._push("select_send")
                self.visit(cl["body"])
                self._pop()
                return None
            except Exception:
                pass

        # Fall back to timeout clause
        if timeout_clause is not None:
            dur = self.visit(timeout_clause["duration"])
            import time as _time
            _time.sleep(float(dur))
            self._push("select_timeout")
            self.visit(timeout_clause["body"])
            self._pop()

        return None

    def visit_WaitStmt(self, node: WaitStmt) -> Any:
        # In headless mode just sleep; in engine mode this would yield
        dur = self.visit(node.duration)
        time.sleep(float(dur))
        return None

    def visit_AIDecl(self, node: AIDecl) -> Any:
        return None   # Phase 16

    def visit_ShaderDecl(self, node: ShaderDecl) -> Any:
        return None   # Phase 14

    # ── Expressions ───────────────────────────────────────────────────────────

    def visit_IntLiteralExpr(self,   n): return n.value
    def visit_FloatLiteralExpr(self, n): return n.value
    def visit_StringLiteralExpr(self,n): return n.value
    def visit_BoolLiteralExpr(self,  n): return n.value
    def visit_NullLiteralExpr(self,  n): return None

    def visit_IdentExpr(self, node: IdentExpr) -> Any:
        return self._env.get(node.name, node.line)

    def visit_ArrayLiteralExpr(self, node: ArrayLiteralExpr) -> Any:
        result = []
        for elem in node.elements:
            if isinstance(elem, SpreadExpr):
                val = self.visit(elem.expr)
                if isinstance(val, (list, InScriptRange)):
                    result.extend(val)
                else:
                    self._error("Spread (...) in array literal requires an array", getattr(elem, 'line', 0))
            else:
                result.append(self.visit(elem))
        return result

    def visit_DictLiteralExpr(self, node: DictLiteralExpr) -> Any:
        d = {}
        for k, v in node.pairs:
            d[self.visit(k)] = self.visit(v)
        return d

    def visit_BinaryExpr(self, node: BinaryExpr) -> Any:
        left = self.visit(node.left)
        op   = node.op

        # Short-circuit logical operators
        if op == "&&": return _is_truthy(left) and _is_truthy(self.visit(node.right))
        if op == "||": return _is_truthy(left) or  _is_truthy(self.visit(node.right))

        right = self.visit(node.right)

        # Operator overloading: if left is an InScriptInstance, check for __add__, etc.
        _OP_MAP = {
            "+": "__add__", "-": "__sub__", "*": "__mul__", "/": "__div__",
            "%": "__mod__", "**": "__pow__", "==": "__eq__", "!=": "__ne__",
            "<": "__lt__", ">": "__gt__", "<=": "__le__", ">=": "__ge__",
        }
        if isinstance(left, InScriptInstance) and op in _OP_MAP:
            method_name = _OP_MAP[op]
            overload = self._find_method(left, method_name)
            if overload:
                return self._call_function(overload, [right], [None], node.line,
                                           self_instance=left)

        if op == "+":
            # String concatenation: coerce right to string if left is string
            if isinstance(left, str):
                return left + _inscript_str(right)
            if isinstance(right, str):
                return _inscript_str(left) + right
            return left + right
        if op == "-":  return left - right
        if op == "*":  return left * right
        if op == "/":
            if right == 0: self._error("Division by zero", node.line)
            return left / right
        if op == "//": 
            if right == 0: self._error("Division by zero", node.line)
            return int(left // right)
        if op == "%":
            if right == 0: self._error("Modulo by zero", node.line)
            return left % right
        if op == "**": return left ** right
        if op == "==": return left == right
        if op == "!=": return left != right
        if op == "<":  return left <  right
        if op == ">":  return left >  right
        if op == "<=": return left <= right
        if op == ">=": return left >= right
        # Bitwise
        if op == "&":  return int(left) & int(right)
        if op == "|":  return int(left) | int(right)
        if op == "^":  return int(left) ^ int(right)
        if op == "<<": return int(left) << int(right)
        if op == ">>": return int(left) >> int(right)

        self._error(f"Unknown binary operator: '{op}'", node.line)

    def visit_UnaryExpr(self, node: UnaryExpr) -> Any:
        val = self.visit(node.operand)
        if node.op == "-": return -val
        if node.op == "!": return not _is_truthy(val)
        if node.op == "~": return ~int(val)
        self._error(f"Unknown unary operator: '{node.op}'", node.line)

    def visit_AssignExpr(self, node: AssignExpr) -> Any:
        val = self.visit(node.value)
        op  = node.op
        target = node.target

        if op != "=":
            # Compound assignment: read current, apply op, write back
            cur = self.visit(target)
            sym_op = op[0]  # '+', '-', '*', '/'
            if sym_op == "+":
                val = (cur + _inscript_str(val)) if isinstance(cur, str) else cur + val
            elif sym_op == "-": val = cur - val
            elif sym_op == "*": val = cur * val
            elif sym_op == "/":
                if val == 0: self._error("Division by zero in compound assignment", node.line)
                val = cur / val
            elif sym_op == "%": val = cur % val

        # Write back to the target
        if isinstance(target, IdentExpr):
            self._env.set(target.name, val, node.line)
        elif isinstance(target, GetAttrExpr):
            obj = self.visit(target.obj)
            _set_attr(obj, target.attr, val, node.line, self)
        elif isinstance(target, IndexExpr):
            obj = self.visit(target.obj)
            idx = self.visit(target.index)
            try:
                obj[idx] = val
            except (IndexError, KeyError) as e:
                self._error(str(e), node.line)
        else:
            self._error("Invalid assignment target", node.line)
        return val

    def visit_SetAttrExpr(self, node: SetAttrExpr) -> Any:
        obj = self.visit(node.obj)
        val = self.visit(node.value)
        _set_attr(obj, node.attr, val, node.line, self)
        return val

    def visit_SetIndexExpr(self, node: SetIndexExpr) -> Any:
        obj = self.visit(node.obj)
        idx = self.visit(node.index)
        val = self.visit(node.value)
        try:
            obj[idx] = val
        except (IndexError, KeyError) as e:
            self._error(str(e), node.line)
        return val

    def visit_GetAttrExpr(self, node: GetAttrExpr) -> Any:
        obj = self.visit(node.obj)
        return _get_attr(obj, node.attr, node.line, self)

    def visit_IndexExpr(self, node: IndexExpr) -> Any:
        obj = self.visit(node.obj)
        idx = self.visit(node.index)
        # Range slice: a[1..4] or a[1..=4] -- works on lists AND strings
        if isinstance(idx, InScriptRange):
            if isinstance(obj, (list, str)):
                start = idx.start
                end   = idx.end + 1 if idx.inclusive else idx.end
                return obj[start:end]
            self._error(f"Cannot slice {type(obj).__name__} with a range", node.line)
        # String character indexing: s[0], s[-1]
        if isinstance(obj, str):
            if not isinstance(idx, int):
                self._error("String index must be an integer", node.line)
            real_idx = idx if idx >= 0 else len(obj) + idx
            if not (0 <= real_idx < len(obj)):
                self._error(f"String index {idx} out of range", node.line)
            return obj[real_idx]
        try:
            return obj[idx]
        except (IndexError, KeyError, TypeError) as e:
            self._error(f"Index error: {e}", node.line)

    def visit_NamespaceAccessExpr(self, node: NamespaceAccessExpr) -> Any:
        """Color::RED, Vec2::ZERO, Math::PI, EnumName::Variant, MyStruct::static_method"""
        # ── User-defined enum/struct takes priority over built-in namespaces ──
        try:
            ns = self._env.get(node.namespace, node.line)
            # Enum namespace: dict with _enum key
            if isinstance(ns, dict) and node.member in ns:
                return ns[node.member]
            # StructDecl: look for static methods in _static_ns
            from ast_nodes import StructDecl as _SD
            if isinstance(ns, _SD):
                if hasattr(ns, '_static_ns') and node.member in ns._static_ns:
                    return ns._static_ns[node.member]
                self._error(f"'{node.namespace}' has no static member '{node.member}'", node.line)
        except Exception as e:
            if "has no static" in str(e):
                raise
            pass

        # ── Built-in game namespaces ─────────────────────────────────────────
        ns_map = {
            "Color": "_Color_ns", "Vec2": "_Vec2_ns",
            "Vec3": "_Vec3_ns",   "Math": "_Math_ns",
        }
        if node.namespace in ns_map:
            ns = self._env.get(ns_map[node.namespace], node.line)
            if node.member in ns:
                return ns[node.member]
            self._error(f"'{node.namespace}' has no member '{node.member}'", node.line)

        self._error(f"Unknown namespace '{node.namespace}'", node.line)

    def visit_CallExpr(self, node: CallExpr) -> Any:
        # Resolve 'self' before evaluating callee so method calls bind the instance
        self_val = None
        if isinstance(node.callee, GetAttrExpr):
            obj = self.visit(node.callee.obj)
            if isinstance(obj, InScriptInstance):
                self_val = obj

        callee = self.visit(node.callee)

        # If the function was returned with a bound self (from _get_attr), use it
        if isinstance(callee, InScriptFunction) and hasattr(callee, '_bound_self'):
            if self_val is None:
                self_val = callee._bound_self

        # Evaluate arguments — expand SpreadExpr (...arr) inline
        arg_vals = []
        arg_names = []
        for arg in node.args:
            if isinstance(arg.value, SpreadExpr):
                spread_val = self.visit(arg.value.expr)
                if isinstance(spread_val, (list, InScriptRange)):
                    for item in spread_val:
                        arg_vals.append(item)
                        arg_names.append(None)
                else:
                    self._error("Spread operator requires an array", node.line)
            else:
                arg_vals.append(self.visit(arg.value))
                arg_names.append(arg.name)

        # Native Python function
        if callable(callee) and not isinstance(callee, (InScriptFunction, type)):
            try:
                return callee(*arg_vals)
            except InScriptRuntimeError:
                raise
            except Exception as e:
                self._error(f"Error in built-in function: {e}", node.line)

        # Struct constructor (StructDecl node stored as value)
        if isinstance(callee, StructDecl):
            return self._create_struct(callee, arg_vals, arg_names, node.line)

        # User-defined InScript function (with optional 'self' binding for methods)
        if isinstance(callee, InScriptFunction):
            return self._call_function(callee, arg_vals, arg_names, node.line,
                                       self_instance=self_val)

        self._error(f"'{node.callee}' is not callable — got {type(callee).__name__}", node.line)

    def _create_struct(self, decl: StructDecl, arg_vals, arg_names, line) -> InScriptInstance:
        """Create a struct instance, applying defaults for omitted fields.
        Raises if any abstract methods have not been overridden by this struct."""
        # Check abstract methods — collect all abstract from base chain
        abstract_required = set()
        implemented = set()
        # Walk up the inheritance chain
        d = decl
        while d is not None:
            for m in getattr(d, 'methods', []):
                if getattr(m, 'is_abstract', False):
                    abstract_required.add(m.name)
                else:
                    implemented.add(m.name)
            parent = getattr(d, 'parent_name', None)
            d = self._env.get(parent, line) if parent else None
            if isinstance(d, dict): d = None  # guard
        unimplemented = abstract_required - implemented
        if unimplemented:
            names = ', '.join(f"'{n}'" for n in sorted(unimplemented))
            self._error(
                f"Cannot instantiate '{decl.name}': abstract method(s) {names} not implemented",
                line)
        fields = {}
        # First apply defaults
        for field in decl.fields:
            if field.default:
                fields[field.name] = self.visit(field.default)
            else:
                fields[field.name] = None

        # Then apply provided args (by position or name)
        if arg_names and any(n is not None for n in arg_names):
            for name, val in zip(arg_names, arg_vals):
                if name: fields[name] = val
                else:
                    # positional among named — match by position
                    pos_idx = [i for i,n in enumerate(arg_names) if n is None].index(
                        arg_names.index(None))
                    fields[decl.fields[pos_idx].name] = val
        else:
            for i, val in enumerate(arg_vals):
                if i < len(decl.fields):
                    fields[decl.fields[i].name] = val

        # Register struct methods as bound functions
        inst = InScriptInstance(decl.name, fields)
        for method in decl.methods:
            bound = InScriptFunction(
                name    = method.name,
                params  = method.params,
                body    = method.body,
                closure = self._env,
            )
            inst.fields[method.name] = bound
        return inst

    def _call_function(self, fn: InScriptFunction, arg_vals, arg_names, line,
                       self_instance=None) -> Any:
        if self._call_depth >= self._MAX_CALL_DEPTH:
            self._error(f"Maximum call depth exceeded ({self._MAX_CALL_DEPTH}) — infinite recursion?", line)

        # Create new environment chained to closure
        call_env = Environment(parent=fn.closure, name=f"fn:{fn.name}")
        prev_env = self._env
        self._env = call_env
        self._call_depth += 1

        # Bind 'self' if this is a method call
        if self_instance is not None:
            call_env.define("self", self_instance)

        # Bind parameters
        if arg_names and any(n is not None for n in arg_names):
            # Named args
            name_to_val = {n: v for n, v in zip(arg_names, arg_vals) if n}
            pos_vals    = [v for n, v in zip(arg_names, arg_vals) if n is None]
            pos_idx     = 0
            for i, param in enumerate(fn.params):
                if getattr(param, 'is_variadic', False):
                    # Collect remaining positional args
                    call_env.define(param.name, pos_vals[pos_idx:])
                    break
                if param.name in name_to_val:
                    call_env.define(param.name, name_to_val[param.name])
                elif pos_idx < len(pos_vals):
                    call_env.define(param.name, pos_vals[pos_idx]); pos_idx += 1
                elif param.default:
                    call_env.define(param.name, self.visit(param.default))
                else:
                    call_env.define(param.name, None)
        else:
            for i, param in enumerate(fn.params):
                if getattr(param, 'is_variadic', False):
                    # Collect all remaining args into a list
                    call_env.define(param.name, arg_vals[i:])
                    break
                if i < len(arg_vals):
                    call_env.define(param.name, arg_vals[i])
                elif param.default:
                    call_env.define(param.name, self.visit(param.default))
                else:
                    call_env.define(param.name, None)

        # Execute body
        result = None
        try:
            for stmt in fn.body.body:
                self.visit(stmt)
        except ReturnSignal as r:
            result = r.value
        except PropagateSignal as sig:
            # `?` operator hit an Err — return the Err dict from this function
            result = sig.err_val
        finally:
            self._env = prev_env
            self._call_depth -= 1

        return result

    def visit_StructInitExpr(self, node: StructInitExpr) -> Any:
        """Player { health: 50, pos: Vec2(0,0) }"""
        try:
            decl = self._env.get(node.struct_name, node.line)
        except Exception:
            self._error(f"Unknown struct '{node.struct_name}'", node.line)

        if not isinstance(decl, StructDecl):
            self._error(f"'{node.struct_name}' is not a struct", node.line)

        # Check for unimplemented abstract methods
        abstract_req = set()
        concrete = set()
        d = decl
        while d is not None:
            for m in getattr(d, 'methods', []):
                if getattr(m, 'is_abstract', False):
                    abstract_req.add(m.name)
                else:
                    concrete.add(m.name)
            pname = getattr(d, 'parent_name', None)
            try: d = self._env.get(pname, node.line) if pname else None
            except: d = None
            if not isinstance(d, StructDecl): d = None
        missing = abstract_req - concrete
        if missing:
            self._error(
                f"Cannot instantiate '{decl.name}': abstract method(s) "
                + ", ".join(f"'{n}'" for n in sorted(missing)) + " not implemented",
                node.line)

        fields = {}
        # Defaults first
        for field in decl.fields:
            fields[field.name] = self.visit(field.default) if field.default else None

        # Then overrides from initializer
        for name, value_node in node.fields:
            fields[name] = self.visit(value_node)

        inst = InScriptInstance(decl.name, fields)
        for method in decl.methods:
            bound = InScriptFunction(method.name, method.params, method.body, self._env)
            inst.fields[method.name] = bound
        return inst

    def visit_LambdaExpr(self, node: LambdaExpr) -> Any:
        return InScriptFunction(
            name    = "<lambda>",
            params  = node.params,
            body    = node.body if isinstance(node.body, BlockStmt)
                      else BlockStmt(body=[ReturnStmt(value=node.body,
                                                       line=node.line, col=node.col)],
                                     line=node.line, col=node.col),
            closure = self._env,
        )

    def visit_RangeExpr(self, node: RangeExpr) -> Any:
        start = self.visit(node.start)
        end   = self.visit(node.end)
        return InScriptRange(start, end, inclusive=node.inclusive)

    def visit_AwaitExpr(self, node: AwaitExpr) -> Any:
        return self.visit(node.expr)   # synchronous in Phase 4

    def visit_SpawnExpr(self, node: SpawnExpr) -> Any:
        return None   # Phase 6 (ECS)

    def visit_MatchArm(self, node: MatchArm) -> Any:
        return self.visit(node.body)

    # ── Phase 31: New visitor methods ─────────────────────────────────────────

    def visit_TernaryExpr(self, node: TernaryExpr) -> Any:
        """cond ? then_expr : else_expr"""
        cond = self.visit(node.condition)
        return self.visit(node.then_expr) if cond else self.visit(node.else_expr)

    def visit_FStringExpr(self, node: FStringExpr) -> Any:
        """f"Hello {name}, score={score}" — evaluate {expr} segments at runtime.
        {{ and }} in source produce literal braces (stored as \x00{ and }\x00 sentinels)."""
        import re
        result = []
        template = node.template
        pos = 0
        # Only match {expr} that are NOT sentinel-escaped (not preceded by \x00)
        for m in re.finditer(r'(?<!\x00)\{([^}\x00][^}]*)\}', template):
            result.append(template[pos:m.start()])
            expr_src = m.group(1).strip()
            try:
                from parser import parse
                prog = parse(expr_src)
                val = None
                for stmt in prog.body:
                    val = self.visit(stmt)
                result.append(_inscript_str(val))
            except Exception as e:
                result.append(f"{{{expr_src}}}")
            pos = m.end()
        result.append(template[pos:])
        # Remove sentinels: \x00{ → { and }\x00 → }
        final = "".join(result).replace("\x00{", "{").replace("}\x00", "}")
        return final

    def visit_DestructureDecl(self, node: DestructureDecl) -> Any:
        """let [a, b, c] = arr  |  let {x, y} = point  |  let [[a,b],[c,d]] = nested"""
        val = self.visit(node.initializer) if node.initializer is not None else None
        self._destructure_apply(node, val)
        return None

    def _destructure_apply(self, node: "DestructureDecl", val: Any) -> None:
        """Apply a destructure pattern to a concrete value (used recursively for nesting)."""
        if node.is_object:
            for i, key in enumerate(node.names):
                alias = node.aliases[i] if node.aliases and i < len(node.aliases) else key
                if isinstance(val, InScriptInstance):
                    field_val = val.fields.get(key)
                elif isinstance(val, dict):
                    field_val = val.get(key)
                else:
                    field_val = None
                self._env.define(alias, field_val, is_const=node.is_const)
        else:
            lst = list(val) if val is not None else []
            for i, name in enumerate(node.names):
                item = lst[i] if i < len(lst) else None
                if isinstance(name, str):
                    if name == "_":
                        continue
                    self._env.define(name, item, is_const=node.is_const)
                else:
                    # Nested DestructureDecl — recurse with the sub-value
                    self._destructure_apply(name, item)

    def visit_SpreadExpr(self, node: SpreadExpr) -> Any:
        """...expr — in expression context, just return the value; expansion
        happens in visit_CallExpr when building arg lists."""
        return self.visit(node.expr)

    def visit_OptChainExpr(self, node: OptChainExpr) -> Any:
        """obj?.member — returns None if obj is null instead of erroring."""
        obj = self.visit(node.obj)
        if obj is None:
            return None
        return _get_attr(obj, node.member, node.line, self)

    def visit_NullishExpr(self, node: NullishExpr) -> Any:
        """left ?? right — evaluates right only if left is null."""
        val = self.visit(node.left)
        return self.visit(node.right) if val is None else val

    def visit_PipeExpr(self, node: PipeExpr) -> Any:
        """value |> fn — calls fn(value)."""
        val = self.visit(node.value)
        fn  = self.visit(node.fn)
        return self._call_fn(fn, [val])

    def visit_ComptimeExpr(self, node: ComptimeExpr) -> Any:
        """comptime { ... } — in an interpreted language, just run the block immediately."""
        self._push("comptime")
        result = None
        try:
            for stmt in node.body.body:
                result = self.visit(stmt)
        except ReturnSignal as r:
            result = r.value
        finally:
            self._pop()
        return result

    def visit_PropagateExpr(self, node: PropagateExpr) -> Any:
        """expr? — if Result is Ok(v) return v; if Err(e) raise PropagateSignal."""
        val = self.visit(node.expr)
        if isinstance(val, dict):
            if "_ok" in val:
                return val["_ok"]
            if "_err" in val:
                raise PropagateSignal(val)
        # Non-Result values pass through unchanged (permissive)
        return val

    def visit_TupleExpr(self, node) -> Any:
        """(a, b, c) — evaluates to a Python list acting as a tuple."""
        return [self.visit(e) for e in node.elements]

    def visit_TupleDestructureDecl(self, node) -> Any:
        """let (q, r) = divmod(17, 5) — binds each name to the corresponding element."""
        val = self.visit(node.initializer)
        # val should be a list (our tuple representation)
        if not isinstance(val, list):
            val = [val]
        for i, name in enumerate(node.names):
            item = val[i] if i < len(val) else None
            self._env.define(name, item, is_const=node.is_const)
        return None

    def visit_ListComprehensionExpr(self, node) -> Any:
        """[x*x for x in 1..=10 if x % 2 == 0]
        [f(x,y) for x in xs for y in ys if cond]"""
        def _expand(clauses, result):
            if not clauses:
                # All loop vars bound — evaluate outer condition and collect expr
                if node.condition is None or _is_truthy(self.visit(node.condition)):
                    result.append(self.visit(node.expr))
                return
            clause = clauses[0]
            rest   = clauses[1:]
            iterable = self.visit(clause["iterable"])
            if isinstance(iterable, InScriptRange):
                iterable = list(iterable)
            for item in iterable:
                self._push("comprehension")
                self._env.define(clause["var"], item)
                try:
                    # Check this clause's own per-item condition (if any)
                    if clause.get("condition") is not None:
                        if not _is_truthy(self.visit(clause["condition"])):
                            continue
                    _expand(rest, result)
                finally:
                    self._pop()

        # Build ordered clause list: first clause + extra_clauses
        clauses = [{"var": node.var, "iterable": node.iterable, "condition": None}]
        for ec in (node.extra_clauses or []):
            clauses.append(ec)

        result = []
        self._push("comprehension_outer")
        try:
            _expand(clauses, result)
        finally:
            self._pop()
        return result

    def visit_LabeledStmt(self, node: LabeledStmt) -> Any:
        """label: stmt — run inner stmt, intercept labeled breaks/continues."""
        try:
            self.visit(node.stmt)
        except BreakSignal as sig:
            if sig.label and sig.label != node.label:
                raise  # propagate to outer label
            # label matches or unlabeled — absorbed here
        except ContinueSignal as sig:
            if sig.label and sig.label != node.label:
                raise
        return None

    def generic_visit(self, node: Node) -> Any:
        return None  # graceful fallthrough for unimplemented nodes


# ─────────────────────────────────────────────────────────────────────────────
# ATTRIBUTE ACCESS HELPERS
# Handle Vec2/Vec3/Color/Rect fields + InScriptInstance fields + method calls
# ─────────────────────────────────────────────────────────────────────────────

def _get_attr(obj: Any, name: str, line: int, interp: Interpreter) -> Any:
    # StructDecl used as namespace for static method access: M.sq(5)
    if isinstance(obj, StructDecl):
        if hasattr(obj, '_static_ns') and name in obj._static_ns:
            return obj._static_ns[name]
        interp._error(f"Struct '{obj.name}' has no static method '{name}'", line)

    # InScript instance (user struct)
    if isinstance(obj, InScriptInstance):
        # Check property getters BEFORE direct field access
        if interp:
            try:
                decl = interp._env.get(obj.struct_name, 0)
            except Exception:
                decl = None
            if isinstance(decl, StructDecl):
                for prop in (decl.properties or []):
                    if prop.name == name and prop.getter_body:
                        fn = InScriptFunction(
                            name=f"get_{name}", params=[], body=prop.getter_body,
                            closure=interp._env,
                        )
                        return interp._call_function(fn, [], [], 0, self_instance=obj)
        if name in obj.fields:
            return obj.fields[name]
        # Use the centralised _find_method which handles inheritance
        fn = interp._find_method(obj, name)
        if fn:
            fn._bound_self = obj
            return fn
        interp._error(f"'{obj.struct_name}' has no attribute '{name}'", line)

    # Built-in game types
    if isinstance(obj, (Vec2, Vec3, Color, Rect)):
        try:
            return obj.get_attr(name)
        except AttributeError:
            pass

    # Lists: .length, .len, etc
    if isinstance(obj, list):
        return _list_method(obj, name, interp, line)

    # Dicts
    if isinstance(obj, dict):
        return _dict_method(obj, name, interp, line)

    # Strings
    if isinstance(obj, str):
        return _string_method(obj, name, interp, line)

    # Generator objects: gen.next(), gen.done
    if isinstance(obj, InScriptGenerator):
        if name == "next":   return obj.next
        if name == "done":   return obj._done
        if name == "value":  return obj._current

    # Stub namespace fallthrough
    if isinstance(obj, _StubNamespace):
        return _StubMethod(obj.name, name)

    interp._error(f"Cannot access attribute '{name}' on {type(obj).__name__}", line)


def _set_attr(obj: Any, name: str, val: Any, line: int, interp=None) -> None:
    if isinstance(obj, InScriptInstance):
        # Check property setters first
        if interp:
            try:
                decl = interp._env.get(obj.struct_name, 0)
            except Exception:
                decl = None
            if isinstance(decl, StructDecl):
                for prop in (decl.properties or []):
                    if prop.name == name and prop.setter_body:
                        # Build a proper param so _call_function binds it correctly
                        from ast_nodes import Param, TypeAnnotation
                        param_name = prop.setter_param or "value"
                        setter_fn = InScriptFunction(
                            name=f"set_{name}",
                            params=[Param(name=param_name, type_ann=None,
                                          line=0, col=0)],
                            body=prop.setter_body,
                            closure=interp._env,
                        )
                        interp._call_function(setter_fn, [val], [None], line,
                                              self_instance=obj)
                        return
        obj.set(name, val); return
    if isinstance(obj, (Vec2, Vec3, Color, Rect)):
        try: obj.set_attr(name, val); return
        except AttributeError: pass
    raise InScriptRuntimeError(f"Cannot set attribute '{name}'", line)


def _list_method(lst, name, interp, line):
    """Return a bound callable for list methods."""
    def push(val):    lst.append(val)
    def pop():        return lst.pop() if lst else None
    def pop_at(i):    return lst.pop(int(i))
    def insert(i, v): lst.insert(int(i), v)
    def remove(v):    lst.remove(v) if v in lst else None
    def contains(v):  return v in lst
    def reverse():    lst.reverse()
    def sort():       lst.sort(key=lambda x: (str(type(x)), x) if not isinstance(x, (int,float)) else (0, x))
    def clear():      lst.clear()
    def first():      return lst[0] if lst else None
    def last():       return lst[-1] if lst else None
    def slice_(a, b): return lst[int(a):int(b)]
    def join(sep=""):
        return sep.join(_inscript_str(x) for x in lst)
    def map_fn(fn):
        return [interp._call_function(fn, [x], [None], line)
                if isinstance(fn, InScriptFunction) else fn(x) for x in lst]
    def filter_fn(fn):
        return [x for x in lst
                if _is_truthy(interp._call_function(fn, [x], [None], line)
                              if isinstance(fn, InScriptFunction) else fn(x))]
    def reduce_fn(init, fn):
        acc = init
        for x in lst:
            acc = interp._call_function(fn, [acc, x], [None, None], line) \
                  if isinstance(fn, InScriptFunction) else fn(acc, x)
        return acc
    def find(fn):
        for x in lst:
            if _is_truthy(interp._call_function(fn, [x], [None], line)
                          if isinstance(fn, InScriptFunction) else fn(x)):
                return x
        return None
    def index_of(v): return lst.index(v) if v in lst else -1

    methods = {
        "push": push, "pop": pop, "pop_at": pop_at,
        "insert": insert, "remove": remove, "contains": contains,
        "reverse": reverse, "sort": sort, "clear": clear,
        "first": first, "last": last, "slice": slice_,
        "join": join, "map": map_fn, "filter": filter_fn,
        "reduce": reduce_fn, "find": find, "index_of": index_of,
        "length": len(lst), "len": len(lst),   # as properties
    }
    if name in methods:
        return methods[name]
    interp._error(f"Array has no method '{name}'", line)


def _dict_method(d, name, interp, line):
    # Channel objects: support .send(v) and .recv() methods
    if isinstance(d, dict) and d.get("_type") == "channel" and "_channel" in d:
        import queue as _q
        if name == "send":
            return lambda v: d["_channel"].put(v)
        if name == "recv":
            def _recv(timeout=None):
                try:
                    return d["_channel"].get(timeout=timeout) if timeout else d["_channel"].get_nowait()
                except _q.Empty:
                    return None
            return _recv
        if name == "empty":
            return d["_channel"].empty()
        if name == "size":
            return d["_channel"].qsize()

    # For enum namespaces and custom dicts: allow direct key access
    if name in d:
        return d[name]

    def get(k, default=None): return d.get(k, default)
    def set_(k, v): d[k] = v
    def has(k):     return k in d
    def remove(k):
        if k in d: del d[k]
    def keys():     return [k for k in d.keys() if not k.startswith("_")]
    def values():   return [v for k,v in d.items() if not k.startswith("_")]
    def items():    return [[k,v] for k,v in d.items() if not k.startswith("_")]
    def clear():    d.clear()

    methods = {
        "get": get, "set": set_, "has": has, "remove": remove,
        "keys": keys, "values": values, "items": items, "clear": clear,
        "length": len(d), "len": len(d),
    }
    if name in methods:
        return methods[name]
    interp._error(f"Dict has no method '{name}': available keys are {list(d.keys())}", line)


def _string_method(s, name, interp, line):
    methods = {
        "upper":       lambda: s.upper(),
        "lower":       lambda: s.lower(),
        "trim":        lambda: s.strip(),
        "trim_start":  lambda: s.lstrip(),
        "trim_end":    lambda: s.rstrip(),
        "split":       lambda sep=" ": s.split(sep),
        "starts_with": lambda prefix: s.startswith(prefix),
        "ends_with":   lambda suffix: s.endswith(suffix),
        "contains":    lambda sub: sub in s,
        "replace":     lambda old, new: s.replace(old, new),
        "to_int":      lambda: int(s),
        "to_float":    lambda: float(s),
        "chars":       lambda: list(s),
        "length": len(s), "len": len(s),
    }
    if name in methods:
        return methods[name]
    interp._error(f"String has no method '{name}'", line)


# ─────────────────────────────────────────────────────────────────────────────
# STUBS (game API namespaces — replaced by real backends in later phases)
# ─────────────────────────────────────────────────────────────────────────────

class _StubNamespace:
    """A namespace that accepts any attribute access and call without crashing."""
    def __init__(self, name): self.name = name
    def __repr__(self): return f"<{self.name}>"

class _StubMethod:
    """A callable stub for game API methods (draw.rect, audio.play, etc.)"""
    def __init__(self, ns, method): self.ns = ns; self.method = method
    def __call__(self, *args, **kwargs): return None  # no-op in headless mode
    def __repr__(self): return f"<{self.ns}.{self.method}>"


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _is_truthy(val) -> bool:
    if val is None:   return False
    if val is False:  return False
    if val == 0:      return False
    if val == 0.0:    return False
    if isinstance(val, str)  and val == "": return False
    if isinstance(val, list) and len(val) == 0: return False
    return True

def _inscript_str(val) -> str:
    if val is None:  return "nil"
    if val is True:  return "true"
    if val is False: return "false"
    if isinstance(val, list):
        return "[" + ", ".join(_inscript_str(v) for v in val) + "]"
    if isinstance(val, float):
        # Always show at least one decimal place: 4.0 → "4.0", 3.14 → "3.14"
        if val == int(val) and not (val != val):  # not NaN
            return f"{int(val)}.0"
        return str(val)
    if isinstance(val, str):
        return val  # bare string — no quotes when printing
    if isinstance(val, dict):
        # Result types
        if "_ok" in val:
            return f"Ok({_inscript_str(val['_ok'])})"
        if "_err" in val:
            return f"Err({_inscript_str(val['_err'])})"
        # ADT enum with fields: Circle{r: 5.0}
        if "_variant" in val and "_enum" in val:
            fields = {k: v for k, v in val.items() if not k.startswith("_")}
            if "_value" not in val and not fields:
                # Simple non-ADT variant stored as tagged dict
                return f"{val['_enum']}::{val['_variant']}"
            if fields:
                field_str = ", ".join(f"{k}: {_inscript_str(v)}" for k, v in fields.items())
                return f"{val['_variant']}({field_str})"
            # Simple variant wrapped with _value
            return f"{val['_enum']}::{val['_variant']}"
    return str(val)


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def run(source: str) -> Any:
    """Lex, parse, and run InScript source code. Returns last expression value."""
    from parser import parse
    prog = parse(source)
    interp = Interpreter(source.splitlines())
    return interp.run(prog)
