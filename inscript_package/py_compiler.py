"""Phase 7: InScript → Python AST Compiler.

Converts InScript game hooks to Python code objects via Python's ast module.
The generated code runs at native CPython speed (no interpreter dispatch overhead).
"""
import ast
import builtins
import typing as T
from ast_nodes import *

# ── helpers ──────────────────────────────────────────────────────────────────

def _name(id: str, ctx=ast.Load()) -> ast.Name:
    return ast.Name(id=id, ctx=ctx)

def _const(value) -> ast.Constant:
    return ast.Constant(value=value)

def _binop(left, op, right) -> ast.BinOp:
    return ast.BinOp(left=left, op=op, right=right)

def _boolop(left, op, right) -> ast.BoolOp:
    return ast.BoolOp(op=op, values=[left, right])

def _compare(left, ops: list, comparators: list) -> ast.Compare:
    return ast.Compare(left=left, ops=ops, comparators=comparators)

def _unaryop(op, operand) -> ast.UnaryOp:
    return ast.UnaryOp(op=op, operand=operand)

def _call(func, args=None, keywords=None) -> ast.Call:
    return ast.Call(func=func, args=args or [], keywords=keywords or [])

def _attr(value, attr, ctx=ast.Load()) -> ast.Attribute:
    return ast.Attribute(value=value, attr=attr, ctx=ctx)

def _assign(targets, value) -> ast.Assign:
    return ast.Assign(targets=targets if isinstance(targets, list) else [targets], value=value)

def _expr_stmt(value) -> ast.Expr:
    return ast.Expr(value=value)

def _return(value=None) -> ast.Return:
    return ast.Return(value=value)

def _pass() -> ast.Pass:
    return ast.Pass()

def _aug_assign(target, op, value) -> ast.AugAssign:
    return ast.AugAssign(target=target, op=op, value=value)

# ── operator mapping ─────────────────────────────────────────────────────────

_BINOP_MAP: T.Dict[str, type] = {
    "+":  ast.Add,
    "-":  ast.Sub,
    "*":  ast.Mult,
    "/":  ast.Div,
    "//": ast.FloorDiv,
    "%":  ast.Mod,
    "**": ast.Pow,
    "&":  ast.BitAnd,
    "|":  ast.BitOr,
    "^":  ast.BitXor,
    "<<": ast.LShift,
    ">>": ast.RShift,
}

_AUGOP_MAP: T.Dict[str, type] = {
    "+=":  ast.Add,
    "-=":  ast.Sub,
    "*=":  ast.Mult,
    "/=":  ast.Div,
    "//=": ast.FloorDiv,
    "%=":  ast.Mod,
    "**=": ast.Pow,
    "&=":  ast.BitAnd,
    "|=":  ast.BitOr,
    "^=":  ast.BitXor,
    "<<=": ast.LShift,
    ">>=": ast.RShift,
}

_CMPOP_MAP: T.Dict[str, type] = {
    "==": ast.Eq,
    "!=": ast.NotEq,
    "<":  ast.Lt,
    ">":  ast.Gt,
    "<=": ast.LtE,
    ">=": ast.GtE,
    "in":        ast.In,
    "not in":    ast.NotIn,
}

_UNARYOP_MAP: T.Dict[str, type] = {
    "-": ast.USub,
    "!": ast.Not,    # mapped to Python's `not`
    "~": ast.Invert,
}

# InScript builtins mapping to Python equivalents
_BUILTIN_MAP: T.Dict[str, str] = {
    "print":   "print",
    "println": "print",
    "string":  "str",
    "int":     "int",
    "float":   "float",
    "bool":    "bool",
    "len":     "len",
    "str":     "str",
    "typeof":  "type",
}

# Names that should never be treated as locals (always global/namespace lookup)
_GLOBAL_NAMES = frozenset({
    "screen", "draw", "draw3d", "input", "audio", "font", "math2d",
    "Color", "clock", "scene", "world",
    "WHITE","BLACK","RED","GREEN","BLUE","YELLOW","CYAN","MAGENTA",
    "ORANGE","GRAY","DARK_GRAY","LIGHT_GRAY","PURPLE","PINK",
    "TEAL","NAVY","LIME","BROWN","SKY","GOLD","TRANSPARENT",
    "Vec2","Vec3","Vec4","Rect",
    # InScript standard library functions (injected into globals by game engine)
    "clamp", "sin", "cos", "sqrt", "abs", "floor", "ceil", "round", "random",
    "lerp", "min", "max",
})

