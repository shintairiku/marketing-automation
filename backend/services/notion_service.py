# -*- coding: utf-8 -*-
"""
Notion API統合サービス
SupabaseのLLMログデータをNotionデータベースと同期する
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import requests
import json

from core.config import settings

logger = logging.getLogger(__name__)

class NotionService:
    """Notion API統合サービスクラス"""
    
    def __init__(self, api_key: str = None, database_id: str = None):
        self.api_key = api_key or settings.notion_api_key
        self.database_id = database_id or settings.notion_database_id
        self.base_url = "https://api.notion.com/v1"
        
        if not self.api_key:
            raise ValueError("Notion API key is required. Set NOTION_API_KEY in environment variables.")
        if not self.database_id:
            raise ValueError("Notion database ID is required. Set NOTION_DATABASE_ID in environment variables.")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
    def create_llm_session_page(self, session_data: Dict[str, Any]) -> Optional[str]:
        """LLMセッションページを作成"""
        try:
            # Notionページのプロパティを構築
            properties = {
                "名前": {
                    "title": [
                        {
                            "text": {
                                "content": f"Session: {session_data.get('session_id', 'Unknown')[:8]}... ({session_data.get('article_uuid', 'Unknown')[:8]}...)"
                            }
                        }
                    ]
                }
            }
            
            # ページの内容を構築（Notionのブロック形式）
            children = self._build_session_content_blocks(session_data)
            
            payload = {
                "parent": {"database_id": self.database_id},
                "properties": properties,
                "children": children
            }
            
            response = requests.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                page_data = response.json()
                page_id = page_data.get("id")
                logger.info(f"LLMセッションページ作成成功: {page_id}")
                print(f"✅ Notionページ作成成功: {page_id}")
                return page_id
            else:
                logger.error(f"ページ作成失敗: {response.status_code} - {response.text}")
                print(f"❌ ページ作成失敗: {response.status_code}")
                print(f"   レスポンス: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"ページ作成エラー: {e}")
            print(f"❌ ページ作成エラー: {e}")
            return None
    
    def _build_session_content_blocks(self, session_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """セッションデータからNotionブロックを構築"""
        blocks = []
        
        # ヘッダー情報
        blocks.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"type": "text", "text": {"content": "📊 LLM セッション概要"}}]
            }
        })
        
        # セッション基本情報
        session_info = f"""
**セッションID:** {session_data.get('session_id', 'N/A')}
**記事UUID:** {session_data.get('article_uuid', 'N/A')}
**ユーザーID:** {session_data.get('user_id', 'N/A')}
**ステータス:** {session_data.get('status', 'N/A')}
**開始日時:** {session_data.get('created_at', 'N/A')}
**完了日時:** {session_data.get('completed_at', 'N/A') or 'N/A'}
**総実行時間:** {session_data.get('total_duration_ms', 0)} ms
"""
        
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": session_info.strip()}}]
            }
        })
        
        # トークン使用量とコスト
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "💰 トークン使用量とコスト"}}]
            }
        })
        
        cost_info = f"""
**総トークン数:** {session_data.get('total_tokens', 0):,}
**入力トークン:** {session_data.get('input_tokens', 0):,}
**出力トークン:** {session_data.get('output_tokens', 0):,}
**キャッシュトークン:** {session_data.get('cache_tokens', 0):,}
**推論トークン:** {session_data.get('reasoning_tokens', 0):,}
**推定コスト:** ${session_data.get('estimated_total_cost', 0):.6f}
"""
        
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": cost_info.strip()}}]
            }
        })
        
        # 初期設定情報
        if session_data.get('initial_input') or session_data.get('seo_keywords'):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "⚙️ 初期設定"}}]
                }
            })
            
            initial_info = f"""
**SEOキーワード:** {', '.join(session_data.get('seo_keywords', []))}
**ターゲット年代:** {session_data.get('target_age_group', 'N/A')}
**画像モード:** {'有効' if session_data.get('image_mode_enabled') else '無効'}
**テーマ生成数:** {session_data.get('generation_theme_count', 'N/A')}
"""
            
            if session_data.get('company_info'):
                company_info = session_data['company_info']
                initial_info += f"""
