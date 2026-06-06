// inscript_vm_engine/src/ir.rs
// LLVM IR Emitter — InScript v3.9.1
//
// Converts a Vec<OpCode> (already compiler-optimized) into LLVM IR text
// in SSA (Static Single Assignment) form, suitable for passing to `llc`
// or `opt` for native code generation.
//
// This is a *template-based* emitter: it does not perform full type
// inference across the whole program (that requires the full type system
// planned for v4.0). Instead it emits a conservative IR that:
//   • Represents every Value as an i64 (tagged integer representation)
//   • Emits arithmetic as LLVM integer/float intrinsics
//   • Emits calls to VM runtime helpers for collection ops
//   • Marks each emitted function with `noinline` so the JIT stub layer
//     can patch the call site once the native code is ready
//
// Output format: valid LLVM 17 IR (.ll text), one function per
// compiled "trace" (a linear sequence of opcodes with no backward jumps).
//
// Usage:
//   let emitter = IrEmitter::new("my_trace");
//   let ir_text = emitter.emit(&opcodes);
//   // Write ir_text to a .ll file and pass to llc / opt

use crate::OpCode;
use std::fmt::Write as FmtWrite;

// ─────────────────────────────────────────────────────────────────────────────
// Tagged value representation
//
// We use a 64-bit tagged integer to represent all Value variants at the
// IR level, matching a common NaN-boxing / tag-bit scheme:
//
//   bits 63-48  tag  (0=Int, 1=Float, 2=Bool, 3=Nil, 4=Ptr)
//   bits 47-0   payload
//
// This avoids the need for fat enums in generated IR and keeps the calling
// convention uniform. The VM runtime (future v4.0) will provide
// `__inscript_untag_int`, `__inscript_untag_float`, etc. helpers.
// ─────────────────────────────────────────────────────────────────────────────

const TAG_INT:   u64 = 0x0000_0000_0000_0000;
const TAG_FLOAT: u64 = 0x0001_0000_0000_0000;
const TAG_BOOL:  u64 = 0x0002_0000_0000_0000;
const TAG_NIL:   u64 = 0x0003_0000_0000_0000;

/// Encode a compile-time integer constant as a tagged i64.
fn tag_int(n: i32) -> i64 {
    (TAG_INT | (n as u64 & 0x0000_FFFF_FFFF_FFFF)) as i64
}

/// Encode a compile-time bool as a tagged i64.
fn tag_bool(b: bool) -> i64 {
    (TAG_BOOL | (b as u64)) as i64
}

/// The tagged nil value.
fn tag_nil() -> i64 {
    TAG_NIL as i64
}

// ─────────────────────────────────────────────────────────────────────────────
// IrEmitter
// ─────────────────────────────────────────────────────────────────────────────

pub struct IrEmitter {
    /// Name used for the emitted LLVM function
    trace_name: String,
    /// SSA register counter
    reg: usize,
    /// Stack of SSA register names (simulates VM stack at IR level)
    vstack: Vec<String>,
    /// Accumulated IR lines
    body: String,
    /// Whether we emitted a terminator already
    terminated: bool,
}

impl IrEmitter {
    pub fn new(trace_name: impl Into<String>) -> Self {
        IrEmitter {
            trace_name: trace_name.into(),
            reg: 0,
            vstack: Vec::new(),
            body: String::new(),
            terminated: false,
        }
    }

    /// Allocate a fresh SSA register name.
    fn fresh(&mut self) -> String {
        let r = format!("%v{}", self.reg);
        self.reg += 1;
        r
    }

    /// Emit a raw IR line into the function body.
    fn emit(&mut self, line: impl AsRef<str>) {
        self.body.push_str("  ");
        self.body.push_str(line.as_ref());
        self.body.push('\n');
    }

    /// Push a register onto the virtual stack.
    fn vpush(&mut self, reg: String) {
        self.vstack.push(reg);
    }

    /// Pop a register from the virtual stack.
    fn vpop(&mut self) -> Option<String> {
        self.vstack.pop()
    }

