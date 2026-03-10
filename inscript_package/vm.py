# inscript/vm.py  — Phase 6.2: Register-based Virtual Machine
#
# Executes FnProto bytecode produced by compiler.py.
# Each call frame has its own register window (a Python list).

from __future__ import annotations
import math, sys
from typing import Any, Dict, List, Optional

from compiler import Op, FnProto, Instr, NIL_REG, compile_source
from stdlib_values import (Vec2, Vec3, Color, Rect,
                            InScriptFunction, InScriptInstance,
                            InScriptRange, InScriptGenerator)
from errors import InScriptRuntimeError


# ─── RUNTIME TYPES ────────────────────────────────────────────────────────────

class UpvalCell:
    __slots__ = ('value',)
    def __init__(self, v): self.value = v
    def __repr__(self): return f"UpvalCell({self.value!r})"

class VMClosure:
    __slots__ = ('proto','upvals','_self')
    def __init__(self, proto, upvals):
        self.proto = proto; self.upvals = upvals; self._self = _UNSET
    def __repr__(self): return f"<fn {self.proto.name}>"

class VMInstance:
    __slots__ = ('struct_name','fields','_desc')
    def __init__(self, name, fields, desc):
        self.struct_name = name; self.fields = fields; self._desc = desc
    def __repr__(self):
        items = ', '.join(f'{k}:{v!r}' for k, v in list(self.fields.items())[:4])
        return f"{self.struct_name}{{{items}}}"

class VMEnum:
    def __init__(self, name, variants): self.name = name; self.variants = variants
    def __getattr__(self, n):
        if n.startswith('_'): raise AttributeError(n)
        if n in self.variants: return VMEnumVariant(self.name, n, self.variants[n])
        raise AttributeError(f"Enum '{self.name}' has no variant '{n}'")
    def __repr__(self): return f"<enum {self.name}>"

class VMEnumVariant:
    __slots__ = ('enum_name','name','value')
    def __init__(self, en, n, v): self.enum_name=en; self.name=n; self.value=v
    def __repr__(self): return f"{self.enum_name}.{self.name}"
    def __eq__(self, o):
        if isinstance(o, VMEnumVariant): return self.enum_name==o.enum_name and self.name==o.name
        return NotImplemented
    def __hash__(self): return hash((self.enum_name,self.name))

class VMModule:
    __slots__ = ('name','_data')
    def __init__(self, name, data): self.name=name; self._data=data
    def __getitem__(self, k): return self._data[k]
    def get(self, k, d=None): return self._data.get(k,d)
    def __contains__(self, k): return k in self._data
    def __repr__(self): return f"<module '{self.name}'>"

class VMIterator:
    __slots__ = ('_it',)
    def __init__(self, src):
        if isinstance(src, InScriptRange):
            step = 1 if src.start <= src.end else -1
            end  = int(src.end) + (step if src.inclusive else 0)
            self._it = iter(range(int(src.start), end, step))
        elif isinstance(src, dict):   self._it = iter(src.keys())
        elif isinstance(src, VMModule):self._it = iter(src._data.values())
        elif isinstance(src, VMInstance):
            self._it = iter(list(src.fields.values()))
        else:
            try: self._it = iter(src)
            except TypeError: self._it = iter([])
    def next(self): return next(self._it)

class Frame:
    __slots__ = ('closure','regs','ip','handlers','upval_cells')
    def __init__(self, closure, n):
        self.closure = closure; self.regs = [None]*(max(n,8)+4)
        self.ip = 0; self.handlers = []; self.upval_cells = {}

_UNSET   = object()
_RETHROW = object()
_NOTFOUND= object()


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _truthy(v):
    if v is None or v is False: return False
    if isinstance(v, (int,float)) and not isinstance(v,bool) and v==0: return False
    if isinstance(v, (list,dict,str)) and len(v)==0: return False
    return True

def _eq(a,b):
    if a is None and b is None: return True
    if a is None or b is None: return False
    if isinstance(a,VMEnumVariant) and isinstance(b,VMEnumVariant):
        return a.enum_name==b.enum_name and a.name==b.name
    try: return a==b
    except: return False

