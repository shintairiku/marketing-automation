# -*- coding: utf-8 -*-
"""
Admin domain schemas
"""
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

# サブスクリプションステータスの型定義
SubscriptionStatusType = Literal["active", "past_due", "canceled", "expired", "none"]

class UserRead(BaseModel):
    """User read schema with subscription info"""
    id: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None

    # サブスクリプション関連
    subscription_status: SubscriptionStatusType = "none"
    is_privileged: bool = False
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False

    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    """User list response schema"""
    users: list[UserRead]
    total: int

class UpdateUserPrivilegeRequest(BaseModel):
    """Request to update user privilege status"""
    is_privileged: bool

class UpdateUserSubscriptionRequest(BaseModel):
    """Request to update user subscription status"""
    status: SubscriptionStatusType
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False

class UserUpdateResponse(BaseModel):
    """Response after updating user"""
    success: bool
    message: str
    user: Optional[UserRead] = None


# ============================================
# 管理者ダッシュボード統計スキーマ
# ============================================

class OverviewStats(BaseModel):
    """Dashboard overview KPI stats"""
    total_users: int = 0
    new_users_this_month: int = 0
    active_subscribers: int = 0
    privileged_users: int = 0
    none_users: int = 0
    total_articles_this_month: int = 0
    articles_prev_month: int = 0
    estimated_mrr: int = 0  # 月間収益（円）

class DailyGenerationCount(BaseModel):
    """Daily article generation count"""
    date: str  # YYYY-MM-DD
    count: int = 0

class GenerationTrendResponse(BaseModel):
    """Generation trend response"""
    daily: list[DailyGenerationCount]
    total: int = 0

class SubscriptionDistribution(BaseModel):
    """Subscription status distribution"""
    status: str
    count: int
    label: str

class SubscriptionDistributionResponse(BaseModel):
    """Distribution response"""
    distribution: list[SubscriptionDistribution]

class RecentActivity(BaseModel):
    """Recent activity entry"""
    type: str  # 'generation', 'subscription_change'
    user_id: str
    user_email: Optional[str] = None
    description: str
    timestamp: Optional[datetime] = None

class RecentActivityResponse(BaseModel):
    """Recent activity response"""
    activities: list[RecentActivity]

class UserUsageItem(BaseModel):
    """Per-user usage for admin"""
    user_id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    articles_generated: int = 0
    total_limit: int = 0
    usage_percentage: float = 0.0


class UserUsageDetail(BaseModel):
    """Detailed usage info for a specific user"""
    articles_generated: int = 0
    articles_limit: int = 0
    addon_articles_limit: int = 0
    total_limit: int = 0
    remaining: int = 0
    billing_period_start: Optional[str] = None
    billing_period_end: Optional[str] = None
    plan_tier_id: Optional[str] = None


class UserGenerationHistory(BaseModel):
    """Blog generation history entry"""
    process_id: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserDetailResponse(BaseModel):
    """Detailed user info for admin user detail page"""
    user: UserRead
    usage: Optional[UserUsageDetail] = None
    generation_history: list[UserGenerationHistory] = []
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    addon_quantity: int = 0
    plan_tier_name: Optional[str] = None
