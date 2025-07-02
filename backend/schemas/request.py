# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class AgeGroup(str, Enum):
    TEENS = "10代"
    TWENTIES = "20代"
    THIRTIES = "30代"
    FORTIES = "40代"
    FIFTIES = "50代"
    SIXTIES = "60代"
    SEVENTIES_OR_OLDER = "70代以上"

class PersonaType(str, Enum):
    HOUSEWIFE = "主婦"
    STUDENT = "学生"
    OFFICE_WORKER = "社会人"
    SELF_EMPLOYED = "自営業"
    EXECUTIVE = "経営者・役員"
    RETIREE = "退職者"
    OTHER = "その他" # ユーザーが独自に設定する場合

class GenerateArticleRequest(BaseModel):
    """記事生成APIリクエストモデル"""
    initial_keywords: List[str] = Field(..., description="記事生成の元となるキーワードリスト", examples=[["札幌", "注文住宅", "自然素材", "子育て"]])
    target_age_group: Optional[AgeGroup] = Field(None, description="ターゲット年代層")
    persona_type: Optional[PersonaType] = Field(None, description="ペルソナ属性")
    custom_persona: Optional[str] = Field(None, description="独自に設定したペルソナ（persona_typeがOTHERの場合に利用）", examples=["札幌近郊で自然素材を使った家づくりに関心がある、小さな子供を持つ30代夫婦"])
    target_length: Optional[int] = Field(None, description="目標文字数（目安）", examples=[3000])
    num_theme_proposals: int = Field(3, description="生成するテーマ案の数", ge=1)
    num_research_queries: int = Field(3, description="リサーチで使用する検索クエリ数", ge=1) # デフォルト値を3に設定
    num_persona_examples: int = Field(3, description="生成する具体的なペルソナの数", ge=1) # 新パラメータ、デフォルト3
    company_name: Optional[str] = Field(None, description="クライアント企業名（指定があれば）", examples=["株式会社ナチュラルホームズ札幌"])
    company_description: Optional[str] = Field(None, description="クライアント企業概要（指定があれば）")
    company_style_guide: Optional[str] = Field(None, description="クライアント企業の文体・トンマナガイド（指定があれば）")
    # vector_store_id: Optional[str] = Field(None, description="File Searchで使用するVector Store ID") # 必要なら追加
    
    # --- 画像モード関連 (新規追加) ---
    image_mode: bool = Field(False, description="画像プレースホルダー機能を使用するかどうか")
    image_settings: Optional[dict] = Field(None, description="画像生成設定")
    
    # --- スタイルテンプレート関連 (新規追加) ---
    style_template_id: Optional[str] = Field(None, description="使用するスタイルテンプレートのID")

    class Config:
        json_schema_extra = {
            "example": {
                "initial_keywords": ["札幌", "注文住宅", "自然素材", "子育て"],
                "target_age_group": AgeGroup.THIRTIES,
                "persona_type": PersonaType.HOUSEWIFE,
                "custom_persona": "札幌近郊で自然素材を使った家づくりに関心がある、小さな子供を持つ30代夫婦",
                "target_length": 3000,
                "num_theme_proposals": 3,
                "num_research_queries": 3,
                "num_persona_examples": 3,
                "company_name": "株式会社ナチュラルホームズ札幌",
                "company_description": "札幌を拠点に、自然素材を活かした健康で快適な注文住宅を提供しています。",
                "image_mode": False,
                "image_settings": {},
                "company_style_guide": "専門用語を避け、温かみのある丁寧語（ですます調）で。子育て世代の読者に寄り添い、安心感を与えるようなトーンを心がける。"
            }
        }
