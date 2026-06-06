# -*- coding: utf-8 -*-
"""
InScript v3.8.0 - CRITICAL BUG FIX TESTS (Standalone Version)
Run with: python test_critical_bugfixes_standalone.py
"""

import sys
import traceback

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
    DefaultParamEvaluator,
    TypeHintEnforcer,
    FileLockManager,
)


# Test counter
tests_passed = 0
tests_failed = 0
tests_total = 0


def test(name, func):
    """Run a single test"""
    global tests_passed, tests_failed, tests_total
    tests_total += 1
    
    try:
        func()
        print(f"✅ PASS: {name}")
        tests_passed += 1
        return True
    except AssertionError as e:
        print(f"❌ FAIL: {name}")
        print(f"   Error: {e}")
        tests_failed += 1
        return False
    except Exception as e:
        print(f"❌ ERROR: {name}")
        print(f"   {type(e).__name__}: {e}")
        tests_failed += 1
        return False


# ─────────────────────────────────────────────────────────────────────────────
# BUG #1 & #6: STACK BOUNDS TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_stack_call_depth_bounded():
    """BUG #6: Call depth should be bounded"""
    checker = StackBoundsChecker(max_call_depth=5)
    for i in range(5):
        checker.push_call()
    
    # 6th call should fail
    try:
        checker.push_call()
        raise AssertionError("Should have raised RuntimeError")
    except RuntimeError:
        pass  # Expected


def test_stack_overflow_detection():
    """BUG #1: Stack overflow should be detected"""
    checker = StackBoundsChecker(max_stack_size=100)
    checker._stack_size = 100
    
    try:
        checker.check_stack_overflow()
        raise AssertionError("Should have raised RuntimeError")
    except RuntimeError:
        pass  # Expected


def test_call_depth_push_pop():
    """BUG #6: Push/pop call depth correctly"""
    checker = StackBoundsChecker(max_call_depth=10)
    
    assert checker._call_depth == 0
    checker.push_call()
    assert checker._call_depth == 1
    checker.pop_call()
    assert checker._call_depth == 0


# ─────────────────────────────────────────────────────────────────────────────
# BUG #2 & #53: INTEGER OVERFLOW TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_overflow_small_numbers():
    """BUG #2: Small numbers should not overflow"""
    result = IntegerOverflowGuard.check_overflow(1000)
    assert result == 1000
    assert isinstance(result, int)


def test_overflow_large_numbers():
    """BUG #2: Large numbers should convert to float"""
    large_int = 2 ** 54
    result = IntegerOverflowGuard.check_overflow(large_int)
    assert isinstance(result, float)


def test_safe_multiply():
    """BUG #2: Multiplication should be safe"""
    result = IntegerOverflowGuard.safe_multiply(100, 100)
    assert result == 10000


def test_safe_multiply_overflow():
    """BUG #2: Large multiplication should convert to float"""
    large = 2 ** 52
    result = IntegerOverflowGuard.safe_multiply(large, large)
    assert isinstance(result, float)


def test_safe_power_small():
    """BUG #2: Small power should work"""
    result = IntegerOverflowGuard.safe_power(2, 3)
    assert result == 8


def test_safe_power_overflow():
    """BUG #2: Large power should raise OverflowError"""
    try:
        IntegerOverflowGuard.safe_power(10000, 10000)  # Much larger
        raise AssertionError("Should have raised OverflowError")
    except OverflowError:
        pass  # Expected


def test_safe_add():
    """BUG #2: Addition should be safe"""
    result = IntegerOverflowGuard.safe_add(100, 200)
    assert result == 300


# ─────────────────────────────────────────────────────────────────────────────
# BUG #4: BOUNDED OBJECT CACHE TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_cache_size_limit():
    """BUG #4: Cache should not exceed max size"""
    cache = BoundedObjectCache(max_size=5)
    
    for i in range(10):
        cache.put(f"key_{i}", f"value_{i}")
    
    assert cache.size() <= 5


