# -*- coding: utf-8 -*-
import asyncio
import time
import logging
from typing import List, Dict, Any, Optional
from fastapi import WebSocketDisconnect
from starlette.websockets import WebSocketState
from openai import BadRequestError, InternalServerError, AuthenticationError
from openai.types.responses import ResponseTextDeltaEvent, ResponseCompletedEvent
from agents import Runner, trace
from agents.exceptions import AgentsException, MaxTurnsExceeded, ModelBehaviorError, UserError
from agents.tracing import custom_span
from rich.console import Console
from pydantic import ValidationError, BaseModel

# 内部モジュールのインポート
from app.core.config import settings
from app.domains.seo_article.schemas import (
    # Server event payloads
    SectionChunkPayload, SelectThemePayload, ApprovePayload, SelectPersonaPayload, EditAndProceedPayload, EditThemePayload, EditPlanPayload, EditOutlinePayload,
    OutlineData, OutlineSectionData,
)
from app.common.schemas import (
    ServerEventMessage, ErrorPayload, UserInputRequestPayload, UserInputType
)
from app.domains.seo_article.context import ArticleContext

console = Console()
logger = logging.getLogger(__name__)

# ログ関連のインポート（オプション）
try:
    from app.infrastructure.logging.service import LoggingService
    from app.infrastructure.analysis.cost_calculation_service import CostCalculationService
    LOGGING_ENABLED = True
except ImportError as e:
    logger.warning(f"Logging system not available: {e}")
    # Use None and handle the checks properly
    LoggingService = None  # type: ignore
    CostCalculationService = None  # type: ignore
    LOGGING_ENABLED = False

def safe_trace_context(workflow_name: str, trace_id: str, group_id: str):
    """トレーシングエラーを安全にハンドリングするコンテキストマネージャー"""
    try:
        return trace(workflow_name=workflow_name, trace_id=trace_id, group_id=group_id)
    except Exception as e:
        logger.warning(f"トレーシング初期化に失敗しました: {e}")
        from contextlib import nullcontext
        return nullcontext()

def safe_custom_span(name: str, data: dict[str, Any] | None = None):
    """カスタムスパンを安全にハンドリングするコンテキストマネージャー"""
    try:
        return custom_span(name=name, data=data)
    except Exception as e:
        logger.warning(f"カスタムスパン作成に失敗しました: {e}")
        from contextlib import nullcontext
        return nullcontext()

def can_continue_autonomously(step: str) -> bool:
    """ステップが自動継続可能かどうかを判定"""
    AUTONOMOUS_STEPS = {
        'keyword_analyzing', 'persona_generating', 'theme_generating',
        'researching', 'writing_sections', 'editing'
    }
    return step in AUTONOMOUS_STEPS

def is_disconnection_resilient(step: str) -> bool:
    """WebSocket切断時でも処理継続可能なステップかどうかを判定"""
    DISCONNECTION_RESILIENT_STEPS = {
        'researching', 'writing_sections', 'editing'
    }
    return step in DISCONNECTION_RESILIENT_STEPS

def requires_user_input(step: str) -> bool:
    """ユーザー入力が必要なステップかどうかを判定"""
    USER_INPUT_STEPS = {
        'persona_generated', 'theme_proposed', 
        'research_plan_generated', 'outline_generated'
    }
    return step in USER_INPUT_STEPS

def calculate_progress_percentage(context: "ArticleContext") -> int:
    """プロセスの進捗率を計算（より詳細な計算）"""
    step_weights = {
        'start': 0,
        'keyword_analyzing': 5,
        'keyword_analyzed': 8,
        'persona_generating': 10,
        'persona_generated': 15,
        'theme_generating': 18,
        'theme_proposed': 25,
        'researching': 40,
        'outline_generating': 65,
        'outline_generated': 70,
        'writing_sections': 75,
        'editing': 95,
        'completed': 100,
        'error': 0
    }
    
    base_progress = step_weights.get(context.current_step, 0)
    
    # より詳細な進捗計算
    if context.current_step == 'researching' and hasattr(context, 'research_progress'):
        # リサーチ進捗を考慮
        if context.research_progress and 'current_query' in context.research_progress:
            query_progress = (context.research_progress['current_query'] / 
                            len(context.research_plan.queries) if context.research_plan else 0) * 20
            base_progress += query_progress
    
    elif context.current_step == 'writing_sections' and hasattr(context, 'sections_progress'):
        # セクション執筆進捗を考慮
        if context.sections_progress and 'current_section' in context.sections_progress:
            section_progress = (context.sections_progress['current_section'] / 
                              len(context.generated_outline.sections) if context.generated_outline else 0) * 20
            base_progress += section_progress
    
    return min(100, int(base_progress))