**会社名:** {company_info.get('company_name', 'N/A')}
**会社説明:** {company_info.get('company_description', 'N/A')[:100]}...
"""
            
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": initial_info.strip()}}]
                }
            })
        
        # LLM呼び出し一覧
        if session_data.get('llm_calls'):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "🤖 LLM呼び出し詳細"}}]
                }
            })
            
            for i, llm_call in enumerate(session_data['llm_calls'][:10]):  # 最大10件表示
                blocks.extend(self._build_llm_call_blocks(llm_call, i + 1))
        
        # パフォーマンス統計
        if session_data.get('performance_metrics'):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "📈 パフォーマンス統計"}}]
                }
            })
            
            metrics = session_data['performance_metrics']
            perf_info = f"""
**総実行数:** {metrics.get('total_executions', 0)}
**総LLM呼び出し数:** {metrics.get('total_llm_calls', 0)}
**総ツール呼び出し数:** {metrics.get('total_tool_calls', 0)}
**平均実行時間:** {metrics.get('avg_execution_duration_ms', 0):.2f} ms
"""
            
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": perf_info.strip()}}]
                }
            })
        
        return blocks
    
    def _build_llm_call_blocks(self, llm_call: Dict[str, Any], call_number: int) -> List[Dict[str, Any]]:
        """LLM呼び出し詳細のブロックを構築"""
        blocks = []
        
        # LLM呼び出しヘッダー
        blocks.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": f"#{call_number} {llm_call.get('model_name', 'Unknown')} - {llm_call.get('called_at', 'N/A')}"}}]
            }
        })
        
        # 基本情報
        basic_info = f"""
**エージェント:** {llm_call.get('agent_name', 'N/A')}
**モデル:** {llm_call.get('model_name', 'N/A')}
**トークン:** {llm_call.get('prompt_tokens', 0)} → {llm_call.get('completion_tokens', 0)} (計: {llm_call.get('total_tokens', 0)})
**コスト:** ${llm_call.get('estimated_cost_usd', 0):.6f}
**実行時間:** {llm_call.get('response_time_ms', 0)} ms
"""
        
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": basic_info.strip()}}]
            }
        })
        
        # システムプロンプト
        system_prompt = llm_call.get('system_prompt', '')
        if system_prompt:
            blocks.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": f"🔧 システムプロンプト ({len(system_prompt)} 文字)"}}],
                    "children": [
                        {
                            "object": "block",
                            "type": "code",
                            "code": {
                                "caption": [],
                                "rich_text": [{"type": "text", "text": {"content": system_prompt[:2000]}}],
                                "language": "plain text"
                            }
                        }
                    ]
                }
            })
        
        # ユーザー入力
        user_prompt = llm_call.get('user_prompt', '')
        if user_prompt:
            blocks.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": f"👤 ユーザー入力 ({len(user_prompt)} 文字)"}}],
                    "children": [
                        {
                            "object": "block",
                            "type": "code",
                            "code": {
                                "caption": [],
                                "rich_text": [{"type": "text", "text": {"content": user_prompt[:2000]}}],
                                "language": "plain text"
                            }
                        }
                    ]
                }
            })
        
        # アシスタント出力
        response_content = llm_call.get('response_content', '')
        if response_content:
            blocks.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": f"🤖 アシスタント出力 ({len(response_content)} 文字)"}}],
                    "children": [
                        {
                            "object": "block",
                            "type": "code",
                            "code": {
                                "caption": [],
                                "rich_text": [{"type": "text", "text": {"content": response_content[:2000]}}],
                                "language": "json"
                            }
                        }
                    ]
                }
            })
        
        # 区切り線
        blocks.append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })
        
        return blocks
    
    def test_connection(self) -> bool:
        """Notion API接続テスト"""
        try:
            response = requests.get(
                f"{self.base_url}/users/me",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                print(f"✅ Notion API接続成功")
                print(f"   ユーザー: {user_data.get('name', 'Unknown')}")
                print(f"   ワークスペース: {user_data.get('bot', {}).get('workspace_name', 'Unknown')}")
                return True
            else:
                print(f"❌ Notion API接続失敗: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Notion API接続エラー: {e}")
            return False