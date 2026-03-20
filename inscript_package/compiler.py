# inscript/compiler.py  — Phase 6.1: Bytecode Compiler
#
# Walks the InScript AST and emits register-based bytecode for the VM.
# Register-based design (like Lua 5.4): each call frame owns a flat register array.

from __future__ import annotations
from enum import IntEnum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Any, Tuple
import struct as _struct, re as _re

from ast_nodes import *


# ─── OPCODES ──────────────────────────────────────────────────────────────────

class Op(IntEnum):
    LOAD_NIL=auto(); LOAD_TRUE=auto(); LOAD_FALSE=auto()
    LOAD_INT=auto(); LOAD_CONST=auto()
    LOAD_GLOBAL=auto(); STORE_GLOBAL=auto()
    LOAD_UPVAL=auto(); STORE_UPVAL=auto()
    MOVE=auto()
    ADD=auto(); SUB=auto(); MUL=auto(); DIV=auto()
    MOD=auto(); POW=auto(); IDIV=auto(); NEG=auto()
    BAND=auto(); BOR=auto(); BXOR=auto(); BNOT=auto(); BLSHIFT=auto(); BRSHIFT=auto()
    EQ=auto(); NEQ=auto(); LT=auto(); LTE=auto(); GT=auto(); GTE=auto()
    CONTAINS=auto(); NOT_CONTAINS=auto()
    NOT=auto()
    CONCAT=auto(); INTERP=auto()
    JUMP=auto(); JUMP_IF_FALSE=auto(); JUMP_IF_TRUE=auto(); JUMP_IF_NIL=auto()
    CALL=auto(); CALL_METHOD=auto(); RETURN=auto()
    MAKE_CLOSURE=auto(); CAPTURE_UPVAL=auto()
    MAKE_ARRAY=auto(); MAKE_DICT=auto(); MAKE_RANGE=auto()
    GET_INDEX=auto(); SET_INDEX=auto()
    GET_FIELD=auto(); SET_FIELD=auto()
    MAKE_INSTANCE=auto()
    ITER_START=auto(); ITER_NEXT=auto()
    IMPORT=auto()
    THROW=auto(); PUSH_HANDLER=auto(); POP_HANDLER=auto()
    PRINT=auto()
    CAST=auto(); IS_TYPE=auto()
    OP_CALL=auto()   # Phase 7: operator overload dispatch
    LINE=auto(); NOP=auto()

NIL_REG = 0xFFFF


# ─── INSTRUCTION ──────────────────────────────────────────────────────────────

@dataclass
class Instr:
    op: Op; a: int = 0; b: int = 0; c: int = 0; line: int = 0
    def __repr__(self): return f"{self.op.name:<16} {self.a:5} {self.b:5} {self.c:5}"


# ─── FUNCTION PROTOTYPE ───────────────────────────────────────────────────────

@dataclass
class FnProto:
    name: str
    params: List[str]             = field(default_factory=list)
    n_locals: int                 = 0
    code: List[Instr]             = field(default_factory=list)
    consts: List[Any]             = field(default_factory=list)
    names: List[str]              = field(default_factory=list)
    protos: List["FnProto"]       = field(default_factory=list)
    upval_descs: List[Any]        = field(default_factory=list)
    n_upvals: int                 = 0
    source_name: str              = "<script>"
    is_method: bool               = False
    param_defaults: dict          = field(default_factory=dict)  # BUG-23: name→AST default node

    def const_idx(self, v) -> int:
        for i, c in enumerate(self.consts):
            if type(c) is type(v) and c == v: return i
        self.consts.append(v); return len(self.consts)-1

    def name_idx(self, n: str) -> int:
        try: return self.names.index(n)
        except: self.names.append(n); return len(self.names)-1

    def emit(self, op, a=0, b=0, c=0) -> int:
        self.code.append(Instr(op, a, b, c)); return len(self.code)-1

    def disassemble(self) -> str:
        lines = [f"=== {self.name} ({len(self.code)} instrs) ==="]
        for i, ins in enumerate(self.code):
            ann = ""
            if ins.op == Op.LOAD_CONST and ins.b < len(self.consts):
                v = self.consts[ins.b]
                ann = f"  ; {v!r}" if not isinstance(v, FnProto) else f"  ; <fn {v.name}>"
            elif ins.op in (Op.LOAD_GLOBAL, Op.STORE_GLOBAL):
                idx = ins.b if ins.op == Op.LOAD_GLOBAL else ins.a
                if idx < len(self.names): ann = f"  ; '{self.names[idx]}'"
            elif ins.op in (Op.GET_FIELD, Op.SET_FIELD, Op.CALL_METHOD, Op.OP_CALL):
                idx = ins.c if ins.op == Op.GET_FIELD else ins.b
                if idx < len(self.names): ann = f"  ; '{self.names[idx]}'"
            lines.append(f"  {i:4d}  {ins!r}{ann}")
        for p in self.protos:
            lines.append(""); lines.append(p.disassemble())
        return "\n".join(lines)


# ─── SCOPE ────────────────────────────────────────────────────────────────────

@dataclass
class _Local:
    name: str; reg: int; depth: int; is_captured: bool = False

@dataclass
class _UpvalDesc:
    name: str; is_local: bool; index: int

