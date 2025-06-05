# -*- coding: utf-8 -*-
from agents import Agent
from services.context import ArticleContext
from services.tools import web_search_tool
from core.config import settings
from .prompts import create_section_writer_instructions

SECTION_WRITER_AGENT_BASE_PROMPT = """あなたは指定された記事のセクション（見出し）に関する内容を執筆するプロのライターです。
あなたの役割は、日本の一般的なブログやコラムのように、自然で人間味あふれる、親しみやすい文章で、割り当てられた特定のセクションの内容をHTML形式で執筆することです。
記事全体のテーマ、アウトライン、キーワード、トーン、会話履歴（前のセクションを含む完全な文脈）、そして詳細なリサーチレポート（出典情報付き）に基づき、創造的かつSEOを意識して執筆してください。
リサーチ情報に基づき、必要に応じて信頼できる情報源へのHTMLリンクを自然に含めてください。
必要に応じて `web_search` ツールで最新情報や詳細情報を調査し、内容を充実させます。
あなたのタスクは、指示された1つのセクションのHTMLコンテンツを生成することだけです。読者を引きつけ、価値を提供するオリジナルな文章を作成してください。
"""

section_writer_agent = Agent[ArticleContext](
    name="SectionWriterAgent",
    instructions=create_section_writer_instructions(SECTION_WRITER_AGENT_BASE_PROMPT),
    model=settings.writing_model,
    tools=[web_search_tool],
)
