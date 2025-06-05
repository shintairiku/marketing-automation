# -*- coding: utf-8 -*-
from typing import Callable, Awaitable
from agents import Agent, RunContextWrapper
from services.context import ArticleContext


def create_research_planner_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        if not ctx.context.selected_theme:
            raise ValueError("リサーチ計画を作成するためのテーマが選択されていません。")
        if not ctx.context.selected_detailed_persona:
            raise ValueError("リサーチ計画のための詳細なペルソナが選択されていません。")
        persona_description = ctx.context.selected_detailed_persona

        seo_guidance_str = ""
        if ctx.context.serp_analysis_report:
            seo_guidance_str = f"""

=== SerpAPI分析ガイダンス ===
競合記事の主要テーマ: {', '.join(ctx.context.serp_analysis_report.main_themes)}
コンテンツギャップ（調査すべき領域）: {', '.join(ctx.context.serp_analysis_report.content_gaps)}
差別化ポイント: {', '.join(ctx.context.serp_analysis_report.competitive_advantages)}
検索ユーザーの意図: {ctx.context.serp_analysis_report.user_intent_analysis}

上記の分析結果を踏まえ、競合が扱っていない角度や、より深く掘り下げるべき領域を重点的にリサーチしてください。
"""

        full_prompt = f"""{base_prompt}

--- リサーチ対象テーマ ---
タイトル: {ctx.context.selected_theme.title}
説明: {ctx.context.selected_theme.description}
キーワード: {', '.join(ctx.context.selected_theme.keywords)}
ターゲットペルソナ詳細:\n{persona_description}
{seo_guidance_str}
---

**重要:**
- 上記テーマについて深く掘り下げるための、具体的で多様な検索クエリを **{ctx.context.num_research_queries}個** 生成してください。
- 各クエリには、そのクエリで何を明らかにしたいか（focus）を明確に記述してください。
- あなたの応答は必ず `ResearchPlan` 型のJSON形式で出力してください。
"""
        return full_prompt
    return dynamic_instructions_func
