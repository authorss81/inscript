import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from repl import EnhancedREPL
r = EnhancedREPL()
# Test path-based import
out, err, _ = r._eval('import "./inscript-packages/packages/vector2/vector2.ins" as v2')
print("err:", repr(err)[:300] if err else "None")
if not err:
    out2, err2, _ = r._eval('import "./inscript-packages/packages/vector2/vector2.ins" as v2; let r = v2.vec2_len(3.0, 4.0)')
    print("result err:", repr(err2)[:300] if err2 else "None")
