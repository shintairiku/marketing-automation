# SEO記事生成におけるデータモデルと設計思想

## 概要

本文書では、SEO記事生成プロセスで利用される主要なデータ構造と設計について詳細に解説します。プロセス全体の状態を保持する`ArticleContext`の各フィールドの役割、APIの入出力を定義するPydanticスキーマ、および各ステップで生成・利用されるデータモデルの詳細を説明します。

## 設計思想

### 1. 型安全性の重視

Pydanticを活用することで、データの入出力時に厳密な型チェックとバリデーションを実施し、システム全体の堅牢性を確保しています。

### 2. 段階的データ蓄積

記事生成プロセスの各ステップで生成されたデータを`ArticleContext`に段階的に蓄積し、後続のステップで活用する設計になっています。

### 3. 柔軟性とスケーラビリティ

JSONBフィールドを活用することで、将来的な機能拡張に対応できる柔軟な設計を採用しています。

### 4. 実時間性の確保

Supabase Realtimeとの連携を考慮し、リアルタイムでの状態同期に最適化されたデータ構造を採用しています。

## 中核データモデル

### 1. ArticleContext（記事生成コンテキスト）

ファイル位置: `/backend/app/domains/seo_article/context.py`

記事生成プロセス全体で共有される中核的なデータ構造。WebSocketからSupabase Realtimeへの移行に対応。

```python
@dataclass
class ArticleContext:
    """記事生成プロセス全体で共有されるコンテキスト (WebSocket対応)"""
    
    # --- ユーザー/API入力 ---
    initial_keywords: List[str] = field(default_factory=list)
    target_age_group: Optional[AgeGroup] = None
    persona_type: Optional[PersonaType] = None
    custom_persona: Optional[str] = None
    target_length: Optional[int] = None
    num_theme_proposals: int = 3
    vector_store_id: Optional[str] = None
    num_research_queries: int = 5
    num_persona_examples: int = 3
```

#### ユーザー入力データ

**基本パラメータ:**
- `initial_keywords`: 記事生成の元となるキーワードリスト
- `target_age_group`: ターゲット年代層（`AgeGroup`枚挙型）
- `persona_type`: ペルソナ属性（`PersonaType`枚挙型）
- `custom_persona`: 独自設定ペルソナ（`PersonaType.OTHER`時に使用）
- `target_length`: 目標文字数

**生成制御パラメータ:**
- `num_theme_proposals`: 生成するテーマ案数（デフォルト: 3）
- `num_research_queries`: リサーチクエリ数（デフォルト: 5）
- `num_persona_examples`: 生成する具体ペルソナ数（デフォルト: 3）

#### 会社情報統合

```python
# 会社情報 - 基本情報
company_name: Optional[str] = None
company_description: Optional[str] = None
company_usp: Optional[str] = None
company_website_url: Optional[str] = None
company_target_persona: Optional[str] = None

# 会社情報 - ブランディング
company_brand_slogan: Optional[str] = None
company_style_guide: Optional[str] = None

# 会社情報 - SEO・コンテンツ戦略
company_target_keywords: Optional[str] = None
company_industry_terms: Optional[str] = None
company_avoid_terms: Optional[str] = None
company_popular_articles: Optional[str] = None
company_target_area: Optional[str] = None
```

#### 画像モード対応

```python
# --- 画像モード関連 ---
image_mode: bool = False
image_settings: Dict[str, Any] = field(default_factory=dict)
image_placeholders: List[ImagePlaceholder] = field(default_factory=list)
```

#### プロセス状態管理

```python
# --- 生成プロセス状態 ---
current_step: Literal[
    "start",
    "keyword_analyzing",
    "keyword_analyzed",
    "persona_generating",
    "persona_generated",
    "persona_selected",
    "theme_generating",
    "theme_proposed",
    "theme_selected",
    "research_planning",
    "research_plan_generated",
    "research_plan_approved",
    "researching",
    "research_synthesizing",
    "research_report_generated",
    "outline_generating",
    "outline_generated",
    "writing_sections",
    "editing",
    "completed",
    "error"
] = "start"
```

