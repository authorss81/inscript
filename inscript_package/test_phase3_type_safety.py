# Phase 3: Type Safety Bugs (BUG #16-18, #29)
# Tests for FFI and type conversion safety

import sys
sys.path.insert(0, '/home/claude/inscript_v380')

from BUG_FIXES_CRITICAL import (
    CircularReferenceDetector,
    TypeConversionGuard,
    UTF8StringHandler,
    CacheKeyValidator
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

def main():
    print("=" * 80)
    print("Phase 3: Type Safety Bugs (BUG #16-18, #29)")
    print("=" * 80)
    
    # BUG #16: Circular References
    print("\nBUG #16: Circular Reference Detection")
    print("-" * 80)
    
    def test_circular_ref_detection():
        detector = CircularReferenceDetector()
        obj = {"key": "value"}
        assert detector.detect_cycle(obj) == False
        assert detector.detect_cycle(obj) == True  # Revisit detects cycle
    
    def test_circular_ref_clear():
        detector = CircularReferenceDetector()
        obj = []
        detector.detect_cycle(obj)
        detector.clear_visit(obj)
        assert detector.detect_cycle(obj) == False
    
    test("Circular reference detection", test_circular_ref_detection)
    test("Clear visit tracking", test_circular_ref_clear)
    
    # BUG #17-18: Type Conversion Safety
    print("\nBUG #17-18: Type Conversion Safety")
    print("-" * 80)
    
    def test_primitive_conversion():
        converter = TypeConversionGuard()
        assert converter.convert_to_python(42) == 42
        assert converter.convert_to_python("hello") == "hello"
        assert converter.convert_to_python(3.14) == 3.14
    
    def test_list_conversion():
        converter = TypeConversionGuard()
        result = converter.convert_to_python([1, 2, 3])
        assert result == [1, 2, 3]
    
    def test_dict_conversion():
        converter = TypeConversionGuard()
        result = converter.convert_to_python({"a": 1, "b": 2})
        assert result == {"a": 1, "b": 2}
    
    def test_nested_conversion():
        converter = TypeConversionGuard()
        nested = [1, {"key": [2, 3]}, 4]
        result = converter.convert_to_python(nested)
        assert result == [1, {"key": [2, 3]}, 4]
    
    test("Primitive type conversion", test_primitive_conversion)
    test("List conversion", test_list_conversion)
    test("Dict conversion", test_dict_conversion)
    test("Nested structure conversion", test_nested_conversion)
    
    # BUG #29: UTF-8 String Extraction
    print("\nBUG #29: UTF-8 String Extraction Safety")
    print("-" * 80)
    
    def test_utf8_index():
        result = UTF8StringHandler.correct_index("hello", 1)
        assert result == "e"
    
    def test_utf8_slice():
        result = UTF8StringHandler.correct_slice("hello", 1, 4)
        assert result == "ell"
    
    def test_utf8_emoji():
        result = UTF8StringHandler.correct_len("👍")
        assert result == 1
    
    test("UTF-8 string indexing", test_utf8_index)
    test("UTF-8 string slicing", test_utf8_slice)
    test("UTF-8 emoji handling", test_utf8_emoji)
    
    # Summary
    print("\n" + "=" * 80)
    print(f"Phase 3 Results: {tests_passed}/{tests_passed + tests_failed} PASS")
    if tests_failed == 0:
        print("✅ All Type Safety fixes verified!")
    return 0 if tests_failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
