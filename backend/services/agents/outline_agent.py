# -*- coding: utf-8 -*-
from agents import Agent
from services.context import ArticleContext
from services.tools import analyze_competitors, get_company_data
from services.models import AgentOutput
from core.config import settings
from services.prompts import create_outline_instructions

OUTLINE_AGENT_BASE_PROMPT = """あなたはSEO記事のアウトライン（構成案）を作成する専門家です。
選択されたテーマ、目標文字数、企業のスタイルガイド、ターゲットペルソナ、そして詳細なリサーチレポート（キーポイントと出典情報を含む）に基づいて、論理的で網羅的、かつ読者の興味を引く記事のアウトラインを生成します。
`analyze_competitors` ツールで競合記事の構成を調査し、差別化できる構成を考案します。
`get_company_data` ツールでスタイルガイドを確認します。
文字数指定に応じて、見出しの数や階層構造を適切に調整します。
ターゲットペルソナが読みやすいように、親しみやすく分かりやすいトーンで記事全体のトーンも提案してください。
"""

outline_agent = Agent[ArticleContext](
    name="OutlineAgent",
    instructions=create_outline_instructions(OUTLINE_AGENT_BASE_PROMPT),
    model=settings.writing_model,
    tools=[analyze_competitors, get_company_data],
    output_type=AgentOutput,
)
