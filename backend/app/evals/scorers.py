# -*- coding: utf-8 -*-
"""Weave-compatible scorers for article evaluations."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import weave
from bs4 import BeautifulSoup
from openai import OpenAI

from app.core.config import settings


@weave.op()
def length_budget_score(output_html: str, target_length: Optional[int] = None) -> Dict[str, Any]:
    """Check whether the generated article stays within ±15% of the target length."""
    soup = BeautifulSoup(output_html or "", "lxml")
    char_count = len(soup.get_text())
    if not target_length:
        return {"chars": char_count, "within_budget": None, "target": None}
    budget = int(target_length * 0.15)
    return {
        "chars": char_count,
        "target": target_length,
        "within_budget": abs(char_count - target_length) <= budget,
        "budget_abs_error": abs(char_count - target_length),
    }


@weave.op()
def heading_structure_score(output_html: str) -> Dict[str, Any]:
    """Validate simple structural heuristics such as a single H1 and FAQ presence."""
    soup = BeautifulSoup(output_html or "", "lxml")
    h1_count = len(soup.find_all("h1"))
    faq_block = bool(soup.select("details, .faq, [data-faq]"))
    return {
        "h1_is_one": h1_count == 1,
        "h1_count": h1_count,
        "has_faq_block": faq_block,
    }


class IntentCoverageJudge(weave.Scorer):
    """LLM-as-judge scorer that rates intent coverage and helpfulness."""

    model_id: str = "gpt-4o-mini"
    system_prompt: str = (
        "You are an impartial Japanese SEO content quality rater. Score the article on a 0-10 scale for "
        "search intent coverage and actionable helpfulness. Respond with valid JSON containing "
        "`intent_coverage`, `helpfulness`, and a short `justification`."
    )

    @weave.op()
    def score(
        self,
        output_html: str,
        keywords: List[str],
        persona: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not settings.openai_api_key:
            return {
                "intent_coverage": None,
                "helpfulness": None,
                "justification": "OPENAI_API_KEY is not configured.",
            }
        prompt = (
            "Evaluate the following Japanese HTML article. Provide numeric scores from 0 to 10 for:\n"
            "- intent_coverage: Does it fully answer the implied search intent for the provided keywords?\n"
            "- helpfulness: Is it actionable, specific, and trustworthy for the described persona?\n"
            "Explain briefly in Japanese.\n"
            f"Keywords: {', '.join(keywords)}\n"
            f"Persona: {persona or 'N/A'}\n"
            "Article HTML:\n"
            f"{output_html}"
        )
        client = OpenAI(api_key=settings.openai_api_key)
        try:
            response = client.responses.create(
                model=self.model_id,
                input=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            content = response.output[0].content[0].text  # type: ignore[attr-defined]
            data = json.loads(content)
            return {
                "intent_coverage": float(data.get("intent_coverage", 0.0)),
                "helpfulness": float(data.get("helpfulness", 0.0)),
                "justification": data.get("justification", ""),
            }
        except Exception as exc:  # pragma: no cover - network call
            return {
                "intent_coverage": None,
                "helpfulness": None,
                "justification": f"judge_error: {exc}",
            }
