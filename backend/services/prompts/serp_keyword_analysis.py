# -*- coding: utf-8 -*-
from typing import Callable, Awaitable
from agents import Agent, RunContextWrapper
from services.context import ArticleContext


def create_serp_keyword_analysis_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        keywords = ctx.context.initial_keywords

        from services.serpapi_service import serpapi_service
        analysis_result = await serpapi_service.analyze_keywords(keywords, num_articles_to_scrape=5)

        articles_summary = ""
        for i, article in enumerate(analysis_result.scraped_articles):
            articles_summary += f"""
記事 {i+1}:
- タイトル: {article.title}
- URL: {article.url}
- 文字数: {article.char_count}
- 画像数: {article.image_count}
- 取得元: {article.source_type}
{f"- 検索順位: {article.position}" if article.position else ""}
{f"- 関連質問: {article.question}" if article.question else ""}
- 見出し構成:
{chr(10).join(f"  * {heading}" for heading in article.headings)}
- 本文プレビュー: {article.content[:200]}...

"""

        related_questions_str = ""
        if analysis_result.related_questions:
            related_questions_str = "関連質問:\n"
            for i, q in enumerate(analysis_result.related_questions):
                related_questions_str += f"  {i+1}. {q.get('question', 'N/A')}\n"

        full_prompt = f"""{base_prompt}

--- SerpAPI分析データ ---
検索クエリ: {analysis_result.search_query}
検索結果総数: {analysis_result.total_results:,}
分析対象記事数: {len(analysis_result.scraped_articles)}
平均文字数: {analysis_result.average_char_count}
推奨目標文字数: {analysis_result.suggested_target_length}

{related_questions_str}

--- 上位記事詳細分析データ ---
{articles_summary}

--- あなたのタスク ---
上記のSerpAPI分析結果を基に、以下の項目を含む包括的なSEO戦略レポートを作成してください：

1. main_themes: 上位記事で頻出する主要テーマ・トピック（5-8個程度）
2. common_headings: 共通して使用される見出しパターン（5-10個程度）
3. content_gaps: 上位記事で不足している可能性のあるコンテンツ（3-5個程度）
4. competitive_advantages: 差別化できる可能性のあるポイント（3-5個程度）
5. user_intent_analysis: 検索ユーザーの意図分析（詳細な文章で）
6. content_strategy_recommendations: コンテンツ戦略の推奨事項（5-8個程度）

**必須フィールド**: あなたの応答には以下の情報を必ず含めてください：
- search_query: "{analysis_result.search_query}"
- total_results: {analysis_result.total_results}
- average_article_length: {analysis_result.average_char_count}
- recommended_target_length: {analysis_result.suggested_target_length}
- analyzed_articles: 分析した記事のリスト（以下の形式で各記事を記述）
  [
    {{
      "url": "記事URL",
      "title": "記事タイトル",
      "headings": ["見出し1", "見出し2", ...],
      "content_preview": "記事内容のプレビュー",
      "char_count": 文字数,
      "image_count": 画像数,
      "source_type": "organic_result" または "related_question",
      "position": 順位（該当する場合）、
      "question": "関連質問"（該当する場合）
    }}, ...
  ]

特に、分析した記事の見出し構成、文字数、扱っているトピックの傾向を詳しく分析し、競合に勝るコンテンツを作成するための戦略を提案してください。
"""
        return full_prompt
    return dynamic_instructions_func
