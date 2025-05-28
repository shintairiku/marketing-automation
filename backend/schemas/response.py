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

class ErrorPayload(BasePayload):
    """エラーペイロード"""
    step: str = Field(description="エラーが発生したステップ")
    error_message: str = Field(description="エラーメッセージ")

class UserInputType(str, Enum):
    """クライアントに要求する入力の種類"""
    SELECT_PERSONA = "select_persona"
    SELECT_THEME = "select_theme"
    APPROVE_PLAN = "approve_plan"
    APPROVE_OUTLINE = "approve_outline"
    # 今後、他の入力タイプを追加可能

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

# クライアントから送信される応答ペイロードのUnion型
ClientResponsePayload = Union[
    SelectPersonaPayload,
    SelectThemePayload,
    ApprovePayload,
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