**ステップ状態詳細:**
- `keyword_analyzing` → `keyword_analyzed`: キーワード分析フェーズ
- `persona_generating` → `persona_generated` → `persona_selected`: ペルソナ生成・選択
- `theme_generating` → `theme_proposed` → `theme_selected`: テーマ提案・選択
- `research_planning` → `research_plan_approved`: リサーチ計画策定・承認
- `researching` → `research_synthesizing` → `research_report_generated`: リサーチ実行・統合
- `outline_generating` → `outline_generated`: アウトライン生成
- `writing_sections`: セクション執筆
- `editing`: 最終編集
- `completed`: 完了

#### 生成済みデータ保持

```python
# テーマ・ペルソナ
generated_themes: List[ThemeIdea] = field(default_factory=list)
generated_detailed_personas: List[str] = field(default_factory=list)
selected_detailed_persona: Optional[str] = None
selected_theme: Optional[ThemeIdea] = None

# リサーチ関連
research_plan: Optional[ResearchPlan] = None
research_query_results: List[ResearchQueryResult] = field(default_factory=list)
research_report: Optional[ResearchReport] = None

# アウトライン・執筆
generated_outline: Optional[Outline] = None
generated_sections: List[ArticleSection] = field(default_factory=list)
generated_sections_html: List[str] = field(default_factory=list)
full_draft_html: Optional[str] = None
final_article: Optional[RevisedArticle] = None
final_article_html: Optional[str] = None
final_article_id: Optional[str] = None
```

#### WebSocket/Realtime連携

```python
# --- WebSocket/インタラクション用 ---
websocket: Optional[WebSocket] = None
user_response_event: Optional[asyncio.Event] = None
expected_user_input: Optional[UserInputType] = None
user_response: Optional[ClientResponsePayload] = None
user_id: Optional[str] = None
process_id: Optional[str] = None
```

## Pydanticスキーマ体系

### 1. リクエストモデル

ファイル位置: `/backend/app/domains/seo_article/schemas.py`

#### GenerateArticleRequest

記事生成APIのメインリクエストモデル。

```python
class GenerateArticleRequest(BaseModel):
    """記事生成APIリクエストモデル"""
    initial_keywords: List[str] = Field(..., description="記事生成の元となるキーワードリスト")
    target_age_group: Optional[AgeGroup] = Field(None, description="ターゲット年代層")
    persona_type: Optional[PersonaType] = Field(None, description="ペルソナ属性")
    custom_persona: Optional[str] = Field(None, description="独自ペルソナ")
    target_length: Optional[int] = Field(None, description="目標文字数")
    num_theme_proposals: int = Field(3, description="テーマ案数", ge=1)
    num_research_queries: int = Field(3, description="リサーチクエリ数", ge=1)
    num_persona_examples: int = Field(3, description="ペルソナ例数", ge=1)
    
    # 会社情報
    company_name: Optional[str] = Field(None, description="企業名")
    company_description: Optional[str] = Field(None, description="企業概要")
    company_style_guide: Optional[str] = Field(None, description="文体ガイド")
    
    # 画像モード
    image_mode: bool = Field(False, description="画像プレースホルダー使用")
    image_settings: Optional[dict] = Field(None, description="画像生成設定")
    
    # スタイルテンプレート
    style_template_id: Optional[str] = Field(None, description="スタイルテンプレートID")
```

#### 列挙型定義

