# -*- coding: utf-8 -*-
"""
Admin domain schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserRead(BaseModel):
    """User read schema"""
    id: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    """User list response schema"""
    users: list[UserRead]
    total: int

