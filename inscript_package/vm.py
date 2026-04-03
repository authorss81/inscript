# -*- coding: utf-8 -*-
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
    __slots__ = ('struct_name','fields','_desc','_super_self','_priv_fields')
    def __init__(self, name, fields, desc):
        self.struct_name = name; self.fields = fields; self._desc = desc
        self._super_self = None   # set when used as a super proxy
        self._priv_fields = set() # set to frozenset of priv field names from __priv__
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
        import math as _m
        if _m.isinf(v): return "Infinity" if v > 0 else "-Infinity"
        if _m.isnan(v): return "NaN"
        # Integer-valued floats display without decimal for cleaner output (3.0 → "3")
        if v == int(v) and abs(v) < 1e15: return str(int(v))
        return str(v)
    if isinstance(v, VMInstance):
        desc = v._desc or {}
        ops  = desc.get('__operators__', {})
        fn   = ops.get('str')
        if fn is not None:
            from vm import VM as _VM
            _vm = _VM.__new__(_VM); _vm._globals = {}
            cl = VMClosure(fn, []); cl._self = v
            result = _vm._do_call(cl, [], v)
            return _ins_str(result)
        return repr(v)
    if isinstance(v, VMEnumVariant): return f"{v.enum_name}.{v.name}"
    if isinstance(v, VMClosure):     return f"<fn {v.proto.name}>"
    if isinstance(v, list):
        return '['+', '.join(_ins_repr(x) for x in v)+']'
    if isinstance(v, dict):
        # Result types
        if '_ok' in v:  return f"Ok({_ins_str(v['_ok'])})"
        if '_err' in v: return f"Err({_ins_repr(v['_err'])})"
        # ADT enum
        if '_variant' in v and '_enum' in v:
            fields = {k: val for k, val in v.items() if not k.startswith('_')}
            if fields:
                fs = ', '.join(f"{k}: {_ins_str(val)}" for k,val in fields.items())
                return f"{v['_variant']}({fs})"
            return f"{v['_enum']}::{v['_variant']}"
        # Plain dict — InScript double-quote style
        pairs = ', '.join(
            f'"{k}": {_ins_repr(val)}' if isinstance(k, str)
            else f'{_ins_repr(k)}: {_ins_repr(val)}'
            for k, val in v.items() if not str(k).startswith('_')
        )
        return '{' + pairs + '}'
    return str(v)

def _ins_repr(v):
    """Like _ins_str but wraps strings in quotes for nested display."""
    if isinstance(v, str):
        escaped = v.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    return _ins_str(v)

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

