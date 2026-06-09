#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup.py — InScript Build Configuration

Version is read dynamically from inscript.py's VERSION constant.
"""

import sys
import os
import re
from setuptools import setup, find_packages

# ── Dynamic version: read from inscript.py ────────
_here = os.path.dirname(os.path.abspath(__file__))
_inscript_py = os.path.join(_here, "inscript.py")
_version_line = open(_inscript_py, encoding="utf-8").read()
_match = re.search(r'^VERSION\s*=\s*"([^"]+)"', _version_line, re.MULTILINE)
if not _match:
    raise RuntimeError(f"Cannot find VERSION in {_inscript_py}")
VERSION = _match.group(1)
# ──────────────────────────────────────────────────

try:
    from setuptools_rust import RustExtension, build_rust
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    build_rust = None

# Rust extension for parser
rust_extensions = []
cmdclass = {}

if RUST_AVAILABLE:
    rust_extensions = [
        RustExtension(
            'inscript.inscript_parser',
            path='inscript_rust_parser/Cargo.toml',
            binding='PyO3',
        ),
    ]
    cmdclass['build_ext'] = build_rust

setup(
    name='inscript-lang',
    version=VERSION,
    description='InScript: Real compilable scripting language for game development',
    author='Shreyasi Sarkar',
    url='https://github.com/authorss81/inscript',
    license='MIT',
    
    packages=find_packages(exclude=['tests', 'docs', 'examples']),
    
    rust_extensions=rust_extensions,
    cmdclass=cmdclass,
    
    extras_require={
        'game': ['pygame>=2.0'],
        'lsp':  ['pygls>=1.0'],
        'dev': ['pytest>=7.0', 'setuptools-rust>=1.1'],
    },
    
    entry_points={
        'console_scripts': [
            'inscript=inscript:main',
        ],
    },
    
    python_requires='>=3.10',
    zip_safe=False,
)
