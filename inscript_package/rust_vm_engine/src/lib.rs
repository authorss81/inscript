// inscript_vm_engine/src/value.rs and opcodes.rs combined
// v3.8.4: Added pool module, cleaner Float display

use std::sync::Arc;
use std::collections::HashMap;
use std::fmt;

pub mod pool;
pub mod compiler;
pub use compiler::OptStats;

/// Descriptor for a compiled user-defined function.
#[derive(Debug, Clone)]
pub struct FuncDef {
    pub opcodes: Vec<OpCode>,
    pub constants: Vec<Arc<Value>>,
    pub param_count: usize,
    pub source_map: Vec<usize>,
}

/// Value types in the VM (OPTIMIZATION v3.8.3: Arrays and Objects store Arc<Value> for O(1) clones)
/// v3.8.4: pool.rs interns Nil/Bool/small-Int to avoid repeated Arc::new() calls
#[derive(Debug, Clone)]
pub enum Value {
    Nil,
    Bool(bool),
    Int(i64),
    Float(f64),
    String(String),
    Array(Vec<Arc<Value>>),              // OPTIMIZATION: Arc for O(1) reference counting
    Object(HashMap<String, Arc<Value>>), // OPTIMIZATION: Arc for O(1) reference counting
    Function(String),                    // Function name
    BoundMethod(String, Arc<Value>),     // Method name + instance (self-binding)
}

impl Value {
    pub fn is_truthy(&self) -> bool {
        match self {
            Value::Nil => false,
            Value::Bool(b) => *b,
            Value::Int(n) => *n != 0,
            Value::Float(f) => *f != 0.0,
            Value::String(s) => !s.is_empty(),
            Value::Array(a) => !a.is_empty(),
            Value::Object(o) => !o.is_empty(),
            Value::Function(_) => true,
            Value::BoundMethod(_, _) => true,
        }
    }

    pub fn type_name(&self) -> &'static str {
        match self {
            Value::Nil => "nil",
            Value::Bool(_) => "bool",
            Value::Int(_) => "int",
            Value::Float(_) => "float",
            Value::String(_) => "string",
            Value::Array(_) => "array",
            Value::Object(_) => "object",
            Value::Function(_) => "function",
            Value::BoundMethod(_, _) => "function",
        }
    }
}

impl Value {
    /// Format value WITHOUT surrounding quotes (unlike Display which quotes strings).
    /// Used for string concatenation and str() conversion.
    pub fn to_display_string(&self) -> String {
        match self {
            Value::Nil => "nil".to_string(),
            Value::Bool(b) => b.to_string(),
            Value::Int(n) => n.to_string(),
            Value::Float(fl) => {
                if fl.fract() == 0.0 {
                    format!("{:.1}", fl)
                } else {
                    fl.to_string()
                }
            }
            Value::String(s) => s.clone(),
            Value::Array(a) => {
                let items: Vec<String> = a.iter().map(|v| v.to_display_string()).collect();
                format!("[{}]", items.join(", "))
            }
            Value::Object(o) => {
                let items: Vec<String> = o.iter().map(|(k, v)| format!("{}: {}", k, v.to_display_string())).collect();
                format!("{{{}}}", items.join(", "))
            }
            Value::Function(name) => format!("<function {}>", name),
            Value::BoundMethod(name, _) => format!("<method {}>", name),
        }
    }
}

impl fmt::Display for Value {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Value::Nil => write!(f, "nil"),
            Value::Bool(b) => write!(f, "{}", b),
            Value::Int(n) => write!(f, "{}", n),
            // v3.8.4: show at least one decimal place so 2.5 prints as "2.5" not "2"
            Value::Float(fl) => {
                if fl.fract() == 0.0 {
                    write!(f, "{:.1}", fl)
                } else {
                    write!(f, "{}", fl)
                }
            }
            Value::String(s) => write!(f, "\"{}\"", s),
            Value::Array(a) => write!(f, "[array:{}]", a.len()),
            Value::Object(o) => write!(f, "{{object:{}}}", o.len()),
            Value::Function(name) => write!(f, "<function {}>", name),
            Value::BoundMethod(name, _) => write!(f, "<method {}>", name),
        }
    }
}

/// OpCode definitions
#[derive(Debug, Clone, Copy)]
pub enum OpCode {
    // Stack operations
    Push(i32),
    Pop,
    Duplicate,
    Swap,          // NEW v3.8.4: swap top two stack items

