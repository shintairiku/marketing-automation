# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from typing import List, Optional

class GenerateArticleRequest(BaseModel):
    """記事生成APIリクエストモデル"""
    initial_keywords: List[str] = Field(..., description="記事生成の元となるキーワードリスト", examples=[["札幌", "注文住宅", "自然素材", "子育て"]])
    target_persona: Optional[str] = Field(None, description="ターゲットペルソナ", examples=["札幌近郊で自然素材を使った家づくりに関心がある、小さな子供を持つ30代夫婦"])
    target_length: Optional[int] = Field(None, description="目標文字数（目安）", examples=[3000])
    num_theme_proposals: int = Field(3, description="生成するテーマ案の数", ge=1)
    num_research_queries: int = Field(5, description="リサーチで使用する検索クエリ数", ge=1)
    company_name: Optional[str] = Field(None, description="クライアント企業名（指定があれば）", examples=["株式会社ナチュラルホームズ札幌"])
    company_description: Optional[str] = Field(None, description="クライアント企業概要（指定があれば）")
    company_style_guide: Optional[str] = Field(None, description="クライアント企業の文体・トンマナガイド（指定があれば）")
    # vector_store_id: Optional[str] = Field(None, description="File Searchで使用するVector Store ID") # 必要なら追加

    class Config:
        json_schema_extra = {
            "example": {
                "initial_keywords": ["札幌", "注文住宅", "自然素材", "子育て"],
                "target_persona": "札幌近郊で自然素材を使った家づくりに関心がある、小さな子供を持つ30代夫婦",
                "target_length": 3000,
                "num_theme_proposals": 3,
                "num_research_queries": 5,
                "company_name": "株式会社ナチュラルホームズ札幌",
                "company_description": "札幌を拠点に、自然素材を活かした健康で快適な注文住宅を提供しています。",
                "company_style_guide": "専門用語を避け、温かみのある丁寧語（ですます調）で。子育て世代の読者に寄り添い、安心感を与えるようなトーンを心がける。"
            }
        }