def _ins_str(v):
    if v is None:    return "nil"
    if v is True:    return "true"
    if v is False:   return "false"
    if isinstance(v, float):
        if v == int(v) and abs(v)<1e15: return str(int(v))
        return str(v)
    if isinstance(v, VMInstance):
        desc = v._desc or {}
        ops  = desc.get('__operators__', {})
        fn   = ops.get('str')
        if fn is not None:
            # Lazy-import VM to call the overload
            from vm import VM as _VM
            _vm = _VM.__new__(_VM)
            _vm._globals = {}
            cl = VMClosure(fn, [])
            cl._self = v
            result = _vm._do_call(cl, [], v)
            return _ins_str(result)
        return repr(v)
    if isinstance(v, VMEnumVariant):return f"{v.enum_name}.{v.name}"
    if isinstance(v, VMClosure):    return f"<fn {v.proto.name}>"
    if isinstance(v, list):  return '['+', '.join(_ins_str(x) for x in v)+']'
    if isinstance(v, dict):
        return '{'+', '.join(f'{_ins_str(k)}: {_ins_str(val)}' for k,val in v.items())+'}'
    return str(v)

def _ins_len(v):
    if isinstance(v,(list,dict,str)): return len(v)
    if isinstance(v,VMInstance):
        desc = v._desc or {}
        ops  = desc.get('__operators__',{})
        fn   = ops.get('len')
        if fn is not None:
            from vm import VM as _VM
            _vm = _VM.__new__(_VM); _vm._globals = {}
            cl = VMClosure(fn,[]); cl._self = v
            return _vm._do_call(cl, [], v)
        return len(v.fields)
    if isinstance(v,InScriptRange): return abs(int(v.end)-int(v.start))
    return 0

def _type_name(v):
    if v is None: return "nil"
    if isinstance(v,bool): return "bool"
    if isinstance(v,int):  return "int"
    if isinstance(v,float):return "float"
    if isinstance(v,str):  return "string"
    if isinstance(v,list): return "array"
    if isinstance(v,dict): return "dict"
    if isinstance(v,VMInstance): return v.struct_name
    if isinstance(v,(VMClosure,)): return "function"
    if isinstance(v,VMEnum): return "enum"
    if isinstance(v,VMEnumVariant): return v.enum_name
    if isinstance(v,VMModule): return "module"
    return type(v).__name__

def _get_idx(obj,idx):
    if isinstance(obj,(list,str)):
        try: return obj[int(idx)]
        except IndexError: raise InScriptRuntimeError(f"index {idx} out of range",0,0,"")
    if isinstance(obj,dict): return obj.get(idx)
    if isinstance(obj,VMInstance):
        desc = obj._desc or {}
        ops  = desc.get('__operators__',{})
        fn   = ops.get('[]')
        if fn is not None:
            from vm import VM as _VM
            _vm = _VM.__new__(_VM); _vm._globals = {}
            cl = VMClosure(fn,[]); cl._self = obj
            return _vm._do_call(cl, [idx], obj)
        return obj.fields.get(idx if isinstance(idx,str) else str(idx))
    if isinstance(obj,VMModule): return obj._data.get(idx)
    return None

def _set_idx(obj,idx,val):
    if isinstance(obj,list):  obj[int(idx)] = val
    elif isinstance(obj,dict): obj[idx] = val
    elif isinstance(obj,VMInstance): obj.fields[str(idx)] = val

def _cast(v, tn):
    try:
        if tn=='int':    return int(v)
        if tn=='float':  return float(v)
        if tn=='string': return _ins_str(v)
        if tn=='bool':   return bool(v)
        return v
    except: raise InScriptRuntimeError(f"cannot cast {v!r} to {tn}",0,0,"")

def _is_type(v, tn):
    m = {'nil': lambda x: x is None, 'int': lambda x: isinstance(x,int) and not isinstance(x,bool),
         'float': lambda x: isinstance(x,float), 'string': lambda x: isinstance(x,str),
         'bool': lambda x: isinstance(x,bool), 'array': lambda x: isinstance(x,list),
         'dict': lambda x: isinstance(x,dict),
         'function': lambda x: isinstance(x,(VMClosure,)) or callable(x)}
    fn = m.get(tn)
    if fn: return fn(v)
    if isinstance(v,VMInstance): return v.struct_name == tn
    if isinstance(v,VMEnumVariant): return v.enum_name == tn
    return False

def _eval_default(node, vm):
    from ast_nodes import (IntLiteralExpr,FloatLiteralExpr,StringLiteralExpr,
                            BoolLiteralExpr,NullLiteralExpr,ArrayLiteralExpr,DictLiteralExpr)
    if node is None: return None
    if isinstance(node,IntLiteralExpr):    return node.value
    if isinstance(node,FloatLiteralExpr):  return node.value
    if isinstance(node,StringLiteralExpr): return node.value
    if isinstance(node,BoolLiteralExpr):   return node.value
    if isinstance(node,NullLiteralExpr):   return None
    if isinstance(node,ArrayLiteralExpr):  return [_eval_default(e,vm) for e in node.elements]
    if isinstance(node,DictLiteralExpr):   return {_eval_default(k,vm):_eval_default(v,vm) for k,v in node.pairs}
    return None