    // Arithmetic
    Add,
    Sub,
    Mul,
    Div,
    Mod,
    Power,
    Negate,        // NEW v3.8.4: unary negation

    // Comparison
    Equal,
    NotEqual,
    LessThan,
    LessEqual,
    GreaterThan,
    GreaterEqual,

    // Logic
    And,
    Or,
    Not,

    // Control flow
    Jump(usize),
    JumpIfFalse(usize),
    JumpIfTrue(usize),
    Call(usize),  // number of arguments
    Return,

    // Register operations
    StoreReg(usize),
    LoadReg(usize),

    // Global operations
    StoreGlobal(usize),
    LoadGlobal(usize),

    // Array/Object operations
    CreateArray(usize),  // array length
    CreateObject(usize), // object size
    Index,
    SetIndex,

    // Constant pool
    LoadConst(usize),  // load constant by index from pool

    // String operations (NEW v3.8.4)
    Concat,   // string concatenation via + on strings
    Length,   // len(x)

    // Iterator protocol (NEW v3.9.4)
    IterStart,   // pop iterable, push [items_array, 0]
    IterNext,    // pop [items, idx], push [items, idx+1], push value_or_nil

    // Other
    Halt,
    Nop,
}

impl OpCode {
    pub fn from_byte(byte: u8) -> Option<Self> {
        match byte {
            0x00 => Some(OpCode::Nop),
            0x01 => Some(OpCode::Pop),
            0x02 => Some(OpCode::Duplicate),
            0x03 => Some(OpCode::Swap),
            0x04 => Some(OpCode::Negate),
            0x05 => Some(OpCode::Concat),
            0x06 => Some(OpCode::Length),
            0x07 => Some(OpCode::IterStart),
            0x08 => Some(OpCode::IterNext),
            0x10 => Some(OpCode::Add),
            0x11 => Some(OpCode::Sub),
            0x12 => Some(OpCode::Mul),
            0x13 => Some(OpCode::Div),
            0x14 => Some(OpCode::Mod),
            0x15 => Some(OpCode::Power),
            0x20 => Some(OpCode::Equal),
            0x21 => Some(OpCode::NotEqual),
            0x22 => Some(OpCode::LessThan),
            0x23 => Some(OpCode::LessEqual),
            0x24 => Some(OpCode::GreaterThan),
            0x25 => Some(OpCode::GreaterEqual),
            0x30 => Some(OpCode::And),
            0x31 => Some(OpCode::Or),
            0x32 => Some(OpCode::Not),
            0xFF => Some(OpCode::Halt),
            _ => None,
        }
    }

    pub fn to_byte(&self) -> u8 {
        match self {
            OpCode::Nop => 0x00,
            OpCode::Pop => 0x01,
            OpCode::Duplicate => 0x02,
            OpCode::Swap => 0x03,
            OpCode::Negate => 0x04,
            OpCode::Concat => 0x05,
            OpCode::Length => 0x06,
            OpCode::IterStart => 0x07,
            OpCode::IterNext => 0x08,
            OpCode::Add => 0x10,
            OpCode::Sub => 0x11,
            OpCode::Mul => 0x12,
            OpCode::Div => 0x13,
            OpCode::Mod => 0x14,
            OpCode::Power => 0x15,
            OpCode::Equal => 0x20,
            OpCode::NotEqual => 0x21,
            OpCode::LessThan => 0x22,
            OpCode::LessEqual => 0x23,
            OpCode::GreaterThan => 0x24,
            OpCode::GreaterEqual => 0x25,
            OpCode::And => 0x30,
            OpCode::Or => 0x31,
            OpCode::Not => 0x32,
            OpCode::Halt => 0xFF,
            _ => 0xFE,
        }
    }
}

pub mod vm;
pub use vm::{VMEngine, VMState, VMStats, CallFrame, ObjectCache};

pub mod ir;
pub use ir::IrEmitter;

pub mod jit;
pub use jit::{JitEngine, JitStats, StubEntry, TraceId, HOT_THRESHOLD, MAX_STUBS};

pub mod compile;

// ─────────────────────────────────────────────────────────────────────
// PyO3 FFI — Python bindings for the VM engine
// ─────────────────────────────────────────────────────────────────────

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyBytes};

