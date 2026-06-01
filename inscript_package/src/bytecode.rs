//! Bytecode definitions and operations

/// VM Operation Codes
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OpCode {
    // Stack operations
    Push = 0x00,      // Push value to stack
    Pop = 0x01,       // Pop from stack
    Dup = 0x02,       // Duplicate top of stack
    
    // Arithmetic
    Add = 0x10,       // Pop two, push sum
    Sub = 0x11,       // Pop two, push difference
    Mul = 0x12,       // Pop two, push product
    Div = 0x13,       // Pop two, push quotient
    Mod = 0x14,       // Pop two, push modulo
    
    // Comparison
    Eq = 0x20,        // Equal
    Ne = 0x21,        // Not equal
    Lt = 0x22,        // Less than
    Le = 0x23,        // Less or equal
    Gt = 0x24,        // Greater than
    Ge = 0x25,        // Greater or equal
    
    // Control flow
    Jmp = 0x30,       // Jump to address
    JmpIfTrue = 0x31, // Jump if top of stack is true
    JmpIfFalse = 0x32,// Jump if top of stack is false
    
    // Functions
    Call = 0x40,      // Call function at address
    Return = 0x41,    // Return from function
    
    // Halt
    Halt = 0xFF,      // Stop execution
}

impl OpCode {
    /// Convert byte to OpCode
    pub fn from_byte(b: u8) -> Option<Self> {
        match b {
            0x00 => Some(OpCode::Push),
            0x01 => Some(OpCode::Pop),
            0x02 => Some(OpCode::Dup),
            0x10 => Some(OpCode::Add),
            0x11 => Some(OpCode::Sub),
            0x12 => Some(OpCode::Mul),
            0x13 => Some(OpCode::Div),
            0x14 => Some(OpCode::Mod),
            0x20 => Some(OpCode::Eq),
            0x21 => Some(OpCode::Ne),
            0x22 => Some(OpCode::Lt),
            0x23 => Some(OpCode::Le),
            0x24 => Some(OpCode::Gt),
            0x25 => Some(OpCode::Ge),
            0x30 => Some(OpCode::Jmp),
            0x31 => Some(OpCode::JmpIfTrue),
            0x32 => Some(OpCode::JmpIfFalse),
            0x40 => Some(OpCode::Call),
            0x41 => Some(OpCode::Return),
            0xFF => Some(OpCode::Halt),
            _ => None,
        }
    }
}

/// Compiled bytecode
pub struct ByteCode {
    pub instructions: Vec<u8>,
}

impl ByteCode {
    /// Create new bytecode
    pub fn new() -> Self {
        ByteCode {
            instructions: Vec::new(),
        }
    }

    /// Get instruction at address
    pub fn get(&self, addr: usize) -> Option<u8> {
        self.instructions.get(addr).copied()
    }

    /// Get length
    pub fn len(&self) -> usize {
        self.instructions.len()
    }

    /// Check if empty
    pub fn is_empty(&self) -> bool {
        self.instructions.is_empty()
    }

    /// Push instruction
    pub fn push(&mut self, op: u8) {
        self.instructions.push(op);
    }
}

impl Default for ByteCode {
    fn default() -> Self {
        Self::new()
    }
}
