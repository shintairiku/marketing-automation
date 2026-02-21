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
    UpdateUserRoleRequest,
    UpdateUserRoleResponse,
    OverviewStats,
    GenerationTrendResponse,
    SubscriptionDistributionResponse,
    RecentActivityResponse,
    UserUsageItem,
    BlogUsageItem,
    PlanTierRead,
    PlanTierListResponse,
    CreatePlanTierRequest,
    UpdatePlanTierRequest,
    ApplyLimitsResult,
    GrantArticlesRequest,
    GrantArticlesResponse,
)
from app.domains.usage.service import usage_service
from app.core.config import settings

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


@router.get("/usage/blog", response_model=list[BlogUsageItem])
async def get_blog_usage(
    limit: int = 200,
    offset: int = 0,
    days: int = 30,
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """Get per-blog process usage list (admin only)"""
    logger.info(f"Admin user {admin_email} requested blog usage list (days={days})")
    try:
        return admin_service.get_blog_usage(limit=limit, offset=offset, days=days)
    except Exception as e:
        logger.error(f"Error getting blog usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to get blog usage")


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


@router.post("/users/{user_id}/grant-articles", response_model=GrantArticlesResponse)
async def grant_articles(
    user_id: str,
    request: GrantArticlesRequest,
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """
    Grant additional articles to a user (admin only)
    """
    logger.info(
        f"Admin user {admin_email} granting {request.amount} articles to user {user_id}"
    )

    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    try:
        result = usage_service.grant_articles(user_id=user_id, amount=request.amount)
        if not result:
            raise HTTPException(
                status_code=404,
                detail="User not found or no usage tracking record"
            )
        return GrantArticlesResponse(
            success=True,
            user_id=user_id,
            admin_granted_articles=result["admin_granted_articles"],
            total_limit=result["total_limit"],
            articles_generated=result["articles_generated"],
            remaining=result["remaining"],
            message=f"{request.amount}件の記事を付与しました",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error granting articles to user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to grant articles")


# ============================================
# User Role Management (Clerk publicMetadata)
# ============================================


@router.patch("/users/{user_id}/role", response_model=UpdateUserRoleResponse)
async def update_user_role(
    user_id: str,
    request: UpdateUserRoleRequest,
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """
    Update user role via Clerk publicMetadata (admin only).

    Sets publicMetadata.role on the Clerk user object.
    This is reflected in the JWT session token after the next token refresh.

    role: "admin" | "privileged" | null (null removes the role)
    """
    logger.info(
        f"Admin user {admin_email} updating role for user {user_id}: {request.role}"
    )

    try:
        import httpx

        clerk_secret_key = settings.clerk_secret_key
        if not clerk_secret_key:
            raise HTTPException(status_code=500, detail="Clerk secret key not configured")

        # Clerk Backend API: Update user metadata
        async with httpx.AsyncClient(timeout=10.0) as client:
            # まず現在のメタデータを取得
            get_response = await client.get(
                f"https://api.clerk.com/v1/users/{user_id}",
                headers={
                    "Authorization": f"Bearer {clerk_secret_key}",
                    "Content-Type": "application/json",
                }
            )

            if get_response.status_code == 404:
                raise HTTPException(status_code=404, detail="User not found in Clerk")
            get_response.raise_for_status()

            current_user = get_response.json()
            current_metadata = current_user.get("public_metadata", {})

            # role を更新（None の場合はキーを削除）
            if request.role:
                current_metadata["role"] = request.role
            else:
                current_metadata.pop("role", None)

            # Clerk API で publicMetadata を更新
            update_response = await client.patch(
                f"https://api.clerk.com/v1/users/{user_id}",
                headers={
                    "Authorization": f"Bearer {clerk_secret_key}",
                    "Content-Type": "application/json",
                },
                json={"public_metadata": current_metadata},
            )

            if update_response.status_code == 404:
                raise HTTPException(status_code=404, detail="User not found in Clerk")
            update_response.raise_for_status()

        # DB の is_privileged も同期（後方互換）
        is_privileged = request.role in ("admin", "privileged")
        admin_service.update_user_privilege(
            user_id,
            UpdateUserPrivilegeRequest(is_privileged=is_privileged),
        )

        role_label = request.role or "一般ユーザー"
        return UpdateUserRoleResponse(
            success=True,
            user_id=user_id,
            role=request.role,
            message=f"ロールを「{role_label}」に変更しました。次回のセッション更新時に反映されます。",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating role for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user role")


# ============================================
# Plan Tier Management Endpoints
# ============================================


@router.get("/plan-tiers", response_model=PlanTierListResponse)
async def get_plan_tiers(
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """Get all plan tiers (admin only)"""
    logger.info(f"Admin user {admin_email} requested plan tiers")
    try:
        tiers = admin_service.get_all_plan_tiers()
        return PlanTierListResponse(tiers=tiers, total=len(tiers))
    except Exception as e:
        logger.error(f"Error getting plan tiers: {e}")
        raise HTTPException(status_code=500, detail="Failed to get plan tiers")


@router.post("/plan-tiers", response_model=PlanTierRead, status_code=201)
async def create_plan_tier(
    request: CreatePlanTierRequest,
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """Create a new plan tier (admin only)"""
    logger.info(f"Admin user {admin_email} creating plan tier: {request.id}")
    try:
        return admin_service.create_plan_tier(request)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating plan tier: {e}")
        raise HTTPException(status_code=500, detail="Failed to create plan tier")


@router.patch("/plan-tiers/{tier_id}", response_model=PlanTierRead)
async def update_plan_tier(
    tier_id: str,
    request: UpdatePlanTierRequest,
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """Update a plan tier (admin only)"""
    logger.info(f"Admin user {admin_email} updating plan tier: {tier_id}")
    try:
        tier = admin_service.update_plan_tier(tier_id, request)
        if not tier:
            raise HTTPException(status_code=404, detail="Plan tier not found")
        return tier
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating plan tier {tier_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update plan tier")


@router.delete("/plan-tiers/{tier_id}", status_code=204)
async def delete_plan_tier(
    tier_id: str,
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """Delete a plan tier (admin only, refuses if referenced)"""
    logger.info(f"Admin user {admin_email} deleting plan tier: {tier_id}")
    try:
        deleted = admin_service.delete_plan_tier(tier_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Plan tier not found")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting plan tier {tier_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete plan tier")


@router.post("/plan-tiers/{tier_id}/apply", response_model=ApplyLimitsResult)
async def apply_plan_tier(
    tier_id: str,
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """Apply tier limits to all active users with this tier (admin only)"""
    logger.info(f"Admin user {admin_email} applying plan tier {tier_id} to active users")
    try:
        return admin_service.apply_tier_to_active_users(tier_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error applying plan tier {tier_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to apply plan tier")
