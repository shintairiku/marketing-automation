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
    BlogAiUsageStats,
    PlanTierRead,
    CreatePlanTierRequest,
    UpdatePlanTierRequest,
    ApplyLimitsResult,
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

    def _get_blog_ai_usage(self, user_id: str) -> Optional[BlogAiUsageStats]:
        """Blog AIのLLM使用量を集計"""
        try:
            sessions_resp = supabase.from_("agent_log_sessions").select(
                "id, created_at, session_metadata"
            ).eq("user_id", user_id).eq(
                "session_metadata->>workflow_type", "blog_generation"
            ).execute()
            sessions = sessions_resp.data or []
            if not sessions:
                return None

            session_ids = [s["id"] for s in sessions]
            last_run_at = None
            for s in sessions:
                created_at = self._parse_datetime(s.get("created_at"))
                if created_at and (last_run_at is None or created_at > last_run_at):
                    last_run_at = created_at

            exec_resp = supabase.from_("agent_execution_logs").select(
                "id, input_tokens, output_tokens, cache_tokens, reasoning_tokens"
            ).in_("session_id", session_ids).execute()
            executions = exec_resp.data or []
            execution_ids = [e["id"] for e in executions]

            llm_calls = []
            if execution_ids:
                llm_resp = supabase.from_("llm_call_logs").select(
                    "prompt_tokens, completion_tokens, cached_tokens, reasoning_tokens, total_tokens, model_name, estimated_cost_usd, called_at"
                ).in_("execution_id", execution_ids).execute()
                llm_calls = llm_resp.data or []

            tool_calls = []
            if execution_ids:
                tool_resp = supabase.from_("tool_call_logs").select(
                    "tool_name, tool_function, status"
                ).in_("execution_id", execution_ids).execute()
                tool_calls = tool_resp.data or []

            input_tokens = 0
            output_tokens = 0
            cached_tokens = 0
            reasoning_tokens = 0
            total_tokens = 0
            estimated_cost = 0.0
            models: set[str] = set()

            if llm_calls:
                for call in llm_calls:
                    input_tokens += int(call.get("prompt_tokens", 0) or 0)
                    output_tokens += int(call.get("completion_tokens", 0) or 0)
                    cached_tokens += int(call.get("cached_tokens", 0) or 0)
                    reasoning_tokens += int(call.get("reasoning_tokens", 0) or 0)
                    total_tokens += int(call.get("total_tokens", 0) or 0)
                    estimated_cost += float(call.get("estimated_cost_usd", 0) or 0)
                    model_name = call.get("model_name")
                    if model_name:
                        models.add(model_name)
            else:
                for execution in executions:
                    input_tokens += int(execution.get("input_tokens", 0) or 0)
                    output_tokens += int(execution.get("output_tokens", 0) or 0)
                    cached_tokens += int(execution.get("cache_tokens", 0) or 0)
                    reasoning_tokens += int(execution.get("reasoning_tokens", 0) or 0)

            tool_breakdown: Dict[str, int] = {}
            for tool in tool_calls:
                name = tool.get("tool_name") or tool.get("tool_function") or "unknown"
                tool_breakdown[name] = tool_breakdown.get(name, 0) + 1

            tools_sorted = [
                {"tool_name": name, "count": count}
                for name, count in sorted(tool_breakdown.items(), key=lambda item: item[1], reverse=True)
            ]

            return BlogAiUsageStats(
                total_tokens=total_tokens or (input_tokens + output_tokens),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_tokens=cached_tokens,
                reasoning_tokens=reasoning_tokens,
                estimated_cost_usd=round(estimated_cost, 6),
                tool_calls=len(tool_calls),
                tools=tools_sorted,
                models=sorted(models),
                last_run_at=last_run_at,
            )
        except Exception as e:
            logger.debug(f"Blog AI usage aggregation failed for user {user_id}: {e}")
            return None

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
            blog_ai_usage=self._get_blog_ai_usage(user_id),
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

    # ============================================
    # Plan Tier CRUD
    # ============================================

    def get_all_plan_tiers(self) -> list[PlanTierRead]:
        """Get all plan tiers ordered by display_order"""
        try:
            response = (
                supabase.from_("plan_tiers")
                .select("*")
                .order("display_order")
                .execute()
            )
            return [PlanTierRead(**tier) for tier in (response.data or [])]
        except Exception as e:
            logger.error(f"Error getting plan tiers: {e}")
            raise

    def create_plan_tier(self, request: CreatePlanTierRequest) -> PlanTierRead:
        """Create a new plan tier"""
        try:
            # Check for duplicate ID
            existing = (
                supabase.from_("plan_tiers")
                .select("id")
                .eq("id", request.id)
                .maybe_single()
                .execute()
            )
            if existing.data:
                raise ValueError(f"Plan tier with id '{request.id}' already exists")

            now = datetime.now(timezone.utc).isoformat()
            data = {
                "id": request.id,
                "name": request.name,
                "stripe_price_id": request.stripe_price_id,
                "monthly_article_limit": request.monthly_article_limit,
                "addon_unit_amount": request.addon_unit_amount,
                "price_amount": request.price_amount,
                "display_order": request.display_order,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
            response = supabase.from_("plan_tiers").insert(data).execute()
            if response.data:
                return PlanTierRead(**response.data[0])
            raise Exception("Failed to insert plan tier")
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating plan tier: {e}")
            raise

    def update_plan_tier(self, tier_id: str, request: UpdatePlanTierRequest) -> Optional[PlanTierRead]:
        """Update an existing plan tier (only changed fields)"""
        try:
            update_data: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
            if request.name is not None:
                update_data["name"] = request.name
            if request.stripe_price_id is not None:
                update_data["stripe_price_id"] = request.stripe_price_id
            if request.monthly_article_limit is not None:
                update_data["monthly_article_limit"] = request.monthly_article_limit
            if request.addon_unit_amount is not None:
                update_data["addon_unit_amount"] = request.addon_unit_amount
            if request.price_amount is not None:
                update_data["price_amount"] = request.price_amount
            if request.display_order is not None:
                update_data["display_order"] = request.display_order
            if request.is_active is not None:
                update_data["is_active"] = request.is_active

            response = (
                supabase.from_("plan_tiers")
                .update(update_data)
                .eq("id", tier_id)
                .execute()
            )
            if response.data:
                return PlanTierRead(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error updating plan tier {tier_id}: {e}")
            raise

    def delete_plan_tier(self, tier_id: str) -> bool:
        """Delete a plan tier (refuses if referenced by usage_tracking or user_subscriptions)"""
        try:
            # Check usage_tracking references
            usage_ref = (
                supabase.from_("usage_tracking")
                .select("id", count="exact")
                .eq("plan_tier_id", tier_id)
                .limit(1)
                .execute()
            )
            if usage_ref.count and usage_ref.count > 0:
                raise ValueError(
                    f"Cannot delete tier '{tier_id}': referenced by {usage_ref.count} usage_tracking records"
                )

            # Check user_subscriptions references
            sub_ref = (
                supabase.from_("user_subscriptions")
                .select("user_id", count="exact")
                .eq("plan_tier_id", tier_id)
                .limit(1)
                .execute()
            )
            if sub_ref.count and sub_ref.count > 0:
                raise ValueError(
                    f"Cannot delete tier '{tier_id}': referenced by {sub_ref.count} user_subscriptions"
                )

            response = (
                supabase.from_("plan_tiers")
                .delete()
                .eq("id", tier_id)
                .execute()
            )
            return bool(response.data)
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error deleting plan tier {tier_id}: {e}")
            raise

    def apply_tier_to_active_users(self, tier_id: str) -> ApplyLimitsResult:
        """
        Apply tier limits to all active usage_tracking records for the given tier.
        Recalculates articles_limit and addon_articles_limit based on tier values
        and each user's subscription quantity/addon_quantity.
        """
        try:
            # Get tier info
            tier_resp = (
                supabase.from_("plan_tiers")
                .select("*")
                .eq("id", tier_id)
                .single()
                .execute()
            )
            tier = tier_resp.data
            if not tier:
                raise ValueError(f"Plan tier '{tier_id}' not found")

            monthly_limit = tier.get("monthly_article_limit", 0)
            addon_unit = tier.get("addon_unit_amount", 20)

            now = datetime.now(timezone.utc).isoformat()

            # Get all active usage_tracking records for this tier
            usage_resp = (
                supabase.from_("usage_tracking")
                .select("id, user_id, organization_id")
                .eq("plan_tier_id", tier_id)
                .gte("billing_period_end", now)
                .execute()
            )
            records = usage_resp.data or []

            updated_count = 0
            for record in records:
                user_id = record.get("user_id")
                org_id = record.get("organization_id")

                # Get subscription quantity and addon_quantity
                quantity = 1
                addon_quantity = 0

                if org_id:
                    try:
                        org_sub = (
                            supabase.from_("organization_subscriptions")
                            .select("quantity, addon_quantity")
                            .eq("organization_id", org_id)
                            .eq("status", "active")
                            .maybe_single()
                            .execute()
                        )
                        if org_sub.data:
                            quantity = org_sub.data.get("quantity", 1)
                            addon_quantity = org_sub.data.get("addon_quantity", 0)
                    except Exception:
                        pass
                elif user_id:
                    try:
                        user_sub = (
                            supabase.from_("user_subscriptions")
                            .select("quantity, addon_quantity")
                            .eq("user_id", user_id)
                            .maybe_single()
                            .execute()
                        )
                        if user_sub.data:
                            quantity = user_sub.data.get("quantity", 1)
                            addon_quantity = user_sub.data.get("addon_quantity", 0)
                    except Exception:
                        pass

                new_articles_limit = monthly_limit * quantity
                new_addon_limit = addon_unit * addon_quantity

                try:
                    supabase.from_("usage_tracking").update({
                        "articles_limit": new_articles_limit,
                        "addon_articles_limit": new_addon_limit,
                    }).eq("id", record["id"]).execute()
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Failed to update usage_tracking {record['id']}: {e}")

            return ApplyLimitsResult(
                updated_count=updated_count,
                message=f"{updated_count}件の使用量レコードを更新しました",
            )
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error applying tier {tier_id} to active users: {e}")
            raise


# Service instance
admin_service = AdminService()