/// Convert a Value to a Python object (int/float/bool/str/list/dict/nil)
#[allow(dead_code)]
fn value_to_py(py: Python, value: &Value) -> PyObject {
    match value {
        Value::Nil => py.None(),
        Value::Bool(b) => b.into_py(py),
        Value::Int(n) => n.into_py(py),
        Value::Float(f) => f.into_py(py),
        Value::String(s) => s.clone().into_py(py),
        Value::Array(arr) => {
            let py_list: Vec<PyObject> = arr.iter().map(|v| value_to_py(py, v)).collect();
            py_list.into_py(py)
        }
        Value::Object(obj) => {
            let dict = PyDict::new_bound(py);
            for (k, v) in obj {
                dict.set_item(k.as_str(), value_to_py(py, v)).ok();
            }
            dict.into()
        }
        Value::Function(name) => format!("<function {}>", name).into_py(py),
        Value::BoundMethod(name, _) => format!("<method {}>", name).into_py(py),
    }
}

/// Python wrapper for VMEngine
#[pyclass(name = "VMEngine")]
pub struct PyVMEngine {
    engine: vm::VMEngine,
}

#[pymethods]
impl PyVMEngine {
    #[new]
    fn new(bytecode: Bound<'_, PyBytes>) -> PyResult<Self> {
        let code = bytecode.as_bytes().to_vec();
        Ok(PyVMEngine {
            engine: vm::VMEngine::new(code),
        })
    }

    fn execute(&mut self) -> PyResult<String> {
        match self.engine.execute() {
            Ok(value) => Ok(value.to_string()),
            Err(e) => Ok(format!("Error: {}", e)),
        }
    }

    fn enable_jit(&mut self) {
        self.engine.enable_jit();
    }

    fn collect_hot_traces_ir(&self, py: Python) -> PyObject {
        let traces = self.engine.collect_hot_traces_ir();
        let list: Vec<PyObject> = traces.iter().map(|(name, ir)| {
            let d = PyDict::new_bound(py);
            d.set_item("name", name).ok();
            d.set_item("ir", ir).ok();
            d.into()
        }).collect();
        list.into_py(py)
    }

    fn reset(&mut self, bytecode: Bound<'_, PyBytes>) {
        let code = bytecode.as_bytes().to_vec();
        self.engine = vm::VMEngine::new(code);
    }

    fn state(&self) -> String {
        format!("{:?}", self.engine.state)
    }

    fn stats(&self, py: Python) -> PyObject {
        let s = self.engine.stats();
        let dict = PyDict::new_bound(py);
        dict.set_item("instructions_executed", s.instructions_executed).ok();
        dict.set_item("stack_depth", s.stack_depth).ok();
        dict.set_item("call_depth", s.call_depth).ok();
        dict.set_item("cache_hits", s.cache_hits).ok();
        dict.set_item("cache_misses", s.cache_misses).ok();
        dict.set_item("cache_hit_rate", s.cache_hit_rate).ok();
        if let Some(ref jit) = s.jit_stats {
            dict.set_item("jit_stats", jit).ok();
        }
        dict.into()
    }
}

/// Optimize InScript bytecode (passed as bytes) and return optimized bytes
#[pyfunction]
fn optimize_bytecode<'a>(py: Python<'a>, bytecode: Bound<'a, PyBytes>) -> Bound<'a, PyBytes> {
    let code = bytecode.as_bytes().to_vec();
    let opcodes: Vec<OpCode> = code.iter().filter_map(|&b| OpCode::from_byte(b)).collect();
    let (optimized, _stats) = compiler::optimize(opcodes);
    let bytes: Vec<u8> = optimized.iter().map(|op| op.to_byte()).collect();
    PyBytes::new_bound(py, &bytes)
}

/// Emit LLVM IR for a named trace
#[pyfunction]
fn emit_ir(trace_name: &str, opcodes_str: Bound<'_, PyBytes>) -> String {
    let bytes = opcodes_str.as_bytes();
    let opcodes: Vec<OpCode> = bytes.iter().filter_map(|&b| OpCode::from_byte(b)).collect();
    ir::emit_ir(trace_name, &opcodes)
}

#[pymodule]
fn inscript_vm_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyVMEngine>()?;
    m.add_function(wrap_pyfunction!(optimize_bytecode, m)?)?;
    m.add_function(wrap_pyfunction!(emit_ir, m)?)?;
    Ok(())
}
