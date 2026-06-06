// inscript_vm_engine/src/vm.rs
// High-performance bytecode virtual machine
// Optimized for game development scripting
// Features: register-based execution, object caching, stack optimization

use crate::value::Value;
use crate::opcodes::OpCode;
use std::collections::HashMap;
use parking_lot::RwLock;
use dashmap::DashMap;
use std::sync::Arc;

/// VM execution state
#[derive(Debug, Clone)]
pub enum VMState {
    Running,
    Paused,
    Halted,
    Error(String),
}

/// Call frame for function execution
#[derive(Debug, Clone)]
pub struct CallFrame {
    pub name: String,
    pub registers: Vec<Value>,
    pub instruction_pointer: usize,
    pub locals: HashMap<String, Value>,
    pub return_address: usize,
}

/// Global object cache for performance
pub struct ObjectCache {
    cache: DashMap<u64, Arc<Value>>,
    hits: std::sync::atomic::AtomicUsize,
    misses: std::sync::atomic::AtomicUsize,
}

impl ObjectCache {
    pub fn new() -> Self {
        ObjectCache {
            cache: DashMap::with_capacity(10000),
            hits: std::sync::atomic::AtomicUsize::new(0),
            misses: std::sync::atomic::AtomicUsize::new(0),
        }
    }

    pub fn get(&self, key: u64) -> Option<Arc<Value>> {
        match self.cache.get(&key) {
            Some(entry) => {
                self.hits.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                Some(entry.value().clone())
            }
            None => {
                self.misses.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                None
            }
        }
    }

    pub fn insert(&self, key: u64, value: Arc<Value>) {
        self.cache.insert(key, value);
    }

    pub fn stats(&self) -> (usize, usize) {
        (
            self.hits.load(std::sync::atomic::Ordering::Relaxed),
            self.misses.load(std::sync::atomic::Ordering::Relaxed),
        )
    }

    pub fn clear(&self) {
        self.cache.clear();
    }
}

/// Main VM Engine
pub struct VMEngine {
    // Bytecode and execution state
    bytecode: Vec<u8>,
    instruction_pointer: usize,
    state: VMState,
    
    // Stack and registers
    stack: Vec<Value>,
    registers: Vec<Value>,
    call_stack: Vec<CallFrame>,
    
    // Global state
    globals: RwLock<HashMap<String, Value>>,
    object_cache: Arc<ObjectCache>,
    
    // Performance metrics
    instructions_executed: usize,
    cache_hits: usize,
    cache_misses: usize,
}

impl VMEngine {
    /// Create new VM engine
    pub fn new(bytecode: Vec<u8>) -> Self {
        VMEngine {
            bytecode,
            instruction_pointer: 0,
            state: VMState::Running,
            stack: Vec::with_capacity(1024),
            registers: vec![Value::Nil; 256],
            call_stack: Vec::with_capacity(128),
            globals: RwLock::new(HashMap::new()),
            object_cache: Arc::new(ObjectCache::new()),
            instructions_executed: 0,
            cache_hits: 0,
            cache_misses: 0,
        }
    }

    /// Execute bytecode
    pub fn execute(&mut self) -> Result<Value, String> {
        while self.instruction_pointer < self.bytecode.len() {
            let opcode = self.fetch_opcode()?;
            self.execute_opcode(opcode)?;
            self.instructions_executed += 1;

            // Yield every 10000 instructions (prevent hang)
            if self.instructions_executed % 10000 == 0 {
                // Check for interrupts (could add cancellation token here)
            }
        }

        match &self.state {
            VMState::Running | VMState::Halted => {
                Ok(self.stack.pop().unwrap_or(Value::Nil))
            }
            VMState::Error(msg) => Err(msg.clone()),
            VMState::Paused => Err("VM paused".to_string()),
        }
    }

    /// Fetch next opcode
    fn fetch_opcode(&mut self) -> Result<OpCode, String> {
        if self.instruction_pointer >= self.bytecode.len() {
            return Err("Instruction pointer out of bounds".to_string());
        }

        let byte = self.bytecode[self.instruction_pointer];
        self.instruction_pointer += 1;
        
        OpCode::from_byte(byte)
            .ok_or_else(|| format!("Invalid opcode: {}", byte))
    }