```python
class AgeGroup(str, Enum):
    TEENS = "10代"
    TWENTIES = "20代"
    THIRTIES = "30代"
    FORTIES = "40代"
    FIFTIES = "50代"
    SIXTIES = "60代"
    SEVENTIES_OR_OLDER = "70代以上"

class PersonaType(str, Enum):
    HOUSEWIFE = "主婦"
    STUDENT = "学生"
    OFFICE_WORKER = "社会人"
    SELF_EMPLOYED = "自営業"
    EXECUTIVE = "経営者・役員"
    RETIREE = "退職者"
    OTHER = "その他"
```

### 2. 応答・イベントモデル

#### ステップ別ペイロード

**ステータス更新:**
```python
class StatusUpdatePayload(BasePayload):
    """ステータス更新ペイロード"""
    step: str = Field(description="現在の処理ステップ名")
    message: str = Field(description="処理状況メッセージ")
    image_mode: Optional[bool] = Field(None, description="画像モード有効性")
```

**テーマ提案:**
```python
class ThemeProposalData(BaseModel):
    title: str
    description: str
    keywords: List[str]

class ThemeProposalPayload(BasePayload):
    """テーマ提案ペイロード"""
    themes: List[ThemeProposalData] = Field(description="提案テーマ案")
```

**リサーチ計画:**
```python
class ResearchPlanQueryData(BaseModel):
    query: str
    focus: str

class ResearchPlanData(BaseModel):
    topic: str
    queries: List[ResearchPlanQueryData]

class ResearchPlanPayload(BasePayload):
    """リサーチ計画ペイロード"""
    plan: ResearchPlanData = Field(description="生成リサーチ計画")
```

#### アウトライン構造

```python
class OutlineSectionData(BaseModel):
    heading: str
    estimated_chars: Optional[int] = None
    subsections: Optional[List['OutlineSectionData']] = None # 再帰構造

class OutlineData(BaseModel):
    title: str
    suggested_tone: str
    sections: List[OutlineSectionData]

class OutlinePayload(BasePayload):
    """アウトラインペイロード"""
    outline: OutlineData = Field(description="生成アウトライン")
```

#### 画像プレースホルダー

```python
class ImagePlaceholderData(BaseModel):
    """画像プレースホルダー情報"""
    placeholder_id: str = Field(description="プレースホルダー一意ID")
    description_jp: str = Field(description="画像説明（日本語）")
    prompt_en: str = Field(description="画像生成用英語プロンプト")
    alt_text: str = Field(description="alt属性テキスト")
```

#### セクション生成

```python
class SectionChunkPayload(BasePayload):
    """セクションHTMLチャンクペイロード（ストリーミング用）"""
    section_index: int = Field(description="セクションインデックス（0ベース）")
    heading: str = Field(description="セクション見出し")
    html_content_chunk: str = Field(description="HTMLコンテンツ断片")
    is_complete: bool = Field(False, description="セクション完了フラグ")
    
    # 画像モード対応
    section_complete_content: Optional[str] = Field(None, description="完全HTMLコンテンツ")
    image_placeholders: Optional[List[ImagePlaceholderData]] = Field(None, description="画像プレースホルダー")
    is_image_mode: bool = Field(False, description="画像モードフラグ")
```

### 3. ユーザー応答モデル

#### 選択・承認系

```python
class SelectPersonaPayload(BasePayload):
    """ペルソナ選択応答"""
    selected_id: int = Field(description="選択ペルソナID（0ベース）", ge=0)

class SelectThemePayload(BasePayload):
    """テーマ選択応答"""
    selected_index: int = Field(description="選択テーマインデックス（0ベース）", ge=0)

class ApprovePayload(BasePayload):
    """承認/拒否応答"""
    approved: bool = Field(description="承認フラグ")
```

#### 編集系

```python
class EditAndProceedPayload(BasePayload):
    """編集して進行要求"""
    edited_content: Dict[str, Any] = Field(description="編集済み内容")

class EditPersonaPayload(BasePayload):
    """ペルソナ編集"""
    edited_persona: Dict[str, Any] = Field(description="編集ペルソナ")

class EditThemePayload(BasePayload):
    """テーマ編集"""
    edited_theme: Dict[str, Any] = Field(description="編集テーマ")

class EditOutlinePayload(BasePayload):
    """アウトライン編集"""
    edited_outline: Dict[str, Any] = Field(description="編集アウトライン")
```

