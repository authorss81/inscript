//! Error types for InScript VM

use std::fmt;

#[derive(Debug, Clone)]
pub enum VMError {
    StackUnderflow,
    StackOverflow,
    TypeMismatch(String),
    DivisionByZero,
    InvalidBytecode(String),
    UnknownOpcode(u8),
    InvalidMemoryAccess,
}

impl fmt::Display for VMError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            VMError::StackUnderflow => write!(f, "Stack underflow"),
            VMError::StackOverflow => write!(f, "Stack overflow"),
            VMError::TypeMismatch(msg) => write!(f, "Type mismatch: {}", msg),
            VMError::DivisionByZero => write!(f, "Division by zero"),
            VMError::InvalidBytecode(msg) => write!(f, "Invalid bytecode: {}", msg),
            VMError::UnknownOpcode(op) => write!(f, "Unknown opcode: {}", op),
            VMError::InvalidMemoryAccess => write!(f, "Invalid memory access"),
        }
    }
}

impl std::error::Error for VMError {}

pub type VMResult<T> = Result<T, VMError>;
