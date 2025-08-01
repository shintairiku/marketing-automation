# バックエンドAPIの概要

## 概要

このドキュメントでは、FastAPIで構築されたマーケティングオートメーションAPIの全体像について詳細に解説します。本APIは、SEO記事生成、会社情報管理、スタイルガイド、画像生成などの主要機能を提供し、現代的なWebアプリケーションアーキテクチャに基づいて設計されています。

## プロジェクト基本情報

### アプリケーション詳細
- **名称**: Marketing Automation API
- **説明**: SEO記事生成、組織管理、ワークフロー自動化を含む包括的なマーケティング自動化API
- **バージョン**: 2.0.0
- **フレームワーク**: FastAPI
- **Python最小バージョン**: 3.12以上

### アーキテクチャ概要
```
Marketing Automation API
├── FastAPI Core Application
├── CORS Middleware (クロスオリジンサポート)
├── Static File Serving (画像配信)
├── Modular Domain Architecture (ドメイン駆動設計)
└── Exception Handling (統一エラー処理)
```

## 主要機能ドメイン

### 1. SEO記事生成ドメイン (`/articles`)
- **機能概要**: AI駆動によるSEO記事の自動生成
- **主要機能**:
  - キーワード分析とペルソナ生成
  - テーマ提案とリサーチ計画
  - アウトライン生成と本文執筆
  - 編集・校正の自動化
  - WebSocket風のリアルタイム通信（Supabase Realtime）
- **技術特徴**:
  - OpenAI Agents SDKによるマルチエージェント実行
  - Supabase Realtimeによる非同期プロセス管理
  - バックグラウンドタスクによる長時間処理対応

### 2. 組織管理ドメイン (`/organizations`)
- **機能概要**: マルチテナント対応の組織管理システム
- **主要機能**:
  - 組織の作成・管理・削除
  - ユーザーの組織内権限管理
  - 組織レベルでのリソース管理

### 3. 会社情報管理ドメイン (`/companies`)
- **機能概要**: 記事生成に使用する会社情報の管理
- **主要機能**:
  - 会社基本情報の登録・更新
  - ターゲットペルソナの設定
  - デフォルト会社情報の管理
- **活用場面**: AI記事生成時のコンテキスト情報として利用

### 4. スタイルテンプレート管理ドメイン (`/style-templates`)
- **機能概要**: 記事の文体・スタイルガイドライン管理
- **主要機能**:
  - 文体テンプレートの作成・管理
  - スタイルガイドラインの適用
  - ユーザー固有のスタイル設定

### 5. 画像生成ドメイン (`/images`)
- **機能概要**: AI駆動による記事用画像の自動生成
- **主要機能**:
  - Vertex AI Imagen 4.0による画像生成
  - Google Cloud Storageへの画像保存
  - 記事内画像プレースホルダーの管理
- **技術仕様**:
  - GCP認証による安全な画像生成
  - 自動画像配信とキャッシュ管理

## API基本仕様

### エントリーポイント
```python
# /home/als0028/study/shintairiku/marketing-automation/backend/main.py
app = FastAPI(
    title="Marketing Automation API",
    description="Comprehensive API for marketing automation including SEO article generation, organization management, and workflow automation.",
    version="2.0.0",
    exception_handlers=exception_handlers
)
```

### CORS設定
```python
# 環境変数から許可するオリジンを取得
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
```

**CORS設定の特徴**:
- 環境変数による動的オリジン設定
- 認証情報付きリクエストの許可
- 全HTTPメソッドのサポート
- 柔軟なヘッダー設定

### 静的ファイル配信
```python
# 生成された画像の静的ファイル配信
images_directory = Path(__file__).parent / settings.image_storage_path.lstrip('/')
images_directory.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=str(images_directory.resolve())), name="images")
```

**静的ファイル配信の仕様**:
- **パス**: `/images`
- **用途**: AI生成画像の配信
- **設定**: 自動ディレクトリ作成
- **セキュリティ**: パス解決によるディレクトリトラバーサル対策

## ルーティング構造

### ルーター階層
```python
# /home/als0028/study/shintairiku/marketing-automation/backend/app/api/router.py
api_router = APIRouter()

# 各ドメインルーターの統合
api_router.include_router(seo_article_router, prefix="/articles", tags=["SEO Article"])
api_router.include_router(organization_router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(company_router, prefix="/companies", tags=["Companies"])
api_router.include_router(style_template_router, prefix="/style-templates", tags=["Style Templates"])
api_router.include_router(image_generation_router, prefix="/images", tags=["Image Generation"])
```

### 基本エンドポイント

#### ヘルスチェック機能
```python
@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the SEO Article Generation API (WebSocket)!"}

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "message": "API is running", "version": "2.0.0"}
```

#### CORS対応
```python
@app.options("/{path:path}", tags=["CORS"])
async def options_handler(path: str):
    return {"message": "OK"}
```

## 技術スタック詳細