    /// Execute single opcode
    fn execute_opcode(&mut self, op: OpCode) -> Result<(), String> {
        match op {
            // Stack operations
            OpCode::Push(val) => {
                self.stack.push(val);
                Ok(())
            }
            OpCode::Pop => {
                self.stack.pop().ok_or("Stack underflow".to_string())?;
                Ok(())
            }
            OpCode::Duplicate => {
                let val = self.stack.last()
                    .ok_or("Stack underflow")?
                    .clone();
                self.stack.push(val);
                Ok(())
            }

            // Arithmetic operations (FAST PATH - no allocation)
            OpCode::Add => self.binary_op(|a, b| a + b),
            OpCode::Sub => self.binary_op(|a, b| a - b),
            OpCode::Mul => self.binary_op(|a, b| a * b),
            OpCode::Div => self.binary_op(|a, b| {
                if b == 0.0 {
                    Err("Division by zero".to_string())
                } else {
                    Ok(a / b)
                }
            }),
            OpCode::Mod => self.binary_op(|a, b| {
                if b == 0.0 {
                    Err("Modulo by zero".to_string())
                } else {
                    Ok(a % b)
                }
            }),

            // Control flow
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
            OpCode::Call(args) => self.call_function(args),
            OpCode::Return => self.return_from_function(),

            // Register operations
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
                self.stack.push(self.registers[reg].clone());
                Ok(())
            }

            // Global operations
            OpCode::StoreGlobal(name) => {
                let val = self.stack.pop().ok_or("Stack underflow")?;
                self.globals.write().insert(name, val);
                Ok(())
            }
            OpCode::LoadGlobal(name) => {
                let val = self.globals.read()
                    .get(&name)
                    .cloned()
                    .ok_or(format!("Undefined global: {}", name))?;
                self.stack.push(val);
                Ok(())
            }

            // Other operations
            _ => Err(format!("Unimplemented opcode: {:?}", op)),
        }
    }

    /// Execute binary operation
    fn binary_op<F>(&mut self, op: F) -> Result<(), String>
    where
        F: Fn(f64, f64) -> Result<f64, String>,
    {
        let b = self.pop_number()?;
        let a = self.pop_number()?;
        let result = op(a, b)?;
        self.stack.push(Value::Float(result));
        Ok(())
    }

    /// Pop and validate number from stack
    fn pop_number(&mut self) -> Result<f64, String> {
        match self.stack.pop() {
            Some(Value::Int(n)) => Ok(n as f64),
            Some(Value::Float(f)) => Ok(f),
            Some(_) => Err("Type error: expected number".to_string()),
            None => Err("Stack underflow".to_string()),
        }
    }

    /// Call function
    fn call_function(&mut self, args: usize) -> Result<(), String> {
        // Pop function and arguments
        let _func = self.stack.pop().ok_or("Stack underflow")?;
        
        // Pop arguments
        for _ in 0..args {
            self.stack.pop().ok_or("Stack underflow")?;
        }
        
        // Create call frame
        let frame = CallFrame {
            name: "user_function".to_string(),
            registers: vec![Value::Nil; 256],
            instruction_pointer: self.instruction_pointer,
            locals: HashMap::new(),
            return_address: self.instruction_pointer,
        };
        
        self.call_stack.push(frame);
        Ok(())
    }

    /// Return from function
    fn return_from_function(&mut self) -> Result<(), String> {
        if let Some(frame) = self.call_stack.pop() {
            self.instruction_pointer = frame.return_address;
            Ok(())
        } else {
            Err("Return without matching call".to_string())
        }
    }

    /// Get VM statistics
    pub fn stats(&self) -> VMStats {
        let (cache_hits, cache_misses) = self.object_cache.stats();
        VMStats {
            instructions_executed: self.instructions_executed,
            stack_depth: self.stack.len(),
            call_depth: self.call_stack.len(),
            cache_hits,
            cache_misses,
            cache_hit_rate: if cache_hits + cache_misses > 0 {
                (cache_hits as f64) / ((cache_hits + cache_misses) as f64)
            } else {
                0.0
            },
        }
    }

    /// Reset VM state for reuse
    pub fn reset(&mut self, bytecode: Vec<u8>) {
        self.bytecode = bytecode;
        self.instruction_pointer = 0;
        self.state = VMState::Running;
        self.stack.clear();
        self.registers = vec![Value::Nil; 256];
        self.call_stack.clear();
        self.instructions_executed = 0;
    }
}

/// VM Statistics
#[derive(Debug, Clone)]
pub struct VMStats {
    pub instructions_executed: usize,
    pub stack_depth: usize,
    pub call_depth: usize,
    pub cache_hits: usize,
    pub cache_misses: usize,
    pub cache_hit_rate: f64,
}

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
    fn test_push_pop() {
        let mut vm = VMEngine::new(vec![]);
        vm.stack.push(Value::Int(42));
        assert_eq!(vm.stack.len(), 1);
        
        let val = vm.stack.pop();
        assert!(matches!(val, Some(Value::Int(42))));
    }

    #[test]
    fn test_registers() {
        let mut vm = VMEngine::new(vec![]);
        vm.registers[0] = Value::Int(100);
        assert!(matches!(vm.registers[0], Value::Int(100)));
    }

    #[test]
    fn test_globals() {
        let mut vm = VMEngine::new(vec![]);
        vm.globals.write().insert("x".to_string(), Value::Int(50));
        
        let val = vm.globals.read().get("x");
        assert!(matches!(val, Some(Value::Int(50))));
    }

    #[test]
    fn test_call_depth() {
        let vm = VMEngine::new(vec![]);
        assert_eq!(vm.call_stack.len(), 0);
    }
}
