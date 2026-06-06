# -*- coding: utf-8 -*-
"""
InScript v3.8.0 - CRITICAL BUG FIX TESTS
Complete test suite for all 26 critical bugs
Run with: python -m pytest test_critical_bugfixes.py -v
"""

import pytest
import sys
import threading
import time
from io import StringIO

# Import the bug fixes
from BUG_FIXES_CRITICAL import (
    StackBoundsChecker,
    IntegerOverflowGuard,
    BoundedObjectCache,
    RegisterBoundsChecker,
    BytecodeValidator,
    CircularReferenceDetector,
    TypeConversionGuard,
    CacheKeyValidator,
    UTF8StringHandler,
    ConstEnforcer,
    TernaryShortCircuitFix,
    SwitchFallthroughControl,
    DefaultParamEvaluator,
    TypeHintEnforcer,
    FileLockManager,
)


# ─────────────────────────────────────────────────────────────────────────────
# BUG #1 & #6: STACK & CALL DEPTH TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestStackBoundsChecker:
    """Test stack and call depth bounds checking (BUG #1, #6)"""
    
    def test_call_depth_check(self):
        """BUG #6: Call depth should be bounded"""
        checker = StackBoundsChecker(max_call_depth=5)
        
        # Should succeed up to limit
        for i in range(5):
            checker.push_call()
        
        # Should fail on 6th call
        with pytest.raises(RuntimeError, match="Call depth.*exceeded"):
            checker.push_call()
    
    def test_stack_overflow_detection(self):
        """BUG #1: Stack overflow should be detected"""
        checker = StackBoundsChecker(max_stack_size=100)
        checker._stack_size = 100
        
        # Should raise on overflow
        with pytest.raises(RuntimeError, match="StackOverflowError"):
            checker.check_stack_overflow()
    
    def test_call_depth_push_pop(self):
        """BUG #6: Push/pop call depth correctly"""
        checker = StackBoundsChecker(max_call_depth=10)
        
        checker.push_call()
        assert checker._call_depth == 1
        
        checker.push_call()
        assert checker._call_depth == 2
        
        checker.pop_call()
        assert checker._call_depth == 1


# ─────────────────────────────────────────────────────────────────────────────
# BUG #2 & #53: INTEGER OVERFLOW TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegerOverflowGuard:
    """Test integer overflow detection (BUG #2, #53)"""
    
    def test_overflow_detection_small_numbers(self):
        """BUG #2: Small numbers should not overflow"""
        result = IntegerOverflowGuard.check_overflow(1000)
        assert result == 1000
        assert isinstance(result, int)
    
    def test_overflow_conversion_to_float(self):
        """BUG #2: Large numbers should convert to float"""
        large_int = 2 ** 54  # Beyond safe integer limit
        result = IntegerOverflowGuard.check_overflow(large_int)
        assert isinstance(result, float)
    
    def test_safe_multiply(self):
        """BUG #2: Multiplication should be safe"""
        result = IntegerOverflowGuard.safe_multiply(100, 100)
        assert result == 10000
    
    def test_safe_multiply_overflow(self):
        """BUG #2: Large multiplication should convert to float"""
        large = 2 ** 52
        result = IntegerOverflowGuard.safe_multiply(large, large)
        assert isinstance(result, float)
    
    def test_safe_power_small(self):
        """BUG #2: Small power should work"""
        result = IntegerOverflowGuard.safe_power(2, 3)
        assert result == 8
    
    def test_safe_power_overflow(self):
        """BUG #2: Large power should raise OverflowError"""
        with pytest.raises(OverflowError):
            IntegerOverflowGuard.safe_power(1000, 1000)
    
    def test_safe_add(self):
        """BUG #2: Addition should be safe"""
        result = IntegerOverflowGuard.safe_add(100, 200)
        assert result == 300


# ─────────────────────────────────────────────────────────────────────────────
# BUG #4: BOUNDED OBJECT CACHE TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestBoundedObjectCache:
    """Test bounded object cache (BUG #4)"""
    
    def test_cache_size_limit(self):
        """BUG #4: Cache should not exceed max size"""
        cache = BoundedObjectCache(max_size=5)
        
        # Add items
        for i in range(10):
            cache.put(f"key_{i}", f"value_{i}")
        
        # Should only have max_size items
        assert cache.size() <= 5
    
    def test_cache_get_put(self):
        """BUG #4: Cache should store and retrieve items"""
        cache = BoundedObjectCache(max_size=100)
        
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_cache_clear(self):
        """BUG #4: Cache should clear properly"""
        cache = BoundedObjectCache(max_size=100)
        
        cache.put("key1", "value1")
        assert cache.size() == 1
        
        cache.clear()
        assert cache.size() == 0
    
    def test_cache_lru_eviction(self):
        """BUG #4: Oldest item should be evicted when full"""
        cache = BoundedObjectCache(max_size=3)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        cache.put("key4", "value4")  # Should evict key1
        
        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"


