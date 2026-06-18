#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup.py — InScript Build Configuration

Version is read dynamically from inscript.py's VERSION constant.
"""

import sys
import os
import re
import sysconfig
from setuptools import setup, find_packages

if sys.platform.startswith('linux'):
    os.environ.setdefault('PYO3_CROSS_PYTHON_VERSION', f"{sys.version_info.major}.{sys.version_info.minor}")

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
    from setuptools_rust import RustExtension, Binding, build_rust as _build_rust
    from setuptools_rust.command import RustCommand
    from setuptools_rust.build import _Platform as _RustPlatform
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    _build_rust = None
    RustCommand = None
    _RustPlatform = None

# Rust extension for parser
rust_extensions = []
cmdclass = {}

if RUST_AVAILABLE:
    rust_extensions = [
        RustExtension(
            'inscript.inscript_parser',
            path='inscript_rust_parser/Cargo.toml',
            binding=Binding.PyO3,
        ),
    ]
    # build_rust.finalize_options calls set_undefined_options("build_ext", ...)
    # which self-recurses when build_rust IS the build_ext command.
    # Subclass to break the cycle by inheriting build_temp from the build command.
    class _SafeBuildRust(_build_rust):
        def initialize_options(self):
            super().initialize_options()
            self.build_lib = None

        def finalize_options(self):
            RustCommand.finalize_options(self)
            if self.target is None:
                self.target = _RustPlatform.CARGO_DEFAULT
            self.set_undefined_options(
                "build",
                ("plat_name", "plat_name"),
                ("build_lib", "build_lib"),
            )
            if getattr(self, 'build_temp', None) is None:
                self.set_undefined_options(
                    "build",
                    ("build_temp", "build_temp"),
                )

        def get_source_files(self):
            filenames = []
            for ext in self.extensions:
                if hasattr(ext, 'path'):
                    filenames.append(ext.path)
            return filenames

        def get_ext_fullpath(self, ext_name):
            fullname = self.get_ext_fullname(ext_name)
            modpath = fullname.split('.')
            filename = self.get_ext_filename(modpath[-1])
            if not getattr(self, 'inplace', False):
                filename = os.path.join(*modpath[:-1] + [filename])
                return os.path.join(self.build_lib, filename)
            return os.path.join(*modpath[:-1], filename)

        def get_ext_fullname(self, ext_name):
            return ext_name

        def get_ext_filename(self, ext_name):
            ext_path = ext_name.split('.')
            ext_suffix = sysconfig.get_config_var('EXT_SUFFIX')
            return os.path.join(*ext_path) + ext_suffix
    cmdclass['build_ext'] = _SafeBuildRust

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
