# -*- coding: utf-8 -*-
"""
Admin domain service
"""
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta, timezone
from app.infrastructure.clerk_client import clerk_client
from app.common.database import supabase
from app.domains.admin.schemas import (
    UserRead,
    UpdateUserPrivilegeRequest,
    UpdateUserSubscriptionRequest,
    SubscriptionStatusType,
    OverviewStats,
    DailyGenerationCount,
    GenerationTrendResponse,
    SubscriptionDistribution,
    SubscriptionDistributionResponse,
    RecentActivity,
    RecentActivityResponse,
    UserUsageItem,
    UserDetailResponse,
    UserUsageDetail,
    UserGenerationHistory,
)

logger = logging.getLogger(__name__)

class AdminService:
    """Admin service for user management"""

    def _get_subscription_map(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all subscriptions from Supabase and return as a map keyed by user_id
        """
        try:
            response = supabase.from_("user_subscriptions").select("*").execute()
            subscriptions = response.data or []

            # Create a map keyed by user_id
            sub_map = {}
            for sub in subscriptions:
                user_id = sub.get("user_id")
                if user_id:
                    sub_map[user_id] = sub

            logger.info(f"Retrieved {len(sub_map)} subscription records from Supabase")
            return sub_map
        except Exception as e:
            logger.error(f"Error fetching subscriptions from Supabase: {e}")
            return {}

    def _get_subscription_for_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get subscription for a specific user
        """
        try:
            response = (
                supabase.from_("user_subscriptions")
                .select("*")
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            return response.data
        except Exception as e:
            logger.debug(f"No subscription found for user {user_id}: {e}")
            return None

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime from various formats"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                # ISO format with timezone
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                try:
                    # Try without timezone
                    return datetime.fromisoformat(value)
                except ValueError:
                    return None
        if isinstance(value, (int, float)):
            # Timestamp in milliseconds
            return datetime.fromtimestamp(value / 1000)
        return None

    def get_all_users(self) -> List[UserRead]:
        """
        Get all users from Clerk API merged with subscription data from Supabase
        """
        try:
            # Get users from Clerk API
            clerk_users = clerk_client.get_all_users()

            # Get subscriptions from Supabase
            subscription_map = self._get_subscription_map()

            users = []
            for clerk_user in clerk_users:
                user_id = clerk_user.get("id", "")

                # Extract primary email
                email = None
                email_addresses = clerk_user.get("email_addresses", [])
                if email_addresses:
                    primary_email = next(
                        (
                            e
                            for e in email_addresses
                            if e.get("id") == clerk_user.get("primary_email_address_id")
                        ),
                        email_addresses[0] if email_addresses else None,
                    )
                    if primary_email:
                        email = primary_email.get("email_address")

                # Extract full name (Japanese format: Last Name + First Name)
                full_name = None
                first_name = clerk_user.get("first_name")
                last_name = clerk_user.get("last_name")
                if first_name or last_name:
                    full_name = f"{last_name or ''} {first_name or ''}".strip()

                # Extract created_at timestamp
                created_at = None
                created_at_timestamp = clerk_user.get("created_at")
                if created_at_timestamp:
                    created_at = datetime.fromtimestamp(created_at_timestamp / 1000)

                # Extract avatar URL
                avatar_url = clerk_user.get("image_url")

                # Get subscription data
                sub_data = subscription_map.get(user_id, {})
                subscription_status: SubscriptionStatusType = sub_data.get("status", "none")
                is_privileged = sub_data.get("is_privileged", False)
                stripe_customer_id = sub_data.get("stripe_customer_id")
                stripe_subscription_id = sub_data.get("stripe_subscription_id")
                current_period_end = self._parse_datetime(
                    sub_data.get("current_period_end")
                )
                cancel_at_period_end = sub_data.get("cancel_at_period_end", False)

                # Check if email domain is @shintairiku.jp (auto-privileged)
                if email and email.lower().endswith("@shintairiku.jp"):
                    is_privileged = True

                user = UserRead(
                    id=user_id,
                    full_name=full_name,
                    email=email,
                    avatar_url=avatar_url,
                    created_at=created_at,
                    subscription_status=subscription_status,
                    is_privileged=is_privileged,
                    stripe_customer_id=stripe_customer_id,
                    stripe_subscription_id=stripe_subscription_id,
                    current_period_end=current_period_end,
                    cancel_at_period_end=cancel_at_period_end,
                )
                users.append(user)

            logger.info(f"Retrieved {len(users)} users with subscription data")
            return users

        except Exception as e:
            logger.error(f"Error retrieving users: {e}")
            raise

    def get_user_by_id(self, user_id: str) -> Optional[UserRead]:
        """
        Get a single user by ID with subscription data
        """
        try:
            clerk_user = clerk_client.get_user(user_id)
            if not clerk_user:
                return None

            # Extract email
            email = None
            email_addresses = clerk_user.get("email_addresses", [])
            if email_addresses:
                primary_email = next(
                    (
                        e
                        for e in email_addresses
                        if e.get("id") == clerk_user.get("primary_email_address_id")
                    ),
                    email_addresses[0] if email_addresses else None,
                )
                if primary_email:
                    email = primary_email.get("email_address")

            # Extract full name
            full_name = None
            first_name = clerk_user.get("first_name")
            last_name = clerk_user.get("last_name")
            if first_name or last_name:
                full_name = f"{last_name or ''} {first_name or ''}".strip()

            # Extract created_at
            created_at = None
            created_at_timestamp = clerk_user.get("created_at")
            if created_at_timestamp:
                created_at = datetime.fromtimestamp(created_at_timestamp / 1000)

            avatar_url = clerk_user.get("image_url")

            # Get subscription data
            sub_data = self._get_subscription_for_user(user_id) or {}
            subscription_status: SubscriptionStatusType = sub_data.get("status", "none")
            is_privileged = sub_data.get("is_privileged", False)
            stripe_customer_id = sub_data.get("stripe_customer_id")
            stripe_subscription_id = sub_data.get("stripe_subscription_id")
            current_period_end = self._parse_datetime(sub_data.get("current_period_end"))
            cancel_at_period_end = sub_data.get("cancel_at_period_end", False)

            # Check if email domain is @shintairiku.jp
            if email and email.lower().endswith("@shintairiku.jp"):
                is_privileged = True

            return UserRead(
                id=user_id,
                full_name=full_name,
                email=email,
                avatar_url=avatar_url,
                created_at=created_at,
                subscription_status=subscription_status,
                is_privileged=is_privileged,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
                current_period_end=current_period_end,
                cancel_at_period_end=cancel_at_period_end,
            )

        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    def update_user_privilege(
        self, user_id: str, request: UpdateUserPrivilegeRequest
    ) -> Optional[UserRead]:
        """
        Update user privilege status (is_privileged)
        """
        try:
            # First, get user from Clerk to get email
            clerk_user = clerk_client.get_user(user_id)
            if not clerk_user:
                logger.error(f"User {user_id} not found in Clerk")
                return None

            # Get email
            email = None
            email_addresses = clerk_user.get("email_addresses", [])
            if email_addresses:
                primary_email = next(
                    (
                        e
                        for e in email_addresses
                        if e.get("id") == clerk_user.get("primary_email_address_id")
                    ),
                    email_addresses[0] if email_addresses else None,
                )
                if primary_email:
                    email = primary_email.get("email_address")

            # Upsert subscription record with new privilege status
            supabase.from_("user_subscriptions").upsert(
                {
                    "user_id": user_id,
                    "email": email,
                    "is_privileged": request.is_privileged,
                },
                on_conflict="user_id",
            ).execute()

            logger.info(
                f"Updated privilege for user {user_id}: is_privileged={request.is_privileged}"
            )

            # Return updated user
            return self.get_user_by_id(user_id)

        except Exception as e:
            logger.error(f"Error updating privilege for user {user_id}: {e}")
            raise

    def get_overview_stats(self) -> OverviewStats:
        """Get dashboard overview statistics"""
        try:
            # ユーザー数
            clerk_users = clerk_client.get_all_users()
            total_users = len(clerk_users)

            # 今月新規登録数
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            new_users_this_month = sum(
                1 for u in clerk_users
                if u.get("created_at") and datetime.fromtimestamp(u["created_at"] / 1000, tz=timezone.utc) >= month_start
            )

            # サブスクリプション統計
            sub_map = self._get_subscription_map()
            active_subscribers = sum(1 for s in sub_map.values() if s.get("status") == "active")
            privileged_users = sum(1 for s in sub_map.values() if s.get("is_privileged"))
            none_users = total_users - active_subscribers - privileged_users

            # 組織サブスクも考慮
            try:
                org_response = supabase.from_("organization_subscriptions").select("quantity, status").eq("status", "active").execute()
                org_subs = org_response.data or []
                org_seat_count = sum(s.get("quantity", 0) for s in org_subs)
            except Exception:
                org_seat_count = 0

            # MRR概算 (個人 * 29800 + チームシート * 29800)
            estimated_mrr = (active_subscribers * 29800) + (org_seat_count * 29800)

            # 今月の記事生成数 (usage_tracking + blog_generation_state)
            total_articles_this_month = 0
            articles_prev_month = 0
            try:
                # usage_tracking から今月の合計
                usage_response = supabase.from_("usage_tracking").select("articles_generated, billing_period_start").gte("billing_period_end", now.isoformat()).lte("billing_period_start", now.isoformat()).execute()
                usage_data = usage_response.data or []
                total_articles_this_month = sum(u.get("articles_generated", 0) for u in usage_data)

                # 前月の記事数
                prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
                prev_usage = supabase.from_("usage_tracking").select("articles_generated").gte("billing_period_end", prev_month_start.isoformat()).lt("billing_period_start", month_start.isoformat()).execute()
                articles_prev_month = sum(u.get("articles_generated", 0) for u in (prev_usage.data or []))
            except Exception as e:
                logger.debug(f"Usage tracking query failed (table may not exist yet): {e}")
                # フォールバック: blog_generation_stateから集計
                try:
                    blog_response = supabase.from_("blog_generation_state").select("id, created_at").gte("created_at", month_start.isoformat()).eq("status", "completed").execute()
                    total_articles_this_month = len(blog_response.data or [])
                except Exception:
                    pass

            return OverviewStats(
                total_users=total_users,
                new_users_this_month=new_users_this_month,
                active_subscribers=active_subscribers,
                privileged_users=privileged_users,
                none_users=max(0, none_users),
                total_articles_this_month=total_articles_this_month,
                articles_prev_month=articles_prev_month,
                estimated_mrr=estimated_mrr,
            )
        except Exception as e:
            logger.error(f"Error getting overview stats: {e}")
            return OverviewStats()

    def get_generation_trend(self, days: int = 30) -> GenerationTrendResponse:
        """Get daily article generation trend"""
        try:
            now = datetime.now(timezone.utc)
            start_date = now - timedelta(days=days)

            # blog_generation_state の completed を日別に集計
            response = supabase.from_("blog_generation_state").select("created_at").eq("status", "completed").gte("created_at", start_date.isoformat()).execute()
            records = response.data or []

            # 日別にカウント
            daily_counts: Dict[str, int] = {}
            for i in range(days):
                d = (start_date + timedelta(days=i + 1)).strftime("%Y-%m-%d")
                daily_counts[d] = 0

            for record in records:
                created = record.get("created_at", "")
                if created:
                    date_str = created[:10]  # YYYY-MM-DD
                    if date_str in daily_counts:
                        daily_counts[date_str] += 1

            daily = [DailyGenerationCount(date=d, count=c) for d, c in sorted(daily_counts.items())]
            total = sum(c.count for c in daily)

            return GenerationTrendResponse(daily=daily, total=total)
        except Exception as e:
            logger.error(f"Error getting generation trend: {e}")
            return GenerationTrendResponse(daily=[], total=0)

    def get_subscription_distribution(self) -> SubscriptionDistributionResponse:
        """Get subscription status distribution"""
        try:
            sub_map = self._get_subscription_map()

            status_labels = {
                "active": "アクティブ",
                "past_due": "支払い遅延",
                "canceled": "キャンセル済み",
                "expired": "期限切れ",
                "none": "未登録",
            }

            counts: Dict[str, int] = {s: 0 for s in status_labels}
            for sub in sub_map.values():
                status = sub.get("status", "none")
                if status in counts:
                    counts[status] += 1
                else:
                    counts["none"] += 1

            # 特権ユーザーも集計
            privileged_count = sum(1 for s in sub_map.values() if s.get("is_privileged"))

            distribution = []
            for status, count in counts.items():
                if count > 0:
                    distribution.append(SubscriptionDistribution(
                        status=status, count=count, label=status_labels.get(status, status)
                    ))
            if privileged_count > 0:
                distribution.append(SubscriptionDistribution(
                    status="privileged", count=privileged_count, label="特権ユーザー"
                ))

            return SubscriptionDistributionResponse(distribution=distribution)
        except Exception as e:
            logger.error(f"Error getting subscription distribution: {e}")
            return SubscriptionDistributionResponse(distribution=[])

    def get_recent_activity(self, limit: int = 20) -> RecentActivityResponse:
        """Get recent activity (generation completions)"""
        try:
            activities: list[RecentActivity] = []

            # 直近のブログ生成
            blog_response = supabase.from_("blog_generation_state").select("user_id, status, created_at, updated_at").order("updated_at", desc=True).limit(limit).execute()

            sub_map = self._get_subscription_map()

            for record in (blog_response.data or []):
                user_id = record.get("user_id", "")
                email = sub_map.get(user_id, {}).get("email")
                status = record.get("status", "")
                timestamp_str = record.get("updated_at") or record.get("created_at")

                status_text = {
                    "completed": "ブログ記事を生成完了",
                    "in_progress": "ブログ記事を生成中",
                    "failed": "ブログ記事の生成に失敗",
                    "cancelled": "ブログ記事の生成をキャンセル",
                }.get(status, f"ブログ生成ステータス: {status}")

                activities.append(RecentActivity(
                    type="generation",
                    user_id=user_id,
                    user_email=email,
                    description=status_text,
                    timestamp=self._parse_datetime(timestamp_str),
                ))

            return RecentActivityResponse(activities=activities[:limit])
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return RecentActivityResponse(activities=[])

    def get_users_usage(self) -> list[UserUsageItem]:
        """Get per-user usage list"""
        try:
            now = datetime.now(timezone.utc)
            response = supabase.from_("usage_tracking").select("user_id, articles_generated, articles_limit, addon_articles_limit").gte("billing_period_end", now.isoformat()).lte("billing_period_start", now.isoformat()).execute()

            sub_map = self._get_subscription_map()
            items = []
            for record in (response.data or []):
                user_id = record.get("user_id", "")
                articles_generated = record.get("articles_generated", 0)
                total_limit = record.get("articles_limit", 0) + record.get("addon_articles_limit", 0)
                usage_pct = (articles_generated / total_limit * 100) if total_limit > 0 else 0

                items.append(UserUsageItem(
                    user_id=user_id,
                    email=sub_map.get(user_id, {}).get("email"),
                    articles_generated=articles_generated,
                    total_limit=total_limit,
                    usage_percentage=round(usage_pct, 1),
                ))

            # 使用率の降順でソート
            items.sort(key=lambda x: x.usage_percentage, reverse=True)
            return items
        except Exception as e:
            logger.error(f"Error getting users usage: {e}")
            return []

    def get_user_detail(self, user_id: str) -> Optional[UserDetailResponse]:
        """Get detailed user info including usage, generation history, and org info"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        now = datetime.now(timezone.utc)
        sub_data = self._get_subscription_for_user(user_id) or {}
        addon_quantity = sub_data.get("addon_quantity", 0)
        upgraded_to_org_id = sub_data.get("upgraded_to_org_id")

        # Determine organization
        org_id = None
        org_name = None
        if upgraded_to_org_id:
            org_id = upgraded_to_org_id
        else:
            try:
                mem_resp = supabase.from_("organization_members").select("organization_id").eq("user_id", user_id).limit(1).execute()
                if mem_resp.data and len(mem_resp.data) > 0:
                    org_id = mem_resp.data[0].get("organization_id")
            except Exception:
                pass

        if org_id:
            try:
                org_resp = supabase.from_("organizations").select("name").eq("id", org_id).maybe_single().execute()
                if org_resp.data:
                    org_name = org_resp.data.get("name")
            except Exception:
                pass

        # Usage tracking
        usage = None
        try:
            # Personal usage
            usage_resp = supabase.from_("usage_tracking").select("*").eq("user_id", user_id).gte("billing_period_end", now.isoformat()).lte("billing_period_start", now.isoformat()).maybe_single().execute()
            usage_data = usage_resp.data

            # Fallback: org usage
            if not usage_data and org_id:
                usage_resp = supabase.from_("usage_tracking").select("*").eq("organization_id", org_id).gte("billing_period_end", now.isoformat()).lte("billing_period_start", now.isoformat()).maybe_single().execute()
                usage_data = usage_resp.data

            if usage_data:
                articles_limit = usage_data.get("articles_limit", 0)
                addon_limit = usage_data.get("addon_articles_limit", 0)
                total_limit = articles_limit + addon_limit
                generated = usage_data.get("articles_generated", 0)
                usage = UserUsageDetail(
                    articles_generated=generated,
                    articles_limit=articles_limit,
                    addon_articles_limit=addon_limit,
                    total_limit=total_limit,
                    remaining=max(0, total_limit - generated),
                    billing_period_start=usage_data.get("billing_period_start"),
                    billing_period_end=usage_data.get("billing_period_end"),
                    plan_tier_id=usage_data.get("plan_tier_id"),
                )
        except Exception as e:
            logger.debug(f"Usage tracking query failed for user {user_id}: {e}")

        # Generation history
        history = []
        try:
            hist_resp = supabase.from_("blog_generation_state").select("id, status, created_at, updated_at").eq("user_id", user_id).order("created_at", desc=True).limit(20).execute()
            for record in (hist_resp.data or []):
                history.append(UserGenerationHistory(
                    process_id=record.get("id", ""),
                    status=record.get("status", ""),
                    created_at=self._parse_datetime(record.get("created_at")),
                    updated_at=self._parse_datetime(record.get("updated_at")),
                ))
        except Exception as e:
            logger.debug(f"Generation history query failed for user {user_id}: {e}")

        # Plan tier name
        plan_tier_name = None
        plan_tier_id = sub_data.get("plan_tier_id") or (usage.plan_tier_id if usage else None)
        if plan_tier_id:
            try:
                tier_resp = supabase.from_("plan_tiers").select("name").eq("id", plan_tier_id).maybe_single().execute()
                if tier_resp.data:
                    plan_tier_name = tier_resp.data.get("name")
            except Exception:
                pass

        return UserDetailResponse(
            user=user,
            usage=usage,
            generation_history=history,
            organization_id=str(org_id) if org_id else None,
            organization_name=org_name,
            addon_quantity=addon_quantity,
            plan_tier_name=plan_tier_name,
        )

    def update_user_subscription(
        self, user_id: str, request: UpdateUserSubscriptionRequest
    ) -> Optional[UserRead]:
        """
        Update user subscription status
        """
        try:
            # Format current_period_end for database
            period_end = None
            if request.current_period_end:
                period_end = request.current_period_end.isoformat()

            # Upsert subscription record
            supabase.from_("user_subscriptions").upsert(
                {
                    "user_id": user_id,
                    "status": request.status,
                    "current_period_end": period_end,
                    "cancel_at_period_end": request.cancel_at_period_end,
                },
                on_conflict="user_id",
            ).execute()

            logger.info(
                f"Updated subscription for user {user_id}: status={request.status}"
            )

            # Return updated user
            return self.get_user_by_id(user_id)

        except Exception as e:
            logger.error(f"Error updating subscription for user {user_id}: {e}")
            raise


# Service instance
admin_service = AdminService()
