"""Single source of truth for version.

All Python modules should import VERSION from here instead of hardcoding it.
"""
import os, re, sys

_version_module = None

def _get_version():
    global _version_module
    if _version_module is not None:
        return _version_module
    # Read from inscript.py's VERSION variable
    vfile = os.path.join(os.path.dirname(__file__), "inscript.py")
    try:
        with open(vfile, encoding="utf-8") as f:
            src = f.read()
        m = re.search(r'^VERSION\s*=\s*"([^"]+)"', src, re.M)
        if m:
            _version_module = m.group(1)
            return _version_module
    except Exception:
        pass
    return "0.0.0"

VERSION = _get_version()
__all__ = ["VERSION"]