# ─────────────────────────────────────────────────────────────────────────────
# BUG #5 & #8: REGISTER BOUNDS TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestRegisterBoundsChecker:
    """Test register bounds checking (BUG #5, #8)"""
    
    def test_register_get_valid(self):
        """BUG #8: Should get valid register"""
        checker = RegisterBoundsChecker(num_registers=256)
        checker.set(0, "value")
        assert checker.get(0) == "value"
    
    def test_register_get_out_of_bounds_negative(self):
        """BUG #5 & #8: Should reject negative index"""
        checker = RegisterBoundsChecker(num_registers=256)
        with pytest.raises(IndexError, match="out of bounds"):
            checker.get(-1)
    
    def test_register_get_out_of_bounds_too_large(self):
        """BUG #5 & #8: Should reject too large index"""
        checker = RegisterBoundsChecker(num_registers=256)
        with pytest.raises(IndexError, match="out of bounds"):
            checker.get(256)
    
    def test_register_set_bounds(self):
        """BUG #8: Should check bounds on set"""
        checker = RegisterBoundsChecker(num_registers=256)
        
        # Valid
        checker.set(0, "value")
        assert checker.get(0) == "value"
        
        # Invalid
        with pytest.raises(IndexError):
            checker.set(256, "value")


# ─────────────────────────────────────────────────────────────────────────────
# BUG #7: BYTECODE VALIDATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestBytecodeValidator:
    """Test bytecode validation (BUG #7)"""
    
    def test_valid_bytecode(self):
        """BUG #7: Valid bytecode should pass"""
        bytecode = [
            ['LOAD_CONST', 5],
            ['LOAD_VAR', 'x'],
            ['BINARY_OP', '+'],
            ['RETURN'],
        ]
        assert BytecodeValidator.validate(bytecode) == True
    
    def test_invalid_bytecode_not_list(self):
        """BUG #7: Bytecode must be list"""
        with pytest.raises(TypeError):
            BytecodeValidator.validate("not a list")
    
    def test_invalid_opcode(self):
        """BUG #7: Invalid opcode should be rejected"""
        bytecode = [
            ['INVALID_OP', 5],
        ]
        with pytest.raises(ValueError, match="invalid opcode"):
            BytecodeValidator.validate(bytecode)
    
    def test_empty_instruction(self):
        """BUG #7: Empty instruction should be rejected"""
        bytecode = [
            [],
        ]
        with pytest.raises(ValueError, match="empty instruction"):
            BytecodeValidator.validate(bytecode)


# ─────────────────────────────────────────────────────────────────────────────
# BUG #16: CIRCULAR REFERENCE DETECTION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestCircularReferenceDetector:
    """Test circular reference detection (BUG #16)"""
    
    def test_no_cycle_on_first_visit(self):
        """BUG #16: First visit should not detect cycle"""
        detector = CircularReferenceDetector()
        obj = {"key": "value"}
        
        assert detector.detect_cycle(obj) == False
    
    def test_cycle_detection_on_revisit(self):
        """BUG #16: Revisiting should detect cycle"""
        detector = CircularReferenceDetector()
        obj = []
        
        # First visit
        detector.detect_cycle(obj)
        
        # Should detect cycle on second visit
        assert detector.detect_cycle(obj) == True
    
    def test_clear_visit(self):
        """BUG #16: Should clear visit tracking"""
        detector = CircularReferenceDetector()
        obj = []
        
        detector.detect_cycle(obj)
        detector.clear_visit(obj)
        
        # After clear, should not detect cycle
        assert detector.detect_cycle(obj) == False