def _list_method(obj,name,vm):
    def b(*a):
        m = {
            'append':  lambda: obj.append(a[0]) or None,
            'pop':     lambda: obj.pop(int(a[0]) if a else -1),
            'insert':  lambda: obj.insert(int(a[0]),a[1]),
            'remove':  lambda: obj.remove(a[0]) or None,
            'index':   lambda: obj.index(a[0]),
            'count':   lambda: obj.count(a[0]),
            'sort':    lambda: (obj.sort(key=lambda x:vm.call(a[0],[x])) if a else obj.sort()) or None,
            'reverse': lambda: obj.reverse() or None,
            'copy':    lambda: list(obj),
            'clear':   lambda: obj.clear() or None,
            'extend':  lambda: obj.extend(a[0]) or None,
            'contains':lambda: a[0] in obj,
            'join':    lambda: (a[0] if a else '').join(_ins_str(x) for x in obj),
            'map':     lambda: [vm.call(a[0],[x]) for x in obj],
            'filter':  lambda: [x for x in obj if vm.call(a[0],[x])],
            'find':    lambda: next((x for x in obj if vm.call(a[0],[x])),None),
            'any':     lambda: any(vm.call(a[0],[x]) for x in obj),
            'all':     lambda: all(vm.call(a[0],[x]) for x in obj),
            'slice':   lambda: obj[int(a[0]):int(a[1])] if len(a)>=2 else obj[int(a[0]):],
            'first':   lambda: obj[0] if obj else None,
            'last':    lambda: obj[-1] if obj else None,
            'flatten': lambda: [x for sub in obj for x in (sub if isinstance(sub,list) else [sub])],
        }.get(name)
        return m() if m else _NOTFOUND
    if name=='length': return len(obj)
    return b

def _str_method(obj,name,vm):
    def b(*a):
        m = {
            'split':      lambda: obj.split(a[0] if a else None),
            'join':       lambda: obj.join(_ins_str(x) for x in a[0]),
            'trim':       lambda: obj.strip(),
            'upper':      lambda: obj.upper(),
            'lower':      lambda: obj.lower(),
            'starts_with':lambda: obj.startswith(a[0] if a else ''),
            'ends_with':  lambda: obj.endswith(a[0] if a else ''),
            'contains':   lambda: (a[0] in obj) if a else False,
            'replace':    lambda: obj.replace(a[0],a[1]) if len(a)>=2 else obj,
            'index_of':   lambda: obj.find(a[0]) if a else -1,
            'substr':     lambda: obj[int(a[0]):int(a[1])] if len(a)>=2 else obj[int(a[0]):],
            'char_at':    lambda: obj[int(a[0])] if a else '',
            'to_int':     lambda: int(obj),
            'to_float':   lambda: float(obj),
            'pad_left':   lambda: obj.rjust(int(a[0]),a[1] if len(a)>1 else ' '),
            'pad_right':  lambda: obj.ljust(int(a[0]),a[1] if len(a)>1 else ' '),
            'repeat':     lambda: obj*(int(a[0]) if a else 1),
            'bytes':      lambda: list(obj.encode()),
        }.get(name)
        return m() if m else _NOTFOUND
    if name=='length': return len(obj)
    return b

def _dict_method(obj,name,vm):
    def b(*a):
        m = {
            'get':     lambda: obj.get(a[0],a[1] if len(a)>1 else None),
            'has':     lambda: a[0] in obj if a else False,
            'set':     lambda: obj.update({a[0]:a[1]}) or None,
            'delete':  lambda: obj.pop(a[0],None),
            'keys':    lambda: list(obj.keys()),
            'values':  lambda: list(obj.values()),
            'entries': lambda: [[k,v] for k,v in obj.items()],
            'merge':   lambda: {**obj,**(a[0] if a else {})},
            'clear':   lambda: obj.clear() or None,
            'copy':    lambda: dict(obj),
        }.get(name)
        return m() if m else _NOTFOUND
    if name=='length': return len(obj)
    return b


# ─── VM ───────────────────────────────────────────────────────────────────────

