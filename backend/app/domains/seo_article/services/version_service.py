# -*- coding: utf-8 -*-
"""
Article Version Management Service

This service handles version control for article editing,
providing functionality similar to Google Docs version history.
"""

from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from app.domains.seo_article.services.flow_service import get_supabase_client

logger = logging.getLogger(__name__)


class ArticleVersionService:
    """Service for managing article edit versions"""

    def __init__(self):
        """Initialize the version service"""
        self.supabase = get_supabase_client()

    async def save_version(
        self,
        article_id: str,
        user_id: str,
        title: str,
        content: str,
        change_description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        max_versions: int = 50
    ) -> Dict[str, Any]:
        """
        Save a new version of an article.

        Args:
            article_id: Article UUID
            user_id: User ID
            title: Article title
            content: Article content (HTML)
            change_description: Optional description of changes
            metadata: Optional metadata (word count, etc.)
            max_versions: Maximum number of versions to keep

        Returns:
            Version information including version_id
        """
        try:
            # Prepare metadata
            if metadata is None:
                metadata = {}

            # Add automatic metadata
            metadata.update({
                "content_length": len(content),
                "title_length": len(title),
                "saved_at": datetime.utcnow().isoformat()
            })

            # Call database function to save version
            result = self.supabase.rpc(
                "save_article_version",
                {
                    "p_article_id": article_id,
                    "p_user_id": user_id,
                    "p_title": title,
                    "p_content": content,
                    "p_change_description": change_description,
                    "p_metadata": metadata,
                    "p_max_versions": max_versions
                }
            ).execute()

            if result.data:
                version_id = result.data
                logger.info(f"Saved version {version_id} for article {article_id}")
                return {
                    "version_id": version_id,
                    "article_id": article_id,
                    "saved_at": datetime.utcnow().isoformat()
                }
            else:
                raise Exception("Failed to save version - no data returned")

        except Exception as e:
            logger.error(f"Error saving article version: {str(e)}")
            raise

    async def get_version_history(
        self,
        article_id: str,
        user_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get version history for an article.

        Args:
            article_id: Article UUID
            user_id: User ID (for authorization)
            limit: Maximum number of versions to return

        Returns:
            List of version information
        """
        try:
            # First verify user has access to this article
            article_result = self.supabase.table("articles").select("*").eq("id", article_id).eq("user_id", user_id).execute()

            if not article_result.data:
                raise Exception(f"Article {article_id} not found or access denied")

            # Get version history
            result = self.supabase.rpc(
                "get_article_version_history",
                {
                    "p_article_id": article_id,
                    "p_limit": limit
                }
            ).execute()

            versions = []
            if result.data:
                for version in result.data:
                    versions.append({
                        "version_id": version["version_id"],
                        "version_number": version["version_number"],
                        "title": version["title"],
                        "change_description": version["change_description"],
                        "is_current": version["is_current"],
                        "created_at": version["created_at"],
                        "user_id": version["user_id"],
                        "metadata": version["metadata"]
                    })

            logger.info(f"Retrieved {len(versions)} versions for article {article_id}")
            return versions

        except Exception as e:
            logger.error(f"Error getting version history: {str(e)}")
            raise

    async def get_version(
        self,
        version_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific version.

        Args:
            version_id: Version UUID
            user_id: User ID (for authorization)

        Returns:
            Version data including content
        """
        try:
            result = self.supabase.rpc(
                "get_article_version",
                {
                    "p_version_id": version_id
                }
            ).execute()

            if not result.data or len(result.data) == 0:
                return None

            version = result.data[0]

            # Verify user has access to this article
            article_result = self.supabase.table("articles").select("user_id").eq("id", version["article_id"]).execute()

            if not article_result.data or article_result.data[0]["user_id"] != user_id:
                raise Exception("Access denied to this version")

            return {
                "version_id": version["version_id"],
                "article_id": version["article_id"],
                "version_number": version["version_number"],
                "title": version["title"],
                "content": version["content"],
                "change_description": version["change_description"],
                "is_current": version["is_current"],
                "created_at": version["created_at"],
                "user_id": version["user_id"],
                "metadata": version["metadata"]
            }

        except Exception as e:
            logger.error(f"Error getting version: {str(e)}")
            raise

    async def restore_version(
        self,
        version_id: str,
        user_id: str,
        create_new_version: bool = True
    ) -> Dict[str, Any]:
        """
        Restore an article to a specific version.

        Args:
            version_id: Version UUID to restore
            user_id: User ID (for authorization)
            create_new_version: Whether to create a new version for this restoration

        Returns:
            Restoration result
        """
        try:
            # Verify access first
            version = await self.get_version(version_id, user_id)
            if not version:
                raise Exception(f"Version {version_id} not found or access denied")

            # Call restore function
            result = self.supabase.rpc(
                "restore_article_version",
                {
                    "p_version_id": version_id,
                    "p_create_new_version": create_new_version
                }
            ).execute()

            if result.data:
                restoration_result = result.data
                logger.info(f"Restored article to version {version_id}")
                return restoration_result
            else:
                raise Exception("Failed to restore version - no data returned")

        except Exception as e:
            logger.error(f"Error restoring version: {str(e)}")
            raise

    async def navigate_version(
        self,
        article_id: str,
        user_id: str,
        direction: str  # 'next' or 'previous'
    ) -> Dict[str, Any]:
        """
        Navigate to next or previous version.

        Args:
            article_id: Article UUID
            user_id: User ID (for authorization)
            direction: 'next' or 'previous'

        Returns:
            Navigation result with new version info
        """
        try:
            # Verify access
            article_result = self.supabase.table("articles").select("*").eq("id", article_id).eq("user_id", user_id).execute()

            if not article_result.data:
                raise Exception(f"Article {article_id} not found or access denied")

            # Navigate
            result = self.supabase.rpc(
                "navigate_to_version",
                {
                    "p_article_id": article_id,
                    "p_direction": direction
                }
            ).execute()

            if result.data:
                new_version_id = result.data
                logger.info(f"Navigated {direction} to version {new_version_id}")

                # Get the new version details
                new_version = await self.get_version(new_version_id, user_id)
                return {
                    "version_id": new_version_id,
                    "direction": direction,
                    "version": new_version
                }
            else:
                raise Exception(f"No {direction} version available")

        except Exception as e:
            logger.error(f"Error navigating version: {str(e)}")
            raise

    async def delete_version(
        self,
        version_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a specific version.

        Args:
            version_id: Version UUID to delete
            user_id: User ID (for authorization)

        Returns:
            True if successful
        """
        try:
            # Verify access first
            version = await self.get_version(version_id, user_id)
            if not version:
                raise Exception(f"Version {version_id} not found or access denied")

            # Call delete function
            result = self.supabase.rpc(
                "delete_article_version",
                {
                    "p_version_id": version_id
                }
            ).execute()

            if result.data:
                logger.info(f"Deleted version {version_id}")
                return True
            else:
                raise Exception("Failed to delete version")

        except Exception as e:
            logger.error(f"Error deleting version: {str(e)}")
            raise

    async def get_current_version(
        self,
        article_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the current version of an article.

        Args:
            article_id: Article UUID
            user_id: User ID (for authorization)

        Returns:
            Current version data
        """
        try:
            # Verify access
            article_result = self.supabase.table("articles").select("*").eq("id", article_id).eq("user_id", user_id).execute()

            if not article_result.data:
                raise Exception(f"Article {article_id} not found or access denied")

            # Get current version ID
            result = self.supabase.rpc(
                "get_current_article_version",
                {
                    "p_article_id": article_id
                }
            ).execute()

            if result.data:
                current_version_id = result.data
                return await self.get_version(current_version_id, user_id)

            return None

        except Exception as e:
            logger.error(f"Error getting current version: {str(e)}")
            raise


# Singleton instance
_version_service_instance: Optional[ArticleVersionService] = None


def get_version_service() -> ArticleVersionService:
    """Get or create the version service singleton"""
    global _version_service_instance
    if _version_service_instance is None:
        _version_service_instance = ArticleVersionService()
    return _version_service_instance
