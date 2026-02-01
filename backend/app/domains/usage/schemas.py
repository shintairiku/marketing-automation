# -*- coding: utf-8 -*-
"""
Usage domain schemas
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UsageInfo(BaseModel):
    """現在の使用量情報"""
    articles_generated: int = 0
    articles_limit: int = 0
    addon_articles_limit: int = 0
    total_limit: int = 0
    remaining: int = 0
    billing_period_start: Optional[datetime] = None
    billing_period_end: Optional[datetime] = None
    plan_tier: Optional[str] = None


class UsageLimitResult(BaseModel):
    """使用量チェック結果"""
    allowed: bool
    current: int = 0
    limit: int = 0
    remaining: int = 0


class AdminUsageStats(BaseModel):
    """管理者向け使用量統計"""
    total_articles_this_month: int = 0
    total_articles_last_month: int = 0
    articles_growth_rate: float = 0.0
    users_near_limit: int = 0


class AdminUserUsage(BaseModel):
    """管理者向けユーザー別使用量"""
    user_id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    articles_generated: int = 0
    articles_limit: int = 0
    addon_articles_limit: int = 0
    total_limit: int = 0
    usage_percentage: float = 0.0
    plan_tier: Optional[str] = None
    billing_period_end: Optional[datetime] = None