### コア依存関係
```toml
# pyproject.toml抜粋
dependencies = [
    "fastapi",                    # Web フレームワーク
    "uvicorn[standard]",         # ASGI サーバー
    "openai",                    # OpenAI API クライアント
    "openai-agents",             # OpenAI Agents SDK
    "sse-starlette",             # Server-Sent Events
    "pydantic-settings",         # 設定管理
    "supabase",                  # Supabase クライアント
    "google-cloud-aiplatform",   # Vertex AI
    "google-cloud-storage",      # Cloud Storage
    "pyjwt",                     # JWT認証
    "psycopg2-binary",           # PostgreSQL接続
]
```

### 主要ライブラリの役割

#### AI・機械学習関連
- **OpenAI**: GPT-4を用いた記事生成
- **OpenAI Agents**: マルチエージェントワークフロー実行
- **Google Cloud AI Platform**: Vertex AI経由の画像生成
- **Google Generative AI**: Gemini API利用

#### データベース・ストレージ
- **Supabase**: メインデータベースとリアルタイム通信
- **PostgreSQL**: リレーショナルデータストレージ
- **Google Cloud Storage**: 生成画像の保存

#### 認証・セキュリティ
- **PyJWT**: Clerk JWTトークンの検証
- **Google Auth**: GCP認証管理

#### 開発・運用支援
- **Rich**: 美しいコンソール出力
- **Ruff**: Python コードフォーマッター
- **Griffe**: 動的なPythonオブジェクト分析

## 設定管理

### 環境変数設定
APIは以下の主要な環境変数を使用します：

```python
# 必須環境変数
SUPABASE_URL                    # Supabaseプロジェクト URL
SUPABASE_SERVICE_ROLE_KEY       # Supabase サービスロールキー
OPENAI_API_KEY                  # OpenAI API キー
GOOGLE_SERVICE_ACCOUNT_JSON     # GCP サービスアカウント
ALLOWED_ORIGINS                 # CORS許可オリジン
```

### 設定の特徴
- **環境別設定**: 開発/本番環境の自動切り替え
- **セキュリティ**: 機密情報の環境変数管理
- **柔軟性**: デプロイ環境に応じた動的設定

## 例外処理とエラーハンドリング

### 統一エラー処理
```python
# app/core/exceptions.py で定義された例外処理
app = FastAPI(
    exception_handlers=exception_handlers
)
```

**エラー処理の特徴**:
- HTTP ステータスコードの適切な設定
- 詳細なエラーメッセージの提供
- セキュリティを考慮した情報露出制御
- 開発・デバッグ用の詳細ログ出力

## パフォーマンスとスケーラビリティ

### 非同期処理設計
- **FastAPI非同期**: 全エンドポイントでの async/await サポート
- **バックグラウンドタスク**: 長時間処理の非同期実行
- **Supabase Realtime**: WebSocket代替のリアルタイム通信

### 効率性の工夫
- **静的ファイル最適化**: 画像配信の高速化
- **データベース接続プール**: 効率的なリソース管理
- **APIレスポンス最適化**: 適切なHTTPキャッシュヘッダー

## セキュリティ仕様

### 認証・認可
- **Clerk JWT認証**: トークンベース認証
- **RLS (Row Level Security)**: データベースレベルのアクセス制御
- **CORS設定**: 適切なオリジン制限

### データ保護
- **環境変数**: 機密情報の安全な管理
- **HTTPS通信**: 暗号化された通信
- **入力検証**: Pydanticによる厳密な型チェック

## 運用・モニタリング

### ログ管理
- **構造化ログ**: JSON形式でのログ出力
- **レベル別ログ**: DEBUG/INFO/WARNING/ERROR
- **AIエージェントログ**: 詳細な実行トレース

### ヘルスチェック
- **基本ヘルスチェック**: `/health` エンドポイント
- **データベース接続確認**: Supabase接続テスト
- **外部サービス状態確認**: OpenAI/GCP API状態

## 今後の拡張計画

### 計画中の機能
```python
# 将来の拡張例
# api_router.include_router(instagram_router, prefix="/instagram", tags=["Instagram"])
```

**拡張予定領域**:
- Instagram連携機能
- LINE連携機能
- WordPress連携機能
- より高度な分析機能

### アーキテクチャの発展性
- **モジュラー設計**: 新機能の容易な追加
- **ドメイン分離**: 各機能の独立性確保
- **マイクロサービス対応**: 将来的な分散化への対応

## まとめ

Marketing Automation APIは、FastAPIの強力な機能を活用し、AI駆動のコンテンツ生成を中心とした包括的なマーケティング自動化プラットフォームを提供しています。モジュラー設計、適切なセキュリティ設定、効率的な非同期処理により、現代的なWebアプリケーションの要求を満たす高性能で拡張性のあるAPIとして設計されています。

このAPIは単なるRESTful APIを超え、リアルタイム通信、AI エージェントとの統合、クラウドサービスとの連携など、最新の技術トレンドを取り入れた次世代のWebアプリケーション基盤として機能しています。