class _Scope:
    def __init__(self, proto, parent=None):
        self.proto = proto; self.parent = parent
        self.locals: List[_Local]     = []
        self.upvals: List[_UpvalDesc] = []
        self.depth = 0; self.n_regs = 0

    def alloc(self):
        r = self.n_regs; self.n_regs += 1
        if self.n_regs > self.proto.n_locals: self.proto.n_locals = self.n_regs
        return r

    def free(self, r):
        if r == self.n_regs-1: self.n_regs -= 1

    def free_to(self, t): self.n_regs = t

    def add_local(self, name):
        r = self.alloc(); self.locals.append(_Local(name, r, self.depth)); return r

    def resolve_local(self, name):
        for loc in reversed(self.locals):
            if loc.name == name: return loc.reg
        return None

    def resolve_upval(self, name):
        if self.parent is None: return None
        reg = self.parent.resolve_local(name)
        if reg is not None:
            for loc in self.parent.locals:
                if loc.reg == reg and loc.name == name: loc.is_captured = True
            return self._add_upval(name, True, reg)
        uv = self.parent.resolve_upval(name)
        if uv is not None: return self._add_upval(name, False, uv)
        return None

    def _add_upval(self, name, is_local, index):
        for i, uv in enumerate(self.upvals):
            if uv.is_local == is_local and uv.index == index: return i
        self.upvals.append(_UpvalDesc(name, is_local, index))
        self.proto.n_upvals = len(self.upvals)
        return len(self.upvals)-1

    def begin_block(self): self.depth += 1
    def end_block(self):
        self.locals = [l for l in self.locals if l.depth < self.depth]
        self.depth -= 1


# ─── COMPILER ─────────────────────────────────────────────────────────────────

