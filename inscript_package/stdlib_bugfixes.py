"""
InScript v3.8.2 - Bug Fixes Extended Stdlib
Provides all implementations for the 39 remaining bugs

This module registers with the stdlib system and makes all fixes
available to the interpreter.
"""

from BUG_FIXES_REMAINING_39 import *
import stdlib as _stdlib_base

# ============================================================================
# PART 1: LANGUAGE FEATURES (BUG #58, #72, #74, #77, #78, #87, #88, #92, #94, #96)
# ============================================================================

_language_features = {
    # Type System
    "Decimal": Decimal,
    "GenericType": GenericType,
    "UnionType": UnionType,
    
    # Object Operations
    "freeze": lambda obj: (FrozenObject(obj).freeze(), obj)[-1],
    "isFrozen": lambda obj: getattr(obj, '_frozen', False),
    "spread": spread_object,
    "spreadArray": spread_array,
    
    # Control Flow
    "doWhile": execute_do_while,
    "labeledBreak": labeled_break,
    "labeledContinue": labeled_continue,
    
    # OOP
    "OverloadedFunction": OverloadedFunction,
    "ClassWithSuper": ClassWithSuper,
    "MultipleInheritanceBase": MultipleInheritanceBase,
    
    # Decorators
    "static": static_method,
    "visible": VisibleMethod,
    "private": PrivateMethod,
    "protected": ProtectedMethod,
    "property": Property,
}

# ============================================================================
# PART 2: ADVANCED FEATURES (BUG #95, #97, #98, #100, #101, #102, #103, #104, #106, #107)
# ============================================================================

_advanced_features = {
    # Async/Promises
    "Promise": Promise,
    "AsyncErrorHandler": AsyncErrorHandler,
    "FinallyGuarantee": FinallyGuarantee,
    
    # Error Types
    "TypedError": TypedError,
    "TypeError": TypeError_Inscript,
    "ValueError": ValueError_Inscript,
    "RuntimeError": RuntimeError_Inscript,
    
    # Debugging
    "DetailedStackTrace": DetailedStackTrace,
    "getStackTrace": DetailedStackTrace.get_detailed_trace,
    
    # Type System Extensions
    "GenericConstraint": GenericType,
    "UnionOf": UnionType,
}

# ============================================================================
# PART 3: STDLIB FUNCTIONS (BUG #109, #110, #111, #112, #113, #114, #115, #116, #117, #119, #120, #121, #122)
# ============================================================================

_stdlib_functions = {
    # String Functions
    "stringReplace": string_replace,
    "Regex": RegexPattern,
    "RegexPattern": RegexPattern,
    
    # Math Functions
    "SecureRandom": SecureRandom,
    "secureRandom": lambda: SecureRandom.random(),
    "secureRandomInt": SecureRandom.randint,
    "safePow": safe_pow,
    "preciseSin": precise_sin,
    "preciseCos": precise_cos,
    "preciseTan": precise_tan,
    
    # Array Functions
    "arrayForEach": array_foreach,
    "LazyMap": LazyMap,
    "arrayReduce": array_reduce,
    
    # Path & File Functions
    "normalizePath": normalize_path,
    "readFileWithEncoding": read_file_with_encoding,
    "writeFileWithEncoding": write_file_with_encoding,
    
    # JSON Functions
    "jsonStringifyDeterministic": json_stringify_deterministic,
    "jsonParseValidated": json_parse_validated,
    
    # Data Structure Analysis
    "CircularReferenceDetector": CircularReferenceDetector,
    "hasCircularReference": CircularReferenceDetector.has_circular_reference,
}

# ============================================================================
# PART 4: IDE/TOOLS (BUG #123, #124, #125, #126-132)
# ============================================================================

_ide_tools = {
    "DefinitionLocator": DefinitionLocator,
    "Autocomplete": Autocomplete,
    "RenameRefactorer": RenameRefactorer,
    "DebuggerBreakpoint": DebuggerBreakpoint,
    "StackTraceAnalyzer": StackTraceAnalyzer,
    "SimpleProfiler": SimpleProfiler,
}

# ============================================================================
# COMBINED MODULE EXPORTS
# ============================================================================

bugfixes = {
    **_language_features,
    **_advanced_features,
    **_stdlib_functions,
    **_ide_tools,
}

# ============================================================================
# REGISTER WITH STDLIB SYSTEM
# ============================================================================

_stdlib_base.register_module("bugfixes", bugfixes)
_stdlib_base.register_module("lang", _language_features)
_stdlib_base.register_module("async", {
    "Promise": Promise,
    "AsyncErrorHandler": AsyncErrorHandler,
    "FinallyGuarantee": FinallyGuarantee,
})
_stdlib_base.register_module("types", {
    "TypedError": TypedError,
    "TypeError": TypeError_Inscript,
    "ValueError": ValueError_Inscript,
    "RuntimeError": RuntimeError_Inscript,
    "UnionType": UnionType,
    "GenericType": GenericType,
})
# v3.9.1 fix: merge into the existing string module instead of replacing it.
# register_module() overwrites the whole dict, destroying the 30 functions
# already registered in stdlib.py (upper, trim_start, split_lines, etc.).
_stdlib_base._MODULES["string"].update({
    "replace": string_replace,
    "Regex": RegexPattern,
})
_stdlib_base.register_module("math_ext", {
    "SecureRandom": SecureRandom,
    "safePow": safe_pow,
    "preciseSin": precise_sin,
    "preciseCos": precise_cos,
    "preciseTan": precise_tan,
})
_stdlib_base.register_module("array_ext", {
    "forEach": array_foreach,
    "LazyMap": LazyMap,
    "reduce": array_reduce,
})
_stdlib_base.register_module("file_ext", {
    "normalizePath": normalize_path,
    "readWithEncoding": read_file_with_encoding,
    "writeWithEncoding": write_file_with_encoding,
})
_stdlib_base.register_module("json_ext", {
    "stringifyDeterministic": json_stringify_deterministic,
    "parseValidated": json_parse_validated,
})
_stdlib_base.register_module("debug", {
    "DetailedStackTrace": DetailedStackTrace,
    "StackTraceAnalyzer": StackTraceAnalyzer,
    "DebuggerBreakpoint": DebuggerBreakpoint,
    "SimpleProfiler": SimpleProfiler,
})

# ============================================================================
# ENHANCED GLOBAL BUILTINS
# ============================================================================

ENHANCED_BUILTINS = {
    # Add to interpreter.globals
    "Decimal": Decimal,
    "Promise": Promise,
    "Regex": RegexPattern,
    "hasCircularReference": CircularReferenceDetector.has_circular_reference,
    "normalizePath": normalize_path,
    "secureRandom": lambda: SecureRandom.random(),
}

# ============================================================================
# INTEGRATION FUNCTION
# ============================================================================

def integrate_with_interpreter(interpreter):
    """Add all bug fixes to interpreter globals"""
    if hasattr(interpreter, 'globals'):
        for name, value in ENHANCED_BUILTINS.items():
            interpreter.globals[name] = value
        print(f"✅ Integrated {len(ENHANCED_BUILTINS)} bug fixes into interpreter globals")
    return interpreter

if __name__ == "__main__":
    print("✅ stdlib_bugfixes module loaded")
    print(f"   Language Features: {len(_language_features)}")
    print(f"   Advanced Features: {len(_advanced_features)}")
    print(f"   Stdlib Functions: {len(_stdlib_functions)}")
    print(f"   IDE/Tools: {len(_ide_tools)}")
    print(f"   Total: {len(bugfixes)} features")
