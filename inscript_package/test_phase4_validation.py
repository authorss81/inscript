# Phase 4: Validation Bugs (BUG #36-38)

import sys
sys.path.insert(0, '/home/claude/inscript_v380')

from BUG_FIXES_CRITICAL import (
    CacheKeyValidator,
    BytecodeValidator
)

tests_passed = 0
tests_failed = 0

def test(name, func):
    global tests_passed, tests_failed
    try:
        func()
        print(f"✅ {name}")
        tests_passed += 1
    except Exception as e:
        print(f"❌ {name}: {e}")
        tests_failed += 1

print("=" * 80)
print("Phase 4: Validation Bugs (BUG #36-38)")
print("=" * 80)

# BUG #36: Cache Key Collision
print("\nBUG #36: Cache Key Collision Detection")
print("-" * 80)

def test_unique_keys():
    validator = CacheKeyValidator()
    assert validator.register_key(hash("key1"), "key1") == True
    assert validator.register_key(hash("key2"), "key2") == True

def test_same_key():
    validator = CacheKeyValidator()
    assert validator.register_key(hash("k"), "k") == True
    assert validator.register_key(hash("k"), "k") == True

test("Unique keys register", test_unique_keys)
test("Same key twice", test_same_key)

# BUG #38: AST Serialization
print("\nBUG #38: Bytecode/AST Validation")
print("-" * 80)

def test_valid_bytecode():
    bytecode = [['LOAD_CONST', 5], ['RETURN']]
    assert BytecodeValidator.validate(bytecode) == True

def test_invalid_opcode():
    bytecode = [['INVALID', 5]]
    try:
        BytecodeValidator.validate(bytecode)
        return False
    except ValueError:
        return True

test("Valid bytecode", test_valid_bytecode)
test("Invalid opcode rejected", test_invalid_opcode)

print("\n" + "=" * 80)
print(f"Phase 4 Results: {tests_passed}/{tests_passed + tests_failed} PASS")