class Compiler:
    def __init__(self, source_name="<script>"):
        self._src = source_name
        self._proto = FnProto("<main>", source_name=source_name)
        self._scope = _Scope(self._proto)
        self._loop_starts = []
        self._break_patches = []
        self._cont_patches  = []

    # helpers
    def _e(self, op, a=0, b=0, c=0):
        idx = self._scope.proto.emit(op, a, b, c)
        self._scope.proto.code[idx].line = getattr(self, '_cur_line', 0)
        return idx
    def _alloc(self): return self._scope.alloc()
    def _free(self, r): self._scope.free(r)
    def _free_to(self, t): self._scope.free_to(t)
    def _top(self): return self._scope.n_regs
    def _const(self, v): return self._scope.proto.const_idx(v)
    def _name(self, n): return self._scope.proto.name_idx(n)

    def _load_lit(self, v, dst):
        if v is None:   self._e(Op.LOAD_NIL, dst)
        elif v is True:  self._e(Op.LOAD_TRUE, dst)
        elif v is False: self._e(Op.LOAD_FALSE, dst)
        elif isinstance(v, int) and -32768 <= v <= 32767: self._e(Op.LOAD_INT, dst, v & 0xFFFF)
        else: self._e(Op.LOAD_CONST, dst, self._const(v))

    def _resolve(self, name):
        r = self._scope.resolve_local(name)
        if r is not None: return 'local', r
        uv = self._scope.resolve_upval(name)
        if uv is not None: return 'upval', uv
        return 'global', self._name(name)

    def _load_name(self, name, dst):
        kind, idx = self._resolve(name)
        if kind == 'local':
            if dst != idx: self._e(Op.MOVE, dst, idx)
        elif kind == 'upval': self._e(Op.LOAD_UPVAL, dst, idx)
        else: self._e(Op.LOAD_GLOBAL, dst, idx)

    def _store_name(self, name, src):
        kind, idx = self._resolve(name)
        if kind == 'local':
            if src != idx: self._e(Op.MOVE, idx, src)
        elif kind == 'upval': self._e(Op.STORE_UPVAL, idx, src)
        else: self._e(Op.STORE_GLOBAL, idx, src)

    def _patch_b(self, idx): self._scope.proto.code[idx].b = len(self._scope.proto.code)-idx-1
    def _patch_a(self, idx): self._scope.proto.code[idx].a = len(self._scope.proto.code)-idx-1
    def _patch_c(self, idx, val): self._scope.proto.code[idx].c = val

    # ── compile entry ─────────────────────────────────────────────────────────
    def compile(self, prog):
        for node in prog.body: self._stmt(node)
        self._e(Op.RETURN, NIL_REG)
        return self._proto

    # ── statements ────────────────────────────────────────────────────────────
    def _stmt(self, node):
        if node is None: return
        # Track current source line for error reporting
        if hasattr(node, 'line') and node.line:
            self._cur_line = node.line

        if isinstance(node, ExprStmt):
            t = self._top(); r = self._expr(node.expr); self._free_to(t)

        elif isinstance(node, VarDecl):
            r = self._expr(node.initializer) if node.initializer else (
                lambda d=self._alloc(): (self._e(Op.LOAD_NIL, d), d)[1])()
            if self._scope.parent is None and self._scope.depth == 0:
                # Top-level let/const (not inside any block) → persist in VM
                # globals via STORE_GLOBAL so state survives across run() calls.
                self._e(Op.STORE_GLOBAL, self._name(node.name), r)
                self._free(r)
            else:
                lr = self._scope.add_local(node.name)
                if r != lr: self._e(Op.MOVE, lr, r); self._free(r)

        elif isinstance(node, BlockStmt):
            self._scope.begin_block()
            for s in node.body: self._stmt(s)
            self._scope.end_block()

        elif isinstance(node, IfStmt):      self._if(node)
        elif isinstance(node, WhileStmt):   self._while(node)
        elif isinstance(node, ForInStmt):   self._for_in(node)
        elif isinstance(node, DoWhileStmt): self._do_while(node)

        elif isinstance(node, ReturnStmt):
            if node.value: r = self._expr(node.value); self._e(Op.RETURN, r); self._free(r)
            else: self._e(Op.RETURN, NIL_REG)

        elif isinstance(node, BreakStmt):
            j = self._e(Op.JUMP, 0)
            if self._break_patches: self._break_patches[-1].append(j)

        elif isinstance(node, ContinueStmt):
            j = self._e(Op.JUMP, 0)
            if self._cont_patches: self._cont_patches[-1].append(j)

        elif isinstance(node, PrintStmt):
            t = self._top(); s = t; n = 0
            for arg in (node.args or []):
                r = self._alloc(); v = self._expr(arg)
                if v != r: self._e(Op.MOVE, r, v); self._free(v)
                n += 1
            self._e(Op.PRINT, s, n); self._free_to(t)

        elif isinstance(node, FunctionDecl):   self._fn_decl(node)
        elif isinstance(node, GeneratorFnDecl): self._gen_fn_decl(node)
        elif isinstance(node, StructDecl):     self._struct_decl(node)
        elif isinstance(node, EnumDecl):       self._enum_decl(node)
        elif isinstance(node, InterfaceDecl):  pass
        elif isinstance(node, ImplDecl):       self._impl_decl(node)
        elif isinstance(node, ImportDecl):     self._import_decl(node)

        elif isinstance(node, ThrowStmt):
            r = self._expr(node.value); self._e(Op.THROW, r); self._free(r)

        elif isinstance(node, TryCatchStmt): self._try_catch(node)
        elif isinstance(node, MatchStmt):    self._match(node)

        elif isinstance(node, YieldStmt):
            r = self._expr(node.value) if node.value else (
                lambda d=self._alloc(): (self._e(Op.LOAD_NIL, d), d)[1])()
            self._e(Op.RETURN, r)

        elif isinstance(node, (SceneDecl, AIDecl, ShaderDecl)):
            dst = self._alloc()
            self._e(Op.LOAD_CONST, dst, self._const(('__decl__', node)))
            self._e(Op.STORE_GLOBAL, self._name(getattr(node,'name','__anon__')), dst)
            self._free(dst)

        elif isinstance(node, ExportDecl):
            inner = getattr(node,'decl',None) or getattr(node,'node',None)
            if inner: self._stmt(inner)

        elif isinstance(node, DecoratedDecl): self._stmt(node.decl)
        elif isinstance(node, LabeledStmt):   self._stmt(node.stmt)
        elif isinstance(node, (WaitStmt, MixinDecl)): pass

    # ── if ────────────────────────────────────────────────────────────────────
    def _if(self, node):
        cond = self._expr(node.condition)
        jf   = self._e(Op.JUMP_IF_FALSE, cond, 0); self._free(cond)
        self._scope.begin_block(); self._stmt(node.then_branch); self._scope.end_block()
        if node.else_branch:
            je = self._e(Op.JUMP, 0); self._patch_b(jf)
            self._scope.begin_block(); self._stmt(node.else_branch); self._scope.end_block()
            self._patch_b(je)
        else: self._patch_b(jf)

    # ── while ─────────────────────────────────────────────────────────────────
    def _while(self, node):
        ls = len(self._scope.proto.code)
        self._loop_starts.append(ls)
        self._break_patches.append([]); self._cont_patches.append([])
        cond = self._expr(node.condition)
        jx   = self._e(Op.JUMP_IF_FALSE, cond, 0); self._free(cond)
        self._scope.begin_block()
        body = node.body
        for s in (body.body if isinstance(body, BlockStmt) else [body]): self._stmt(s)
        self._scope.end_block()
        self._e(Op.JUMP, 0, ls - len(self._scope.proto.code) - 1)
        # jx points to after loop. Else handling:
        # - when condition false → run else, then end
        # - break → skip else, jump to end
        # - natural exit (condition became false mid-loop is same as condition-false entry)
        here_after_loop = len(self._scope.proto.code)
        if getattr(node, 'else_branch', None):
            # jx jumps here (to else block) on condition false
            self._patch_b(jx)
            # break patches need to skip the else — insert a skip jump that break goes to
            # but that means break patches point here too, which would run else...
            # CORRECT approach: break jumps OVER the else; jx falls INTO else
            # We need two different targets. Use a skip-jump before else:
            # Structure: ... | JUMP_back | [jx target=here] | JUMP_skip | else_block | [skip target] | end
            # But break already patches to here_after_loop which is before JUMP_skip...
            # Simplest: patch break to after else, jx to else start
            # Compile else first to know its size, then patch
            self._scope.begin_block(); self._stmt(node.else_branch); self._scope.end_block()
            end_pos = len(self._scope.proto.code)
            # Now patch break to end (past else)
            for j in self._break_patches.pop(): self._scope.proto.code[j].b = end_pos-j-1
        else:
            self._patch_b(jx)
            for j in self._break_patches.pop(): self._scope.proto.code[j].b = here_after_loop-j-1
        for j in self._cont_patches.pop():  self._scope.proto.code[j].b = ls-j-1
        self._loop_starts.pop()

    # ── do-while ──────────────────────────────────────────────────────────────
    def _do_while(self, node):
        from ast_nodes import BlockStmt
        ls = len(self._scope.proto.code)
        self._loop_starts.append(ls)
        self._break_patches.append([]); self._cont_patches.append([])
        self._scope.begin_block()
        body = node.body
        for s in (body.body if isinstance(body, BlockStmt) else [body]): self._stmt(s)
        self._scope.end_block()
        cond = self._expr(node.condition)
        # Jump back to start if condition true
        self._e(Op.JUMP_IF_TRUE, cond, ls - len(self._scope.proto.code) - 1); self._free(cond)
        here = len(self._scope.proto.code)
        for j in self._break_patches.pop(): self._scope.proto.code[j].b = here-j-1
        for j in self._cont_patches.pop():  self._scope.proto.code[j].b = ls-j-1
        self._loop_starts.pop()

    # ── for-in ────────────────────────────────────────────────────────────────
    def _for_in(self, node):
        t = self._top()
        self._break_patches.append([]); self._cont_patches.append([])
        isrc = self._expr(node.iterable)
        ir   = self._alloc(); self._e(Op.ITER_START, ir, isrc); self._free(isrc)
        ls   = len(self._scope.proto.code)
        self._loop_starts.append(ls)
        vr   = self._alloc()
        jx   = self._e(Op.ITER_NEXT, vr, ir, 0)
        self._scope.begin_block()
        vn = node.var_name
        extra_vars = getattr(node, '_extra_vars', [])
        if extra_vars:
            # Multi-var destructure: for k, v in entries(d)
            all_vars = [vn] + extra_vars
            for i, n in enumerate(all_vars):
                lr = self._scope.add_local(n); ir2 = self._alloc()
                self._e(Op.LOAD_INT, ir2, i); self._e(Op.GET_INDEX, lr, vr, ir2); self._free(ir2)
        elif isinstance(vn, list):
            for i, n in enumerate(vn):
                lr = self._scope.add_local(n); ir2 = self._alloc()
                self._e(Op.LOAD_INT, ir2, i); self._e(Op.GET_INDEX, lr, vr, ir2); self._free(ir2)
        else:
            lr = self._scope.add_local(vn); self._e(Op.MOVE, lr, vr)
        body = node.body
        for s in (body.body if isinstance(body, BlockStmt) else [body]): self._stmt(s)
        self._scope.end_block()
        self._e(Op.JUMP, 0, ls - len(self._scope.proto.code) - 1)
        # ep = where ITER_NEXT's 'done' jump should land
        if getattr(node, 'else_branch', None):
            # jx (ITER_NEXT done) → else block directly
            # break → past else block
            # Insert skip_jump for break BEFORE else, patch jx to AFTER skip_jump
            skip_j = self._e(Op.JUMP, 0)    # break lands here → jumps past else
            ep = len(self._scope.proto.code); self._patch_c(jx, ep-jx-1)  # jx → past skip_j (into else)
            self._free(vr); self._free_to(t)
            # Patch break to skip_j position (they jump over else)
            for j in self._break_patches.pop(): self._scope.proto.code[j].b = (skip_j)-j-1
            for j in self._cont_patches.pop():  self._scope.proto.code[j].b = ls-j-1
            self._loop_starts.pop()
            self._scope.begin_block(); self._stmt(node.else_branch); self._scope.end_block()
            self._patch_b(skip_j)  # skip_j now jumps to here (past else)
        else:
            ep = len(self._scope.proto.code); self._patch_c(jx, ep-jx-1)
            self._free(vr); self._free_to(t)
            here = len(self._scope.proto.code)
            for j in self._break_patches.pop(): self._scope.proto.code[j].b = here-j-1
            for j in self._cont_patches.pop():  self._scope.proto.code[j].b = ls-j-1
            self._loop_starts.pop()

    # ── fn decl ───────────────────────────────────────────────────────────────
    def _fn_decl(self, node):
        proto = self._compile_fn(node.name, node.params, node.body,
                                  is_method=getattr(node,'is_method',False))
        self._scope.proto.protos.append(proto)
        ci = self._scope.proto.const_idx(proto)
        dst = self._alloc()
        self._e(Op.MAKE_CLOSURE, dst, ci, len(proto.upval_descs))
        for uv in proto.upval_descs: self._e(Op.CAPTURE_UPVAL, 0, 1 if uv.is_local else 0, uv.index)
        lr = self._scope.add_local(node.name)
        if dst != lr: self._e(Op.MOVE, lr, dst); self._free(dst)
        # Also store in globals so recursive calls (LOAD_GLOBAL) work
        self._e(Op.STORE_GLOBAL, self._name(node.name), lr)

    def _gen_fn_decl(self, node):
        """BUG-24 fix: store GeneratorFnDecl as a special descriptor.
        The VM calls it via a sub-interpreter (same as interpreter path)."""
        desc = ('__gen_decl__', node)
        dst  = self._alloc()
        self._e(Op.LOAD_CONST, dst, self._const(desc))
        self._e(Op.STORE_GLOBAL, self._name(node.name), dst)
        self._free(dst)

    def _compile_fn(self, name, params, body, is_method=False):
        proto  = FnProto(name, [p.name for p in params], source_name=self._src, is_method=is_method)
        # BUG-23 fix: store default AST nodes so VM can fill missing args
        for p in params:
            if p.default is not None:
                proto.param_defaults[p.name] = p.default
        parent = self._scope; self._scope = _Scope(proto, parent=parent)
        if is_method: self._scope.add_local('self')
        for p in params: self._scope.add_local(p.name)
        for s in (body.body if isinstance(body, BlockStmt) else [body]): self._stmt(s)
        if not proto.code or proto.code[-1].op != Op.RETURN: self._e(Op.RETURN, NIL_REG)
        proto.upval_descs = list(self._scope.upvals); self._scope = parent
        return proto

    # ── struct decl ───────────────────────────────────────────────────────────
    def _struct_decl(self, node):
        methods = {}; operators = {}
        for m in node.methods:
            p = self._compile_fn(f"{node.name}.{m.name}", m.params, m.body, is_method=True)
            self._scope.proto.protos.append(p); methods[m.name] = p
        for prop in (node.properties or []):
            if prop.getter_body:
                p = self._compile_fn(f"{node.name}.get_{prop.name}", [], prop.getter_body, is_method=True)
                self._scope.proto.protos.append(p); methods[f'__get_{prop.name}'] = p
            if prop.setter_body:
                fp = Param(name=prop.setter_param or 'value', line=prop.line, col=prop.col)
                p  = self._compile_fn(f"{node.name}.set_{prop.name}", [fp], prop.setter_body, is_method=True)
                self._scope.proto.protos.append(p); methods[f'__set_{prop.name}'] = p
        for op_d in (node.operators or []):  # Phase 7
            p = self._compile_fn(f"{node.name}.__op_{op_d.op_symbol}", op_d.params, op_d.body, is_method=True)
            self._scope.proto.protos.append(p)
            # Unary minus stored as '-u' to distinguish from binary '-'
            key = '-u' if (op_d.op_symbol == '-' and op_d.is_unary) else op_d.op_symbol
            operators[key] = p
        desc = {'__type__':'struct_decl','__name__':node.name,
                '__fields__':{sf.name:sf.default for sf in node.fields},
                '__methods__':methods,'__operators__':operators,
                '__parent__':node.parent_name,'__interfaces__':node.interfaces,'__node__':node}
        dst = self._alloc()
        self._e(Op.LOAD_CONST, dst, self._const(desc))
        self._e(Op.STORE_GLOBAL, self._name(node.name), dst); self._free(dst)

    # ── enum decl ─────────────────────────────────────────────────────────────
    def _enum_decl(self, node):
        variants = {}
        for i, v in enumerate(node.variants):
            if v.fields:
                # ADT variant: store field names so VM can build tagged dict on call
                variants[v.name] = {'__adt_fields__': [f[0] for f in v.fields],
                                    '__enum__': node.name, '__variant__': v.name}
            else:
                val = v.value
                if val is None: val = i
                elif isinstance(val, IntLiteralExpr): val = val.value
                elif isinstance(val, StringLiteralExpr): val = val.value
                variants[v.name] = val
        desc = {'__type__':'enum_decl','__name__':node.name,'__variants__':variants,'__node__':node}
        dst = self._alloc()
        self._e(Op.LOAD_CONST, dst, self._const(desc))
        self._e(Op.STORE_GLOBAL, self._name(node.name), dst); self._free(dst)

    # ── impl decl ─────────────────────────────────────────────────────────────
    def _impl_decl(self, node):
        for m in node.methods:
            p = self._compile_fn(f"{node.struct_name}.{m.name}", m.params, m.body, is_method=True)
            self._scope.proto.protos.append(p)
            dr = self._alloc(); mr = self._alloc(); fr = self._alloc(); kr = self._alloc()
            self._e(Op.LOAD_GLOBAL, dr, self._name(node.struct_name))
            self._e(Op.GET_FIELD,   mr, dr, self._name('__methods__'))
            self._e(Op.LOAD_CONST,  fr, self._const(p))
            self._e(Op.LOAD_CONST,  kr, self._const(m.name))
            self._e(Op.SET_INDEX,   mr, kr, fr)
            self._free(dr); self._free(mr); self._free(fr); self._free(kr)

    # ── import decl ───────────────────────────────────────────────────────────
    def _import_decl(self, node):
        dst = self._alloc()
        self._e(Op.IMPORT, dst, self._const(node.path))
        alias = node.alias or node.path
        lr = self._scope.add_local(alias)
        if dst != lr: self._e(Op.MOVE, lr, dst); self._free(dst)

    # ── try/catch ─────────────────────────────────────────────────────────────
    def _try_catch(self, node):
        exc_r = self._alloc()
        pi    = self._e(Op.PUSH_HANDLER, 0, exc_r)
        self._scope.begin_block(); self._stmt(node.body); self._scope.end_block()
        self._e(Op.POP_HANDLER)
        je = self._e(Op.JUMP, 0)
        self._patch_a(pi)
        if node.catch_var:
            lr = self._scope.add_local(node.catch_var); self._e(Op.MOVE, lr, exc_r)
        self._scope.begin_block(); self._stmt(node.handler); self._scope.end_block()
        self._patch_b(je); self._free(exc_r)

    # ── match ─────────────────────────────────────────────────────────────────
    def _match(self, node):
        subj = self._expr(node.subject); ends = []
        for arm in node.arms:
            pat = arm.pattern
            wild = (pat is None or (isinstance(pat, IdentExpr) and pat.name == '_'))
            if wild:
                self._scope.begin_block(); self._stmt(arm.body); self._scope.end_block()
                ends.append(self._e(Op.JUMP, 0)); break
            cr = self._alloc(); pr = self._expr(pat)
            self._e(Op.EQ, cr, subj, pr); self._free(pr)
            jf = self._e(Op.JUMP_IF_FALSE, cr, 0); self._free(cr)
            self._scope.begin_block(); self._stmt(arm.body); self._scope.end_block()
            ends.append(self._e(Op.JUMP, 0)); self._patch_b(jf)
        self._free(subj)
        for j in ends: self._patch_b(j)

    # ── expressions ───────────────────────────────────────────────────────────
    _ARITH = {'+':Op.ADD,'-':Op.SUB,'*':Op.MUL,'/':Op.DIV,
              '%':Op.MOD,'**':Op.POW,'div':Op.IDIV,'//':Op.IDIV,'++':Op.CONCAT,
              '&':Op.BAND,'|':Op.BOR,'^':Op.BXOR,'<<':Op.BLSHIFT,'>>':Op.BRSHIFT}
    _CMP   = {'==':Op.EQ,'!=':Op.NEQ,'<':Op.LT,'<=':Op.LTE,'>':Op.GT,'>=':Op.GTE,
              'in':Op.CONTAINS,'not in':Op.NOT_CONTAINS}

    def _expr(self, node):
        dst = self._alloc()

        if isinstance(node, IntLiteralExpr):    self._load_lit(node.value, dst)
        elif isinstance(node, FloatLiteralExpr): self._e(Op.LOAD_CONST, dst, self._const(node.value))
        elif isinstance(node, StringLiteralExpr):self._e(Op.LOAD_CONST, dst, self._const(node.value))
        elif isinstance(node, BoolLiteralExpr):  self._e(Op.LOAD_TRUE if node.value else Op.LOAD_FALSE, dst)
        elif isinstance(node, NullLiteralExpr):  self._e(Op.LOAD_NIL, dst)

        elif isinstance(node, IdentExpr):
            self._free(dst); dst = self._alloc(); self._load_name(node.name, dst)

        elif isinstance(node, BinaryExpr):
            self._free(dst); dst = self._binary(node)

        elif isinstance(node, UnaryExpr):
            src = self._expr(node.operand)
            if node.op == '-': self._e(Op.NEG, dst, src)
            elif node.op in ('!','not'): self._e(Op.NOT, dst, src)
            elif node.op == '~': self._e(Op.BNOT, dst, src)
            else: self._e(Op.MOVE, dst, src)
            self._free(src)

        elif isinstance(node, AssignExpr):
            self._free(dst); dst = self._assign_expr(node)

        elif isinstance(node, CallExpr):
            self._free(dst); dst = self._call(node)

        elif isinstance(node, GetAttrExpr):
            obj = self._expr(node.obj)
            self._e(Op.GET_FIELD, dst, obj, self._name(node.attr)); self._free(obj)

        elif isinstance(node, SetAttrExpr):
            obj = self._expr(node.obj); val = self._expr(node.value)
            self._e(Op.SET_FIELD, obj, self._name(node.attr), val)
            self._e(Op.MOVE, dst, val); self._free(obj); self._free(val)

        elif isinstance(node, IndexExpr):
            obj = self._expr(node.obj); idx = self._expr(node.index)
            self._e(Op.GET_INDEX, dst, obj, idx); self._free(obj); self._free(idx)

        elif isinstance(node, SetIndexExpr):
            obj = self._expr(node.obj); idx = self._expr(node.index); val = self._expr(node.value)
            self._e(Op.SET_INDEX, obj, idx, val); self._e(Op.MOVE, dst, val)
            self._free(obj); self._free(idx); self._free(val)

        elif isinstance(node, ArrayLiteralExpr):
            self._free(dst); dst = self._array_from(node.elements)

        elif isinstance(node, DictLiteralExpr):
            self._free(dst); dst = self._dict_lit(node)

        elif isinstance(node, StructInitExpr):
            self._free(dst); dst = self._struct_init(node)

        elif isinstance(node, LambdaExpr):
            self._free(dst); dst = self._lambda(node)

        elif isinstance(node, RangeExpr):
            s = self._expr(node.start); e = self._expr(node.end)
            # Pack inclusive flag into high bit of c operand (register numbers are always < 0x8000)
            inc_bit = 0x8000 if node.inclusive else 0
            self._e(Op.MAKE_RANGE, dst, s, e | inc_bit)
            self._free(s); self._free(e)

        elif isinstance(node, FStringExpr):
            self._free(dst); dst = self._fstring(node)

        elif isinstance(node, TernaryExpr):
            cond = self._expr(node.condition)
            jf   = self._e(Op.JUMP_IF_FALSE, cond, 0); self._free(cond)
            vt   = self._expr(node.then_expr); self._e(Op.MOVE, dst, vt); self._free(vt)
            je   = self._e(Op.JUMP, 0); self._patch_b(jf)
            vf   = self._expr(node.else_expr); self._e(Op.MOVE, dst, vf); self._free(vf)
            self._patch_b(je)

        elif isinstance(node, OptChainExpr):
            obj = self._expr(node.obj)
            jn  = self._e(Op.JUMP_IF_NIL, obj, 0)
            self._e(Op.GET_FIELD, dst, obj, self._name(node.attr))
            je  = self._e(Op.JUMP, 0); self._patch_b(jn)
            self._e(Op.LOAD_NIL, dst); self._patch_b(je); self._free(obj)

        elif isinstance(node, NullishExpr):
            left = self._expr(node.left)
            jn   = self._e(Op.JUMP_IF_NIL, left, 0)
            self._e(Op.MOVE, dst, left)
            je   = self._e(Op.JUMP, 0); self._patch_b(jn)
            right = self._expr(node.right); self._e(Op.MOVE, dst, right); self._free(right)
            self._patch_b(je); self._free(left)

        elif isinstance(node, PipeExpr):
            # BUG-22 fix: PipeExpr uses .value and .fn, not .left/.right
            fn = self._expr(node.fn); arg = self._expr(node.value)
            self._e(Op.MOVE, fn+1, arg); self._e(Op.CALL, fn, 1, dst)
            self._free(fn); self._free(arg)

        elif isinstance(node, ListComprehensionExpr):
            self._free(dst); dst = self._list_comp(node)

        elif isinstance(node, TupleExpr):
            self._free(dst); dst = self._array_from(node.elements)

        elif isinstance(node, CastExpr):
            src = self._expr(node.expr)
            tn  = node.cast_type.name if hasattr(node.cast_type,'name') else str(node.cast_type)
            self._e(Op.CAST, dst, src, self._name(tn)); self._free(src)

        elif isinstance(node, IsExpr):
            src = self._expr(node.expr)
            tn  = node.check_type.name if hasattr(node.check_type,'name') else str(node.check_type)
            self._e(Op.IS_TYPE, dst, src, self._name(tn)); self._free(src)

        elif isinstance(node, NamespaceAccessExpr):
            obj = self._expr(node.obj)
            self._e(Op.GET_FIELD, dst, obj, self._name(node.attr)); self._free(obj)

        elif isinstance(node, SpreadExpr):
            src = self._expr(node.expr); self._e(Op.MOVE, dst, src); self._free(src)

        else:
            self._e(Op.LOAD_NIL, dst)

        return dst

    # ── binary ────────────────────────────────────────────────────────────────
    def _binary(self, node):
        op  = node.op; dst = self._alloc()
        if op == '&&':
            l = self._expr(node.left); self._e(Op.MOVE, dst, l); self._free(l)
            jf = self._e(Op.JUMP_IF_FALSE, dst, 0)
            r  = self._expr(node.right); self._e(Op.MOVE, dst, r); self._free(r)
            self._patch_b(jf); return dst
        if op == '||':
            l = self._expr(node.left); self._e(Op.MOVE, dst, l); self._free(l)
            jt = self._e(Op.JUMP_IF_TRUE, dst, 0)
            r  = self._expr(node.right); self._e(Op.MOVE, dst, r); self._free(r)
            self._patch_b(jt); return dst
        # compound assign
        if op in ('+=','-=','*=','/=','%=','**=','div=','++=','&=','|=','^=','<<=','>>='): 
            base = op[:-1]
            lv = self._expr(node.left); rv = self._expr(node.right)
            vm = self._ARITH.get(base, Op.ADD); self._e(vm, dst, lv, rv)
            self._free(lv); self._free(rv)
            t = node.left
            if isinstance(t, IdentExpr): self._store_name(t.name, dst)
            elif isinstance(t, GetAttrExpr):
                obj = self._expr(t.obj); self._e(Op.SET_FIELD, obj, self._name(t.attr), dst); self._free(obj)
            elif isinstance(t, IndexExpr):
                obj = self._expr(t.obj); idx = self._expr(t.index)
                self._e(Op.SET_INDEX, obj, idx, dst); self._free(obj); self._free(idx)
            return dst
        lv = self._expr(node.left); rv = self._expr(node.right)
        vm = self._ARITH.get(op) or self._CMP.get(op)
        if vm: self._e(vm, dst, lv, rv)
        else:
            fn = self._alloc()
            self._e(Op.LOAD_GLOBAL, fn, self._name(f'__op_{op}'))
            self._e(Op.MOVE, fn+1, lv); self._e(Op.MOVE, fn+2, rv)
            self._e(Op.CALL, fn, 2, dst); self._free(fn)
        self._free(lv); self._free(rv); return dst

    # ── assign expr ───────────────────────────────────────────────────────────
    def _assign_expr(self, node):
        if node.op != '=':
            fake = BinaryExpr(left=node.target, op=node.op, right=node.value, line=node.line, col=node.col)
            return self._binary(fake)
        val = self._expr(node.value)
        t = node.target
        if isinstance(t, IdentExpr): self._store_name(t.name, val)
        elif isinstance(t, GetAttrExpr):
            obj = self._expr(t.obj); self._e(Op.SET_FIELD, obj, self._name(t.attr), val); self._free(obj)
        elif isinstance(t, IndexExpr):
            obj = self._expr(t.obj); idx = self._expr(t.index)
            self._e(Op.SET_INDEX, obj, idx, val); self._free(obj); self._free(idx)
        return val

    # ── call ──────────────────────────────────────────────────────────────────
    def _call(self, node):
        dst = self._alloc()
        if isinstance(node.callee, GetAttrExpr):
            obj = self._expr(node.callee.obj); ni = self._name(node.callee.attr)
            t   = self._top()
            for arg in node.args:
                r = self._alloc(); v = self._expr(arg.value)
                if v != r: self._e(Op.MOVE, r, v); self._free(v)
            self._e(Op.CALL_METHOD, obj, ni, len(node.args))
            self._e(Op.MOVE, dst, obj); self._free_to(t); self._free(obj)
            return dst
        fn = self._expr(node.callee); t = self._top()
        for arg in node.args:
            r = self._alloc(); v = self._expr(arg.value)
            if v != r: self._e(Op.MOVE, r, v); self._free(v)
        self._e(Op.CALL, fn, len(node.args), dst)
        self._free_to(t); self._free(fn); return dst

    # ── array / dict / struct ─────────────────────────────────────────────────
    def _array_from(self, elems):
        t = self._top()
        for i, e in enumerate(elems):
            slot = t + i
            # Ensure n_regs is at slot so _expr fills from there
            if self._scope.n_regs < slot:
                self._scope.n_regs = slot
            v = self._expr(e)
            if v != slot:
                self._e(Op.MOVE, slot, v)
            # Seal slot: release any temps above it
            self._scope.n_regs = slot + 1
            if slot + 1 > self._scope.proto.n_locals:
                self._scope.proto.n_locals = slot + 1
        dst = self._alloc()
        self._e(Op.MAKE_ARRAY, dst, t, len(elems))
        self._free_to(t); self._scope.n_regs = dst + 1
        return dst

    def _dict_lit(self, node):
        t = self._top()
        for i, (k, v) in enumerate(node.pairs):
            kslot = t + i * 2
            vslot = t + i * 2 + 1
            # Key
            if self._scope.n_regs < kslot:
                self._scope.n_regs = kslot
            kv = self._expr(k)
            if kv != kslot:
                self._e(Op.MOVE, kslot, kv)
            self._scope.n_regs = kslot + 1
            if kslot + 1 > self._scope.proto.n_locals:
                self._scope.proto.n_locals = kslot + 1
            # Value
            vv = self._expr(v)
            if vv != vslot:
                self._e(Op.MOVE, vslot, vv)
            self._scope.n_regs = vslot + 1
            if vslot + 1 > self._scope.proto.n_locals:
                self._scope.proto.n_locals = vslot + 1
        dst = self._alloc()
        self._e(Op.MAKE_DICT, dst, t, len(node.pairs))
        self._free_to(t); self._scope.n_regs = dst + 1
        return dst

    def _struct_init(self, node):
        t = self._top()
        # Allocate dst FIRST — VM reads pairs starting at a+1 (dst+1)
        dst = self._alloc()
        pairs = node.fields
        for i, (fname, fval) in enumerate(pairs):
            kslot = dst + 1 + i * 2
            vslot = dst + 1 + i * 2 + 1
            if self._scope.n_regs < kslot:
                self._scope.n_regs = kslot
            # Key is always a field-name string constant
            self._e(Op.LOAD_CONST, kslot, self._const(fname))
            self._scope.n_regs = kslot + 1
            if kslot + 1 > self._scope.proto.n_locals:
                self._scope.proto.n_locals = kslot + 1
            # Value
            vv = self._expr(fval)
            if vv != vslot:
                self._e(Op.MOVE, vslot, vv)
            self._scope.n_regs = vslot + 1
            if vslot + 1 > self._scope.proto.n_locals:
                self._scope.proto.n_locals = vslot + 1
        ti = self._name(node.struct_name)
        self._e(Op.MAKE_INSTANCE, dst, ti, len(pairs))
        self._free_to(t); self._scope.n_regs = dst + 1
        return dst

    # ── lambda ────────────────────────────────────────────────────────────────
    def _lambda(self, node):
        body = node.body
        if not isinstance(body, BlockStmt):
            body = BlockStmt(body=[ReturnStmt(value=body,line=body.line,col=body.col)],
                              line=body.line,col=body.col)
        proto = self._compile_fn('<lambda>', node.params, body)
        self._scope.proto.protos.append(proto)
        ci = self._scope.proto.const_idx(proto); dst = self._alloc()
        self._e(Op.MAKE_CLOSURE, dst, ci, len(proto.upval_descs))
        for uv in proto.upval_descs: self._e(Op.CAPTURE_UPVAL, 0, 1 if uv.is_local else 0, uv.index)
        return dst

    # ── fstring ───────────────────────────────────────────────────────────────
    def _fstring(self, node):
        template = node.template; parts = []; i = 0
        while i < len(template):
            b = template.find('{', i)
            if b == -1:
                if i < len(template):
                    parts.append(StringLiteralExpr(value=template[i:],line=node.line,col=node.col))
                break
            if b > i:
                parts.append(StringLiteralExpr(value=template[i:b],line=node.line,col=node.col))
            depth=1; j=b+1
            while j < len(template) and depth:
                if template[j]=='{': depth+=1
                elif template[j]=='}': depth-=1
                j+=1
            expr_src = template[b+1:j-1].strip()
            try:
                from lexer import Lexer; from parser import Parser as P
                toks = Lexer(expr_src,'<fstr>').tokenize()
                sub  = P(toks, expr_src).parse_expr()
                parts.append(sub)
            except Exception:
                parts.append(StringLiteralExpr(value=expr_src,line=node.line,col=node.col))
            i = j
        t = self._top(); s = t
        for part in parts:
            r = self._alloc(); v = self._expr(part)
            if v != r: self._e(Op.MOVE, r, v); self._free(v)
        dst = self._alloc(); self._e(Op.INTERP, dst, s, len(parts))
        self._free_to(s); self._scope.n_regs = dst+1; return dst

    # ── list comp ─────────────────────────────────────────────────────────────
    def _list_comp(self, node):
        t = self._top(); res = self._alloc()
        self._e(Op.MAKE_ARRAY, res, t, 0)

        # Build list of all clauses: first clause + extra_clauses
        clauses = [{'var': node.var, 'iterable': node.iterable, 'condition': node.condition}]
        for ec in (node.extra_clauses or []):
            clauses.append(ec)

        # Nested loop state: (iter_reg, loop_start_ip, jump_exit_instr_idx)
        loop_stack = []

        for clause in clauses:
            isrc = self._expr(clause['iterable']); ir = self._alloc()
            self._e(Op.ITER_START, ir, isrc); self._free(isrc)
            ls   = len(self._scope.proto.code)
            self._break_patches.append([]); self._cont_patches.append([])
            vr   = self._alloc(); jx = self._e(Op.ITER_NEXT, vr, ir, 0)
            self._scope.begin_block()
            lr = self._scope.add_local(clause['var']); self._e(Op.MOVE, lr, vr)
            loop_stack.append((ir, ls, jx, vr))

        # Optional condition (only on last clause for simplicity)
        js = None
        last_condition = clauses[-1].get('condition') or node.condition
        if last_condition:
            cr = self._expr(last_condition); js = self._e(Op.JUMP_IF_FALSE, cr, 0); self._free(cr)

        er = self._expr(node.expr)
        fn_r  = self._alloc()
        self._e(Op.GET_FIELD, fn_r, res, self._name('append'))
        arg_r = self._alloc()
        if er != arg_r: self._e(Op.MOVE, arg_r, er)
        self._e(Op.CALL, fn_r, 1, fn_r)
        self._scope.n_regs = fn_r

        if js: self._patch_b(js)

        # Close loops in reverse order
        for (ir, ls, jx, vr) in reversed(loop_stack):
            self._scope.end_block()
            self._e(Op.JUMP, 0, ls - len(self._scope.proto.code) - 1)
            ep = len(self._scope.proto.code); self._patch_c(jx, ep-jx-1)
            self._free(vr)
            self._break_patches.pop(); self._cont_patches.pop()

        self._free_to(t)
        self._scope.n_regs = res + 1
        return res


# ─── IBC SERIALIZATION ────────────────────────────────────────────────────────

IBC_MAGIC = b'IBC\x01'; IBC_VERSION = 2

def write_ibc(proto, path):
    import pickle
    payload = pickle.dumps(proto, 4)
    with open(path,'wb') as f:
        f.write(IBC_MAGIC + _struct.pack('>HI', IBC_VERSION, len(payload)) + payload)

def read_ibc(path):
    import pickle
    with open(path,'rb') as f:
        if f.read(4) != IBC_MAGIC: raise ValueError(f"Not an IBC file: {path}")
        ver, ln = _struct.unpack('>HI', f.read(6))
        if ver != IBC_VERSION: raise ValueError(f"IBC version {ver} != {IBC_VERSION}")
        return pickle.loads(f.read(ln))


# ─── CONVENIENCE ──────────────────────────────────────────────────────────────

def compile_source(source, filename="<script>"):
    from lexer import Lexer; from parser import Parser
    toks = Lexer(source, filename).tokenize()
    prog = Parser(toks, source).parse()
    return Compiler(filename).compile(prog)