def _run_gen_via_interp(node, arg_vals, globals_dict):
    """BUG-24 fix: run a GeneratorFnDecl via a sub-interpreter (same path as the
    tree-walking interpreter uses). The VM stores generator functions as
    ('__gen_decl__', node) tuples; calling them goes through here."""
    from interpreter import Interpreter
    from environment import Environment

    interp = Interpreter.__new__(Interpreter)
    interp._src = '<vm_gen>'; interp._call_depth = 0; interp._MAX_CALL_DEPTH = 200
    from errors import InScriptCallStack
    interp._call_stack = InScriptCallStack('<vm_gen>')
    # Share globals so user-defined names are visible
    global_env = Environment(name='gen_global')
    for k, v in globals_dict.items():
        global_env.define(k, v)
    interp._globals = global_env
    interp._env = global_env

    # Delegate to the interpreter's own visit_GeneratorFnDecl logic, which handles
    # threading + queue protocol correctly, then call the resulting factory.
    interp.visit_GeneratorFnDecl(node)
    factory = global_env._store.get(node.name)
    if callable(factory):
        return factory(*arg_vals)
    raise InScriptRuntimeError(f"generator factory for '{node.name}' not callable", 0, 0, "")


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
            'append':   lambda: obj.append(a[0]) or None,
            'push':     lambda: obj.append(a[0]) or None,
            'pop':      lambda: obj.pop(int(a[0]) if a else -1),
            'pop_at':   lambda: obj.pop(int(a[0])) if a else None,
            'insert':   lambda: obj.insert(int(a[0]),a[1]),
            'remove':   lambda: obj.remove(a[0]) or None,
            'index':    lambda: obj.index(a[0]) if a[0] in obj else -1,
            'index_of': lambda: obj.index(a[0]) if a[0] in obj else -1,
            'count':    lambda: (
                            len(obj) if not a
                            else sum(1 for x in obj if vm.call(a[0],[x]))
                            if isinstance(a[0], VMClosure)
                            else obj.count(a[0])
                        ),
            'sort':     lambda: (obj.sort(key=lambda x:vm.call(a[0],[x])) if a else obj.sort()) or None,
            'sorted':   lambda: sorted(obj, key=lambda x:vm.call(a[0],[x])) if a else sorted(obj),
            'take_while': lambda: list(__import__('itertools').takewhile(lambda x: vm.call(a[0],[x]), obj)),
            'drop_while': lambda: list(__import__('itertools').dropwhile(lambda x: vm.call(a[0],[x]), obj)),
            'window':   lambda: [obj[i:i+int(a[0])] for i in range(len(obj)-int(a[0])+1)],
            'none':     lambda: not any(vm.call(a[0],[x]) for x in obj) if a else not any(bool(x) for x in obj),
            'index_where': lambda: next((i for i,x in enumerate(obj) if vm.call(a[0],[x])), -1),
            'last_where': lambda: next((x for x in reversed(obj) if vm.call(a[0],[x])), None),
            'partition': lambda: [[x for x in obj if vm.call(a[0],[x])],[x for x in obj if not vm.call(a[0],[x])]],
            'reverse':  lambda: obj.reverse() or None,
            'copy':     lambda: list(obj),
            'clear':    lambda: obj.clear() or None,
            'extend':   lambda: obj.extend(a[0]) or None,
            'contains': lambda: a[0] in obj,
            'includes': lambda: a[0] in obj,
            'join':     lambda: (a[0] if a else '').join(_ins_str(x) for x in obj),
            'map':      lambda: [vm.call(a[0],[x]) for x in obj],
            'filter':   lambda: [x for x in obj if vm.call(a[0],[x])],
            'reduce':   lambda: (lambda fn,lst,init: (lambda acc,items: [acc := vm.call(fn,[acc,x]) for x in items] and acc)
                                 (lst[0] if init is _NOTFOUND else init, lst[1:] if init is _NOTFOUND else lst)
                                )(a[0], obj, a[1] if len(a)>1 else _NOTFOUND),
            'find':     lambda: next((x for x in obj if vm.call(a[0],[x])),None),
            'any':      lambda: any(vm.call(a[0],[x]) for x in obj),
            'all':      lambda: all(vm.call(a[0],[x]) for x in obj),
            'each':     lambda: [vm.call(a[0],[x]) for x in obj] and None,
            'flat_map': lambda: [y for x in obj for y in (vm.call(a[0],[x]) if a else x)],
            'zip':      lambda: [list(pair) for pair in zip(obj, a[0])] if a else obj,
            'sum':      lambda: sum(vm.call(a[0],[x]) for x in obj) if a else sum(obj),
            'min_by':   lambda: min(obj, key=lambda x: vm.call(a[0],[x])) if a else min(obj),
            'max_by':   lambda: max(obj, key=lambda x: vm.call(a[0],[x])) if a else max(obj),
            'group_by': lambda: (lambda d: [d.setdefault(_ins_str(vm.call(a[0],[x])),[]).append(x) for x in obj] and d)({}) if a else {},
            'unique':   lambda: list(dict.fromkeys(obj)),
            'slice':    lambda: obj[int(a[0]):int(a[1])] if len(a)>=2 else obj[int(a[0]):],
            'take':     lambda: obj[:int(a[0])] if a else obj,
            'skip':     lambda: obj[int(a[0]):] if a else obj,
            'chunk':    lambda: [obj[i:i+int(a[0])] for i in range(0,len(obj),int(a[0]))] if a else [obj],
            'is_empty': lambda: len(obj) == 0,
            'first':    lambda: obj[0] if obj else None,
            'last':     lambda: obj[-1] if obj else None,
            'flatten':  lambda: [x for sub in obj for x in (sub if isinstance(sub,list) else [sub])],
        }.get(name)
        return m() if m else _NOTFOUND
    if name in ('length','len'): return len(obj)
    return b

