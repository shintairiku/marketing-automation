from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
from enum import Enum

class TargetPersona(str, Enum):
    """ターゲットペルソナの選択肢"""
    SMALL_BUSINESS_OWNER = "中小企業の経営者"
    LARGE_COMPANY_STAFF = "大企業の担当者"
    INDIVIDUAL_BUSINESS = "個人事業主"
    MARKETING_STAFF = "マーケティング担当者"
    HOUSEWIFE = "主婦"
    STUDENT = "学生"
    SENIOR = "シニア層"
    GENERAL_CONSUMER = "一般消費者"

class CompanyInfoBase(BaseModel):
    """会社情報の基本スキーマ"""
    name: str = Field(..., description="会社名", max_length=200)
    website_url: HttpUrl = Field(..., description="企業HP URL")
    description: str = Field(..., description="会社概要", max_length=2000)
    usp: str = Field(..., description="USP（企業の強み・差別化ポイント）", max_length=1000)
    target_persona: str = Field(..., description="ターゲットペルソナ", max_length=1000)
    
    # 詳細設定（任意項目）
    brand_slogan: Optional[str] = Field(None, description="ブランドスローガン／キャッチコピー", max_length=200)
    target_keywords: Optional[str] = Field(None, description="上位表示を狙いたいキーワード", max_length=500)
    industry_terms: Optional[str] = Field(None, description="業界特有の専門用語リスト", max_length=500)
    avoid_terms: Optional[str] = Field(None, description="避けたい表現・NGワードリスト", max_length=500)
    popular_articles: Optional[str] = Field(None, description="過去に人気だった記事タイトル・URL", max_length=1000)
    target_area: Optional[str] = Field(None, description="ターゲットエリア・エリアキーワード", max_length=200)

class CompanyInfoCreate(CompanyInfoBase):
    """会社情報作成用スキーマ"""
    is_default: Optional[bool] = Field(False, description="デフォルト会社として設定するか")

class CompanyInfoUpdate(BaseModel):
    """会社情報更新用スキーマ（部分更新対応）"""
    name: Optional[str] = Field(None, description="会社名", max_length=200)
    website_url: Optional[HttpUrl] = Field(None, description="企業HP URL")
    description: Optional[str] = Field(None, description="会社概要", max_length=2000)
    usp: Optional[str] = Field(None, description="USP（企業の強み・差別化ポイント）", max_length=1000)
    target_persona: Optional[str] = Field(None, description="ターゲットペルソナ", max_length=1000)
    is_default: Optional[bool] = Field(None, description="デフォルト会社として設定するか")
    
    # 詳細設定（任意項目）
    brand_slogan: Optional[str] = Field(None, description="ブランドスローガン／キャッチコピー", max_length=200)
    target_keywords: Optional[str] = Field(None, description="上位表示を狙いたいキーワード", max_length=500)
    industry_terms: Optional[str] = Field(None, description="業界特有の専門用語リスト", max_length=500)
    avoid_terms: Optional[str] = Field(None, description="避けたい表現・NGワードリスト", max_length=500)
    popular_articles: Optional[str] = Field(None, description="過去に人気だった記事タイトル・URL", max_length=1000)
    target_area: Optional[str] = Field(None, description="ターゲットエリア・エリアキーワード", max_length=200)

class CompanyInfoResponse(CompanyInfoBase):
    """会社情報レスポンス用スキーマ"""
    id: str = Field(..., description="会社情報ID")
    user_id: str = Field(..., description="ユーザーID")
    is_default: bool = Field(..., description="デフォルト会社かどうか")
    created_at: datetime = Field(..., description="作成日時")
    updated_at: datetime = Field(..., description="更新日時")

    class Config:
        from_attributes = True

class CompanyInfoList(BaseModel):
    """会社情報一覧レスポンス用スキーマ"""
    companies: List[CompanyInfoResponse] = Field(..., description="会社情報一覧")
    total: int = Field(..., description="総件数")
    default_company_id: Optional[str] = Field(None, description="デフォルト会社のID")

class SetDefaultCompanyRequest(BaseModel):
    """デフォルト会社設定用スキーマ"""
    company_id: str = Field(..., description="デフォルトに設定する会社ID")