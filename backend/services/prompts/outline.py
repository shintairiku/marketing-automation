# -*- coding: utf-8 -*-
from typing import Callable, Awaitable
from agents import Agent, RunContextWrapper
from services.context import ArticleContext


def create_outline_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        if not ctx.context.selected_theme or not ctx.context.research_report:
            raise ValueError("アウトライン作成に必要なテーマまたはリサーチレポートがありません。")
        if not ctx.context.selected_detailed_persona:
            raise ValueError("アウトライン作成のための詳細なペルソナが選択されていません。")
        persona_description = ctx.context.selected_detailed_persona

        research_summary = ctx.context.research_report.overall_summary
        company_info_str = ""
        if ctx.context.company_name or ctx.context.company_description:
            company_info_str = f"\nクライアント情報:\n  企業名: {ctx.context.company_name or '未設定'}\n  企業概要: {ctx.context.company_description or '未設定'}\n"

        seo_structure_guidance = ""
        if ctx.context.serp_analysis_report:
            seo_structure_guidance = f"""

=== SerpAPI構成戦略ガイダンス ===
競合共通見出しパターン: {', '.join(ctx.context.serp_analysis_report.common_headings)}
推奨文字数: {ctx.context.serp_analysis_report.recommended_target_length}文字
コンテンツギャップ（新規追加推奨）: {', '.join(ctx.context.serp_analysis_report.content_gaps)}
差別化ポイント: {', '.join(ctx.context.serp_analysis_report.competitive_advantages)}
コンテンツ戦略: {', '.join(ctx.context.serp_analysis_report.content_strategy_recommendations)}

上記を参考に、競合に勝る構成を設計してください。共通見出しは参考程度に留め、差別化要素を強く反映したアウトラインを作成してください。
"""

        full_prompt = f"""{base_prompt}

--- 入力情報 ---
選択されたテーマ:
  タイトル: {ctx.context.selected_theme.title}
  説明: {ctx.context.selected_theme.description}
  キーワード: {', '.join(ctx.context.selected_theme.keywords)}
ターゲット文字数: {ctx.context.target_length or '指定なし（標準的な長さで）'}
ターゲットペルソナ詳細:\n{persona_description}
{company_info_str}
{seo_structure_guidance}
--- 詳細なリサーチ結果 ---
{research_summary}
参照した全情報源URL数: {len(ctx.context.research_report.all_sources)}
---

**重要:**
- 上記のテーマと**詳細なリサーチ結果**、そして競合分析の結果（ツール使用）に基づいて、記事のアウトラインを作成してください。
- リサーチ結果の**キーポイント（出典情報も考慮）**や面白い切り口をアウトラインに反映させてください。
- **ターゲットペルソナ「{persona_description}」** が読みやすいように、日本の一般的なブログやコラムのような、**親しみやすく分かりやすいトーン**でアウトラインを作成してください。記事全体のトーンも提案してください。
- SerpAPI分析で判明した競合の弱点を補強し、差別化要素を強調した構成にしてください。
- あなたの応答は必ず `Outline` または `ClarificationNeeded` 型のJSON形式で出力してください。 (APIコンテキストではClarificationNeededはエラーとして処理)
- 文字数指定がある場合は、それに応じてセクション数や深さを調整してください。
"""
        return full_prompt
    return dynamic_instructions_func
