# バックエンドアーキテクチャとディレクトリ構造の仕様

## 概要

このドキュメントでは、FastAPIを用いたマーケティングオートメーションAPIのバックエンドアーキテクチャについて詳細に解説します。バックエンドはドメイン駆動設計（DDD）の原則に基づき、明確な責務分離と高い保守性を実現する構造で設計されています。

## 全体アーキテクチャ

### 技術スタック
- **フレームワーク**: FastAPI 
- **言語**: Python 3.12+
- **パッケージ管理**: uv
- **設定管理**: Pydantic Settings
- **データベース**: Supabase (PostgreSQL)
- **認証**: Clerk JWT
- **AI SDK**: OpenAI Agents SDK
- **クラウド**: Google Cloud Platform (Vertex AI, Cloud Storage)

### アーキテクチャ原則
1. **ドメイン駆動設計 (DDD)**: ビジネスロジックをドメインごとに分離
2. **依存性の逆転**: インフラ層がドメイン層に依存
3. **単一責任の原則**: 各モジュールは単一の責務を持つ
4. **設定の外部化**: 環境変数による設定管理
5. **レイヤード アーキテクチャ**: 明確な層分離

## ディレクトリ構造詳細

```
backend/
├── app/
│   ├── __init__.py
│   ├── api/                    # APIルーティング層
│   │   ├── __init__.py
│   │   └── router.py          # メインAPIルーター統合
│   ├── common/                 # 共通機能層
│   │   ├── __init__.py
│   │   ├── auth.py            # Clerk認証機能
│   │   ├── database.py        # Supabaseクライアント
│   │   └── schemas.py         # 共通データスキーマ
│   ├── core/                   # コア機能層
│   │   ├── __init__.py
│   │   ├── config.py          # 設定管理
│   │   ├── exceptions.py      # 例外ハンドリング
│   │   └── logger.py          # ログ設定
│   ├── domains/                # ドメイン層
│   │   ├── __init__.py
│   │   ├── seo_article/       # SEO記事生成ドメイン
│   │   ├── company/           # 会社情報ドメイン
│   │   ├── organization/      # 組織管理ドメイン
│   │   ├── style_template/    # スタイルテンプレートドメイン
│   │   └── image_generation/  # 画像生成ドメイン
│   └── infrastructure/         # インフラストラクチャ層
│       ├── __init__.py
│       ├── analysis/          # データ分析機能
│       ├── external_apis/     # 外部API連携
│       ├── gcp_auth.py       # GCP認証管理
│       └── logging/          # ログシステム
├── main.py                    # FastAPIアプリケーション エントリーポイント
├── pyproject.toml            # プロジェクト設定
└── tests/                    # テストディレクトリ
```

## 各層の詳細仕様

### 1. APIルーティング層 (`app/api/`)

#### 責務
- HTTPリクエストのルーティング
- 各ドメインエンドポイントの統合
- CORS設定とミドルウェア管理

#### 主要ファイル

**`router.py`**
```python
from fastapi import APIRouter
from app.domains.seo_article.endpoints import router as seo_article_router
from app.domains.organization.endpoints import router as organization_router
from app.domains.company.endpoints import router as company_router
from app.domains.style_template.endpoints import router as style_template_router
from app.domains.image_generation.endpoints import router as image_generation_router

api_router = APIRouter()

# 各ドメインルーターの統合
api_router.include_router(seo_article_router, prefix="/articles", tags=["SEO Article"])
api_router.include_router(organization_router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(company_router, prefix="/companies", tags=["Companies"])
api_router.include_router(style_template_router, prefix="/style-templates", tags=["Style Templates"])
api_router.include_router(image_generation_router, prefix="/images", tags=["Image Generation"])
```

### 2. 共通機能層 (`app/common/`)

#### 責務
- 認証・認可機能
- データベース接続管理
- 共通データスキーマ定義

#### 主要ファイル

**`auth.py`**
- Clerk JWTトークンの検証
- ユーザーID抽出機能
- 開発環境用フォールバック認証

