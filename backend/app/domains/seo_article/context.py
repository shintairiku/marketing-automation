# -*- coding: utf-8 -*-
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Union, Optional, Tuple, Any, Literal
from pydantic import BaseModel
from fastapi import WebSocket # <<< WebSocket をインポート

# 循環参照を避けるため、モデルは直接インポートせず、型ヒントとして文字列を使うか、
# このファイル内で必要なモデルを再定義/インポートする
from app.domains.seo_article.schemas import (
    ThemeProposal as ThemeIdea, ResearchPlan, ResearchQueryResult, ResearchReport, 
    Outline, AgentOutput, ArticleSection, SerpKeywordAnalysisReport, ImagePlaceholder,
    ClientResponsePayload, AgeGroup, PersonaType
)
# WebSocketメッセージスキーマもインポート (型ヒント用)
from app.common.schemas import UserInputType

@dataclass
class ArticleContext:
    """記事生成プロセス全体で共有されるコンテキスト (WebSocket対応)"""
    # --- ユーザー/API入力 ---
    initial_keywords: List[str] = field(default_factory=list)
    target_age_group: Optional[AgeGroup] = None # 追加
    persona_type: Optional[PersonaType] = None # 追加
    custom_persona: Optional[str] = None # 追加 (target_persona の代わり)
    target_length: Optional[int] = None # 目標文字数
    num_theme_proposals: int = 3
    vector_store_id: Optional[str] = None # File Search用
    num_research_queries: int = 5 # リサーチクエリ数の上限
    num_persona_examples: int = 3 # 追加: 生成する具体的なペルソナの数
    # 会社情報 - 基本情報
    company_name: Optional[str] = None
    company_description: Optional[str] = None
    company_usp: Optional[str] = None
    company_website_url: Optional[str] = None
    company_target_persona: Optional[str] = None
    
    # 会社情報 - ブランディング
    company_brand_slogan: Optional[str] = None
    company_style_guide: Optional[str] = None # 文体、トンマナなど
    
    # 会社情報 - SEO・コンテンツ戦略
    company_target_keywords: Optional[str] = None
    company_industry_terms: Optional[str] = None
    company_avoid_terms: Optional[str] = None
    company_popular_articles: Optional[str] = None
    company_target_area: Optional[str] = None
    
    # 過去記事情報
    past_articles_summary: Optional[str] = None # 過去記事の傾向 (ツールで取得想定)
    
    # --- 画像モード関連 (新規追加) ---
    image_mode: bool = False # 画像プレースホルダー機能を使用するかどうか
    image_settings: Dict[str, Any] = field(default_factory=dict) # 画像生成設定
    image_placeholders: List[ImagePlaceholder] = field(default_factory=list) # 生成された画像プレースホルダーのリスト
    
    # --- スタイルテンプレート関連 (新規追加) ---
    style_template_id: Optional[str] = None # 使用するスタイルテンプレートのID
    style_template_settings: Dict[str, Any] = field(default_factory=dict) # スタイルテンプレートの設定内容

    # --- SerpAPI分析関連 (新規追加) ---
    serp_analysis_report: Optional[SerpKeywordAnalysisReport] = None # SerpAPIキーワード分析結果
    
    # --- ペルソナ生成関連 (新規追加) ---
    generated_detailed_personas: List[str] = field(default_factory=list) # PersonaGeneratorAgentによって生成された具体的なペルソナ記述のリスト
    selected_detailed_persona: Optional[str] = None # ユーザーによって選択された単一の具体的なペルソナ記述
    
    # --- テーマ生成関連 ---
    generated_themes: List[ThemeIdea] = field(default_factory=list) # テーマ生成エージェントによって生成されたテーマ案のリスト

    # --- 生成プロセス状態 ---
    current_step: Literal[
        "start",
        "keyword_analyzing", # 新ステップ: SerpAPIキーワード分析中
        "keyword_analyzed",  # 新ステップ: SerpAPIキーワード分析完了
        "persona_generating", # 新ステップ: 具体的なペルソナ生成中
        "persona_generated",  # 新ステップ: 具体的なペルソナ生成完了、ユーザー選択待ち
        "persona_selected",   # 新ステップ: 具体的なペルソナ選択完了
        "theme_generating",   # テーマ生成中
        "theme_proposed",     # ユーザー選択待ち
        "theme_selected",
        "research_planning",
        "research_plan_generated", # ユーザー承認待ち
        "research_plan_approved",  # 計画承認済み
        "researching",
        "research_synthesizing",
        "research_report_generated", # 承認は任意
        "outline_generating",
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

    # --- 進捗追跡関連 ---
    research_progress: Optional[Dict[str, Any]] = None # リサーチ進捗状況
    sections_progress: Optional[Dict[str, Any]] = None # セクション執筆進捗状況
    
    # --- WebSocket/インタラクション用 ---
    websocket: Optional[WebSocket] = None # WebSocket接続オブジェクト
    user_response_event: Optional[asyncio.Event] = None # ユーザー応答待ち用イベント
    expected_user_input: Optional[UserInputType] = None # 現在待っている入力タイプ
    user_response: Optional[ClientResponsePayload] = None # ユーザーからの応答ペイロード
    user_id: Optional[str] = None # ユーザーID (認証から取得)
    process_id: Optional[str] = None # プロセスID (記事生成セッション識別用)

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

