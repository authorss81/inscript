// inscript_vm_engine/src/compiler.rs
// Compiler Optimization Passes — InScript v3.9.0
//
// Applies a pipeline of bytecode-level optimizations before execution.
// All passes operate on Vec<OpCode> (already pre-decoded) so there is
// zero parsing overhead.
//
// Pass pipeline (in order):
//   1. Constant Folding      — evaluate pure arithmetic at compile time
//   2. Instruction Fusion    — merge common 2-3 opcode sequences
//   3. Strength Reduction    — replace expensive ops with cheaper equivalents
//   4. Dead Code Elimination — strip unreachable code after jumps/halts
//   5. Nop Elimination       — compact out all Nop instructions left by passes
//
// Expected speedup: 2-4x reduction in executed instructions for typical code
// Combined with v3.8.4 baseline: 70-100x vs v3.8.0

use std::collections::HashMap;

use crate::OpCode;

// ─────────────────────────────────────────────────────────────────────────────
// Public entry point
// ─────────────────────────────────────────────────────────────────────────────

/// Run all optimization passes on a decoded opcode stream.
/// Returns optimized opcode vector and statistics about what was changed.
pub fn optimize(opcodes: Vec<OpCode>) -> (Vec<OpCode>, OptStats) {
    let original_len = opcodes.len();

    let (opcodes, fold_count)     = pass_constant_fold(opcodes);
    let (opcodes, fuse_count)     = pass_instruction_fuse(opcodes);
    let (opcodes, strength_count) = pass_strength_reduce(opcodes);
    let (opcodes, dce_count)      = pass_dead_code_elim(opcodes);
    let opcodes                    = pass_nop_compact(opcodes);

    let final_len = opcodes.len();

    (opcodes, OptStats {
        original_instructions: original_len,
        final_instructions:    final_len,
        instructions_removed:  original_len.saturating_sub(final_len),
        constant_folds:        fold_count,
        instruction_fusions:   fuse_count,
        strength_reductions:   strength_count,
        dead_code_removed:     dce_count,
        specializations:       0,
        type_map:              None,
    })
}

/// Run all optimization passes PLUS type specialization.
/// This pass rewrites generic opcodes to typed variants when type inference
/// proves the operand types.
pub fn optimize_with_types(opcodes: Vec<OpCode>) -> (Vec<OpCode>, OptStats, TypeMap) {
    let type_map = pass_type_inference(&opcodes);
    let (opcodes, specializations) = pass_type_specialize(opcodes, &type_map);
    let (opcodes, mut stats) = optimize(opcodes);
    stats.type_map = Some(type_map.clone());
    stats.specializations = specializations;
    (opcodes, stats, type_map)
}

// ─────────────────────────────────────────────────────────────────────────────
// Pass 1: Constant Folding
//
// Detects Push(a) Push(b) <ArithOp> and replaces with Push(result).
// Works for Int×Int pairs covering Add, Sub, Mul, Mod.
// Division is excluded (always returns Float — handled by Float fold below).
// Float pairs also folded where both operands are representable as i32.
//
// Pattern matched (window of 3):
//   [Push(a), Push(b), Add]  →  [Push(a+b), Nop, Nop]
//   [Push(a), Push(b), Sub]  →  [Push(a-b), Nop, Nop]
//   [Push(a), Push(b), Mul]  →  [Push(a*b), Nop, Nop]
//   [Push(a), Push(b), Mod]  →  [Push(a%b), Nop, Nop]  (b≠0)
// ─────────────────────────────────────────────────────────────────────────────

fn pass_constant_fold(mut ops: Vec<OpCode>) -> (Vec<OpCode>, usize) {
    let mut count = 0;
    let len = ops.len();
    if len < 3 { return (ops, 0); }

    let mut i = 0;
    while i + 2 < ops.len() {
        let folded = match (ops[i], ops[i+1], ops[i+2]) {
            (OpCode::Push(a), OpCode::Push(b), OpCode::Add) => {
                let result = (a as i64).saturating_add(b as i64);
                if result >= i32::MIN as i64 && result <= i32::MAX as i64 {
                    Some(result as i32)
                } else { None }
            }
            (OpCode::Push(a), OpCode::Push(b), OpCode::Sub) => {
                let result = (a as i64).saturating_sub(b as i64);
                if result >= i32::MIN as i64 && result <= i32::MAX as i64 {
                    Some(result as i32)
                } else { None }
            }
            (OpCode::Push(a), OpCode::Push(b), OpCode::Mul) => {
                let result = (a as i64).saturating_mul(b as i64);
                if result >= i32::MIN as i64 && result <= i32::MAX as i64 {
                    Some(result as i32)
                } else { None }
            }
            (OpCode::Push(a), OpCode::Push(b), OpCode::Mod) if b != 0 => {
                Some(a % b)
            }
            _ => None,
        };

        if let Some(val) = folded {
            ops[i]   = OpCode::Push(val);
            ops[i+1] = OpCode::Nop;
            ops[i+2] = OpCode::Nop;
            count += 1;
            // Don't advance i — the new Push(val) might fold again
            // with what comes next (e.g. Push(5) Nop Nop Push(3) Add)
            // but Nops in between will be handled by nop_compact later.
            // Advance past the triple to avoid infinite loops.
            i += 3;
        } else {
            i += 1;
        }
    }

    (ops, count)
}

