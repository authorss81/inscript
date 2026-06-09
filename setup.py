"""
InScript — setup.py
Correct structure: this file is at the ROOT, one level ABOVE inscript_package/

Directory layout:
  inscript_release/          ← you run `python -m build` from here
    setup.py                 ← this file
    pyproject.toml
    README.md
    inscript_package/        ← the actual Python package
      __init__.py
      inscript.py
      ...
"""
from setuptools import setup, find_packages

setup(
    name             = "inscript-lang",
    version          = "3.9.3",
    author           = "InScript Contributors",
    description      = "InScript — a modern scripting language for game development",
    long_description = open("README.md", encoding="utf-8").read(),
    long_description_content_type = "text/markdown",
    license          = "MIT",
    python_requires  = ">=3.10",
    packages         = find_packages(),           # finds inscript_package/
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