### 4. リサーチ関連モデル

#### SerpAPI分析

```python
class SerpAnalysisArticleData(BaseModel):
    """SerpAPI分析記事データ"""
    url: str
    title: str
    headings: List[str]
    content_preview: str
    char_count: int
    image_count: int
    source_type: str
    position: Optional[int] = None
    question: Optional[str] = None

class SerpKeywordAnalysisReport(BaseModel):
    """SERPキーワード分析レポート"""
    search_query: str = Field(description="検索クエリ")
    total_results: int = Field(default=0, description="検索結果総数")
    analyzed_articles: List[SerpAnalysisArticleData] = Field(default_factory=list)
    average_article_length: int = Field(default=0, description="平均文字数")
    recommended_target_length: int = Field(default=3000, description="推奨文字数")
    main_themes: List[str] = Field(default_factory=list, description="主要テーマ")
    common_headings: List[str] = Field(default_factory=list, description="共通見出し")
    content_gaps: List[str] = Field(default_factory=list, description="コンテンツギャップ")
    competitive_advantages: List[str] = Field(default_factory=list, description="競争優位性")
    user_intent_analysis: str = Field(default="", description="ユーザー意図分析")
    content_strategy_recommendations: List[str] = Field(default_factory=list, description="戦略推奨")
    
    # 後方互換性
    keyword: str = Field(description="分析キーワード")
    competition_level: str = Field(default="medium", description="競合レベル")
    search_volume: Optional[int] = Field(None, description="検索ボリューム")
    difficulty: Optional[str] = Field(None, description="難易度")
    recommendations: List[str] = Field(default_factory=list, description="推奨事項")
```

#### リサーチ結果構造

```python
class SourceSnippet(BaseModel):
    """リサーチ抽出情報出典"""
    title: str = Field(description="出典タイトル")
    url: str = Field(description="出典URL")
    snippet: str = Field(description="抽出情報・データ・主張")

class ResearchQueryResult(BaseModel):
    """リサーチクエリ結果"""
    query: str = Field(description="検索クエリ")
    results: List[SourceSnippet] = Field(default_factory=list, description="抽出情報")
    summary: Optional[str] = Field(None, description="結果サマリー")

class KeyPointData(BaseModel):
    point: str
    supporting_sources: List[str]

class ResearchReportData(BaseModel):
    topic: str
    overall_summary: str
    key_points: List[KeyPointData]
    interesting_angles: List[str]
    all_sources: List[str]
```

### 5. 記事構造モデル

#### 基本記事構造

```python
class ArticleSection(BaseModel):
    """記事セクション"""
    title: str = Field(description="セクションタイトル")
    content: str = Field(description="セクション内容")
    order: int = Field(description="セクション順序")

class ArticleSectionWithImages(BaseModel):
    """画像付き記事セクション"""
    title: str = Field(description="セクションタイトル")
    content: str = Field(description="セクション内容")
    order: int = Field(description="セクション順序")
    images: List[ImagePlaceholderData] = Field(default_factory=list, description="画像プレースホルダー")

class RevisedArticle(BaseModel):
    """修正済み記事"""
    title: str = Field(description="記事タイトル")
    content: str = Field(description="記事本文")
    sections: List[ArticleSection] = Field(default_factory=list, description="セクション")
    revision_notes: Optional[str] = Field(None, description="修正メモ")
```

#### 最終結果

```python
class FinalResultPayload(BasePayload):
    """最終結果ペイロード"""
    title: str = Field(description="最終記事タイトル")
    final_html_content: str = Field(description="完成記事HTMLコンテンツ")
    article_id: Optional[str] = Field(default=None, description="生成記事ID")
```

