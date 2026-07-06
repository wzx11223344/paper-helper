"""
paper_helper — AI-powered full-cycle academic writing assistant
for Chinese thesis and research papers.

Modules:
    outline   : Auto-generate 5-level thesis outline from topic
    lit_review: Literature review framework with Semantic Scholar search
    formatter : GB/T 7714 citation formatting, heading consistency, spacing
    checker   : Detect common academic writing issues
"""

__version__ = "1.0.0"
__author__ = "paper-helper"

from paper_helper.outline import generate_outline, OutlineGenerator
from paper_helper.lit_review import build_lit_review, LitReviewBuilder
from paper_helper.formatter import format_document, check_format, DocumentFormatter
from paper_helper.checker import check_document, Checker

__all__ = [
    "generate_outline",
    "OutlineGenerator",
    "build_lit_review",
    "LitReviewBuilder",
    "format_document",
    "check_format",
    "DocumentFormatter",
    "check_document",
    "Checker",
]
