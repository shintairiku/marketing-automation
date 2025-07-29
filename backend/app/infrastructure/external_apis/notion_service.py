# -*- coding: utf-8 -*-
"""
Notion API統合サービス
SupabaseのLLMログデータをNotionデータベースと同期する
"""
import logging
from typing import Dict, Any, List, Optional
import requests
import json

from app.core.config import settings

logger = logging.getLogger(__name__)

class NotionService:
    """Notion API統合サービスクラス"""
    
    def __init__(self, api_key: Optional[str] = None, database_id: Optional[str] = None):
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
        """LLMセッションページを作成し、コンテンツをチャンクで追加"""
        page_id = None
        try:
            # 記事タイトルを取得し、ない場合はフォールバック
            article_title = session_data.get('article_title')
            if article_title:
                page_title = article_title
            else:
                # フォールバック: SEOキーワードがある場合はそれを使用
                seo_keywords = session_data.get('seo_keywords', [])
                if seo_keywords:
                    page_title = f"記事生成: {', '.join(seo_keywords[:3])}..."
                else:
                    page_title = f"記事生成: {session_data.get('session_id', 'Unknown')[:8]}..."
            
            # Notionページのプロパティを構築
            properties = {
                "名前": {
                    "title": [
                        {
                            "text": {
                                "content": page_title
                            }
                        }
                    ]
                }
            }
            
            # 開始日時プロパティを追加
            if session_data.get('created_at'):
                properties["開始日時"] = {  # type: ignore[dict-item]
                    "date": {
                        "start": session_data['created_at']
                    }
                }
            
            # SEOキーワードプロパティを追加
            seo_keywords = session_data.get('seo_keywords', [])
            if seo_keywords:
                properties["SEOキーワード"] = {
                    "multi_select": [
                        {"name": keyword} for keyword in seo_keywords
                    ]
                }
            
            # 1. プロパティのみでページを作成
            page_payload = {
                "parent": {"database_id": self.database_id},
                "properties": properties,
            }
            
            response = requests.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=page_payload,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"ページ作成失敗: {response.status_code} - {response.text}")
                print(f"❌ ページ作成失敗: {response.status_code}")
                print(f"   レスポンス: {response.text}")
                return None
            
            page_data = response.json()
            page_id = page_data.get("id")
            logger.info(f"LLMセッションページ作成成功: {page_id}")
            print(f"✅ Notionページ作成成功: {page_id}")
            
            # 2. ページの中身（ブロック）を構築
            children = self._build_session_content_blocks(session_data)
            
            # 3. ブロックをチャンクで追加
            if children:
                print(f"   ... {len(children)}件のブロックを追加中...")
                self.append_blocks_to_page(page_id, children)
                print("   ✅ ブロックの追加が完了しました")
            
            return page_id
                
        except Exception as e:
            logger.error(f"ページ処理エラー (ID: {page_id}): {e}")
            print(f"❌ ページ処理エラー (ID: {page_id}): {e}")
            return None
    
    def append_blocks_to_page(self, page_id: str, blocks: List[Dict[str, Any]]):
        """ページにブロックを追加（100件ごとのチャンク処理）"""
        for i in range(0, len(blocks), 100):
            chunk = blocks[i:i + 100]
            payload = {"children": chunk}
            
            try:
                response = requests.patch(
                    f"{self.base_url}/blocks/{page_id}/children",
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    logger.info(f"ページ {page_id} に {len(chunk)} ブロックを追加成功")
                else:
                    logger.error(f"ブロック追加失敗: {response.status_code} - {response.text}")
                    print(f"❌ ブロック追加失敗: {response.status_code}")
                    print(f"   レスポンス: {response.text}")
                    response.raise_for_status()

            except requests.exceptions.RequestException as e:
                logger.error(f"ブロック追加リクエストエラー: {e}")
                print(f"❌ ブロック追加リクエストエラー: {e}")
                raise

    def _build_session_content_blocks(self, session_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """セッションデータからNotionブロックを構築"""
        blocks: List[Dict[str, Any]] = []
        
        # ヘッダー情報
        blocks.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"type": "text", "text": {"content": "📊 LLM セッション概要"}}]
            }
        })
        
        # セッション基本情報
        session_info_blocks = [
            f"セッションID: {session_data.get('session_id', 'N/A')}",
            f"記事UUID: {session_data.get('article_uuid', 'N/A')}",
            f"ユーザーID: {session_data.get('user_id', 'N/A')}",
            f"ステータス: {session_data.get('status', 'N/A')}",
            f"開始日時: {session_data.get('created_at', 'N/A')}",
            f"完了日時: {session_data.get('completed_at', 'N/A') or 'N/A'}",
            f"総実行時間: {session_data.get('total_duration_ms', 0)} ms"
        ]
        
        for info_line in session_info_blocks:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": self._format_text_with_bold(info_line)
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
        
        cost_info_blocks = [
            f"総トークン数: {session_data.get('total_tokens', 0):,}",
            f"入力トークン: {session_data.get('input_tokens', 0):,}",
            f"出力トークン: {session_data.get('output_tokens', 0):,}",
            f"キャッシュトークン: {session_data.get('cache_tokens', 0):,}",
            f"推論トークン: {session_data.get('reasoning_tokens', 0):,}",
            f"推定コスト: ${session_data.get('estimated_total_cost', 0):.6f}"
        ]
        
        for cost_line in cost_info_blocks:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": self._format_text_with_bold(cost_line)
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
            
            initial_info_blocks = [
                f"SEOキーワード: {', '.join(session_data.get('seo_keywords', []))}",
                f"ターゲット年代: {session_data.get('target_age_group', 'N/A')}",
                f"画像モード: {'有効' if session_data.get('image_mode_enabled') else '無効'}",
                f"テーマ生成数: {session_data.get('generation_theme_count', 'N/A')}"
            ]
            
            if session_data.get('company_info'):
                company_info = session_data['company_info']
                initial_info_blocks.extend([
                    f"会社名: {company_info.get('company_name', 'N/A')}",
                    f"会社説明: {company_info.get('company_description', 'N/A')[:100]}..."
                ])
            
            for info_line in initial_info_blocks:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": self._format_text_with_bold(info_line)
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
            
            for i, llm_call in enumerate(session_data['llm_calls']):
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
            perf_info_blocks = [
                f"総実行数: {metrics.get('total_executions', 0)}",
                f"総LLM呼び出し数: {metrics.get('total_llm_calls', 0)}",
                f"総ツール呼び出し数: {metrics.get('total_tool_calls', 0)}",
                f"平均実行時間: {metrics.get('avg_execution_duration_ms', 0):.2f} ms"
            ]
            
            for perf_line in perf_info_blocks:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": self._format_text_with_bold(perf_line)
                    }
                })
        
        
        return blocks
    
    def _get_llm_call_title(self, llm_call: Dict[str, Any], call_number: int) -> str:
        """LLM呼び出しの分かりやすいタイトルを生成"""
        # エージェント名から処理内容を推測
        agent_name = llm_call.get('agent_name', '').lower()
        
        # 具体的なエージェント名でマッピング
        if 'serpkeywordanalysisagent' in agent_name:
            return f"#{call_number} SERP分析"
        elif 'personageneratoragent' in agent_name:
            return f"#{call_number} ペルソナ生成"
        elif 'themeagent' in agent_name:
            return f"#{call_number} テーマ生成"
        elif 'researchplanneragent' in agent_name:
            return f"#{call_number} リサーチ計画"
        elif 'researcheragent' in agent_name:
            return f"#{call_number} リサーチ実行"
        elif 'researchsynthesizeragent' in agent_name:
            return f"#{call_number} リサーチ要約"
        elif 'outlineagent' in agent_name:
            return f"#{call_number} アウトライン生成"
        elif 'editoragent' in agent_name:
            return f"#{call_number} 編集・校正"
        # 従来の部分一致マッピング（フォールバック）
        elif 'serp' in agent_name or 'keyword' in agent_name:
            return f"#{call_number} SERP分析"
        elif 'persona' in agent_name:
            return f"#{call_number} ペルソナ生成"
        elif 'theme' in agent_name:
            return f"#{call_number} テーマ生成"
        elif 'research' in agent_name:
            if 'planner' in agent_name:
                return f"#{call_number} リサーチ計画"
            elif 'synthesizer' in agent_name:
                return f"#{call_number} リサーチ要約"
            else:
                return f"#{call_number} リサーチ実行"
        elif 'outline' in agent_name:
            return f"#{call_number} アウトライン生成"
        elif 'editor' in agent_name:
            return f"#{call_number} 編集・校正"
        else:
            # フォールバック: モデル名を使用
            model_name = llm_call.get('model_name', 'Unknown')
            return f"#{call_number} {model_name}処理"
    
    def _format_text_with_bold(self, text: str) -> List[Dict[str, Any]]:
        """テキストのコロン前を太字にフォーマット"""
        if ":" in text:
            parts = text.split(":", 1)
            return [
                {
                    "type": "text",
                    "text": {"content": parts[0]},
                    "annotations": {"bold": True}
                },
                {
                    "type": "text",
                    "text": {"content": ": " + parts[1]}
                }
            ]
        else:
            return [{"type": "text", "text": {"content": text}}]
    
    def _build_llm_call_blocks(self, llm_call: Dict[str, Any], call_number: int) -> List[Dict[str, Any]]:
        """LLM呼び出し詳細のブロックを構築"""
        blocks: List[Dict[str, Any]] = []
        
        # LLM呼び出しヘッダー
        blocks.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": self._get_llm_call_title(llm_call, call_number)}}]
            }
        })
        
        # 基本情報（キャッシュトークン情報を含む）
        basic_info_blocks = [
            f"エージェント: {llm_call.get('agent_name', 'N/A')}",
            f"モデル: {llm_call.get('model_name', 'N/A')}",
            f"トークン: {llm_call.get('prompt_tokens', 0):,} → {llm_call.get('completion_tokens', 0):,} (計: {llm_call.get('total_tokens', 0):,})",
            f"キャッシュトークン: {llm_call.get('cached_tokens', 0):,}",
            f"推論トークン: {llm_call.get('reasoning_tokens', 0):,}",
            f"コスト: ${llm_call.get('estimated_cost_usd', 0):.6f}",
            f"実行時間: {llm_call.get('response_time_ms', 0)} ms"
        ]
        
        for info_line in basic_info_blocks:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": self._format_text_with_bold(info_line)
                }
            })
        
        # システムプロンプト（通常テキストで表示、文字数制限なし）
        system_prompt = llm_call.get('system_prompt', '')
        if system_prompt:
            # システムプロンプトを複数のテキストブロックに分割して表示
            system_blocks = self._split_text_into_blocks(system_prompt)
            blocks.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": f"🔧 システムプロンプト ({len(system_prompt):,} 文字)"}}],
                    "children": system_blocks
                }
            })
        
        # ユーザー入力（通常テキストで表示、文字数制限なし）
        user_prompt = llm_call.get('user_prompt', '')
        if user_prompt:
            user_blocks = self._split_text_into_blocks(user_prompt)
            blocks.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": f"👤 ユーザー入力 ({len(user_prompt):,} 文字)"}}],
                    "children": user_blocks
                }
            })
        
        # アシスタント出力（構造化データを分解して表示）
        response_content = llm_call.get('response_content', '')
        if response_content:
            response_blocks = self._format_response_content(response_content)
            blocks.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": f"🤖 アシスタント出力 ({len(response_content):,} 文字)"}}],
                    "children": response_blocks
                }
            })
        
        # 区切り線
        blocks.append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })
        
        return blocks
    
    def _split_text_into_blocks(self, text: str) -> List[Dict[str, Any]]:
        """長いテキストを複数のパラグラフブロックに分割"""
        blocks: List[Dict[str, Any]] = []
        # Notion APIの制限に合わせて1900文字ごとに分割（安全マージン）
        chunk_size = 1900
        
        if not text:
            return blocks
            
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            # 最後のチャンクが空でないことを確認
            if chunk.strip():
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": chunk}}]
                    }
                })
        
        # 空のブロックリストの場合、デフォルトブロックを追加
        if not blocks:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": "(空のコンテンツ)"}}]
                }
            })
        
        return blocks
    
    def _format_response_content(self, content: str) -> List[Dict[str, Any]]:
        """アシスタント出力をフォーマットして表示"""
        blocks: List[Dict[str, Any]] = []
        
        try:
            # JSONかどうかチェック
            parsed_json = json.loads(content)
            
            # JSONの場合は構造化して表示
            if isinstance(parsed_json, dict):
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "📋 構造化データ"}}]
                    }
                })
                
                for key, value in parsed_json.items():
                    if isinstance(value, (dict, list)):
                        # 複雑な構造の場合は文字列化
                        value_str = json.dumps(value, ensure_ascii=False, indent=2)
                        blocks.append({
                            "object": "block",
                            "type": "toggle",
                            "toggle": {
                                "rich_text": [{"type": "text", "text": {"content": f"🔸 {key}"}}],
                                "children": self._split_text_into_blocks(value_str)
                            }
                        })
                    else:
                        # 単純な値の場合は直接表示（2000文字制限適用）
                        content_text = f"{key}: {value}"
                        if len(content_text) > 2000:
                            content_text = content_text[:1997] + "..."
                        blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": self._format_text_with_bold(content_text)
                            }
                        })
            elif isinstance(parsed_json, list):
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "📋 リスト形式データ"}}]
                    }
                })
                
                for i, item in enumerate(parsed_json):
                    if isinstance(item, (dict, list)):
                        item_str = json.dumps(item, ensure_ascii=False, indent=2)
                        blocks.append({
                            "object": "block",
                            "type": "toggle",
                            "toggle": {
                                "rich_text": [{"type": "text", "text": {"content": f"🔸 項目 {i+1}"}}],
                                "children": self._split_text_into_blocks(item_str)
                            }
                        })
                    else:
                        # 2000文字制限適用
                        content_text = f"{i+1}. {item}"
                        if len(content_text) > 2000:
                            content_text = content_text[:1997] + "..."
                        blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": self._format_text_with_bold(content_text)
                            }
                        })
            else:
                # プリミティブ型の場合は通常のテキストとして表示
                blocks.extend(self._split_text_into_blocks(str(parsed_json)))
                
        except (json.JSONDecodeError, TypeError):
            # JSONでない場合は通常のテキストとして表示
            blocks.extend(self._split_text_into_blocks(content))
        
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
                print("✅ Notion API接続成功")
                print(f"   ユーザー: {user_data.get('name', 'Unknown')}")
                print(f"   ワークスペース: {user_data.get('bot', {}).get('workspace_name', 'Unknown')}")
                return True
            else:
                print(f"❌ Notion API接続失敗: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Notion API接続エラー: {e}")
            return False