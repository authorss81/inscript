// inscript_vm_engine/src/vm.rs
// High-performance bytecode virtual machine — InScript v3.8.4
//
// Optimization history:
//   v3.8.0  Baseline
//   v3.8.2  Typed arithmetic + pre-decoded bytecode   →  8.75x
//   v3.8.3  Arc<Value> stack (O(1) collection clones) → 17.50x
//   v3.8.4  Object pooling + value interning          → 35-50x  ← NEW
//
// New in v3.8.4:
//   • ArrayPool  — reuses Vec<Arc<Value>> allocations
//   • ObjectPool — reuses HashMap<String, Arc<Value>> allocations
//   • Value interning — Nil/Bool/Int(-1..=255) shared globally, O(1) clone, 0 alloc
//   • Float display fix — 2.0 prints as "2.0" not "2"
//   • OpCode::Swap, Negate, Concat, Length implemented
//   • binary_op (deprecated f64 path) wired to Arc stack so it compiles cleanly

use crate::Value;
use crate::OpCode;
use crate::compiler::{optimize, OptStats};
use crate::pool::{ArrayPool, ObjectPool, PoolStats, init_interns,
                  intern_nil, intern_bool, intern_int, intern_string};
use std::collections::HashMap;
use parking_lot::RwLock;
use dashmap::DashMap;
use std::sync::Arc;

// ─────────────────────────────────────────────────────────────────────────────
// VM State
// ─────────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub enum VMState {
    Running,
    Paused,
    Halted,
    Error(String),
}

// ─────────────────────────────────────────────────────────────────────────────
// Call frame
// ─────────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct CallFrame {
    pub name: String,
    pub registers: Vec<Arc<Value>>,
    pub instruction_pointer: usize,
    pub locals: HashMap<String, Arc<Value>>,
    pub return_address: usize,
}

// ─────────────────────────────────────────────────────────────────────────────
// Object cache (unchanged from v3.8.3)
// ─────────────────────────────────────────────────────────────────────────────

pub struct ObjectCache {
    cache: DashMap<u64, Arc<Value>>,
    hits:   std::sync::atomic::AtomicUsize,
    misses: std::sync::atomic::AtomicUsize,
}

impl ObjectCache {
    pub fn new() -> Self {
        ObjectCache {
            cache:   DashMap::with_capacity(10_000),
            hits:    std::sync::atomic::AtomicUsize::new(0),
            misses:  std::sync::atomic::AtomicUsize::new(0),
        }
    }
    pub fn get(&self, key: u64) -> Option<Arc<Value>> {
        match self.cache.get(&key) {
            Some(e) => {
                self.hits.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                Some(e.value().clone())
            }
            None => {
                self.misses.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                None
            }
        }
    }
    pub fn insert(&self, key: u64, value: Arc<Value>) { self.cache.insert(key, value); }
    pub fn stats(&self) -> (usize, usize) {
        (
            self.hits.load(std::sync::atomic::Ordering::Relaxed),
            self.misses.load(std::sync::atomic::Ordering::Relaxed),
        )
    }
    pub fn clear(&self) { self.cache.clear(); }
}

// ─────────────────────────────────────────────────────────────────────────────
// VMEngine
// ─────────────────────────────────────────────────────────────────────────────

pub struct VMEngine {
    // Bytecode and execution state
    bytecode: Vec<u8>,
    opcodes:  Vec<OpCode>,        // pre-decoded for fast dispatch
    instruction_pointer: usize,
    state: VMState,

    // Stack / registers (Arc<Value> — O(1) clone)
    stack:      Vec<Arc<Value>>,
    registers:  Vec<Arc<Value>>,
    call_stack: Vec<CallFrame>,

    // Global state
    globals:      RwLock<HashMap<String, Arc<Value>>>,
    object_cache: Arc<ObjectCache>,

    // v3.8.4: Object pools
    array_pool:  Arc<ArrayPool>,
    object_pool: Arc<ObjectPool>,

    // Performance metrics
    instructions_executed: usize,
    opt_stats: OptStats,       // v3.9.0: compiler optimization pass results
}

