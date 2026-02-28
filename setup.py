#!/usr/bin/env python3
"""
Setup configuration for Inscript language interpreter.
Allows installation via: pip install inscript
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="inscript",
    version="0.2.0",
    author="Shreyasi Sarkar",
    author_email="your-email@example.com",
    description="A Python-like interpreted programming language with clean, English-style syntax",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/YourUsername/inscript",
    project_urls={
        "Documentation": "https://github.com/YourUsername/inscript/tree/main/docs",
        "Source": "https://github.com/YourUsername/inscript",
        "Tracker": "https://github.com/YourUsername/inscript/issues",
    },
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        # No external dependencies - uses only Python standard library
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=22.0",
            "flake8>=5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "inscript=inscript.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Topic :: Software Development :: Languages",
        "Topic :: Software Development :: Interpreters",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    keywords="language interpreter python-like clean syntax",
    license="MIT",
    include_package_data=True,
)
