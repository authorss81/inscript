# -*- coding: utf-8 -*-
"""
InScript — setup.py
pyproject.toml is the canonical config for v1.0.23+
This file is kept for compatibility with older pip versions.

VERSION is read dynamically from inscript.py so setup.py, pyproject.toml,
and inscript.py always agree — no more manual sync needed.
"""
import re
from pathlib import Path
from setuptools import setup

def _read_version():
    src = Path(__file__).parent / "inscript.py"
    m   = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']',
                    src.read_text(encoding="utf-8"), re.M)
    if not m:
        raise RuntimeError("VERSION not found in inscript.py")
    return m.group(1)

VERSION = _read_version()

setup(
    name             = "inscript-lang",
    version          = VERSION,
    author           = "Shreyasi Sarkar",
    description      = "InScript — a game-focused scripting language for 2D games",
    long_description = open("README.md", encoding="utf-8").read(),
    long_description_content_type = "text/markdown",
    license          = "MIT",
    python_requires  = ">=3.10",
    keywords         = ["game", "scripting", "language", "gamedev", "gdscript"],
    classifiers      = [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Games/Entertainment",
        "Topic :: Software Development :: Interpreters",
    ],
    py_modules = [
        "inscript", "repl", "lexer", "parser", "interpreter",
        "compiler", "vm", "analyzer", "errors", "environment",
        "stdlib", "stdlib_extended", "stdlib_extended_2", "stdlib_game",
        "stdlib_values", "ast_nodes", "inscript_fmt", "inscript_test",
        "pygame_backend",
    ],
    package_data     = {"": ["examples/*.ins", "lsp/*.py", "*.md"]},
    install_requires = [],
    extras_require   = {
        "game": ["pygame>=2.0"],
        "lsp":  ["pygls>=1.0"],
        "all":  ["pygame>=2.0", "pygls>=1.0"],
    },
    entry_points     = {"console_scripts": ["inscript=inscript:main"]},
    project_urls     = {
        "Homepage":      "https://github.com/authorss81/inscript",
        "Documentation": "https://authorss81.github.io/inscript/docs/",
        "Bug Tracker":   "https://github.com/authorss81/inscript/issues",
    },
)
