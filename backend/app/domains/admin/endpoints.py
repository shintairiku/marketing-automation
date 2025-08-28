# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.common.auth import get_current_admin_user
from app.domains.admin.auth.clerk_validator import AdminUser
from app.common.database import create_supabase_client


router = APIRouter()


@router.get("/ping", tags=["Admin"])
async def admin_ping(admin_user: AdminUser = Depends(get_current_admin_user)):
    """Admin ping endpoint using FastAPI dependency injection"""
    return {"message": "admin pong", "user_id": admin_user.user_id}


@router.get("/audit/logs", tags=["Admin"])
async def get_audit_logs(
    admin_user: AdminUser = Depends(get_current_admin_user),
    limit: int = Query(50, ge=1, le=500, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    admin_user_filter: Optional[str] = Query(None, description="Filter by admin user ID"),
    action_filter: Optional[str] = Query(None, description="Filter by action type"),
    start_date: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter to date (ISO format)")
) -> Dict[str, Any]:
    """Query admin audit logs with filtering"""
    try:
        supabase = create_supabase_client()
        
        # Start with base query
        query = supabase.table("admin_audit_logs").select("*")
        
        # Apply filters
        if admin_user_filter:
            query = query.eq("admin_user_id", admin_user_filter)
        
        if action_filter:
            query = query.eq("action", action_filter)
            
        if start_date:
            query = query.gte("timestamp", start_date)
            
        if end_date:
            query = query.lte("timestamp", end_date)
        
        # Apply pagination and ordering
        query = query.order("timestamp", desc=True).limit(limit).offset(offset)
        
        result = query.execute()
        
        # Get total count for pagination info
        count_query = supabase.table("admin_audit_logs").select("id", count="exact")
        if admin_user_filter:
            count_query = count_query.eq("admin_user_id", admin_user_filter)
        if action_filter:
            count_query = count_query.eq("action", action_filter)
        if start_date:
            count_query = count_query.gte("timestamp", start_date)
        if end_date:
            count_query = count_query.lte("timestamp", end_date)
            
        count_result = count_query.execute()
        total_count = count_result.count if count_result.count else 0
        
        return {
            "logs": result.data,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total_count,
                "has_more": offset + limit < total_count
            }
        }
        
    except Exception as e:
        return {"error": f"Failed to query audit logs: {str(e)}", "logs": [], "pagination": {"total": 0}}


