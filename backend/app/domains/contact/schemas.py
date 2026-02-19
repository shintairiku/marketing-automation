# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class InquiryCategory(str, Enum):
    general = "general"
    bug_report = "bug_report"
    feature_request = "feature_request"
    billing = "billing"
    account = "account"
    other = "other"


class InquiryStatus(str, Enum):
    new = "new"
    read = "read"
    replied = "replied"


class ContactInquiryCreate(BaseModel):
    name: str = Field(..., description="送信者名", max_length=100)
    email: str = Field(..., description="連絡先メールアドレス", max_length=255)
    category: InquiryCategory = Field(InquiryCategory.general, description="カテゴリ")
    subject: str = Field(..., description="件名", max_length=200)
    message: str = Field(..., description="お問い合わせ内容", max_length=5000)


class ContactInquiryResponse(BaseModel):
    id: str
    user_id: str
    name: str
    email: str
    category: str
    subject: str
    message: str
    status: str
    admin_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContactInquiryListResponse(BaseModel):
    inquiries: List[ContactInquiryResponse]
    total: int


class UpdateInquiryStatusRequest(BaseModel):
    status: InquiryStatus = Field(..., description="新しいステータス")
    admin_note: Optional[str] = Field(None, description="管理者メモ", max_length=2000)
