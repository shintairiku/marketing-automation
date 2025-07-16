# -*- coding: utf-8 -*-
"""
エージェントログシステム用のPydanticモデル（Supabase直接アクセス用）
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

# 現在は直接Supabaseを使用するため、Pydanticモデルで定義
# SQLAlchemyモデルは後で必要に応じて実装

class AgentLogSessionData(BaseModel):
    """ログセッション作成用データ"""
    article_uuid: str
    user_id: str
    organization_id: Optional[str] = None
    initial_input: Dict[str, Any] = {}
    seo_keywords: List[str] = []
    image_mode_enabled: bool = False
    article_style_info: Dict[str, Any] = {}
    generation_theme_count: int = 1
    target_age_group: Optional[str] = None
    persona_settings: Dict[str, Any] = {}
    company_info: Dict[str, Any] = {}
    session_metadata: Dict[str, Any] = {}
    status: str = "started"

class AgentExecutionLogData(BaseModel):
    """エージェント実行ログ作成用データ"""
    session_id: str
    agent_name: str
    agent_type: str
    step_number: int
    sub_step_number: int = 1
    input_data: Dict[str, Any] = {}
    llm_model: Optional[str] = None
    llm_provider: str = "openai"
    execution_metadata: Dict[str, Any] = {}
    status: str = "started"

class LLMCallLogData(BaseModel):
    """LLM呼び出しログ作成用データ"""
    execution_id: str
    call_sequence: int
    api_type: str = "chat_completions"
    model_name: str
    provider: str = "openai"
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    full_prompt_data: Dict[str, Any] = {}
    response_content: Optional[str] = None
    response_data: Dict[str, Any] = {}
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    response_time_ms: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    http_status_code: Optional[int] = None
    api_response_id: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0

class ToolCallLogData(BaseModel):
    """ツール呼び出しログ作成用データ"""
    execution_id: str
    tool_name: str
    tool_function: str
    call_sequence: int
    input_parameters: Dict[str, Any] = {}
    output_data: Dict[str, Any] = {}
    status: str = "started"
    execution_time_ms: Optional[int] = None
    data_size_bytes: Optional[int] = None
    api_calls_count: int = 1
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    tool_metadata: Dict[str, Any] = {}

class WorkflowStepLogData(BaseModel):
    """ワークフローステップログ作成用データ"""
    session_id: str
    step_name: str
    step_type: str
    step_order: int
    step_input: Dict[str, Any] = {}
    primary_execution_id: Optional[str] = None
    step_metadata: Dict[str, Any] = {}
    status: str = "pending"