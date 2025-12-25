# -*- coding: utf-8 -*-
"""
エージェントログシステム用サービス層
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.common.database import supabase

logger = logging.getLogger(__name__)

class LoggingService:
    """エージェントログシステムのサービス層"""
    
    @staticmethod
    def create_log_session(
        article_uuid: str,
        user_id: str,
        organization_id: Optional[str] = None,
        initial_input: Optional[Dict[str, Any]] = None,
        seo_keywords: Optional[List[str]] = None,
        image_mode_enabled: bool = False,
        article_style_info: Optional[Dict[str, Any]] = None,
        generation_theme_count: int = 1,
        target_age_group: Optional[str] = None,
        target_age_groups: Optional[List[str]] = None,
        persona_settings: Optional[Dict[str, Any]] = None,
        company_info: Optional[Dict[str, Any]] = None,
        session_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """新しいログセッションを作成"""
        try:
            logger.info(f"Creating log session for article_uuid: {article_uuid}, user_id: {user_id}")
            session_data = {
                "article_uuid": article_uuid,
                "user_id": user_id,
                "organization_id": organization_id,
                "initial_input": initial_input or {},
                "seo_keywords": seo_keywords or [],
                "image_mode_enabled": image_mode_enabled,
                "article_style_info": article_style_info or {},
                "generation_theme_count": generation_theme_count,
                "target_age_group": target_age_group,
                "persona_settings": persona_settings or {},
                "company_info": company_info or {},
                "session_metadata": session_metadata or {},
                "status": "started"
            }
            if target_age_groups:
                metadata = session_data["session_metadata"].copy()
                metadata.setdefault("audience_preferences", {})["target_age_groups"] = target_age_groups
                session_data["session_metadata"] = metadata
            
            logger.info(f"Inserting session data: {session_data}")
            result = supabase.table("agent_log_sessions").insert(session_data).execute()
            session_id = result.data[0]["id"]
            
            logger.info(f"Created log session {session_id} for article {article_uuid}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create log session: {e}")
            raise

    @staticmethod
    def update_session_status(
        session_id: str,
        status: str,
        total_steps: Optional[int] = None,
        completed_steps: Optional[int] = None,
        completed_at: Optional[datetime] = None
    ) -> None:
        """セッションの状態を更新"""
        try:
            update_data: Dict[str, Any] = {"status": status}
            
            # valid_step_counts制約を満たすため、ステップ数の整合性をチェック
            if total_steps is not None or completed_steps is not None:
                # 現在の値を取得
                current_session = supabase.table("agent_log_sessions").select("total_steps, completed_steps").eq("id", session_id).execute()
                if current_session.data:
                    current_total = current_session.data[0].get("total_steps", 0)
                    current_completed = current_session.data[0].get("completed_steps", 0)
                    
                    # 新しい値を決定
                    new_total = total_steps if total_steps is not None else current_total
                    new_completed = completed_steps if completed_steps is not None else current_completed
                    
                    # 制約違反を防ぐための調整
                    if new_completed > new_total:
                        logger.warning(f"completed_steps({new_completed}) > total_steps({new_total}), adjusting total_steps")
                        new_total = new_completed
                    
                    # total_stepsが0の場合、completed_stepsも0にする
                    if new_total == 0 and new_completed > 0:
                        logger.warning(f"total_steps is 0 but completed_steps is {new_completed}, setting both to {new_completed}")
                        new_total = new_completed
                    
                    update_data["total_steps"] = new_total
                    update_data["completed_steps"] = new_completed
                    
                    logger.info(f"Session {session_id} steps: {current_total}→{new_total} (total), {current_completed}→{new_completed} (completed)")
            
            if completed_at is not None:
                update_data["completed_at"] = completed_at.isoformat()
            
            supabase.table("agent_log_sessions").update(update_data).eq("id", session_id).execute()
            logger.info(f"Updated session {session_id} status to {status}")
            
        except Exception as e:
            logger.error(f"Failed to update session status: {e}")
            raise

    @staticmethod
    def create_execution_log(
        session_id: str,
        agent_name: str,
        agent_type: str,
        step_number: int,
        sub_step_number: int = 1,
        input_data: Optional[Dict[str, Any]] = None,
        llm_model: Optional[str] = None,
        llm_provider: str = "openai",
        execution_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """エージェント実行ログを作成"""
        try:
            logger.info(f"Creating execution log for session {session_id}, agent {agent_name}")
            execution_data = {
                "session_id": session_id,
                "agent_name": agent_name,
                "agent_type": agent_type,
                "step_number": step_number,
                "sub_step_number": sub_step_number,
                "input_data": input_data or {},
                "llm_model": llm_model,
                "llm_provider": llm_provider,
                "execution_metadata": execution_metadata or {},
                "status": "started"
            }
            
            logger.info(f"Inserting execution data: {execution_data}")
            result = supabase.table("agent_execution_logs").insert(execution_data).execute()
            execution_id = result.data[0]["id"]
            
            logger.info(f"Created execution log {execution_id} for agent {agent_name}")
            return execution_id
            
        except Exception as e:
            logger.error(f"Failed to create execution log: {e}")
            raise

    @staticmethod
    def update_execution_log(
        execution_id: str,
        status: str,
        output_data: Optional[Dict[str, Any]] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_tokens: int = 0,
        reasoning_tokens: int = 0,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """エージェント実行ログを更新"""
        try:
            update_data: Dict[str, Any] = {"status": status}
            
            if output_data is not None:
                update_data["output_data"] = output_data
            if input_tokens > 0:
                update_data["input_tokens"] = input_tokens
            if output_tokens > 0:
                update_data["output_tokens"] = output_tokens
            if cache_tokens > 0:
                update_data["cache_tokens"] = cache_tokens
            if reasoning_tokens > 0:
                update_data["reasoning_tokens"] = reasoning_tokens
            if duration_ms is not None:
                update_data["duration_ms"] = duration_ms
            if error_message:
                update_data["error_message"] = error_message
            if error_details:
                update_data["error_details"] = error_details
            if status in ["completed", "failed", "timeout"]:
                update_data["completed_at"] = datetime.now().isoformat()
            
            supabase.table("agent_execution_logs").update(update_data).eq("id", execution_id).execute()
            logger.info(f"Updated execution log {execution_id} status to {status}")
            
        except Exception as e:
            logger.error(f"Failed to update execution log: {e}")
            raise

    @staticmethod
    def create_llm_call_log(
        execution_id: str,
        call_sequence: int,
        api_type: str,
        model_name: str,
        provider: str = "openai",
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        full_prompt_data: Optional[Dict[str, Any]] = None,
        response_content: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        cached_tokens: int = 0,
        reasoning_tokens: int = 0,
        response_time_ms: Optional[int] = None,
        estimated_cost_usd: Optional[float] = None,
        http_status_code: Optional[int] = None,
        api_response_id: Optional[str] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0
    ) -> str:
        """LLM呼び出しログを作成"""
        try:
            llm_call_data = {
                "execution_id": execution_id,
                "call_sequence": call_sequence,
                "api_type": api_type,
                "model_name": model_name,
                "provider": provider,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "full_prompt_data": full_prompt_data or {},
                "response_content": response_content,
                "response_data": response_data or {},
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cached_tokens": cached_tokens,
                "reasoning_tokens": reasoning_tokens,
                "response_time_ms": response_time_ms,
                "estimated_cost_usd": estimated_cost_usd,
                "http_status_code": http_status_code,
                "api_response_id": api_response_id,
                "error_type": error_type,
                "error_message": error_message,
                "retry_count": retry_count
            }
            
            result = supabase.table("llm_call_logs").insert(llm_call_data).execute()
            call_id = result.data[0]["id"]
            
            logger.info(f"Created LLM call log {call_id} for model {model_name}")
            return call_id
            
        except Exception as e:
            logger.error(f"Failed to create LLM call log: {e}")
            raise

    @staticmethod
    def create_tool_call_log(
        execution_id: str,
        tool_name: str,
        tool_function: str,
        call_sequence: int,
        input_parameters: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        status: str = "started",
        execution_time_ms: Optional[int] = None,
        data_size_bytes: Optional[int] = None,
        api_calls_count: int = 1,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0,
        tool_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """ツール呼び出しログを作成"""
        try:
            tool_call_data = {
                "execution_id": execution_id,
                "tool_name": tool_name,
                "tool_function": tool_function,
                "call_sequence": call_sequence,
                "input_parameters": input_parameters or {},
                "output_data": output_data or {},
                "status": status,
                "execution_time_ms": execution_time_ms,
                "data_size_bytes": data_size_bytes,
                "api_calls_count": api_calls_count,
                "error_type": error_type,
                "error_message": error_message,
                "retry_count": retry_count,
                "tool_metadata": tool_metadata or {}
            }
            
            if status in ["completed", "failed", "timeout"]:
                tool_call_data["completed_at"] = datetime.now().isoformat()
            
            result = supabase.table("tool_call_logs").insert(tool_call_data).execute()
            call_id = result.data[0]["id"]
            
            logger.info(f"Created tool call log {call_id} for tool {tool_name}")
            return call_id
            
        except Exception as e:
            logger.error(f"Failed to create tool call log: {e}")
            raise

    @staticmethod
    def update_tool_call_log(
        call_id: str,
        status: str,
        output_data: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[int] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """ツール呼び出しログを更新"""
        try:
            update_data: Dict[str, Any] = {"status": status}
            
            if output_data is not None:
                update_data["output_data"] = output_data
            if execution_time_ms is not None:
                update_data["execution_time_ms"] = execution_time_ms
            if error_type:
                update_data["error_type"] = error_type
            if error_message:
                update_data["error_message"] = error_message
            if status in ["completed", "failed", "timeout"]:
                update_data["completed_at"] = datetime.now().isoformat()
            
            supabase.table("tool_call_logs").update(update_data).eq("id", call_id).execute()
            logger.info(f"Updated tool call log {call_id} status to {status}")
            
        except Exception as e:
            logger.error(f"Failed to update tool call log: {e}")
            raise

    @staticmethod
    def create_workflow_step_log(
        session_id: str,
        step_name: str,
        step_type: str,
        step_order: int,
        step_input: Optional[Dict[str, Any]] = None,
        primary_execution_id: Optional[str] = None,
        step_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """ワークフローステップログを作成"""
        try:
            step_data = {
                "session_id": session_id,
                "step_name": step_name,
                "step_type": step_type,
                "step_order": step_order,
                "step_input": step_input or {},
                "primary_execution_id": primary_execution_id,
                "step_metadata": step_metadata or {},
                "status": "pending"
            }
            
            result = supabase.table("workflow_step_logs").insert(step_data).execute()
            step_id = result.data[0]["id"]
            
            logger.info(f"Created workflow step log {step_id} for step {step_name}")
            return step_id
            
        except Exception as e:
            logger.error(f"Failed to create workflow step log: {e}")
            raise

    @staticmethod
    def update_workflow_step_log(
        step_id: str,
        status: str,
        step_output: Optional[Dict[str, Any]] = None,
        intermediate_results: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None
    ) -> None:
        """ワークフローステップログを更新"""
        try:
            update_data: Dict[str, Any] = {"status": status}
            
            if step_output is not None:
                update_data["step_output"] = step_output
            if intermediate_results is not None:
                update_data["intermediate_results"] = intermediate_results
            if duration_ms is not None:
                update_data["duration_ms"] = duration_ms
            
            if status == "running" and "started_at" not in update_data:
                update_data["started_at"] = datetime.now().isoformat()
            elif status in ["completed", "failed", "skipped"]:
                update_data["completed_at"] = datetime.now().isoformat()
            
            supabase.table("workflow_step_logs").update(update_data).eq("id", step_id).execute()
            logger.info(f"Updated workflow step log {step_id} status to {status}")
            
        except Exception as e:
            logger.error(f"Failed to update workflow step log: {e}")
            raise

    @staticmethod
    def get_session_performance_metrics(session_id: str) -> Dict[str, Any]:
        """セッションのパフォーマンスメトリクスを取得"""
        try:
            # セッション情報
            session_result = supabase.table("agent_log_sessions").select("*").eq("id", session_id).execute()
            if not session_result.data:
                raise ValueError(f"Session {session_id} not found")
            
            session = session_result.data[0]
            
            # 実行ログ統計
            execution_result = supabase.table("agent_execution_logs").select("*").eq("session_id", session_id).execute()
            executions = execution_result.data
            
            # LLM呼び出し統計
            llm_calls_result = supabase.rpc("get_session_llm_stats", {"session_id": session_id}).execute()
            
            # ツール呼び出し統計
            tool_calls_result = supabase.rpc("get_session_tool_stats", {"session_id": session_id}).execute()
            
            total_tokens = sum(
                (ex.get("input_tokens", 0) + ex.get("output_tokens", 0) + 
                 ex.get("cache_tokens", 0) + ex.get("reasoning_tokens", 0))
                for ex in executions
            )
            
            metrics = {
                "session_id": session_id,
                "session_status": session["status"],
                "total_executions": len(executions),
                "total_tokens": total_tokens,
                "session_duration_ms": None,
                "created_at": session["created_at"],
                "completed_at": session.get("completed_at"),
                "executions_by_type": {},
                "llm_calls_stats": llm_calls_result.data if llm_calls_result.data else {},
                "tool_calls_stats": tool_calls_result.data if tool_calls_result.data else {}
            }
            
            # セッション継続時間計算
            if session.get("completed_at"):
                from datetime import datetime
                start = datetime.fromisoformat(session["created_at"].replace('Z', '+00:00'))
                end = datetime.fromisoformat(session["completed_at"].replace('Z', '+00:00'))
                metrics["session_duration_ms"] = int((end - start).total_seconds() * 1000)
            
            # エージェントタイプ別統計
            for execution in executions:
                agent_type = execution["agent_type"]
                if agent_type not in metrics["executions_by_type"]:
                    metrics["executions_by_type"][agent_type] = {
                        "count": 0,
                        "total_tokens": 0,
                        "avg_duration_ms": 0,
                        "success_rate": 0
                    }
                
                metrics["executions_by_type"][agent_type]["count"] += 1
                metrics["executions_by_type"][agent_type]["total_tokens"] += (
                    execution.get("input_tokens", 0) + execution.get("output_tokens", 0) +
                    execution.get("cache_tokens", 0) + execution.get("reasoning_tokens", 0)
                )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get session performance metrics: {e}")
            raise

    @staticmethod
    def get_user_session_logs(
        user_id: str,
        organization_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """ユーザーのセッションログを取得"""
        try:
            query = supabase.table("agent_log_sessions").select("*")
            
            if organization_id:
                query = query.eq("organization_id", organization_id)
            else:
                query = query.eq("user_id", user_id)
            
            if status_filter:
                query = query.eq("status", status_filter)
            
            query = query.order("created_at", desc=True).limit(limit).offset(offset)
            result = query.execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Failed to get user session logs: {e}")
            raise
