# -*- coding: utf-8 -*-
from agents import Agent
from services.context import ArticleContext
from services.models import AgentOutput
from core.config import settings
from .prompts import create_research_planner_instructions

RESEARCH_PLANNER_AGENT_BASE_PROMPT = """あなたは優秀なリサーチプランナーです。
与えられた記事テーマに基づき、そのテーマを深く掘り下げ、読者が知りたいであろう情報を網羅するための効果的なWeb検索クエリプランを作成します。
"""

research_planner_agent = Agent[ArticleContext](
    name="ResearchPlannerAgent",
    instructions=create_research_planner_instructions(RESEARCH_PLANNER_AGENT_BASE_PROMPT),
    model=settings.research_model,
    tools=[],
    output_type=AgentOutput,
)
