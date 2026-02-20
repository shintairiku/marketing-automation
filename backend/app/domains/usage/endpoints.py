# -*- coding: utf-8 -*-
"""
Usage domain API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
import logging

from app.common.auth import get_current_user_id_from_token
from app.common.admin_auth import get_admin_user_email_from_token
from app.domains.usage.service import usage_service
from app.domains.usage.schemas import UsageInfo, AdminUsageStats, AdminUserUsage
from app.common.database import supabase

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/current", response_model=UsageInfo)
async def get_current_usage(
    user_id: str = Depends(get_current_user_id_from_token),
):
    """現在の使用量を取得"""
    # ユーザーの組織を確認（チームプランの場合）
    org_id = _get_user_active_org(user_id)
    return usage_service.get_current_usage(user_id=user_id, organization_id=org_id)


# =====================================================
# 管理者用エンドポイント
# =====================================================


@router.get("/admin/stats", response_model=AdminUsageStats)
async def get_admin_usage_stats(
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """全体の使用量統計（管理者のみ）"""
    logger.info(f"Admin {admin_email} requested usage stats")

    from datetime import datetime, timedelta

    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    # 今月の使用量合計
    try:
        this_month = supabase.table("usage_tracking").select(
            "articles_generated"
        ).gte("billing_period_end", month_start.isoformat()).execute()

        total_this_month = sum(r["articles_generated"] for r in (this_month.data or []))

        # 先月の使用量合計
        last_month = supabase.table("usage_tracking").select(
            "articles_generated"
        ).gte(
            "billing_period_start", last_month_start.isoformat()
        ).lt(
            "billing_period_start", month_start.isoformat()
        ).execute()

        total_last_month = sum(r["articles_generated"] for r in (last_month.data or []))

        # 成長率
        growth_rate = 0.0
        if total_last_month > 0:
            growth_rate = ((total_this_month - total_last_month) / total_last_month) * 100

        # 上限に近いユーザー数（80%以上使用）
        near_limit = 0
        if this_month.data:
            for r in this_month.data:
                total_limit = r.get("articles_limit", 0) + r.get("addon_articles_limit", 0) + r.get("admin_granted_articles", 0)
                if total_limit > 0 and r["articles_generated"] / total_limit >= 0.8:
                    near_limit += 1

        return AdminUsageStats(
            total_articles_this_month=total_this_month,
            total_articles_last_month=total_last_month,
            articles_growth_rate=round(growth_rate, 1),
            users_near_limit=near_limit,
        )
    except Exception as e:
        logger.error(f"Failed to get usage stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get usage stats")


@router.get("/admin/users", response_model=list[AdminUserUsage])
async def get_admin_user_usage(
    admin_email: str = Depends(get_admin_user_email_from_token),
):
    """ユーザー別使用量一覧（管理者のみ）"""
    logger.info(f"Admin {admin_email} requested user usage list")

    from datetime import datetime

    now = datetime.utcnow().isoformat()

    try:
        # 現在の期間のトラッキングレコードを取得
        result = supabase.table("usage_tracking").select("*").lte(
            "billing_period_start", now
        ).gte("billing_period_end", now).execute()

        if not result.data:
            return []

        # ユーザー情報を取得
        user_ids = [r["user_id"] for r in result.data if r.get("user_id")]
        user_map = {}
        if user_ids:
            users = supabase.table("user_subscriptions").select(
                "user_id, email"
            ).in_("user_id", user_ids).execute()
            user_map = {u["user_id"]: u for u in (users.data or [])}

        items = []
        for r in result.data:
            uid = r.get("user_id") or ""
            user_info = user_map.get(uid, {})
            admin_granted = r.get("admin_granted_articles", 0)
            total_limit = r["articles_limit"] + r["addon_articles_limit"] + admin_granted
            pct = (r["articles_generated"] / total_limit * 100) if total_limit > 0 else 0

            items.append(AdminUserUsage(
                user_id=uid,
                email=user_info.get("email"),
                articles_generated=r["articles_generated"],
                articles_limit=r["articles_limit"],
                addon_articles_limit=r["addon_articles_limit"],
                admin_granted_articles=admin_granted,
                total_limit=total_limit,
                usage_percentage=round(pct, 1),
                plan_tier=r.get("plan_tier_id"),
                billing_period_end=r.get("billing_period_end"),
            ))

        # 使用率順でソート（降順）
        items.sort(key=lambda x: x.usage_percentage, reverse=True)
        return items

    except Exception as e:
        logger.error(f"Failed to get user usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user usage")


def _get_user_active_org(user_id: str) -> str | None:
    """ユーザーがチームプランで所属している組織のIDを取得"""
    try:
        # 1. upgraded_to_org_id があれば、そのorgの使用量を参照
        sub = supabase.table("user_subscriptions").select(
            "upgraded_to_org_id"
        ).eq("user_id", user_id).maybe_single().execute()

        if sub.data and sub.data.get("upgraded_to_org_id"):
            return sub.data["upgraded_to_org_id"]

        # 2. organization_members テーブルでアクティブな組織サブスクがある組織を探す
        memberships = supabase.table("organization_members").select(
            "organization_id"
        ).eq("user_id", user_id).execute()

        if memberships.data:
            org_ids = [m["organization_id"] for m in memberships.data]
            # アクティブなサブスクがある組織を探す
            org_subs = supabase.table("organization_subscriptions").select(
                "organization_id"
            ).in_("organization_id", org_ids).eq("status", "active").limit(1).execute()

            if org_subs.data:
                return org_subs.data[0]["organization_id"]

        return None
    except Exception:
        return None