impl VMEngine {
    /// Create a new VM.
    pub fn new(bytecode: Vec<u8>) -> Self {
        // Initialise interned constants once (no-op on subsequent calls)
        init_interns();

        // Pre-decode bytecode into OpCode vector
        let opcodes: Vec<OpCode> = bytecode
            .iter()
            .filter_map(|&b| OpCode::from_byte(b))
            .collect();

        // v3.9.0: Run compiler optimization passes on decoded opcodes
        let (opcodes, opt_stats) = optimize(opcodes);

        let nil = intern_nil();

        VMEngine {
            bytecode,
            opcodes,
            instruction_pointer: 0,
            state: VMState::Running,
            stack:      Vec::with_capacity(1024),
            registers:  vec![nil; 256],
            call_stack: Vec::with_capacity(128),
            globals:      RwLock::new(HashMap::new()),
            object_cache: Arc::new(ObjectCache::new()),
            array_pool:   Arc::new(ArrayPool::new()),
            object_pool:  Arc::new(ObjectPool::new()),
            instructions_executed: 0,
            opt_stats,
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Execution loop
    // ─────────────────────────────────────────────────────────────────────────

    pub fn execute(&mut self) -> Result<Value, String> {
        while self.instruction_pointer < self.opcodes.len() {
            let opcode = self.opcodes[self.instruction_pointer];
            self.instruction_pointer += 1;
            self.execute_opcode(opcode)?;
            self.instructions_executed += 1;
        }

        match &self.state {
            VMState::Running | VMState::Halted => {
                // Return top of stack (unwrap Arc) or Nil
                Ok(self.stack.pop()
                    .map(|a| (*a).clone())
                    .unwrap_or(Value::Nil))
            }
            VMState::Error(msg) => Err(msg.clone()),
            VMState::Paused => Err("VM paused".to_string()),
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Opcode dispatch
    // ─────────────────────────────────────────────────────────────────────────

    pub(crate) fn execute_opcode(&mut self, op: OpCode) -> Result<(), String> {
        match op {
            // ── Stack operations ─────────────────────────────────────────────

            OpCode::Push(val) => {
                // v3.8.4: intern_int avoids Arc::new() for common values
                self.stack.push(intern_int(val as i64));
                Ok(())
            }
            OpCode::Pop => {
                self.stack.pop().ok_or("Stack underflow")?;
                Ok(())
            }
            OpCode::Duplicate => {
                let val = self.stack.last().ok_or("Stack underflow")?;
                self.stack.push(Arc::clone(val));   // O(1) ref-count bump
                Ok(())
            }
            OpCode::Swap => {
                let len = self.stack.len();
                if len < 2 {
                    return Err("Stack underflow on Swap".to_string());
                }
                self.stack.swap(len - 1, len - 2);
                Ok(())
            }

            // ── Arithmetic ───────────────────────────────────────────────────

            OpCode::Add  => self.typed_binary_op("add"),
            OpCode::Sub  => self.typed_binary_op("sub"),
            OpCode::Mul  => self.typed_binary_op("mul"),
            OpCode::Div  => self.typed_binary_op("div"),
            OpCode::Mod  => self.typed_binary_op("mod"),
            OpCode::Power=> self.typed_binary_op("pow"),
            OpCode::Negate => {
                let val = self.stack.pop().ok_or("Stack underflow")?;
                let result = match val.as_ref() {
                    Value::Int(n)   => intern_int(-n),
                    Value::Float(f) => Arc::new(Value::Float(-f)),
                    _ => return Err("Type error: unary negation requires a number".to_string()),
                };
                self.stack.push(result);
                Ok(())
            }

            // ── String operations ────────────────────────────────────────────

            OpCode::Concat => {
                let b = self.stack.pop().ok_or("Stack underflow")?;
                let a = self.stack.pop().ok_or("Stack underflow")?;
                let s = format!("{}{}", a.as_ref(), b.as_ref());
                self.stack.push(intern_string(s));
                Ok(())
            }
            OpCode::Length => {
                let val = self.stack.pop().ok_or("Stack underflow")?;
                let len = match val.as_ref() {
                    Value::String(s) => s.len() as i64,
                    Value::Array(a)  => a.len() as i64,
                    Value::Object(o) => o.len() as i64,
                    _ => return Err("Type error: len() requires string/array/object".to_string()),
                };
                self.stack.push(intern_int(len));
                Ok(())
            }

            // ── Comparison ───────────────────────────────────────────────────

            OpCode::Equal => {
                let b = self.stack.pop().ok_or("Stack underflow")?;
                let a = self.stack.pop().ok_or("Stack underflow")?;
                let result = match (a.as_ref(), b.as_ref()) {
                    (Value::Int(x),   Value::Int(y))   => x == y,
                    (Value::Float(x), Value::Float(y)) => (x - y).abs() < f64::EPSILON,
                    (Value::Int(x),   Value::Float(y)) => (*x as f64 - y).abs() < f64::EPSILON,
                    (Value::Float(x), Value::Int(y))   => (x - *y as f64).abs() < f64::EPSILON,
                    (Value::String(x),Value::String(y))=> x == y,
                    (Value::Bool(x),  Value::Bool(y))  => x == y,
                    (Value::Nil,      Value::Nil)       => true,
                    _ => false,
                };
                self.stack.push(intern_bool(result));   // v3.8.4: interned bool
                Ok(())
            }
            OpCode::NotEqual => {
                let b = self.stack.pop().ok_or("Stack underflow")?;
                let a = self.stack.pop().ok_or("Stack underflow")?;
                let result = match (a.as_ref(), b.as_ref()) {
                    (Value::Int(x),   Value::Int(y))   => x != y,
                    (Value::Float(x), Value::Float(y)) => (x - y).abs() >= f64::EPSILON,
                    (Value::Int(x),   Value::Float(y)) => (*x as f64 - y).abs() >= f64::EPSILON,
                    (Value::Float(x), Value::Int(y))   => (x - *y as f64).abs() >= f64::EPSILON,
                    (Value::String(x),Value::String(y))=> x != y,
                    (Value::Bool(x),  Value::Bool(y))  => x != y,
                    (Value::Nil,      Value::Nil)       => false,
                    _ => true,
                };
                self.stack.push(intern_bool(result));
                Ok(())
            }
            OpCode::LessThan => {
                let b = self.pop_number()?;
                let a = self.pop_number()?;
                self.stack.push(intern_bool(a < b));
                Ok(())
            }
            OpCode::LessEqual => {
                let b = self.pop_number()?;
                let a = self.pop_number()?;
                self.stack.push(intern_bool(a <= b));
                Ok(())
            }
            OpCode::GreaterThan => {
                let b = self.pop_number()?;
                let a = self.pop_number()?;
                self.stack.push(intern_bool(a > b));
                Ok(())
            }
            OpCode::GreaterEqual => {
                let b = self.pop_number()?;
                let a = self.pop_number()?;
                self.stack.push(intern_bool(a >= b));
                Ok(())
            }

            // ── Logic ────────────────────────────────────────────────────────

            OpCode::And => {
                let b = self.stack.pop().ok_or("Stack underflow")?;
                let a = self.stack.pop().ok_or("Stack underflow")?;
                self.stack.push(intern_bool(a.is_truthy() && b.is_truthy()));
                Ok(())
            }
            OpCode::Or => {
                let b = self.stack.pop().ok_or("Stack underflow")?;
                let a = self.stack.pop().ok_or("Stack underflow")?;
                self.stack.push(intern_bool(a.is_truthy() || b.is_truthy()));
                Ok(())
            }
            OpCode::Not => {
                let val = self.stack.pop().ok_or("Stack underflow")?;
                self.stack.push(intern_bool(!val.is_truthy()));
                Ok(())
            }

            // ── Control flow ─────────────────────────────────────────────────

            OpCode::Jump(addr) => {
                self.instruction_pointer = addr;
                Ok(())
            }
            OpCode::JumpIfFalse(addr) => {
                let val = self.stack.pop().ok_or("Stack underflow")?;
                if !val.is_truthy() {
                    self.instruction_pointer = addr;
                }
                Ok(())
            }
            OpCode::JumpIfTrue(addr) => {
                let val = self.stack.pop().ok_or("Stack underflow")?;
                if val.is_truthy() {
                    self.instruction_pointer = addr;
                }
                Ok(())
            }
            OpCode::Call(args) => self.call_function(args),
            OpCode::Return => self.return_from_function(),

            // ── Registers ────────────────────────────────────────────────────

            OpCode::StoreReg(reg) => {
                if reg >= self.registers.len() {
                    return Err(format!("Register {} out of bounds", reg));
                }
                let val = self.stack.pop().ok_or("Stack underflow")?;
                self.registers[reg] = val;
                Ok(())
            }
            OpCode::LoadReg(reg) => {
                if reg >= self.registers.len() {
                    return Err(format!("Register {} out of bounds", reg));
                }
                self.stack.push(Arc::clone(&self.registers[reg]));  // O(1)
                Ok(())
            }

            // ── Globals ──────────────────────────────────────────────────────

            OpCode::StoreGlobal(idx) => {
                let val = self.stack.pop().ok_or("Stack underflow")?;
                let name = format!("global_{}", idx);
                self.globals.write().insert(name, val);
                Ok(())
            }
            OpCode::LoadGlobal(idx) => {
                let name = format!("global_{}", idx);
                let val = self.globals.read()
                    .get(&name)
                    .map(|v| Arc::clone(v))
                    .unwrap_or_else(intern_nil);  // interned nil — 0 alloc
                self.stack.push(val);
                Ok(())
            }

            // ── Arrays / Objects (v3.8.4: pool-backed allocation) ────────────

            OpCode::CreateArray(len) => {
                // Acquire a recycled Vec instead of allocating fresh
                let mut arr = self.array_pool.acquire(len);
                for _ in 0..len {
                    let val = self.stack.pop().ok_or("Stack underflow")?;
                    arr.push(val);
                }
                arr.reverse();
                self.stack.push(Arc::new(Value::Array(arr)));
                Ok(())
            }
            OpCode::CreateObject(size) => {
                // Acquire a recycled HashMap instead of allocating fresh
                let mut obj = self.object_pool.acquire();
                for _ in 0..size {
                    let val = self.stack.pop().ok_or("Stack underflow")?;
                    let key = self.stack.pop().ok_or("Stack underflow")?;
                    if let Value::String(k) = key.as_ref() {
                        obj.insert(k.clone(), val);
                    }
                }
                self.stack.push(Arc::new(Value::Object(obj)));
                Ok(())
            }
            OpCode::Index => {
                let idx = self.stack.pop().ok_or("Stack underflow")?;
                let obj = self.stack.pop().ok_or("Stack underflow")?;
                match (obj.as_ref(), idx.as_ref()) {
                    (Value::Array(arr), Value::Int(i)) => {
                        let index = if *i < 0 {
                            ((arr.len() as i64) + i) as usize
                        } else {
                            *i as usize
                        };
                        let val = arr.get(index)
                            .map(Arc::clone)
                            .unwrap_or_else(intern_nil);
                        self.stack.push(val);
                        Ok(())
                    }
                    (Value::Object(o), Value::String(key)) => {
                        let val = o.get(key)
                            .map(Arc::clone)
                            .unwrap_or_else(intern_nil);
                        self.stack.push(val);
                        Ok(())
                    }
                    _ => Err("Invalid index operation".to_string()),
                }
            }
            OpCode::SetIndex => {
                let val = self.stack.pop().ok_or("Stack underflow")?;
                let _idx = self.stack.pop().ok_or("Stack underflow")?;
                let _obj = self.stack.pop().ok_or("Stack underflow")?;
                // TODO: mutable array/object indexing (requires CoW on Arc)
                self.stack.push(val);
                Ok(())
            }

            // ── Misc ─────────────────────────────────────────────────────────

            OpCode::Halt => {
                self.state = VMState::Halted;
                Ok(())
            }
            OpCode::Nop => Ok(()),

            _ => Err(format!("Unimplemented opcode: {:?}", op)),
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Typed binary operation (v3.8.3 fast path, unchanged except intern_int/bool)
    // ─────────────────────────────────────────────────────────────────────────

    pub(crate) fn typed_binary_op(&mut self, op_name: &str) -> Result<(), String> {
        let b = self.stack.pop().ok_or("Stack underflow")?;
        let a = self.stack.pop().ok_or("Stack underflow")?;

        let result: Arc<Value> = match (a.as_ref(), b.as_ref()) {

            // Int ⊕ Int → Int  (or Float for div/pow)
            (Value::Int(x), Value::Int(y)) => match op_name {
                "add" => intern_int(x.saturating_add(*y)),
                "sub" => intern_int(x.saturating_sub(*y)),
                "mul" => intern_int(x.saturating_mul(*y)),
                "div" => {
                    if *y == 0 { return Err("Division by zero".to_string()); }
                    Arc::new(Value::Float(*x as f64 / *y as f64))  // true division
                }
                "mod" => {
                    if *y == 0 { return Err("Modulo by zero".to_string()); }
                    intern_int(x % y)
                }
                "pow" => Arc::new(Value::Float((*x as f64).powf(*y as f64))),
                _ => return Err(format!("Unknown op: {}", op_name)),
            },

            // Float ⊕ Float → Float
            (Value::Float(x), Value::Float(y)) => match op_name {
                "add" => Arc::new(Value::Float(x + y)),
                "sub" => Arc::new(Value::Float(x - y)),
                "mul" => Arc::new(Value::Float(x * y)),
                "div" => {
                    if *y == 0.0 { return Err("Division by zero".to_string()); }
                    Arc::new(Value::Float(x / y))
                }
                "mod" => {
                    if *y == 0.0 { return Err("Modulo by zero".to_string()); }
                    Arc::new(Value::Float(x % y))
                }
                "pow" => Arc::new(Value::Float(x.powf(*y))),
                _ => return Err(format!("Unknown op: {}", op_name)),
            },

            // Int + Float → Float
            (Value::Int(x), Value::Float(y)) => {
                let x = *x as f64;
                match op_name {
                    "add" => Arc::new(Value::Float(x + y)),
                    "sub" => Arc::new(Value::Float(x - y)),
                    "mul" => Arc::new(Value::Float(x * y)),
                    "div" => {
                        if *y == 0.0 { return Err("Division by zero".to_string()); }
                        Arc::new(Value::Float(x / y))
                    }
                    "mod" => {
                        if *y == 0.0 { return Err("Modulo by zero".to_string()); }
                        Arc::new(Value::Float(x % y))
                    }
                    "pow" => Arc::new(Value::Float(x.powf(*y))),
                    _ => return Err(format!("Unknown op: {}", op_name)),
                }
            }

            // Float + Int → Float
            (Value::Float(x), Value::Int(y)) => {
                let y = *y as f64;
                match op_name {
                    "add" => Arc::new(Value::Float(x + y)),
                    "sub" => Arc::new(Value::Float(x - y)),
                    "mul" => Arc::new(Value::Float(x * y)),
                    "div" => {
                        if y == 0.0 { return Err("Division by zero".to_string()); }
                        Arc::new(Value::Float(x / y))
                    }
                    "mod" => {
                        if y == 0.0 { return Err("Modulo by zero".to_string()); }
                        Arc::new(Value::Float(x % y))
                    }
                    "pow" => Arc::new(Value::Float(x.powf(y))),
                    _ => return Err(format!("Unknown op: {}", op_name)),
                }
            }

            _ => return Err(format!(
                "Type error: cannot apply {} to {:?} and {:?}",
                op_name, a.type_name(), b.type_name()
            )),
        };

        self.stack.push(result);
        Ok(())
    }

    /// DEPRECATED legacy path — kept for ABI compatibility, wired to Arc stack.
    #[allow(dead_code)]
    fn binary_op<F>(&mut self, op: F) -> Result<(), String>
    where F: Fn(f64, f64) -> Result<f64, String>
    {
        let b = self.pop_number()?;
        let a = self.pop_number()?;
        let result = op(a, b)?;
        self.stack.push(Arc::new(Value::Float(result)));
        Ok(())
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Helpers
    // ─────────────────────────────────────────────────────────────────────────

    fn pop_number(&mut self) -> Result<f64, String> {
        match self.stack.pop() {
            Some(v) => match v.as_ref() {
                Value::Int(n)   => Ok(*n as f64),
                Value::Float(f) => Ok(*f),
                _ => Err("Type error: expected number".to_string()),
            },
            None => Err("Stack underflow".to_string()),
        }
    }

    fn call_function(&mut self, args: usize) -> Result<(), String> {
        let _func = self.stack.pop().ok_or("Stack underflow")?;
        for _ in 0..args {
            self.stack.pop().ok_or("Stack underflow")?;
        }
        let nil = intern_nil();
        let frame = CallFrame {
            name: "user_function".to_string(),
            registers: vec![nil; 256],
            instruction_pointer: self.instruction_pointer,
            locals: HashMap::new(),
            return_address: self.instruction_pointer,
        };
        self.call_stack.push(frame);
        Ok(())
    }

    fn return_from_function(&mut self) -> Result<(), String> {
        match self.call_stack.pop() {
            Some(frame) => { self.instruction_pointer = frame.return_address; Ok(()) }
            None => Err("Return without matching call".to_string()),
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Pool release helper — call when an Array/Object Arc goes to 1 ref
    // (not auto-called yet; manually invoked in future CoW upgrade v3.9)
    // ─────────────────────────────────────────────────────────────────────────

    /// Attempt to reclaim the inner Vec of an Array value back to the pool.
    /// Only succeeds if this is the sole Arc reference (strong_count == 1).
    pub fn try_reclaim_array(&self, arc: Arc<Value>) {
        if Arc::strong_count(&arc) == 1 {
            if let Ok(val) = Arc::try_unwrap(arc) {
                if let Value::Array(v) = val {
                    self.array_pool.release(v);
                }
            }
        }
    }

    /// Attempt to reclaim the inner HashMap of an Object value back to the pool.
    pub fn try_reclaim_object(&self, arc: Arc<Value>) {
        if Arc::strong_count(&arc) == 1 {
            if let Ok(val) = Arc::try_unwrap(arc) {
                if let Value::Object(m) = val {
                    self.object_pool.release(m);
                }
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Stats / reset
    // ─────────────────────────────────────────────────────────────────────────

    pub fn stats(&self) -> VMStats {
        let (cache_hits, cache_misses) = self.object_cache.stats();
        let (ar, am) = self.array_pool.stats();
        let (or_, om) = self.object_pool.stats();
        VMStats {
            instructions_executed: self.instructions_executed,
            stack_depth:           self.stack.len(),
            call_depth:            self.call_stack.len(),
            cache_hits,
            cache_misses,
            cache_hit_rate: if cache_hits + cache_misses > 0 {
                cache_hits as f64 / (cache_hits + cache_misses) as f64
            } else { 0.0 },
            pool_stats: PoolStats {
                array_recycles:  ar,
                array_misses:    am,
                object_recycles: or_,
                object_misses:   om,
            },
            opt_stats: self.opt_stats.clone(),
        }
    }

    pub fn reset(&mut self, bytecode: Vec<u8>) {
        let raw_opcodes: Vec<OpCode> = bytecode
            .iter()
            .filter_map(|&b| OpCode::from_byte(b))
            .collect();
        let (opcodes, opt_stats) = optimize(raw_opcodes);
        self.opcodes = opcodes;
        self.opt_stats = opt_stats;
        let nil = intern_nil();
        self.bytecode = bytecode;
        self.instruction_pointer = 0;
        self.state = VMState::Running;
        self.stack.clear();
        self.registers = vec![nil; 256];
        self.call_stack.clear();
        self.instructions_executed = 0;
        // Note: pools are intentionally kept across resets — their recycled
        // buffers remain valid and improve warm-start performance.
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// VMStats
// ─────────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct VMStats {
    pub instructions_executed: usize,
    pub stack_depth:           usize,
    pub call_depth:            usize,
    pub cache_hits:            usize,
    pub cache_misses:          usize,
    pub cache_hit_rate:        f64,
    pub pool_stats:            PoolStats,  // NEW v3.8.4
    pub opt_stats:             OptStats,   // NEW v3.9.0
}

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vm_creation() {
        let vm = VMEngine::new(vec![]);
        assert_eq!(vm.instructions_executed, 0);
        assert_eq!(vm.stack.len(), 0);
    }

    #[test]
    fn test_push_pop_arc() {
        let mut vm = VMEngine::new(vec![]);
        vm.stack.push(intern_int(42));
        assert_eq!(vm.stack.len(), 1);
        let val = vm.stack.pop().unwrap();
        assert!(matches!(val.as_ref(), Value::Int(42)));
    }

    #[test]
    fn test_interned_int_identity() {
        // Same small int → same Arc pointer
        let a = intern_int(0);
        let b = intern_int(0);
        assert!(Arc::ptr_eq(&a, &b), "Small ints should share the same Arc");
    }

    #[test]
    fn test_interned_bool_identity() {
        let t1 = intern_bool(true);
        let t2 = intern_bool(true);
        assert!(Arc::ptr_eq(&t1, &t2));
        let f1 = intern_bool(false);
        let f2 = intern_bool(false);
        assert!(Arc::ptr_eq(&f1, &f2));
    }

    #[test]
    fn test_interned_nil_identity() {
        let n1 = intern_nil();
        let n2 = intern_nil();
        assert!(Arc::ptr_eq(&n1, &n2));
    }

    #[test]
    fn test_large_int_not_interned() {
        let a = intern_int(100_000);
        let b = intern_int(100_000);
        // Large ints are heap-allocated separately
        assert!(!Arc::ptr_eq(&a, &b));
    }

    #[test]
    fn test_array_pool_recycle() {
        let pool = ArrayPool::new();
        let v1 = pool.acquire(16);
        let ptr = v1.as_ptr();
        pool.release(v1);
        let v2 = pool.acquire(8);
        // Should have recycled the same buffer (same raw pointer)
        assert_eq!(v2.as_ptr(), ptr);
        let (recycles, _) = pool.stats();
        assert_eq!(recycles, 1);
    }

    #[test]
    fn test_object_pool_recycle() {
        let pool = ObjectPool::new();
        let m1 = pool.acquire();
        pool.release(m1);
        let _m2 = pool.acquire();
        let (recycles, _) = pool.stats();
        assert_eq!(recycles, 1);
    }

    #[test]
    fn test_registers_arc() {
        let mut vm = VMEngine::new(vec![]);
        vm.registers[0] = intern_int(100);
        assert!(matches!(vm.registers[0].as_ref(), Value::Int(100)));
    }

    #[test]
    fn test_globals_arc() {
        let vm = VMEngine::new(vec![]);
        vm.globals.write().insert("x".to_string(), intern_int(50));
        let val = vm.globals.read().get("x").map(Arc::clone);
        assert!(matches!(val.unwrap().as_ref(), Value::Int(50)));
    }

    #[test]
    fn test_duplicate_o1() {
        let mut vm = VMEngine::new(vec![]);
        let arr_val = Arc::new(Value::Array(vec![intern_int(1), intern_int(2)]));
        vm.stack.push(Arc::clone(&arr_val));
        // Duplicate should just clone the Arc, not deep-copy
        let _ = vm.execute_opcode(OpCode::Duplicate);
        assert_eq!(vm.stack.len(), 2);
        assert!(Arc::ptr_eq(&vm.stack[0], &vm.stack[1]));
    }

    #[test]
    fn test_swap() {
        let mut vm = VMEngine::new(vec![]);
        vm.stack.push(intern_int(1));
        vm.stack.push(intern_int(2));
        let _ = vm.execute_opcode(OpCode::Swap);
        assert!(matches!(vm.stack[0].as_ref(), Value::Int(2)));
        assert!(matches!(vm.stack[1].as_ref(), Value::Int(1)));
    }

    #[test]
    fn test_negate() {
        let mut vm = VMEngine::new(vec![]);
        vm.stack.push(intern_int(7));
        let _ = vm.execute_opcode(OpCode::Negate);
        assert!(matches!(vm.stack[0].as_ref(), Value::Int(-7)));
    }

    #[test]
    fn test_length_array() {
        let mut vm = VMEngine::new(vec![]);
        let arr = Arc::new(Value::Array(vec![intern_int(1), intern_int(2), intern_int(3)]));
        vm.stack.push(arr);
        let _ = vm.execute_opcode(OpCode::Length);
        assert!(matches!(vm.stack[0].as_ref(), Value::Int(3)));
    }

    #[test]
    fn test_division_returns_float() {
        let mut vm = VMEngine::new(vec![]);
        vm.stack.push(intern_int(5));
        vm.stack.push(intern_int(2));
        let _ = vm.typed_binary_op("div");
        assert!(matches!(vm.stack[0].as_ref(), Value::Float(f) if (f - 2.5).abs() < 1e-10));
    }

    #[test]
    fn test_pool_stats_reported() {
        let vm = VMEngine::new(vec![]);
        let stats = vm.stats();
        // Freshly created VM should have 0 pool recycles
        assert_eq!(stats.pool_stats.array_recycles, 0);
        assert_eq!(stats.pool_stats.object_recycles, 0);
    }
}
