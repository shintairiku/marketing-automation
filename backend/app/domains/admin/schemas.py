# -*- coding: utf-8 -*-
"""
Admin domain schemas
"""

from pydantic import BaseModel, Field
from typing import Any, Optional, Literal
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


class BlogTraceLlmCall(BaseModel):
    """Detailed LLM call log for trace view"""

    id: str
    execution_id: str
    call_sequence: int = 1
    api_type: str = "responses_api"
    model_name: str
    provider: str = "openai"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    estimated_cost_usd: float = 0.0
    api_response_id: Optional[str] = None
    called_at: Optional[datetime] = None
    response_data: dict[str, Any] = Field(default_factory=dict)


class BlogTraceToolCall(BaseModel):
    """Detailed tool call log for trace view"""

    id: str
    execution_id: str
    call_sequence: int = 1
    tool_name: str
    tool_function: str
    status: str = "started"
    input_parameters: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: Optional[int] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    called_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tool_metadata: dict[str, Any] = Field(default_factory=dict)


class BlogTraceEvent(BaseModel):
    """Normalized stream event for admin trace view"""

    id: str
    execution_id: Optional[str] = None
    event_sequence: int
    source: str
    event_type: str
    event_name: Optional[str] = None
    agent_name: Optional[str] = None
    role: Optional[str] = None
    message_text: Optional[str] = None
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    response_id: Optional[str] = None
    model_name: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] = Field(default_factory=dict)
    event_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class BlogUsageTraceExecution(BaseModel):
    """Execution with nested llm/tool logs"""

    id: str
    step_number: int
    sub_step_number: int = 1
    status: str
    llm_model: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_tokens: int = 0
    reasoning_tokens: int = 0
    llm_calls: list[BlogTraceLlmCall] = Field(default_factory=list)
    tool_calls: list[BlogTraceToolCall] = Field(default_factory=list)


class BlogUsageTraceResponse(BaseModel):
    """Detailed trace payload for one blog process"""

    process_id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    session_id: Optional[str] = None
    session_status: Optional[str] = None
    session_created_at: Optional[datetime] = None
    session_completed_at: Optional[datetime] = None
    initial_input: dict[str, Any] = Field(default_factory=dict)
    session_metadata: dict[str, Any] = Field(default_factory=dict)
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    last_response_id: Optional[str] = None
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    estimated_cost_usd: float = 0.0
    executions: list[BlogUsageTraceExecution] = Field(default_factory=list)
    trace_events: list[BlogTraceEvent] = Field(default_factory=list)


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
