# -*- coding: utf-8 -*-
from agents import Agent
from services.context import ArticleContext
from services.models import ResearchReport
from core.config import settings
from .prompts import create_research_synthesizer_instructions

RESEARCH_SYNTHESIZER_AGENT_BASE_PROMPT = """あなたは情報を整理し、要点を抽出し、統合する専門家です。
収集された詳細なリサーチ結果（抜粋と出典）を分析し、記事のテーマに沿って統合・要約します。
各キーポイントについて、それを裏付ける情報源URLを明確に紐付け、記事作成者がすぐに活用できる実用的で詳細なリサーチレポートを作成します。
"""

research_synthesizer_agent = Agent[ArticleContext](
    name="ResearchSynthesizerAgent",
    instructions=create_research_synthesizer_instructions(RESEARCH_SYNTHESIZER_AGENT_BASE_PROMPT),
    model=settings.research_model,
    tools=[],
    output_type=ResearchReport,
)
