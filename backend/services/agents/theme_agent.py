# -*- coding: utf-8 -*-
from agents import Agent
from services.context import ArticleContext
from services.tools import web_search_tool, get_company_data
from services.models import AgentOutput
from core.config import settings
from services.prompts import create_theme_instructions

THEME_AGENT_BASE_PROMPT = """あなたはSEO記事のテーマを考案する専門家です。
与えられたキーワード、ターゲットペルソナ、企業情報を分析し、読者の検索意図とSEO効果を考慮した上で、創造的で魅力的な記事テーマ案を複数生成します。
必要であれば `get_company_data` ツールで企業情報を補強し、`web_search` ツールで関連トレンドや競合を調査できます。
情報が不足している場合は、ClarificationNeededを返してください。
"""

theme_agent = Agent[ArticleContext](
    name="ThemeAgent",
    instructions=create_theme_instructions(THEME_AGENT_BASE_PROMPT),
    model=settings.default_model,
    tools=[get_company_data, web_search_tool],
    output_type=AgentOutput,
)
