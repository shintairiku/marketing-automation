# -*- coding: utf-8 -*-
from agents import Agent
from services.context import ArticleContext
from services.tools import web_search_tool
from services.models import ResearchQueryResult
from core.config import settings
from services.prompts import create_researcher_instructions

RESEARCHER_AGENT_BASE_PROMPT = """あなたは熟練したディープリサーチャーです。
指定された検索クエリでWeb検索を実行し、結果を深く分析します。
記事テーマに関連する具体的で信頼できる情報、データ、主張、引用を詳細に抽出し、最も適切な出典元URLとタイトルを特定して、指定された形式で返します。
必ず web_search ツールを使用してください。
"""

researcher_agent = Agent[ArticleContext](
    name="ResearcherAgent",
    instructions=create_researcher_instructions(RESEARCHER_AGENT_BASE_PROMPT),
    model=settings.research_model,
    tools=[web_search_tool],
    output_type=ResearchQueryResult,
)
