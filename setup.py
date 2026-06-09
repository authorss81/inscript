"""
InScript — setup.py
Correct structure: this file is at the ROOT, one level ABOVE inscript_package/

Version is read dynamically from inscript_package/inscript.py's VERSION constant.
"""
import os
import re
from setuptools import setup, find_packages

# ── Dynamic version: read from the real VERSION in inscript_package ──
_here = os.path.dirname(os.path.abspath(__file__))
_inscript_py = os.path.join(_here, "inscript_package", "inscript.py")
_version_line = open(_inscript_py, encoding="utf-8").read()
_match = re.search(r'^VERSION\s*=\s*"([^"]+)"', _version_line, re.MULTILINE)
if not _match:
    raise RuntimeError(f"Cannot find VERSION in {_inscript_py}")
VERSION = _match.group(1)
# ─────────────────────────────────────────────────────────────────────

setup(
    name             = "inscript-lang",
    version          = VERSION,
    author           = "InScript Contributors",
    description      = "InScript — a modern scripting language for game development",
    long_description = open("README.md", encoding="utf-8").read(),
    long_description_content_type = "text/markdown",
    license          = "MIT",
    python_requires  = ">=3.10",
    packages         = find_packages(),
    package_data     = {"inscript_package": ["examples/*.ins"]},
    entry_points     = {"console_scripts": ["inscript=inscript_package.inscript:main"]},
    classifiers      = [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Interpreters",
        "Topic :: Games/Entertainment",
    ],
    extras_require   = {"lsp": ["pygls>=1.3"]},
    project_urls     = {
        "Homepage":   "https://github.com/authorss81/inscript",
        "Repository": "https://github.com/authorss81/inscript",
    },
)
