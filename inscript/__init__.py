"""
Inscript - A clean, Python-like interpreted language with English-style keywords.
Focus: Language feel, clarity, and developer happiness.
"""

__version__ = "0.2.0"
__author__ = "Inscript Community"

from . import lexer
from . import parser
from . import interpreter
from . import cli

# Export main for entry point
from .cli import main

__all__ = ["lexer", "parser", "interpreter", "cli", "main"]