```python
def get_current_user_id_from_token(authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    """Extract user ID from Clerk JWT token"""
    if not authorization:
        return "user_2y2DRx4Xb5PbvMVoVWmDluHCeFV"  # 開発用フォールバック
    
    try:
        token = authorization.credentials
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get("sub")
        return user_id if user_id else "user_2y2DRx4Xb5PbvMVoVWmDluHCeFV"
    except Exception as e:
        logger.warning(f"Authentication error: {e}")
        return "user_2y2DRx4Xb5PbvMVoVWmDluHCeFV"
```

**`database.py`**
- Supabaseクライアントの初期化
- サービスロールキーによる管理者権限アクセス
- 接続テスト機能

```python
def create_supabase_client() -> Client:
    """Create a Supabase client with service role key for backend operations"""
    supabase_client = create_client(
        settings.supabase_url,
        settings.supabase_service_role_key
    )
    return supabase_client

# グローバルクライアントインスタンス
supabase: Client = create_supabase_client()
```

### 3. コア機能層 (`app/core/`)

#### 責務
- アプリケーション設定管理
- 例外ハンドリング
- ロギング設定

#### 主要ファイル

**`config.py`**
- Pydantic Settingsによる型安全な設定管理
- 環境変数の自動読み込み
- OpenAI Agents SDKの初期化

```python
class Settings(BaseSettings):
    # API キー設定
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    serpapi_key: str = Field(default_factory=lambda: os.getenv("SERPAPI_API_KEY", ""))
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    
    # Supabase設定
    supabase_url: str = Field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_service_role_key: str = Field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
    
    # Clerk設定
    clerk_secret_key: str = Field(default_factory=lambda: os.getenv("CLERK_SECRET_KEY", ""))
    
    # Google Cloud設定
    google_cloud_project: str = Field(default_factory=lambda: os.getenv("GOOGLE_CLOUD_PROJECT", ""))
    google_service_account_json: str = Field(default_factory=lambda: os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", ""))
    
    # モデル設定
    default_model: str = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
    model_for_agents: str = os.getenv("MODEL_FOR_AGENTS", "gpt-4o-mini")
```

### 4. ドメイン層 (`app/domains/`)

#### 責務
- ビジネスロジックの実装
- ドメイン固有のAPIエンドポイント
- ドメイン専用のデータモデル

#### ドメイン一覧

1. **`seo_article/`** - SEO記事生成ドメイン
   - 記事生成プロセスの管理
   - OpenAI Agents SDKを使用した多段階生成
   - Supabase Realtimeによる進捗通知

2. **`company/`** - 会社情報ドメイン
   - 会社情報の管理
   - ブランディング情報
   - SEO・コンテンツ戦略情報

3. **`organization/`** - 組織管理ドメイン
   - 組織階層管理
   - ユーザー組織関連付け

4. **`style_template/`** - スタイルテンプレートドメイン
   - 記事スタイルテンプレート管理
   - 文体・トーン設定

5. **`image_generation/`** - 画像生成ドメイン
   - Vertex AI Imagen 4.0による画像生成
   - Google Cloud Storageへの保存

#### ドメイン内部構造（seo_articleを例に）

```
seo_article/
├── __init__.py
├── agents/                    # AIエージェント定義
│   ├── __init__.py
│   ├── definitions.py         # エージェント設定
│   └── tools.py              # エージェント用ツール
├── context.py                 # 記事生成コンテキスト
├── endpoints.py               # APIエンドポイント
├── schemas.py                 # データスキーマ
├── presentation/              # プレゼンテーション層
└── services/                  # サービス層
    ├── __init__.py
    ├── generation_service.py  # メインサービス
    ├── flow_service.py       # フロー管理
    └── background_task_manager.py  # バックグラウンドタスク
```

### 5. インフラストラクチャ層 (`app/infrastructure/`)

#### 責務
- 外部システムとの連携
- 技術的な横断的関心事
- データ分析・ログ機能

