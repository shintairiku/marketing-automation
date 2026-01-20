# -*- coding: utf-8 -*-
"""
Admin domain API endpoints
"""
from fastapi import APIRouter, Depends
import logging

from app.common.admin_auth import get_admin_user_email_from_token
from app.domains.admin.service import admin_service
from app.domains.admin.schemas import UserListResponse

logger = logging.getLogger(__name__)

# Create router with admin prefix
router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users", response_model=UserListResponse)
async def get_users(
    admin_email: str = Depends(get_admin_user_email_from_token)
):
    """
    Get all users (admin only)
    
    Requires @shintairiku.jp email domain
    """
    logger.info(f"Admin user {admin_email} requested user list")
    
    try:
        users = admin_service.get_all_users()
        return UserListResponse(
            users=users,
            total=len(users)
        )
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise

