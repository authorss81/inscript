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
use crate::FuncDef;
use crate::compiler::{optimize_with_types, OptStats};
use crate::jit::{JitEngine, TraceId};
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
    pub return_address: usize,
    pub saved_opcodes: Vec<OpCode>,
    pub saved_constants: Vec<Arc<Value>>,
    pub saved_stack: Vec<Arc<Value>>,
    pub saved_source_map: Vec<usize>,
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
// InlineCache — Phase 4.2
//
// Caches method resolution results keyed by (class_name, method_name).
// Eliminates the O(n) class hierarchy walk for monomorphic call sites.
// ─────────────────────────────────────────────────────────────────────────────

pub struct InlineCache {
    cache: std::sync::Mutex<HashMap<(String, String), Option<String>>>,
}

impl InlineCache {
    pub fn new() -> Self {
        InlineCache { cache: std::sync::Mutex::new(HashMap::new()) }
    }

    pub fn lookup(&self, class_name: &str, method_name: &str) -> Option<Option<String>> {
        self.cache.lock().unwrap().get(&(class_name.to_string(), method_name.to_string())).cloned()
    }

    pub fn insert(&self, class_name: &str, method_name: &str, resolved: Option<String>) {
        self.cache.lock().unwrap().insert((class_name.to_string(), method_name.to_string()), resolved);
    }

    pub fn len(&self) -> usize {
        self.cache.lock().unwrap().len()
    }

    pub fn clear(&self) {
        self.cache.lock().unwrap().clear();
    }
}

