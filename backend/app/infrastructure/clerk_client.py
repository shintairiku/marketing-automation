# -*- coding: utf-8 -*-
"""
Clerk API client for backend operations
"""
import httpx
import logging
from typing import List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class ClerkClient:
    """Clerk Backend API client"""
    
    def __init__(self):
        self.secret_key = settings.clerk_secret_key
        self.base_url = "https://api.clerk.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    def get_all_users(self, limit: int = 500) -> List[Dict[str, Any]]:
        """
        Get all users from Clerk
        
        Args:
            limit: Maximum number of users to retrieve per page
            
        Returns:
            List of user dictionaries
        """
        if not self.secret_key:
            logger.error("Clerk secret key is not configured")
            raise ValueError("Clerk secret key is required")
        
        all_users = []
        offset = 0
        
        try:
            with httpx.Client(timeout=30.0) as client:
                while True:
                    params = {
                        "limit": limit,
                        "offset": offset
                    }
                    
                    response = client.get(
                        f"{self.base_url}/users",
                        headers=self.headers,
                        params=params
                    )
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    if isinstance(data, list):
                        users = data
                    else:
                        users = data.get("data", [])
                    
                    if not users:
                        break
                    
                    all_users.extend(users)
                    
                    # Check if there are more pages
                    if len(users) < limit:
                        break
                    
                    offset += limit
                    
                    logger.info(f"Retrieved {len(all_users)} users so far...")
            
            logger.info(f"Successfully retrieved {len(all_users)} users from Clerk")
            return all_users
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Clerk API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error fetching users from Clerk: {e}")
            raise
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single user by ID from Clerk
        
        Args:
            user_id: Clerk user ID
            
        Returns:
            User dictionary or None if not found
        """
        if not self.secret_key:
            logger.error("Clerk secret key is not configured")
            raise ValueError("Clerk secret key is required")
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{self.base_url}/users/{user_id}",
                    headers=self.headers
                )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Clerk API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error fetching user from Clerk: {e}")
            raise

# Global client instance
clerk_client = ClerkClient()

