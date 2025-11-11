# -*- coding: utf-8 -*-
"""Weave Model wrapper around the SEO article generation flow."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict, List, Optional

import weave
from agents import RunConfig

from app.domains.seo_article.context import ArticleContext
from app.domains.seo_article.services.generation_service import ArticleGenerationService


class ArticleFlowModel(weave.Model):
    """Wrap the existing multi-agent flow so it can be evaluated via Weave."""

    outline_prompt_variant: str = "baseline"
    flow_type: str = "research_first"

    @weave.op()
    async def predict(
        self,
        initial_keywords: List[str],
        target_age_group: Optional[str] = None,
        persona_type: Optional[str] = None,
        custom_persona: Optional[str] = None,
        target_length: Optional[int] = None,
        company_name: Optional[str] = None,
        style_template_id: Optional[str] = None,
        flow_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        service = ArticleGenerationService()
        context = ArticleContext(
            initial_keywords=initial_keywords,
            target_age_group=target_age_group,
            persona_type=persona_type,
            custom_persona=custom_persona,
            target_length=target_length,
            company_name=company_name,
            style_template_id=style_template_id,
            flow_type=flow_type or self.flow_type,
            user_id="weave-eval",
            auto_decision_mode=True,
            disable_realtime_events=True,
        )
        context.process_id = f"eval-{uuid.uuid4().hex}"

        run_config = RunConfig(
            workflow_name=f"seo_article_eval::{self.outline_prompt_variant}",
            trace_id=str(uuid.uuid4()),
            group_id=context.process_id,
        )

        await service.flow_manager.run_generation_loop(
            context,
            run_config,
            process_id=None,
            user_id=None,
        )

        html_output = (
            context.final_article_html
            or context.full_draft_html
            or "\n".join(context.generated_sections_html)
        )
        if not html_output:
            raise RuntimeError("Article flow completed without producing HTML output.")

        return {
            "html": html_output,
            "observability": context.observability,
            "article_context": {
                "target_length": context.target_length,
                "flow_type": context.flow_type,
                "selected_theme": getattr(context.selected_theme, "title", None),
            },
        }
