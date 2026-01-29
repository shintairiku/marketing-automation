# -*- coding: utf-8 -*-
"""
Admin domain API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
import logging

from app.common.admin_auth import get_admin_user_email_from_token
from app.domains.admin.service import admin_service
from app.domains.admin.schemas import (
    UserListResponse,
    UserRead,
    UpdateUserPrivilegeRequest,
    UpdateUserSubscriptionRequest,
    UserUpdateResponse,
)

logger = logging.getLogger(__name__)

# Create router with admin prefix
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=UserListResponse)
async def get_users(
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """
    Get all users with subscription info (admin only)

    Requires @shintairiku.jp email domain
    """
    logger.info(f"Admin user {admin_email} requested user list")

    try:
        users = admin_service.get_all_users()
        return UserListResponse(users=users, total=len(users))
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(status_code=500, detail="Failed to get users")


@router.get("/users/{user_id}", response_model=UserRead)
async def get_user(
    user_id: str,
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """
    Get a specific user by ID (admin only)

    Requires @shintairiku.jp email domain
    """
    logger.info(f"Admin user {admin_email} requested user {user_id}")

    try:
        user = admin_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user")


@router.patch("/users/{user_id}/privilege", response_model=UserUpdateResponse)
async def update_user_privilege(
    user_id: str,
    request: UpdateUserPrivilegeRequest,
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """
    Update user privilege status (is_privileged) (admin only)

    Requires @shintairiku.jp email domain
    """
    logger.info(
        f"Admin user {admin_email} updating privilege for user {user_id}: {request.is_privileged}"
    )

    try:
        user = admin_service.update_user_privilege(user_id, request)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserUpdateResponse(
            success=True,
            message=f"Privilege updated: is_privileged={request.is_privileged}",
            user=user,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating privilege for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update privilege")


@router.patch("/users/{user_id}/subscription", response_model=UserUpdateResponse)
async def update_user_subscription(
    user_id: str,
    request: UpdateUserSubscriptionRequest,
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """
    Update user subscription status (admin only)

    Requires @shintairiku.jp email domain
    """
    logger.info(
        f"Admin user {admin_email} updating subscription for user {user_id}: {request.status}"
    )

    try:
        user = admin_service.update_user_subscription(user_id, request)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserUpdateResponse(
            success=True,
            message=f"Subscription updated: status={request.status}",
            user=user,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update subscription")