## データ変換・統合パターン

### 1. リクエスト → ArticleContext変換

```python
def create_context_from_request(request: GenerateArticleRequest, user_id: str) -> ArticleContext:
    """リクエストからArticleContextを生成"""
    context = ArticleContext(
        initial_keywords=request.initial_keywords,
        target_age_group=request.target_age_group,
        persona_type=request.persona_type,
        custom_persona=request.custom_persona,
        target_length=request.target_length,
        num_theme_proposals=request.num_theme_proposals,
        num_research_queries=request.num_research_queries,
        num_persona_examples=request.num_persona_examples,
        
        # 会社情報
        company_name=request.company_name,
        company_description=request.company_description,
        company_style_guide=request.company_style_guide,
        
        # 画像モード
        image_mode=request.image_mode,
        image_settings=request.image_settings or {},
        
        # スタイルテンプレート
        style_template_id=request.style_template_id,
        
        # 実行コンテキスト
        user_id=user_id
    )
    return context
```

### 2. ArticleContext → JSON永続化

データベースの`generated_articles_state.article_context`フィールドにJSONB形式で保存：

```python
def serialize_context_to_db(context: ArticleContext) -> Dict[str, Any]:
    """ArticleContextをDB保存用辞書に変換"""
    return {
        # 基本設定
        "initial_keywords": context.initial_keywords,
        "target_age_group": context.target_age_group.value if context.target_age_group else None,
        "persona_type": context.persona_type.value if context.persona_type else None,
        "custom_persona": context.custom_persona,
        "target_length": context.target_length,
        
        # 生成済みデータ
        "generated_detailed_personas": context.generated_detailed_personas,
        "selected_detailed_persona": context.selected_detailed_persona,
        "generated_themes": [asdict(theme) for theme in context.generated_themes],
        "selected_theme": asdict(context.selected_theme) if context.selected_theme else None,
        "research_plan": asdict(context.research_plan) if context.research_plan else None,
        "research_query_results": [asdict(result) for result in context.research_query_results],
        "generated_outline": asdict(context.generated_outline) if context.generated_outline else None,
        "generated_sections_html": context.generated_sections_html,
        "final_article_html": context.final_article_html,
        
        # 画像関連
        "image_mode": context.image_mode,
        "image_placeholders": [asdict(placeholder) for placeholder in context.image_placeholders],
        
        # プロセス状態
        "current_step": context.current_step,
        "current_section_index": context.current_section_index,
        
        # メタデータ
        "process_id": context.process_id,
        "user_id": context.user_id
    }
```

### 3. JSON → ArticleContext復元

```python
def deserialize_context_from_db(data: Dict[str, Any]) -> ArticleContext:
    """DB辞書からArticleContextを復元"""
    context = ArticleContext()
    
    # 基本設定復元
    context.initial_keywords = data.get("initial_keywords", [])
    if data.get("target_age_group"):
        context.target_age_group = AgeGroup(data["target_age_group"])
    if data.get("persona_type"):
        context.persona_type = PersonaType(data["persona_type"])
    context.custom_persona = data.get("custom_persona")
    context.target_length = data.get("target_length")
    
    # 生成済みデータ復元
    context.generated_detailed_personas = data.get("generated_detailed_personas", [])
    context.selected_detailed_persona = data.get("selected_detailed_persona")
    
    if data.get("generated_themes"):
        context.generated_themes = [
            ThemeProposalData(**theme_data) 
            for theme_data in data["generated_themes"]
        ]
    
    if data.get("selected_theme"):
        context.selected_theme = ThemeProposalData(**data["selected_theme"])
    
    # その他のデータ復元...
    
    return context
```

## エラーハンドリングパターン

### 1. バリデーションエラー

