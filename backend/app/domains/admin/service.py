# -*- coding: utf-8 -*-
"""
Admin domain service
"""
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from app.infrastructure.clerk_client import clerk_client
from app.common.database import supabase
from app.domains.admin.schemas import (
    UserRead,
    UpdateUserPrivilegeRequest,
    UpdateUserSubscriptionRequest,
    SubscriptionStatusType,
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
