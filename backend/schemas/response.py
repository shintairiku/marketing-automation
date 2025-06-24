# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field, field_validator
from typing import Any, Literal, Optional, Dict, List, Union
from enum import Enum

# --- 共通モデル ---
class BasePayload(BaseModel):
    """WebSocketメッセージペイロードの基底クラス"""
    pass

# --- サーバー -> クライアント イベントペイロード ---
class StatusUpdatePayload(BasePayload):
    """ステータス更新ペイロード"""
    step: str = Field(description="現在の処理ステップ名")
    message: str = Field(description="処理状況に関するメッセージ")
    image_mode: Optional[bool] = Field(None, description="画像モードが有効かどうか")

class ThemeProposalData(BaseModel): # services.models.ThemeIdea と同期
    title: str
    description: str
    keywords: List[str]

class ThemeProposalPayload(BasePayload):
    """テーマ提案ペイロード (選択要求時に使用)"""
    themes: List[ThemeProposalData] = Field(description="提案されたテーマ案")

class ResearchPlanQueryData(BaseModel): # services.models.ResearchQuery と同期
    query: str
    focus: str

class ResearchPlanData(BaseModel): # services.models.ResearchPlan と同期 (status除く)
    topic: str
    queries: List[ResearchPlanQueryData]

class ResearchPlanPayload(BasePayload):
    """リサーチ計画ペイロード (承認要求時に使用)"""
    plan: ResearchPlanData = Field(description="生成されたリサーチ計画")

class ResearchProgressPayload(BasePayload):
    """リサーチ進捗ペイロード"""
    query_index: int = Field(description="現在実行中のクエリインデックス (0ベース)")
    total_queries: int = Field(description="総クエリ数")
    query: str = Field(description="実行中のクエリ文字列")

class KeyPointData(BaseModel): # services.models.KeyPoint と同期
    point: str
    supporting_sources: List[str]

class ResearchReportData(BaseModel): # services.models.ResearchReport と同期 (status除く)
    topic: str
    overall_summary: str
    key_points: List[KeyPointData]
    interesting_angles: List[str]
    all_sources: List[str]

class ResearchCompletePayload(BasePayload):
    """リサーチ完了ペイロード (情報提供用)"""
    report: ResearchReportData = Field(description="生成されたリサーチレポート")

class OutlineSectionData(BaseModel): # services.models.OutlineSection と同期 (再帰定義)
    heading: str
    estimated_chars: Optional[int] = None
    subsections: Optional[List['OutlineSectionData']] = None # 再帰的な型ヒント

class OutlineData(BaseModel): # services.models.Outline と同期 (status除く)
    title: str
    suggested_tone: str
    sections: List[OutlineSectionData]

class OutlinePayload(BasePayload):
    """アウトラインペイロード (承認要求時に使用)"""
    outline: OutlineData = Field(description="生成されたアウトライン")

class SectionChunkPayload(BasePayload):
    """セクションHTMLチャンクペイロード (ストリーミング用)"""
    section_index: int = Field(description="生成中のセクションインデックス (0ベース)")
    heading: str = Field(description="生成中のセクションの見出し")
    html_content_chunk: str = Field(description="生成されたHTMLコンテンツの断片")
    is_complete: bool = Field(False, description="このセクションの生成が完了したか")

class EditingStartPayload(BasePayload):
    """編集開始ペイロード"""
    message: str = "最終編集を開始します..."

class FinalResultPayload(BasePayload):
    """最終結果ペイロード"""
    title: str = Field(description="最終的な記事タイトル")
    final_html_content: str = Field(description="完成した記事のHTMLコンテンツ")
    # 新規追加: DBに保存された記事ID (フロントエンドで編集ページへ遷移する際に使用)
    article_id: Optional[str] = Field(default=None, description="生成された記事の一意ID")

class ErrorPayload(BasePayload):
    """エラーペイロード"""
    step: str = Field(description="エラーが発生したステップ")
    error_message: str = Field(description="エラーメッセージ")

# 新しいペイロード: SerpAPIキーワード分析結果
class SerpAnalysisArticleData(BaseModel):
    """SerpAPI分析記事データ"""
    url: str
    title: str
    headings: List[str]
    content_preview: str
    char_count: int
    image_count: int
    source_type: str
    position: Optional[int] = None
    question: Optional[str] = None

class SerpKeywordAnalysisPayload(BasePayload):
    """SerpAPIキーワード分析結果ペイロード"""
    search_query: str = Field(description="実行した検索クエリ")
    total_results: int = Field(description="検索結果の総数")
    analyzed_articles: List[SerpAnalysisArticleData] = Field(description="分析対象記事のリスト")
    average_article_length: int = Field(description="分析した記事の平均文字数")
    recommended_target_length: int = Field(description="推奨記事文字数")
    main_themes: List[str] = Field(description="上位記事で頻出する主要テーマ")
    common_headings: List[str] = Field(description="上位記事で共通して使用される見出しパターン")
    content_gaps: List[str] = Field(description="上位記事で不足している可能性のあるコンテンツ")
    competitive_advantages: List[str] = Field(description="差別化できる可能性のあるポイント")
    user_intent_analysis: str = Field(description="検索ユーザーの意図分析")
    content_strategy_recommendations: List[str] = Field(description="コンテンツ戦略の推奨事項")

