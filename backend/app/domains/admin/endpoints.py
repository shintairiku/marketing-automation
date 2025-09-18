# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends

from app.common.auth import get_current_admin_user
from app.domains.admin.auth.clerk_validator import AdminUser


router = APIRouter()


@router.get("/ping", tags=["Admin"])
async def admin_ping(admin_user: AdminUser = Depends(get_current_admin_user)):
    """Admin ping endpoint using FastAPI dependency injection"""
    return {"message": "admin pong", "user_id": admin_user.user_id}


