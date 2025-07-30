# -*- coding: utf-8 -*-
"""
記事管理サービス - 記事のCRUD操作と管理機能を提供

このサービスは記事の作成、読み取り、更新、削除操作を担当します。
生成機能はgeneration_service.pyで実装されています。
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.common.database import supabase

logger = logging.getLogger(__name__)

class ArticleManagementService:
    """記事管理サービス"""
    
    def __init__(self):
        self.supabase = supabase
    
    async def get_user_articles(
        self,
        user_id: str,
        status_filter: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """ユーザーの記事一覧を取得"""
        try:
            query = self.supabase.table("articles").select("*").eq("user_id", user_id)
            
            if status_filter:
                query = query.eq("status", status_filter)
            
            result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting user articles: {e}")
            raise
    
    async def get_article(self, article_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """記事の詳細情報を取得"""
        try:
            result = self.supabase.table("articles").select("*").eq("id", article_id).eq("user_id", user_id).execute()
            
            if not result.data:
                return None
            
            return result.data[0]
        except Exception as e:
            logger.error(f"Error getting article {article_id}: {e}")
            raise
    
    async def update_article(
        self,
        article_id: str,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """記事を更新"""
        try:
            # 更新データに更新時刻を追加
            update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            result = self.supabase.table("articles").update(update_data).eq("id", article_id).eq("user_id", user_id).execute()
            
            if not result.data:
                raise ValueError("Article not found or update failed")
            
            return result.data[0]
        except Exception as e:
            logger.error(f"Error updating article {article_id}: {e}")
            raise
    
    async def delete_article(self, article_id: str, user_id: str) -> bool:
        """記事を削除"""
        try:
            result = self.supabase.table("articles").delete().eq("id", article_id).eq("user_id", user_id).execute()
            
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error deleting article {article_id}: {e}")
            raise
    
    async def get_all_user_processes(
        self,
        user_id: str,
        status_filter: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """ユーザーの全プロセス（記事＋生成プロセス）を取得"""
        try:
            # 記事を取得
            articles_query = self.supabase.table("articles").select("*").eq("user_id", user_id)
            if status_filter:
                articles_query = articles_query.eq("status", status_filter)
            
            articles_result = articles_query.order("created_at", desc=True).execute()
            
            # 生成プロセスを取得
            processes_query = self.supabase.table("article_generation_processes").select("*").eq("user_id", user_id)
            if status_filter:
                processes_query = processes_query.eq("status", status_filter)
            
            processes_result = processes_query.order("created_at", desc=True).execute()
            
            # 統合して返す
            all_items = []
            
            # 記事を追加
            for article in articles_result.data or []:
                all_items.append({
                    **article,
                    "type": "article"
                })
            
            # 生成プロセスを追加
            for process in processes_result.data or []:
                all_items.append({
                    **process,
                    "type": "generation_process"
                })
            
            # 作成日時でソート
            all_items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            # ページネーション
            return all_items[offset:offset + limit]
            
        except Exception as e:
            logger.error(f"Error getting all user processes: {e}")
            raise
    
    async def get_recoverable_processes(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """復旧可能な生成プロセスを取得"""
        try:
            # 一時停止中または特定のエラー状態のプロセスを取得
            result = self.supabase.table("article_generation_processes").select("*").eq("user_id", user_id).in_("status", ["paused", "error", "connection_lost"]).order("created_at", desc=True).limit(limit).execute()
            
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting recoverable processes: {e}")
            raise

# サービスインスタンス
article_management_service = ArticleManagementService()