# バックエンドにおけるSupabaseクライアントの設定仕様

## 概要

このドキュメントでは、Marketing Automation APIバックエンドにおけるSupabaseクライアントの設定と管理について詳細に解説します。バックエンドは管理者権限を持つサービスロールキーを使用してSupabaseに接続し、Row Level Security（RLS）をバイパスした完全なデータアクセスを実現しています。

## Supabaseクライアント設定の概要

### アーキテクチャ構成
```
バックエンド FastAPI Application
    ↓ Service Role Key
Supabase Database (PostgreSQL)
    ↓ RLS Bypass
Full Database Access
```

### 権限レベル比較
| クライアント種別 | 権限レベル | RLS適用 | 用途 |
|-----------------|-----------|---------|------|
| Anonymous Key | 読み取りのみ | 適用 | 公開データアクセス |
| User JWT | ユーザー権限 | 適用 | フロントエンド |
| Service Role Key | 管理者権限 | バイパス | バックエンドAPI |

## Supabaseクライアント実装詳細

### モジュール構成
**ファイルパス**: `/home/als0028/study/shintairiku/marketing-automation/backend/app/common/database.py`

```python
"""
Supabase client for backend operations
"""
from supabase import create_client, Client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
```

### 主要コンポーネント

#### 1. クライアント作成関数
```python
def create_supabase_client() -> Client:
    """Create a Supabase client with service role key for backend operations"""
    try:
        supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
        return supabase_client
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        raise
```

**機能仕様**:
- **目的**: サービスロールキーによる管理者権限クライアント作成
- **パラメータ**: 
  - `supabase_url`: SupabaseプロジェクトURL
  - `supabase_service_role_key`: サービスロールキー
- **戻り値**: 設定済みSupabaseクライアントインスタンス
- **例外処理**: 作成失敗時のログ出力と例外再発生

#### 2. グローバルクライアントインスタンス
```python
# Global client instance
supabase: Client = create_supabase_client()
```

**設計思想**:
- **シングルトンパターン**: アプリケーション全体で単一のクライアントインスタンス
- **初期化タイミング**: モジュールインポート時に自動初期化
- **再利用性**: 全てのドメインで共通利用可能
- **効率性**: 接続プールの効率的な活用

#### 3. 接続テスト機能
```python
def test_connection() -> bool:
    """Test Supabase connection"""
    try:
        # Simple test query to verify connection
        supabase.from_("company_info").select("id").limit(1).execute()
        logger.info("Supabase connection successful")
        return True
    except Exception as e:
        logger.error(f"Supabase connection test failed: {e}")
        return False
```

**テスト仕様**:
- **テスト方法**: `company_info`テーブルへの軽量クエリ実行
- **クエリ内容**: `SELECT id FROM company_info LIMIT 1`
- **成功判定**: 例外が発生しないこと
- **ログ出力**: 成功・失敗の両方をログに記録

## 設定管理システム

### 環境変数による設定
```python
from app.core.config import settings

# 設定値の取得
SUPABASE_URL = settings.supabase_url
SUPABASE_SERVICE_ROLE_KEY = settings.supabase_service_role_key
```

### 必要な環境変数
```bash
# Supabase接続設定
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

**環境変数の説明**:
- **SUPABASE_URL**: SupabaseプロジェクトのREST API URL
- **SUPABASE_SERVICE_ROLE_KEY**: サービスロールキー（管理者権限）

### 設定クラスの実装例
```python
# app/core/config.py での設定例
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    supabase_url: str
    supabase_service_role_key: str
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

## サービスロールキーの特権と責任

### 管理者権限の範囲

#### 1. RLS（Row Level Security）バイパス
```sql
-- RLSポリシーが設定されたテーブル例
CREATE POLICY "Users can only view their own articles" ON articles
FOR SELECT USING (user_id = auth.uid()::text);

-- サービスロールキーはこのポリシーをバイパス
-- 全てのユーザーの記事にアクセス可能
```

#### 2. 全テーブルアクセス権限
```python
# 任意のユーザーのデータを操作可能
supabase.table("articles").select("*").eq("user_id", "any_user_id").execute()
supabase.table("company_info").update({"name": "Updated"}).eq("id", "any_id").execute()
supabase.table("organizations").delete().eq("id", "any_org_id").execute()
```

#### 3. システムテーブルアクセス
```python
# システムメタデータへのアクセス
supabase.table("auth.users").select("*").execute()  # 全ユーザー情報
supabase.rpc("database_functions").execute()         # データベース関数実行
```

### セキュリティ責任

#### アクセス制御の実装
```python
# バックエンドでのユーザーデータアクセス制御例
async def get_user_articles(user_id: str):
    """特定ユーザーの記事のみを取得"""
    result = supabase.table("articles").select("*").eq("user_id", user_id).execute()
    return result.data

async def ensure_user_access(resource_user_id: str, current_user_id: str):
    """ユーザーのリソースアクセス権限確認"""
    if resource_user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied")
```