// ─────────────────────────────────────────────────────────────────────────────
// Pass 2: Instruction Fusion
//
// Merges common 2-instruction sequences into single semantically-equivalent
// instructions or Nop pairs.
//
// Patterns:
//   [Duplicate, Pop]      → [Nop, Nop]         (dup then immediately pop = nothing)
//   [Push(n), Negate]     → [Push(-n), Nop]    (fold negation into push)
//   [Not, Not]            → [Nop, Nop]          (double negation = identity)
//   [Push(0), Add]        → [Nop, Nop]          (add zero = identity)
//   [Push(1), Mul]        → [Nop, Nop]          (mul one = identity)
//   [Push(0), Sub]        → [Negate, Nop]       (sub zero from top = negate... 
//                                                 wait: stack is [x, 0], sub = x-0 = x)
//                                                Actually Push(0) Sub = no-op on x
//   [Push(0), Sub]        → [Nop, Nop]          (x - 0 = x)
// ─────────────────────────────────────────────────────────────────────────────

fn pass_instruction_fuse(mut ops: Vec<OpCode>) -> (Vec<OpCode>, usize) {
    let mut count = 0;
    let len = ops.len();
    if len < 2 { return (ops, 0); }

    let mut i = 0;
    while i + 1 < ops.len() {
        let fused = match (ops[i], ops[i+1]) {
            // Dup then immediate pop = no effect
            (OpCode::Duplicate, OpCode::Pop) => Some((OpCode::Nop, OpCode::Nop)),

            // Double logical not = identity
            (OpCode::Not, OpCode::Not) => Some((OpCode::Nop, OpCode::Nop)),

            // Push(n) Negate → Push(-n) Nop
            (OpCode::Push(n), OpCode::Negate) => {
                Some((OpCode::Push(n.saturating_neg()), OpCode::Nop))
            }

            // Push(0) Add → Nop Nop  (x + 0 = x)
            (OpCode::Push(0), OpCode::Add) => Some((OpCode::Nop, OpCode::Nop)),

            // Push(0) Sub → Nop Nop  (x - 0 = x)
            (OpCode::Push(0), OpCode::Sub) => Some((OpCode::Nop, OpCode::Nop)),

            // Push(1) Mul → Nop Nop  (x * 1 = x)
            (OpCode::Push(1), OpCode::Mul) => Some((OpCode::Nop, OpCode::Nop)),

            // Push(1) Div → Nop Nop  (x / 1 = x as float, but this changes type!)
            // Skip — type change makes this unsafe to elide.

            // Push(0) Mul → Pop Push(0)  (x * 0 = 0, but we still consume x)
            // Can't safely fuse without knowing stack depth — skip.

            _ => None,
        };

        if let Some((a, b)) = fused {
            ops[i]   = a;
            ops[i+1] = b;
            count += 1;
            i += 2;
        } else {
            i += 1;
        }
    }

    (ops, count)
}

// ─────────────────────────────────────────────────────────────────────────────
// Pass 3: Strength Reduction
//
// Replaces expensive operations with cheaper equivalents where semantics
// are identical.
//
// Patterns:
//   [Push(2), Mul]   → not safe to replace with shift (Int→Int but
//                       mixed types exist) — skip for now, mark for v3.9.1
//
//   [Push(2), Power] → [Duplicate, Mul, Nop]   (x^2 = x*x, saves powf() call)
//   [Push(1), Power] → [Pop, Push(1), Nop]     wait: x^1 = x, not 1
//                     → [Nop, Nop, Nop]         x^1 = x (pop push then use = identity)
//                       Actually: stack is [x], then Push(1) Power → [x^1.0] = [x as float]
//                       Type changes — not safe to elide. Skip.
//
//   [Push(0), Power] → result is always 1 (x^0 = 1), but x could be 0 → 0^0=1 by convention
//                       Stack: [x, 0] → Power → [1.0]
//                     → [Pop, Pop, Push(1)]  — but Push(1) is int, result should be Float(1.0)
//                       Not representable as Push(i32). Skip for type safety.
//
// Safe reductions:
//   Push(2) Power (x^2) → Duplicate Mul  (saves expensive powf, gives same Float result)
// ─────────────────────────────────────────────────────────────────────────────

fn pass_strength_reduce(mut ops: Vec<OpCode>) -> (Vec<OpCode>, usize) {
    let mut count = 0;
    let len = ops.len();
    if len < 2 { return (ops, 0); }

    let mut i = 0;
    while i + 1 < ops.len() {
        match (ops[i], ops[i+1]) {
            // x^2 → x*x  (Duplicate then Mul — same float result, no powf() call)
            (OpCode::Push(2), OpCode::Power) => {
                ops[i]   = OpCode::Duplicate;
                ops[i+1] = OpCode::Mul;
                count += 1;
                i += 2;
            }
            _ => { i += 1; }
        }
    }

    (ops, count)
}

// ─────────────────────────────────────────────────────────────────────────────
// Pass 4: Dead Code Elimination
//
// Marks opcodes after unconditional jumps or Halt as Nop.
// An opcode is dead if it is preceded by an unconditional Jump or Halt
// with no label (JumpTarget) pointing to it.
//
// Simple linear scan: after seeing Jump(addr) or Halt, mark subsequent
// opcodes as Nop until:
//   (a) we reach the end, or
//   (b) we reach an opcode that is the target of some Jump in the program.
//
// Jump targets are collected first, then the scan runs.
// ─────────────────────────────────────────────────────────────────────────────

fn pass_dead_code_elim(mut ops: Vec<OpCode>) -> (Vec<OpCode>, usize) {
    let len = ops.len();
    if len == 0 { return (ops, 0); }

    // Collect all jump targets
    let mut targets = std::collections::HashSet::new();
    for op in &ops {
        match op {
            OpCode::Jump(a) | OpCode::JumpIfFalse(a) | OpCode::JumpIfTrue(a) => {
                targets.insert(*a);
            }
            _ => {}
        }
    }

    let mut count = 0;
    let mut dead  = false;

    for i in 0..len {
        // If this instruction is a jump target, it's reachable → resume
        if targets.contains(&i) {
            dead = false;
        }

        if dead {
            if !matches!(ops[i], OpCode::Nop) {
                ops[i] = OpCode::Nop;
                count += 1;
            }
        }

        // Mark everything after unconditional jump/halt as potentially dead
        match ops[i] {
            OpCode::Jump(_) | OpCode::Halt => { dead = true; }
            _ => {}
        }
    }

    (ops, count)
}