def _str_method(obj,name,vm):
    def b(*a):
        m = {
            'split':      lambda: obj.split(a[0] if a else None, int(a[1]) if len(a)>1 else -1),
            'join':       lambda: obj.join(_ins_str(x) for x in a[0]),
            'trim':       lambda: obj.strip(),
            'trim_start': lambda: obj.lstrip(),
            'trim_end':   lambda: obj.rstrip(),
            'upper':      lambda: obj.upper(),
            'lower':      lambda: obj.lower(),
            'to_upper':   lambda: obj.upper(),
            'to_lower':   lambda: obj.lower(),
            'starts_with':lambda: obj.startswith(a[0] if a else ''),
            'ends_with':  lambda: obj.endswith(a[0] if a else ''),
            'contains':   lambda: (a[0] in obj) if a else False,
            'replace':    lambda: obj.replace(a[0],a[1]) if len(a)>=2 else obj,
            'index':      lambda: obj.find(a[0]) if a else -1,
            'index_of':   lambda: obj.find(a[0]) if a else -1,
            'substr':     lambda: obj[int(a[0]):int(a[1])] if len(a)>=2 else obj[int(a[0]):],
            'char_at':    lambda: obj[int(a[0])] if a else '',
            'chars':      lambda: list(obj),
            'to_int':     lambda: int(obj),
            'to_float':   lambda: float(obj),
            'to_string':  lambda: obj,
            'pad_left':   lambda: obj.rjust(int(a[0]),a[1] if len(a)>1 else ' '),
            'pad_right':  lambda: obj.ljust(int(a[0]),a[1] if len(a)>1 else ' '),
            'repeat':     lambda: obj*(int(a[0]) if a else 1),
            'reverse':    lambda: obj[::-1],
            'count':      lambda: obj.count(a[0]) if a else len(obj),
            'format':     lambda: (obj.format(*[x for x in a if not isinstance(x,dict)],
                                              **{k:v for d in a if isinstance(d,dict) for k,v in d.items()})),
            'is_empty':   lambda: len(obj)==0,
            'is_alpha':   lambda: obj.isalpha(),
            'is_numeric': lambda: obj.isnumeric(),
            'is_alnum':   lambda: obj.isalnum(),
            'bytes':      lambda: list(obj.encode('utf-8')),
            'is_upper':   lambda: obj.isupper(),
            'is_lower':   lambda: obj.islower(),
            'is_space':   lambda: obj.isspace(),
            'is_digit':   lambda: obj.isdigit(),
            'swapcase':   lambda: obj.swapcase(),
            'zfill':      lambda: obj.zfill(int(a[0])) if a else obj.zfill(0),
            'encode':     lambda: list(obj.encode(a[0] if a else 'utf-8')),
            'lines':      lambda: obj.splitlines(),
            'title':      lambda: obj.title(),
            'capitalize': lambda: obj.capitalize(),
            'strip':      lambda: obj.strip(),
            'lstrip':     lambda: obj.lstrip(),
            'rstrip':     lambda: obj.rstrip(),
            'center':     lambda: obj.center(int(a[0]), a[1][0] if len(a)>1 and a[1] else ' '),
        }.get(name)
        return m() if m else _NOTFOUND
    if name in ('length','len'): return len(obj)
    return b