def test_cache_get_put():
    """BUG #4: Cache should store and retrieve items"""
    cache = BoundedObjectCache(max_size=100)
    
    cache.put("key1", "value1")
    assert cache.get("key1") == "value1"


def test_cache_clear():
    """BUG #4: Cache should clear properly"""
    cache = BoundedObjectCache(max_size=100)
    
    cache.put("key1", "value1")
    assert cache.size() == 1
    
    cache.clear()
    assert cache.size() == 0


def test_cache_lru_eviction():
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

def test_register_get_valid():
    """BUG #8: Should get valid register"""
    checker = RegisterBoundsChecker(num_registers=256)
    checker.set(0, "value")
    assert checker.get(0) == "value"


def test_register_get_out_of_bounds_negative():
    """BUG #5 & #8: Should reject negative index"""
    checker = RegisterBoundsChecker(num_registers=256)
    
    try:
        checker.get(-1)
        raise AssertionError("Should have raised IndexError")
    except IndexError:
        pass  # Expected


def test_register_get_out_of_bounds_too_large():
    """BUG #5 & #8: Should reject too large index"""
    checker = RegisterBoundsChecker(num_registers=256)
    
    try:
        checker.get(256)
        raise AssertionError("Should have raised IndexError")
    except IndexError:
        pass  # Expected


def test_register_set_bounds():
    """BUG #8: Should check bounds on set"""
    checker = RegisterBoundsChecker(num_registers=256)
    
    checker.set(0, "value")
    assert checker.get(0) == "value"
    
    try:
        checker.set(256, "value")
        raise AssertionError("Should have raised IndexError")
    except IndexError:
        pass  # Expected


# ─────────────────────────────────────────────────────────────────────────────
# BUG #7: BYTECODE VALIDATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_valid_bytecode():
    """BUG #7: Valid bytecode should pass"""
    bytecode = [
        ['LOAD_CONST', 5],
        ['LOAD_VAR', 'x'],
        ['BINARY_OP', '+'],
        ['RETURN'],
    ]
    assert BytecodeValidator.validate(bytecode) == True


def test_invalid_bytecode_not_list():
    """BUG #7: Bytecode must be list"""
    try:
        BytecodeValidator.validate("not a list")
        raise AssertionError("Should have raised TypeError")
    except TypeError:
        pass  # Expected


def test_invalid_opcode():
    """BUG #7: Invalid opcode should be rejected"""
    bytecode = [
        ['INVALID_OP', 5],
    ]
    try:
        BytecodeValidator.validate(bytecode)
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass  # Expected


def test_empty_instruction():
    """BUG #7: Empty instruction should be rejected"""
    bytecode = [[]]
    try:
        BytecodeValidator.validate(bytecode)
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass  # Expected


# ─────────────────────────────────────────────────────────────────────────────
# BUG #16: CIRCULAR REFERENCE DETECTION TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_no_cycle_on_first_visit():
    """BUG #16: First visit should not detect cycle"""
    detector = CircularReferenceDetector()
    obj = {"key": "value"}
    
    assert detector.detect_cycle(obj) == False


def test_cycle_detection_on_revisit():
    """BUG #16: Revisiting should detect cycle"""
    detector = CircularReferenceDetector()
    obj = []
    
    detector.detect_cycle(obj)
    assert detector.detect_cycle(obj) == True


def test_clear_visit():
    """BUG #16: Should clear visit tracking"""
    detector = CircularReferenceDetector()
    obj = []
    
    detector.detect_cycle(obj)
    detector.clear_visit(obj)
    
    assert detector.detect_cycle(obj) == False


# ─────────────────────────────────────────────────────────────────────────────
# BUG #17 & #18: TYPE CONVERSION GUARD TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_convert_primitives():
    """BUG #17 & #18: Should convert primitive types"""
    converter = TypeConversionGuard()
    
    assert converter.convert_to_python(42) == 42
    assert converter.convert_to_python("hello") == "hello"
    assert converter.convert_to_python(3.14) == 3.14
    assert converter.convert_to_python(True) == True


