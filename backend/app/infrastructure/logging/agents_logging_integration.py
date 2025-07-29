# -*- coding: utf-8 -*-
"""
OpenAI Agents SDK とログシステムの統合モジュール（簡素版）
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

# LoggingServiceのインポート
try:
    from app.infrastructure.logging.service import LoggingService
    LOGGING_SERVICE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Logging service not available: {e}")
    # Use None and handle the checks properly
    LoggingService = None  # type: ignore
    LOGGING_SERVICE_AVAILABLE = False

class MultiAgentWorkflowLogger:
    """マルチエージェントワークフロー全体のログ管理クラス（簡素版）"""
    
    def __init__(
        self,
        article_uuid: str,
        user_id: str,
        organization_id: Optional[str] = None,
        initial_config: Optional[Dict[str, Any]] = None
    ):
        self.article_uuid = article_uuid
        self.user_id = user_id
        self.organization_id = organization_id
        self.initial_config = initial_config or {}
        self.logging_service = LoggingService() if LOGGING_SERVICE_AVAILABLE else None
        self.session_id: Optional[str] = None
        self.current_step = 1
        
    def initialize_session(self) -> str:
        """ログセッションを初期化"""
        if not self.logging_service:
            self.session_id = str(uuid.uuid4())
            logging.warning("LoggingService not available, using UUID as fallback session ID")
            return self.session_id
        
        try:
            self.session_id = self.logging_service.create_log_session(
                article_uuid=self.article_uuid,
                user_id=self.user_id,
                organization_id=self.organization_id,
                initial_input=self.initial_config.get("initial_input", {}),
                seo_keywords=self.initial_config.get("seo_keywords", []),
                image_mode_enabled=self.initial_config.get("image_mode_enabled", False),
                article_style_info=self.initial_config.get("article_style_info", {}),
                generation_theme_count=self.initial_config.get("generation_theme_count", 1),
                target_age_group=self.initial_config.get("target_age_group"),
                persona_settings=self.initial_config.get("persona_settings", {}),
                company_info=self.initial_config.get("company_info", {}),
                session_metadata={"workflow_type": "seo_article_generation"}
            )
            logging.info(f"Initialized log session {self.session_id}")
            return self.session_id
        except Exception as e:
            logging.error(f"Failed to initialize log session: {e}")
            self.session_id = str(uuid.uuid4())
            return self.session_id
    
    def log_workflow_step(self, step_name: str, step_data: Optional[Dict[str, Any]] = None, primary_execution_id: Optional[str] = None):
        """ワークフローステップをログに記録"""
        if self.logging_service and self.session_id:
            try:
                # ステップタイプを決定
                step_type = "autonomous"
                if step_name in ["persona_generated", "theme_proposed", "research_plan_generated", "outline_generated"]:
                    step_type = "user_input"
                elif step_name in ["error", "completed", "cancelled"]:
                    step_type = "terminal"
                elif step_name in ["keyword_analyzing", "persona_generating", "theme_generating", "research_planning", "researching", "writing_sections", "editing"]:
                    step_type = "processing"
                
                step_id = self.logging_service.create_workflow_step_log(
                    session_id=self.session_id,
                    step_name=step_name,
                    step_type=step_type,
                    step_order=self.current_step,
                    step_input=step_data or {},
                    primary_execution_id=primary_execution_id,
                    step_metadata={
                        "article_uuid": self.article_uuid,
                        "timestamp": datetime.now().isoformat(),
                        "user_id": self.user_id,
                        "organization_id": self.organization_id
                    }
                )
                
                logging.info(f"Logged workflow step {step_name} (step_id: {step_id}, order: {self.current_step})")
                self.current_step += 1
                return step_id
                
            except Exception as e:
                logging.warning(f"Failed to log workflow step: {e}")
                return None
    
    def update_workflow_step_status(self, step_id: str, status: str, step_output: Optional[Dict[str, Any]] = None, duration_ms: Optional[int] = None):
        """ワークフローステップの状態を更新"""
        if self.logging_service and step_id:
            try:
                self.logging_service.update_workflow_step_log(
                    step_id=step_id,
                    status=status,
                    step_output=step_output,
                    duration_ms=duration_ms
                )
                logging.info(f"Updated workflow step {step_id} status to {status}")
            except Exception as e:
                logging.warning(f"Failed to update workflow step: {e}")
    
    def complete_session(self, status: str = "completed"):
        """セッションを完了としてマーク"""
        if self.logging_service and self.session_id:
            try:
                self.logging_service.update_session_status(
                    session_id=self.session_id,
                    status=status,
                    completed_steps=self.current_step - 1,
                    completed_at=datetime.now()
                )
            except Exception as e:
                logging.warning(f"Failed to complete session: {e}")
    
    def finalize_session(self, status: str = "completed"):
        """セッションをファイナライズ（complete_sessionのエイリアス）"""
        self.complete_session(status)