class VM:
    def __init__(self, filename="<script>"):
        self._filename = filename
        self._globals: Dict[str,Any] = {}
        self._register_builtins()

    def _register_builtins(self):
        import math as _m, random as _r, time as _t
        g = self._globals
        g['print']  = print
        g['input']  = input
        g['int']    = lambda v=0, base=10: (int(v,base) if isinstance(v,str) and base!=10 else int(v))
        g['float']  = float
        g['str']    = _ins_str
        g['bool']   = bool
        g['len']    = _ins_len
        g['type']   = _type_name
        g['range']  = lambda s,e=None,step=1: InScriptRange(s,e,False) if e is not None else InScriptRange(0,s,False)
        g['abs']    = abs; g['min']=min; g['max']=max; g['round']=round
        g['floor']  = _m.floor; g['ceil']=_m.ceil; g['sqrt']=_m.sqrt
        g['pow']    = pow; g['sin']=_m.sin; g['cos']=_m.cos; g['tan']=_m.tan
        g['atan2']  = _m.atan2; g['log']=_m.log; g['exp']=_m.exp
        g['pi']     = _m.pi; g['inf']=float('inf'); g['nan']=float('nan')
        g['nil']    = None; g['true']=True; g['false']=False
        g['ord']    = ord; g['chr']=chr; g['repr']=repr
        g['Array']  = list; g['Dict']=dict
        g['keys']   = lambda d: list(d.keys()) if isinstance(d,dict) else []
        g['values'] = lambda d: list(d.values()) if isinstance(d,dict) else []
        g['zip']    = lambda *a: [list(x) for x in zip(*a)]
        g['enumerate']=lambda it,s=0: [[i,v] for i,v in enumerate(it,s)]
        g['sorted'] = sorted; g['reversed']=lambda it: list(reversed(it))
        g['map']    = lambda fn,it: [self.call(fn,[x]) for x in it]
        g['filter'] = lambda fn,it: [x for x in it if self.call(fn,[x])]
        g['reduce'] = lambda fn,it,init=None: self._reduce(fn,it,init)
        g['any']    = lambda it: any(it); g['all']=lambda it: all(it)
        g['sum']    = sum
        g['Vec2']   = Vec2; g['Vec3']=Vec3; g['Color']=Color; g['Rect']=Rect
        g['random'] = _r.random; g['rand_int']=_r.randint; g['rand_float']=_r.uniform
        g['rand_choice']=_r.choice; g['shuffle']=_r.shuffle; g['seed']=_r.seed
        g['time']   = _t.time; g['sleep']=_t.sleep
        g['clamp']  = lambda v,lo,hi: max(lo,min(hi,v))
        g['lerp']   = lambda a,b,t: a+(b-a)*t
        g['sign']   = lambda v: (1 if v>0 else -1 if v<0 else 0)
        g['hypot']  = _m.hypot; g['degrees']=_m.degrees; g['radians']=_m.radians
        g['Error']  = lambda msg="": RuntimeError(str(msg))
        g['__import_module__'] = self._import_module

    def _import_module(self, name):
        from stdlib import load_module
        try: return VMModule(name, load_module(name))
        except ImportError as e: raise InScriptRuntimeError(str(e),0,0,"")

    def _reduce(self,fn,it,init):
        acc=init
        for v in it:
            if acc is None: acc=v
            else: acc=self.call(fn,[acc,v])
        return acc

    def run(self, proto, source_lines=None):
        cl = VMClosure(proto, [])
        frame = Frame(cl, proto.n_locals)
        return self._exec(frame)

    def call(self, fn, args):
        if isinstance(fn, VMClosure): return self._do_call(fn, args, _UNSET)
        elif callable(fn): return fn(*args)
        else: raise InScriptRuntimeError(f"'{fn!r}' is not callable",0,0,"")

    # ── main loop ─────────────────────────────────────────────────────────────
    def _exec(self, frame: Frame):
        proto  = frame.closure.proto
        code   = proto.code
        consts = proto.consts
        names  = proto.names
        regs   = frame.regs

        def R(r):
            if r == NIL_REG: return None
            if r >= len(regs): regs.extend([None]*(r-len(regs)+1))
            return regs[r]
        def W(r, v):
            if r == NIL_REG: return
            if r >= len(regs): regs.extend([None]*(r-len(regs)+1))
            regs[r] = v

        ip = 0; n = len(code)
        while ip < n:
            ins = code[ip]; op=ins.op; a=ins.a; b=ins.b; c=ins.c
            ip += 1
            try:
                # ── load/store ────────────────────────────────────────────────
                if   op==Op.LOAD_NIL:   W(a,None)
                elif op==Op.LOAD_TRUE:  W(a,True)
                elif op==Op.LOAD_FALSE: W(a,False)
                elif op==Op.LOAD_INT:   W(a, b if b<=32767 else b-65536)
                elif op==Op.LOAD_CONST: W(a, consts[b])
                elif op==Op.LOAD_GLOBAL:W(a, self._globals.get(names[b]))
                elif op==Op.STORE_GLOBAL: self._globals[names[a]] = R(b)
                elif op==Op.LOAD_UPVAL: W(a, frame.closure.upvals[b].value)
                elif op==Op.STORE_UPVAL:frame.closure.upvals[a].value = R(b)
                elif op==Op.MOVE:       W(a, R(b))

                # ── arithmetic ────────────────────────────────────────────────
                elif op==Op.ADD:
                    av,bv = R(b),R(c)
                    if isinstance(av,VMInstance):
                        W(a, self._op_overload(av,'+',bv))
                    elif isinstance(av,str) or isinstance(bv,str):
                        W(a, str(av)+str(bv))
                    else: W(a, av+bv)
                elif op==Op.SUB:
                    av,bv=R(b),R(c)
                    W(a, self._op_overload(av,'-',bv) if isinstance(av,VMInstance) else av-bv)
                elif op==Op.MUL:
                    av,bv=R(b),R(c)
                    W(a, self._op_overload(av,'*',bv) if isinstance(av,VMInstance) else av*bv)
                elif op==Op.DIV:
                    av,bv=R(b),R(c)
                    if isinstance(av,VMInstance): W(a,self._op_overload(av,'/',bv))
                    else:
                        if bv==0: raise InScriptRuntimeError("division by zero",0,0,"")
                        W(a, av/bv)
                elif op==Op.MOD:
                    av,bv=R(b),R(c)
                    W(a, self._op_overload(av,'%',bv) if isinstance(av,VMInstance) else av%bv)
                elif op==Op.POW:
                    av,bv=R(b),R(c)
                    W(a, self._op_overload(av,'**',bv) if isinstance(av,VMInstance) else av**bv)
                elif op==Op.IDIV:
                    av,bv=R(b),R(c)
                    if bv==0: raise InScriptRuntimeError("floor division by zero",0,0,"")
                    W(a, math.floor(av/bv))
                elif op==Op.NEG:
                    av=R(b)
                    if isinstance(av,VMInstance):
                        # unary - stored as '-u', binary - stored as '-'
                        r = self._op_overload(av, '-u', None)
                        if r is _NOTFOUND: r = self._op_overload(av, '-', None)
                        W(a, r if r is not _NOTFOUND else -av)
                    else: W(a, -av)

                # ── comparison ────────────────────────────────────────────────
                elif op==Op.EQ:
                    av,bv=R(b),R(c)
                    if isinstance(av,VMInstance):
                        r=self._op_overload(av,'==',bv)
                        W(a, _eq(av,bv) if r is _NOTFOUND else r)
                    else: W(a,_eq(av,bv))
                elif op==Op.NEQ:
                    av,bv=R(b),R(c)
                    if isinstance(av,VMInstance):
                        r=self._op_overload(av,'!=',bv)
                        if r is _NOTFOUND:
                            # fall back: negate == overload
                            r2=self._op_overload(av,'==',bv)
                            W(a, not _eq(av,bv) if r2 is _NOTFOUND else not r2)
                        else: W(a, r)
                    else: W(a,not _eq(av,bv))
                elif op==Op.LT:
                    av,bv=R(b),R(c)
                    if isinstance(av,VMInstance):
                        r=self._op_overload(av,'<',bv)
                        W(a, av<bv if r is _NOTFOUND else r)
                    else: W(a,av<bv)
                elif op==Op.LTE:
                    av,bv=R(b),R(c)
                    if isinstance(av,VMInstance):
                        r=self._op_overload(av,'<=',bv)
                        W(a, av<=bv if r is _NOTFOUND else r)
                    else: W(a,av<=bv)
                elif op==Op.GT:
                    av,bv=R(b),R(c)
                    if isinstance(av,VMInstance):
                        r=self._op_overload(av,'>',bv)
                        W(a, av>bv if r is _NOTFOUND else r)
                    else: W(a,av>bv)
                elif op==Op.GTE:
                    av,bv=R(b),R(c)
                    if isinstance(av,VMInstance):
                        r=self._op_overload(av,'>=',bv)
                        W(a, av>=bv if r is _NOTFOUND else r)
                    else: W(a,av>=bv)

                # ── logical ───────────────────────────────────────────────────
                elif op==Op.NOT: W(a, not _truthy(R(b)))

                # ── string ────────────────────────────────────────────────────
                elif op==Op.CONCAT: W(a, str(R(b))+str(R(c)))
                elif op==Op.INTERP:
                    # a=dst, b=start_reg, c=count
                    W(a, ''.join(_ins_str(R(b+i)) for i in range(c)))

                # ── control flow ──────────────────────────────────────────────
                elif op==Op.JUMP:           ip += b
                elif op==Op.JUMP_IF_FALSE:
                    if not _truthy(R(a)): ip += b
                elif op==Op.JUMP_IF_TRUE:
                    if _truthy(R(a)): ip += b
                elif op==Op.JUMP_IF_NIL:
                    if R(a) is None: ip += b

                # ── return ────────────────────────────────────────────────────
                elif op==Op.RETURN: return R(a)

                # ── call ──────────────────────────────────────────────────────
                elif op==Op.CALL:
                    fn   = R(a); argc = b
                    args = [R(a+1+i) for i in range(argc)]
                    try:    W(c, self._do_call(fn, args, _UNSET))
                    except Exception as e:
                        r = self._handle_exc(e, frame); 
                        if r is _RETHROW: raise
                        ip, er, ev = r; W(er, ev); continue

                elif op==Op.CALL_METHOD:
                    obj = R(a); mname = names[b]; argc = c
                    args = [R(a+1+i) for i in range(argc)]
                    try:
                        res_cm = self._do_method(obj, mname, args)
                        # Preserve obj for in-place mutating methods (append, sort, etc.)
                        W(a, obj if res_cm is None and isinstance(obj,(list,dict,VMInstance)) else res_cm)
                    except Exception as e:
                        r = self._handle_exc(e, frame)
                        if r is _RETHROW: raise
                        ip, er, ev = r; W(er, ev); continue

                # ── closure ───────────────────────────────────────────────────
                elif op==Op.MAKE_CLOSURE:
                    fn_proto = consts[b]; n_uvs = c; uvs = []
                    for _ in range(n_uvs):
                        cap = code[ip]; ip += 1
                        is_local = bool(cap.b); idx = cap.c
                        if is_local:
                            if idx not in frame.upval_cells:
                                frame.upval_cells[idx] = UpvalCell(R(idx))
                            uvs.append(frame.upval_cells[idx])
                        else:
                            uvs.append(frame.closure.upvals[idx])
                    W(a, VMClosure(fn_proto, uvs))

                elif op==Op.CAPTURE_UPVAL: pass  # consumed by MAKE_CLOSURE

                # ── collections ───────────────────────────────────────────────
                elif op==Op.MAKE_ARRAY: W(a, [R(b+i) for i in range(c)])
                elif op==Op.MAKE_DICT:
                    d = {}
                    for i in range(c): d[R(b+i*2)] = R(b+i*2+1)
                    W(a, d)
                elif op==Op.MAKE_RANGE:
                    # Inclusive flag packed in high bit of c by compiler
                    inc = bool(c & 0x8000)
                    end_reg = c & 0x7FFF
                    W(a, InScriptRange(R(b), R(end_reg), inclusive=inc))

                elif op==Op.GET_INDEX: W(a, _get_idx(R(b), R(c)))
                elif op==Op.SET_INDEX: _set_idx(R(a), R(b), R(c))
                elif op==Op.GET_FIELD: W(a, self._get_field(R(b), names[c]))
                elif op==Op.SET_FIELD: self._set_field(R(a), names[b], R(c))

                # ── struct instance ───────────────────────────────────────────
                elif op==Op.MAKE_INSTANCE:
                    type_name = names[b]; n_pairs = c
                    desc = self._globals.get(type_name, {})
                    fields = {}
                    # Field pairs start at a+1: k0,v0,k1,v1,...
                    for i in range(n_pairs):
                        k = R(a+1+i*2); v = R(a+1+i*2+1)
                        if k is not None: fields[k] = v
                    # Fill defaults
                    if isinstance(desc,dict) and '__fields__' in desc:
                        for fn, fdef in desc['__fields__'].items():
                            if fn not in fields:
                                fields[fn] = _eval_default(fdef, self)
                    inst = VMInstance(type_name, fields, desc if isinstance(desc,dict) else {})
                    # Run init method if present
                    if isinstance(desc,dict):
                        init_fn = desc.get('__methods__',{}).get('init') or desc.get('__methods__',{}).get('__init__')
                        if init_fn:
                            cl = VMClosure(init_fn,[])
                            cl._self = inst
                            self._do_call(cl, [], inst)
                    W(a, inst)

                # ── iteration ─────────────────────────────────────────────────
                elif op==Op.ITER_START: W(a, VMIterator(R(b)))
                elif op==Op.ITER_NEXT:
                    it = R(b)
                    try:    W(a, it.next())
                    except StopIteration: ip += c

                # ── import ────────────────────────────────────────────────────
                elif op==Op.IMPORT:
                    mod_name = consts[b]; W(a, self._import_module(mod_name))

                # ── exception ─────────────────────────────────────────────────
                elif op==Op.THROW:
                    exc = R(a)
                    if not isinstance(exc, Exception): exc = RuntimeError(_ins_str(exc))
                    r = self._handle_exc(exc, frame)
                    if r is _RETHROW: raise exc
                    ip, er, ev = r; W(er, ev); continue
                elif op==Op.PUSH_HANDLER:
                    frame.handlers.append((ip+a, b))  # (catch_ip, exc_reg)
                elif op==Op.POP_HANDLER:
                    if frame.handlers: frame.handlers.pop()

                # ── print ─────────────────────────────────────────────────────
                elif op==Op.PRINT:
                    print(' '.join(_ins_str(R(a+i)) for i in range(b)))

                # ── type ops ──────────────────────────────────────────────────
                elif op==Op.CAST:    W(a, _cast(R(b), names[c]))
                elif op==Op.IS_TYPE: W(a, _is_type(R(b), names[c]))

                # ── Phase 7: operator overload ────────────────────────────────
                elif op==Op.OP_CALL:
                    op_name = names[b]; lv = R(c)
                    rv = R(c+1) if c+1 < len(regs) else None
                    W(a, self._op_overload(lv, op_name, rv))

                elif op in (Op.LINE, Op.NOP): pass

            # All exceptions (including InScriptRuntimeError) go through _handle_exc
            except Exception as e:
                r = self._handle_exc(e, frame)
                if r is _RETHROW: raise InScriptRuntimeError(str(e),0,0,"")
                ip, er, ev = r; W(er, ev); continue

        return None

    # ─── exception handler ────────────────────────────────────────────────────
    def _handle_exc(self, exc, frame):
        if frame.handlers:
            catch_ip, exc_reg = frame.handlers.pop()
            return (catch_ip, exc_reg, exc)
        return _RETHROW

    # ─── field get/set ────────────────────────────────────────────────────────
    def _get_field(self, obj, name):
        if obj is None:
            raise InScriptRuntimeError(f"null pointer: .{name} on nil",0,0,"")
        # Handle enum/struct descriptor dicts stored in globals
        if isinstance(obj, dict) and '__type__' in obj:
            if obj['__type__'] == 'enum_decl':
                variants = obj.get('__variants__', {})
                if name in variants:
                    return VMEnumVariant(obj['__name__'], name, variants[name])
                return None
            if obj['__type__'] == 'struct_decl':
                # Struct used as constructor — return the descriptor itself
                return obj
        if isinstance(obj, VMInstance):
            desc   = obj._desc or {}
            fields = obj.fields
            if name in fields: return fields[name]
            meths = desc.get('__methods__',{})
            getter_key = f'__get_{name}'
            if getter_key in meths:
                cl = VMClosure(meths[getter_key],[]); cl._self = obj
                return self._do_call(cl,[],obj)
            if name in meths:
                fn = meths[name]
                if isinstance(fn, FnProto): cl = VMClosure(fn,[]); cl._self = obj; return cl
                return fn
            # traverse parent chain
            parent = desc.get('__parent__')
            if parent:
                pdesc = self._globals.get(parent,{})
                if isinstance(pdesc,dict):
                    if name in pdesc.get('__methods__',{}):
                        fn = pdesc['__methods__'][name]
                        cl = VMClosure(fn,[]); cl._self = obj; return cl
            return None
        if isinstance(obj, VMModule):   return obj._data.get(name)
        if isinstance(obj, VMEnum):     return getattr(obj, name, None)
        if isinstance(obj, VMEnumVariant):
            if name=='name':  return obj.name
            if name=='value': return obj.value
            return None
        if isinstance(obj, dict):       return obj.get(name)
        if isinstance(obj, list):       return _list_method(obj, name, self)
        if isinstance(obj, str):        return _str_method(obj, name, self)
        if isinstance(obj, (Vec2,Vec3,Color,Rect)): return getattr(obj, name, None)
        if isinstance(obj, InScriptRange):
            if name=='start': return obj.start
            if name=='end':   return obj.end
        if hasattr(obj, name): return getattr(obj, name)
        return None

    def _set_field(self, obj, name, val):
        if isinstance(obj, VMInstance):
            desc = obj._desc or {}
            setter_key = f'__set_{name}'
            meths = desc.get('__methods__',{})
            if setter_key in meths:
                cl = VMClosure(meths[setter_key],[]); cl._self = obj
                self._do_call(cl,[val],obj); return
            obj.fields[name] = val
        elif isinstance(obj, dict): obj[name] = val
        elif isinstance(obj, (Vec2,Vec3,Color,Rect)): setattr(obj, name, val)
        elif hasattr(obj, name): setattr(obj, name, val)

    # ─── call dispatch ────────────────────────────────────────────────────────
    def _do_call(self, fn, args, self_val):
        if fn is None: raise InScriptRuntimeError("called nil",0,0,"")

        if isinstance(fn, VMClosure):
            proto = fn.proto
            # struct/enum descriptor used as constructor
            if isinstance(proto, dict): return self._construct(proto, args)
            frame = Frame(fn, proto.n_locals)
            r0 = 0
            self_v = fn._self if fn._self is not _UNSET else (self_val if self_val is not _UNSET else None)
            if proto.is_method or self_v is not None:
                frame.regs[0] = self_v; r0 = 1
            for i, v in enumerate(args):
                idx = r0+i
                while idx >= len(frame.regs): frame.regs.append(None)
                frame.regs[idx] = v
            return self._exec(frame)

        if isinstance(fn, dict):
            return self._construct(fn, args)

        if isinstance(fn, VMEnum):
            if args:
                arg = args[0]
                for nm, v in fn.variants.items():
                    if nm==arg or v==arg: return VMEnumVariant(fn.name,nm,v)
            return fn

        if isinstance(fn, type) and fn in (Vec2,Vec3,Color,Rect): return fn(*args)
        if callable(fn): return fn(*args)
        raise InScriptRuntimeError(f"'{fn!r}' is not callable",0,0,"")

    def _do_method(self, obj, mname, args):
        m = self._get_field(obj, mname)
        if m is None:
            # built-in method fallback
            if isinstance(obj,list):   r=_list_method(obj,mname,self)(*args); return r if r is not _NOTFOUND else None
            if isinstance(obj,str):    r=_str_method(obj,mname,self)(*args); return r if r is not _NOTFOUND else None
            if isinstance(obj,dict):   r=_dict_method(obj,mname,self)(*args); return r if r is not _NOTFOUND else None
            raise InScriptRuntimeError(f"no method '{mname}' on {_type_name(obj)}",0,0,"")
        if callable(m) and not isinstance(m, (VMClosure,)):
            return m(*args)
        return self._do_call(m, args, obj)

    def _construct(self, desc, args):
        if desc.get('__type__')=='enum_decl':
            if args:
                arg=args[0]
                for nm,v in desc['__variants__'].items():
                    if nm==arg or v==arg: return VMEnumVariant(desc['__name__'],nm,v)
            return VMEnum(desc['__name__'], desc['__variants__'])

        if desc.get('__type__')=='struct_decl':
            fields = {}
            for fn, fdef in desc.get('__fields__',{}).items():
                fields[fn] = _eval_default(fdef, self)
            if args and isinstance(args[0], dict): fields.update(args[0])
            elif args:
                params = list(desc.get('__fields__',{}).keys())
                for i,v in enumerate(args):
                    if i < len(params): fields[params[i]] = v
            inst = VMInstance(desc['__name__'], fields, desc)
            init = desc.get('__methods__',{}).get('init') or desc.get('__methods__',{}).get('__init__')
            if init:
                cl = VMClosure(init,[]); cl._self = inst
                self._do_call(cl, args, inst)
            return inst
        return None

    # ─── Phase 7: operator overloads ──────────────────────────────────────────
    def _op_overload(self, obj, op_sym, other):
        if not isinstance(obj, VMInstance): return _NOTFOUND
        desc = obj._desc or {}
        ops  = desc.get('__operators__',{})
        meths= desc.get('__methods__',{})
        fn   = ops.get(op_sym) or meths.get(f'__op_{op_sym}')
        if fn is None: return _NOTFOUND
        cl = VMClosure(fn,[]); cl._self = obj
        args = [other] if other is not None else []
        return self._do_call(cl, args, obj)


# ─── CONVENIENCE ──────────────────────────────────────────────────────────────

def run_source(source, filename="<script>", source_lines=None):
    proto = compile_source(source, filename)
    vm = VM(filename)
    return vm.run(proto, source_lines or source.splitlines())