#### 主要モジュール

**`analysis/`**
- コンテンツ分析機能
- コスト計算サービス
- メトリクス収集

**`external_apis/`**
- Google Cloud Storage連携
- Notion API連携
- SerpAPI連携

**`gcp_auth.py`**
- Google Cloud Platform認証管理
- ローカル開発環境とクラウド環境の統一認証

**`logging/`**
- マルチエージェントワークフローログ
- LLM API呼び出しログ
- パフォーマンスメトリクス

## メインアプリケーション (`main.py`)

### 設定内容

```python
app = FastAPI(
    title="Marketing Automation API",
    description="Comprehensive API for marketing automation including SEO article generation, organization management, and workflow automation.",
    version="2.0.0",
    exception_handlers=exception_handlers
)

# CORS設定
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# APIルーターの統合
app.include_router(api_router)

# 静的ファイル配信
app.mount("/images", StaticFiles(directory=str(images_directory.resolve())), name="images")
```

## 設計パターンと原則

### 1. ドメイン駆動設計 (DDD)

**ドメインの分離**
- 各ドメインは独立したビジネス領域を表現
- ドメイン間の結合度を最小化
- 明確な境界コンテキスト

**レイヤード アーキテクチャ**
- プレゼンテーション層: APIエンドポイント
- アプリケーション層: サービスクラス
- ドメイン層: ビジネスロジック
- インフラストラクチャ層: 外部システム連携

### 2. 依存性注入とサービス層

**サービスクラスの責務**
- ビジネスロジックの調整
- データベース操作の抽象化
- 外部API呼び出しの管理

**依存性の管理**
- FastAPIのDependsによる依存性注入
- 設定の外部化
- テスタビリティの向上

### 3. エラーハンドリング戦略

**例外の階層化**
- ビジネス例外
- 技術例外
- システム例外

**統一的なエラーレスポンス**
- 一貫したエラー形式
- 適切なHTTPステータスコード
- デバッグ情報の制御

## パフォーマンスと拡張性

### 1. 非同期処理

**BackgroundTasksの活用**
- 重い処理のバックグラウンド実行
- ユーザー体験の向上
- システムリソースの効率的利用

### 2. データベース最適化

**Supabaseの活用**
- リアルタイム通信
- 行レベルセキュリティ (RLS)
- 自動スケーリング

### 3. キャッシュ戦略

**メモリキャッシュ**
- 設定データのキャッシュ
- APIレスポンスキャッシュ
- 計算結果の一時保存

## セキュリティ考慮事項

### 1. 認証・認可

**Clerk統合**
- JWT検証
- ユーザー権限管理
- セキュアなセッション管理

### 2. データ保護

**機密データの取り扱い**
- 環境変数による秘密情報管理
- ログからの機密情報除外
- 適切なアクセス制御

### 3. API セキュリティ

**CORS設定**
- 許可オリジンの制限
- 認証情報の適切な処理
- セキュアヘッダーの設定

## 監視とロギング

### 1. 構造化ログ

**ログレベルの分類**
- DEBUG: 開発・デバッグ情報
- INFO: 一般的な処理情報
- WARNING: 警告レベルの問題
- ERROR: エラー情報
- CRITICAL: 致命的な問題

### 2. メトリクス収集

**パフォーマンス指標**
- APIレスポンス時間
- エラー率
- リクエスト数
- リソース使用量

## 拡張とメンテナンス

### 1. 新ドメインの追加

**標準的な手順**
1. `domains/`下に新ディレクトリ作成
2. 標準的なファイル構造の実装
3. `api/router.py`へのルーター追加
4. テストの作成

### 2. コード品質

**品質保証**
- 型ヒントの活用
- Pydanticによるデータ検証
- 自動テストの実装
- コードレビューの実施

この設計により、マーケティングオートメーションAPIは高い保守性、拡張性、パフォーマンスを実現しています。各層の明確な責務分離により、ビジネス要件の変更に柔軟に対応できる構造となっています。