def _dict_method(obj,name,vm):
    def b(*a):
        _pub = lambda d: {k:v for k,v in d.items() if not str(k).startswith('_')}
        m = {
            'get':        lambda: obj.get(a[0],a[1] if len(a)>1 else None),
            'has':        lambda: a[0] in obj if a else False,
            'has_key':    lambda: a[0] in obj if a else False,
            'has_value':  lambda: a[0] in obj.values() if a else False,
            'set':        lambda: obj.update({a[0]:a[1]}) or None,
            'delete':     lambda: obj.pop(a[0],None),
            'remove':     lambda: obj.pop(a[0],None),
            'pop':        lambda: obj.pop(a[0],a[1] if len(a)>1 else None),
            'keys':       lambda: list(_pub(obj).keys()),
            'values':     lambda: list(_pub(obj).values()),
            'items':      lambda: [[k,v] for k,v in _pub(obj).items()],
            'entries':    lambda: [[k,v] for k,v in _pub(obj).items()],
            'merge':      lambda: {**obj,**(a[0] if a else {})},
            'update':     lambda: obj.update(a[0] if a else {}) or None,
            'copy':       lambda: dict(obj),
            'clear':      lambda: obj.clear() or None,
            'is_empty':   lambda: len(_pub(obj)) == 0,
            'to_pairs':   lambda: [[k,v] for k,v in _pub(obj).items()],
            'filter':     lambda: {k:v for k,v in _pub(obj).items() if vm.call(a[0],[k,v])},
            'map_values': lambda: {k:vm.call(a[0],[v]) for k,v in _pub(obj).items()},
            'map_keys':   lambda: {vm.call(a[0],[k]):v for k,v in _pub(obj).items()},
            'each':       lambda: [vm.call(a[0],[k,v]) for k,v in _pub(obj).items()] and None,
            'any_value':  lambda: any(vm.call(a[0],[v]) for v in _pub(obj).values()),
            'all_values': lambda: all(vm.call(a[0],[v]) for v in _pub(obj).values()),
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

        # ── Extended builtins matching interpreter ──────────────────────────
        # string() / typeof()
        g['string']    = _ins_str
        g['stringify'] = _ins_str   # deprecated alias
        g['typeof']    = _type_name
        # Array helpers
        g['push']      = lambda lst, val: (lst.append(val), lst)[1]
        g['pop']       = lambda lst: lst.pop() if lst else None
        g['fill']      = lambda n_or_lst, val: ([val]*int(n_or_lst) if isinstance(n_or_lst,int)
                         else [val]*len(n_or_lst))
        g['flatten']   = lambda lst: [y for x in lst for y in (x if isinstance(x,list) else [x])]
        g['unique']    = lambda lst: list(dict.fromkeys(lst))
        g['flatten_deep'] = lambda lst: [y for x in lst for y in (flatten_deep(x) if isinstance(x,list) else [x])]
        g['sort']      = lambda lst, key=None: (lst.sort(key=key) or lst)
        g['concat']    = lambda *lists: [x for lst in lists for x in lst]
        # Dict helpers
        g['entries']   = lambda d: ([[k,v] for k,v in d.items() if not str(k).startswith('_')]
                         if isinstance(d,dict) else
                         [[k,v] for k,v in d.fields.items() if not callable(v)] if hasattr(d,'fields') else [])
        g['dict_items']= g['entries']  # deprecated alias
        g['merge']     = lambda a,b: {**a,**b}
        # Type checks
        g['is_nil']    = lambda v: v is None
        g['is_null']   = lambda v: v is None
        g['is_int']    = lambda v: isinstance(v,int) and not isinstance(v,bool)
        g['is_float']  = lambda v: isinstance(v,float)
        g['is_string'] = lambda v: isinstance(v,str)
        g['is_str']    = lambda v: isinstance(v,str)
        g['is_bool']   = lambda v: isinstance(v,bool)
        g['is_array']  = lambda v: isinstance(v,list)
        g['is_dict']   = lambda v: isinstance(v,dict) and '_variant' not in v
        g['is_fn']     = lambda v: callable(v)
        # Assertions
        g['assert']     = lambda cond, msg="Assertion failed": (None if cond else (_ for _ in ()).throw(RuntimeError(str(msg))))
        g['panic']      = lambda msg="panic": (_ for _ in ()).throw(RuntimeError(str(msg)))
        g['unreachable']= lambda msg="unreachable": (_ for _ in ()).throw(RuntimeError(str(msg)))
        # Result types
        g['Ok']        = lambda v=None: {'_ok': v}
        g['Err']       = lambda v=None: {'_err': v}
        # Math extras
        g['PI']        = _m.pi; g['E']=_m.e; g['TAU']=_m.tau
        g['INF']       = float('inf'); g['NAN']=float('nan')
        g['clamp']     = lambda v,lo,hi: max(lo,min(hi,v))
        g['map_range'] = lambda v,a1,b1,a2,b2: a2+(v-a1)/(b1-a1)*(b2-a2) if b1!=a1 else a2
        g['lerp']      = lambda a,b,t: a+(b-a)*t
        g['sign']      = lambda v: (1 if v>0 else -1 if v<0 else 0)
        # String helpers
        g['char_code']  = lambda s: ord(s[0]) if s else 0
        g['from_code']  = lambda n: chr(int(n))
        # Collection
        g['zip']        = lambda *a: [list(x) for x in zip(*a)]
        g['enumerate']  = lambda it,s=0: [[i,v] for i,v in enumerate(it,s)]

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
                elif op==Op.LOAD_GLOBAL:
                    _gn = names[b]
                    # 'super' is resolved dynamically: find current self and its parent struct
                    if _gn == 'super':
                        self_obj = frame.regs[0] if frame.regs else None
                        if isinstance(self_obj, VMInstance):
                            desc = self_obj._desc or {}
                            parent_name = desc.get('__parent__')
                            parent_desc = self._globals.get(parent_name) if parent_name else None
                            if parent_desc and isinstance(parent_desc, dict):
                                # Create a proxy: VMInstance with parent's methods but same fields
                                proxy = VMInstance(parent_name, self_obj.fields, parent_desc)
                                proxy._super_self = self_obj  # track original for method binding
                                W(a, proxy); continue
                        W(a, None)
                    elif _gn not in self._globals:
                        raise InScriptRuntimeError(f"Undefined variable '{_gn}'", ins.line, 0, "")
                    else:
                        W(a, self._globals[_gn])
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
                        if bv==0:
                            if isinstance(av,float) or isinstance(bv,float):
                                import math as _dmath
                                W(a, float('nan') if av==0 else _dmath.copysign(float('inf'), av))
                            else:
                                raise InScriptRuntimeError("division by zero",ins.line,0,"")
                        else:
                            W(a, av/bv)
                elif op==Op.MOD:
                    av,bv=R(b),R(c)
                    W(a, self._op_overload(av,'%',bv) if isinstance(av,VMInstance) else av%bv)
                elif op==Op.POW:
                    av,bv=R(b),R(c)
                    if isinstance(av,VMInstance):
                        W(a, self._op_overload(av,'**',bv))
                    else:
                        if (isinstance(av,int) and not isinstance(av,bool)
                                and isinstance(bv,int) and not isinstance(bv,bool)
                                and bv>0 and abs(av)>1):
                            import math as _m
                            try: _eb = bv*_m.log2(abs(av))
                            except: _eb = float('inf')
                            if _eb>100_000:
                                raise InScriptRuntimeError(
                                    f"OverflowError: {av}**{bv} would produce ~{int(_eb*0.30103):,} digits — too large. Use float({av})**{bv} for an approximation.",
                                    ip,0,"")
                        W(a, av**bv)
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

                # ── bitwise ───────────────────────────────────────────────────
                elif op==Op.BAND:   W(a, int(R(b)) & int(R(c)))
                elif op==Op.BOR:    W(a, int(R(b)) | int(R(c)))
                elif op==Op.BXOR:   W(a, int(R(b)) ^ int(R(c)))
                elif op==Op.BLSHIFT:W(a, int(R(b)) << int(R(c)))
                elif op==Op.BRSHIFT:W(a, int(R(b)) >> int(R(c)))
                elif op==Op.BNOT:   W(a, ~int(R(b)))

                # ── comparison ────────────────────────────────────────────────
                elif op==Op.EQ:
                    av,bv=R(b),R(c)
                    # Range pattern: n == range → n in range (for match case 1..=5)
                    if isinstance(bv, InScriptRange): W(a, av in bv)
                    elif isinstance(av, InScriptRange): W(a, bv in av)
                    elif isinstance(av,VMInstance):
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

                # ── membership ────────────────────────────────────────────────
                elif op==Op.CONTAINS:
                    lv, rv = R(b), R(c)
                    if isinstance(rv, str):   W(a, str(lv) in rv)
                    elif isinstance(rv, dict): W(a, lv in rv)
                    elif isinstance(rv, list): W(a, lv in rv)
                    elif hasattr(rv, '__iter__'): W(a, lv in rv)
                    else: W(a, False)
                elif op==Op.NOT_CONTAINS:
                    lv, rv = R(b), R(c)
                    if isinstance(rv, str):   W(a, str(lv) not in rv)
                    elif isinstance(rv, dict): W(a, lv not in rv)
                    elif isinstance(rv, list): W(a, lv not in rv)
                    elif hasattr(rv, '__iter__'): W(a, lv not in rv)
                    else: W(a, True)

                # ── string ────────────────────────────────────────────────────
                elif op==Op.CONCAT:
                    lv, rv = R(b), R(c)
                    W(a, lv + rv if isinstance(lv, list) and isinstance(rv, list) else str(lv)+str(rv))
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
                    # Set private fields from descriptor
                    if isinstance(desc, dict):
                        inst._priv_fields = desc.get('__priv__', set())
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
                    thrown_val = R(a)
                    # Preserve the thrown value for catch binding
                    if isinstance(thrown_val, Exception):
                        exc = thrown_val
                        exc._thrown_value = getattr(exc, '_thrown_value', thrown_val)
                    else:
                        exc = InScriptRuntimeError(_ins_str(thrown_val), 0, 0, "")
                        exc._thrown_value = thrown_val  # store original for catch
                    r = self._handle_exc(exc, frame)
                    if r is _RETHROW: raise exc
                    ip, er, ev = r
                    # Give catch the original value, not the wrapped exception
                    W(er, getattr(ev, '_thrown_value', ev) if isinstance(ev, Exception) else ev)
                    continue
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
                if r is _RETHROW:
                    if isinstance(e, InScriptRuntimeError): raise
                    raise InScriptRuntimeError(str(e),0,0,"")
                ip, er, ev = r
                # Use _thrown_value if set (preserves struct/non-string thrown values)
                W(er, getattr(ev, '_thrown_value', ev) if isinstance(ev, Exception) else ev)
                continue

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
                # Static field/method access: M.PI, M.sq(5), M.MAX
                static_fields = obj.get('__static__', {})
                if name in static_fields:
                    return static_fields[name]
                static_methods = obj.get('__static_methods__', {})
                if name in static_methods:
                    cl = VMClosure(static_methods[name], [])
                    cl._self = None   # static: no self, prevents _do_call placing struct as reg[0]
                    return cl
                # Fallback: return the descriptor (used as constructor)
                return obj
        if isinstance(obj, VMInstance):
            desc   = obj._desc or {}
            fields = obj.fields
            if name in fields:
                priv = obj._priv_fields
                if name in priv:
                    # Allow if current executing method's self is this instance
                    if getattr(self, '_current_self', None) is obj:
                        pass  # inside a method on this instance — allowed
                    else:
                        raise InScriptRuntimeError(f"Cannot access private field '{name}'", 0, 0, "")
                return fields[name]
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
            priv = obj._priv_fields
            if name in priv:
                if getattr(self, '_current_self', None) is not obj:
                    raise InScriptRuntimeError(f"Cannot set private field '{name}'", 0, 0, "")
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

        # BUG-24 fix: generator function descriptor → run via sub-interpreter
        if isinstance(fn, tuple) and len(fn) == 2 and fn[0] == '__gen_decl__':
            node = fn[1]
            main_globals = self._globals
            def _make_gen(*a):
                return _run_gen_via_interp(node, a, main_globals)
            return _make_gen(*args)

        if isinstance(fn, VMClosure):
            proto = fn.proto
            # struct/enum descriptor used as constructor
            if isinstance(proto, dict): return self._construct(proto, args)
            frame = Frame(fn, proto.n_locals)
            r0 = 0
            # Only inject self if: the fn has an explicit _self bound OR
            # (self_val is provided AND the proto is a method)
            # Static methods (is_method=False, _self=_UNSET) must NOT receive self_val
            if fn._self is not _UNSET:
                self_v = fn._self
            elif proto.is_method and self_val is not _UNSET:
                self_v = self_val
            else:
                self_v = None
            if self_v is not None:
                frame.regs[0] = self_v; r0 = 1
            _prev_self = getattr(self, "_current_self", None)
            self._current_self = self_v
            # Handle variadic *args param
            vararg = proto.vararg_param if proto.vararg_param else ""
            if vararg and vararg in proto.params:
                vi = proto.params.index(vararg)
                # Place non-variadic positional args first
                for i in range(vi):
                    idx = r0 + i
                    while idx >= len(frame.regs): frame.regs.append(None)
                    frame.regs[idx] = args[i] if i < len(args) else None
                # Pack remaining args into the variadic list
                vararg_list = list(args[vi:])
                vidx = r0 + vi
                while vidx >= len(frame.regs): frame.regs.append(None)
                frame.regs[vidx] = vararg_list
            else:
                for i, v in enumerate(args):
                    idx = r0 + i
                    while idx >= len(frame.regs): frame.regs.append(None)
                    frame.regs[idx] = v
                # Fill in default values for missing parameters
                if proto.param_defaults:
                    for pi, pname in enumerate(proto.params):
                        reg = r0 + pi
                        while reg >= len(frame.regs): frame.regs.append(None)
                        if frame.regs[reg] is None and pname in proto.param_defaults:
                            frame.regs[reg] = _eval_default(proto.param_defaults[pname], self)
            try:
                return self._exec(frame)
            finally:
                self._current_self = _prev_self

        if isinstance(fn, dict):
            return self._construct(fn, args)

        if isinstance(fn, VMEnum):
            if args:
                arg = args[0]
                for nm, v in fn.variants.items():
                    if nm==arg or v==arg: return VMEnumVariant(fn.name,nm,v)
            return fn

        # ADT enum variant with data fields: Shape.Circle(5.0) → tagged dict
        if isinstance(fn, VMEnumVariant):
            v = fn.value
            if isinstance(v, dict) and '__adt_fields__' in v:
                fields = v['__adt_fields__']
                d = {'_variant': fn.name, '_enum': fn.enum_name}
                for i, fname in enumerate(fields):
                    d[fname] = args[i] if i < len(args) else None
                return d
            # Simple variant called as function — just return itself
            return fn

        if isinstance(fn, type) and fn in (Vec2,Vec3,Color,Rect): return fn(*args)
        if callable(fn): return fn(*args)
        raise InScriptRuntimeError(f"'{fn!r}' is not callable",0,0,"")

    def _do_method(self, obj, mname, args):
        m = self._get_field(obj, mname)
        if m is None:
            if isinstance(obj, list):
                r = _list_method(obj, mname, self)(*args)
                return r if r is not _NOTFOUND else None
            if isinstance(obj, str):
                r = _str_method(obj, mname, self)(*args)
                return r if r is not _NOTFOUND else None
            if isinstance(obj, dict):
                # Result type methods
                if '_ok' in obj or '_err' in obj:
                    is_ok = '_ok' in obj
                    val   = obj.get('_ok') if is_ok else obj.get('_err')
                    res_m = {
                        'is_ok':     lambda: is_ok,
                        'is_err':    lambda: not is_ok,
                        'unwrap':    lambda: val if is_ok else (_ for _ in ()).throw(None),
                        'unwrap_or': lambda: val if is_ok else (args[0] if args else None),
                        'value':     lambda: val,
                        'map':       lambda: {'_ok': self.call(args[0],[val])} if is_ok else obj,
                    }
                    if mname in res_m:
                        try: return res_m[mname]()
                        except: raise InScriptRuntimeError(f"unwrap() called on Err({_ins_str(val)})",0,0,"")
                r = _dict_method(obj, mname, self)(*args)
                return r if r is not _NOTFOUND else None
            # int methods
            if isinstance(obj, bool):
                bm = {'to_string': lambda: 'true' if obj else 'false', 'to_int': lambda: int(obj)}
                if mname in bm: return bm[mname]()
            if isinstance(obj, int) and not isinstance(obj, bool):
                import math as _m
                im = {
                    'to_string': lambda: str(obj), 'to_float': lambda: float(obj),
                    'abs': lambda: abs(obj), 'is_even': lambda: obj%2==0,
                    'is_odd': lambda: obj%2!=0,
                    'to_hex': lambda: format(obj,'x'), 'to_bin': lambda: format(obj,'b'),
                    'to_oct': lambda: format(obj,'o'),
                    'pow': lambda: pow(obj, int(args[0])) if args else obj,
                    'gcd': lambda: _m.gcd(obj, int(args[0])) if args else obj,
                    'bit_count': lambda: bin(obj).count('1'),
                    'factorial': lambda: _m.factorial(obj),
                    'clamp': lambda: max(args[0], min(args[1], obj)) if len(args)>=2 else obj,
                }
                if mname in im: return im[mname]()
            if isinstance(obj, float):
                import math as _m
                fm = {
                    'to_string': lambda: str(obj) if not obj.is_integer() else f"{int(obj)}.0",
                    'to_int': lambda: int(obj), 'abs': lambda: abs(obj),
                    'floor': lambda: int(_m.floor(obj)), 'ceil': lambda: int(_m.ceil(obj)),
                    'round': lambda: round(obj, int(args[0])) if args else round(obj),
                    'is_nan': lambda: _m.isnan(obj), 'is_inf': lambda: _m.isinf(obj),
                    'sqrt': lambda: _m.sqrt(obj),
                    'clamp': lambda: max(args[0], min(args[1], obj)) if len(args)>=2 else obj,
                }
                if mname in fm: return fm[mname]()
            if isinstance(obj, VMInstance):
                import copy as _copy_mod
                if mname == 'copy':
                    nf = {}
                    for k, v in obj.fields.items():
                        nf[k] = _copy_mod.deepcopy(v) if isinstance(v,(list,dict)) else v
                    return VMInstance(obj.struct_name, nf, obj._desc)
                if mname == 'to_dict':
                    return {k: v for k,v in obj.fields.items() if not isinstance(v,VMClosure)}
                if mname == 'has': return args[0] in obj.fields if args else False
            # Generic Python object fallback (stdlib objects: Queue, Set, etc.)
            if hasattr(obj, mname):
                attr = getattr(obj, mname)
                if callable(attr): return attr(*args)
                return attr
            raise InScriptRuntimeError(f"no method '{mname}' on {_type_name(obj)}", 0, 0, "")
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
            inst._priv_fields = desc.get('__priv__', set())
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
