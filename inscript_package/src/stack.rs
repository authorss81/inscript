//! Stack implementation for VM

use crate::error::{VMError, VMResult};
use crate::value::Value;

/// VM Stack - fixed size for predictable performance
pub struct Stack {
    data: Vec<Value>,
    capacity: usize,
}

impl Stack {
    /// Create new stack with capacity
    pub fn new(capacity: usize) -> Self {
        Stack {
            data: Vec::with_capacity(capacity),
            capacity,
        }
    }

    /// Push value onto stack
    #[inline]
    pub fn push(&mut self, value: Value) -> VMResult<()> {
        if self.data.len() >= self.capacity {
            return Err(VMError::StackOverflow);
        }
        self.data.push(value);
        Ok(())
    }

    /// Pop value from stack
    #[inline]
    pub fn pop(&mut self) -> VMResult<Value> {
        self.data.pop().ok_or(VMError::StackUnderflow)
    }

    /// Peek at top value without removing
    #[inline]
    pub fn peek(&self) -> VMResult<&Value> {
        self.data.last().ok_or(VMError::StackUnderflow)
    }

    /// Duplicate top of stack
    #[inline]
    pub fn dup(&mut self) -> VMResult<()> {
        if self.data.len() >= self.capacity {
            return Err(VMError::StackOverflow);
        }
        let value = self.peek()?.clone();
        self.data.push(value);
        Ok(())
    }

    /// Get current depth
    #[inline]
    pub fn depth(&self) -> usize {
        self.data.len()
    }

    /// Check if empty
    #[inline]
    pub fn is_empty(&self) -> bool {
        self.data.is_empty()
    }

    /// Clear stack
    pub fn clear(&mut self) {
        self.data.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_push_pop() {
        let mut stack = Stack::new(10);
        stack.push(Value::Int(42)).unwrap();
        let val = stack.pop().unwrap();
        assert!(matches!(val, Value::Int(42)));
    }

    #[test]
    fn test_stack_overflow() {
        let mut stack = Stack::new(1);
        stack.push(Value::Int(1)).unwrap();
        assert!(stack.push(Value::Int(2)).is_err());
    }

    #[test]
    fn test_stack_underflow() {
        let mut stack: Stack = Stack::new(10);
        assert!(stack.pop().is_err());
    }
}
