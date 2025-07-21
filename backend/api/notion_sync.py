# -*- coding: utf-8 -*-
"""
Notion同期のAPIエンドポイント
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from services.notion_sync_service import NotionSyncService

router = APIRouter(prefix="/notion", tags=["notion"])

class SyncRequest(BaseModel):
    session_id: Optional[str] = None
    hours: Optional[int] = 24

class SyncResponse(BaseModel):
    success: bool
    message: str
    synced_count: Optional[int] = None
    page_id: Optional[str] = None

@router.post("/sync", response_model=SyncResponse)
async def sync_to_notion(request: SyncRequest, background_tasks: BackgroundTasks):
    """
    SupabaseのLLMログをNotionに同期する
    
    - session_id が指定された場合: 特定のセッションを同期
    - session_id が未指定の場合: 最新のセッションを一括同期
    """
    try:
        sync_service = NotionSyncService()
        
        if request.session_id:
            # 特定セッションの同期
            success = sync_service.sync_session_to_notion(request.session_id)
            if success:
                return SyncResponse(
                    success=True,
                    message=f"セッション {request.session_id} をNotionに同期しました",
                    synced_count=1
                )
            else:
                raise HTTPException(status_code=500, detail="セッションの同期に失敗しました")
        else:
            # 最新セッションの一括同期
            synced_count = sync_service.sync_recent_sessions(hours=request.hours)
            return SyncResponse(
                success=True,
                message=f"最新 {request.hours} 時間以内の {synced_count} セッションをNotionに同期しました",
                synced_count=synced_count
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同期エラー: {str(e)}")

@router.get("/test")
async def test_notion_connection():
    """Notion API接続テスト"""
    try:
        sync_service = NotionSyncService()
        success = sync_service.notion_service.test_connection()
        
        if success:
            return {"success": True, "message": "Notion API接続成功"}
        else:
            raise HTTPException(status_code=500, detail="Notion API接続失敗")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"接続テストエラー: {str(e)}")

@router.post("/sync-background")
async def sync_to_notion_background(request: SyncRequest, background_tasks: BackgroundTasks):
    """
    バックグラウンドでNotionに同期する（非同期処理）
    """
    def sync_task():
        try:
            sync_service = NotionSyncService()
            if request.session_id:
                sync_service.sync_session_to_notion(request.session_id)
            else:
                sync_service.sync_recent_sessions(hours=request.hours)
        except Exception as e:
            print(f"Background sync error: {e}")
    
    background_tasks.add_task(sync_task)
    
    return SyncResponse(
        success=True,
        message="バックグラウンド同期を開始しました"
    )