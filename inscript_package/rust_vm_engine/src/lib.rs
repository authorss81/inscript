// inscript_vm_engine/src/value.rs and opcodes.rs combined
// v3.8.4: Added pool module, cleaner Float display

use std::sync::Arc;
use std::collections::HashMap;
use std::fmt;

pub mod pool;
pub mod compiler;
pub use compiler::OptStats;

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

    // String operations (NEW v3.8.4)
    Concat,   // string concatenation via + on strings
    Length,   // len(x)

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