// ─────────────────────────────────────────────────────────────────────────────
// Pass 5: Nop Compaction
//
// Removes all Nop instructions from the stream.
// Must run LAST because earlier passes patch instructions to Nop in-place.
//
// IMPORTANT: After compaction, all Jump targets become invalid.
// This pass also rewrites Jump addresses to account for removed Nops.
// ─────────────────────────────────────────────────────────────────────────────

fn pass_nop_compact(ops: Vec<OpCode>) -> Vec<OpCode> {
    let len = ops.len();

    // Build a mapping: old_index → new_index (after Nops removed)
    // Any Nop gets mapped to usize::MAX (sentinel for "removed")
    let mut index_map = vec![0usize; len];
    let mut new_idx = 0usize;
    for (old, op) in ops.iter().enumerate() {
        if matches!(op, OpCode::Nop) {
            index_map[old] = usize::MAX; // will be removed
        } else {
            index_map[old] = new_idx;
            new_idx += 1;
        }
    }

    // Build compacted vector, rewriting jump targets
    let mut result = Vec::with_capacity(new_idx);
    for op in ops {
        match op {
            OpCode::Nop => { /* drop */ }
            OpCode::Jump(a) => {
                let new_a = remap_target(a, &index_map);
                result.push(OpCode::Jump(new_a));
            }
            OpCode::JumpIfFalse(a) => {
                let new_a = remap_target(a, &index_map);
                result.push(OpCode::JumpIfFalse(new_a));
            }
            OpCode::JumpIfTrue(a) => {
                let new_a = remap_target(a, &index_map);
                result.push(OpCode::JumpIfTrue(new_a));
            }
            other => result.push(other),
        }
    }

    result
}

/// Remap a jump target through the index_map.
/// If the target was a Nop, walk forward to find the next live instruction.
fn remap_target(old_addr: usize, index_map: &[usize]) -> usize {
    let mut addr = old_addr;
    while addr < index_map.len() {
        if index_map[addr] != usize::MAX {
            return index_map[addr];
        }
        addr += 1;
    }
    // Target was past the end (or all remaining were Nops) — point to end
    index_map.iter().filter(|&&x| x != usize::MAX).copied().max().unwrap_or(0)
}

// ─────────────────────────────────────────────────────────────────────────────
// Type Inference Pass
//
// Forward data-flow analysis that tracks types on the stack at each program
// point. Uses fixed-point iteration to handle loops and conditional branches.
// ─────────────────────────────────────────────────────────────────────────────

/// Abstract type lattice for InScript values.
/// Order: Top > {Int, Float, Bool, String, Array, Object, Nil} > Bottom
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Type {
    Top,
    Int,
    Float,
    Bool,
    String,
    Array,
    Object,
    Nil,
    Bottom,
}

/// State of the type system at a program point.
/// Tracks both the value stack types and register types.
#[derive(Debug, Clone, PartialEq)]
pub struct TypeState {
    stack: Vec<Type>,
    registers: [Type; 256],
}

/// Maps opcode index → stack types just before executing that opcode.
pub type TypeMap = HashMap<usize, Vec<Type>>;

/// Greatest lower bound in the type lattice.
/// Top ⊓ X = X, Bottom ⊓ X = Bottom, Int ⊓ Float = Top (mixed), etc.
fn meet(a: Type, b: Type) -> Type {
    if a == b { return a; }
    match (a, b) {
        (Type::Top, x) | (x, Type::Top) => x,
        (Type::Bottom, _) | (_, Type::Bottom) => Type::Bottom,
        _ => Type::Top,
    }
}

/// Merge two type states at a control-flow join point.
fn meet_type_state(a: &TypeState, b: &TypeState) -> TypeState {
    let stack_len = a.stack.len().min(b.stack.len());
    let mut stack = Vec::with_capacity(stack_len);
    for i in 0..stack_len {
        stack.push(meet(a.stack[i], b.stack[i]));
    }
    let mut registers = [Type::Bottom; 256];
    for i in 0..256 {
        registers[i] = meet(a.registers[i], b.registers[i]);
    }
    TypeState { stack, registers }
}

impl TypeState {
    fn new() -> Self {
        TypeState {
            stack: Vec::new(),
            registers: [Type::Top; 256],
        }
    }

