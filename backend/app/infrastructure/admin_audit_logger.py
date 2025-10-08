"""Simple admin audit logging system"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from app.common.database import create_supabase_client

logger = logging.getLogger(__name__)


class AdminAuditLogger:
    """Simple admin audit logger that stores structured logs"""
    
    def __init__(self):
        self.supabase = create_supabase_client()
    
    def log_admin_action(
        self,
        admin_user_id: str,
        admin_email: str,
        action: str,
        request_method: str,
        request_path: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        target_resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> None:
        """Log an admin action with structured data"""
        try:
            audit_entry = {
                "timestamp": datetime.now().isoformat(),
                "admin_user_id": admin_user_id,
                "admin_email": admin_email,
                "action": action,
                "request_method": request_method,
                "request_path": request_path,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "target_resource": target_resource,
                "details": details or {},
                "session_id": session_id
            }
            
            # Store in database
            self.supabase.table("admin_audit_logs").insert(audit_entry).execute()
            
            # Also log to application logs
            logger.info(f"[ADMIN_AUDIT] {admin_email} {action} {request_method} {request_path}")
            
        except Exception as e:
            logger.error(f"Failed to log admin action: {e}")
            # Don't raise - audit logging shouldn't break the application