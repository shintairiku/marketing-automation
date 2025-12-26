# -*- coding: utf-8 -*-
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Union, Optional, Any, Literal
from fastapi import WebSocket # <<< WebSocket をインポート

# 循環参照を避けるため、モデルは直接インポートせず、型ヒントとして文字列を使うか、
# このファイル内で必要なモデルを再定義/インポートする
from app.domains.seo_article.schemas import (
    ThemeProposalData as ThemeIdea, ResearchPlan, ResearchQueryResult, ResearchReport, 
    Outline, AgentOutput, ArticleSection, SerpKeywordAnalysisReport, ImagePlaceholder,
    ClientResponsePayload, AgeGroup, PersonaType, RevisedArticle
)
# WebSocketメッセージスキーマもインポート (型ヒント用)
from app.common.schemas import UserInputType

@dataclass
class ArticleContext:
    """記事生成プロセス全体で共有されるコンテキスト (WebSocket対応)"""
    # --- ユーザー/API入力 ---
    initial_keywords: List[str] = field(default_factory=list)
    # 代表値（後方互換用）と複数指定の両方を保持
    target_age_group: Optional[AgeGroup] = None
    target_age_groups: List[AgeGroup] = field(default_factory=list)
    persona_type: Optional[PersonaType] = None
    persona_types: List[PersonaType] = field(default_factory=list)
    custom_persona: Optional[str] = None # 追加 (target_persona の代わり)
    target_length: Optional[int] = None # 目標文字数
    num_theme_proposals: int = 3
    vector_store_id: Optional[str] = None # File Search用
    num_research_queries: int = 5 # リサーチクエリ数の上限
    num_persona_examples: int = 3 # 追加: 生成する具体的なペルソナの数
    
    # フロー設定
    flow_type: Optional[Literal["research_first", "outline_first"]] = None  # "research_first"（リサーチ先行） or "outline_first"（構成先行）
    auto_mode: bool = False  # ユーザー承認ステップを自動解決するか
    auto_selection_strategy: str = "best_match"  # first / best_match

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

    # --- アウトライン高度化設定 ---
    advanced_outline_mode: bool = False
    outline_top_level_heading: int = 2

    # --- SerpAPI分析関連 (新規追加) ---
    serp_analysis_report: Optional[SerpKeywordAnalysisReport] = None # SerpAPIキーワード分析結果
    has_serp_api_key: bool = False # SerpAPIキーが利用可能かどうか
    
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
        "researching",        # 統合リサーチ実行中（計画・実行・要約を含む）
        "research_completed", # リサーチ完了処理中（アウトライン遷移前の一時ステップ）
        "outline_generating",
        "outline_generated", # ユーザー承認待ち
        "writing_sections",
        "editing",
        "completed",
        "error"
    ] = "start"
    selected_theme: Optional[ThemeIdea] = None
    # 注意(legacy-flow): 旧リサーチフロー（複数ステップ）で保存されたプロセスを復元するために残しています。
    # 現行フローでは `research_report` を直接利用します。
    research_plan: Optional[ResearchPlan] = None
    current_research_query_index: int = 0
    research_query_results: List[ResearchQueryResult] = field(default_factory=list)
    research_report: Optional[ResearchReport] = None
    # 新形式: 構造化せずそのまま保持するリサーチテキスト
    research_sources_text: Optional[str] = None
    research_sources_tagged: Optional[str] = None
    generated_outline: Optional[Outline] = None
    current_section_index: int = 0
    generated_sections: List[ArticleSection] = field(default_factory=list)
    generated_sections_html: List[str] = field(default_factory=list)
    full_draft_html: Optional[str] = None
    final_article: Optional[RevisedArticle] = None
    final_article_html: Optional[str] = None
    final_article_id: Optional[str] = None
    error_message: Optional[str] = None
    last_agent_output: Optional[Union[AgentOutput, ArticleSection]] = None
    section_writer_history: List[Dict[str, Any]] = field(default_factory=list)

    # --- Responses API conversation continuity (optional, for future use) ---
    responses_conversation_id: Optional[str] = None
    last_response_id: Optional[str] = None

    # --- 進捗追跡関連 ---
    # 注意(legacy-flow): 廃止されたプランナー／リサーチャーステージの進捗管理を
    # 後方互換のために保持しています。
    research_progress: Optional[Dict[str, Any]] = None # リサーチ進捗状況
    executing_step: Optional[str] = None  # 現在実行中のステップ（重複実行防止用）
    sections_progress: Optional[Dict[str, Any]] = None # セクション執筆進捗状況
    
    # --- WebSocket/インタラクション用 ---
    websocket: Optional[WebSocket] = None # WebSocket接続オブジェクト
    user_response_event: Optional[asyncio.Event] = None # ユーザー応答待ち用イベント
    expected_user_input: Optional[UserInputType] = None # 現在待っている入力タイプ
    user_response: Optional[ClientResponsePayload] = None # ユーザーからの応答ペイロード
    user_id: Optional[str] = None # ユーザーID (認証から取得)
    process_id: Optional[str] = None # プロセスID (記事生成セッション識別用)
    trace_id: Optional[str] = None  # OpenAI Agents トレースID（プロセス全体で共有）
    enable_final_editing: bool = False  # 最終編集エージェントを実行するか

    # --- 以下、既存のメソッド ---
    def __post_init__(self):
        # target_age_group / persona_type を代表値＋配列の両方に正規化
        if isinstance(self.target_age_group, list):
            self.target_age_groups = [v for v in self.target_age_group if v is not None]
            self.target_age_group = self.target_age_groups[0] if self.target_age_groups else None
        elif self.target_age_group and not self.target_age_groups:
            self.target_age_groups = [self.target_age_group]

        if isinstance(self.persona_type, list):
            self.persona_types = [v for v in self.persona_type if v is not None]
            self.persona_type = self.persona_types[0] if self.persona_types else None
        elif self.persona_type and not self.persona_types:
            self.persona_types = [self.persona_type]

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

    def reset_after_theme_selection(self) -> None:
        """テーマを変更した際に、リサーチ・アウトライン以降の状態を初期化する。"""
        # 注意(legacy-flow): 旧プランナー／リサーチャーフローで作成されたスナップショットを
        # 現行フローでも安全に復元できるよう、当時のフィールドをクリアします。
        self.research_plan = None
        self.research_progress = None
        self.research_query_results = []
        self.current_research_query_index = 0
        self.research_report = None
        self.research_sources_text = None
        self.research_sources_tagged = None

        self.generated_outline = None
        self.outline = None
        self.generated_sections = []
        self.generated_sections_html = []
        self.current_section_index = 0
        self.sections_progress = None

        self.executing_step = None
        self.full_draft_html = None
        self.final_article = None
        self.final_article_html = None
        self.final_article_id = None
        self.last_agent_output = None
        self.section_writer_history = []

    # yield_sse_event は article_service 内のヘルパー関数 _send_server_event に置き換え