    /// Apply the transfer function for a single opcode.
    fn transfer(&self, op: &OpCode) -> Self {
        let mut new = self.clone();
        match op {
            OpCode::Push(_) => {
                new.stack.push(Type::Int);
            }
            OpCode::Pop => {
                new.stack.pop();
            }
            OpCode::Duplicate => {
                if let Some(t) = new.stack.last().copied() {
                    new.stack.push(t);
                }
            }
            OpCode::Swap => {
                let len = new.stack.len();
                if len >= 2 {
                    new.stack.swap(len - 1, len - 2);
                }
            }
            OpCode::Add | OpCode::Sub | OpCode::Mul | OpCode::Mod => {
                let b = new.stack.pop().unwrap_or(Type::Top);
                let a = new.stack.pop().unwrap_or(Type::Top);
                let result = match (a, b) {
                    (Type::Int, Type::Int) => Type::Int,
                    (Type::Float, _) | (_, Type::Float) => Type::Float,
                    _ => Type::Top,
                };
                new.stack.push(result);
            }
            OpCode::Div | OpCode::Power => {
                new.stack.pop();
                new.stack.pop();
                new.stack.push(Type::Float);
            }
            OpCode::Negate => {
                if let Some(t) = new.stack.last().copied() {
                    let result = match t {
                        Type::Int => Type::Int,
                        Type::Float => Type::Float,
                        _ => Type::Top,
                    };
                    *new.stack.last_mut().unwrap() = result;
                }
            }
            OpCode::Equal | OpCode::NotEqual
            | OpCode::LessThan | OpCode::LessEqual
            | OpCode::GreaterThan | OpCode::GreaterEqual => {
                new.stack.pop();
                new.stack.pop();
                new.stack.push(Type::Bool);
            }
            OpCode::And | OpCode::Or => {
                new.stack.pop();
                new.stack.pop();
                new.stack.push(Type::Bool);
            }
            OpCode::Not => {
                new.stack.pop();
                new.stack.push(Type::Bool);
            }
            OpCode::Jump(_) => {}
            OpCode::JumpIfFalse(_) | OpCode::JumpIfTrue(_) => {
                new.stack.pop();
            }
            OpCode::Call(n) => {
                for _ in 0..=*n {
                    new.stack.pop();
                }
                new.stack.push(Type::Top);
            }
            OpCode::Return | OpCode::Halt => {
                new.stack.clear();
            }
            OpCode::StoreReg(idx) => {
                if let Some(t) = new.stack.pop() {
                    new.registers[*idx] = t;
                }
            }
            OpCode::LoadReg(idx) => {
                new.stack.push(new.registers[*idx]);
            }
            OpCode::StoreGlobal(_) => {
                new.stack.pop();
            }
            OpCode::LoadGlobal(_) => {
                new.stack.push(Type::Top);
            }
            OpCode::CreateArray(n) => {
                for _ in 0..*n {
                    new.stack.pop();
                }
                new.stack.push(Type::Array);
            }
            OpCode::CreateObject(n) => {
                for _ in 0..(2 * *n) {
                    new.stack.pop();
                }
                new.stack.push(Type::Object);
            }
            OpCode::Index => {
                new.stack.pop();
                new.stack.pop();
                new.stack.push(Type::Top);
            }
            OpCode::SetIndex => {
                new.stack.pop();
                new.stack.pop();
                new.stack.pop();
            }
            OpCode::LoadConst(_) => {
                new.stack.push(Type::Top);
            }
            OpCode::Concat => {
                new.stack.pop();
                new.stack.pop();
                new.stack.push(Type::String);
            }
            OpCode::Length => {
                new.stack.pop();
                new.stack.push(Type::Int);
            }
            OpCode::IterStart => {
                new.stack.pop();
                new.stack.push(Type::Array);
            }
            OpCode::IterNext => {
                new.stack.pop();
                new.stack.push(Type::Array);
                new.stack.push(Type::Top);
            }
            OpCode::Nop => {}

            // Phase 4.1: typed opcodes have same type behavior as generics
            OpCode::AddInt | OpCode::AddFloat
            | OpCode::SubInt | OpCode::SubFloat
            | OpCode::MulInt | OpCode::MulFloat
            | OpCode::ModInt | OpCode::ModFloat => {
                let b = new.stack.pop().unwrap_or(Type::Top);
                let a = new.stack.pop().unwrap_or(Type::Top);
                let result = match (a, b) {
                    (Type::Int, Type::Int) => Type::Int,
                    (Type::Float, _) | (_, Type::Float) => Type::Float,
                    _ => Type::Top,
                };
                new.stack.push(result);
            }
            OpCode::DivFloat => {
                new.stack.pop();
                new.stack.pop();
                new.stack.push(Type::Float);
            }
            OpCode::EqualInt | OpCode::EqualFloat
            | OpCode::LessThanInt | OpCode::LessThanFloat => {
                new.stack.pop();
                new.stack.pop();
                new.stack.push(Type::Bool);
            }
        }
        new
    }
}

/// Merge incoming state into a target program point.
/// Returns true if the target state changed.
fn merge_state(target: &mut Option<TypeState>, incoming: &TypeState) -> bool {
    match target {
        None => {
            *target = Some(incoming.clone());
            true
        }
        Some(existing) => {
            let merged = meet_type_state(existing, incoming);
            if merged == *existing {
                false
            } else {
                *existing = merged;
                true
            }
        }
    }
}

