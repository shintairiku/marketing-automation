# ドメイン駆動設計（DDD）に基づくバックエンドの責務分離

## 概要

このドキュメントでは、Marketing Automation APIにおけるドメイン駆動設計（Domain-Driven Design, DDD）の実装について詳細に解説します。`domains`ディレクトリ内に`seo_article`、`company`、`organization`、`style_template`、`image_generation`といったビジネスドメインごとに関心事を集約し、各ドメインが独自のAPIエンドポイント、サービスロジック、データスキーマを持つことで、責務を明確に分離する設計を採用しています。

## ドメイン駆動設計の概要

### DDDの基本概念
```
Business Domain (ビジネスドメイン)
├── Core Domain (中核ドメイン)
│   └── SEO Article Generation
├── Supporting Domains (支援ドメイン)
│   ├── Company Management
│   ├── Organization Management
│   └── Style Template Management
└── Generic Domains (汎用ドメイン)
    └── Image Generation
```

### 責務分離の原則
1. **高凝集**: 関連する機能を同一ドメイン内に集約
2. **疎結合**: ドメイン間の依存関係を最小化
3. **単一責任**: 各ドメインは特定のビジネス領域のみを担当
4. **境界文脈**: 明確な境界内でのモデルの一貫性維持

## バックエンドアーキテクチャ構造

### 全体ディレクトリ構成
```
backend/app/
├── domains/                    # ビジネスドメイン
│   ├── __init__.py
│   ├── seo_article/           # SEO記事生成ドメイン（中核）
│   ├── company/               # 会社管理ドメイン（支援）
│   ├── organization/          # 組織管理ドメイン（支援）
│   ├── style_template/        # スタイルテンプレートドメイン（支援）
│   └── image_generation/      # 画像生成ドメイン（汎用）
├── common/                    # 共通機能
│   ├── auth.py               # 認証処理
│   ├── database.py           # データベース接続
│   └── schemas.py           # 共通スキーマ
├── core/                      # アプリケーションコア
│   ├── config.py            # 設定管理
│   ├── exceptions.py        # 例外定義
│   └── logger.py           # ログ設定
├── infrastructure/           # インフラストラクチャ層
│   ├── external_apis/       # 外部API連携
│   ├── logging/            # ログシステム
│   └── gcp_auth.py        # GCP認証
└── api/                     # API統合層
    └── router.py           # ルーター統合
```

## ドメイン別詳細設計

### 1. SEO記事生成ドメイン（中核ドメイン）

#### ディレクトリ構造
```
domains/seo_article/
├── __init__.py
├── endpoints.py           # APIエンドポイント
├── schemas.py            # データスキーマ
├── context.py           # 記事生成コンテキスト
├── agents/              # エージェント定義
│   ├── __init__.py
│   ├── definitions.py   # エージェント定義
│   └── tools.py        # エージェント用ツール
├── services/            # ビジネスロジック
│   ├── __init__.py
│   ├── generation_service.py
│   ├── management_service.py
│   ├── flow_service.py
│   └── background_task_manager.py
└── presentation/        # プレゼンテーション層
```

#### 責務と境界
**中核責務**:
- SEO記事の自動生成プロセス管理
- AI エージェントによるマルチステップ実行
- リアルタイム進捗管理とユーザー対話

**境界定義**:
- **内部**: 記事生成ロジック、エージェント管理、状態管理
- **外部依存**: 会社情報（Company Domain）、スタイル設定（Style Template Domain）

#### 主要コンポーネント

##### エンドポイント層 (`endpoints.py`)
```python
# SEO記事生成ドメインのAPIエンドポイント
router = APIRouter()

@router.get("/", response_model=List[dict])
async def get_articles(user_id: str = Depends(get_current_user_id_from_token)):
    """ユーザーの記事一覧取得"""
    articles = await article_service.get_user_articles(user_id)
    return articles

@router.post("/generation/create")
async def create_generation_process(
    request: GenerateArticleRequest,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """記事生成プロセスの開始"""
    process_id = await article_service.start_generation(request, user_id)
    return {"process_id": process_id}
```