## データベース操作パターン

### 基本CRUD操作

#### 1. データ取得（Select）
```python
# 単一レコード取得
result = supabase.table("articles").select("*").eq("id", article_id).execute()
article = result.data[0] if result.data else None

# 条件付き複数レコード取得
result = supabase.table("articles").select("*").eq("user_id", user_id).limit(20).execute()
articles = result.data

# 結合クエリ
result = supabase.table("articles").select("""
    *,
    company_info(name, business_description)
""").eq("user_id", user_id).execute()
```

#### 2. データ挿入（Insert）
```python
# 単一レコード挿入
insert_data = {
    "id": str(uuid.uuid4()),
    "user_id": user_id,
    "title": "新しい記事",
    "content": "記事内容",
    "status": "draft"
}
result = supabase.table("articles").insert(insert_data).execute()

# 複数レコード一括挿入
batch_data = [
    {"user_id": user_id, "title": "記事1"},
    {"user_id": user_id, "title": "記事2"},
]
result = supabase.table("articles").insert(batch_data).execute()
```

#### 3. データ更新（Update）
```python
# 条件付き更新
result = supabase.table("articles").update({
    "title": "更新されたタイトル",
    "updated_at": datetime.now().isoformat()
}).eq("id", article_id).execute()

# 複数条件での更新
result = supabase.table("articles").update({
    "status": "published"
}).eq("user_id", user_id).eq("status", "draft").execute()
```

#### 4. データ削除（Delete）
```python
# 単一レコード削除
result = supabase.table("articles").delete().eq("id", article_id).execute()

# 条件付き削除
result = supabase.table("articles").delete().eq("user_id", user_id).eq("status", "draft").execute()
```

### 高度なクエリパターン

#### 1. フィルタリングとソート
```python
result = supabase.table("articles").select("*").filter(
    "created_at", "gte", "2025-01-01"
).order("created_at", desc=True).limit(10).execute()
```

#### 2. 全文検索
```python
result = supabase.table("articles").select("*").text_search(
    "title", "マーケティング"
).execute()
```

#### 3. JSON列の操作
```python
# JSONBフィールドのクエリ
result = supabase.table("generated_articles_state").select("*").filter(
    "article_context->current_step", "eq", "writing_sections"
).execute()
```

## リアルタイム機能との統合

### Realtimeチャンネル設定
```python
# リアルタイム購読の設定例
def setup_realtime_subscription(table_name: str, user_id: str):
    channel = supabase.channel(f"{table_name}_{user_id}")
    
    channel.on("postgres_changes", {
        "event": "*",
        "schema": "public",
        "table": table_name,
        "filter": f"user_id=eq.{user_id}"
    }, handle_realtime_event)
    
    channel.subscribe()
    return channel
```

### イベント処理
```python
def handle_realtime_event(payload):
    """リアルタイムイベントの処理"""
    event_type = payload.get("eventType")
    table = payload.get("table")
    record = payload.get("new", payload.get("old"))
    
    logger.info(f"Realtime event: {event_type} on {table}")
    
    # イベントに応じた後続処理
    if event_type == "INSERT" and table == "process_events":
        notify_frontend(record)
```

## エラーハンドリングとログ

### 例外処理パターン
```python
async def safe_database_operation(operation_func):
    """データベース操作の安全な実行"""
    try:
        result = operation_func()
        if not result.data:
            logger.warning("No data returned from database operation")
            return None
        return result.data
    except Exception as e:
        logger.error(f"Database operation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        )
```

### ログレベル設定
```python
# ログ設定例
logger = logging.getLogger(__name__)

# 成功ログ
logger.info("Supabase connection successful")
logger.debug(f"Query executed: {query}")

# 警告ログ
logger.warning("No data returned from query")

# エラーログ
logger.error(f"Supabase connection test failed: {e}")
logger.critical("Supabase client initialization failed")
```

## パフォーマンス最適化

### 接続プール管理
```python
# 接続プール設定（supabase-py内部）
client_options = {
    "connection_timeout": 30,
    "read_timeout": 60,
    "pool_connections": 10,
    "pool_maxsize": 20
}
```

### クエリ最適化
```python
# インデックスを活用したクエリ
result = supabase.table("articles").select("id, title, created_at").eq(
    "user_id", user_id
).order("created_at", desc=True).limit(20).execute()

# 不要なカラムの除外
result = supabase.table("articles").select("id, title").execute()
```