def test_convert_list():
    """BUG #17 & #18: Should convert lists"""
    converter = TypeConversionGuard()
    result = converter.convert_to_python([1, 2, 3])
    assert result == [1, 2, 3]


def test_convert_dict():
    """BUG #17 & #18: Should convert dicts"""
    converter = TypeConversionGuard()
    result = converter.convert_to_python({"key": "value"})
    assert result == {"key": "value"}


# ─────────────────────────────────────────────────────────────────────────────
# BUG #36: CACHE KEY COLLISION TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_unique_keys():
    """BUG #36: Unique keys should register successfully"""
    validator = CacheKeyValidator()
    
    assert validator.register_key(hash("key1"), "key1") == True
    assert validator.register_key(hash("key2"), "key2") == True


def test_same_key_twice():
    """BUG #36: Same key twice should succeed"""
    validator = CacheKeyValidator()
    
    assert validator.register_key(hash("key1"), "key1") == True
    assert validator.register_key(hash("key1"), "key1") == True


def test_hash_collision():
    """BUG #36: Different keys with same hash should be detected"""
    validator = CacheKeyValidator()
    
    validator.register_key(999, "key_a")
    result = validator.register_key(999, "key_b")
    assert result == False


# ─────────────────────────────────────────────────────────────────────────────
# BUG #61: UTF-8 STRING HANDLER TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_ascii_length():
    """BUG #61: ASCII string length should be correct"""
    assert UTF8StringHandler.correct_len("hello") == 5


def test_utf8_emoji_length():
    """BUG #61: Emoji length should be correct"""
    assert UTF8StringHandler.correct_len("👍👎") == 2


def test_utf8_multibyte_length():
    """BUG #61: Multi-byte UTF-8 should count as 1 char"""
    assert UTF8StringHandler.correct_len("你好") == 2


def test_string_index_valid():
    """BUG #61: Valid index should return character"""
    result = UTF8StringHandler.correct_index("hello", 0)
    assert result == "h"


def test_string_index_bounds():
    """BUG #61: Out of bounds index should raise"""
    try:
        UTF8StringHandler.correct_index("hello", 10)
        raise AssertionError("Should have raised IndexError")
    except IndexError:
        pass  # Expected


def test_string_slice():
    """BUG #61: Slice should work correctly"""
    result = UTF8StringHandler.correct_slice("hello", 1, 4)
    assert result == "ell"


# ─────────────────────────────────────────────────────────────────────────────
# BUG #76: CONST ENFORCER TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_declare_const():
    """BUG #76: Should declare const variable"""
    enforcer = ConstEnforcer()
    enforcer.declare_const("x", 42)
    assert enforcer.get_const("x") == 42


def test_redeclare_const_fails():
    """BUG #76: Redeclaring const should fail"""
    enforcer = ConstEnforcer()
    enforcer.declare_const("x", 42)
    
    try:
        enforcer.declare_const("x", 100)
        raise AssertionError("Should have raised RuntimeError")
    except RuntimeError:
        pass  # Expected


def test_is_const():
    """BUG #76: Should identify const variables"""
    enforcer = ConstEnforcer()
    enforcer.declare_const("x", 42)
    
    assert enforcer.is_const("x") == True
    assert enforcer.is_const("y") == False


# ─────────────────────────────────────────────────────────────────────────────
# BUG #89: DEFAULT PARAMETER EVALUATOR TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_with_call_args():
    """BUG #89: Provided args should override defaults"""
    params = ['x', 'y']
    defaults = {'y': 10}
    call_args = {'x': 5, 'y': 20}
    
    result = DefaultParamEvaluator.evaluate_defaults(params, defaults, call_args)
    assert result == {'x': 5, 'y': 20}