##### サービス層 (`services/`)
```python
# generation_service.py
class ArticleGenerationService:
    """記事生成の中核ビジネスロジック"""
    
    async def start_generation(self, request: GenerateArticleRequest, user_id: str):
        """記事生成プロセスの開始"""
        # ビジネスルールの適用
        # 外部ドメインからの情報取得
        # エージェント実行の開始
        
    async def process_user_input(self, process_id: str, input_data: dict):
        """ユーザー入力の処理"""
        # 入力検証
        # 状態更新
        # 次ステップの実行
```

##### ドメインモデル (`context.py`)
```python
@dataclass
class ArticleContext:
    """記事生成プロセスの状態管理"""
    current_step: str
    user_input_type: Optional[str]
    personas: Optional[List[PersonaData]]
    themes: Optional[List[ThemeData]]
    research_plan: Optional[ResearchPlan]
    # ... 他の状態情報
```

### 2. 会社管理ドメイン（支援ドメイン）

#### ディレクトリ構造
```
domains/company/
├── __init__.py
├── endpoints.py      # 会社情報 CRUD API
├── schemas.py       # 会社情報スキーマ定義
├── models.py        # データモデル
└── service.py       # 会社管理サービス
```

#### 責務と境界
**支援責務**:
- 会社基本情報の管理
- ターゲットペルソナの設定
- デフォルト会社情報の管理

**境界定義**:
- **提供サービス**: SEO記事生成時のコンテキスト情報
- **独立性**: 他ドメインに依存しない自完結型

#### 主要コンポーネント

##### データスキーマ (`schemas.py`)
```python
class CompanyInfoCreate(BaseModel):
    """会社情報作成スキーマ"""
    company_name: str
    business_description: str
    target_persona: str
    company_tone: str
    contact_info: Optional[dict]

class CompanyInfoResponse(BaseModel):
    """会社情報レスポンススキーマ"""
    id: str
    company_name: str
    business_description: str
    is_default: bool
    created_at: datetime
```

##### ビジネスサービス (`service.py`)
```python
class CompanyService:
    """会社管理のビジネスロジック"""
    
    @staticmethod
    async def create_company(company_data: CompanyInfoCreate, user_id: str):
        """会社情報の作成"""
        # バリデーション
        # データベース保存
        # デフォルト設定の管理
        
    @staticmethod
    async def get_default_company(user_id: str):
        """デフォルト会社情報の取得"""
        # デフォルト会社の特定
        # 存在確認
        # データ返却
```

### 3. 組織管理ドメイン（支援ドメイン）

#### ディレクトリ構造
```
domains/organization/
├── __init__.py
├── endpoints.py     # 組織管理 API
├── schemas.py      # 組織関連スキーマ
└── service.py      # 組織管理サービス
```

#### 責務と境界
**支援責務**:
- マルチテナント組織管理
- メンバー権限管理
- 招待システム

**境界定義**:
- **横断的機能**: 全ドメインでの組織レベルアクセス制御
- **独立運用**: 組織構造の変更が他ドメインに影響しない

#### 主要コンポーネント

##### サービス層 (`service.py`)
```python
class OrganizationService:
    """組織管理のビジネスロジック"""
    
    async def create_organization(self, user_id: str, org_data: OrganizationCreate):
        """組織の作成"""
        # 組織作成
        # オーナー権限設定
        # メンバーテーブル初期化
        
    async def invite_member(self, org_id: str, invitation_data: InvitationCreate):
        """メンバー招待"""
        # 招待トークン生成
        # 期限設定
        # 通知送信
```

### 4. スタイルテンプレートドメイン（支援ドメイン）

#### ディレクトリ構造
```
domains/style_template/
├── __init__.py
├── endpoints.py     # スタイルテンプレート API
└── schemas.py      # テンプレートスキーマ
```

#### 責務と境界
**支援責務**:
- 記事文体・スタイルの管理
- ユーザー・組織レベルのテンプレート
- デフォルトテンプレート機能

