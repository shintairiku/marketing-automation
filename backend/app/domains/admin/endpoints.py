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
    UserDetailResponse,
    UpdateUserPrivilegeRequest,
    UpdateUserSubscriptionRequest,
    UserUpdateResponse,
    OverviewStats,
    GenerationTrendResponse,
    SubscriptionDistributionResponse,
    RecentActivityResponse,
    UserUsageItem,
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


@router.get("/users/{user_id}/detail", response_model=UserDetailResponse)
async def get_user_detail(
    user_id: str,
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """
    Get detailed user info including usage, generation history, org info (admin only)
    """
    logger.info(f"Admin user {admin_email} requested user detail for {user_id}")

    try:
        detail = admin_service.get_user_detail(user_id)
        if not detail:
            raise HTTPException(status_code=404, detail="User not found")
        return detail
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user detail {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user detail")


@router.get("/stats/overview", response_model=OverviewStats)
async def get_overview_stats(
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """Get dashboard overview statistics (admin only)"""
    logger.info(f"Admin user {admin_email} requested overview stats")
    try:
        return admin_service.get_overview_stats()
    except Exception as e:
        logger.error(f"Error getting overview stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get overview stats")


@router.get("/stats/generation-trend", response_model=GenerationTrendResponse)
async def get_generation_trend(
    days: int = 30,
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """Get daily article generation trend (admin only)"""
    logger.info(f"Admin user {admin_email} requested generation trend ({days} days)")
    try:
        return admin_service.get_generation_trend(days=days)
    except Exception as e:
        logger.error(f"Error getting generation trend: {e}")
        raise HTTPException(status_code=500, detail="Failed to get generation trend")


@router.get("/stats/subscription-distribution", response_model=SubscriptionDistributionResponse)
async def get_subscription_distribution(
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """Get subscription status distribution (admin only)"""
    logger.info(f"Admin user {admin_email} requested subscription distribution")
    try:
        return admin_service.get_subscription_distribution()
    except Exception as e:
        logger.error(f"Error getting subscription distribution: {e}")
        raise HTTPException(status_code=500, detail="Failed to get distribution")


@router.get("/activity/recent", response_model=RecentActivityResponse)
async def get_recent_activity(
    limit: int = 20,
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """Get recent activity (admin only)"""
    logger.info(f"Admin user {admin_email} requested recent activity")
    try:
        return admin_service.get_recent_activity(limit=limit)
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recent activity")


@router.get("/usage/users", response_model=list[UserUsageItem])
async def get_users_usage(
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """Get per-user usage list (admin only)"""
    logger.info(f"Admin user {admin_email} requested users usage")
    try:
        return admin_service.get_users_usage()
    except Exception as e:
        logger.error(f"Error getting users usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to get users usage")


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