def test_with_defaults():
    """BUG #89: Missing args should use defaults"""
    params = ['x', 'y']
    defaults = {'y': 10}
    call_args = {'x': 5}
    
    result = DefaultParamEvaluator.evaluate_defaults(params, defaults, call_args)
    assert result == {'x': 5, 'y': 10}


def test_missing_required_param():
    """BUG #89: Missing required parameter should fail"""
    params = ['x', 'y']
    defaults = {}
    call_args = {'x': 5}
    
    try:
        DefaultParamEvaluator.evaluate_defaults(params, defaults, call_args)
        raise AssertionError("Should have raised TypeError")
    except TypeError:
        pass  # Expected


# ─────────────────────────────────────────────────────────────────────────────
# BUG #105: TYPE HINT ENFORCER TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_check_int_type():
    """BUG #105: Should verify int type"""
    assert TypeHintEnforcer.check_type(42, 'int') == True
    assert TypeHintEnforcer.check_type("not int", 'int') == False


def test_check_string_type():
    """BUG #105: Should verify string type"""
    assert TypeHintEnforcer.check_type("hello", 'str') == True
    assert TypeHintEnforcer.check_type(42, 'str') == False


def test_check_list_type():
    """BUG #105: Should verify list type"""
    assert TypeHintEnforcer.check_type([1, 2, 3], 'list') == True
    assert TypeHintEnforcer.check_type("not list", 'list') == False


def test_any_type():
    """BUG #105: 'any' type should accept anything"""
    assert TypeHintEnforcer.check_type(42, 'any') == True
    assert TypeHintEnforcer.check_type("anything", 'any') == True


# ─────────────────────────────────────────────────────────────────────────────
# INTEGRATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_integration_overflow_and_bounds():
    """Test overflow guard + bounds checking"""
    result = IntegerOverflowGuard.safe_multiply(2**52, 2**52)
    assert isinstance(result, float)
    
    checker = RegisterBoundsChecker(256)
    try:
        checker.set(256, result)
        raise AssertionError("Should have raised IndexError")
    except IndexError:
        pass  # Expected


def test_integration_cache_with_validation():
    """Test cache with collision detection"""
    cache = BoundedObjectCache(max_size=100)
    validator = CacheKeyValidator()
    
    validator.register_key(hash("key1"), "key1")
    cache.put("key1", "value1")
    
    assert cache.get("key1") == "value1"


def test_integration_string_with_const():
    """Test UTF-8 strings with const enforcement"""
    enforcer = ConstEnforcer()
    
    string_val = "Hello 世界"
    enforcer.declare_const("msg", string_val)
    
    retrieved = enforcer.get_const("msg")
    length = UTF8StringHandler.correct_len(retrieved)
    assert length == 8


