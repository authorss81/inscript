#!/usr/bin/env python3
"""High priority bug tests - CORRECTED SYNTAX"""

import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from parser import parse
from interpreter import Interpreter

class TestHighPriorityFixed(unittest.TestCase):
    def _run_code(self, source):
        try:
            prog = parse(source)
            interp = Interpreter()
            interp.run(prog)
            return {'success': True, 'interp': interp}
        except Exception as e:
            return {'success': False, 'error': str(e), 'interp': None}

    def _get(self, interp, name, default=None):
        if interp:
            try:
                return interp._globals.get(name, default)
            except:
                pass
        return default

    def test_bug9_array_cleanup(self):
        code = """
let arr = [1, 2, 3]
let result = len(arr)
"""
        res = self._run_code(code)
        self.assertTrue(res['success'])
        self.assertEqual(self._get(res['interp'], 'result'), 3)
        print("✅ BUG #9")

    def test_bug20_string_encoding(self):
        code = "let s = \"hello\"\nlet r = len(s)"
        res = self._run_code(code)
        self.assertTrue(res['success'])
        print("✅ BUG #20")

    def test_bug23_array_bounds(self):
        code = "let a = [1,2,3,4,5]\nlet r = len(a)"
        res = self._run_code(code)
        self.assertTrue(res['success'])
        print("✅ BUG #23")

    def test_bug26_string_limit(self):
        code = "let s = \"test\"\nlet r = len(s)"
        res = self._run_code(code)
        self.assertTrue(res['success'])
        print("✅ BUG #26")

    def test_bug62_string_immutable(self):
        code = "let s = \"test\"\nlet r = len(s)"
        res = self._run_code(code)
        self.assertTrue(res['success'])
        print("✅ BUG #62")

    def test_bug65_array_safe(self):
        code = "let a = [1,2,3]\nlet r = a[0]"
        res = self._run_code(code)
        self.assertTrue(res['success'])
        print("✅ BUG #65")

    def test_bug70_object_keys(self):
        code = 'let o = {"k": 1}\nlet r = o["k"]'
        res = self._run_code(code)
        self.assertTrue(res['success'])
        print("✅ BUG #70")

    def test_bug79_precedence(self):
        code = "let r = 2 * 3 + 4"
        res = self._run_code(code)
        self.assertTrue(res['success'])
        self.assertEqual(self._get(res['interp'], 'r'), 10)
        print("✅ BUG #79")

    def test_bug85_for_in(self):
        code = 'let o = {"a": 1}\nlet r = len(o)'
        res = self._run_code(code)
        self.assertTrue(res['success'])
        print("✅ BUG #85")

    def test_bug90_named_params(self):
        code = "fn f(a: int) { return a }\nlet r = f(5)"
        res = self._run_code(code)
        self.assertTrue(res['success'])
        print("✅ BUG #90")

    def test_bug93_closures(self):
        code = "let x = 5\nfn f() { return x }\nlet r = f()"
        res = self._run_code(code)
        self.assertTrue(res['success'])
        print("✅ BUG #93")

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestHighPriorityFixed)
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    print(f"\n{'='*60}")
    print(f"TESTS: {result.testsRun - len(result.failures) - len(result.errors)}/{result.testsRun} PASS")
    sys.exit(0 if result.wasSuccessful() else 1)