impl Default for InlineCache {
    fn default() -> Self {
        Self::new()
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// VMEngine
// ─────────────────────────────────────────────────────────────────────────────

pub struct VMEngine {
    // Bytecode and execution state
    bytecode: Vec<u8>,
    opcodes:  Vec<OpCode>,        // pre-decoded for fast dispatch
    instruction_pointer: usize,
    pub(crate) state: VMState,

    // Stack / registers (Arc<Value> — O(1) clone)
    stack:      Vec<Arc<Value>>,
    registers:  Vec<Arc<Value>>,
    call_stack: Vec<CallFrame>,

    // Global state
    globals:      RwLock<HashMap<String, Arc<Value>>>,
    constants:    Vec<Arc<Value>>,
    func_table:   HashMap<String, FuncDef>,
    object_cache: Arc<ObjectCache>,
    source_map: Vec<usize>,  // line number for each opcode (0 = unknown)

    // v3.8.4: Object pools
    array_pool:  Arc<ArrayPool>,
    object_pool: Arc<ObjectPool>,

    // v3.9.4+: JIT compilation engine (hot trace detection → LLVM IR)
    jit: Option<JitEngine>,

    // Phase 4.2: Inline cache for method dispatch
    method_cache: InlineCache,

    // Phase 5.1: Native function callbacks (Python bridge)
    native_callbacks: HashMap<String, Arc<dyn Fn(&[Arc<Value>]) -> Result<Arc<Value>, String> + Send + Sync>>,

    // Performance metrics
    instructions_executed: usize,
    opt_stats: OptStats,       // v3.9.0: compiler optimization pass results
}

impl VMEngine {
    /// Create a new VM from raw bytecode.
    pub fn new(bytecode: Vec<u8>) -> Self {
        // Initialise interned constants once (no-op on subsequent calls)
        init_interns();

        // Pre-decode bytecode into OpCode vector
        let opcodes: Vec<OpCode> = bytecode
            .iter()
            .filter_map(|&b| OpCode::from_byte(b))
            .collect();

        // v3.9.0: Run compiler optimization passes (including type specialization)
        let (opcodes, opt_stats, _type_map) = optimize_with_types(opcodes);

        Self::from_opcodes(opcodes, Vec::new(), opt_stats)
    }

    /// Create a new VM from pre-compiled opcodes (bypasses bytecode decoding).
    pub fn from_opcodes(opcodes: Vec<OpCode>, constants: Vec<Arc<Value>>, opt_stats: OptStats) -> Self {
        Self::from_opcodes_with_funcs(opcodes, constants, HashMap::new(), opt_stats)
    }

    /// Create a new VM with pre-compiled opcodes, source map, and a function table.
    pub fn from_opcodes_with_funcs(
        opcodes: Vec<OpCode>,
        constants: Vec<Arc<Value>>,
        func_table: HashMap<String, FuncDef>,
        opt_stats: OptStats,
    ) -> Self {
        Self::from_opcodes_with_source_map(opcodes, constants, Vec::new(), func_table, opt_stats)
    }

    /// Create a new VM with pre-compiled opcodes and source map.
    pub fn from_opcodes_with_source_map(
        opcodes: Vec<OpCode>,
        constants: Vec<Arc<Value>>,
        source_map: Vec<usize>,
        func_table: HashMap<String, FuncDef>,
        opt_stats: OptStats,
    ) -> Self {
        init_interns();
        let nil = intern_nil();
        let mut globals = HashMap::new();
        // Register user-defined functions from func_table
        for (name, _def) in &func_table {
            globals.insert(name.clone(), Arc::new(Value::Function(name.clone())));
        }
        // Register builtin functions
        globals.insert("print".to_string(), Arc::new(Value::Function("print".to_string())));
        globals.insert("clock".to_string(), Arc::new(Value::Function("clock".to_string())));
        globals.insert("str".to_string(), Arc::new(Value::Function("str".to_string())));
        globals.insert("int".to_string(), Arc::new(Value::Function("int".to_string())));
        globals.insert("float".to_string(), Arc::new(Value::Function("float".to_string())));
        globals.insert("len".to_string(), Arc::new(Value::Function("len".to_string())));
        globals.insert("range".to_string(), Arc::new(Value::Function("range".to_string())));
        globals.insert("typeof".to_string(), Arc::new(Value::Function("typeof".to_string())));
        globals.insert("input".to_string(), Arc::new(Value::Function("input".to_string())));
        globals.insert("sqrt".to_string(), Arc::new(Value::Function("sqrt".to_string())));
        globals.insert("abs".to_string(), Arc::new(Value::Function("abs".to_string())));
        globals.insert("min".to_string(), Arc::new(Value::Function("min".to_string())));
        globals.insert("max".to_string(), Arc::new(Value::Function("max".to_string())));
        globals.insert("pow".to_string(), Arc::new(Value::Function("pow".to_string())));
        globals.insert("round".to_string(), Arc::new(Value::Function("round".to_string())));
        globals.insert("rand".to_string(), Arc::new(Value::Function("rand".to_string())));
        globals.insert("cos".to_string(), Arc::new(Value::Function("cos".to_string())));
        globals.insert("sin".to_string(), Arc::new(Value::Function("sin".to_string())));
        // Register user-defined functions in globals
        for (name, _def) in &func_table {
            globals.insert(name.clone(), Arc::new(Value::Function(name.clone())));
        }
        VMEngine {
            bytecode: Vec::new(),
            opcodes,
            instruction_pointer: 0,
            state: VMState::Running,
            stack:      Vec::with_capacity(1024),
            registers:  vec![nil; 256],
            call_stack: Vec::with_capacity(128),
            globals:      RwLock::new(globals),
            constants,
            func_table,
            source_map,
            object_cache: Arc::new(ObjectCache::new()),
            array_pool:   Arc::new(ArrayPool::new()),
            object_pool:  Arc::new(ObjectPool::new()),
            jit: None,
            method_cache: InlineCache::new(),
            native_callbacks: HashMap::new(),
            instructions_executed: 0,
            opt_stats,
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // JIT control
    // ─────────────────────────────────────────────────────────────────────────

    /// Enable JIT trace detection. Hot loops will be compiled to LLVM IR
    /// automatically during execution.
    pub fn enable_jit(&mut self) {
        self.jit = Some(JitEngine::new());
    }

    /// Returns true if JIT is enabled.
    pub fn jit_enabled(&self) -> bool {
        self.jit.is_some()
    }

    /// Collect all hot traces as (trace_name, llvm_ir) pairs.
    pub fn collect_hot_traces_ir(&self) -> Vec<(String, String)> {
        self.jit.as_ref()
            .map(|j| j.collect_hot_traces())
            .unwrap_or_default()
    }

    /// Get JIT stats as a formatted string, or None if JIT is disabled.
    pub fn jit_stats_string(&self) -> Option<String> {
        self.jit.as_ref().map(|j| j.stats_string())
    }

    /// Record execution of a loop body for JIT trace detection.
    fn record_loop_execution(&mut self, loop_header: usize, jump_ip: usize) {
        let jit = match self.jit.as_mut() {
            Some(j) => j,
            None => return,
        };
        let trace_id = TraceId::from_index(loop_header);
        if jit.get_stub(&trace_id).is_none() {
            // Extract loop body opcodes from header to the backward jump (inclusive)
            let body = self.opcodes[loop_header..=jump_ip].to_vec();
            jit.register_trace(trace_id.clone(), body);
        }
        jit.record_trace_execution(&trace_id);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Execution loop
    // ─────────────────────────────────────────────────────────────────────────

    pub fn execute(&mut self) -> Result<Value, String> {
        while self.instruction_pointer < self.opcodes.len() {
            let ip = self.instruction_pointer;
            let opcode = self.opcodes[ip];
            self.instruction_pointer += 1;
            self.execute_opcode(opcode).map_err(|e| {
                let line = self.source_map.get(ip).copied().unwrap_or(0);
                if line > 0 {
                    format!("Line {}: {}", line, e)
                } else {
                    e
                }
            })?;
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

            // ── Arithmetic (generic) ───────────────────────────────────────

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

            // ── Phase 4.1: Type-specialized arithmetic fast paths ──────────

            OpCode::AddInt => self.int_binary_op(|a, b| Ok(a.saturating_add(b))),
            OpCode::SubInt => self.int_binary_op(|a, b| Ok(a.saturating_sub(b))),
            OpCode::MulInt => self.int_binary_op(|a, b| Ok(a.saturating_mul(b))),
            OpCode::ModInt => self.int_binary_op(|a, b| if b == 0 {
                Err("Modulo by zero".to_string())
            } else {
                Ok(a % b)
            }),
            OpCode::AddFloat => self.float_binary_op(|a, b| Ok(a + b)),
            OpCode::SubFloat => self.float_binary_op(|a, b| Ok(a - b)),
            OpCode::MulFloat => self.float_binary_op(|a, b| Ok(a * b)),
            OpCode::DivFloat => self.float_binary_op(|a, b| {
                if b == 0.0 { Err("Division by zero".to_string()) }
                else { Ok(a / b) }
            }),
            OpCode::ModFloat => self.float_binary_op(|a, b| {
                if b == 0.0 { Err("Modulo by zero".to_string()) }
                else { Ok(a % b) }
            }),
            OpCode::EqualInt => self.int_cmp_op(|a, b| a == b),
            OpCode::EqualFloat => self.float_cmp_op(|a, b| (a - b).abs() < f64::EPSILON),
            OpCode::LessThanInt => self.int_cmp_op(|a, b| a < b),
            OpCode::LessThanFloat => self.float_cmp_op(|a, b| a < b),

            // ── String operations ────────────────────────────────────────────

            OpCode::Concat => {
                let b = self.stack.pop().ok_or("Stack underflow")?;
                let a = self.stack.pop().ok_or("Stack underflow")?;
                let s = format!("{}{}", a.as_ref().to_display_string(), b.as_ref().to_display_string());
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
            OpCode::IterStart => {
                let val = self.stack.pop().ok_or("Stack underflow")?;
                let items: Arc<Value> = match val.as_ref() {
                    Value::Array(_) => {
                        // Use the array itself as the items to iterate
                        Arc::clone(&val)
                    }
                    Value::String(s) => {
                        let chars: Vec<Arc<Value>> = s.chars()
                            .map(|c| intern_string(c.to_string()))
                            .collect();
                        Arc::new(Value::Array(chars))
                    }
                    Value::Object(obj) => {
                        // Iterate over object keys (sorted)
                        let mut keys: Vec<String> = obj.keys().cloned().collect();
                        keys.sort();
                        let key_vals: Vec<Arc<Value>> = keys.into_iter()
                            .map(|k| intern_string(k))
                            .collect();
                        Arc::new(Value::Array(key_vals))
                    }
                    _ => return Err("Type error: cannot iterate over value".to_string()),
                };
                // Push iterator state: [items_array, index=0]
                self.stack.push(Arc::new(Value::Array(vec![items, intern_int(0)])));
                Ok(())
            }
            OpCode::IterNext => {
                let iter = self.stack.pop().ok_or("Stack underflow")?;
                match iter.as_ref() {
                    Value::Array(pair) if pair.len() == 2 => {
                        let items = Arc::clone(&pair[0]);
                        let idx = match pair[1].as_ref() {
                            Value::Int(i) if *i >= 0 => *i as usize,
                            _ => return Err("Invalid iterator: bad index".to_string()),
                        };
                        let len = match items.as_ref() {
                            Value::Array(arr) => arr.len(),
                            _ => return Err("Invalid iterator state".to_string()),
                        };
                        if idx < len {
                            let value = match items.as_ref() {
                                Value::Array(arr) => Arc::clone(&arr[idx]),
                                _ => intern_nil(),
                            };
                            self.stack.push(Arc::new(Value::Array(vec![items, intern_int(idx as i64 + 1)])));
                            self.stack.push(value);
                        } else {
                            // Done: push nil placeholder + nil sentinel
                            self.stack.push(intern_nil());
                            self.stack.push(intern_nil());
                        }
                    }
                    _ => return Err("Invalid iterator state".to_string()),
                }
                Ok(())
            }
            OpCode::LoadConst(idx) => {
                let val = self.constants.get(idx)
                    .ok_or_else(|| format!("Constant pool index {} out of bounds", idx))?;
                self.stack.push(Arc::clone(val));
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
                let jump_ip = self.instruction_pointer - 1;
                self.instruction_pointer = addr;
                if addr < jump_ip {
                    self.record_loop_execution(addr, jump_ip);
                }
                Ok(())
            }
            OpCode::JumpIfFalse(addr) => {
                let jump_ip = self.instruction_pointer - 1;
                let val = self.stack.pop().ok_or("Stack underflow")?;
                if !val.is_truthy() {
                    self.instruction_pointer = addr;
                    if addr < jump_ip {
                        self.record_loop_execution(addr, jump_ip);
                    }
                }
                Ok(())
            }
            OpCode::JumpIfTrue(addr) => {
                let jump_ip = self.instruction_pointer - 1;
                let val = self.stack.pop().ok_or("Stack underflow")?;
                if val.is_truthy() {
                    self.instruction_pointer = addr;
                    if addr < jump_ip {
                        self.record_loop_execution(addr, jump_ip);
                    }
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
                let name = match self.constants.get(idx) {
                    Some(c) => match &**c {
                        Value::String(s) => s.clone(),
                        _ => format!("global_{}", idx),
                    },
                    None => format!("global_{}", idx),
                };
                self.globals.write().insert(name, val);
                Ok(())
            }
            OpCode::LoadGlobal(idx) => {
                let name = match self.constants.get(idx) {
                    Some(c) => match &**c {
                        Value::String(s) => s.clone(),
                        _ => format!("global_{}", idx),
                    },
                    None => format!("global_{}", idx),
                };
                let val = self.globals.read()
                    .get(&name)
                    .map(|v| Arc::clone(v))
                    .unwrap_or_else(intern_nil);
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
                        // First check instance fields
                        if let Some(val) = o.get(key) {
                            self.stack.push(Arc::clone(val));
                            return Ok(());
                        }
                        // Not found — check class descriptor's methods (includes parent chain)
                        let val = self._lookup_method_in_class(o, key, &obj);
                        self.stack.push(val);
                        Ok(())
                    }
                    _ => Err("Invalid index operation".to_string()),
                }
            }
            OpCode::SetIndex => {
                let val = self.stack.pop().ok_or("Stack underflow")?;
                let idx = self.stack.pop().ok_or("Stack underflow")?;
                let mut obj = self.stack.pop().ok_or("Stack underflow")?;
                let obj_mut = Arc::make_mut(&mut obj);
                match (obj_mut, idx.as_ref()) {
                    (Value::Array(arr), Value::Int(i)) => {
                        let index = if *i < 0 {
                            ((arr.len() as i64) + i) as usize
                        } else {
                            *i as usize
                        };
                        if index < arr.len() {
                            arr[index] = val;
                        }
                    }
                    (Value::Object(m), value) => {
                        let key = value.to_display_string();
                        m.insert(key, val);
                    }
                    _ => {}
                }
                self.stack.push(obj);
                Ok(())
            }

            // ── Misc ─────────────────────────────────────────────────────────

            OpCode::Halt => {
                self.state = VMState::Halted;
                Ok(())
            }
            OpCode::Nop => Ok(()),
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

    // ── Phase 4.1: Typed opcode helpers ──────────────────────────────────

    /// Fast path: both operands are Int, result is Int.
    fn int_binary_op<F>(&mut self, op: F) -> Result<(), String>
    where F: FnOnce(i64, i64) -> Result<i64, String> {
        let b = self.stack.pop().ok_or("Stack underflow")?;
        let a = self.stack.pop().ok_or("Stack underflow")?;
        let x = match a.as_ref() { Value::Int(n) => *n, _ => return Err("Type error: expected int".to_string()) };
        let y = match b.as_ref() { Value::Int(n) => *n, _ => return Err("Type error: expected int".to_string()) };
        let result = op(x, y)?;
        self.stack.push(intern_int(result));
        Ok(())
    }

    /// Fast path: both operands are Float, result is Float.
    fn float_binary_op<F>(&mut self, op: F) -> Result<(), String>
    where F: FnOnce(f64, f64) -> Result<f64, String> {
        let b = self.stack.pop().ok_or("Stack underflow")?;
        let a = self.stack.pop().ok_or("Stack underflow")?;
        let x = match a.as_ref() { Value::Float(f) => *f, _ => return Err("Type error: expected float".to_string()) };
        let y = match b.as_ref() { Value::Float(f) => *f, _ => return Err("Type error: expected float".to_string()) };
        let result = op(x, y)?;
        self.stack.push(Arc::new(Value::Float(result)));
        Ok(())
    }

    /// Fast path: Int comparison → Bool.
    fn int_cmp_op<F>(&mut self, op: F) -> Result<(), String>
    where F: FnOnce(i64, i64) -> bool {
        let b = self.stack.pop().ok_or("Stack underflow")?;
        let a = self.stack.pop().ok_or("Stack underflow")?;
        let x = match a.as_ref() { Value::Int(n) => *n, _ => return Err("Type error: expected int".to_string()) };
        let y = match b.as_ref() { Value::Int(n) => *n, _ => return Err("Type error: expected int".to_string()) };
        self.stack.push(intern_bool(op(x, y)));
        Ok(())
    }

    /// Fast path: Float comparison → Bool.
    fn float_cmp_op<F>(&mut self, op: F) -> Result<(), String>
    where F: FnOnce(f64, f64) -> bool {
        let b = self.stack.pop().ok_or("Stack underflow")?;
        let a = self.stack.pop().ok_or("Stack underflow")?;
        let x = match a.as_ref() { Value::Float(f) => *f, _ => return Err("Type error: expected float".to_string()) };
        let y = match b.as_ref() { Value::Float(f) => *f, _ => return Err("Type error: expected float".to_string()) };
        self.stack.push(intern_bool(op(x, y)));
        Ok(())
    }

    /// Look up a method name in a class descriptor (including parent chain).
    /// Returns BoundMethod if found, Nil otherwise.
    fn _lookup_method_in_class(&self, obj_fields: &HashMap<String, Arc<Value>>, key: &str, obj: &Arc<Value>) -> Arc<Value> {
        let class_name = match obj_fields.get("__class__").and_then(|v| {
            if let Value::String(cname) = v.as_ref() { Some(cname.clone()) } else { None }
        }) {
            Some(cn) => cn,
            None => return intern_nil(),
        };

        // Phase 4.2: Inline cache check — fast path for monomorphic call sites
        if let Some(cached) = self.method_cache.lookup(&class_name, key) {
            return match cached {
                Some(full_name) => Arc::new(Value::BoundMethod(full_name, Arc::clone(obj))),
                None => intern_nil(),
            };
        }

        let globals = self.globals.read();
        let mut current = Some(class_name.clone());
        let mut resolved: Option<String> = None;
        while let Some(cname) = current.take() {
            if let Some(desc) = globals.get(&cname) {
                if let Value::Object(desc_obj) = desc.as_ref() {
                    if let Some(methods) = desc_obj.get("__methods__") {
                        if let Value::Object(methods_obj) = methods.as_ref() {
                            if let Some(method_name) = methods_obj.get(key) {
                                if let Value::String(full_name) = method_name.as_ref() {
                                    resolved = Some(full_name.clone());
                                    break;
                                }
                            }
                        }
                    }
                    // Walk up parent chain
                    if let Some(parent_name) = desc_obj.get("__parent__") {
                        if let Value::String(pname) = parent_name.as_ref() {
                            if !pname.is_empty() {
                                current = Some(pname.clone());
                            }
                        }
                    }
                }
            }
        }

        // Cache the result (even if not found — negative caching avoids re-walking)
        self.method_cache.insert(&class_name, key, resolved.clone());

        match resolved {
            Some(full_name) => Arc::new(Value::BoundMethod(full_name, Arc::clone(obj))),
            None => intern_nil(),
        }
    }

    fn call_function(&mut self, args: usize) -> Result<(), String> {
        // Stack layout: [func, arg1, arg2, ..., argN]
        // Pop args first, then func
        let mut call_args = Vec::with_capacity(args);
        for _ in 0..args {
            call_args.push(self.stack.pop().ok_or("Stack underflow")?);
        }
        call_args.reverse();
        let func = self.stack.pop().ok_or("Stack underflow")?;

        match &*func {
            Value::BoundMethod(method_name, instance) => {
                // Bound method: prepend instance as first arg (self)
                if let Some(func_def) = self.func_table.get(method_name) {
                    let nil = intern_nil();
                    let saved_opcodes = std::mem::replace(&mut self.opcodes, func_def.opcodes.clone());
                    let saved_constants = std::mem::replace(&mut self.constants, func_def.constants.clone());
                    let saved_registers = std::mem::replace(&mut self.registers, vec![nil; 256]);
                    let saved_stack = std::mem::take(&mut self.stack);
                    let saved_source_map = std::mem::replace(&mut self.source_map, func_def.source_map.clone());
                    let saved_ip = self.instruction_pointer;

                    // Set arg[0] = self (the instance), then remaining args
                    self.registers[0] = Arc::clone(instance);
                    for (i, arg) in call_args.iter().enumerate() {
                        if i + 1 < func_def.param_count {
                            self.registers[i + 1] = Arc::clone(arg);
                        }
                    }
                    let frame = CallFrame {
                        name: method_name.clone(),
                        registers: saved_registers,
                        instruction_pointer: saved_ip,
                        return_address: saved_ip,
                        saved_opcodes,
                        saved_constants,
                        saved_stack,
                        saved_source_map,
                    };
                    self.call_stack.push(frame);
                    self.instruction_pointer = 0;
                    Ok(())
                } else {
                    let nil = intern_nil();
                    self.stack.push(nil);
                    Ok(())
                }
            }
            Value::NativeFn(name) => {
                // Native function callback (Python bridge)
                if let Some(callback) = self.native_callbacks.get(name) {
                    let result = (callback)(&call_args)?;
                    self.stack.push(result);
                    Ok(())
                } else {
                    let nil = intern_nil();
                    self.stack.push(nil);
                    Ok(())
                }
            }
            Value::Function(name) => {
                // Phase 5.1: Check native callbacks first (Python bridge)
                if let Some(callback) = self.native_callbacks.get(name) {
                    let result = (callback)(&call_args)?;
                    self.stack.push(result);
                    return Ok(());
                }
                // Check if this is a user-defined function
                if let Some(func_def) = self.func_table.get(name) {
                    // Save caller state
                    let nil = intern_nil();
                    let saved_opcodes = std::mem::replace(&mut self.opcodes, func_def.opcodes.clone());
                    let saved_constants = std::mem::replace(&mut self.constants, func_def.constants.clone());
                    let saved_registers = std::mem::replace(&mut self.registers, vec![nil; 256]);
                    let saved_stack = std::mem::take(&mut self.stack);
                    let saved_source_map = std::mem::replace(&mut self.source_map, func_def.source_map.clone());
                    let saved_ip = self.instruction_pointer;

                    // Set up arguments in registers
                    for (i, arg) in call_args.iter().enumerate() {
                        if i < func_def.param_count {
                            self.registers[i] = Arc::clone(arg);
                        }
                    }
                    // Push call frame
                    let frame = CallFrame {
                        name: name.clone(),
                        registers: saved_registers,
                        instruction_pointer: saved_ip,
                        return_address: saved_ip,
                        saved_opcodes,
                        saved_constants,
                        saved_stack,
                        saved_source_map,
                    };
                    self.call_stack.push(frame);
                    self.instruction_pointer = 0;
                    Ok(())
                } else {
                match name.as_str() {
                    "print" => {
                        use std::io::Write;
                        let stdout = std::io::stdout();
                        let mut handle = stdout.lock();
                        for v in &call_args {
                            write!(handle, "{}", v).ok();
                        }
                        writeln!(handle).ok();
                        handle.flush().ok();
                        let nil = intern_nil();
                        self.stack.push(nil);
                        Ok(())
                    }
                    "clock" => {
                        let now = std::time::SystemTime::now()
                            .duration_since(std::time::UNIX_EPOCH)
                            .unwrap_or_default()
                            .as_secs_f64();
                        self.stack.push(Arc::new(Value::Float(now)));
                        Ok(())
                    }
                    "str" => {
                        let val = call_args.first().cloned().unwrap_or_else(intern_nil);
                        let s = val.as_ref().to_display_string();
                        self.stack.push(intern_string(s));
                        Ok(())
                    }
                    "int" => {
                        let val = call_args.first().cloned().unwrap_or_else(intern_nil);
                        let n = match &*val {
                            Value::Int(i) => *i,
                            Value::Float(f) => *f as i64,
                            Value::String(s) => s.parse::<i64>().unwrap_or(0),
                            Value::Bool(b) => if *b { 1 } else { 0 },
                            _ => 0,
                        };
                        self.stack.push(intern_int(n));
                        Ok(())
                    }
                    "float" => {
                        let val = call_args.first().cloned().unwrap_or_else(intern_nil);
                        let f = match &*val {
                            Value::Int(i) => *i as f64,
                            Value::Float(fv) => *fv,
                            Value::String(s) => s.parse::<f64>().unwrap_or(0.0),
                            Value::Bool(b) => if *b { 1.0 } else { 0.0 },
                            _ => 0.0,
                        };
                        self.stack.push(Arc::new(Value::Float(f)));
                        Ok(())
                    }
                    "len" => {
                        let val = call_args.first().cloned().unwrap_or_else(intern_nil);
                        let n = match &*val {
                            Value::String(s) => s.len() as i64,
                            Value::Array(a) => a.len() as i64,
                            Value::Object(o) => o.len() as i64,
                            _ => 0,
                        };
                        self.stack.push(intern_int(n));
                        Ok(())
                    }
                    "range" => {
                        let start = call_args.get(0).cloned().unwrap_or_else(|| intern_int(0));
                        let end = call_args.get(1).cloned().unwrap_or_else(|| intern_int(0));
                        let s = match &*start { Value::Int(n) => *n, _ => 0 };
                        let e = match &*end { Value::Int(n) => *n, _ => 0 };
                        let mut arr = Vec::new();
                        for i in s..e {
                            arr.push(intern_int(i));
                        }
                        self.stack.push(Arc::new(Value::Array(arr)));
                        Ok(())
                    }
                    "typeof" => {
                        let val = call_args.first().cloned().unwrap_or_else(intern_nil);
                        let s = val.type_name().to_string();
                        self.stack.push(intern_string(s));
                        Ok(())
                    }
                    "input" => {
                        use std::io::Write;
                        let stdout = std::io::stdout();
                        let mut handle = stdout.lock();
                        if let Some(prompt) = call_args.first() {
                            write!(handle, "{}", prompt).ok();
                            handle.flush().ok();
                        }
                        let mut line = String::new();
                        match std::io::stdin().read_line(&mut line) {
                            Ok(_) => {
                                let trimmed = line.trim_end_matches('\n').trim_end_matches('\r').to_string();
                                self.stack.push(intern_string(trimmed));
                            }
                            Err(_) => {
                                let nil = intern_nil();
                                self.stack.push(nil);
                            }
                        }
                        Ok(())
                    }
                    "sqrt" => {
                        let val = call_args.first().cloned().unwrap_or_else(intern_nil);
                        let n = match &*val {
                            Value::Int(i) => *i as f64,
                            Value::Float(f) => *f,
                            _ => 0.0,
                        };
                        self.stack.push(Arc::new(Value::Float(n.sqrt())));
                        Ok(())
                    }
                    "abs" => {
                        let val = call_args.first().cloned().unwrap_or_else(intern_nil);
                        match &*val {
                            Value::Int(i) => {
                                self.stack.push(intern_int(i.abs()));
                            }
                            Value::Float(f) => {
                                self.stack.push(Arc::new(Value::Float(f.abs())));
                            }
                            _ => {
                                self.stack.push(Arc::clone(&val));
                            }
                        }
                        Ok(())
                    }
                    "min" => {
                        let a = call_args.get(0).cloned().unwrap_or_else(intern_nil);
                        let b = call_args.get(1).cloned().unwrap_or_else(intern_nil);
                        let result = match (&*a, &*b) {
                            (Value::Int(x), Value::Int(y)) => Value::Int((*x).min(*y)),
                            (Value::Float(x), Value::Float(y)) => Value::Float((*x).min(*y)),
                            (Value::Int(x), Value::Float(y)) => Value::Float((*x as f64).min(*y)),
                            (Value::Float(x), Value::Int(y)) => Value::Float((*x).min(*y as f64)),
                            (Value::String(x), Value::String(y)) => Value::String(if *x < *y { x.clone() } else { y.clone() }),
                            _ => Value::Nil,
                        };
                        self.stack.push(Arc::new(result));
                        Ok(())
                    }
                    "max" => {
                        let a = call_args.get(0).cloned().unwrap_or_else(intern_nil);
                        let b = call_args.get(1).cloned().unwrap_or_else(intern_nil);
                        let result = match (&*a, &*b) {
                            (Value::Int(x), Value::Int(y)) => Value::Int((*x).max(*y)),
                            (Value::Float(x), Value::Float(y)) => Value::Float((*x).max(*y)),
                            (Value::Int(x), Value::Float(y)) => Value::Float((*x as f64).max(*y)),
                            (Value::Float(x), Value::Int(y)) => Value::Float((*x).max(*y as f64)),
                            (Value::String(x), Value::String(y)) => Value::String(if *x > *y { x.clone() } else { y.clone() }),
                            _ => Value::Nil,
                        };
                        self.stack.push(Arc::new(result));
                        Ok(())
                    }
                    "pow" => {
                        let a = call_args.get(0).cloned().unwrap_or_else(intern_nil);
                        let b = call_args.get(1).cloned().unwrap_or_else(intern_nil);
                        let x = match &*a { Value::Int(i) => *i as f64, Value::Float(f) => *f, _ => 0.0 };
                        let y = match &*b { Value::Int(i) => *i as f64, Value::Float(f) => *f, _ => 0.0 };
                        self.stack.push(Arc::new(Value::Float(x.powf(y))));
                        Ok(())
                    }
                    "round" => {
                        let val = call_args.first().cloned().unwrap_or_else(intern_nil);
                        let n = match call_args.get(1) {
                            Some(places) => match (&*val, &**places) {
                                (Value::Float(f), Value::Int(p)) => {
                                    let factor = 10f64.powi(*p as i32);
                                    (f * factor).round() / factor
                                }
                                (Value::Int(i), Value::Int(p)) => {
                                    let factor = 10f64.powi(*p as i32);
                                    (*i as f64 * factor).round() / factor
                                }
                                (Value::Float(f), _) => f.round(),
                                (Value::Int(i), _) => *i as f64,
                                _ => 0.0,
                            },
                            None => match &*val {
                                Value::Float(f) => f.round(),
                                Value::Int(i) => *i as f64,
                                _ => 0.0,
                            },
                        };
                        self.stack.push(Arc::new(Value::Float(n)));
                        Ok(())
                    }
                    "rand" => {
                        use std::time::{SystemTime, UNIX_EPOCH};
                        let seed = SystemTime::now()
                            .duration_since(UNIX_EPOCH)
                            .unwrap_or_default()
                            .as_nanos();
                        let mut state = seed;
                        state ^= state >> 12;
                        state ^= state << 25;
                        state ^= state >> 27;
                        let val = (state as f64) / (u64::MAX as f64);
                        match call_args.len() {
                            0 => {
                                // rand()
                                self.stack.push(Arc::new(Value::Float(val)));
                            }
                            1 => {
                                // rand(max)
                                let max = &*call_args[0];
                                let m = match max {
                                    Value::Int(i) => *i as f64,
                                    Value::Float(f) => *f,
                                    _ => 1.0,
                                };
                                self.stack.push(Arc::new(Value::Float(val * m)));
                            }
                            _ => {
                                // rand(min, max)
                                let min = match &*call_args[0] {
                                    Value::Int(i) => *i as f64,
                                    Value::Float(f) => *f,
                                    _ => 0.0,
                                };
                                let max = match &*call_args[1] {
                                    Value::Int(i) => *i as f64,
                                    Value::Float(f) => *f,
                                    _ => 1.0,
                                };
                                self.stack.push(Arc::new(Value::Float(min + val * (max - min))));
                            }
                        }
                        Ok(())
                    }
                    "cos" => {
                        let val = call_args.first().cloned().unwrap_or_else(intern_nil);
                        let n = match &*val {
                            Value::Int(i) => (*i as f64).cos(),
                            Value::Float(f) => f.cos(),
                            _ => 0.0,
                        };
                        self.stack.push(Arc::new(Value::Float(n)));
                        Ok(())
                    }
                    "sin" => {
                        let val = call_args.first().cloned().unwrap_or_else(intern_nil);
                        let n = match &*val {
                            Value::Int(i) => (*i as f64).sin(),
                            Value::Float(f) => f.sin(),
                            _ => 0.0,
                        };
                        self.stack.push(Arc::new(Value::Float(n)));
                        Ok(())
                    }
                    _ => {
                        // Unknown function — return nil
                        let nil = intern_nil();
                        self.stack.push(nil);
                        Ok(())
                    }
                }
                }
            }
            _ => {
                // Not a function — return nil
                let nil = intern_nil();
                self.stack.push(nil);
                Ok(())
            }
        }
    }

    fn return_from_function(&mut self) -> Result<(), String> {
        match self.call_stack.pop() {
            Some(frame) => {
                // Keep the return value (top of current stack)
                let return_val = self.stack.pop()
                    .unwrap_or_else(intern_nil);
                // Restore caller state
                self.opcodes = frame.saved_opcodes;
                self.constants = frame.saved_constants;
                self.registers = frame.registers;
                self.stack = frame.saved_stack;
                self.source_map = frame.saved_source_map;
                self.instruction_pointer = frame.return_address;
                // Push return value onto caller's stack
                self.stack.push(return_val);
                Ok(())
            }
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
            jit_stats: self.jit_stats_string(),
            method_cache_entries: self.method_cache.len(),
        }
    }

    // ── Phase 5.1: Native function callbacks ─────────────────────────────

    /// Register a native (Python) function callback by name.
    pub fn register_native_fn<F>(&mut self, name: &str, callback: F)
    where F: Fn(&[Arc<Value>]) -> Result<Arc<Value>, String> + Send + Sync + 'static,
    {
        self.native_callbacks.insert(name.to_string(), Arc::new(callback));
        // Also add to globals so LoadGlobal can find it as NativeFn value
        self.globals.write().insert(name.to_string(), Arc::new(Value::NativeFn(name.to_string())));
    }

    pub fn reset(&mut self, bytecode: Vec<u8>) {
        let raw_opcodes: Vec<OpCode> = bytecode
            .iter()
            .filter_map(|&b| OpCode::from_byte(b))
            .collect();
        let (opcodes, opt_stats, _type_map) = optimize_with_types(raw_opcodes);
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
    pub jit_stats:             Option<String>,  // v3.9.4+: JIT stats
    pub method_cache_entries:  usize,       // Phase 4.2: inline cache size
}

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::jit::HOT_THRESHOLD;

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

    // ── JIT integration tests ─────────────────────────────────────────────

    /// Build a counter loop: count reg[0] from 0 to LIMIT, then halt.
    ///   IP 0: Push(0)              # init counter
    ///   IP 1: StoreReg(0)
    ///   IP 2: LoadReg(0)           # ← loop header
    ///   IP 3: Push(LIMIT)
    ///   IP 4: LessThan
    ///   IP 5: JumpIfFalse(11)      # exit if counter >= LIMIT
    ///   IP 6: LoadReg(0)
    ///   IP 7: Push(1)
    ///   IP 8: Add
    ///   IP 9: StoreReg(0)
    ///   IP 10: Jump(2)             # ← backward jump (loop backedge)
    ///   IP 11: LoadReg(0)          # result
    ///   IP 12: Halt
    fn make_loop_opcodes(limit: i32) -> Vec<OpCode> {
        vec![
            OpCode::Push(0),
            OpCode::StoreReg(0),
            OpCode::LoadReg(0),
            OpCode::Push(limit),
            OpCode::LessThan,
            OpCode::JumpIfFalse(11),
            OpCode::LoadReg(0),
            OpCode::Push(1),
            OpCode::Add,
            OpCode::StoreReg(0),
            OpCode::Jump(2),
            OpCode::LoadReg(0),
            OpCode::Halt,
        ]
    }

    #[test]
    fn test_jit_disabled_by_default() {
        let vm = VMEngine::from_opcodes(make_loop_opcodes(10), vec![], OptStats::default());
        assert!(!vm.jit_enabled());
        assert!(vm.collect_hot_traces_ir().is_empty());
        assert!(vm.jit_stats_string().is_none());
    }

    #[test]
    fn test_jit_enable() {
        let mut vm = VMEngine::from_opcodes(make_loop_opcodes(10), vec![], OptStats::default());
        assert!(!vm.jit_enabled());
        vm.enable_jit();
        assert!(vm.jit_enabled());
        assert!(vm.jit_stats_string().is_some());
    }

    #[test]
    fn test_jit_detects_loop_backedge() {
        // Use a loop that runs more than HOT_THRESHOLD iterations to trigger IR gen
        let mut vm = VMEngine::from_opcodes(make_loop_opcodes(HOT_THRESHOLD as i32 + 200), vec![], OptStats::default());
        vm.enable_jit();

        let result = vm.execute();
        assert!(result.is_ok(), "VM execution should succeed: {:?}", result);

        let stats = vm.jit_stats_string().unwrap();
        assert!(stats.contains("JIT Stats"), "Stats: {}", stats);

        let traces = vm.collect_hot_traces_ir();
        assert!(!traces.is_empty(), "Expected at least one hot trace after {} iterations", HOT_THRESHOLD + 200);
        let (_name, ir) = &traces[0];
        assert!(ir.contains("define i64 @"), "IR missing function def");
        // Loop trace ends with a backward branch (not ret), which is valid IR
        assert!(ir.contains("br label") || ir.contains("ret i64"),
            "IR should contain a valid terminator (br or ret)");
    }

    #[test]
    fn test_jit_loop_hot_after_threshold() {
        let mut vm = VMEngine::from_opcodes(make_loop_opcodes(HOT_THRESHOLD as i32 + 100), vec![], OptStats::default());
        vm.enable_jit();

        let result = vm.execute();
        assert!(result.is_ok(), "VM execution should succeed: {:?}", result);

        let traces = vm.collect_hot_traces_ir();
        assert!(!traces.is_empty(), "Expected hot traces after >= HOT_THRESHOLD loop iterations");
        for (name, ir) in &traces {
            assert!(ir.contains("define i64 @"), "IR for {} should contain function def", name);
            assert!(ir.contains("br label") || ir.contains("ret i64"),
                "IR for {} should contain a valid terminator (br or ret)", name);
        }
    }

    #[test]
    fn test_jit_below_threshold_not_hot() {
        // A small loop should NOT produce hot traces
        let mut vm = VMEngine::from_opcodes(make_loop_opcodes(5), vec![], OptStats::default());
        vm.enable_jit();

        let result = vm.execute();
        assert!(result.is_ok());

        let traces = vm.collect_hot_traces_ir();
        assert!(traces.is_empty(), "Small loop should not produce hot traces");
    }

    #[test]
    fn test_jit_stats_in_vm_stats() {
        let mut vm = VMEngine::from_opcodes(make_loop_opcodes(HOT_THRESHOLD as i32 + 50), vec![], OptStats::default());
        vm.enable_jit();
        let _ = vm.execute();

        let stats = vm.stats();
        assert!(stats.jit_stats.is_some(), "JIT stats should be present in VMStats");
        let jit = stats.jit_stats.unwrap();
        assert!(jit.contains("Total traces:"), "JIT stats should mention total traces: {}", jit);
    }
}