# ─────────────────────────────────────────────────────────────────────────────
# MAIN TEST RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def main():
    """Run all tests"""
    global tests_passed, tests_failed, tests_total
    
    print("=" * 80)
    print("InScript v3.8.0 - CRITICAL BUG FIX TESTS")
    print("=" * 80)
    print()
    
    # BUG #1 & #6: Stack Bounds
    print("BUG #1 & #6: Stack Bounds Tests")
    print("-" * 80)
    test("Stack call depth bounded", test_stack_call_depth_bounded)
    test("Stack overflow detection", test_stack_overflow_detection)
    test("Call depth push/pop", test_call_depth_push_pop)
    print()
    
    # BUG #2 & #53: Integer Overflow
    print("BUG #2 & #53: Integer Overflow Tests")
    print("-" * 80)
    test("Overflow small numbers", test_overflow_small_numbers)
    test("Overflow large numbers", test_overflow_large_numbers)
    test("Safe multiply", test_safe_multiply)
    test("Safe multiply overflow", test_safe_multiply_overflow)
    test("Safe power small", test_safe_power_small)
    test("Safe power overflow", test_safe_power_overflow)
    test("Safe add", test_safe_add)
    print()
    
    # BUG #4: Bounded Cache
    print("BUG #4: Bounded Object Cache Tests")
    print("-" * 80)
    test("Cache size limit", test_cache_size_limit)
    test("Cache get/put", test_cache_get_put)
    test("Cache clear", test_cache_clear)
    test("Cache LRU eviction", test_cache_lru_eviction)
    print()
    
    # BUG #5 & #8: Register Bounds
    print("BUG #5 & #8: Register Bounds Tests")
    print("-" * 80)
    test("Register get valid", test_register_get_valid)
    test("Register get negative", test_register_get_out_of_bounds_negative)
    test("Register get too large", test_register_get_out_of_bounds_too_large)
    test("Register set bounds", test_register_set_bounds)
    print()
    
    # BUG #7: Bytecode Validation
    print("BUG #7: Bytecode Validation Tests")
    print("-" * 80)
    test("Valid bytecode", test_valid_bytecode)
    test("Invalid bytecode not list", test_invalid_bytecode_not_list)
    test("Invalid opcode", test_invalid_opcode)
    test("Empty instruction", test_empty_instruction)
    print()
    
    # BUG #16: Circular Reference
    print("BUG #16: Circular Reference Detection Tests")
    print("-" * 80)
    test("No cycle on first visit", test_no_cycle_on_first_visit)
    test("Cycle detection on revisit", test_cycle_detection_on_revisit)
    test("Clear visit", test_clear_visit)
    print()
    
    # BUG #17 & #18: Type Conversion
    print("BUG #17 & #18: Type Conversion Guard Tests")
    print("-" * 80)
    test("Convert primitives", test_convert_primitives)
    test("Convert list", test_convert_list)
    test("Convert dict", test_convert_dict)
    print()
    
    # BUG #36: Cache Key Collision
    print("BUG #36: Cache Key Collision Tests")
    print("-" * 80)
    test("Unique keys", test_unique_keys)
    test("Same key twice", test_same_key_twice)
    test("Hash collision", test_hash_collision)
    print()
    
    # BUG #61: UTF-8 String Handling
    print("BUG #61: UTF-8 String Handler Tests")
    print("-" * 80)
    test("ASCII length", test_ascii_length)
    test("UTF-8 emoji length", test_utf8_emoji_length)
    test("UTF-8 multibyte length", test_utf8_multibyte_length)
    test("String index valid", test_string_index_valid)
    test("String index bounds", test_string_index_bounds)
    test("String slice", test_string_slice)
    print()
    
    # BUG #76: Const Enforcer
    print("BUG #76: Const Enforcer Tests")
    print("-" * 80)
    test("Declare const", test_declare_const)
    test("Redeclare const fails", test_redeclare_const_fails)
    test("Is const", test_is_const)
    print()
    
    # BUG #89: Default Parameter Evaluator
    print("BUG #89: Default Parameter Evaluator Tests")
    print("-" * 80)
    test("With call args", test_with_call_args)
    test("With defaults", test_with_defaults)
    test("Missing required param", test_missing_required_param)
    print()
    
    # BUG #105: Type Hint Enforcer
    print("BUG #105: Type Hint Enforcer Tests")
    print("-" * 80)
    test("Check int type", test_check_int_type)
    test("Check string type", test_check_string_type)
    test("Check list type", test_check_list_type)
    test("Any type", test_any_type)
    print()
    
    # Integration Tests
    print("Integration Tests")
    print("-" * 80)
    test("Overflow and bounds together", test_integration_overflow_and_bounds)
    test("Cache with validation", test_integration_cache_with_validation)
    test("String with const", test_integration_string_with_const)
    print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {tests_total}")
    print(f"Passed: {tests_passed} ✅")
    print(f"Failed: {tests_failed} ❌")
    
    if tests_failed == 0:
        print("\n🎉 ALL TESTS PASSED! All bug fixes are working correctly!")
        return 0
    else:
        print(f"\n⚠️  {tests_failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