**境界定義**:
- **提供サービス**: SEO記事生成時のスタイル指定
- **設定管理**: テンプレートの作成・編集・適用

### 5. 画像生成ドメイン（汎用ドメイン）

#### ディレクトリ構造
```
domains/image_generation/
├── __init__.py
├── endpoints.py     # 画像生成・管理 API
├── schemas.py      # 画像関連スキーマ
└── service.py      # 画像生成サービス
```

#### 責務と境界
**汎用責務**:
- AI による画像生成
- 画像アップロード・管理
- クラウドストレージ連携

**境界定義**:
- **技術的機能**: ビジネスロジックよりも技術実装中心
- **再利用性**: 複数のドメインから利用可能

## ドメイン間の連携パターン

### 1. サービス間通信

#### 同期的連携
```python
# SEO記事生成での会社情報取得
class ArticleGenerationService:
    async def get_generation_context(self, user_id: str):
        # 会社ドメインからデフォルト会社情報を取得
        company_info = await CompanyService.get_default_company(user_id)
        
        # スタイルテンプレートドメインからデフォルトスタイル取得
        style_template = await StyleTemplateService.get_default_template(user_id)
        
        return ArticleContext(
            company_info=company_info,
            style_template=style_template
        )
```

#### 依存関係の管理
```python
# 依存関係の注入パターン
class ArticleGenerationService:
    def __init__(
        self,
        company_service: CompanyService,
        style_service: StyleTemplateService
    ):
        self.company_service = company_service
        self.style_service = style_service
```

### 2. データ整合性の管理

#### トランザクション境界
```python
async def create_article_with_dependencies(user_id: str, article_data: dict):
    """複数ドメインにまたがるトランザクション"""
    async with database_transaction():
        # 記事作成（SEO Article Domain）
        article = await ArticleService.create_article(article_data, user_id)
        
        # 画像プレースホルダー作成（Image Generation Domain）
        await ImageService.create_placeholders(article.id, article_data.images)
        
        return article
```

#### イベント駆動アーキテクチャ
```python
# ドメインイベント
class ArticleCompletedEvent:
    def __init__(self, article_id: str, user_id: str):
        self.article_id = article_id
        self.user_id = user_id

# イベントハンドラー
async def handle_article_completed(event: ArticleCompletedEvent):
    """記事完成時の後続処理"""
    # 画像生成の最終化
    await ImageService.finalize_article_images(event.article_id)
    
    # 統計情報の更新
    await AnalyticsService.update_user_stats(event.user_id)
```

## 共通機能の管理

### 1. 共通ライブラリ (`common/`)

#### 認証機能 (`auth.py`)
```python
# 全ドメインで共有される認証機能
def get_current_user_id_from_token(authorization) -> str:
    """JWT トークンからユーザーID抽出"""
    # 全ドメインで統一的な認証処理
```

#### データベース接続 (`database.py`)
```python
# 全ドメインで共有されるデータベースクライアント
supabase: Client = create_supabase_client()

def test_connection() -> bool:
    """データベース接続テスト"""
    # 全ドメインで共通の接続確認
```

### 2. インフラストラクチャ層 (`infrastructure/`)

#### 外部API連携 (`external_apis/`)
```python
# 複数ドメインで利用される外部サービス
class GCSService:
    """Google Cloud Storage サービス"""
    # 画像生成ドメインとファイル管理で共有

class NotionService:
    """Notion API連携サービス"""
    # 将来的な拡張での共有利用
```

## API統合層の設計

### ルーター統合 (`api/router.py`)
```python
from fastapi import APIRouter

# 各ドメインのルーターをインポート
from app.domains.seo_article.endpoints import router as seo_article_router
from app.domains.company.endpoints import router as company_router
from app.domains.organization.endpoints import router as organization_router
from app.domains.style_template.endpoints import router as style_template_router
from app.domains.image_generation.endpoints import router as image_generation_router

api_router = APIRouter()

# 各ドメインルーターを統合
api_router.include_router(seo_article_router, prefix="/articles", tags=["SEO Article"])
api_router.include_router(company_router, prefix="/companies", tags=["Companies"])
api_router.include_router(organization_router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(style_template_router, prefix="/style-templates", tags=["Style Templates"])
api_router.include_router(image_generation_router, prefix="/images", tags=["Image Generation"])
```

