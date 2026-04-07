# -*- coding: utf-8 -*-
"""
InScript — setup.py (legacy fallback; pyproject.toml is canonical for v1.0.21+)
Upgrade from v0.6: pip install --upgrade inscript-lang
Publish: python -m build && python -m twine upload dist/*
"""
from setuptools import setup, find_packages

setup(
    name             = "inscript-lang",
    version          = "1.0.21",
    author           = "Shreyasi Sarkar",
    description      = "InScript — a modern scripting language for game development",
    long_description = open("README.md", encoding="utf-8").read(),
    long_description_content_type = "text/markdown",
    license          = "MIT",
    python_requires  = ">=3.10",
    packages         = find_packages(),
    package_data     = {"": ["*.ins", "examples/*.ins", "*.md"]},
    entry_points     = {"console_scripts": ["inscript=inscript:main"]},
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
        "Homepage":   "https://inscript-lang.dev",
        "Repository": "https://github.com/YOUR_USERNAME/inscript",
    },
)