class UserInputType(str, Enum):
    """クライアントに要求する入力の種類"""
    SELECT_PERSONA = "select_persona"
    SELECT_THEME = "select_theme"
    APPROVE_PLAN = "approve_plan"
    APPROVE_OUTLINE = "approve_outline"
    REGENERATE = "regenerate"
    EDIT_AND_PROCEED = "edit_and_proceed"
    # 個別編集系
    EDIT_PERSONA = "edit_persona"
    EDIT_THEME = "edit_theme"
    EDIT_PLAN = "edit_plan"
    EDIT_OUTLINE = "edit_outline"
    EDIT_GENERIC = "edit_generic"

class UserInputRequestPayload(BasePayload):
    """ユーザー入力要求ペイロード"""
    request_type: UserInputType = Field(description="要求する入力の種類")
    data: Optional[Dict[str, Any]] = Field(None, description="入力要求に関連するデータ (テーマ案リスト、計画詳細など)")

# 新しいペイロード: 生成されたペルソナリスト (クライアント送信用)
class GeneratedPersonaData(BaseModel):
    id: int
    description: str

class GeneratedPersonasPayload(BasePayload):
    """生成されたペルソナリストペイロード (選択要求時に使用)"""
    personas: List[GeneratedPersonaData] = Field(description="生成された具体的なペルソナのリスト")

# サーバーから送信されるイベントペイロードのUnion型
ServerEventPayload = Union[
    StatusUpdatePayload,
    SerpKeywordAnalysisPayload,
    GeneratedPersonasPayload,
    ThemeProposalPayload, # 選択要求時に使用
    ResearchPlanPayload,  # 承認要求時に使用
    ResearchProgressPayload,
    ResearchCompletePayload,
    OutlinePayload,       # 承認要求時に使用
    SectionChunkPayload,
    EditingStartPayload,
    FinalResultPayload,
    ErrorPayload,
    UserInputRequestPayload, # ユーザー入力を要求するイベント
]

# --- クライアント -> サーバー 応答ペイロード ---
class SelectPersonaPayload(BasePayload):
    """ペルソナ選択応答ペイロード"""
    selected_id: int = Field(description="ユーザーが選択したペルソナのID (0ベース)", ge=0)

class SelectThemePayload(BasePayload):
    """テーマ選択応答ペイロード"""
    selected_index: int = Field(description="ユーザーが選択したテーマのインデックス (0ベース)", ge=0)

class ApprovePayload(BasePayload):
    """承認/拒否応答ペイロード"""
    approved: bool = Field(description="承認したかどうか")
    # reason: Optional[str] = Field(None, description="拒否した場合の理由など (任意)")

# 新しいクライアント応答ペイロード
class RegeneratePayload(BasePayload):
    """再生成要求ペイロード (特定のステップの再生成を意図)"""
    # 現状、どのステップを再生成するかはサーバー側のコンテキストで判断するため、
    # このペイロード自体に特別なフィールドは不要かもしれない。
    # 必要であれば、再生成対象のステップを示すフィールドを追加する。
    pass # シンプルにするため、一旦フィールドなし

class EditAndProceedPayload(BasePayload):
    """編集して進行要求ペイロード"""
    # edited_step: UserInputType = Field(description="どのステップの内容を編集したか") # server_service側で判断
    edited_content: Dict[str, Any] = Field(description="ユーザーによって編集された内容")

# 個別編集用ペイロード
class EditPersonaPayload(BasePayload):
    """ペルソナ編集ペイロード"""
    edited_persona: Dict[str, Any] = Field(description="編集されたペルソナ")

class EditThemePayload(BasePayload):
    """テーマ編集ペイロード"""
    edited_theme: Dict[str, Any] = Field(description="編集されたテーマ")

class EditPlanPayload(BasePayload):
    """計画編集ペイロード"""
    edited_plan: Dict[str, Any] = Field(description="編集された計画")

class EditOutlinePayload(BasePayload):
    """アウトライン編集ペイロード"""
    edited_outline: Dict[str, Any] = Field(description="編集されたアウトライン")

# クライアントから送信される応答ペイロードのUnion型
ClientResponsePayload = Union[
    SelectPersonaPayload,
    SelectThemePayload,
    ApprovePayload,
    RegeneratePayload,
    EditAndProceedPayload,
    EditPersonaPayload,
    EditThemePayload,
    EditPlanPayload,
    EditOutlinePayload,
]

# --- WebSocketメッセージモデル ---
class WebSocketMessage(BaseModel):
    """WebSocketで送受信されるメッセージの基本形式"""
    type: Literal["server_event", "client_response"]
    payload: Dict[str, Any] # 実際のペイロードは type に応じて解釈

    @field_validator('payload', mode='before')
    @classmethod
    def payload_to_dict(cls, v):
        if isinstance(v, BaseModel):
            return v.model_dump()
        return v

class ServerEventMessage(WebSocketMessage):
    """サーバーからクライアントへのイベントメッセージ"""
    type: Literal["server_event"] = "server_event"
    payload: ServerEventPayload # 具体的なペイロード型

class ClientResponseMessage(WebSocketMessage):
    """クライアントからサーバーへの応答メッセージ"""
    type: Literal["client_response"] = "client_response"
    response_type: UserInputType = Field(description="どの要求に対する応答かを示す")
    payload: ClientResponsePayload # 具体的なペイロード型

# UserActionPayload は ClientResponseMessage.payload の型ヒントとして使用
UserActionPayload = ClientResponsePayload