### 統合のメリット
1. **明確な境界**: 各ドメインの責務が明確
2. **拡張性**: 新しいドメインの容易な追加
3. **保守性**: ドメイン内の変更が他に影響しない
4. **テスト容易性**: ドメイン単位でのテスト実行

## ドメインの進化と拡張

### 新ドメインの追加パターン
```python
# 将来追加される Instagram ドメインの例
domains/instagram/
├── __init__.py
├── endpoints.py     # Instagram 連携 API
├── schemas.py      # Instagram データスキーマ
├── service.py      # Instagram ビジネスロジック
└── models.py       # Instagram データモデル

# API統合での追加
api_router.include_router(instagram_router, prefix="/instagram", tags=["Instagram"])
```

### ドメインの分割パターン
```python
# SEO記事生成ドメインが大きくなった場合の分割例
domains/
├── article_generation/     # 記事生成コア
├── article_workflow/      # ワークフロー管理
├── article_analytics/     # 記事分析
└── article_publishing/    # 記事公開
```

## 設計品質の維持

### 1. アーキテクチャ原則の遵守

#### 単一責任原則
- 各ドメインは特定のビジネス機能のみを担当
- 責務の重複を避ける
- 明確な境界の維持

#### 開放閉鎖原則
- 新機能追加時は既存コードの変更を最小化
- インターフェースの安定性維持
- 拡張ポイントの明確化

### 2. 依存関係の管理

#### 依存の方向性
```
Presentation Layer (endpoints.py)
         ↓
Application Layer (services/)
         ↓
Domain Layer (models.py, schemas.py)
         ↓
Infrastructure Layer (database, external APIs)
```

#### 循環依存の回避
```python
# 避けるべきパターン
# Company Domain → SEO Article Domain
# SEO Article Domain → Company Domain

# 推奨パターン
# SEO Article Domain → Company Domain（一方向）
```

### 3. テスト戦略

#### ドメイン単位テスト
```python
# SEO記事生成ドメインのテスト
class TestSEOArticleDomain:
    async def test_article_generation_service(self):
        # サービス層のテスト
        
    async def test_article_endpoints(self):
        # エンドポイント層のテスト
        
    async def test_article_schemas(self):
        # スキーマ検証のテスト
```

#### 統合テスト
```python
class TestDomainIntegration:
    async def test_article_with_company_info(self):
        # ドメイン間連携のテスト
        
    async def test_end_to_end_article_generation(self):
        # エンドツーエンドのテスト
```

## まとめ

Marketing Automation APIのドメイン駆動設計実装は、ビジネス要件に基づいた明確な責務分離により、以下の利益を提供しています：

### 設計上の利益
1. **保守性向上**: ドメイン内の変更が他への影響を最小化
2. **拡張性確保**: 新機能・新ドメインの容易な追加
3. **理解容易性**: ビジネスロジックとドメイン構造の一致
4. **チーム開発**: ドメイン単位での並行開発可能

### 技術的利益
1. **テスト容易性**: ドメイン単位でのテスト実行
2. **再利用性**: 共通機能の効率的な活用
3. **スケーラビリティ**: ドメイン別の性能最適化
4. **デバッグ効率**: 問題の発生箇所の特定容易性

### ビジネス価値
1. **変更対応力**: ビジネス要件変更への迅速な対応
2. **品質向上**: ドメイン専門知識の集約
3. **開発効率**: 明確な責務による開発速度向上
4. **将来性**: システムの長期的な発展性確保

このDDD実装により、Marketing Automation APIは単なる技術的なAPIを超えて、ビジネスドメインの複雑性を適切に管理し、持続可能な成長を支援するアーキテクチャを実現しています。