### バッチ処理
```python
# 大量データの効率的な処理
async def process_articles_in_batches(user_id: str, batch_size: int = 100):
    offset = 0
    while True:
        result = supabase.table("articles").select("*").eq(
            "user_id", user_id
        ).range(offset, offset + batch_size - 1).execute()
        
        if not result.data:
            break
            
        # バッチ処理
        await process_article_batch(result.data)
        offset += batch_size
```

## 監視とヘルスチェック

### 定期的な接続確認
```python
from fastapi import BackgroundTasks

async def periodic_health_check():
    """定期的なデータベース接続確認"""
    is_healthy = test_connection()
    
    if not is_healthy:
        logger.critical("Supabase connection health check failed")
        # アラート送信、再接続試行などの処理
        
    return is_healthy

# FastAPIエンドポイント
@app.get("/health/database")
async def database_health():
    is_healthy = test_connection()
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "timestamp": datetime.now().isoformat()
    }
```

### メトリクス収集
```python
import time
from functools import wraps

def measure_query_time(func):
    """クエリ実行時間の測定"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        
        logger.info(f"Query executed in {execution_time:.2f}s")
        return result
    return wrapper

@measure_query_time
def get_articles_with_metrics(user_id: str):
    return supabase.table("articles").select("*").eq("user_id", user_id).execute()
```

## セキュリティベストプラクティス

### 入力値検証
```python
import re
from typing import Optional

def validate_user_id(user_id: str) -> bool:
    """ユーザーIDの形式検証"""
    # Clerk ユーザーIDの形式: user_xxxxxxxxxxxxxxxxxxxxx
    pattern = r'^user_[a-zA-Z0-9]{24}$'
    return bool(re.match(pattern, user_id))

def sanitize_input(value: str) -> str:
    """SQL インジェクション対策"""
    # supabase-pyが自動的にエスケープするが、追加の検証
    if not value or len(value) > 1000:
        raise ValueError("Invalid input value")
    return value.strip()
```

### データアクセス監査
```python
async def audit_database_access(user_id: str, table: str, operation: str, resource_id: Optional[str] = None):
    """データアクセスの監査ログ"""
    audit_log = {
        "user_id": user_id,
        "table": table,
        "operation": operation,
        "resource_id": resource_id,
        "timestamp": datetime.now().isoformat(),
        "ip_address": request.client.host  # FastAPI request context
    }
    
    # 監査ログテーブルへの記録
    supabase.table("audit_logs").insert(audit_log).execute()
```

## トラブルシューティング

### 一般的な問題と解決策

#### 1. 接続エラー
**症状**: `Failed to create Supabase client`
```python
# 診断コード
def diagnose_connection_issue():
    try:
        # 環境変数の確認
        print(f"SUPABASE_URL: {settings.supabase_url}")
        print(f"Service key exists: {bool(settings.supabase_service_role_key)}")
        
        # ネットワーク接続の確認
        import requests
        response = requests.get(settings.supabase_url + "/rest/v1/", timeout=10)
        print(f"API endpoint accessible: {response.status_code == 200}")
        
    except Exception as e:
        print(f"Diagnosis failed: {e}")
```

#### 2. 権限エラー
**症状**: RLSポリシーによるアクセス拒否
```python
# サービスロールキーの確認
def verify_service_role():
    try:
        # システムテーブルへのアクセステスト
        result = supabase.table("auth.users").select("id").limit(1).execute()
        return True
    except Exception as e:
        logger.error(f"Service role verification failed: {e}")
        return False
```

#### 3. クエリエラー
**症状**: 予期しないクエリ結果
```python
# デバッグ用クエリログ
def debug_query(table: str, filters: dict):
    logger.debug(f"Executing query on {table} with filters: {filters}")
    
    try:
        query = supabase.table(table).select("*")
        for key, value in filters.items():
            query = query.eq(key, value)
        
        result = query.execute()
        logger.debug(f"Query returned {len(result.data)} records")
        return result
        
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise
```

## まとめ

バックエンドのSupabaseクライアント設定は、サービスロールキーによる管理者権限を活用して、セキュアかつ効率的なデータベースアクセスを実現しています。

### 主要な特徴
- **管理者権限**: RLSバイパスによる完全なデータアクセス
- **シングルトン設計**: アプリケーション全体での統一クライアント
- **堅牢なエラー処理**: 包括的な例外処理とログ出力
- **パフォーマンス最適化**: 接続プール管理とクエリ最適化
- **セキュリティ**: 適切なアクセス制御と監査機能

### セキュリティ配慮
- **環境変数管理**: 機密情報の安全な管理
- **入力値検証**: SQLインジェクション対策
- **監査ログ**: データアクセスの追跡可能性
- **権限分離**: バックエンドでの適切なアクセス制御

このSupabaseクライアント設定により、スケーラブルで安全なデータベースアクセス基盤が提供され、マーケティング自動化プラットフォームの信頼性の高い動作を支えています。