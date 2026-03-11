---
paths: backend/app/domains/blog/**/*,frontend/src/app/(tools)/blog/**/*
---

# Blog AI ドメイン知見

## WordPress MCP 連携
- 接続方式: 接続URL貼り付け方式 (プラグイン管理画面で生成)
- `POST /blog/connect/wordpress/url` で登録。code パラメータ自動抽出
- 全ツールは `call_wordpress_mcp_tool()` 経由 (`wordpress_mcp_service.py`)
- プラグインバージョン: v1.2.0 (22ツール)

## 構造化出力 (output_type)
```python
class BlogCompletionOutput(BaseModel):
    post_id: Optional[int] = None
    preview_url: Optional[str] = None
    edit_url: Optional[str] = None
    summary: str
```
- エージェントの最終出力を Pydantic モデルで強制
- `_process_result` がフィールドを直接参照してDB保存

## 画像入力
- 初期入力 (`/blog/new`): multipart/form-data で最大5枚
- 質問フェーズ (`/blog/[processId]`): `image_upload` タイプ
- クライアントサイドで Canvas API リサイズ+JPEG圧縮 (3MB以内)
- バックエンドで Pillow WebP 変換
- OpenAI input_image 型でエージェントに渡す

## エージェントツール設計
- `upload_user_image_to_wordpress`: Base64にエージェントが触れない複合ツール
- `ask_user_questions`: input_types に `image_upload` 対応、`defer_loading=False`（常にロード）
- `WebSearchTool`: 最新情報検索用の組み込みツール
- `ToolSearchTool`: ツール検索有効化（v0.11.0 で SDK 対応）
- WordPress参照ツール: `compact=True` でトークン最適化 (短キー形式)
- **ツール検索 + Namespace**: 22ツールを5ネームスペースに分類、`defer_loading=True` で47%トークン削減
  - `wp_content_read`: 記事取得・分析 (6ツール)
  - `wp_theme_blocks`: テーマ・ブロック情報 (4ツール)
  - `wp_content_write`: 記事作成・更新 (3ツール)
  - `wp_media`: メディア管理 (4ツール)
  - `wp_taxonomy_site`: タクソノミー・サイト情報 (6ツール)

## Prompt Caching 最適化
- `prompt_cache_key`: グローバルスコープ (`bai:v1:<model>:g:<hash>`)
- `prompt_cache_retention='24h'`
- gpt-5.4 は `prompt_cache_key` 必須 (自動キャッシュされない)
- キー上限64文字 → SHA-256ハッシュ方式

## GPT-5.4 コンテキスト管理 (2026-03-05~)
- **サーバーサイドコンパクション**: `context_management=[{"type":"compaction","compact_threshold":400000}]`
  - コンテキストが閾値を超えると自動圧縮。暗号化compaction itemが返される
  - `extra_body` 経由で ModelSettings に注入
- **1Mトークンコンテキスト**: GPT-5.4で対応 (GPT-5.2は400K)
- **長文料金**: 入力272K超で2倍料金（$5.00/M input, $0.50/M cached）
- **allowed_tools**: `tool_choice={"type":"allowed_tools",...}` でフェーズ別ツール制限可能（将来対応予定）
- **ツール検索**: `ToolSearchTool` + `defer_loading=True` + `tool_namespace()` で47%トークン削減。**openai-agents v0.11.0 で SDK 対応済み、Blog AI に実装済み**

## ストリーミングリトライ
- `httpx.RemoteProtocolError`, `APIConnectionError`, `APITimeoutError` を自動リトライ
- 最大3回、指数バックオフ
- リトライ中は `generation_warning` イベントを通知

## Reasoning Summary 日本語翻訳
- gpt-5-nano (`effort="minimal"`, 111トークン/回) で翻訳
- 翻訳失敗時は英語テキストをそのまま使用

## コスト/ログ
- `agent_log_sessions.article_uuid` に `process_id` を保存
- `blog_agent_trace_events` テーブルで詳細トレース (delta/keepalive は保存しない)
- `llm_call_logs.response_data` にキャッシュ設定メタデータを含む

## 利用上限
- 生成開始前に `check_can_generate()` → 429エラー
- 成功時のみ `record_success()` でカウント (Blog AI のみ対象)
- 組織メンバーは `organization_members` テーブルでフォールバック検索