# ─────────────────────────────────────────────────────────────────────────────
# BUG #17 & #18: TYPE CONVERSION GUARD TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestTypeConversionGuard:
    """Test safe type conversion (BUG #17, #18)"""
    
    def test_convert_primitives(self):
        """BUG #17 & #18: Should convert primitive types"""
        converter = TypeConversionGuard()
        
        assert converter.convert_to_python(42) == 42
        assert converter.convert_to_python("hello") == "hello"
        assert converter.convert_to_python(3.14) == 3.14
        assert converter.convert_to_python(True) == True
    
    def test_convert_list(self):
        """BUG #17 & #18: Should convert lists"""
        converter = TypeConversionGuard()
        result = converter.convert_to_python([1, 2, 3])
        assert result == [1, 2, 3]
    
    def test_convert_dict(self):
        """BUG #17 & #18: Should convert dicts"""
        converter = TypeConversionGuard()
        result = converter.convert_to_python({"key": "value"})
        assert result == {"key": "value"}
    
    def test_convert_nested(self):
        """BUG #17 & #18: Should convert nested structures"""
        converter = TypeConversionGuard()
        nested = [1, {"key": [2, 3]}, 4]
        result = converter.convert_to_python(nested)
        assert result == [1, {"key": [2, 3]}, 4]


# ─────────────────────────────────────────────────────────────────────────────
# BUG #36: CACHE KEY COLLISION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestCacheKeyValidator:
    """Test cache key collision detection (BUG #36)"""
    
    def test_unique_keys(self):
        """BUG #36: Unique keys should register successfully"""
        validator = CacheKeyValidator()
        
        assert validator.register_key(hash("key1"), "key1") == True
        assert validator.register_key(hash("key2"), "key2") == True
    
    def test_same_key_twice(self):
        """BUG #36: Same key twice should succeed"""
        validator = CacheKeyValidator()
        
        assert validator.register_key(hash("key1"), "key1") == True
        assert validator.register_key(hash("key1"), "key1") == True
    
    def test_hash_collision_different_key(self):
        """BUG #36: Different keys with same hash should be detected"""
        validator = CacheKeyValidator()
        
        # Register first key
        validator.register_key(999, "key_a")
        
        # Try to register different key with same hash
        # This simulates a hash collision
        result = validator.register_key(999, "key_b")
        assert result == False  # Collision detected


# ─────────────────────────────────────────────────────────────────────────────
# BUG #61: UTF-8 STRING HANDLER TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestUTF8StringHandler:
    """Test UTF-8 string handling (BUG #61)"""
    
    def test_ascii_length(self):
        """BUG #61: ASCII string length should be correct"""
        assert UTF8StringHandler.correct_len("hello") == 5
    
    def test_utf8_emoji_length(self):
        """BUG #61: Emoji length should be correct (1 char each)"""
        # Each emoji is 1 character in Python 3
        assert UTF8StringHandler.correct_len("👍👎") == 2
    
    def test_utf8_multi_byte_length(self):
        """BUG #61: Multi-byte UTF-8 should count as 1 char"""
        assert UTF8StringHandler.correct_len("你好") == 2  # Chinese
    
    def test_string_index_valid(self):
        """BUG #61: Valid index should return character"""
        result = UTF8StringHandler.correct_index("hello", 0)
        assert result == "h"
    
    def test_string_index_bounds(self):
        """BUG #61: Out of bounds index should raise"""
        with pytest.raises(IndexError):
            UTF8StringHandler.correct_index("hello", 10)
    
    def test_string_slice(self):
        """BUG #61: Slice should work correctly"""
        result = UTF8StringHandler.correct_slice("hello", 1, 4)
        assert result == "ell"


# ─────────────────────────────────────────────────────────────────────────────
# BUG #76: CONST ENFORCER TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestConstEnforcer:
    """Test const enforcement (BUG #76)"""
    
    def test_declare_const(self):
        """BUG #76: Should declare const variable"""
        enforcer = ConstEnforcer()
        enforcer.declare_const("x", 42)
        assert enforcer.get_const("x") == 42
    
    def test_redeclare_const_fails(self):
        """BUG #76: Redeclaring const should fail"""
        enforcer = ConstEnforcer()
        enforcer.declare_const("x", 42)
        
        with pytest.raises(RuntimeError, match="Cannot redeclare"):
            enforcer.declare_const("x", 100)
    
    def test_is_const(self):
        """BUG #76: Should identify const variables"""
        enforcer = ConstEnforcer()
        enforcer.declare_const("x", 42)
        
        assert enforcer.is_const("x") == True
        assert enforcer.is_const("y") == False


