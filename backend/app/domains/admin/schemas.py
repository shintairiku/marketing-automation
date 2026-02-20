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


# ============================================
# プランティア管理スキーマ
# ============================================

class PlanTierRead(BaseModel):
    """Plan tier read schema"""
    id: str
    name: str
    stripe_price_id: Optional[str] = None
    monthly_article_limit: int = 0
    addon_unit_amount: int = 20
    price_amount: int = 0
    display_order: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class CreatePlanTierRequest(BaseModel):
    """Request to create a plan tier"""
    id: str
    name: str
    stripe_price_id: Optional[str] = None
    monthly_article_limit: int
    addon_unit_amount: int = 20
    price_amount: int = 0
    display_order: int = 0

class UpdatePlanTierRequest(BaseModel):
    """Request to update a plan tier"""
    name: Optional[str] = None
    stripe_price_id: Optional[str] = None
    monthly_article_limit: Optional[int] = None
    addon_unit_amount: Optional[int] = None
    price_amount: Optional[int] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None

class PlanTierListResponse(BaseModel):
    """Plan tier list response"""
    tiers: list[PlanTierRead]
    total: int

class ApplyLimitsResult(BaseModel):
    """Result of applying tier limits to active users"""
    updated_count: int
    message: str


class GrantArticlesRequest(BaseModel):
    """Request to grant additional articles to a user"""
    amount: int  # 付与する記事数

class GrantArticlesResponse(BaseModel):
    """Response after granting articles"""
    success: bool
    user_id: str
    admin_granted_articles: int = 0
    total_limit: int = 0
    articles_generated: int = 0
    remaining: int = 0
    message: str = ""

class UserUsageDetail(BaseModel):
    """Detailed usage info for a specific user"""
    articles_generated: int = 0
    articles_limit: int = 0
    addon_articles_limit: int = 0
    admin_granted_articles: int = 0
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


class BlogAiUsageStats(BaseModel):
    """Blog AI LLM usage stats"""
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    estimated_cost_usd: float = 0.0
    tool_calls: int = 0
    tools: list[dict] = []
    models: list[str] = []
    last_run_at: Optional[datetime] = None


class BlogUsageItem(BaseModel):
    """Blog AI usage entry per process"""
    process_id: str
    user_id: str
    user_email: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    estimated_cost_usd: float = 0.0
    tool_calls: int = 0
    models: list[str] = []

class UserDetailResponse(BaseModel):
    """Detailed user info for admin user detail page"""
    user: UserRead
    usage: Optional[UserUsageDetail] = None
    blog_ai_usage: Optional[BlogAiUsageStats] = None
    generation_history: list[UserGenerationHistory] = []
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    addon_quantity: int = 0
    plan_tier_name: Optional[str] = None
