# Notion統合システム セットアップガイド

## 概要

SupabaseのLLMログデータをNotionデータベースと自動同期するシステムのセットアップ手順です。

## 必要な環境変数

`.env` ファイルに以下の設定を追加してください：

```bash
# Notion API設定
NOTION_API_KEY=your_notion_integration_token
NOTION_DATABASE_ID=your_database_id
```

## セットアップ手順

### 1. Notion統合の作成

1. [Notion Developers](https://www.notion.so/my-integrations) にアクセス
2. 「New integration」をクリック
3. 統合名を入力（例：「LLM Log Sync」）
4. 適切なワークスペースを選択
5. 「Submit」をクリック
6. 「Internal Integration Token」をコピーして `NOTION_API_KEY` に設定

### 2. Notionデータベースの準備

1. Notionで新しいデータベースを作成
2. データベースの共有設定で、作成した統合を追加
3. データベースURLから Database ID を抽出
   - URL例: `https://www.notion.so/123456789abcdef?v=...`
   - Database ID: `12345678-9abc-def0-1234-56789abcdef0` （ハイフン付き形式）

### 3. 環境変数の設定

```bash
# .env ファイルに追加
NOTION_API_KEY=ntn_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_DATABASE_ID=12345678-9abc-def0-1234-56789abcdef0
```

## データベーススキーマ

Notionデータベースには最低限以下のプロパティが必要です：

- **名前** (Title): セッションの識別子

システムが自動的に以下の情報をページコンテンツとして追加します：

- 📊 セッション概要（ID、ステータス、実行時間）
- 💰 トークン使用量とコスト詳細
- ⚙️ 初期設定（SEOキーワード、ターゲット年代等）
- 🤖 LLM呼び出し詳細（システムプロンプト、ユーザー入力、出力）
- 📈 パフォーマンス統計

## 使用方法

### 自動同期

記事生成が完了すると自動的にNotionに同期されます。

### 手動同期

```python
from services.notion_sync_service import NotionSyncService

sync_service = NotionSyncService()

# 特定セッションを同期
sync_service.sync_session_to_notion("session_id_here")

# 最新24時間のセッションを一括同期
sync_service.sync_recent_sessions(hours=24)
```

### API経由での同期

```bash
# 最新セッションを同期
curl -X POST "http://localhost:8000/notion/sync" \
  -H "Content-Type: application/json" \
  -d '{"hours": 24}'

# 特定セッションを同期
curl -X POST "http://localhost:8000/notion/sync" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "your-session-id"}'

# 接続テスト
curl -X GET "http://localhost:8000/notion/test"
```

## テスト

```bash
# 同期システムのテスト
python test_notion_sync.py
```

## トラブルシューティング

### よくあるエラー

1. **`Notion API key is required`**
   - `.env` ファイルに `NOTION_API_KEY` が設定されているか確認

2. **`Notion database ID is required`**
   - `.env` ファイルに `NOTION_DATABASE_ID` が設定されているか確認

3. **`status: 401` (Unauthorized)**
   - NotionのAPIキーが正しいか確認
   - 統合がデータベースに追加されているか確認

4. **`status: 404` (Not Found)**
   - Database IDが正しいか確認
   - データベースが存在し、アクセス権限があるか確認

### デバッグ

ログレベルを上げてデバッグ情報を表示：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## セキュリティ

- APIキーとDatabase IDは `.env` ファイルで管理
- 本番環境では環境変数として設定
- `.env` ファイルは `.gitignore` に追加してコミットしない

## 制限事項

- Notion APIの制限: 1分間に10リクエスト（通常使用では問題なし）
- ページサイズ制限: 1ページあたり2000文字制限のためプロンプト/レスポンスは切り詰められる
- 同期は一方向（Supabase → Notion のみ）