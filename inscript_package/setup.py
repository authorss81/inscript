#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup.py — InScript v3.7.3 Build Configuration

Builds:
  1. Python package (inscript)
  2. Rust parser module (inscript_parser)
  3. All extensions and tools
"""

import sys
import os
from setuptools import setup, find_packages

try:
    from setuptools_rust import RustExtension, build_rust
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    build_rust = None

# Rust extension for parser (v3.7.3)
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
    version='3.7.3',
    description='InScript: Real compilable scripting language for game development',
    author='Shreyasi Sarkar',
    url='https://github.com/authorss81/inscript',
    license='MIT',
    
    packages=find_packages(exclude=['tests', 'docs', 'examples']),
    
    rust_extensions=rust_extensions,
    cmdclass=cmdclass,
    
    install_requires=['pyo3>=0.21'] if RUST_AVAILABLE else [],
    
    extras_require={
        'dev': ['pytest>=7.0', 'setuptools-rust>=1.1', 'maturin>=0.14'],
    },
    
    entry_points={
        'console_scripts': [
            'inscript=inscript:main',
        ],
    },
    
    python_requires='>=3.8',
    zip_safe=False,
)