    /// Emit IR for a binary integer arithmetic operation.
    /// Both operands are assumed to be TAG_INT-tagged i64s.
    /// We extract the payload, operate, re-tag, and push result.
    fn emit_int_arith(&mut self, llvm_op: &str) {
        let b_reg = match self.vpop() { Some(r) => r, None => return };
        let a_reg = match self.vpop() { Some(r) => r, None => return };

        // Untag: mask off the tag bits (lower 48 bits = payload)
        let mask = self.fresh();
        self.emit(format!("{} = and i64 {}, 281474976710655  ; 0xFFFFFFFFFFFF", mask, a_reg));
        let mask_b = self.fresh();
        self.emit(format!("{} = and i64 {}, 281474976710655", mask_b, b_reg));

        // Truncate to i32 for arithmetic (payload fits)
        let a32 = self.fresh();
        self.emit(format!("{} = trunc i64 {} to i32", a32, mask));
        let b32 = self.fresh();
        self.emit(format!("{} = trunc i64 {} to i32", b32, mask_b));

        // Perform operation
        let result32 = self.fresh();
        self.emit(format!("{} = {} i32 {}, {}", result32, llvm_op, a32, b32));

        // Zero-extend back to i64 and re-tag as INT (tag = 0, so just zext)
        let result64 = self.fresh();
        self.emit(format!("{} = zext i32 {} to i64", result64, result32));

        self.vpush(result64);
    }

    /// Emit IR for integer division — result is float (matches v3.8.3 fix).
    fn emit_int_div(&mut self) {
        let b_reg = match self.vpop() { Some(r) => r, None => return };
        let a_reg = match self.vpop() { Some(r) => r, None => return };

        // Untag
        let ma = self.fresh();
        self.emit(format!("{} = and i64 {}, 281474976710655", ma, a_reg));
        let mb = self.fresh();
        self.emit(format!("{} = and i64 {}, 281474976710655", mb, b_reg));

        // Sitofp to double
        let fa = self.fresh();
        self.emit(format!("{} = sitofp i64 {} to double", fa, ma));
        let fb = self.fresh();
        self.emit(format!("{} = sitofp i64 {} to double", fb, mb));

        // fdiv
        let fd = self.fresh();
        self.emit(format!("{} = fdiv double {}, {}", fd, fa, fb));

        // Bitcast float bits to i64 then OR in float tag
        let fbits = self.fresh();
        self.emit(format!("{} = bitcast double {} to i64", fbits, fd));
        let tagged = self.fresh();
        self.emit(format!("{} = or i64 {}, {}", tagged, fbits, TAG_FLOAT as i64));

        self.vpush(tagged);
    }

    /// Emit IR for a comparison, result is tagged bool.
    fn emit_cmp(&mut self, icmp_pred: &str) {
        let b_reg = match self.vpop() { Some(r) => r, None => return };
        let a_reg = match self.vpop() { Some(r) => r, None => return };

        let ma = self.fresh();
        self.emit(format!("{} = and i64 {}, 281474976710655", ma, a_reg));
        let mb = self.fresh();
        self.emit(format!("{} = and i64 {}, 281474976710655", mb, b_reg));

        let cmp = self.fresh();
        self.emit(format!("{} = icmp {} i64 {}, {}", cmp, icmp_pred, ma, mb));

        // zext i1 to i64, then tag as BOOL
        let ext = self.fresh();
        self.emit(format!("{} = zext i1 {} to i64", ext, cmp));
        let tagged = self.fresh();
        self.emit(format!("{} = or i64 {}, {}", tagged, ext, TAG_BOOL as i64));

        self.vpush(tagged);
    }

