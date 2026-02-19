# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class InquiryCategory(str, Enum):
    """お問い合わせカテゴリ"""
    GENERAL = "general"
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    BILLING = "billing"
    OTHER = "other"


class InquiryStatus(str, Enum):
    """お問い合わせステータス"""
    NEW = "new"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ContactInquiryCreate(BaseModel):
    """お問い合わせ作成スキーマ"""
    category: InquiryCategory = Field(default=InquiryCategory.GENERAL, description="カテゴリ")
    subject: str = Field(..., description="件名", min_length=1, max_length=200)
    message: str = Field(..., description="お問い合わせ内容", min_length=1, max_length=5000)


class ContactInquiryResponse(BaseModel):
    """お問い合わせレスポンス"""
    id: str
    user_id: str
    user_email: str
    user_name: Optional[str] = None
    category: str
    subject: str
    message: str
    status: str
    admin_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContactInquiryList(BaseModel):
    """お問い合わせ一覧レスポンス"""
    inquiries: List[ContactInquiryResponse]
    total: int


class ContactInquiryStatusUpdate(BaseModel):
    """ステータス更新スキーマ"""
    status: InquiryStatus = Field(..., description="新しいステータス")
    admin_notes: Optional[str] = Field(None, description="管理者メモ", max_length=2000)
