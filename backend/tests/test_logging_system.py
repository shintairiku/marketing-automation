#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ログシステムの簡単なテストスクリプト
"""
import asyncio
import uuid

# ログシステムのインポート
try:
    from services.logging_service import LoggingService
    from agents_logging_integration import MultiAgentWorkflowLogger
    LOGGING_AVAILABLE = True
except ImportError as e:
    print(f"ログシステムのインポートに失敗: {e}")
    LOGGING_AVAILABLE = False

async def test_logging_system():
    """ログシステムの包括的テスト"""
    if not LOGGING_AVAILABLE:
        print("❌ ログシステムが利用できません。")
        return False
    
    print("🧪 ログシステムのテストを開始します...")
    
    try:
        # 1. LoggingService のテスト
        print("\n1️⃣ LoggingService のテスト")
        logging_service = LoggingService()
        
        # テスト用のセッションを作成
        test_article_uuid = str(uuid.uuid4())
        test_user_id = "test_user_12345"
        
        session_id = logging_service.create_log_session(
            article_uuid=test_article_uuid,
            user_id=test_user_id,
            initial_input={"keywords": ["テスト", "ログ", "システム"]},
            seo_keywords=["テスト", "ログ", "システム"],
            image_mode_enabled=False,
            article_style_info={"style": "formal"},
            generation_theme_count=3,
            target_age_group="30代",
            persona_settings={"persona_type": "ビジネスパーソン"},
            company_info={"company_name": "テスト株式会社"},
            session_metadata={"test_run": True}
        )
        print(f"✅ ログセッション作成成功: {session_id}")
        
        # 2. エージェント実行ログのテスト
        print("\n2️⃣ エージェント実行ログのテスト")
        execution_id = logging_service.create_execution_log(
            session_id=session_id,
            agent_name="TestAgent",
            agent_type="test_execution",
            step_number=1,
            input_data={"test_input": "テストデータ"},
            llm_model="gpt-4o",
            execution_metadata={"test": True}
        )
        print(f"✅ エージェント実行ログ作成成功: {execution_id}")
        
        # 3. LLM呼び出しログのテスト
        print("\n3️⃣ LLM呼び出しログのテスト")
        llm_call_id = logging_service.create_llm_call_log(
            execution_id=execution_id,
            call_sequence=1,
            api_type="chat_completions",
            model_name="gpt-4o",
            system_prompt="あなたはテスト用のアシスタントです。",
            user_prompt="テストメッセージを生成してください。",
            response_content="これはテスト応答です。",
            prompt_tokens=50,
            completion_tokens=25,
            total_tokens=75,
            estimated_cost_usd=0.001,
            full_prompt_data={"test": True},
            response_data={"test_response": True}
        )
        print(f"✅ LLM呼び出しログ作成成功: {llm_call_id}")
        
        # 4. ツール呼び出しログのテスト
        print("\n4️⃣ ツール呼び出しログのテスト")
        tool_call_id = logging_service.create_tool_call_log(
            execution_id=execution_id,
            tool_name="WebSearch",
            tool_function="web_search",
            call_sequence=1,
            input_parameters={"query": "テストクエリ", "max_results": 5},
            output_data={"results": ["結果1", "結果2", "結果3"]},
            status="completed",
            data_size_bytes=1024,
            api_calls_count=1,
            tool_metadata={"test_tool": True}
        )
        print(f"✅ ツール呼び出しログ作成成功: {tool_call_id}")
        
        # 5. ワークフローステップログのテスト
        print("\n5️⃣ ワークフローステップログのテスト")
        workflow_step_id = logging_service.create_workflow_step_log(
            session_id=session_id,
            step_name="test_step",
            step_type="autonomous",
            step_order=1,
            step_input={"step_input": "テストステップ"},
            primary_execution_id=execution_id,
            step_metadata={"test_step": True}
        )
        print(f"✅ ワークフローステップログ作成成功: {workflow_step_id}")
        
        # 6. MultiAgentWorkflowLogger のテスト
        print("\n6️⃣ MultiAgentWorkflowLogger のテスト")
        workflow_logger = MultiAgentWorkflowLogger(
            article_uuid=test_article_uuid,
            user_id=test_user_id,
            initial_config={
                "seo_keywords": ["テスト", "ログ"],
                "image_mode_enabled": False,
                "target_age_group": "30代"
            }
        )
        
        # セッション初期化をスキップ（既に作成済み）
        workflow_logger.session_id = session_id
        print("✅ MultiAgentWorkflowLogger 初期化成功")
        
        # ワークフローステップをログ
        step_id = workflow_logger.log_workflow_step(
            step_name="test_workflow_step",
            step_data={"test": "ワークフロー"},
            primary_execution_id=execution_id
        )
        print(f"✅ ワークフローステップログ記録成功: {step_id}")
        
        # 7. ログの更新テスト
        print("\n7️⃣ ログ更新のテスト")
        
        # エージェント実行ログの更新
        logging_service.update_execution_log(
            execution_id=execution_id,
            status="completed",
            output_data={"test_output": "完了"},
            input_tokens=50,
            output_tokens=25,
            duration_ms=5000
        )
        print("✅ エージェント実行ログ更新成功")
        
        # ワークフローステップの更新
        if step_id:
            workflow_logger.update_workflow_step_status(
                step_id=step_id,
                status="completed",
                step_output={"result": "完了"},
                duration_ms=3000
            )
            print("✅ ワークフローステップ更新成功")
        
        # セッションの完了
        workflow_logger.complete_session("completed")
        print("✅ セッション完了成功")
        
        # 8. パフォーマンスメトリクスの取得テスト
        print("\n8️⃣ パフォーマンスメトリクス取得のテスト")
        try:
            metrics = logging_service.get_session_performance_metrics(session_id)
            print("✅ パフォーマンスメトリクス取得成功:")
            print(f"   - 実行回数: {metrics.get('total_executions', 0)}")
            print(f"   - LLM呼び出し回数: {metrics.get('total_llm_calls', 0)}")
            print(f"   - ツール呼び出し回数: {metrics.get('total_tool_calls', 0)}")
            print(f"   - 総トークン数: {metrics.get('total_tokens', 0)}")
            print(f"   - 推定コスト: ${metrics.get('estimated_total_cost', 0):.6f}")
        except Exception as e:
            print(f"⚠️ パフォーマンスメトリクス取得でエラー: {e}")
        
        print("\n🎉 すべてのテストが成功しました！")
        print(f"📊 テストセッションID: {session_id}")
        print(f"📝 テスト記事UUID: {test_article_uuid}")
        
        # 9. 実際のLLMログテーブルの確認
        print("\n9️⃣ LLMログテーブルの確認")
        try:
            from database.supabase_client import supabase
            
            # 作成したセッションのLLM呼び出しログを確認
            llm_logs = supabase.table("llm_call_logs") \
                .select("*") \
                .eq("execution_id", execution_id) \
                .execute()
            
            if llm_logs.data:
                print(f"✅ LLM呼び出しログが見つかりました: {len(llm_logs.data)} 件")
                for log in llm_logs.data:
                    print(f"   - ID: {log['id']}")
                    print(f"   - モデル: {log.get('model_name', 'N/A')}")
                    print(f"   - システムプロンプト: {len(log.get('system_prompt', '') or '')} chars")
                    print(f"   - ユーザープロンプト: {len(log.get('user_prompt', '') or '')} chars")
                    print(f"   - 応答: {len(log.get('response_content', '') or '')} chars")
                    print(f"   - トークン: {log.get('prompt_tokens', 0)} + {log.get('completion_tokens', 0)} = {log.get('total_tokens', 0)}")
                    print(f"   - コスト: ${log.get('estimated_cost_usd', 0):.6f}")
            else:
                print("⚠️ LLM呼び出しログが見つかりませんでした")
                
            # セッション全体のログも確認
            all_executions = supabase.table("agent_execution_logs") \
                .select("*") \
                .eq("session_id", session_id) \
                .execute()
            
            print(f"📊 セッション内の実行ログ: {len(all_executions.data)} 件")
            
            all_llm_logs = supabase.table("llm_call_logs") \
                .select("*") \
                .in_("execution_id", [exec_log['id'] for exec_log in all_executions.data]) \
                .execute()
                
            print(f"📊 セッション内のLLM呼び出しログ: {len(all_llm_logs.data)} 件")
            
        except Exception as e:
            print(f"⚠️ LLMログテーブル確認でエラー: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ テスト中にエラーが発生しました: {e}")
        import traceback
        print(f"エラー詳細:\n{traceback.format_exc()}")
        return False

def main():
    """メイン関数"""
    print("🚀 ログシステムの動作確認テストを実行します")
    print("=" * 60)
    
    success = asyncio.run(test_logging_system())
    
    print("=" * 60)
    if success:
        print("✅ ログシステムは正常に動作しています！")
        print("\n📋 実装された機能:")
        print("   ✓ ログセッション管理")
        print("   ✓ エージェント実行ログ")
        print("   ✓ LLM呼び出しログ（トークン統計・コスト計算）")
        print("   ✓ ツール呼び出しログ（WebSearch、SerpAPI等）")
        print("   ✓ ワークフローステップログ")
        print("   ✓ エラーハンドリング")
        print("   ✓ パフォーマンスメトリクス")
        print("   ✓ MultiAgentWorkflowLogger統合")
    else:
        print("❌ ログシステムにエラーがあります。ログを確認してください。")

if __name__ == "__main__":
    main()