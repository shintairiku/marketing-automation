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
- `ask_user_questions`: input_types に `image_upload` 対応
- `WebSearchTool`: 最新情報検索用の組み込みツール
- WordPress参照ツール: `compact=True` でトークン最適化 (短キー形式)

## Prompt Caching 最適化
- `prompt_cache_key`: グローバルスコープ (`bai:v1:<model>:g:<hash>`)
- `prompt_cache_retention='24h'`
- gpt-5.2 は `prompt_cache_key` 必須 (自動キャッシュされない)
- キー上限64文字 → SHA-256ハッシュ方式

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
