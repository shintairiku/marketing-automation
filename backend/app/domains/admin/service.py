# -*- coding: utf-8 -*-
"""
Admin domain service
"""
from typing import List
import logging
from app.common.database import supabase
from app.domains.admin.schemas import UserRead

logger = logging.getLogger(__name__)

class AdminService:
    """Admin service for user management"""
    
    def get_all_users(self) -> List[UserRead]:
        """
        Get all users from database
        Note: This uses service role key to bypass RLS
        """
        try:
            # Query users table
            response = supabase.table("users").select("*").execute()
            
            users = []
            for row in response.data:
                # Get email from auth.users table
                # Note: We need to join with auth.users to get email
                # For now, we'll use the id to query auth.users
                user = UserRead(
                    id=str(row.get("id", "")),
                    full_name=row.get("full_name"),
                    avatar_url=row.get("avatar_url"),
                    created_at=row.get("created_at"),
                    email=None  # Email is in auth.users, not in public.users
                )
                users.append(user)
            
            logger.info(f"Retrieved {len(users)} users")
            return users
            
        except Exception as e:
            logger.error(f"Error retrieving users: {e}")
            raise

# Service instance
admin_service = AdminService()

