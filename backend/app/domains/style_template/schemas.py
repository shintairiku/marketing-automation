# -*- coding: utf-8 -*-
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class AutoStyleTemplateRequest(BaseModel):
    """スタイルテンプレート自動入力リクエスト"""
    website_url: HttpUrl = Field(..., description="企業HP URL")
    fields: List[str] = Field(..., description="充実化するフィールドのリスト")


class AutoStyleTemplateResponse(BaseModel):
    """スタイルテンプレート自動入力レスポンス"""
    tone: Optional[str] = Field(None, description="トーン・調子")
    style: Optional[str] = Field(None, description="文体")
    approach: Optional[str] = Field(None, description="アプローチ・方針")
    vocabulary: Optional[str] = Field(None, description="語彙・表現の指針")
    structure: Optional[str] = Field(None, description="記事構成の指針")
    special_instructions: Optional[str] = Field(None, description="特別な指示")