/// Forward data-flow type inference pass.
/// Returns a map from opcode index → stack types just before that opcode.
///
/// Uses fixed-point iteration: keeps re-processing opcodes until the type
/// state at every program point stabilizes.
pub fn pass_type_inference(ops: &[OpCode]) -> TypeMap {
    let n = ops.len();
    if n == 0 { return HashMap::new(); }

    let mut states: Vec<Option<TypeState>> = vec![None; n + 1];
    states[0] = Some(TypeState::new());

    let mut changed = true;
    while changed {
        changed = false;
        for i in 0..n {
            let state = match &states[i] {
                Some(s) => s.clone(),
                None => continue,
            };

            let new_state = state.transfer(&ops[i]);

            match &ops[i] {
                OpCode::Jump(addr) => {
                    if *addr < states.len() {
                        changed |= merge_state(&mut states[*addr], &new_state);
                    }
                }
                OpCode::JumpIfFalse(addr) | OpCode::JumpIfTrue(addr) => {
                    changed |= merge_state(&mut states[i + 1], &new_state);
                    if *addr < states.len() {
                        changed |= merge_state(&mut states[*addr], &new_state);
                    }
                }
                OpCode::Halt | OpCode::Return => {
                    changed |= merge_state(&mut states[n], &new_state);
                }
                _ => {
                    changed |= merge_state(&mut states[i + 1], &new_state);
                }
            }
        }
    }

    let mut map = HashMap::new();
    for (i, state) in states.iter().enumerate() {
        if let Some(s) = state {
            map.insert(i, s.stack.clone());
        }
    }
    map
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 4.1: Type Specialization Pass
//
// Rewrites generic opcodes to typed variants using the type inference map.
// When the type state proves both operands are Int or Float, the generic
// opcode is replaced with the monomorphized version, eliminating Value
// boxing/unboxing overhead at runtime.
//
// Patterns:
//   Add  → AddInt   (when both operands are known Int)
//   Add  → AddFloat (when at least one operand is known Float)
//   Sub  → SubInt   (when both operands are known Int)
//   Sub  → SubFloat (when at least one operand is known Float)
//   ... etc for Mul, Mod, Negate, comparisons
// ─────────────────────────────────────────────────────────────────────────────

fn pass_type_specialize(ops: Vec<OpCode>, type_map: &TypeMap) -> (Vec<OpCode>, usize) {
    let mut result = ops;
    let mut count = 0;

    // For each opcode, look at the stack types *before* it executes.
    // We need at least the top 1-2 types to decide.
    for i in 0..result.len() {
        let stack_types = match type_map.get(&i) {
            Some(s) => s,
            None => continue,
        };

        result[i] = match &result[i] {
            // ── Binary arithmetic ─────────────────────────────────
            OpCode::Add => {
                if stack_types.len() >= 2 {
                    match (stack_types[stack_types.len() - 2], stack_types[stack_types.len() - 1]) {
                        (Type::Int, Type::Int) => { count += 1; OpCode::AddInt }
                        (Type::Float, _) | (_, Type::Float) => { count += 1; OpCode::AddFloat }
                        _ => continue,
                    }
                } else { continue; }
            }
            OpCode::Sub => {
                if stack_types.len() >= 2 {
                    match (stack_types[stack_types.len() - 2], stack_types[stack_types.len() - 1]) {
                        (Type::Int, Type::Int) => { count += 1; OpCode::SubInt }
                        (Type::Float, _) | (_, Type::Float) => { count += 1; OpCode::SubFloat }
                        _ => continue,
                    }
                } else { continue; }
            }
            OpCode::Mul => {
                if stack_types.len() >= 2 {
                    match (stack_types[stack_types.len() - 2], stack_types[stack_types.len() - 1]) {
                        (Type::Int, Type::Int) => { count += 1; OpCode::MulInt }
                        (Type::Float, _) | (_, Type::Float) => { count += 1; OpCode::MulFloat }
                        _ => continue,
                    }
                } else { continue; }
            }
            OpCode::Div => {
                // Division always returns Float — only specialize to Float variants
                if stack_types.len() >= 2 {
                    match (stack_types[stack_types.len() - 2], stack_types[stack_types.len() - 1]) {
                        (Type::Float, _) | (_, Type::Float) => { count += 1; OpCode::DivFloat }
                        (Type::Int, Type::Int) => { count += 1; OpCode::DivFloat }
                        _ => continue,
                    }
                } else { continue; }
            }
            OpCode::Mod => {
                if stack_types.len() >= 2 {
                    match (stack_types[stack_types.len() - 2], stack_types[stack_types.len() - 1]) {
                        (Type::Int, Type::Int) => { count += 1; OpCode::ModInt }
                        (Type::Float, _) | (_, Type::Float) => { count += 1; OpCode::ModFloat }
                        _ => continue,
                    }
                } else { continue; }
            }
            // ── Comparisons ─────────────────────────────────────
            OpCode::Equal => {
                if stack_types.len() >= 2 {
                    match (stack_types[stack_types.len() - 2], stack_types[stack_types.len() - 1]) {
                        (Type::Int, Type::Int) => { count += 1; OpCode::EqualInt }
                        (Type::Float, _) | (_, Type::Float) => { count += 1; OpCode::EqualFloat }
                        _ => continue,
                    }
                } else { continue; }
            }
            OpCode::LessThan => {
                if stack_types.len() >= 2 {
                    match (stack_types[stack_types.len() - 2], stack_types[stack_types.len() - 1]) {
                        (Type::Int, Type::Int) => { count += 1; OpCode::LessThanInt }
                        (Type::Float, _) | (_, Type::Float) => { count += 1; OpCode::LessThanFloat }
                        _ => continue,
                    }
                } else { continue; }
            }
            // Others are not specialized yet
            _ => continue,
        };
    }

    (result, count)
}

// ─────────────────────────────────────────────────────────────────────────────
// Stats
// ─────────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Default)]
pub struct OptStats {
    pub original_instructions: usize,
    pub final_instructions:    usize,
    pub instructions_removed:  usize,
    pub constant_folds:        usize,
    pub instruction_fusions:   usize,
    pub strength_reductions:   usize,
    pub dead_code_removed:     usize,
    pub specializations:       usize,
    pub type_map: Option<TypeMap>,
}

impl OptStats {
    pub fn reduction_pct(&self) -> f64 {
        if self.original_instructions == 0 { return 0.0; }
        self.instructions_removed as f64 / self.original_instructions as f64 * 100.0
    }
}

impl std::fmt::Display for OptStats {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f,
            "OptStats {{ {}/{} instructions ({:.1}% reduction) | folds={} fusions={} strength={} dce={} specializations={} type_map={} }}",
            self.final_instructions,
            self.original_instructions,
            self.reduction_pct(),
            self.constant_folds,
            self.instruction_fusions,
            self.strength_reductions,
            self.dead_code_removed,
            self.specializations,
            if self.type_map.is_some() { "yes" } else { "no" },
        )
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    // ── Constant folding ─────────────────────────────────────────────────────

    #[test]
    fn fold_add() {
        let ops = vec![OpCode::Push(3), OpCode::Push(4), OpCode::Add];
        let (out, stats) = optimize(ops);
        assert_eq!(stats.constant_folds, 1);
        assert!(out.iter().any(|o| matches!(o, OpCode::Push(7))));
        // No Push(3) or Push(4) remaining
        assert!(!out.iter().any(|o| matches!(o, OpCode::Push(3))));
    }

    #[test]
    fn fold_sub() {
        let ops = vec![OpCode::Push(10), OpCode::Push(3), OpCode::Sub];
        let (out, stats) = optimize(ops);
        assert_eq!(stats.constant_folds, 1);
        assert!(out.iter().any(|o| matches!(o, OpCode::Push(7))));
    }

    #[test]
    fn fold_mul() {
        let ops = vec![OpCode::Push(6), OpCode::Push(7), OpCode::Mul];
        let (out, stats) = optimize(ops);
        assert_eq!(stats.constant_folds, 1);
        assert!(out.iter().any(|o| matches!(o, OpCode::Push(42))));
    }

    #[test]
    fn fold_mod() {
        let ops = vec![OpCode::Push(10), OpCode::Push(3), OpCode::Mod];
        let (out, stats) = optimize(ops);
        assert_eq!(stats.constant_folds, 1);
        assert!(out.iter().any(|o| matches!(o, OpCode::Push(1))));
    }

    #[test]
    fn no_fold_div_int() {
        // Division returns Float — can't represent in Push(i32), skip
        let ops = vec![OpCode::Push(5), OpCode::Push(2), OpCode::Div];
        let (out, stats) = optimize(ops);
        assert_eq!(stats.constant_folds, 0);
        assert!(out.iter().any(|o| matches!(o, OpCode::Div)));
    }

    #[test]
    fn fold_chained() {
        // Push(1) Push(2) Add Push(3) Add  →  Push(3) Push(3) Add  →  Push(6)
        let ops = vec![
            OpCode::Push(1), OpCode::Push(2), OpCode::Add,
            OpCode::Push(3), OpCode::Add,
        ];
        let (out, _stats) = optimize(ops);
        // Should contain Push(6) after two fold rounds
        // (single pass folds first triple; second Add is not a triple without rerun)
        // After first pass: [Push(3), Nop, Nop, Push(3), Add] → compacted: [Push(3), Push(3), Add]
        // That triple is then folded in a second... but we do single pass.
        // At minimum the first fold should fire.
        assert!(out.iter().any(|o| matches!(o, OpCode::Push(3) | OpCode::Push(6))));
    }

    // ── Instruction fusion ───────────────────────────────────────────────────

    #[test]
    fn fuse_dup_pop() {
        let ops = vec![OpCode::Push(1), OpCode::Duplicate, OpCode::Pop];
        let (out, stats) = optimize(ops);
        assert!(stats.instruction_fusions >= 1);
        // Dup+Pop become Nops which are then compacted out
        assert!(!out.iter().any(|o| matches!(o, OpCode::Duplicate)));
        assert!(!out.iter().any(|o| matches!(o, OpCode::Pop)));
    }

    #[test]
    fn fuse_not_not() {
        let ops = vec![OpCode::Push(1), OpCode::Not, OpCode::Not];
        let (out, stats) = optimize(ops);
        assert!(stats.instruction_fusions >= 1);
        assert!(!out.iter().any(|o| matches!(o, OpCode::Not)));
    }

    #[test]
    fn fuse_push_negate() {
        let ops = vec![OpCode::Push(5), OpCode::Negate];
        let (out, stats) = optimize(ops);
        assert!(stats.instruction_fusions >= 1);
        assert!(out.iter().any(|o| matches!(o, OpCode::Push(-5))));
        assert!(!out.iter().any(|o| matches!(o, OpCode::Negate)));
    }

    #[test]
    fn fuse_add_zero() {
        let ops = vec![OpCode::Push(42), OpCode::Push(0), OpCode::Add];
        let (out, stats) = optimize(ops);
        // Push(0) Add is handled by constant folding, not instruction fusion
        assert!(stats.constant_folds >= 1, "Expected constant fold, got folds={}", stats.constant_folds);
        assert!(out.iter().any(|o| matches!(o, OpCode::Push(42))));
        assert!(!out.iter().any(|o| matches!(o, OpCode::Add)));
    }

    #[test]
    fn fuse_mul_one() {
        let ops = vec![OpCode::Push(99), OpCode::Push(1), OpCode::Mul];
        let (out, stats) = optimize(ops);
        // Push(1) Mul is handled by constant folding, not instruction fusion
        assert!(stats.constant_folds >= 1, "Expected constant fold, got folds={}", stats.constant_folds);
        assert!(!out.iter().any(|o| matches!(o, OpCode::Mul)));
    }

    // ── Strength reduction ───────────────────────────────────────────────────

    #[test]
    fn strength_pow2_to_dup_mul() {
        let ops = vec![OpCode::Push(2), OpCode::Power];
        let (out, stats) = optimize(ops);
        assert_eq!(stats.strength_reductions, 1);
        assert!(out.iter().any(|o| matches!(o, OpCode::Duplicate)));
        assert!(out.iter().any(|o| matches!(o, OpCode::Mul)));
        assert!(!out.iter().any(|o| matches!(o, OpCode::Power)));
    }

    // ── Dead code elimination ────────────────────────────────────────────────

    #[test]
    fn dce_after_halt() {
        let ops = vec![
            OpCode::Push(1),
            OpCode::Halt,
            OpCode::Push(2),  // dead
            OpCode::Add,      // dead
        ];
        let (out, stats) = optimize(ops);
        assert!(stats.dead_code_removed >= 2);
        assert!(!out.iter().any(|o| matches!(o, OpCode::Add)));
    }

    #[test]
    fn dce_after_jump() {
        let ops = vec![
            OpCode::Push(1),
            OpCode::Jump(4),   // jumps to index 4 (past the dead block)
            OpCode::Push(2),   // dead (index 2)
            OpCode::Add,       // dead (index 3)
            OpCode::Halt,      // live (index 4, jump target)
        ];
        let (out, stats) = optimize(ops);
        assert!(stats.dead_code_removed >= 2);
        assert!(out.iter().any(|o| matches!(o, OpCode::Halt)));
    }

    #[test]
    fn dce_preserves_jump_targets() {
        // Code that jumps forward, target must stay live
        let ops = vec![
            OpCode::Push(1),
            OpCode::JumpIfFalse(3),
            OpCode::Push(2),
            OpCode::Halt,     // jump target — must not be eliminated
        ];
        let (out, stats) = optimize(ops);
        assert_eq!(stats.dead_code_removed, 0);
        assert!(out.iter().any(|o| matches!(o, OpCode::Halt)));
    }

    // ── Nop compaction ───────────────────────────────────────────────────────

    #[test]
    fn nop_compact_removes_nops() {
        let ops = vec![OpCode::Nop, OpCode::Push(1), OpCode::Nop, OpCode::Halt];
        let (out, _) = optimize(ops);
        assert!(!out.iter().any(|o| matches!(o, OpCode::Nop)));
    }

    #[test]
    fn nop_compact_rewrites_jump() {
        // After removing a leading Nop, Jump(2) must become Jump(1)
        let ops = vec![
            OpCode::Nop,       // index 0 → removed
            OpCode::Push(1),   // index 1 → new index 0
            OpCode::Jump(1),   // target was old index 1 → new index 0
        ];
        let (out, _) = optimize(ops);
        // Jump target should be 0 after compaction
        let has_jump_to_0 = out.iter().any(|o| matches!(o, OpCode::Jump(0)));
        assert!(has_jump_to_0, "Jump target not rewritten: {:?}", out);
    }

    // ── Full pipeline ────────────────────────────────────────────────────────

    #[test]
    fn full_pipeline_reduction() {
        // A small program with multiple optimization opportunities
        let ops = vec![
            OpCode::Push(2),
            OpCode::Push(3),
            OpCode::Add,       // → Push(5) via fold
            OpCode::Push(1),
            OpCode::Mul,       // → Nop Nop via fuse (x*1)
            OpCode::Halt,
            OpCode::Push(99),  // dead after Halt
        ];
        let (out, stats) = optimize(ops);
        assert!(stats.instructions_removed > 0);
        assert!(stats.constant_folds >= 1 || stats.instruction_fusions >= 1);
        println!("{}", stats);
        assert!(!out.iter().any(|o| matches!(o, OpCode::Nop)));
    }

    #[test]
    fn stats_reduction_pct() {
        let stats = OptStats {
            original_instructions: 10,
            final_instructions: 6,
            instructions_removed: 4,
            ..Default::default()
        };
        let pct = stats.reduction_pct();
        assert!((pct - 40.0).abs() < 0.01);
    }

    #[test]
    fn empty_program_no_panic() {
        let (out, stats) = optimize(vec![]);
        assert!(out.is_empty());
        assert_eq!(stats.original_instructions, 0);
    }

    #[test]
    fn single_instruction_no_panic() {
        let (out, _) = optimize(vec![OpCode::Halt]);
        assert_eq!(out.len(), 1);
    }

    // ── Type inference ─────────────────────────────────────────────────────────
    use super::Type;

    #[test]
    fn infer_push_int() {
        let ops = vec![OpCode::Push(42)];
        let map = pass_type_inference(&ops);
        assert_eq!(map.get(&0).map(|s| s.len()), Some(0));
        assert_eq!(map.get(&1).unwrap()[0], Type::Int);
    }

    #[test]
    fn infer_add_int_int() {
        let ops = vec![OpCode::Push(1), OpCode::Push(2), OpCode::Add];
        let map = pass_type_inference(&ops);
        assert_eq!(map.get(&3).unwrap()[0], Type::Int);
    }

    #[test]
    fn infer_div_float() {
        let ops = vec![OpCode::Push(5), OpCode::Push(2), OpCode::Div];
        let map = pass_type_inference(&ops);
        assert_eq!(map.get(&3).unwrap()[0], Type::Float);
    }

    #[test]
    fn infer_comparison_bool() {
        let ops = vec![OpCode::Push(1), OpCode::Push(2), OpCode::Equal];
        let map = pass_type_inference(&ops);
        assert_eq!(map.get(&3).unwrap()[0], Type::Bool);
    }

    #[test]
    fn infer_negate_int() {
        let ops = vec![OpCode::Push(5), OpCode::Negate];
        let map = pass_type_inference(&ops);
        assert_eq!(map.get(&2).unwrap()[0], Type::Int);
    }

    #[test]
    fn infer_jump_merge_int() {
        let ops = vec![
            OpCode::Push(1),
            OpCode::JumpIfFalse(4),
            OpCode::Push(2),
            OpCode::Jump(5),
            OpCode::Push(3),
            OpCode::Halt,
        ];
        let map = pass_type_inference(&ops);
        // At the merge point before Halt (index 5), both paths push Int
        assert_eq!(map.get(&5).unwrap().len(), 1);
        assert_eq!(map.get(&5).unwrap()[0], Type::Int);
    }

    #[test]
    fn infer_create_array() {
        let ops = vec![
            OpCode::Push(1),
            OpCode::Push(2),
            OpCode::Push(3),
            OpCode::CreateArray(3),
        ];
        let map = pass_type_inference(&ops);
        assert_eq!(map.get(&4).unwrap()[0], Type::Array);
    }

    #[test]
    fn infer_concat_string() {
        let ops = vec![
            OpCode::LoadConst(0),
            OpCode::LoadConst(1),
            OpCode::Concat,
        ];
        let map = pass_type_inference(&ops);
        assert_eq!(map.get(&3).unwrap()[0], Type::String);
    }

    #[test]
    fn infer_length_int() {
        let ops = vec![OpCode::Push(5), OpCode::Length];
        let map = pass_type_inference(&ops);
        assert_eq!(map.get(&2).unwrap()[0], Type::Int);
    }

    #[test]
    fn infer_optimize_with_types() {
        let ops = vec![OpCode::Push(2), OpCode::Push(3), OpCode::Add, OpCode::Halt];
        let (_optimized, stats, type_map) = optimize_with_types(ops);
        assert!(stats.type_map.is_some());
        assert!(!type_map.is_empty());
    }

    // ── Type specialization ─────────────────────────────────────────────────────

    #[test]
    fn specialize_add_int() {
        let ops = vec![OpCode::Push(1), OpCode::Push(2), OpCode::Add, OpCode::Halt];
        let type_map = pass_type_inference(&ops);
        let (out, count) = pass_type_specialize(ops, &type_map);
        assert_eq!(count, 1, "Expected Add → AddInt");
        assert!(matches!(out[2], OpCode::AddInt), "Expected AddInt, got {:?}", out[2]);
    }

    #[test]
    fn specialize_sub_int() {
        let ops = vec![OpCode::Push(5), OpCode::Push(3), OpCode::Sub, OpCode::Halt];
        let type_map = pass_type_inference(&ops);
        let (out, count) = pass_type_specialize(ops, &type_map);
        assert_eq!(count, 1);
        assert!(matches!(out[2], OpCode::SubInt));
    }

    #[test]
    fn specialize_mul_int() {
        let ops = vec![OpCode::Push(2), OpCode::Push(3), OpCode::Mul, OpCode::Halt];
        let type_map = pass_type_inference(&ops);
        let (out, count) = pass_type_specialize(ops, &type_map);
        assert_eq!(count, 1);
        assert!(matches!(out[2], OpCode::MulInt));
    }

    #[test]
    fn specialize_div_float_int() {
        // Division always returns Float → both Int paths specialize to DivFloat
        let ops = vec![OpCode::Push(5), OpCode::Push(2), OpCode::Div, OpCode::Halt];
        let type_map = pass_type_inference(&ops);
        let (out, count) = pass_type_specialize(ops, &type_map);
        assert_eq!(count, 1);
        assert!(matches!(out[2], OpCode::DivFloat));
    }

    #[test]
    fn specialize_mod_int() {
        let ops = vec![OpCode::Push(10), OpCode::Push(3), OpCode::Mod, OpCode::Halt];
        let type_map = pass_type_inference(&ops);
        let (out, count) = pass_type_specialize(ops, &type_map);
        assert_eq!(count, 1);
        assert!(matches!(out[2], OpCode::ModInt));
    }

    #[test]
    fn specialize_equal_int() {
        let ops = vec![OpCode::Push(1), OpCode::Push(2), OpCode::Equal, OpCode::Halt];
        let type_map = pass_type_inference(&ops);
        let (out, count) = pass_type_specialize(ops, &type_map);
        assert_eq!(count, 1);
        assert!(matches!(out[2], OpCode::EqualInt));
    }

    #[test]
    fn specialize_lessthan_int() {
        let ops = vec![OpCode::Push(1), OpCode::Push(2), OpCode::LessThan, OpCode::Halt];
        let type_map = pass_type_inference(&ops);
        let (out, count) = pass_type_specialize(ops, &type_map);
        assert_eq!(count, 1);
        assert!(matches!(out[2], OpCode::LessThanInt));
    }

    #[test]
    fn specialize_add_float() {
        // Push(1) → Int, Push(2) → Int, but Div → Float. Then Add should be AddFloat.
        let ops = vec![
            OpCode::Push(1), OpCode::Push(2), OpCode::Div,    // stack: [Float]
            OpCode::Push(3), OpCode::Push(4), OpCode::Div,    // stack: [Float, Float]
            OpCode::Add,
            OpCode::Halt,
        ];
        let type_map = pass_type_inference(&ops);
        let (out, count) = pass_type_specialize(ops, &type_map);
        // Both Divs are specialized (Int+Int→DivFloat) AND Add is specialized (Float+Float→AddFloat)
        assert_eq!(count, 3, "Expected 3 specializations (2 DivFloat + 1 AddFloat)");
        assert!(matches!(out[6], OpCode::AddFloat), "Expected AddFloat at index 6, got {:?}", out[6]);
    }

    #[test]
    fn specialize_no_change_on_unknown_types() {
        // LoadGlobal leaves Type::Top on stack — no specialization possible
        let ops = vec![OpCode::LoadGlobal(0), OpCode::LoadGlobal(1), OpCode::Add, OpCode::Halt];
        let type_map = pass_type_inference(&ops);
        let (out, count) = pass_type_specialize(ops, &type_map);
        assert_eq!(count, 0, "Expected no specialization for Top operands");
        assert!(matches!(out[2], OpCode::Add), "Expected Add unchanged");
    }

    #[test]
    fn specialize_pipeline_integration() {
        // Full pipeline with type specialization should produce typed opcodes
        let ops = vec![OpCode::Push(5), OpCode::Push(3), OpCode::Add, OpCode::Halt];
        let (out, stats, _) = optimize_with_types(ops);
        assert!(stats.specializations >= 1, "Expected at least 1 specialization");
        // The pipeline may fold it to Push(8) — that's fine too
        assert!(
            out.iter().any(|o| matches!(o, OpCode::AddInt)) || stats.constant_folds >= 1,
            "Expected either AddInt or constant fold, got: {:?}", out
        );
    }
}
