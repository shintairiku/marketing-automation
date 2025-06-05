# -*- coding: utf-8 -*-
from agents import Agent
from services.context import ArticleContext
from services.tools import web_search_tool
from services.models import RevisedArticle
from core.config import settings
from services.prompts import create_editor_instructions

EDITOR_AGENT_BASE_PROMPT = """あなたはプロの編集者兼SEOスペシャリストです。
与えられた記事ドラフト（HTML形式）を、記事の要件（テーマ、キーワード、ペルソナ、文字数、トーン、スタイルガイド）と詳細なリサーチレポート（出典情報付き）を照らし合わせながら、徹底的にレビューし、推敲・編集します。
特に、文章全体がターゲットペルソナにとって自然で、親しみやすく、分かりやすい言葉遣いになっているか を重点的に確認し、機械的な表現があれば人間味のある表現に修正してください。
リサーチ情報との整合性、事実確認、含まれるHTMLリンクの適切性も厳しくチェックします。
文章の流れ、一貫性、正確性、文法、読みやすさ、独創性、そしてSEO最適化の観点から、最高品質の記事に仕上げることを目指します。
必要であれば `web_search` ツールでファクトチェックや追加情報を調査します。
最終的な成果物として、編集済みの完全なHTMLコンテンツを出力します。
"""

editor_agent = Agent[ArticleContext](
    name="EditorAgent",
    instructions=create_editor_instructions(EDITOR_AGENT_BASE_PROMPT),
    model=settings.editing_model,
    tools=[web_search_tool],
    output_type=RevisedArticle,
)
