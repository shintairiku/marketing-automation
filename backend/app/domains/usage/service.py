# -*- coding: utf-8 -*-
"""
Usage Limit Service

Blog AIの月間記事生成上限を管理する。
- 使用量チェック（生成開始前のプリチェック）
- 成功時のカウント（原子的インクリメント）
- 使用量情報の取得
- 上限の再計算（プラン変更時）
"""
import logging
from datetime import datetime
from typing import Optional

from app.common.database import supabase
from app.domains.usage.schemas import UsageInfo, UsageLimitResult

logger = logging.getLogger(__name__)


class UsageLimitService:
    """利用上限サービス"""

    def __init__(self):
        self.db = supabase

    def check_can_generate(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
    ) -> UsageLimitResult:
        """
        生成可能かどうかをチェック（読み取り専用、インクリメントなし）。
        生成開始前のプリチェックに使用。
        特権ユーザーは常に許可。
        """
        # 特権ユーザーチェック
        if self._is_privileged(user_id):
            return UsageLimitResult(allowed=True, current=0, limit=999999, remaining=999999)

        tracking = self._get_current_tracking(user_id, organization_id)
        if not tracking:
            # トラッキングレコードがない場合、サブスク情報から作成を試みる
            tracking = self._create_tracking_from_subscription(user_id, organization_id)
            if not tracking:
                # サブスクがない場合は拒否
                return UsageLimitResult(allowed=False, current=0, limit=0, remaining=0)

        total_limit = tracking["articles_limit"] + tracking["addon_articles_limit"] + tracking.get("admin_granted_articles", 0)
        current = tracking["articles_generated"]
        remaining = max(0, total_limit - current)

        return UsageLimitResult(
            allowed=current < total_limit,
            current=current,
            limit=total_limit,
            remaining=remaining,
        )

    def record_success(
        self,
        user_id: str,
        process_id: str,
        organization_id: Optional[str] = None,
    ) -> bool:
        """
        生成成功時にカウントをインクリメント。
        原子的操作で競合条件を防止。

        Returns:
            True: インクリメント成功, False: 上限到達
        """
        tracking = self._get_current_tracking(user_id, organization_id)
        if not tracking:
            tracking = self._create_tracking_from_subscription(user_id, organization_id)
            if not tracking:
                logger.warning(f"No tracking record for user={user_id}, org={organization_id}")
                return False

        # 特権ユーザーは常にカウントするが拒否しない
        is_privileged = self._is_privileged(user_id)

        # 原子的インクリメント（DB関数）
        try:
            result = self.db.rpc(
                "increment_usage_if_allowed",
                {"p_tracking_id": tracking["id"]},
            ).execute()

            if result.data and len(result.data) > 0:
                row = result.data[0]
                was_allowed = row.get("was_allowed", False)

                if was_allowed or is_privileged:
                    # ログ記録
                    self._record_usage_log(tracking["id"], user_id, process_id)

                    if not was_allowed and is_privileged:
                        # 特権ユーザーが上限超過しても許可（手動インクリメント）
                        self.db.table("usage_tracking").update({
                            "articles_generated": row.get("new_count", 0) + 1,
                            "updated_at": datetime.utcnow().isoformat(),
                        }).eq("id", tracking["id"]).execute()

                    return True

                return False

            return False

        except Exception as e:
            logger.error(f"Failed to increment usage: {e}")
            # エラー時も特権ユーザーは許可
            if is_privileged:
                self._record_usage_log(tracking["id"], user_id, process_id)
                return True
            return False

    def get_current_usage(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
    ) -> UsageInfo:
        """現在の使用量情報を取得"""
        # 特権ユーザーの場合
        if self._is_privileged(user_id):
            return UsageInfo(
                articles_generated=0,
                articles_limit=999999,
                addon_articles_limit=0,
                total_limit=999999,
                remaining=999999,
                plan_tier="privileged",
            )

        tracking = self._get_current_tracking(user_id, organization_id)
        if not tracking:
            tracking = self._create_tracking_from_subscription(user_id, organization_id)

        if not tracking:
            return UsageInfo()

        admin_granted = tracking.get("admin_granted_articles", 0)
        total_limit = tracking["articles_limit"] + tracking["addon_articles_limit"] + admin_granted
        return UsageInfo(
            articles_generated=tracking["articles_generated"],
            articles_limit=tracking["articles_limit"],
            addon_articles_limit=tracking["addon_articles_limit"],
            admin_granted_articles=admin_granted,
            total_limit=total_limit,
            remaining=max(0, total_limit - tracking["articles_generated"]),
            billing_period_start=tracking.get("billing_period_start"),
            billing_period_end=tracking.get("billing_period_end"),
            plan_tier=tracking.get("plan_tier_id"),
        )

    def recalculate_limits(
        self,
        user_id: Optional[str],
        organization_id: Optional[str],
        plan_tier_id: str,
        quantity: int = 1,
        addon_quantity: int = 0,
    ) -> None:
        """
        プラン変更・アドオン変更時に現在期間の上限を再計算。
        articles_generated は変更しない。
        """
        tracking = self._get_current_tracking(user_id, organization_id)
        if not tracking:
            logger.info(f"No tracking to recalculate for user={user_id}, org={organization_id}")
            return

        # プランの上限を取得
        tier = self._get_plan_tier(plan_tier_id)
        if not tier:
            logger.warning(f"Plan tier not found: {plan_tier_id}")
            return

        new_limit = tier["monthly_article_limit"] * quantity
        new_addon_limit = tier["addon_unit_amount"] * addon_quantity

        self.db.table("usage_tracking").update({
            "articles_limit": new_limit,
            "addon_articles_limit": new_addon_limit,
            "plan_tier_id": plan_tier_id,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", tracking["id"]).execute()

        logger.info(
            f"Recalculated limits: user={user_id}, org={organization_id}, "
            f"limit={new_limit}, addon={new_addon_limit}"
        )

    def create_tracking_for_period(
        self,
        user_id: Optional[str],
        organization_id: Optional[str],
        billing_period_start: str,
        billing_period_end: str,
        plan_tier_id: str,
        quantity: int = 1,
        addon_quantity: int = 0,
    ) -> Optional[dict]:
        """新しい請求期間のトラッキングレコードを作成（冪等）"""
        tier = self._get_plan_tier(plan_tier_id)
        if not tier:
            logger.warning(f"Plan tier not found: {plan_tier_id}")
            return None

        articles_limit = tier["monthly_article_limit"] * quantity
        addon_articles_limit = tier["addon_unit_amount"] * addon_quantity

        data: dict = {
            "billing_period_start": billing_period_start,
            "billing_period_end": billing_period_end,
            "articles_generated": 0,
            "articles_limit": articles_limit,
            "addon_articles_limit": addon_articles_limit,
            "plan_tier_id": plan_tier_id,
        }

        if user_id:
            data["user_id"] = user_id
        elif organization_id:
            data["organization_id"] = organization_id
        else:
            return None

        try:
            result = self.db.table("usage_tracking").upsert(
                data,
                on_conflict="user_id,billing_period_start" if user_id else "organization_id,billing_period_start",
            ).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to create tracking: {e}")
            return None

    # ========================================
    # Private methods
    # ========================================

    def _is_privileged(self, user_id: str) -> bool:
        """特権ユーザーかどうかチェック"""
        try:
            result = self.db.table("user_subscriptions").select(
                "is_privileged"
            ).eq("user_id", user_id).maybe_single().execute()
            return result.data.get("is_privileged", False) if result.data else False
        except Exception:
            return False

    def _get_current_tracking(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
    ) -> Optional[dict]:
        """現在の請求期間のトラッキングレコードを取得"""
        now = datetime.utcnow().isoformat()

        try:
            if organization_id:
                result = self.db.table("usage_tracking").select("*").eq(
                    "organization_id", organization_id
                ).lte("billing_period_start", now).gte(
                    "billing_period_end", now
                ).maybe_single().execute()
            else:
                result = self.db.table("usage_tracking").select("*").eq(
                    "user_id", user_id
                ).lte("billing_period_start", now).gte(
                    "billing_period_end", now
                ).maybe_single().execute()

            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Failed to get tracking: {e}")
            return None

    def _create_tracking_from_subscription(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
    ) -> Optional[dict]:
        """サブスクリプション情報からトラッキングレコードを自動作成"""
        try:
            if organization_id:
                sub = self.db.table("organization_subscriptions").select(
                    "id, plan_tier_id, quantity, addon_quantity, current_period_start, current_period_end, status"
                ).eq("organization_id", organization_id).eq(
                    "status", "active"
                ).maybe_single().execute()

                if not sub.data:
                    return None

                return self.create_tracking_for_period(
                    user_id=None,
                    organization_id=organization_id,
                    billing_period_start=sub.data["current_period_start"],
                    billing_period_end=sub.data["current_period_end"],
                    plan_tier_id=sub.data.get("plan_tier_id") or "default",
                    quantity=sub.data.get("quantity", 1),
                    addon_quantity=sub.data.get("addon_quantity", 0),
                )
            else:
                sub = self.db.table("user_subscriptions").select(
                    "plan_tier_id, current_period_end, status, stripe_subscription_id, addon_quantity"
                ).eq("user_id", user_id).maybe_single().execute()

                if not sub.data:
                    return None

                plan_tier_id = sub.data.get("plan_tier_id") or "free"

                # フリープランユーザー（Stripeサブスクなし）
                if plan_tier_id == "free" or (sub.data.get("status") in ("none", None) and not sub.data.get("stripe_subscription_id")):
                    return self._create_tracking_for_free_plan(user_id, plan_tier_id)

                if sub.data.get("status") not in ("active", "past_due", "canceled"):
                    return None

                # current_period_end から期間を推定（1ヶ月前をstartとする）
                period_end = sub.data.get("current_period_end")
                if not period_end:
                    return None

                from datetime import timedelta
                end_dt = datetime.fromisoformat(period_end.replace("Z", "+00:00")) if isinstance(period_end, str) else period_end
                start_dt = end_dt - timedelta(days=30)

                return self.create_tracking_for_period(
                    user_id=user_id,
                    organization_id=None,
                    billing_period_start=start_dt.isoformat(),
                    billing_period_end=end_dt.isoformat(),
                    plan_tier_id=sub.data.get("plan_tier_id") or "default",
                    quantity=1,
                    addon_quantity=sub.data.get("addon_quantity", 0),
                )
        except Exception as e:
            logger.error(f"Failed to create tracking from subscription: {e}")
            return None

    def _create_tracking_for_free_plan(
        self,
        user_id: str,
        plan_tier_id: str = "free",
    ) -> Optional[dict]:
        """フリープランユーザー用のトラッキングレコードを自動作成（月初〜月末）"""
        try:
            from datetime import timedelta
            now = datetime.utcnow()
            # 月初
            start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # 翌月初
            if now.month == 12:
                end_dt = start_dt.replace(year=now.year + 1, month=1)
            else:
                end_dt = start_dt.replace(month=now.month + 1)

            return self.create_tracking_for_period(
                user_id=user_id,
                organization_id=None,
                billing_period_start=start_dt.isoformat(),
                billing_period_end=end_dt.isoformat(),
                plan_tier_id=plan_tier_id,
                quantity=1,
                addon_quantity=0,
            )
        except Exception as e:
            logger.error(f"Failed to create free plan tracking: {e}")
            return None

    def grant_articles(
        self,
        user_id: str,
        amount: int,
        organization_id: Optional[str] = None,
    ) -> Optional[dict]:
        """
        管理者がユーザーに追加記事を付与する。
        admin_granted_articles カラムをインクリメント。
        トラッキングレコードがない場合は自動作成する。
        """
        tracking = self._get_current_tracking(user_id, organization_id)
        if not tracking:
            tracking = self._create_tracking_from_subscription(user_id, organization_id)
            if not tracking:
                logger.warning(f"Cannot grant articles: no tracking for user={user_id}")
                return None

        current_granted = tracking.get("admin_granted_articles", 0)
        new_granted = current_granted + amount

        try:
            result = self.db.table("usage_tracking").update({
                "admin_granted_articles": new_granted,
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", tracking["id"]).execute()

            if result.data:
                updated = result.data[0]
                total_limit = updated["articles_limit"] + updated["addon_articles_limit"] + updated.get("admin_granted_articles", 0)
                return {
                    "user_id": user_id,
                    "admin_granted_articles": new_granted,
                    "total_limit": total_limit,
                    "articles_generated": updated["articles_generated"],
                    "remaining": max(0, total_limit - updated["articles_generated"]),
                }
            return None
        except Exception as e:
            logger.error(f"Failed to grant articles: {e}")
            return None

    def _get_plan_tier(self, plan_tier_id: str) -> Optional[dict]:
        """プランティア情報を取得"""
        try:
            result = self.db.table("plan_tiers").select("*").eq(
                "id", plan_tier_id
            ).maybe_single().execute()
            return result.data if result.data else None
        except Exception:
            return None

    def _record_usage_log(
        self,
        tracking_id: str,
        user_id: str,
        process_id: str,
    ) -> None:
        """使用量ログを記録"""
        try:
            self.db.table("usage_logs").insert({
                "usage_tracking_id": tracking_id,
                "user_id": user_id,
                "generation_process_id": process_id,
            }).execute()
        except Exception as e:
            logger.error(f"Failed to record usage log: {e}")


# Global instance
usage_service = UsageLimitService()
