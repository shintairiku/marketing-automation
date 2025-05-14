# -*- coding: utf-8 -*-
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Union, Optional, Tuple, Any, Literal
from pydantic import BaseModel
from fastapi import WebSocket # <<< WebSocket をインポート

# 循環参照を避けるため、モデルは直接インポートせず、型ヒントとして文字列を使うか、
# このファイル内で必要なモデルを再定義/インポートする
from services.models import ThemeIdea, ResearchPlan, ResearchQueryResult, ResearchReport, Outline, AgentOutput, ArticleSection
# WebSocketメッセージスキーマもインポート (型ヒント用)
from schemas.response import ClientResponsePayload, UserInputType

@dataclass
class ArticleContext:
    """記事生成プロセス全体で共有されるコンテキスト (WebSocket対応)"""
    # --- ユーザー/API入力 ---
    initial_keywords: List[str] = field(default_factory=list)
    target_persona: Optional[str] = None
    target_length: Optional[int] = None # 目標文字数
    num_theme_proposals: int = 3
    vector_store_id: Optional[str] = None # File Search用
    num_research_queries: int = 5 # リサーチクエリ数の上限
    company_name: Optional[str] = None
    company_description: Optional[str] = None
    company_style_guide: Optional[str] = None # 文体、トンマナなど
    past_articles_summary: Optional[str] = None # 過去記事の傾向 (ツールで取得想定)

    # --- 生成プロセス状態 ---
    current_step: Literal[
        "start",
        "theme_proposed", # ユーザー選択待ち
        "theme_selected",
        "research_planning",
        "research_plan_generated", # ユーザー承認待ち
        "researching",
        "research_synthesizing",
        "research_report_generated", # 承認は任意
        "outline_generation",
        "outline_generated", # ユーザー承認待ち
        "writing_sections",
        "editing",
        "completed",
        "error"
    ] = "start"
    selected_theme: Optional[ThemeIdea] = None
    research_plan: Optional[ResearchPlan] = None
    current_research_query_index: int = 0
    research_query_results: List[ResearchQueryResult] = field(default_factory=list)
    research_report: Optional[ResearchReport] = None
    generated_outline: Optional[Outline] = None
    current_section_index: int = 0
    generated_sections_html: List[str] = field(default_factory=list)
    full_draft_html: Optional[str] = None
    final_article_html: Optional[str] = None
    error_message: Optional[str] = None
    last_agent_output: Optional[Union[AgentOutput, ArticleSection]] = None
    section_writer_history: List[Dict[str, Any]] = field(default_factory=list)

    # --- WebSocket/インタラクション用 ---
    websocket: Optional[WebSocket] = None # WebSocket接続オブジェクト
    user_response_event: Optional[asyncio.Event] = None # ユーザー応答待ち用イベント
    expected_user_input: Optional[UserInputType] = None # 現在待っている入力タイプ
    user_response: Optional[ClientResponsePayload] = None # ユーザーからの応答ペイロード

    # --- 以下、既存のメソッド ---
    def get_full_draft(self) -> str:
        return "\n".join(self.generated_sections_html)

    def add_query_result(self, result: ResearchQueryResult):
        self.research_query_results.append(result)

    def clear_section_writer_history(self):
        self.section_writer_history = []

    def add_to_section_writer_history(self, role: Literal["user", "assistant", "system", "developer", "tool"], content: str):
        content_type = "output_text" if role == "assistant" else "input_text"
        if role == "system" or role == "developer":
             content_type = "input_text"
        message: Dict[str, Any] = {
            "role": role,
            "content": [{"type": content_type, "text": content}]
        }
        self.section_writer_history.append(message)

    # yield_sse_event は article_service 内のヘルパー関数 _send_server_event に置き換え

