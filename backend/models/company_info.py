from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from database.database import Base

class CompanyInfo(Base):
    """会社情報テーブル"""
    __tablename__ = "company_info"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)  # ClerkのユーザーID
    
    # 必須項目
    name = Column(String(200), nullable=False)
    website_url = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    usp = Column(Text, nullable=False)
    target_persona = Column(String(50), nullable=False)
    
    # デフォルト設定
    is_default = Column(Boolean, default=False, nullable=False)
    
    # 詳細設定（任意項目）
    brand_slogan = Column(String(200), nullable=True)
    target_keywords = Column(String(500), nullable=True)
    industry_terms = Column(String(500), nullable=True)
    avoid_terms = Column(String(500), nullable=True)
    popular_articles = Column(Text, nullable=True)
    target_area = Column(String(200), nullable=True)
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # インデックス
    __table_args__ = (
        Index('idx_company_info_user_id', 'user_id'),
        Index('idx_company_info_user_default', 'user_id', 'is_default'),
    )

    def __repr__(self):
        return f"<CompanyInfo(id={self.id}, name={self.name}, user_id={self.user_id}, is_default={self.is_default})>"