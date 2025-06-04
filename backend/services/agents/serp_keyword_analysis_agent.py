# -*- coding: utf-8 -*-
from agents import Agent
from services.context import ArticleContext
from services.models import SerpKeywordAnalysisReport
from core.config import settings
from .prompts import create_serp_keyword_analysis_instructions

SERP_KEYWORD_ANALYSIS_AGENT_BASE_PROMPT = """あなたはSEOとキーワード分析の専門家です。
SerpAPIで取得されたGoogle検索結果と、上位記事のスクレイピング結果を詳細に分析し、以下を含む包括的なSEO戦略レポートを作成します：

1. 上位記事で頻出する主要テーマ・トピック
2. 共通して使用される見出しパターン・構成
3. 上位記事で不足している可能性のあるコンテンツ（コンテンツギャップ）
4. 差別化できる可能性のあるポイント
5. 検索ユーザーの意図分析（情報収集、比較検討、購入検討など）
6. コンテンツ戦略の推奨事項

あなたの分析結果は、後続の記事生成プロセス（ペルソナ生成、テーマ提案、アウトライン作成、執筆）において重要な参考資料として活用されます。
特に、ターゲットキーワードで上位表示を狙うために必要な要素を明確に特定し、実用的な戦略を提案してください。

あなたの応答は必ず `SerpKeywordAnalysisReport` 型のJSON形式で出力してください。
"""

serp_keyword_analysis_agent = Agent[ArticleContext](
    name="SerpKeywordAnalysisAgent",
    instructions=create_serp_keyword_analysis_instructions(SERP_KEYWORD_ANALYSIS_AGENT_BASE_PROMPT),
    model=settings.research_model,
    tools=[],
    output_type=SerpKeywordAnalysisReport,
)
