//! Virtual Machine - Core Interpreter

use crate::error::{VMError, VMResult};
use crate::value::Value;
use crate::bytecode::OpCode;
use crate::stack::Stack;

/// Virtual Machine
pub struct VirtualMachine {
    stack: Stack,
    pc: usize,  // Program counter
    executions: u64,
}

impl VirtualMachine {
    /// Create new VM instance
    pub fn new() -> Self {
        VirtualMachine {
            stack: Stack::new(10000),
            pc: 0,
            executions: 0,
        }
    }

    /// Execute bytecode
    pub fn execute(&mut self, bytecode: &[u8]) -> VMResult<String> {
        self.executions += 1;
        self.pc = 0;
        self.stack.clear();

        while self.pc < bytecode.len() {
            let op_byte = bytecode[self.pc];
            self.pc += 1;

            match OpCode::from_byte(op_byte) {
                Some(OpCode::Push) => {
                    // Simple: push next byte as integer
                    if self.pc < bytecode.len() {
                        let val = bytecode[self.pc] as i64;
                        self.pc += 1;
                        self.stack.push(Value::Int(val))?;
                    }
                }

                Some(OpCode::Pop) => {
                    self.stack.pop()?;
                }

                Some(OpCode::Dup) => {
                    self.stack.dup()?;
                }

                Some(OpCode::Add) => {
                    let b = self.stack.pop()?;
                    let a = self.stack.pop()?;
                    let result = a.add(&b)?;
                    self.stack.push(result)?;
                }

                Some(OpCode::Sub) => {
                    let b = self.stack.pop()?;
                    let a = self.stack.pop()?;
                    let result = a.sub(&b)?;
                    self.stack.push(result)?;
                }

                Some(OpCode::Mul) => {
                    let b = self.stack.pop()?;
                    let a = self.stack.pop()?;
                    let result = a.mul(&b)?;
                    self.stack.push(result)?;
                }

                Some(OpCode::Div) => {
                    let b = self.stack.pop()?;
                    let a = self.stack.pop()?;
                    let result = a.div(&b)?;
                    self.stack.push(result)?;
                }

                Some(OpCode::Jmp) => {
                    // Jump to address (next byte)
                    if self.pc < bytecode.len() {
                        self.pc = bytecode[self.pc] as usize;
                    }
                }

                Some(OpCode::JmpIfTrue) => {
                    let cond = self.stack.pop()?;
                    if cond.is_truthy() && self.pc < bytecode.len() {
                        self.pc = bytecode[self.pc] as usize;
                    } else if self.pc < bytecode.len() {
                        self.pc += 1;
                    }
                }

                Some(OpCode::JmpIfFalse) => {
                    let cond = self.stack.pop()?;
                    if !cond.is_truthy() && self.pc < bytecode.len() {
                        self.pc = bytecode[self.pc] as usize;
                    } else if self.pc < bytecode.len() {
                        self.pc += 1;
                    }
                }

                Some(OpCode::Halt) => {
                    break;
                }

                _ => {
                    return Err(VMError::UnknownOpcode(op_byte));
                }
            }
        }

        // Return top of stack as string
        match self.stack.pop() {
            Ok(val) => Ok(val.to_string()),
            Err(_) => Ok("nil".to_string()),
        }
    }

    /// Get execution count
    pub fn execution_count(&self) -> u64 {
        self.executions
    }

    /// Get stack depth
    pub fn stack_depth(&self) -> usize {
        self.stack.depth()
    }
}

impl Default for VirtualMachine {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simple_arithmetic() {
        let mut vm = VirtualMachine::new();
        // Push 5, Push 3, Add
        let bytecode = vec![0x00, 5, 0x00, 3, 0x10, 0xFF];
        let result = vm.execute(&bytecode).unwrap();
        assert_eq!(result, "8");
    }

    #[test]
    fn test_multiple_operations() {
        let mut vm = VirtualMachine::new();
        // Push 10, Push 2, Div
        let bytecode = vec![0x00, 10, 0x00, 2, 0x13, 0xFF];
        let result = vm.execute(&bytecode).unwrap();
        assert_eq!(result, "5");
    }
}
