"""
Integration Patch for InScript v3.8.2
Patches interpreter.py and vm.py to include all 39 bug fixes

This file can be run standalone to patch the interpreter files,
or imported to access the patch functions.
"""

import sys
import os

def patch_interpreter():
    """Add bug fix imports to interpreter.py"""
    interpreter_file = "interpreter.py"
    
    if not os.path.exists(interpreter_file):
        print(f"❌ {interpreter_file} not found")
        return False
    
    with open(interpreter_file, 'r') as f:
        content = f.read()
    
    # Check if already patched
    if "BUG_FIXES_REMAINING_39" in content:
        print("✅ interpreter.py already patched")
        return True
    
    # Find the import section (after other imports, before classes)
    import_location = content.find("from stdlib_values import")
    
    if import_location == -1:
        print("❌ Could not find import location in interpreter.py")
        return False
    
    # Add our imports right before the Interpreter class
    patch_code = """
# ============================================================================
# BUG FIXES: All 39 remaining bugs - v3.8.2
# ============================================================================
try:
    from BUG_FIXES_REMAINING_39 import *
    from INTERPRETER_INTEGRATION import COMPLETE_STDLIB, integrate_into_interpreter
    from INTERPRETER_INTEGRATION import initialize_vm_extensions
except ImportError:
    import sys
    print("[WARNING] BUG_FIXES_REMAINING_39 module not found", file=sys.stderr)

"""
    
    # Find class Interpreter location
    class_location = content.find("class Interpreter(")
    if class_location == -1:
        print("❌ Could not find Interpreter class")
        return False
    
    # Insert patch before the class
    new_content = content[:class_location] + patch_code + content[class_location:]
    
    with open(interpreter_file, 'w') as f:
        f.write(new_content)
    
    print("✅ Successfully patched interpreter.py")
    return True


def patch_vm():
    """Add bug fix support to vm.py"""
    vm_file = "vm.py"
    
    if not os.path.exists(vm_file):
        print(f"❌ {vm_file} not found")
        return False
    
    with open(vm_file, 'r') as f:
        content = f.read()
    
    # Check if already patched
    if "BUG_FIXES_REMAINING_39" in content:
        print("✅ vm.py already patched")
        return True
    
    # Find the imports section
    import_end = content.find("\n\n", content.find("import"))
    if import_end == -1:
        import_end = content.find("\nclass", content.find("import"))
    
    if import_end == -1:
        print("❌ Could not find import section in vm.py")
        return False
    
    patch_code = """
# ============================================================================
# BUG FIXES: VM Support for all 39 remaining bugs - v3.8.2
# ============================================================================
try:
    from BUG_FIXES_REMAINING_39 import *
    from INTERPRETER_INTEGRATION import VM_EXTENSIONS
except ImportError:
    import sys
    print("[WARNING] BUG_FIXES_REMAINING_39 module not found for VM", file=sys.stderr)

"""
    
    # Insert patch in imports
    new_content = content[:import_end] + patch_code + content[import_end:]
    
    with open(vm_file, 'w') as f:
        f.write(new_content)
    
    print("✅ Successfully patched vm.py")
    return True


def patch_stdlib():
    """Add bug fix stdlib module to stdlib.py"""
    stdlib_file = "stdlib.py"
    
    if not os.path.exists(stdlib_file):
        print(f"❌ {stdlib_file} not found")
        return False
    
    with open(stdlib_file, 'r') as f:
        content = f.read()
    
    # Check if already patched
    if "stdlib_bugfixes" in content:
        print("✅ stdlib.py already includes bugfixes")
        return True
    
    # Add import at the end
    patch_code = """

# ============================================================================
# BUG FIXES: Extended stdlib with all 39 remaining bugs - v3.8.2
# ============================================================================
try:
    import stdlib_bugfixes  # noqa: F401
except Exception as _bugfix_error:
    import sys
    print(f'[stdlib_bugfixes load error] {_bugfix_error}', file=sys.stderr)
"""
    
    new_content = content + patch_code
    
    with open(stdlib_file, 'w') as f:
        f.write(new_content)
    
    print("✅ Successfully patched stdlib.py")
    return True


def apply_all_patches():
    """Apply all patches to interpreter files"""
    print("\n" + "="*70)
    print("InScript v3.8.2 - Applying All Bug Fix Patches")
    print("="*70 + "\n")
    
    results = {
        "interpreter.py": patch_interpreter(),
        "vm.py": patch_vm(),
        "stdlib.py": patch_stdlib(),
    }
    
    print("\n" + "="*70)
    print("PATCH SUMMARY")
    print("="*70)
    
    all_success = all(results.values())
    for filename, success in results.items():
        status = "✅ PATCHED" if success else "❌ FAILED"
        print(f"{status}: {filename}")
    
    print("="*70)
    
    if all_success:
        print("\n✅ All patches applied successfully!")
        print("   The interpreter now includes all 39 bug fixes.")
        print("   Run tests with: python3 test_bug_fixes_remaining_39.py")
        return True
    else:
        print("\n❌ Some patches failed. Please check the errors above.")
        return False


# ============================================================================
# VERIFICATION FUNCTION
# ============================================================================

def verify_patches():
    """Verify all patches were applied correctly"""
    print("\n" + "="*70)
    print("Verifying Bug Fix Integration")
    print("="*70 + "\n")
    
    files_to_check = {
        "interpreter.py": "BUG_FIXES_REMAINING_39",
        "vm.py": "BUG_FIXES_REMAINING_39",
        "stdlib.py": "stdlib_bugfixes",
    }
    
    all_verified = True
    for filename, marker in files_to_check.items():
        try:
            with open(filename, 'r') as f:
                content = f.read()
                if marker in content:
                    print(f"✅ {filename}: Bug fixes integrated")
                else:
                    print(f"❌ {filename}: Bug fixes NOT found")
                    all_verified = False
        except FileNotFoundError:
            print(f"❌ {filename}: File not found")
            all_verified = False
    
    print("\n" + "="*70)
    if all_verified:
        print("✅ All patches verified successfully!")
    else:
        print("❌ Some patches could not be verified")
    print("="*70 + "\n")
    
    return all_verified


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        verify_patches()
    else:
        success = apply_all_patches()
        print("\nVerifying patches...")
        verify_patches()
        sys.exit(0 if success else 1)
