# -*- coding: utf-8 -*-
"""
Supabase → Notion同期サービス
LLMログデータをSupabaseからNotionに同期する
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from database.supabase_client import supabase
from services.notion_service import NotionService
from services.logging_service import LoggingService

logger = logging.getLogger(__name__)

class NotionSyncService:
    """Supabase → Notion同期サービスクラス"""
    
    def __init__(self):
        self.notion_service = NotionService()
        self.logging_service = LoggingService()
        self.synced_sessions = set()  # 既に同期済みのセッションIDを記録
        
    def sync_session_to_notion(self, session_id: str) -> bool:
        """指定されたセッションをNotionに同期"""
        try:
            # セッションデータを取得
            session_data = self._get_complete_session_data(session_id)
            if not session_data:
                logger.error(f"セッションデータが見つかりません: {session_id}")
                return False
            
            # Notionページを作成
            page_id = self.notion_service.create_llm_session_page(session_data)
            if page_id:
                self.synced_sessions.add(session_id)
                logger.info(f"セッション {session_id} をNotionに同期完了: {page_id}")
                print(f"✅ セッション {session_id[:8]}... をNotionに同期完了")
                return True
            else:
                logger.error(f"Notionページ作成失敗: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"セッション同期エラー: {e}")
            print(f"❌ セッション同期エラー: {e}")
            return False
    
    def sync_recent_sessions(self, hours: int = 24) -> int:
        """指定された時間内の最新セッションをNotionに同期"""
        try:
            # 最新のセッションを取得（時間計算を修正）
            from datetime import timedelta
            cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            
            recent_sessions = supabase.table("agent_log_sessions") \
                .select("id, status, created_at") \
                .gte("created_at", cutoff_time) \
                .order("created_at", desc=True) \
                .execute()
            
            synced_count = 0
            total_sessions = len(recent_sessions.data)
            
            print(f"🔄 {hours}時間以内の{total_sessions}件のセッションを同期開始...")
            
            for session in recent_sessions.data:
                session_id = session['id']
                
                # 既に同期済みの場合はスキップ
                if session_id in self.synced_sessions:
                    continue
                
                # 完了または失敗したセッションのみ同期
                if session['status'] in ['completed', 'failed']:
                    if self.sync_session_to_notion(session_id):
                        synced_count += 1
                    
            print(f"✅ {synced_count}/{total_sessions} セッションの同期が完了しました")
            return synced_count
            
        except Exception as e:
            logger.error(f"最新セッション同期エラー: {e}")
            print(f"❌ 最新セッション同期エラー: {e}")
            return 0
    
    def _get_complete_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """セッションの完全なデータを取得"""
        try:
            # 1. セッション基本情報を取得
            session_result = supabase.table("agent_log_sessions") \
                .select("*") \
                .eq("id", session_id) \
                .execute()
            
            if not session_result.data:
                return None
            
            session = session_result.data[0]
            
            # 2. エージェント実行ログを取得
            executions_result = supabase.table("agent_execution_logs") \
                .select("*") \
                .eq("session_id", session_id) \
                .order("started_at", desc=False) \
                .execute()
            
            executions = executions_result.data
            
            # 3. LLM呼び出しログを取得
            execution_ids = [exec_log['id'] for exec_log in executions]
            llm_calls = []
            
            if execution_ids:
                llm_calls_result = supabase.table("llm_call_logs") \
                    .select("*") \
                    .in_("execution_id", execution_ids) \
                    .order("called_at", desc=False) \
                    .execute()
                
                # エージェント名を追加
                for llm_call in llm_calls_result.data:
                    execution_id = llm_call['execution_id']
                    matching_execution = next((e for e in executions if e['id'] == execution_id), None)
                    if matching_execution:
                        llm_call['agent_name'] = matching_execution['agent_name']
                        llm_call['agent_type'] = matching_execution['agent_type']
                
                llm_calls = llm_calls_result.data
            
            # 4. ツール呼び出しログを取得
            tool_calls = []
            if execution_ids:
                tool_calls_result = supabase.table("tool_call_logs") \
                    .select("*") \
                    .in_("execution_id", execution_ids) \
                    .order("called_at", desc=False) \
                    .execute()
                
                tool_calls = tool_calls_result.data
            
            # 5. ワークフローステップログを取得
            workflow_steps_result = supabase.table("workflow_step_logs") \
                .select("*") \
                .eq("session_id", session_id) \
                .order("step_order", desc=False) \
                .execute()
            
            workflow_steps = workflow_steps_result.data
            
            # 6. 統計データを計算
            total_tokens = sum(llm_call.get('total_tokens', 0) for llm_call in llm_calls)
            input_tokens = sum(llm_call.get('prompt_tokens', 0) for llm_call in llm_calls)
            output_tokens = sum(llm_call.get('completion_tokens', 0) for llm_call in llm_calls)
            cache_tokens = sum(llm_call.get('cached_tokens', 0) for llm_call in llm_calls)
            reasoning_tokens = sum(llm_call.get('reasoning_tokens', 0) for llm_call in llm_calls)
            estimated_total_cost = sum(llm_call.get('estimated_cost_usd', 0) for llm_call in llm_calls)
            
            total_duration_ms = sum(exec_log.get('duration_ms', 0) or 0 for exec_log in executions)
            
            # 7. 完全なデータを構築
            complete_data = {
                # セッション基本情報
                **session,
                
                # 統計データ
                "total_tokens": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_tokens": cache_tokens,
                "reasoning_tokens": reasoning_tokens,
                "estimated_total_cost": estimated_total_cost,
                "total_duration_ms": total_duration_ms,
                
                # 詳細データ
                "executions": executions,
                "llm_calls": llm_calls,
                "tool_calls": tool_calls,
                "workflow_steps": workflow_steps,
                
                # パフォーマンスメトリクス
                "performance_metrics": {
                    "total_executions": len(executions),
                    "total_llm_calls": len(llm_calls),
                    "total_tool_calls": len(tool_calls),
                    "total_workflow_steps": len(workflow_steps),
                    "avg_execution_duration_ms": total_duration_ms / len(executions) if executions else 0,
                    "success_rate": len([e for e in executions if e.get('status') == 'completed']) / len(executions) if executions else 0
                }
            }
            
            return complete_data
            
        except Exception as e:
            logger.error(f"セッションデータ取得エラー: {e}")
            return None
    
    def test_sync(self) -> bool:
        """同期機能のテスト"""
        try:
            print("🧪 Notion同期機能のテストを開始...")
            
            # 1. Notion接続テスト
            print("\n1️⃣ Notion API接続テスト")
            if not self.notion_service.test_connection():
                return False
            
            # 2. 最新のセッションを1件取得してテスト同期
            print("\n2️⃣ テストセッション取得")
            recent_sessions = supabase.table("agent_log_sessions") \
                .select("id, status, created_at") \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
            
            if not recent_sessions.data:
                print("❌ テスト用のセッションが見つかりません")
                return False
            
            test_session = recent_sessions.data[0]
            session_id = test_session['id']
            
            print(f"   テストセッション: {session_id}")
            print(f"   ステータス: {test_session['status']}")
            print(f"   作成日時: {test_session['created_at']}")
            
            # 3. テスト同期実行
            print("\n3️⃣ テスト同期実行")
            success = self.sync_session_to_notion(session_id)
            
            if success:
                print("✅ テスト同期が成功しました！")
                return True
            else:
                print("❌ テスト同期に失敗しました")
                return False
            
        except Exception as e:
            logger.error(f"同期テストエラー: {e}")
            print(f"❌ 同期テストエラー: {e}")
            return False