# ── CompileError ──────────────────────────────────────────────────────────────

class CompileError(Exception):
    """Raised when hook compilation fails — caller should fall back to AST walker."""


# ── name collection cache ─────────────────────────────────────────────────────
_names_cache: T.Dict[int, tuple] = {}  # id(node) -> (names_seen, names_assigned)


# ── HookCode ──────────────────────────────────────────────────────────────────

class HookCode:
    """Compiled hook ready for execution.

    The generated Python function signature is:
        def __hook(state, dt=None):
    where `state` is the shared scene-state dict and `dt` is the optional
    frame delta-time (on_update only).
    """
    __slots__ = ('code', 'param_count', 'name')
    def __init__(self, code, param_count: int, name: str = ""):
        self.code = code
        # param_count == len(params) — 0 for no-param hooks, 1 for on_update
        self.param_count = param_count
        self.name = name

    def exec(self, globals_dict: dict, args: list, state: dict = None):
        """Execute the compiled hook.

        globals_dict — game namespaces (draw, screen, input, etc.) injected
            into the function's __globals__.
        args — positional args for the hook (e.g. [dt] for on_update).
        state — shared scene state dict (all let variables).
        """
        if state is None:
            state = {}
        old_globals = self.code.__globals__.copy()
        try:
            self.code.__globals__.update(globals_dict)
            if self.param_count == 0:
                self.code(state)
            else:
                self.code(state, *args)
        finally:
            self.code.__globals__.clear()
            self.code.__globals__.update(old_globals)


