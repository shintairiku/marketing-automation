# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field, field_validator
from typing import Any, Literal, Optional, Dict
from enum import Enum

# --- 共通モデル ---
class BasePayload(BaseModel):
    """WebSocketメッセージペイロードの基底クラス"""
    pass

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

class ErrorPayload(BasePayload):
    """エラーペイロード"""
    step: str = Field(description="エラーが発生したステップ")
    error_message: str = Field(description="エラーメッセージ")

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
    # payload: ServerEventPayload # 具体的なペイロード型は各ドメインで定義

class ClientResponseMessage(WebSocketMessage):
    """クライアントからサーバーへの応答メッセージ"""
    type: Literal["client_response"] = "client_response"
    response_type: UserInputType = Field(description="どの要求に対する応答かを示す")
    # payload: ClientResponsePayload # 具体的なペイロード型は各ドメインで定義