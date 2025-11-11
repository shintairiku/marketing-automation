# -*- coding: utf-8 -*-
"""
Weave-first evaluation scaffolding for the SEO article generation flow.
"""

from .datasets import EXAMPLES
from .model import ArticleFlowModel
from .scorers import (
    length_budget_score,
    heading_structure_score,
    IntentCoverageJudge,
)

__all__ = [
    "EXAMPLES",
    "ArticleFlowModel",
    "length_budget_score",
    "heading_structure_score",
    "IntentCoverageJudge",
]