```python
from pydantic import ValidationError

try:
    request = GenerateArticleRequest(**request_data)
except ValidationError as e:
    # 詳細なエラー情報を含むレスポンス
    return {
        "error": "validation_error",
        "details": e.errors(),
        "message": "リクエストデータの形式が正しくありません"
    }
```

### 2. データ変換エラー

```python
class DataConversionError(Exception):
    """データ変換エラー"""
    def __init__(self, message: str, original_data: Any = None):
        super().__init__(message)
        self.original_data = original_data

def safe_convert_payload(payload_data: Dict[str, Any], target_class: type) -> BaseModel:
    """安全なペイロード変換"""
    try:
        return target_class(**payload_data)
    except Exception as e:
        raise DataConversionError(
            f"Failed to convert to {target_class.__name__}: {str(e)}",
            original_data=payload_data
        )
```

## パフォーマンス最適化

### 1. 遅延読み込み

大きなデータ構造は必要時のみ読み込み：

```python
class LazyLoadedContent:
    def __init__(self, content_id: str):
        self._content_id = content_id
        self._content: Optional[str] = None
    
    @property
    def content(self) -> str:
        if self._content is None:
            self._content = self._load_content()
        return self._content
    
    def _load_content(self) -> str:
        # データベースから実際のコンテンツを読み込み
        return load_content_from_db(self._content_id)
```

### 2. キャッシュ戦略

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_serialized_context(context_hash: str) -> Dict[str, Any]:
    """コンテキストのシリアライズ結果をキャッシュ"""
    return serialize_context_to_db(context)
```

### 3. 部分更新

必要な部分のみ更新するパターン：

```python
def update_context_step_data(
    context: ArticleContext, 
    step: str, 
    step_data: Dict[str, Any]
) -> None:
    """特定ステップのデータのみ更新"""
    if step == "theme_generated":
        context.generated_themes = [
            ThemeProposalData(**theme) for theme in step_data["themes"]
        ]
    elif step == "persona_generated":
        context.generated_detailed_personas = step_data["personas"]
    elif step == "outline_generated":
        context.generated_outline = OutlineData(**step_data["outline"])
    # 他のステップ...
```

## 実装例

### 1. エージェント出力の標準化

```python
class StandardizedAgentOutput(BaseModel):
    """標準化されたエージェント出力"""
    step_name: str = Field(description="実行ステップ名")
    output_type: str = Field(description="出力タイプ")
    data: Dict[str, Any] = Field(description="出力データ")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="メタデータ")
    timing: Dict[str, Any] = Field(default_factory=dict, description="実行時間情報")
    
    def to_context_update(self) -> Dict[str, Any]:
        """ArticleContext更新用データに変換"""
        return {
            "step": self.step_name,
            "data": self.data,
            "metadata": self.metadata
        }
```

### 2. 型安全なペイロード変換

```python
def convert_payload_to_model(payload: Dict[str, Any], response_type: str) -> BaseModel:
    """ペイロードを適切なPydanticモデルに変換"""
    conversion_map = {
        "select_persona": SelectPersonaPayload,
        "select_theme": SelectThemePayload,
        "approve_plan": ApprovePayload,
        "approve_outline": ApprovePayload,
        "regenerate": RegeneratePayload,
        "edit_and_proceed": EditAndProceedPayload,
        "edit_persona": EditPersonaPayload,
        "edit_theme": EditThemePayload,
        "edit_outline": EditOutlinePayload,
    }
    
    model_class = conversion_map.get(response_type)
    if not model_class:
        raise ValueError(f"Unknown response type: {response_type}")
    
    try:
        return model_class(**payload)
    except ValidationError as e:
        raise ValueError(f"Invalid payload for {response_type}: {e}")
```

## まとめ

本データモデル設計は、SEO記事生成の複雑なワークフローを型安全かつ効率的に管理するための包括的なソリューションです。Pydanticによる厳密な型チェック、段階的データ蓄積、リアルタイム同期対応により、堅牢で拡張性の高いシステムを実現しています。