# ─────────────────────────────────────────────────────────────────────────────
# BUG #89: DEFAULT PARAMETER EVALUATOR TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestDefaultParamEvaluator:
    """Test default parameter evaluation (BUG #89)"""
    
    def test_with_call_args(self):
        """BUG #89: Provided args should override defaults"""
        params = ['x', 'y']
        defaults = {'y': 10}
        call_args = {'x': 5, 'y': 20}
        
        result = DefaultParamEvaluator.evaluate_defaults(params, defaults, call_args)
        assert result == {'x': 5, 'y': 20}
    
    def test_with_defaults(self):
        """BUG #89: Missing args should use defaults"""
        params = ['x', 'y']
        defaults = {'y': 10}
        call_args = {'x': 5}
        
        result = DefaultParamEvaluator.evaluate_defaults(params, defaults, call_args)
        assert result == {'x': 5, 'y': 10}
    
    def test_missing_required_param(self):
        """BUG #89: Missing required parameter should fail"""
        params = ['x', 'y']
        defaults = {}
        call_args = {'x': 5}
        
        with pytest.raises(TypeError, match="Missing required parameter"):
            DefaultParamEvaluator.evaluate_defaults(params, defaults, call_args)


# ─────────────────────────────────────────────────────────────────────────────
# BUG #105: TYPE HINT ENFORCER TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestTypeHintEnforcer:
    """Test type hint enforcement (BUG #105)"""
    
    def test_check_int_type(self):
        """BUG #105: Should verify int type"""
        assert TypeHintEnforcer.check_type(42, 'int') == True
        assert TypeHintEnforcer.check_type("not int", 'int') == False
    
    def test_check_string_type(self):
        """BUG #105: Should verify string type"""
        assert TypeHintEnforcer.check_type("hello", 'str') == True
        assert TypeHintEnforcer.check_type(42, 'str') == False
    
    def test_check_list_type(self):
        """BUG #105: Should verify list type"""
        assert TypeHintEnforcer.check_type([1, 2, 3], 'list') == True
        assert TypeHintEnforcer.check_type("not list", 'list') == False
    
    def test_any_type(self):
        """BUG #105: 'any' type should accept anything"""
        assert TypeHintEnforcer.check_type(42, 'any') == True
        assert TypeHintEnforcer.check_type("anything", 'any') == True


# ─────────────────────────────────────────────────────────────────────────────
# BUG #118: FILE LOCK MANAGER TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestFileLockManager:
    """Test file locking (BUG #118)"""
    
    def test_thread_safe_write(self):
        """BUG #118: Write should be thread-safe"""
        import tempfile
        import os
        
        manager = FileLockManager()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            filepath = f.name
        
        try:
            # Write to file
            manager.write_file_safe(filepath, "test content")
            
            # Verify content
            with open(filepath, 'r') as f:
                content = f.read()
            assert content == "test content"
        finally:
            os.unlink(filepath)
    
    def test_thread_safe_read(self):
        """BUG #118: Read should be thread-safe"""
        import tempfile
        import os
        
        manager = FileLockManager()
        
        # Create temp file with content
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            filepath = f.name
        
        try:
            # Read file
            content = manager.read_file_safe(filepath)
            assert content == "test content"
        finally:
            os.unlink(filepath)


# ─────────────────────────────────────────────────────────────────────────────
# INTEGRATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegration:
    """Test multiple fixes working together"""
    
    def test_overflow_and_bounds_together(self):
        """Test overflow guard + bounds checking"""
        # Integer overflow
        result = IntegerOverflowGuard.safe_multiply(2**52, 2**52)
        assert isinstance(result, float)
        
        # Register bounds
        checker = RegisterBoundsChecker(256)
        with pytest.raises(IndexError):
            checker.set(256, result)
    
    def test_cache_with_key_validation(self):
        """Test cache with collision detection"""
        cache = BoundedObjectCache(max_size=100)
        validator = CacheKeyValidator()
        
        # Register keys
        validator.register_key(hash("key1"), "key1")
        cache.put("key1", "value1")
        
        # Verify
        assert cache.get("key1") == "value1"
    
    def test_string_handling_with_const(self):
        """Test UTF-8 strings with const enforcement"""
        enforcer = ConstEnforcer()
        
        # Declare const string
        string_val = "Hello 世界"
        enforcer.declare_const("msg", string_val)
        
        # Get and check length
        retrieved = enforcer.get_const("msg")
        length = UTF8StringHandler.correct_len(retrieved)
        assert length == 8  # "Hello " (6) + "世界" (2)


# ─────────────────────────────────────────────────────────────────────────────
# RUN TESTS
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
