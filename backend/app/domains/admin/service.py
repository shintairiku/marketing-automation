# -*- coding: utf-8 -*-
"""
Admin domain service
"""
from typing import List
import logging
from datetime import datetime
from app.infrastructure.clerk_client import clerk_client
from app.domains.admin.schemas import UserRead

logger = logging.getLogger(__name__)

class AdminService:
    """Admin service for user management"""
    
    def get_all_users(self) -> List[UserRead]:
        """
        Get all users from Clerk API
        """
        try:
            # Get users from Clerk API
            clerk_users = clerk_client.get_all_users()
            
            users = []
            for clerk_user in clerk_users:
                # Extract primary email
                email = None
                email_addresses = clerk_user.get("email_addresses", [])
                if email_addresses:
                    # Find primary email or use first email
                    primary_email = next(
                        (e for e in email_addresses if e.get("id") == clerk_user.get("primary_email_address_id")),
                        email_addresses[0] if email_addresses else None
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
                    # Clerk returns timestamp in milliseconds
                    created_at = datetime.fromtimestamp(created_at_timestamp / 1000)
                
                # Extract avatar URL
                avatar_url = clerk_user.get("image_url")
                
                user = UserRead(
                    id=clerk_user.get("id", ""),
                    full_name=full_name,
                    email=email,
                    avatar_url=avatar_url,
                    created_at=created_at
                )
                users.append(user)
            
            logger.info(f"Retrieved {len(users)} users from Clerk")
            return users
            
        except Exception as e:
            logger.error(f"Error retrieving users from Clerk: {e}")
            raise

# Service instance
admin_service = AdminService()

