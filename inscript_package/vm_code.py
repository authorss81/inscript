# vm_code.py — InScript .ibc binary format for FnProto
# v2.4.0: Real bytecode, no pickle — custom compact binary encoding
#
# Format per FnProto:
#   name (str) | source_name (str) | flags byte
#   params count + param name strings
#   n_locals (u16) | n_upvals (u16) | is_method (u8)
#   vararg_param (str)
#   consts: count (u32) + each encoded value
#   names:  count (u32) + each string
#   upval_descs: count (u32) + each descriptor
#   nested protos: count (u32) + each proto recursively
#   instructions: count (u32) + each (op u8, a u16, b u16, c u16, line u16)

from __future__ import annotations
import struct
from typing import Any

IBC_MAGIC   = b"INSC\x02\x01"   # v2.4.0 register-VM (distinct from stub \x02\x00)
IBC_VERSION = 3

# Constant type tags
_T_NIL   = 0x00
_T_TRUE  = 0x01
_T_FALSE = 0x02
_T_INT   = 0x03
_T_FLOAT = 0x04
_T_STR   = 0x05
_T_PROTO = 0x06   # nested FnProto
_T_DICT  = 0x07   # dict constant (used for struct descriptors)
_T_LIST  = 0x08   # list constant


# ── Encoder ───────────────────────────────────────────────────────────────────

def _sanitize_value(v):
    """Convert a value to a serializable form; pre-evaluate AST literal nodes."""
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (list, tuple)):
        return [_sanitize_value(x) for x in v]
    if isinstance(v, dict):
        return _sanitize_dict(v)
    if isinstance(v, set):
        return None   # sets not serializable — drop
    # AST literal nodes — evaluate to their Python value
    t = type(v).__name__
    if t == 'IntLiteralExpr':    return v.value
    if t == 'FloatLiteralExpr':  return float(v.value)
    if t == 'StringLiteralExpr': return v.value
    if t == 'BoolLiteralExpr':   return v.value
    if t == 'NilLiteralExpr':    return None
    if t == 'NullLiteralExpr':   return None
    # FnProto (method) — kept as-is for nested encoding
    if hasattr(v, 'code') and hasattr(v, 'name') and hasattr(v, 'params'):
        return v   # FnProto
    # Any other complex object — drop
    return None


def _sanitize_dict(d: dict) -> dict:
    """Recursively sanitize a dict constant for serialization."""
    result = {}
    for k, v in d.items():
        if not isinstance(k, str):
            continue   # only string keys
        san = _sanitize_value(v)
        if san is not None or v is None:  # keep explicit None values
            result[k] = san
    return result


class _Enc:
    def __init__(self):
        self.buf = bytearray()

    def u8(self, v):   self.buf += struct.pack("B",  v & 0xFF)
    def u16(self, v):  self.buf += struct.pack(">H", v & 0xFFFF)
    def u32(self, v):  self.buf += struct.pack(">I", v & 0xFFFFFFFF)
    def i64(self, v):  self.buf += struct.pack(">q", v)
    def f64(self, v):  self.buf += struct.pack(">d", v)

    def string(self, s: str):
        b = s.encode("utf-8")
        self.u32(len(b))
        self.buf += b

    def value(self, v: Any):
        if v is None:
            self.u8(_T_NIL)
        elif v is True:
            self.u8(_T_TRUE)
        elif v is False:
            self.u8(_T_FALSE)
        elif isinstance(v, int):
            self.u8(_T_INT); self.i64(v)
        elif isinstance(v, float):
            self.u8(_T_FLOAT); self.f64(v)
        elif isinstance(v, str):
            self.u8(_T_STR); self.string(v)
        elif isinstance(v, dict):
            self.u8(_T_DICT)
            # Struct descriptors contain AST nodes in __fields__ — pre-evaluate them
            safe = _sanitize_dict(v)
            self.u32(len(safe))
            for k, val in safe.items():
                self.value(k)
                self.value(val)
        elif isinstance(v, (list, tuple)):
            self.u8(_T_LIST)
            items = list(v)
            self.u32(len(items))
            for item in items:
                self.value(item)
        else:
            # FnProto (nested function)
            self.u8(_T_PROTO); self.proto(v)

    def proto(self, p):
        from compiler import FnProto
        self.string(p.name)
        self.string(p.source_name)
        self.u16(p.n_locals)
        self.u16(p.n_upvals)
        self.u8(1 if p.is_method else 0)
        self.string(p.vararg_param or "")
        # params
        self.u32(len(p.params))
        for param in p.params:
            self.string(param)
        # consts
        self.u32(len(p.consts))
        for c in p.consts:
            self.value(c)
        # names
        self.u32(len(p.names))
        for n in p.names:
            self.string(n)
        # upval_descs: each is (in_stack: bool, idx: int)
        self.u32(len(p.upval_descs))
        for ud in p.upval_descs:
            in_stack = ud[0] if isinstance(ud, (list, tuple)) else getattr(ud, 'in_stack', True)
            idx      = ud[1] if isinstance(ud, (list, tuple)) else getattr(ud, 'idx', 0)
            self.u8(1 if in_stack else 0)
            self.u16(idx)
        # nested protos
        self.u32(len(p.protos))
        for sub in p.protos:
            self.proto(sub)
        # instructions: op(u8) a(u16) b(i16) c(i16) line(u16)
        # b and c are signed (can be negative relative jump offsets)
        self.u32(len(p.code))
        for ins in p.code:
            self.u8(int(ins.op))
            self.u16(ins.a & 0xFFFF)
            # b and c: sign-extended i16
            self.buf += struct.pack(">h", max(-32768, min(32767, ins.b)))
            self.buf += struct.pack(">h", max(-32768, min(32767, ins.c)))
            self.u16(ins.line & 0xFFFF)