class GenerationUtils:
    """記事生成に関するユーティリティ関数を提供するクラス"""
    
    def __init__(self, service):
        self.service = service  # ArticleGenerationServiceへの参照

    def normalize_outline_structure(self, outline: Any, top_level_hint: int = 2) -> OutlineData:
        """Ensure outline has consistent heading levels and subsection structure."""
        if outline is None:
            raise ValueError("Outline cannot be None when normalizing structure")

        outline_dict = outline.model_dump() if hasattr(outline, "model_dump") else dict(outline)

        raw_top_level = outline_dict.get("top_level_heading", top_level_hint)
        try:
            top_level = int(raw_top_level)
        except (TypeError, ValueError):
            top_level = top_level_hint or 2
        if top_level not in (2, 3):
            top_level = 2 if top_level < 3 else 3

        def normalize_node(node: Any, fallback_level: int) -> Dict[str, Any]:
            node_dict = node.model_dump() if hasattr(node, "model_dump") else dict(node)

            # Normalize heading information
            heading = node_dict.get("heading") or ""
            node_dict["heading"] = heading.strip()

            raw_level = node_dict.get("level", fallback_level)
            try:
                level = int(raw_level)
            except (TypeError, ValueError):
                level = fallback_level
            level = max(min(level, 6), fallback_level)
            node_dict["level"] = level

            # Normalize optional fields
            if node_dict.get("description") is None:
                node_dict["description"] = ""

            estimated = node_dict.get("estimated_chars")
            if estimated is not None:
                try:
                    node_dict["estimated_chars"] = max(0, int(estimated))
                except (TypeError, ValueError):
                    node_dict["estimated_chars"] = None

            children = node_dict.get("subsections") or []
            normalized_children: List[Dict[str, Any]] = []
            for child in children:
                normalized_child = normalize_node(child, min(level + 1, 6))
                if normalized_child.get("heading"):
                    normalized_children.append(normalized_child)
            node_dict["subsections"] = normalized_children
            return node_dict

        normalized_sections: List[Dict[str, Any]] = []
        for section in outline_dict.get("sections", []) or []:
            normalized_section = normalize_node(section, top_level)
            if normalized_section.get("heading"):
                normalized_sections.append(normalized_section)

        outline_dict["top_level_heading"] = top_level
        outline_dict["sections"] = normalized_sections

        return OutlineData(**outline_dict)

    async def send_server_event(self, context: ArticleContext, payload: BaseModel):
        """WebSocket経由でサーバーイベントを送信するヘルパー関数"""
        if context.websocket:
            try:
                # Check WebSocket state before attempting to send
                if context.websocket.client_state == WebSocketState.CONNECTED:
                    payload_dict = payload.model_dump() if hasattr(payload, 'model_dump') else payload
                    message = ServerEventMessage(payload=payload_dict)
                    await context.websocket.send_json(message.model_dump())
                else:
                    console.print("[yellow]WebSocket not connected, skipping message send.[/yellow]")
            except WebSocketDisconnect:
                console.print("[yellow]WebSocket disconnected while trying to send message.[/yellow]")
                # Don't re-raise - handle gracefully and continue execution
                context.websocket = None  # Clear the reference to prevent further attempts
            except Exception as e:
                console.print(f"[bold red]Error sending WebSocket message: {e}[/bold red]")
                # Don't re-raise general exceptions either - log and continue
        else:
            console.print(f"[Warning] WebSocket not available. Event discarded: {payload.model_dump_json(indent=2)}")

    async def send_error(self, context: ArticleContext, error_message: str, step: Optional[str] = None):
        """WebSocket経由でエラーイベントを送信するヘルパー関数"""
        current_step = step or (context.current_step if context else "unknown")
        payload = ErrorPayload(step=current_step, error_message=error_message)
        await self.send_server_event(context, payload)

    def convert_payload_to_model(self, payload: Dict[str, Any], response_type: UserInputType) -> Optional[BaseModel]:
        """Convert dictionary payload to appropriate Pydantic model based on response type"""
        try:
            if response_type == UserInputType.SELECT_PERSONA:
                return SelectPersonaPayload(**payload)
            elif response_type == UserInputType.SELECT_THEME:
                return SelectThemePayload(**payload)
            elif response_type == UserInputType.APPROVE_PLAN:
                return ApprovePayload(**payload)
            elif response_type == UserInputType.APPROVE_OUTLINE:
                return ApprovePayload(**payload)
            elif response_type == UserInputType.REGENERATE:
                return ApprovePayload(**payload)  # REGENERATE uses ApprovePayload structure
            elif response_type == UserInputType.EDIT_AND_PROCEED:
                return EditAndProceedPayload(**payload)
            elif response_type == UserInputType.EDIT_THEME:
                return EditThemePayload(**payload)
            elif response_type == UserInputType.EDIT_PLAN:
                return EditPlanPayload(**payload)
            elif response_type == UserInputType.EDIT_OUTLINE:
                return EditOutlinePayload(**payload)
            else:
                logger.warning(f"Unknown response type for payload conversion: {response_type}")
                return None
        except ValidationError as e:
            logger.error(f"Failed to convert payload to {response_type} model: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error converting payload: {e}")
            return None

    async def request_user_input(self, context: ArticleContext, request_type: UserInputType, data: Optional[Dict[str, Any]] = None):
        """クライアントに特定のタイプの入力を要求し、応答を待つ"""
        context.expected_user_input = request_type
        context.user_response = None # 前回の応答をクリア
        if context.user_response_event:
            context.user_response_event.clear() # イベントをリセット

        payload = UserInputRequestPayload(request_type=request_type, data=data)
        await self.send_server_event(context, payload)

        # クライアントからの応答を待つ (タイムアウトは handle_websocket_connection で処理)
        console.print(f"[blue]ユーザー応答を待機中... (request_type: {request_type})[/blue]")
        if context.user_response_event:
            await context.user_response_event.wait()
        console.print("[blue]ユーザー応答を受信しました！[/blue]")

        response = context.user_response
        context.user_response = None # 応答をクリア
        context.expected_user_input = None # 期待する入力をクリア
        console.print(f"[blue]ユーザー応答処理完了: {response.response_type if response else 'None'}[/blue]")
        return response

    def extract_token_usage_from_result(self, result) -> Optional[Dict[str, Any]]:
        """OpenAI Agents SDKの実行結果からトークン使用量を抽出"""
        try:
            # デバッグ情報（開発用）
            if logger.isEnabledFor(logging.DEBUG):
                console.print(f"[debug]Result type: {type(result)}")
                if hasattr(result, '__dict__'):
                    console.print(f"[debug]Result.__dict__ keys: {list(result.__dict__.keys())}")
            
            # RunResult._raw_responses から ModelResponse を取得
            raw_responses = None
            # 最も可能性の高い属性名から順番に試行
            candidate_attrs = [
                '_raw_responses', 'raw_responses', '_responses', 'responses',
                '_RunResult__raw_responses', '__raw_responses', 
                'new_items', '_new_items'  # RunItemsかもしれない
            ]
            
            for attr_name in candidate_attrs:
                if hasattr(result, attr_name):
                    attr_value = getattr(result, attr_name)
                    if logger.isEnabledFor(logging.DEBUG):
                        console.print(f"[debug]Checking {attr_name}: {type(attr_value)}")
                    if attr_value and hasattr(attr_value, '__len__') and len(attr_value) > 0:
                        # リストの最初の要素をチェック
                        first_item = attr_value[0]
                        if hasattr(first_item, 'usage') or 'ModelResponse' in str(type(first_item)):
                            raw_responses = attr_value
                            if logger.isEnabledFor(logging.DEBUG):
                                console.print(f"[debug]✅ Found raw_responses via {attr_name}")
                            break
            
            if raw_responses:
                # 最後のModelResponseから使用量を取得
                last_response = raw_responses[-1]
                if hasattr(last_response, 'usage') and last_response.usage:
                    usage = last_response.usage
                    
                    # トークン使用量を抽出
                    input_tokens = getattr(usage, 'input_tokens', 0)
                    output_tokens = getattr(usage, 'output_tokens', 0)
                    cache_tokens = getattr(usage.input_tokens_details, 'cached_tokens', 0) if hasattr(usage, 'input_tokens_details') and usage.input_tokens_details else 0
                    reasoning_tokens = getattr(usage.output_tokens_details, 'reasoning_tokens', 0) if hasattr(usage, 'output_tokens_details') and usage.output_tokens_details else 0
                    total_tokens = getattr(usage, 'total_tokens', 0)
                    
                    # 実際のモデル名を取得（可能であれば）
                    model_name = getattr(last_response, 'model', 'gpt-4o')
                    
                    # 新しいコスト計算サービスを使用
                    if CostCalculationService is not None:
                        cost_info = CostCalculationService.calculate_cost(
                            model_name=model_name,
                            prompt_tokens=input_tokens,
                            completion_tokens=output_tokens,
                            cached_tokens=cache_tokens,
                            reasoning_tokens=reasoning_tokens,
                            total_tokens=total_tokens
                        )
                        estimated_cost = cost_info["cost_breakdown"]["total_cost_usd"]
                    else:
                        # フォールバック: 古いコスト計算方法
                        estimated_cost = self.estimate_cost(usage)
                    
                    return {
                        "model": model_name,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cache_tokens": cache_tokens,
                        "reasoning_tokens": reasoning_tokens,
                        "total_tokens": total_tokens,
                        "estimated_cost": estimated_cost
                    }
            
            # フォールバック: デフォルト値を使用
            logger.warning("No usage data found in result, using fallback values")
            
            # 新しいコスト計算サービスを使用
            if CostCalculationService is not None:
                cost_info = CostCalculationService.calculate_cost(
                    model_name="gpt-4o",
                    prompt_tokens=100,  # 概算値
                    completion_tokens=50,   # 概算値
                    cached_tokens=0,
                    reasoning_tokens=0,
                    total_tokens=150
                )
                estimated_cost = cost_info["cost_breakdown"]["total_cost_usd"]
            else:
                estimated_cost = 0.001
            
            return {
                "model": "gpt-4o",
                "input_tokens": 100,  # 概算値
                "output_tokens": 50,   # 概算値
                "cache_tokens": 0,
                "reasoning_tokens": 0,
                "total_tokens": 150,
                "estimated_cost": estimated_cost
            }
        except Exception as e:
            logger.warning(f"Failed to extract token usage: {e}")
            return None

    def estimate_cost(self, usage) -> float:
        """トークン使用量からコストを概算"""
        try:
            input_tokens = getattr(usage, 'input_tokens', 0)
            output_tokens = getattr(usage, 'output_tokens', 0)
            # GPT-4o の概算料金 (2025年1月時点)
            input_cost = input_tokens * 0.0000025   # $2.50 per 1M tokens
            output_cost = output_tokens * 0.00001    # $10.00 per 1M tokens
            return input_cost + output_cost
        except Exception:
            return 0.001  # デフォルト値

    def estimate_cost_from_metadata(self, metadata: Dict[str, Any]) -> float:
        """メタデータからコストを概算"""
        try:
            input_tokens = metadata.get('input_tokens', 0)
            output_tokens = metadata.get('output_tokens', 0)
            cache_tokens = metadata.get('cache_tokens', 0)
            reasoning_tokens = metadata.get('reasoning_tokens', 0)
            model_name = metadata.get('model', 'gpt-4o')
            
            # 新しいコスト計算サービスを使用
            if CostCalculationService is not None:
                cost_info = CostCalculationService.calculate_cost(
                    model_name=model_name,
                    prompt_tokens=input_tokens,
                    completion_tokens=output_tokens,
                    cached_tokens=cache_tokens,
                    reasoning_tokens=reasoning_tokens
                )
                return cost_info["cost_breakdown"]["total_cost_usd"]
            else:
                # フォールバック: 古いコスト計算方法
                input_cost = input_tokens * 0.0000025
                output_cost = output_tokens * 0.00001
                return input_cost + output_cost
        except Exception:
            return 0.001

    def extract_conversation_history_from_result(self, result, agent_input: str) -> Dict[str, Any]:
        """OpenAI Agents SDKの実行結果から会話履歴を詳細に抽出"""
        try:
            console.print(f"[debug]Starting conversation history extraction. Agent input type: {type(agent_input)}")
            conversation_data: Dict[str, Any] = {
                "system_prompt": "",
                "user_prompt": str(agent_input) if agent_input else "",
                "assistant_response": "",
                "tool_calls": [],
                "reasoning": "",
                "full_output": []
            }
            console.print(f"[debug]Initial conversation_data created: {type(conversation_data)}")

            # まず、resultの構造をデバッグ出力
            if logger.isEnabledFor(logging.DEBUG):
                console.print(f"[debug]Result type: {type(result)}")
                if hasattr(result, '__dict__'):
                    console.print(f"[debug]Result attributes: {list(result.__dict__.keys())}")

            # RunResultから生の応答を取得（より多くの候補を試行）
            raw_responses = None
            candidate_attrs = [
                '_RunResult__raw_responses', 'raw_responses', '_raw_responses', '_responses', 'responses',
                'new_items', '_new_items', 'items', '_items', 'messages', '_messages'
            ]
            
            for attr_name in candidate_attrs:
                if hasattr(result, attr_name):
                    attr_value = getattr(result, attr_name)
                    console.print(f"[debug]Checking {attr_name}: {type(attr_value)}")
                    if attr_value:
                        raw_responses = attr_value
                        console.print(f"[debug]Found raw_responses via {attr_name}")
                        break
            
            if not raw_responses:
                raw_responses = []
                console.print("[debug]No raw_responses found, using empty list")

            # raw_responsesの内容を解析
            if raw_responses:
                console.print(f"[debug]Processing {len(raw_responses)} raw responses")
                for i, response in enumerate(raw_responses):
                    console.print(f"[debug]Response {i}: {type(response)}")
                    
                    # ModelResponseオブジェクトから内容を抽出
                    if hasattr(response, 'output') and response.output:
                        console.print(f"[debug]Response {i} has output: {len(response.output)} items")
                        for j, output_item in enumerate(response.output):
                            console.print(f"[debug]Output item {j}: {type(output_item)}")
                            
                            # メッセージコンテンツの抽出
                            if hasattr(output_item, 'type'):
                                item_type = getattr(output_item, 'type', 'unknown')
                                console.print(f"[debug]Item type: {item_type}")
                                
                                if item_type == 'message' or 'message' in str(item_type):
                                    content = ""
                                    if hasattr(output_item, 'content'):
                                        content = getattr(output_item, 'content', '')
                                        if isinstance(content, list):
                                            # リストの場合、各要素を結合
                                            content_parts: List[str] = []
                                            for part in content:
                                                if hasattr(part, 'text'):
                                                    content_parts.append(str(part.text))
                                                else:
                                                    content_parts.append(str(part))
                                            content = '\n'.join(content_parts)
                                        conversation_data["assistant_response"] += str(content)
                                        console.print(f"[debug]Added message content: {len(str(content))} chars")
                                
                                elif 'tool_call' in str(item_type):
                                    tool_call_data = {
                                        "type": item_type,
                                        "name": getattr(output_item, 'name', ''),
                                        "arguments": getattr(output_item, 'arguments', {}),
                                        "result": getattr(output_item, 'result', None)
                                    }
                                    conversation_data["tool_calls"].append(tool_call_data)
                                    console.print(f"[debug]Added tool call: {tool_call_data['name']}")
                                
                                elif item_type == 'reasoning':
                                    reasoning_content = getattr(output_item, 'content', '')
                                    if isinstance(reasoning_content, list):
                                        reasoning_content = '\n'.join([str(r) for r in reasoning_content])
                                    conversation_data["reasoning"] += str(reasoning_content)
                                    console.print(f"[debug]Added reasoning: {len(str(reasoning_content))} chars")
                            
                            # 全出力を記録
                            conversation_data["full_output"].append({
                                "type": getattr(output_item, 'type', 'unknown'),
                                "content": str(output_item)[:500]
                            })
                    
                    # システムプロンプトの抽出試行
                    if hasattr(response, 'system') and response.system:
                        conversation_data["system_prompt"] = str(response.system)
                        console.print(f"[debug]Found system prompt: {len(conversation_data['system_prompt'])} chars")

            # エージェントの指示をシステムプロンプトとして記録
            if not conversation_data["system_prompt"]:
                if hasattr(result, '_last_agent') and result._last_agent:
                    agent = result._last_agent
                    if hasattr(agent, 'instructions'):
                        instructions = agent.instructions
                        if callable(instructions):
                            # 動的指示の場合は、実行時に解決された値を使用
                            conversation_data["system_prompt"] = "Dynamic instructions (resolved at runtime)"
                            console.print(f"[debug]Marked system prompt as dynamic for agent: {agent.name}")
                        else:
                            conversation_data["system_prompt"] = str(instructions)
                            console.print(f"[debug]Set static system prompt from agent: {len(conversation_data['system_prompt'])} chars")

            # 最終出力も記録
            if hasattr(result, 'final_output') and result.final_output:
                conversation_data["final_output"] = str(result.final_output)[:1000]

            # assistant_responseが空の場合、final_outputを使用
            if not conversation_data["assistant_response"] and conversation_data.get("final_output"):
                conversation_data["assistant_response"] = conversation_data["final_output"]
                console.print(f"[debug]Used final_output as assistant_response: {len(conversation_data['assistant_response'])} chars")

            console.print("[debug]Final conversation data:")
            console.print(f"[debug]  System prompt: {len(conversation_data['system_prompt'])} chars")
            console.print(f"[debug]  User prompt: {len(conversation_data['user_prompt'])} chars")
            console.print(f"[debug]  Assistant response: {len(conversation_data['assistant_response'])} chars")
            console.print(f"[debug]  Tool calls: {len(conversation_data['tool_calls'])}")
            console.print(f"[debug]  Reasoning: {len(conversation_data['reasoning'])} chars")
            
            return conversation_data
            
        except Exception as e:
            logger.warning(f"Failed to extract conversation history: {e}")
            import traceback
            logger.debug(f"Conversation history extraction traceback: {traceback.format_exc()}")
            console.print(f"[red]Conversation history extraction failed: {e}[/red]")
            return {
                "system_prompt": "Unknown",
                "user_prompt": str(agent_input) if agent_input else "",
                "assistant_response": str(result.final_output) if hasattr(result, 'final_output') else "",
                "tool_calls": [],
                "reasoning": "",
                "full_output": []
            }

    async def log_tool_calls(self, execution_id: str, tool_calls: List[Dict[str, Any]]) -> None:
        """ツール呼び出しを詳細にログに記録"""
        if not self.service.logging_service or not tool_calls:
            return
        
        try:
            for i, tool_call in enumerate(tool_calls):
                tool_name = tool_call.get("name", "unknown")
                tool_type = tool_call.get("type", "unknown")
                tool_arguments = tool_call.get("arguments", {})
                tool_result = tool_call.get("result", None)
                
                # ツール名からfunction名を推定
                tool_function = "unknown"
                if "websearch" in tool_name.lower() or "search" in tool_name.lower():
                    tool_function = "web_search"
                elif "serpapi" in tool_name.lower():
                    tool_function = "serp_api_search"
                elif "scrape" in tool_name.lower():
                    tool_function = "web_scraping"
                elif "fetch" in tool_name.lower():
                    tool_function = "web_fetch"
                else:
                    tool_function = tool_name.lower().replace(" ", "_")
                
                # データサイズを概算
                data_size_bytes = len(str(tool_result)) if tool_result else 0
                
                # API呼び出し回数を推定（WebSearchやSerpAPIは複数回呼び出すことがある）
                api_calls_count = 1
                if isinstance(tool_arguments, dict):
                    # 複数URLやクエリがある場合
                    urls = tool_arguments.get("urls", [])
                    queries = tool_arguments.get("queries", [])
                    if urls and isinstance(urls, list):
                        api_calls_count = len(urls)
                    elif queries and isinstance(queries, list):
                        api_calls_count = len(queries)
                
                tool_call_id = self.service.logging_service.create_tool_call_log(
                    execution_id=execution_id,
                    tool_name=tool_name,
                    tool_function=tool_function,
                    call_sequence=i + 1,
                    input_parameters=tool_arguments,
                    output_data={"result": str(tool_result)[:1000] if tool_result else ""},
                    status="completed",
                    data_size_bytes=data_size_bytes,
                    api_calls_count=api_calls_count,
                    tool_metadata={
                        "tool_type": tool_type,
                        "result_length": len(str(tool_result)) if tool_result else 0,
                        "arguments_count": len(tool_arguments) if isinstance(tool_arguments, dict) else 0
                    }
                )
                
                console.print(f"[cyan]🔧 Tool call logged: {tool_call_id} ({tool_name})[/cyan]")
                console.print(f"[dim]  API calls: {api_calls_count}, Data size: {data_size_bytes} bytes[/dim]")
                
        except Exception as e:
            logger.warning(f"Failed to log tool calls: {e}")
            console.print(f"[red]❌ Tool call logging failed: {e}[/red]")

    def safe_trace_context(self, workflow_name: str, trace_id: str, group_id: str):
        """トレーシングエラーを安全にハンドリングするコンテキストマネージャー"""
        return safe_trace_context(workflow_name, trace_id, group_id)

    def safe_custom_span(self, name: str, data: dict[str, Any] | None = None):
        """カスタムスパンを安全にハンドリングするコンテキストマネージャー"""
        return safe_custom_span(name, data)

    def calculate_progress_percentage(self, context: "ArticleContext") -> int:
        """プロセスの進捗率を計算（より詳細な計算）"""
        return calculate_progress_percentage(context)

    def can_continue_autonomously(self, step: str) -> bool:
        """ステップが自動継続可能かどうかを判定"""
        return can_continue_autonomously(step)

    def is_disconnection_resilient(self, step: str) -> bool:
        """WebSocket切断時でも処理継続可能なステップかどうかを判定"""
        return is_disconnection_resilient(step)

    def requires_user_input(self, step: str) -> bool:
        """ユーザー入力が必要なステップかどうかを判定"""
        return requires_user_input(step)

    # 追加のユーティリティメソッド（必要に応じて実装）
    async def handle_streaming_execution(self, agent, agent_input, context, run_config, target_index, target_heading):
        """ストリーミング実行の処理"""
        accumulated_html = ""
        stream_result = None
        last_exception = None
        start_time = time.time()

        for attempt in range(settings.max_retries):
            try:
                console.print(f"[dim]ストリーミング開始 (試行 {attempt + 1}/{settings.max_retries})...[/dim]")
                stream_result = Runner.run_streamed(
                    starting_agent=agent, input=agent_input, context=context, run_config=run_config, max_turns=10
                )
                console.print(f"[dim]ストリーム開始: セクション {target_index + 1}「{target_heading}」[/dim]")
                accumulated_html = ""

                async for event in stream_result.stream_events():
                    if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                        delta = event.data.delta
                        accumulated_html += delta
                        # WebSocketでHTMLチャンクを送信（切断時は無視して継続）
                        try:
                            await self.send_server_event(context, SectionChunkPayload(
                                section_index=target_index,
                                heading=target_heading,
                                html_content_chunk=delta,
                                is_complete=False
                            ))
                        except Exception as ws_err:
                            # WebSocket送信エラーは無視して処理を継続
                            console.print(f"[dim]WebSocket送信エラー（処理継続）: {ws_err}[/dim]")
                            # WebSocket参照をクリアして今後の送信を防ぐ
                            if context.websocket:
                                context.websocket = None
                    elif event.type == "run_item_stream_event" and event.item.type == "tool_call_item":
                        console.print(f"\n[dim]ツール呼び出し: {event.item.name}[/dim]")
                    elif event.type == "raw_response_event" and isinstance(event.data, ResponseCompletedEvent):
                         console.print("\n[dim]レスポンス完了イベント受信[/dim]")

                console.print(f"\n[dim]ストリーム終了: セクション {target_index + 1}「{target_heading}」[/dim]")
                last_exception = None
                break
            except (InternalServerError, BadRequestError, MaxTurnsExceeded, ModelBehaviorError, AgentsException, UserError, AuthenticationError, Exception) as e:
                last_exception = e
                attempt_time = time.time() - start_time
                error_type = type(e).__name__
                
                # エラーメトリクス記録
                logger.warning(f"ストリーミング実行エラー (試行 {attempt + 1}/{settings.max_retries}): {error_type} - {e}, 経過時間: {attempt_time:.2f}秒")
                
                console.print(f"\n[yellow]ストリーミング中にエラー発生 (試行 {attempt + 1}/{settings.max_retries}): {error_type} - {e}[/yellow]")
                if isinstance(e, (BadRequestError, MaxTurnsExceeded, ModelBehaviorError, UserError, AuthenticationError)):
                    break # リトライしないエラー
                if attempt < settings.max_retries - 1:
                    delay = settings.initial_retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    context.error_message = f"ストリーミングエラー: {str(e)}"
                    context.current_step = "error"
                    break

        if context.current_step == "error": 
            raise last_exception or Exception("Streaming execution failed")
        if last_exception: 
            raise last_exception

        return accumulated_html

    async def finalize_section_content(self, context, accumulated_html, target_index, target_heading):
        """セクションコンテンツの最終化処理"""
        from app.domains.seo_article.schemas import ArticleSection

        # セクション完全性をチェック
        if accumulated_html and len(accumulated_html.strip()) > 50:  # 最小長チェック
            generated_section = ArticleSection(
                title=target_heading, content=accumulated_html.strip(), order=target_index
            )
            console.print(f"[green]セクション {target_index + 1}「{generated_section.title}」のHTMLをストリームから構築しました。（{len(accumulated_html)}文字）[/green]")
            
            # 完了イベントを送信（WebSocket切断時は無視される）
            try:
                await self.send_server_event(context, SectionChunkPayload(
                    section_index=target_index, heading=target_heading, html_content_chunk="", is_complete=True
                ))
            except Exception as ws_err:
                console.print(f"[dim]セクション完了イベント送信エラー（処理継続）: {ws_err}[/dim]")
            
            return generated_section
        else:
            # セクションが不完全な場合はエラーとしてリトライ
            error_msg = f"セクション {target_index + 1} のHTMLコンテンツが不完全または空です（{len(accumulated_html) if accumulated_html else 0}文字）"
            console.print(f"[red]{error_msg}[/red]")
            raise ValueError(error_msg)

    def validate_section_completeness(self, context, sections, total_sections):
        """セクション完了の検証"""
        generated_sections_count = len([s for s in context.generated_sections_html if s and s.strip()])
        
        console.print(f"[yellow]セクション進捗: {context.current_section_index}/{total_sections}, 生成済み: {generated_sections_count}[/yellow]")
        
        if context.current_section_index >= total_sections:
            # 実際にすべてのセクションが生成されているかを確認
            if generated_sections_count < total_sections:
                console.print(f"[red]エラー: セクションインデックス({context.current_section_index})は完了を示しているが、実際の生成セクション数({generated_sections_count})が不足[/red]")
                console.print("[yellow]セクションライティングを再開します[/yellow]")
                # 不足分から再開
                context.current_section_index = generated_sections_count
                return False
            else:
                # 画像モードの場合は記事全体に最低1つの画像プレースホルダーがあることを確認
                if getattr(context, 'image_mode', False):
                    total_placeholders = len(getattr(context, 'image_placeholders', []))
                    if total_placeholders == 0:
                        raise ValueError("画像モードで記事を生成しましたが、記事全体に画像プレースホルダーが1つも含まれていません。記事全体で最低1つの画像プレースホルダーが必要です。")
                    console.print(f"[green]画像プレースホルダー検証OK: 記事全体で{total_placeholders}個のプレースホルダーが含まれています[/green]")
                
                context.full_draft_html = context.get_full_draft()
                
                # 空のドラフトチェック
                if not context.full_draft_html or len(context.full_draft_html.strip()) < 100:
                    console.print(f"[red]エラー: 生成されたドラフトが空または短すぎます（{len(context.full_draft_html) if context.full_draft_html else 0}文字）[/red]")
                    raise ValueError("セクションライティングが正常に完了していません。ドラフトが空です。")
                
                return True
        return False
