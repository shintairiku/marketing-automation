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