def encode_proto(p) -> bytes:
    enc = _Enc()
    enc.proto(p)
    return bytes(enc.buf)


def write_ibc(p, path: str):
    payload = encode_proto(p)
    header  = IBC_MAGIC + struct.pack(">BI", IBC_VERSION, len(payload))
    with open(path, "wb") as f:
        f.write(header + payload)


# ── Decoder ───────────────────────────────────────────────────────────────────

class _Dec:
    def __init__(self, data: bytes, pos: int = 0):
        self.data = data
        self.pos  = pos

    def read(self, n):
        b = self.data[self.pos:self.pos+n]; self.pos += n; return b

    def u8(self):  return struct.unpack("B",  self.read(1))[0]
    def u16(self): return struct.unpack(">H", self.read(2))[0]
    def u32(self): return struct.unpack(">I", self.read(4))[0]
    def i64(self): return struct.unpack(">q", self.read(8))[0]
    def f64(self): return struct.unpack(">d", self.read(8))[0]

    def string(self):
        n = self.u32(); return self.read(n).decode("utf-8")

    def value(self):
        tag = self.u8()
        if tag == _T_NIL:   return None
        if tag == _T_TRUE:  return True
        if tag == _T_FALSE: return False
        if tag == _T_INT:   return self.i64()
        if tag == _T_FLOAT: return self.f64()
        if tag == _T_STR:   return self.string()
        if tag == _T_DICT:
            n = self.u32()
            return {self.value(): self.value() for _ in range(n)}
        if tag == _T_LIST:
            n = self.u32()
            return [self.value() for _ in range(n)]
        if tag == _T_PROTO: return self.proto()
        raise ValueError(f"Unknown constant tag: {tag:#x}")

    def proto(self):
        from compiler import FnProto, Instr, Op
        p             = FnProto(name=self.string())
        p.source_name = self.string()
        p.n_locals    = self.u16()
        p.n_upvals    = self.u16()
        p.is_method   = bool(self.u8())
        p.vararg_param = self.string()
        n_params = self.u32()
        p.params = [self.string() for _ in range(n_params)]
        n_consts = self.u32()
        p.consts = [self.value() for _ in range(n_consts)]
        n_names  = self.u32()
        p.names  = [self.string() for _ in range(n_names)]
        n_upvals = self.u32()
        p.upval_descs = [(bool(self.u8()), self.u16()) for _ in range(n_upvals)]
        n_protos = self.u32()
        p.protos = [self.proto() for _ in range(n_protos)]
        n_ins    = self.u32()
        p.code   = []
        for _ in range(n_ins):
            op_b      = self.u8()
            a         = self.u16()
            b, c      = struct.unpack(">hh", self.read(4))   # signed i16
            line      = self.u16()
            p.code.append(Instr(Op(op_b), a, b, c, line))
        return p


def read_ibc(path: str):
    """Read and verify an .ibc file, return the top-level FnProto."""
    with open(path, "rb") as f:
        data = f.read()
    hdr_len = len(IBC_MAGIC) + 5
    if not data.startswith(IBC_MAGIC):
        raise ValueError(f"Not a valid InScript .ibc file: {path}")
    version, payload_len = struct.unpack(">BI", data[len(IBC_MAGIC):hdr_len])
    if version != IBC_VERSION:
        raise ValueError(f".ibc version mismatch: file={version}, expected={IBC_VERSION}")
    dec = _Dec(data[hdr_len : hdr_len + payload_len])
    return dec.proto()


def decode_proto(data: bytes):
    dec = _Dec(data)
    return dec.proto()
