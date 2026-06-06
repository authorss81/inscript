// inscript_vm_engine/src/value.rs and opcodes.rs combined

use std::collections::HashMap;
use std::fmt;

/// Value types in the VM
#[derive(Debug, Clone)]
pub enum Value {
    Nil,
    Bool(bool),
    Int(i64),
    Float(f64),
    String(String),
    Array(Vec<Value>),
    Object(HashMap<String, Value>),
    Function(String), // Function name
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
            Value::Float(fl) => write!(f, "{}", fl),
            Value::String(s) => write!(f, "\"{}\"", s),
            Value::Array(_) => write!(f, "[array]"),
            Value::Object(_) => write!(f, "{{object}}"),
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
    
    // Arithmetic
    Add,
    Sub,
    Mul,
    Div,
    Mod,
    Power,
    
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
    Call(usize), // number of arguments
    Return,
    
    // Register operations
    StoreReg(usize),
    LoadReg(usize),
    
    // Global operations
    StoreGlobal(usize), // index into string pool
    LoadGlobal(usize),
    
    // Array/Object operations
    CreateArray(usize), // array length
    CreateObject(usize), // object size
    Index,
    SetIndex,
    
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
            _ => 0xFE, // Unknown opcode
        }
    }
}