class PyCompiler:
    """Compile InScript hook AST to Python code object."""

    def __init__(self):
        self._func_params: T.Set[str] = set()  # hook parameter names (Python locals)
        self._match_bindings: T.Set[str] = set()  # match-introduced variable names
        self._lambda_params: T.Set[str] = set()  # lambda parameter names

    def compile_hook(self, node, params: T.List[str] = None,
                     hook_name: str = "") -> T.Optional[HookCode]:
        """Compile a hook body (BlockStmt) to a Python callable.

        Returns HookCode or None if compilation fails (caller falls back).
        The generated function receives a `state` dict as first arg (shared
        scene state) and optional `dt` as second arg. Game namespaces (draw,
        screen, etc.) must be in the globals dict passed to HookCode.exec().
        """
        # Set function parameter names so _visit_IdentExpr treats them as
        # Python locals (LOAD_FAST), not state dict lookups.
        self._func_params = set(params or [])

        # Collect all variable names BEFORE conversion so _visit knows
        # which names are scene state vs. game namespaces vs. builtins.
        self._collect_names(node)

        try:
            py_ast = self._convert(node)
        except CompileError:
            return None
        except Exception:
            return None
        if py_ast is None:
            return None

        # Wrap in a function — scene state via `state` dict, `dt` for update hooks
        func_args = [ast.arg(arg="state", annotation=None)]
        if params:
            func_args.append(ast.arg(arg="dt", annotation=None))

        body_stmts = py_ast.body if isinstance(py_ast, ast.Module) else (py_ast if isinstance(py_ast, list) else [py_ast])
        func_def = ast.FunctionDef(
            name="__hook",
            args=ast.arguments(
                posonlyargs=[],
                args=func_args,
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=body_stmts,
            decorator_list=[],
            returns=None,
        )
        mod = ast.Module(body=[func_def], type_ignores=[])
        ast.fix_missing_locations(mod)

        try:
            code = compile(mod, f"<inscript:{hook_name}>", "exec")
        except SyntaxError:
            return None

        ns = {}
        try:
            exec(code, ns)
        except Exception:
            return None

        fn = ns.get("__hook")
        if fn is None:
            return None

        return HookCode(fn, len(params) if params else 0, hook_name)

    def _collect_names(self, node):
        """Collect all IdentExpr names used in the AST (for scoping decisions)."""
        key = id(node)
        cached = _names_cache.get(key)
        if cached is not None:
            self._names_seen, self._names_assigned = cached
            return
        self._names_seen: set = set()
        self._names_assigned: set = set()
        self._walk(node)
        # Cache the exact set objects — they're only read after this point,
        # and each compile_hook call creates a fresh PyCompiler instance.
        _names_cache[key] = (self._names_seen, self._names_assigned)

    def _walk(self, node):
        """Walk AST and collect identifier names."""
        if isinstance(node, IdentExpr):
            self._names_seen.add(node.name)
        elif isinstance(node, AssignExpr):
            if isinstance(node.target, IdentExpr):
                self._names_assigned.add(node.target.name)
            self._walk(node.value)
            if not isinstance(node.target, IdentExpr):
                self._walk(node.target)
        elif isinstance(node, VarDecl):
            self._names_assigned.add(node.name)
            if node.initializer:
                self._walk(node.initializer)
        elif isinstance(node, BinaryExpr):
            self._walk(node.left); self._walk(node.right)
        elif isinstance(node, UnaryExpr):
            self._walk(node.operand)
        elif isinstance(node, CallExpr):
            self._walk(node.callee)
            for a in node.args:
                self._walk(a.value)
        elif isinstance(node, GetAttrExpr):
            self._walk(node.obj)
        elif isinstance(node, IndexExpr):
            self._walk(node.obj); self._walk(node.index)
        elif isinstance(node, IfStmt):
            self._walk(node.condition)
            self._walk(node.then_branch)
            if node.else_branch:
                self._walk(node.else_branch)
        elif isinstance(node, WhileStmt):
            self._walk(node.condition)
            self._walk(node.body)
            if node.else_branch:
                self._walk(node.else_branch)
        elif isinstance(node, ForInStmt):
            self._walk(node.iterable)
            self._walk(node.body)
            if node.else_branch:
                self._walk(node.else_branch)
        elif isinstance(node, BlockStmt):
            for s in node.body:
                self._walk(s)
        elif isinstance(node, ExprStmt):
            self._walk(node.expr)
        elif isinstance(node, ReturnStmt):
            if node.value:
                self._walk(node.value)
        elif isinstance(node, TernaryExpr):
            self._walk(node.condition)
            self._walk(node.then_expr)
            self._walk(node.else_expr)
        elif isinstance(node, ArrayLiteralExpr):
            for e in node.elements:
                self._walk(e)
        elif isinstance(node, DictLiteralExpr):
            for k, v in node.pairs:
                self._walk(k)
                self._walk(v)
        elif isinstance(node, RangeExpr):
            self._walk(node.start)
            self._walk(node.end)
        elif isinstance(node, MatchStmt):
            self._walk(node.subject)
            for arm in node.arms:
                self._walk(arm)
        elif isinstance(node, MatchArm):
            if node.pattern is not None:
                self._walk(node.pattern)
            if node.guard is not None:
                self._walk(node.guard)
            if node.body is not None:
                self._walk(node.body)
        elif isinstance(node, TypePattern):
            pass  # type_name and var_name are metadata, not sub-nodes
        elif isinstance(node, NamespaceAccessExpr):
            self._names_seen.add(node.namespace)
        elif isinstance(node, LambdaExpr):
            # Lambda params are NOT added to _names_assigned (lambda-local)
            self._walk(node.body)
        elif hasattr(node, 'body') and isinstance(node.body, list):
            for s in node.body:
                self._walk(s)

    def _convert(self, node) -> T.Optional[T.List[ast.AST]]:
        """Convert an InScript AST node to Python AST nodes."""
        method = getattr(self, f"_visit_{type(node).__name__}", None)
        if method is None:
            raise CompileError(f"Unsupported node type: {type(node).__name__}")
        return method(node)

    # ── statements ───────────────────────────────────────────────────────────

    def _visit_BlockStmt(self, node: BlockStmt) -> T.List[ast.AST]:
        stmts = []
        for stmt in node.body:
            result = self._convert(stmt)
            if result is not None:
                if isinstance(result, list):
                    stmts.extend(result)
                else:
                    stmts.append(result)
        return stmts

    def _visit_ExprStmt(self, node: ExprStmt) -> ast.AST:
        expr = self._convert(node.expr)
        # AssignExpr is already a statement (ast.Assign), don't wrap in Expr
        if isinstance(expr, (ast.Assign, ast.AugAssign)):
            return expr
        return _expr_stmt(expr)

    def _visit_ReturnStmt(self, node: ReturnStmt) -> ast.Return:
        if node.value is not None:
            val = self._convert(node.value)
        else:
            val = None
        return _return(val)

    def _visit_BreakStmt(self, node: BreakStmt) -> ast.Break:
        return ast.Break()

    def _visit_ContinueStmt(self, node: ContinueStmt) -> ast.Continue:
        return ast.Continue()

    def _visit_Pass(self, node=None) -> ast.Pass:
        return _pass()

    def _visit_PrintStmt(self, node: PrintStmt) -> ast.Expr:
        args = [self._convert(a) for a in node.args]
        if not args:
            args = [_const(None)]
        return _expr_stmt(_call(_name("print"), args))

    # ── declarations ─────────────────────────────────────────────────────────

    def _visit_VarDecl(self, node: VarDecl) -> ast.Assign:
        if node.initializer is not None:
            value = self._convert(node.initializer)
        else:
            value = _const(None)
        return _assign([
            ast.Subscript(value=_name("state"), slice=_const(node.name), ctx=ast.Store())
        ], value)

    # ── control flow ─────────────────────────────────────────────────────────

    def _visit_IfStmt(self, node: IfStmt) -> ast.If:
        test = self._convert(node.condition)
        then_body = self._convert(node.then_branch) or []
        if isinstance(then_body, ast.AST):
            then_body = [then_body]
        else_body = []
        if node.else_branch is not None:
            eb = self._convert(node.else_branch)
            if eb is not None:
                if isinstance(eb, list):
                    else_body = eb
                else:
                    else_body = [eb]
        return ast.If(test=test, body=then_body, orelse=else_body)

    def _visit_WhileStmt(self, node: WhileStmt) -> ast.While:
        test = self._convert(node.condition)
        body = self._convert(node.body) or []
        if isinstance(body, ast.AST):
            body = [body]
        # Only else_branch if the InScript node has a while-else
        orelse = []
        if node.else_branch is not None:
            eb = self._convert(node.else_branch)
            if eb is not None:
                orelse = [eb] if not isinstance(eb, list) else eb
        return ast.While(test=test, body=body, orelse=orelse)

    def _visit_ForInStmt(self, node: ForInStmt) -> ast.For:
        iterable = self._convert(node.iterable)
        target = _name(node.var_name, ast.Store())
        body = self._convert(node.body) or []
        if isinstance(body, ast.AST):
            body = [body]
        orelse = []
        if node.else_branch is not None:
            eb = self._convert(node.else_branch)
            if eb is not None:
                orelse = [eb] if not isinstance(eb, list) else eb
        return ast.For(target=target, iter=iterable, body=body, orelse=orelse)

    # ── expressions ──────────────────────────────────────────────────────────

    def _visit_IdentExpr(self, node: IdentExpr) -> ast.AST:
        name = node.name
        if name == "nil" or name == "null":
            return _const(None)
        if name == "true":
            return _const(True)
        if name == "false":
            return _const(False)
        # Function parameters are Python locals (LOAD_FAST)
        if name in self._func_params:
            return _name(name)
        # Match arm bindings are Python locals (introduced by match/case patterns)
        if name in self._match_bindings:
            return _name(name)
        # Lambda parameters are Python locals
        if name in self._lambda_params:
            return _name(name)
        # Game namespaces and remapped builtins: Python global/builtin lookup
        if name in _GLOBAL_NAMES:
            return _name(name)
        if name in _BUILTIN_MAP:
            return _name(_BUILTIN_MAP[name])
        # Scene variables (explicitly assigned via let or =): state["name"]
        if name in self._names_assigned:
            return ast.Subscript(
                value=_name("state"),
                slice=_const(name),
                ctx=ast.Load(),
            )
        # Python builtins (like map, filter, range, sum) — check dynamically
        if hasattr(builtins, name):
            return _name(name)
        # Everything else is scene state → read from state dict
        # (covers pre-populated scene vars that weren't assigned in this hook)
        return ast.Subscript(
            value=_name("state"),
            slice=_const(name),
            ctx=ast.Load(),
        )

    def _visit_IntLiteralExpr(self, node: IntLiteralExpr) -> ast.Constant:
        return _const(node.value)

    def _visit_FloatLiteralExpr(self, node: FloatLiteralExpr) -> ast.Constant:
        return _const(node.value)

    def _visit_StringLiteralExpr(self, node: StringLiteralExpr) -> ast.Constant:
        return _const(node.value)

    def _visit_BoolLiteralExpr(self, node: BoolLiteralExpr) -> ast.Constant:
        return _const(node.value)

    def _visit_NullLiteralExpr(self, node: NullLiteralExpr) -> ast.Constant:
        return _const(None)

    def _visit_ArrayLiteralExpr(self, node: ArrayLiteralExpr) -> ast.List:
        elts = [self._convert(e) for e in node.elements]
        return ast.List(elts=elts, ctx=ast.Load())

    def _visit_DictLiteralExpr(self, node: DictLiteralExpr) -> ast.Dict:
        keys = []
        values = []
        for pair in node.pairs:
            key_node, val_node = pair
            keys.append(self._convert(key_node))
            values.append(self._convert(val_node))
        return ast.Dict(keys=keys, values=values)

    def _visit_TernaryExpr(self, node: TernaryExpr) -> ast.IfExp:
        test = self._convert(node.condition)
        then_expr = self._convert(node.then_expr)
        else_expr = self._convert(node.else_expr)
        return ast.IfExp(test=test, body=then_expr, orelse=else_expr)

    def _visit_BinaryExpr(self, node: BinaryExpr) -> ast.AST:
        op = node.op
        left = self._convert(node.left)
        right = self._convert(node.right)

        # Short-circuit logical operators
        if op == "&&":
            return _boolop(left, ast.And(), right)
        if op == "||":
            return _boolop(left, ast.Or(), right)

        # Comparison operators
        if op in _CMPOP_MAP:
            return _compare(left, [_CMPOP_MAP[op]()], [right])

        # Arithmetic / bitwise operators
        if op in _BINOP_MAP:
            return _binop(left, _BINOP_MAP[op](), right)

        # Range operator
        if op == "..":
            return _call(_name("range"), [left, right])

        raise CompileError(f"Unsupported binary operator: '{op}'")

    def _visit_UnaryExpr(self, node: UnaryExpr) -> ast.AST:
        op = node.op
        operand = self._convert(node.operand)
        if op == "!":
            return _unaryop(ast.Not(), operand)
        if op == "-":
            return _unaryop(ast.USub(), operand)
        if op == "~":
            return _unaryop(ast.Invert(), operand)
        raise CompileError(f"Unsupported unary operator: '{op}'")

    def _visit_AssignExpr(self, node: AssignExpr) -> ast.AST:
        target = node.target
        value = self._convert(node.value)
        op = node.op

        # Resolve target — scene vars go through state dict; game namespaces
        # (screen, draw, etc.) cannot be reassigned, so everything else is state.
        if isinstance(target, IdentExpr):
            name = target.name
            if name in _GLOBAL_NAMES or name in _BUILTIN_MAP:
                target_node = _name(name, ast.Store())
            else:
                target_node = ast.Subscript(
                    value=_name("state"), slice=_const(name), ctx=ast.Store()
                )
        elif isinstance(target, GetAttrExpr):
            target_node = _attr(self._convert(target.obj), target.attr, ast.Store())
        elif isinstance(target, IndexExpr):
            target_node = ast.Subscript(
                value=self._convert(target.obj),
                slice=self._convert(target.index),
                ctx=ast.Store(),
            )
        else:
            raise CompileError(f"Unsupported assignment target: {type(target).__name__}")

        if op == "=":
            return _assign([target_node], value)
        elif op in _AUGOP_MAP:
            if isinstance(target, GetAttrExpr):
                loaded = _attr(self._convert(target.obj), target.attr, ast.Load())
                return _assign([target_node], _binop(loaded, _AUGOP_MAP[op](), value))
            if isinstance(target_node, ast.Subscript):
                # state[x] += val → state[x] = state[x] + val
                loaded = ast.Subscript(
                    value=_name("state"),
                    slice=target_node.slice,
                    ctx=ast.Load(),
                )
                return _assign([target_node], _binop(loaded, _AUGOP_MAP[op](), value))
            return _aug_assign(target_node, _AUGOP_MAP[op](), value)
        elif op == "??=":
            loaded = ast.Subscript(
                value=_name("state"), slice=_const(target.name), ctx=ast.Load()
            ) if isinstance(target, IdentExpr) else target_node
            return ast.If(
                test=ast.Compare(left=loaded, ops=[ast.Is()], comparators=[_const(None)]),
                body=[_assign([target_node], value)],
                orelse=[],
            )
        else:
            raise CompileError(f"Unsupported assignment operator: '{op}'")

    def _visit_GetAttrExpr(self, node: GetAttrExpr) -> ast.Attribute:
        obj = self._convert(node.obj)
        return _attr(obj, node.attr)

    def _visit_CallExpr(self, node: CallExpr) -> ast.Call:
        # Build callee
        if isinstance(node.callee, GetAttrExpr):
            # Method call: obj.method(...)
            obj = self._convert(node.callee.obj)
            callee = _attr(obj, node.callee.attr)
        elif isinstance(node.callee, IdentExpr):
            # Direct function call: foo(...)
            # Use _visit_IdentExpr so scene vars (lambda closures) resolve
            # to state["name"] rather than Python globals.
            callee = self._visit_IdentExpr(node.callee)
        else:
            callee = self._convert(node.callee)

        # Build args
        args = []
        keywords = []
        for arg in node.args:
            val = self._convert(arg.value)
            if arg.name is not None:
                keywords.append(ast.keyword(arg=arg.name, value=val))
            else:
                args.append(val)

        return _call(callee, args, keywords)

    def _visit_IndexExpr(self, node: IndexExpr) -> ast.Subscript:
        obj = self._convert(node.obj)
        index = self._convert(node.index)
        return ast.Subscript(value=obj, slice=index, ctx=ast.Load())

    def _visit_RangeExpr(self, node: RangeExpr) -> ast.Call:
        start = self._convert(node.start)
        end = self._convert(node.end)
        if node.inclusive:
            # 0..=10 → range(0, 11)
            end = _binop(end, ast.Add(), _const(1))
        return _call(_name("range"), [start, end])

    def _visit_NamespaceAccessExpr(self, node):
        """Color::RED → Color.RED (Python attribute access)."""
        return _attr(_name(node.namespace), node.member)

    def _fstring_segments(self, template: str):
        """Split f-string template into (kind, text) pairs — "lit" or "expr".
        Handles sentinel-escaped braces \x00{ and }\x00 (from {{ and }} in source),
        nested brace depth, and inline strings inside expressions.
        """
        segments = []
        i = 0
        n = len(template)
        lit_buf = []
        while i < n:
            ch = template[i]
            if ch == "\x00" and i + 1 < n and template[i + 1] == "{":
                lit_buf.append("{"); i += 2
            elif ch == "}" and i + 1 < n and template[i + 1] == "\x00":
                lit_buf.append("}"); i += 2
            elif ch == "{":
                if lit_buf:
                    segments.append(("lit", "".join(lit_buf))); lit_buf = []
                depth = 1; j = i + 1; in_str = None
                while j < n and depth > 0:
                    c2 = template[j]
                    if in_str:
                        if c2 == "\\" and j + 1 < n: j += 2; continue
                        if c2 == in_str: in_str = None
                    elif c2 in ('"', "'"):
                        in_str = c2
                    elif c2 == "{":
                        depth += 1
                    elif c2 == "}":
                        depth -= 1
                        if depth == 0: break
                    j += 1
                segments.append(("expr", template[i + 1:j]))
                i = j + 1
            else:
                lit_buf.append(ch); i += 1
        if lit_buf:
            segments.append(("lit", "".join(lit_buf)))
        return segments

    def _visit_FStringExpr(self, node):
        """f"Hello {name}, score={score:.1f}" → Python JoinedStr.

        Splits the template into literal/expr segments, converts each expr
        through _convert so scene vars become state["name"] lookups, and
        builds a Python ast.JoinedStr with FormattedValue entries.
        """
        from parser import Parser as _Parser
        from lexer import tokenize as _tokenize

        values = []
        for kind, text in self._fstring_segments(node.template):
            if kind == "lit":
                values.append(_const(text))
                continue
            # Expression segment: split off optional format spec {expr:spec}
            # Must handle :: (namespace access) correctly — detect double colon
            inner = text.strip()
            fmt_spec = None
            depth = 0; ternary_depth = 0; split_at = -1
            i = 0
            n = len(inner)
            while i < n:
                ch = inner[i]
                if ch in "([{": depth += 1
                elif ch in ")]}": depth -= 1
                elif ch == "?" and depth == 0: ternary_depth += 1
                elif ch == ":" and depth == 0:
                    if ternary_depth > 0:
                        ternary_depth -= 1
                    elif i + 1 < n and inner[i + 1] == ":":
                        # :: — namespace access, skip both colons
                        i += 1
                    else:
                        split_at = i
                        break
                i += 1
            if split_at > 0:
                expr_src = inner[:split_at].strip()
                fmt_spec = inner[split_at + 1:].strip()
            else:
                expr_src = inner

            # Parse the InScript expression source and convert it
            try:
                toks = _tokenize(expr_src, "<fstring>")
                p = _Parser(toks)
                prog = p.parse()
                # Extract the expression from the parsed program
                converted = None
                for stmt in prog.body:
                    if hasattr(stmt, 'expr'):
                        converted = self._convert(stmt.expr)
                    elif isinstance(stmt, ExprStmt):
                        converted = self._convert(stmt.expr)
                if converted is None:
                    raise CompileError(f"Empty f-string expression: {expr_src}")
            except Exception:
                raise CompileError(f"Cannot compile f-string expression: {expr_src}")

            fmt_spec_ast = _const(fmt_spec) if fmt_spec else None
            values.append(ast.FormattedValue(
                value=converted,
                conversion=-1,
                format_spec=fmt_spec_ast,
            ))

        return ast.JoinedStr(values=values)

    def _visit_LambdaExpr(self, node):
        """|x, y| x + y  →  Python lambda.

        The body may be a single expression (|x| x * 2) or a BlockStmt
        (|x| { return x * 2 }). Only single-expression bodies map directly
        to Python's ast.Lambda; block bodies must contain exactly one
        ReturnStmt with a value.
        """
        # Build Python function arguments from lambda params
        py_args = [ast.arg(arg=p.name) for p in node.params]

        # Register lambda parameter names so _visit_IdentExpr resolves them
        # as Python locals, not state dict lookups.
        prev_lambda = self._lambda_params.copy()
        for p in node.params:
            self._lambda_params.add(p.name)

        # Convert body
        if isinstance(node.body, BlockStmt):
            # Block body — extract single return expression or fail
            stmts = node.body.body
            if len(stmts) == 1 and isinstance(stmts[0], ReturnStmt) and stmts[0].value is not None:
                body = self._convert(stmts[0].value)
            else:
                self._lambda_params = prev_lambda
                raise CompileError("Lambda with multi-statement block body not supported")
        else:
            # Single expression body: |x| x * 2
            body = self._convert(node.body)

        self._lambda_params = prev_lambda

        return ast.Lambda(
            args=ast.arguments(
                posonlyargs=[],
                args=py_args,
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=body,
        )

    # ── unsupported — fallback will be used ──────────────────────────────────

    def _visit_FunctionDecl(self, node):
        raise CompileError("Function declarations not supported in hooks")

    def _visit_StructDecl(self, node):
        raise CompileError("Struct declarations not supported in hooks")

    def _visit_ClassDecl(self, node):
        raise CompileError("Class declarations not supported in hooks")

    def _visit_ForExpr(self, node):
        raise CompileError("List comprehensions not supported in hooks")

    def _convert_pattern(self, node, binding=None):
        """Convert InScript match pattern to Python ast.Match pattern node.

        InScript supports five pattern forms in match arms:
          - Wildcard: pattern=None, binding=None       → MatchAs()
          - Binding:  pattern=None, binding="h"         → MatchAs(name="h")
          - Type:     TypePattern(type_name, var_name)  → MatchClass(cls, [MatchAs(var)])
          - Literal:  ExprNode (int, string, etc.)      → MatchValue(value)
        """
        if node is None and binding is None:
            # Wildcard: `case _ { }`
            return ast.MatchAs()
        if node is None and binding is not None:
            # Binding only: `case h if guard { }`
            return ast.MatchAs(name=binding)
        if isinstance(node, TypePattern):
            # Type-narrowing: `case int x { }` or `case Vec2 v { }`
            cls_name = _name(node.type_name)
            var_pattern = ast.MatchAs(name=node.var_name)
            return ast.MatchClass(
                cls=cls_name,
                patterns=[var_pattern],
                kwd_attrs=[],
                kwd_patterns=[],
            )
        # Expression / literal pattern: `case 1 { }` or `case x + 1 { }`
        value = self._convert(node)
        return ast.MatchValue(value=value)

    def _visit_MatchStmt(self, node):
        subject = self._convert(node.subject)
        cases = []
        for arm in node.arms:
            pattern = self._convert_pattern(arm.pattern, arm.binding)

            # Collect bindings introduced by this arm's pattern BEFORE
            # converting guard/body so match-introduced names resolve as
            # Python locals (not state dict lookups).
            prev_bindings = self._match_bindings.copy()
            if arm.binding is not None:
                self._match_bindings.add(arm.binding)
            if isinstance(arm.pattern, TypePattern):
                self._match_bindings.add(arm.pattern.var_name)

            guard = None
            if arm.guard is not None:
                guard = self._convert(arm.guard)

            body = self._visit_BlockStmt(arm.body) if arm.body else []
            if isinstance(body, ast.AST):
                body = [body]
            if not body:
                body = [_pass()]

            # Restore bindings
            self._match_bindings = prev_bindings

            cases.append(
                ast.match_case(pattern=pattern, guard=guard, body=body)
            )
        return ast.Match(subject=subject, cases=cases)


# ── convenience API ──────────────────────────────────────────────────────────

def compile_hook(hook_node, params: T.List[str] = None,
                 hook_name: str = "") -> T.Optional[HookCode]:
    """Compile a scene hook body to a Python callable.  Returns None on failure."""
    compiler = PyCompiler()
    return compiler.compile_hook(hook_node, params, hook_name)


# ── test ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from lexer import Lexer
    from parser import Parser
    from analyzer import Analyzer, Symbol, T_ANY

    src = r'''
scene Test {
    on_update(dt: float) {
        let x = 10
        let y = 20
        let z = x + y
        if z > 25 {
            z = z * 2
        }
        print("z = " + string(z))
    }
}
'''
    toks = Lexer(src).tokenize()
    ast = Parser(toks).parse()
    analyzer = Analyzer()
    for n in ["screen", "draw", "input", "print", "string", "str", "int", "float"]:
        analyzer._scope.symbols[n] = Symbol(n, T_ANY, kind="var")
    analyzer.analyze(ast)

    scene = [n for n in ast.body if hasattr(n, 'name') and n.name == 'Test'][0]
    for hook in scene.hooks:
        params = [p.name for p in hook.params]
        hc = compile_hook(hook.body, params, hook.hook_type)
        if hc:
            print(f"✅ {hook.hook_type} compiled (params={params})")
            hc.exec({"print": print, "string": str}, [1/60], {"x": 10, "y": 20, "z": 30})
        else:
            print(f"❌ {hook.hook_type} compilation failed")
