# -*- coding: utf-8 -*-
from typing import Callable, Awaitable
from agents import Agent, RunContextWrapper
from services.context import ArticleContext


def create_theme_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        if not ctx.context.selected_detailed_persona:
            raise ValueError("テーマ提案のための詳細なペルソナが選択されていません。")
        persona_description = ctx.context.selected_detailed_persona
        company_info_str = f"企業名: {ctx.context.company_name}\n概要: {ctx.context.company_description}\n文体ガイド: {ctx.context.company_style_guide}\n過去記事傾向: {ctx.context.past_articles_summary}" if ctx.context.company_name else "企業情報なし"

        seo_analysis_str = ""
        if ctx.context.serp_analysis_report:
            seo_analysis_str = f"""

=== SerpAPI競合分析結果 ===
検索クエリ: {ctx.context.serp_analysis_report.search_query}
競合記事数: {len(ctx.context.serp_analysis_report.analyzed_articles)}
推奨文字数: {ctx.context.serp_analysis_report.recommended_target_length}文字

主要テーマ（競合頻出）: {', '.join(ctx.context.serp_analysis_report.main_themes)}
共通見出し: {', '.join(ctx.context.serp_analysis_report.common_headings[:8])}
コンテンツギャップ: {', '.join(ctx.context.serp_analysis_report.content_gaps)}
差別化ポイント: {', '.join(ctx.context.serp_analysis_report.competitive_advantages)}
検索意図: {ctx.context.serp_analysis_report.user_intent_analysis}

戦略推奨: {', '.join(ctx.context.serp_analysis_report.content_strategy_recommendations[:5])}

上記の競合分析を活用し、検索上位を狙える差別化されたテーマを提案してください。
"""

        full_prompt = f"""{base_prompt}

--- 入力情報 ---
キーワード: {', '.join(ctx.context.initial_keywords)}
ターゲットペルソナ詳細:\n{persona_description}
提案するテーマ数: {ctx.context.num_theme_proposals}
企業情報:\n{company_info_str}
{seo_analysis_str}
---

あなたの応答は必ず `ThemeProposal` または `ClarificationNeeded` 型のJSON形式で出力してください。
"""
        return full_prompt
    return dynamic_instructions_func