    /// Main emit method — processes opcodes and returns complete .ll IR text.
    pub fn emit_trace(&mut self, opcodes: &[OpCode]) -> String {
        // Collect external runtime declarations we need
        let mut decls = String::new();
        let mut needs_runtime = false;

        for op in opcodes {
            if !self.terminated {
                match op {
                    OpCode::Push(n) => {
                        let tagged = tag_int(*n);
                        let r = self.fresh();
                        self.emit(format!("{} = add i64 0, {}  ; Push({})", r, tagged, n));
                        self.vpush(r);
                    }

                    OpCode::Pop => {
                        self.vpop();
                    }

                    OpCode::Duplicate => {
                        if let Some(top) = self.vstack.last().cloned() {
                            self.vpush(top);
                        }
                    }

                    OpCode::Swap => {
                        let len = self.vstack.len();
                        if len >= 2 {
                            self.vstack.swap(len - 1, len - 2);
                        }
                    }

                    OpCode::Add  => self.emit_int_arith("add nsw"),
                    OpCode::Sub  => self.emit_int_arith("sub nsw"),
                    OpCode::Mul  => self.emit_int_arith("mul nsw"),
                    OpCode::Mod  => self.emit_int_arith("srem"),
                    OpCode::Div  => self.emit_int_div(),

                    OpCode::Negate => {
                        if let Some(r) = self.vpop() {
                            let m = self.fresh();
                            self.emit(format!("{} = and i64 {}, 281474976710655", m, r));
                            let neg = self.fresh();
                            self.emit(format!("{} = sub i64 0, {}", neg, m));
                            self.vpush(neg);
                        }
                    }

                    OpCode::Power => {
                        // Call runtime helper — pow not inlinable in simple IR
                        needs_runtime = true;
                        let b = match self.vpop() { Some(r) => r, None => continue };
                        let a = match self.vpop() { Some(r) => r, None => continue };
                        let r = self.fresh();
                        self.emit(format!("{} = call i64 @__inscript_pow(i64 {}, i64 {})", r, a, b));
                        self.vpush(r);
                    }

                    OpCode::Equal        => self.emit_cmp("eq"),
                    OpCode::NotEqual     => self.emit_cmp("ne"),
                    OpCode::LessThan     => self.emit_cmp("slt"),
                    OpCode::LessEqual    => self.emit_cmp("sle"),
                    OpCode::GreaterThan  => self.emit_cmp("sgt"),
                    OpCode::GreaterEqual => self.emit_cmp("sge"),

                    OpCode::Not => {
                        if let Some(r) = self.vpop() {
                            // Extract payload, compare to 0, invert
                            let payload = self.fresh();
                            self.emit(format!("{} = and i64 {}, 281474976710655", payload, r));
                            let is_zero = self.fresh();
                            self.emit(format!("{} = icmp eq i64 {}, 0", is_zero, payload));
                            let ext = self.fresh();
                            self.emit(format!("{} = zext i1 {} to i64", ext, is_zero));
                            let tagged = self.fresh();
                            self.emit(format!("{} = or i64 {}, {}", tagged, ext, TAG_BOOL as i64));
                            self.vpush(tagged);
                        }
                    }

                    OpCode::And => {
                        let b = match self.vpop() { Some(r) => r, None => continue };
                        let a = match self.vpop() { Some(r) => r, None => continue };
                        let pa = self.fresh();
                        self.emit(format!("{} = and i64 {}, 281474976710655", pa, a));
                        let pb = self.fresh();
                        self.emit(format!("{} = and i64 {}, 281474976710655", pb, b));
                        let ba = self.fresh();
                        self.emit(format!("{} = icmp ne i64 {}, 0", ba, pa));
                        let bb = self.fresh();
                        self.emit(format!("{} = icmp ne i64 {}, 0", bb, pb));
                        let both = self.fresh();
                        self.emit(format!("{} = and i1 {}, {}", both, ba, bb));
                        let ext = self.fresh();
                        self.emit(format!("{} = zext i1 {} to i64", ext, both));
                        let tagged = self.fresh();
                        self.emit(format!("{} = or i64 {}, {}", tagged, ext, TAG_BOOL as i64));
                        self.vpush(tagged);
                    }

                    OpCode::Or => {
                        let b = match self.vpop() { Some(r) => r, None => continue };
                        let a = match self.vpop() { Some(r) => r, None => continue };
                        let pa = self.fresh();
                        self.emit(format!("{} = and i64 {}, 281474976710655", pa, a));
                        let pb = self.fresh();
                        self.emit(format!("{} = and i64 {}, 281474976710655", pb, b));
                        let ba = self.fresh();
                        self.emit(format!("{} = icmp ne i64 {}, 0", ba, pa));
                        let bb = self.fresh();
                        self.emit(format!("{} = icmp ne i64 {}, 0", bb, pb));
                        let either = self.fresh();
                        self.emit(format!("{} = or i1 {}, {}", either, ba, bb));
                        let ext = self.fresh();
                        self.emit(format!("{} = zext i1 {} to i64", ext, either));
                        let tagged = self.fresh();
                        self.emit(format!("{} = or i64 {}, {}", tagged, ext, TAG_BOOL as i64));
                        self.vpush(tagged);
                    }

                    OpCode::Jump(addr) => {
                        self.emit(format!("br label %L{}", addr));
                        self.terminated = true;
                    }

                    OpCode::JumpIfFalse(addr) => {
                        if let Some(r) = self.vpop() {
                            let payload = self.fresh();
                            self.emit(format!("{} = and i64 {}, 281474976710655", payload, r));
                            let cond = self.fresh();
                            self.emit(format!("{} = icmp eq i64 {}, 0", cond, payload));
                            let next = self.reg;
                            self.emit(format!("br i1 {}, label %L{}, label %L{}", cond, addr, next));
                            // Emit fall-through label
                            let _ = write!(self.body, "L{}:\n", next);
                        }
                    }

                    OpCode::JumpIfTrue(addr) => {
                        if let Some(r) = self.vpop() {
                            let payload = self.fresh();
                            self.emit(format!("{} = and i64 {}, 281474976710655", payload, r));
                            let cond = self.fresh();
                            self.emit(format!("{} = icmp ne i64 {}, 0", cond, payload));
                            let next = self.reg;
                            self.emit(format!("br i1 {}, label %L{}, label %L{}", cond, addr, next));
                            let _ = write!(self.body, "L{}:\n", next);
                        }
                    }

                    OpCode::StoreReg(reg) => {
                        needs_runtime = true;
                        if let Some(val) = self.vpop() {
                            self.emit(format!(
                                "call void @__inscript_store_reg(i64 {}, i64 {})",
                                reg, val
                            ));
                        }
                    }

                    OpCode::LoadReg(reg) => {
                        needs_runtime = true;
                        let r = self.fresh();
                        self.emit(format!(
                            "{} = call i64 @__inscript_load_reg(i64 {})",
                            r, reg
                        ));
                        self.vpush(r);
                    }

                    OpCode::LoadGlobal(idx) => {
                        needs_runtime = true;
                        let r = self.fresh();
                        self.emit(format!(
                            "{} = call i64 @__inscript_load_global(i64 {})",
                            r, idx
                        ));
                        self.vpush(r);
                    }

                    OpCode::StoreGlobal(idx) => {
                        needs_runtime = true;
                        if let Some(val) = self.vpop() {
                            self.emit(format!(
                                "call void @__inscript_store_global(i64 {}, i64 {})",
                                idx, val
                            ));
                        }
                    }

                    OpCode::CreateArray(_) | OpCode::CreateObject(_)
                    | OpCode::Index | OpCode::SetIndex
                    | OpCode::Concat | OpCode::Length => {
                        // Collection ops always call runtime — can't inline
                        needs_runtime = true;
                        let r = self.fresh();
                        self.emit(format!(
                            "{} = call i64 @__inscript_collection_op(i64 {})",
                            r, self.reg as i64
                        ));
                        self.vpush(r);
                    }

                    OpCode::Call(args) => {
                        needs_runtime = true;
                        // Pop args + function value, call runtime dispatch
                        for _ in 0..*args { self.vpop(); }
                        let func = self.vpop().unwrap_or_else(|| "0".to_string());
                        let r = self.fresh();
                        self.emit(format!(
                            "{} = call i64 @__inscript_call(i64 {}, i64 {})",
                            r, func, args
                        ));
                        self.vpush(r);
                    }

                    OpCode::Return => {
                        let ret = self.vpop()
                            .unwrap_or_else(|| format!("{}", tag_nil()));
                        self.emit(format!("ret i64 {}", ret));
                        self.terminated = true;
                    }

                    OpCode::Halt => {
                        let ret = self.vpop()
                            .unwrap_or_else(|| format!("{}", tag_nil()));
                        self.emit(format!("ret i64 {}  ; Halt", ret));
                        self.terminated = true;
                    }

                    OpCode::Nop => { /* already removed by compiler passes */ }
                }
                // NOTE: match is exhaustive — all 37 OpCode variants are handled above.
            }
        }

        // Emit final return if not yet terminated
        if !self.terminated {
            let ret = self.vpop()
                .unwrap_or_else(|| format!("{}", tag_nil()));
            self.emit(format!("ret i64 {}", ret));
        }

        // Runtime declarations
        if needs_runtime {
            decls.push_str("declare i64 @__inscript_pow(i64, i64)\n");
            decls.push_str("declare void @__inscript_store_reg(i64, i64)\n");
            decls.push_str("declare i64 @__inscript_load_reg(i64)\n");
            decls.push_str("declare i64 @__inscript_load_global(i64)\n");
            decls.push_str("declare void @__inscript_store_global(i64, i64)\n");
            decls.push_str("declare i64 @__inscript_collection_op(i64)\n");
            decls.push_str("declare i64 @__inscript_call(i64, i64)\n");

            decls.push('\n');
        }

        // Assemble complete .ll module
        let mut out = String::new();
        let _ = writeln!(out, "; InScript v3.9.1 — Generated LLVM IR");
        let _ = writeln!(out, "; Trace: {}", self.trace_name);
        let _ = writeln!(out, "; DO NOT EDIT — auto-generated by ir.rs\n");
        let _ = writeln!(out, "target triple = \"x86_64-unknown-linux-gnu\"");
        let _ = writeln!(out, "target datalayout = \"e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128\"\n");
        out.push_str(&decls);
        let _ = writeln!(out, "define i64 @{}() noinline {{", self.trace_name);
        let _ = writeln!(out, "entry:");
        out.push_str(&self.body);
        let _ = writeln!(out, "}}");

        out
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Convenience wrapper
// ─────────────────────────────────────────────────────────────────────────────

/// Emit LLVM IR for a slice of opcodes. Returns the .ll text.
pub fn emit_ir(trace_name: &str, opcodes: &[OpCode]) -> String {
    let mut emitter = IrEmitter::new(trace_name);
    emitter.emit_trace(opcodes)
}

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn emit_empty_trace() {
        let ir = emit_ir("test_empty", &[]);
        assert!(ir.contains("define i64 @test_empty()"));
        assert!(ir.contains("ret i64"));
    }

    #[test]
    fn emit_push_halt() {
        let ops = vec![OpCode::Push(42), OpCode::Halt];
        let ir = emit_ir("test_push", &ops);
        assert!(ir.contains("define i64 @test_push()"));
        assert!(ir.contains("Push(42)"));
        assert!(ir.contains("ret i64"));
        assert!(ir.contains("Halt"));
    }

    #[test]
    fn emit_add() {
        let ops = vec![OpCode::Push(3), OpCode::Push(4), OpCode::Add, OpCode::Halt];
        let ir = emit_ir("test_add", &ops);
        assert!(ir.contains("add nsw"));
        assert!(ir.contains("ret i64"));
    }

    #[test]
    fn emit_sub() {
        let ops = vec![OpCode::Push(10), OpCode::Push(3), OpCode::Sub, OpCode::Return];
        let ir = emit_ir("test_sub", &ops);
        assert!(ir.contains("sub nsw"));
    }

    #[test]
    fn emit_mul() {
        let ops = vec![OpCode::Push(6), OpCode::Push(7), OpCode::Mul, OpCode::Halt];
        let ir = emit_ir("test_mul", &ops);
        assert!(ir.contains("mul nsw"));
    }

    #[test]
    fn emit_div_produces_float_ir() {
        let ops = vec![OpCode::Push(5), OpCode::Push(2), OpCode::Div, OpCode::Halt];
        let ir = emit_ir("test_div", &ops);
        // Division path uses sitofp + fdiv
        assert!(ir.contains("sitofp"));
        assert!(ir.contains("fdiv"));
    }

    #[test]
    fn emit_comparisons() {
        for (op, pred) in &[
            (OpCode::Equal,        "eq"),
            (OpCode::NotEqual,     "ne"),
            (OpCode::LessThan,     "slt"),
            (OpCode::LessEqual,    "sle"),
            (OpCode::GreaterThan,  "sgt"),
            (OpCode::GreaterEqual, "sge"),
        ] {
            let ops = vec![OpCode::Push(1), OpCode::Push(2), op.clone(), OpCode::Halt];
            let ir = emit_ir("test_cmp", &ops);
            assert!(ir.contains(pred), "Missing predicate '{}' for {:?}", pred, op);
        }
    }

    #[test]
    fn emit_not() {
        let ops = vec![OpCode::Push(0), OpCode::Not, OpCode::Halt];
        let ir = emit_ir("test_not", &ops);
        assert!(ir.contains("icmp eq"));
    }

    #[test]
    fn emit_and_or() {
        let ops = vec![OpCode::Push(1), OpCode::Push(0), OpCode::And, OpCode::Halt];
        let ir = emit_ir("test_and", &ops);
        assert!(ir.contains("and i1"));

        let ops2 = vec![OpCode::Push(1), OpCode::Push(0), OpCode::Or, OpCode::Halt];
        let ir2 = emit_ir("test_or", &ops2);
        assert!(ir2.contains("or i1"));
    }

    #[test]
    fn emit_negate() {
        let ops = vec![OpCode::Push(5), OpCode::Negate, OpCode::Halt];
        let ir = emit_ir("test_negate", &ops);
        assert!(ir.contains("sub i64 0,"));
    }

    #[test]
    fn emit_jump() {
        let ops = vec![OpCode::Push(1), OpCode::Jump(0)];
        let ir = emit_ir("test_jump", &ops);
        assert!(ir.contains("br label %L0"));
    }

    #[test]
    fn emit_jump_if_false() {
        let ops = vec![OpCode::Push(0), OpCode::JumpIfFalse(5), OpCode::Halt];
        let ir = emit_ir("test_jif", &ops);
        assert!(ir.contains("br i1"));
        assert!(ir.contains("L5"));
    }

    #[test]
    fn emit_load_store_reg() {
        let ops = vec![OpCode::Push(99), OpCode::StoreReg(0), OpCode::LoadReg(0), OpCode::Halt];
        let ir = emit_ir("test_regs", &ops);
        assert!(ir.contains("@__inscript_store_reg"));
        assert!(ir.contains("@__inscript_load_reg"));
        assert!(ir.contains("declare"));
    }

    #[test]
    fn emit_global() {
        let ops = vec![OpCode::LoadGlobal(0), OpCode::Halt];
        let ir = emit_ir("test_global", &ops);
        assert!(ir.contains("@__inscript_load_global"));
    }

    #[test]
    fn emit_power_uses_runtime() {
        let ops = vec![OpCode::Push(3), OpCode::Push(2), OpCode::Power, OpCode::Halt];
        let ir = emit_ir("test_pow", &ops);
        assert!(ir.contains("@__inscript_pow"));
    }

    #[test]
    fn emit_duplicate_no_ir() {
        // Duplicate is purely a vstack operation — emits no IR instructions
        let ops = vec![OpCode::Push(7), OpCode::Duplicate, OpCode::Add, OpCode::Halt];
        let ir = emit_ir("test_dup", &ops);
        // Should compile to add nsw (7+7)
        assert!(ir.contains("add nsw"));
    }

    #[test]
    fn emit_swap() {
        // Swap is a vstack swap — no IR emitted, but subsequent ops see swapped order
        let ops = vec![
            OpCode::Push(1), OpCode::Push(2),
            OpCode::Swap,
            OpCode::Sub,   // 2 - 1 = 1, not 1 - 2
            OpCode::Halt,
        ];
        let ir = emit_ir("test_swap", &ops);
        assert!(ir.contains("sub nsw"));
    }

    #[test]
    fn emit_tag_int_encoding() {
        // tag_int(0) should be 0 (TAG_INT=0, payload=0)
        assert_eq!(tag_int(0), 0);
        // tag_int(1) should be 1
        assert_eq!(tag_int(1), 1);
        // tag_bool(true) should have TAG_BOOL bits set
        assert_eq!(tag_bool(true) as u64 & !0xFFFF_FFFF_FFFFu64, TAG_BOOL);
    }

    #[test]
    fn emit_nil_encoding() {
        assert_eq!(tag_nil() as u64 & !0xFFFF_FFFF_FFFFu64, TAG_NIL);
    }

    #[test]
    fn ir_is_valid_text() {
        let ops = vec![
            OpCode::Push(2), OpCode::Push(3), OpCode::Mul,
            OpCode::Push(1), OpCode::Add,
            OpCode::Halt,
        ];
        let ir = emit_ir("test_valid", &ops);
        // Basic structural checks
        assert!(ir.starts_with("; InScript"));
        assert!(ir.contains("target triple"));
        assert!(ir.contains("define i64 @test_valid()"));
        assert!(ir.contains("entry:"));
        assert!(ir.ends_with("}\n"));
    }

    #[test]
    fn no_panic_on_underflow() {
        // Operations with empty vstack should not panic
        let ops = vec![OpCode::Add, OpCode::Halt];
        let ir = emit_ir("test_underflow", &ops);
        assert!(ir.contains("ret i64"));
    }
}
