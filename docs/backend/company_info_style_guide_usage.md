# 会社情報とスタイルガイドの活用仕様

## 概要

本文書では、ユーザーが登録した「会社情報」と「スタイルガイド」が、SEO記事生成プロセスでどのように活用されるかを詳細に解説します。`ArticleContext`に読み込まれたこれらの情報が、各エージェントのプロンプトに組み込まれ、生成される記事のトーン＆マナーや内容の方向性を決定する仕組みを詳述します。

## システム構成

```
┌─────────────────────────┐
│    ユーザー登録         │
├─────────────────────────┤
│  • 会社情報管理        │
│  • 記事スタイル設定  │
└─────────────────────────┘
           │
           ▼
┌─────────────────────────┐
│   データベース保存      │
├─────────────────────────┤
│  • company_info         │
│  • style_guide_templates│
└─────────────────────────┘
           │
           ▼
┌─────────────────────────┐
│  記事生成API呼び出し    │
├─────────────────────────┤
│  • 会社情報取得         │
│  • スタイルテンプレート │
│    取得・適用           │
└─────────────────────────┘
           │
           ▼
┌─────────────────────────┐
│   ArticleContext        │
├─────────────────────────┤
│  • 会社情報統合         │
│  • スタイル設定統合     │
└─────────────────────────┘
           │
           ▼
┌─────────────────────────┐
│  エージェント実行       │
├─────────────────────────┤
│  • プロンプト生成       │
│  • 企業情報・スタイル   │
│    ガイドライン反映     │
└─────────────────────────┘
```

## データベース構造

### 1. company_info テーブル

会社情報を管理するメインテーブル。

```sql
CREATE TABLE company_info (
    id TEXT PRIMARY KEY DEFAULT (gen_random_uuid()::text),
    user_id TEXT NOT NULL,
    
    -- 基本情報
    name VARCHAR(200) NOT NULL,
    website_url VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    usp TEXT NOT NULL,
    target_persona VARCHAR(50) NOT NULL,
    
    -- デフォルト設定
    is_default BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- 詳細設定（オプション）
    brand_slogan VARCHAR(200),
    target_keywords VARCHAR(500),
    industry_terms VARCHAR(500),
    avoid_terms VARCHAR(500),
    popular_articles TEXT,
    target_area VARCHAR(200),
    
    -- タイムスタンプ
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**主要フィールド説明:**

| フィールド | 説明 | 記事生成での活用方法 |
|-----------|------|-------------------|
| `name` | 企業名 | 記事タイトル・本文で企業名として言及 |
| `description` | 企業概要 | 企業の専門性・信頼性を示す文脈 |
| `usp` | 独自の価値提案 | 記事の差別化ポイント・競争優位性 |
| `target_persona` | ターゲットペルソナ | 記事のトーン・語りかけ方の決定 |
| `brand_slogan` | ブランドスローガン | 記事の方向性・価値観の反映 |
| `target_keywords` | SEO対象キーワード | 記事内での自然なキーワード組み込み |
| `industry_terms` | 業界専門用語 | 適切な専門用語の使用 |
| `avoid_terms` | 避けるべき用語 | 表現の制限・ブランドイメージ保護 |
| `target_area` | 対象エリア | 地域性を活かした内容の生成 |

### 2. style_guide_templates テーブル

記事スタイルのテンプレートを管理するテーブル。

```sql
CREATE TABLE style_guide_templates (
    id TEXT PRIMARY KEY DEFAULT (gen_random_uuid()::text),
    user_id TEXT NOT NULL,
    
    -- テンプレート基本情報
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    
    -- スタイル設定
    tone TEXT NOT NULL, -- 'formal', 'casual', 'friendly', 'professional'
    style TEXT NOT NULL, -- 'informative', 'persuasive', 'educational', 'conversational'
    target_audience TEXT NOT NULL, -- 'general', 'business', 'technical', 'beginner'
    
    -- 詳細ガイドライン
    writing_guidelines TEXT,
    vocabulary_preferences TEXT,
    sentence_structure_preferences TEXT,
    formatting_preferences TEXT,
    
    -- 使用禁止・推奨事項
    prohibited_words TEXT[],
    preferred_phrases TEXT[],
    brand_voice_keywords TEXT[],
    
    -- その他設定
    max_sentence_length INTEGER DEFAULT 50,
    paragraph_structure_preference TEXT,
    call_to_action_style TEXT,
    
    -- メタデータ
    template_metadata JSONB DEFAULT '{}',
    
    -- タイムスタンプ
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**主要フィールド説明:**

| フィールド | 説明 | 記事生成での活用方法 |
|-----------|------|-------------------|
| `tone` | トーン・調子 | 文章の雰囲気・親しみやすさの調整 |
| `style` | 文体 | 説明的・説得的・教育的・会話的の選択 |
| `target_audience` | 対象読者層 | 語彙・表現レベルの調整 |
| `writing_guidelines` | 執筆ガイドライン | 具体的な執筆方針・注意事項 |
| `vocabulary_preferences` | 語彙の好み | 使用する語彙・表現の傾向 |
| `prohibited_words` | 使用禁止ワード | NGワード・表現の除外 |
| `preferred_phrases` | 推奨フレーズ | ブランドらしい表現の積極使用 |
| `brand_voice_keywords` | ブランドボイスキーワード | 企業らしさを表現するキーワード |

## ArticleContext での統合

### 1. 会社情報の統合

ファイル位置: `/backend/app/domains/seo_article/context.py`

```python
@dataclass
class ArticleContext:
    # 会社情報 - 基本情報
    company_name: Optional[str] = None
    company_description: Optional[str] = None
    company_usp: Optional[str] = None
    company_website_url: Optional[str] = None
    company_target_persona: Optional[str] = None
    
    # 会社情報 - ブランディング
    company_brand_slogan: Optional[str] = None
    company_style_guide: Optional[str] = None # 文体、トンマナなど
    
    # 会社情報 - SEO・コンテンツ戦略
    company_target_keywords: Optional[str] = None
    company_industry_terms: Optional[str] = None
    company_avoid_terms: Optional[str] = None
    company_popular_articles: Optional[str] = None
    company_target_area: Optional[str] = None
```

### 2. スタイルテンプレートの統合

```python
@dataclass
class ArticleContext:
    # スタイルテンプレート関連
    style_template_id: Optional[str] = None # 使用するスタイルテンプレートのID
    style_template_settings: Dict[str, Any] = field(default_factory=dict) # スタイルテンプレートの設定内容
```

## データ取得・統合プロセス

### 1. 会社情報の取得

ファイル位置: `/backend/app/domains/company/service.py`

```python
class CompanyService:
    @staticmethod
    async def get_default_company(user_id: str) -> Optional[CompanyInfoResponse]:
        """デフォルト会社情報を取得"""
        try:
            result = supabase.from_("company_info")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("is_default", True)\
                .limit(1)\
                .execute()

            if not result.data:
                return None

            return CompanyInfoResponse(**result.data[0])

        except Exception as e:
            logger.error(f"Failed to get default company for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="デフォルト会社情報の取得に失敗しました"
            )
```

### 2. スタイルテンプレートの取得

ファイル位置: `/backend/app/domains/style_template/endpoints.py`

```python
@router.get("", response_model=List[StyleTemplateResponse])
async def get_style_templates(
    user_id: str = Depends(get_current_user_id_from_token)
):
    """Get all style templates accessible to the user"""
    try:
        # Build query to get user's personal templates
        query = supabase.table("style_guide_templates").select("*").eq("user_id", user_id)
        
        result = query.eq("is_active", True).order("is_default", desc=True).order("created_at", desc=True).execute()
        
        if result.data:
            return [StyleTemplateResponse(**template) for template in result.data]
        else:
            return []
            
    except Exception as e:
        logger.error(f"Error fetching style templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch style templates"
        )
```

### 3. ArticleContext への統合処理

記事生成APIで会社情報とスタイルテンプレートを統合：

```python
async def integrate_company_and_style_info(
    context: ArticleContext, 
    user_id: str,
    company_id: Optional[str] = None,
    style_template_id: Optional[str] = None
) -> ArticleContext:
    """会社情報とスタイルテンプレートをArticleContextに統合"""
    
    # 会社情報の取得・統合
    if company_id:
        company_info = await CompanyService.get_company_by_id(company_id, user_id)
    else:
        company_info = await CompanyService.get_default_company(user_id)
    
    if company_info:
        context.company_name = company_info.name
        context.company_description = company_info.description
        context.company_usp = company_info.usp
        context.company_website_url = str(company_info.website_url)
        context.company_target_persona = company_info.target_persona
        context.company_brand_slogan = company_info.brand_slogan
        context.company_target_keywords = company_info.target_keywords
        context.company_industry_terms = company_info.industry_terms
        context.company_avoid_terms = company_info.avoid_terms
        context.company_popular_articles = company_info.popular_articles
        context.company_target_area = company_info.target_area
    
    # スタイルテンプレートの取得・統合
    if style_template_id:
        # 指定されたテンプレートを取得
        style_template = await get_style_template_by_id(style_template_id, user_id)
        if style_template:
            context.style_template_id = style_template_id
            context.style_template_settings = {
                "tone": style_template.tone,
                "style": style_template.style,
                "target_audience": style_template.target_audience,
                "writing_guidelines": style_template.writing_guidelines,
                "vocabulary_preferences": style_template.vocabulary_preferences,
                "prohibited_words": style_template.prohibited_words,
                "preferred_phrases": style_template.preferred_phrases,
                "brand_voice_keywords": style_template.brand_voice_keywords,
                "max_sentence_length": style_template.max_sentence_length,
                "paragraph_structure_preference": style_template.paragraph_structure_preference
            }
    
    return context
```

## エージェントプロンプトでの活用

### 1. 会社情報コンテキストの構築

ファイル位置: `/backend/app/domains/seo_article/agents/definitions.py`

```python
def build_enhanced_company_context(ctx: ArticleContext) -> str:
    """拡張された会社情報コンテキストを構築"""
    if not hasattr(ctx, 'company_name') or not ctx.company_name:
        return "企業情報: 未設定（一般的な記事として作成）"
    
    company_parts = []
    
    # 基本情報
    company_parts.append(f"企業名: {ctx.company_name}")
    
    if hasattr(ctx, 'company_description') and ctx.company_description:
        company_parts.append(f"概要: {ctx.company_description}")
    
    if hasattr(ctx, 'company_usp') and ctx.company_usp:
        company_parts.append(f"USP・強み: {ctx.company_usp}")
    
    if hasattr(ctx, 'company_website_url') and ctx.company_website_url:
        company_parts.append(f"ウェブサイト: {ctx.company_website_url}")
    
    if hasattr(ctx, 'company_target_persona') and ctx.company_target_persona:
        company_parts.append(f"主要ターゲット: {ctx.company_target_persona}")
    
    # ブランディング情報
    if hasattr(ctx, 'company_brand_slogan') and ctx.company_brand_slogan:
        company_parts.append(f"ブランドスローガン: {ctx.company_brand_slogan}")
    
    # SEO・コンテンツ戦略
    if hasattr(ctx, 'company_target_keywords') and ctx.company_target_keywords:
        company_parts.append(f"重要キーワード: {ctx.company_target_keywords}")
    
    if hasattr(ctx, 'company_industry_terms') and ctx.company_industry_terms:
        company_parts.append(f"業界専門用語: {ctx.company_industry_terms}")
    
    if hasattr(ctx, 'company_avoid_terms') and ctx.company_avoid_terms:
        company_parts.append(f"避けるべき表現: {ctx.company_avoid_terms}")
    
    # コンテンツ参考情報
    if hasattr(ctx, 'company_popular_articles') and ctx.company_popular_articles:
        company_parts.append(f"人気記事参考: {ctx.company_popular_articles}")
    
    if hasattr(ctx, 'company_target_area') and ctx.company_target_area:
        company_parts.append(f"対象エリア: {ctx.company_target_area}")
    
    return "\n".join(company_parts)
```

### 2. スタイルガイドコンテキストの構築

```python
def build_style_context(ctx: ArticleContext) -> str:
    """スタイルガイドコンテキストを構築（カスタムテンプレート優先）"""
    if hasattr(ctx, 'style_template_settings') and ctx.style_template_settings:
        # カスタムスタイルテンプレートが設定されている場合
        style_parts = ["=== カスタムスタイルガイド ==="]
        
        if ctx.style_template_settings.get('tone'):
            style_parts.append(f"トーン・調子: {ctx.style_template_settings['tone']}")
        
        if ctx.style_template_settings.get('style'):
            style_parts.append(f"文体: {ctx.style_template_settings['style']}")
        
        if ctx.style_template_settings.get('approach'):
            style_parts.append(f"アプローチ・方針: {ctx.style_template_settings['approach']}")
        
        if ctx.style_template_settings.get('vocabulary_preferences'):
            style_parts.append(f"語彙・表現の指針: {ctx.style_template_settings['vocabulary_preferences']}")
        
        if ctx.style_template_settings.get('writing_guidelines'):
            style_parts.append(f"執筆ガイドライン: {ctx.style_template_settings['writing_guidelines']}")
        
        if ctx.style_template_settings.get('prohibited_words'):
            prohibited_words_str = ", ".join(ctx.style_template_settings['prohibited_words'])
            style_parts.append(f"使用禁止ワード: {prohibited_words_str}")
        
        if ctx.style_template_settings.get('preferred_phrases'):
            preferred_phrases_str = ", ".join(ctx.style_template_settings['preferred_phrases'])
            style_parts.append(f"推奨フレーズ: {preferred_phrases_str}")
        
        if ctx.style_template_settings.get('brand_voice_keywords'):
            brand_keywords_str = ", ".join(ctx.style_template_settings['brand_voice_keywords'])
            style_parts.append(f"ブランドボイスキーワード: {brand_keywords_str}")
        
        style_parts.append("")
        style_parts.append("**重要: 上記のカスタムスタイルガイドに従って執筆してください。従来のデフォルトスタイルは適用せず、このカスタム設定を優先してください。**")
        
        return "\n".join(style_parts)
    
    elif hasattr(ctx, 'company_style_guide') and ctx.company_style_guide:
        # 従来の会社スタイルガイドがある場合
        return f"=== 会社スタイルガイド ===\n文体・トンマナ: {ctx.company_style_guide}"
    
    else:
        # デフォルトスタイル
        return "=== デフォルトスタイルガイド ===\n親しみやすく分かりやすい文章で、読者に寄り添うトーン。専門用語を避け、日本の一般的なブログやコラムのような自然で人間味あふれる表現を使用。"
```

## 各エージェントでの活用例

### 1. テーマ提案エージェント

```python
def create_theme_instructions(base_prompt: str):
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        # 拡張された会社情報コンテキストを使用
        company_info_str = build_enhanced_company_context(ctx.context)
        
        full_prompt = f"""{base_prompt}

=== 企業情報 ===
{company_info_str}

**重要な注意事項:**
- 企業情報を活用して、その企業らしさが出るテーマを提案してください
- 企業のターゲット顧客や強みを反映した独自性のあるアプローチを心がけてください
- 企業の重要キーワードを自然に組み込んだテーマを考案してください
- 避けるべき表現がある場合は、それに配慮したテーマにしてください

あなたの応答は必ず `ThemeProposal` または `ClarificationNeeded` 型のJSON形式で出力してください。
"""
        return full_prompt
    return dynamic_instructions_func
```

### 2. セクション執筆エージェント

```python
def create_section_writer_instructions(base_prompt: str):
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        # 拡張された会社情報コンテキストを使用
        company_info_str = build_enhanced_company_context(ctx.context)
        
        # スタイルガイドコンテキストを構築
        style_guide_context = build_style_context(ctx.context)

        full_prompt = f"""{base_prompt}

=== 企業情報 ===
{company_info_str}

{style_guide_context}

--- **【最重要】執筆スタイルとトーンについて** ---
- 企業情報に記載された文体・トンマナ要件も必ず遵守してください。
- スタイルガイドで指定された禁止ワードは絶対に使用しないでください。
- 推奨フレーズやブランドボイスキーワードを積極的に活用してください。
- 企業の強み（USP）や専門性を自然に表現に織り込んでください。
---

--- 執筆ルール ---
1. 企業の業界専門用語を適切に使用し、避けるべき表現は使用しないでください。
2. 企業の対象エリアが設定されている場合は、地域性を活かした内容を心がけてください。
3. 企業のウェブサイトURLやブランドスローガンを必要に応じて自然に言及してください。
4. スタイルガイドで設定された文字数制限や段落構造の好みに従ってください。
---
"""
        return full_prompt
    return dynamic_instructions_func
```

### 3. 編集エージェント

```python
def create_editor_instructions(base_prompt: str):
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        # 拡張された会社情報コンテキストを使用
        company_info_str = build_enhanced_company_context(ctx.context)
        
        # スタイルガイドコンテキストを構築
        style_guide_context = build_style_context(ctx.context)

        full_prompt = f"""{base_prompt}

=== 企業情報 ===
{company_info_str}

{style_guide_context}

**重要:**
- チェックポイント:
    - 指示されたトーンとスタイルガイドの遵守 (**自然さ、親しみやすさ重視**)
    - 企業情報との整合性（USP、強み、対象エリア等の正確な反映）
    - スタイルガイドの禁止ワード・推奨表現の遵守
    - 企業らしさの表現（ブランドボイス、専門性の適切な表現）
    - 業界用語の適切な使用と避けるべき表現の除外
    - 対象読者層に適した語彙・表現レベル
---
"""
        return full_prompt
    return dynamic_instructions_func
```

## 実装パターンと最適化

### 1. キャッシュ戦略

会社情報とスタイルテンプレートは変更頻度が低いため、効率的なキャッシュを実装：

```python
from functools import lru_cache
from typing import Optional
import asyncio

class CompanyInfoCache:
    def __init__(self):
        self._cache = {}
        self._cache_timeout = 3600  # 1時間
    
    async def get_default_company_cached(self, user_id: str) -> Optional[CompanyInfoResponse]:
        """デフォルト会社情報をキャッシュ付きで取得"""
        cache_key = f"default_company_{user_id}"
        
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_timeout:
                return cached_data
        
        # キャッシュにないか期限切れの場合、DBから取得
        company_info = await CompanyService.get_default_company(user_id)
        
        if company_info:
            self._cache[cache_key] = (company_info, time.time())
        
        return company_info
    
    def invalidate_user_cache(self, user_id: str):
        """ユーザーのキャッシュを無効化"""
        keys_to_remove = [key for key in self._cache if user_id in key]
        for key in keys_to_remove:
            del self._cache[key]

# グローバルキャッシュインスタンス
company_cache = CompanyInfoCache()
```

### 2. 動的プロンプト最適化

プロンプト生成処理の最適化：

```python
def optimize_prompt_generation(ctx: ArticleContext) -> Dict[str, str]:
    """プロンプト生成の最適化"""
    optimized_contexts = {}
    
    # 会社情報の事前構築
    if ctx.company_name:
        company_context = build_enhanced_company_context(ctx)
        # 長すぎる場合は要約
        if len(company_context) > 1000:
            company_context = summarize_company_context(company_context)
        optimized_contexts['company'] = company_context
    
    # スタイルガイドの事前構築  
    style_context = build_style_context(ctx)
    optimized_contexts['style'] = style_context
    
    return optimized_contexts

def summarize_company_context(full_context: str) -> str:
    """会社情報コンテキストを要約"""
    # 重要度の高い情報を優先的に保持
    lines = full_context.split('\n')
    high_priority = []
    medium_priority = []
    
    for line in lines:
        if any(keyword in line for keyword in ['企業名:', 'USP・強み:', 'ブランドスローガン:']):
            high_priority.append(line)
        elif any(keyword in line for keyword in ['重要キーワード:', '避けるべき表現:']):
            high_priority.append(line)
        else:
            medium_priority.append(line)
    
    # 高優先度は全て含め、中優先度は必要に応じて削る
    result = high_priority + medium_priority[:5]  # 上位5項目まで
    return '\n'.join(result)
```

### 3. バリデーション機能

設定内容の妥当性チェック：

```python
class StyleGuideValidator:
    @staticmethod
    def validate_style_settings(settings: Dict[str, Any]) -> List[str]:
        """スタイル設定の妥当性をチェック"""
        errors = []
        
        # 必須フィールドの確認
        required_fields = ['tone', 'style', 'target_audience']
        for field in required_fields:
            if not settings.get(field):
                errors.append(f"必須フィールド '{field}' が設定されていません")
        
        # 禁止ワードと推奨フレーズの重複チェック
        prohibited = set(settings.get('prohibited_words', []))
        preferred = set(settings.get('preferred_phrases', []))
        conflicts = prohibited.intersection(preferred)
        if conflicts:
            errors.append(f"禁止ワードと推奨フレーズに重複があります: {list(conflicts)}")
        
        # 文字数制限の妥当性
        max_length = settings.get('max_sentence_length', 50)
        if max_length < 10 or max_length > 200:
            errors.append("最大文字数は10-200の範囲で設定してください")
        
        return errors

class CompanyInfoValidator:
    @staticmethod
    def validate_company_info(company_info: Dict[str, Any]) -> List[str]:
        """会社情報の妥当性をチェック"""
        errors = []
        
        # URL形式の確認
        if company_info.get('website_url'):
            if not company_info['website_url'].startswith(('http://', 'https://')):
                errors.append("ウェブサイトURLは http:// または https:// で始まる必要があります")
        
        # キーワードの重複チェック
        target_keywords = company_info.get('target_keywords', '')
        avoid_terms = company_info.get('avoid_terms', '')
        if target_keywords and avoid_terms:
            target_set = set(target_keywords.lower().split(','))
            avoid_set = set(avoid_terms.lower().split(','))
            conflicts = target_set.intersection(avoid_set)
            if conflicts:
                errors.append(f"重要キーワードと避けるべき表現に重複があります: {list(conflicts)}")
        
        return errors
```

## 運用・保守に関する考慮事項

### 1. 設定変更の影響範囲

会社情報やスタイルガイドの変更は、進行中の記事生成プロセスに影響する可能性があります：

```python
async def handle_company_info_update(user_id: str, company_id: str):
    """会社情報更新時の処理"""
    
    # 進行中のプロセスがあるかチェック
    active_processes = await get_active_generation_processes(user_id)
    
    if active_processes:
        logger.warning(f"User {user_id} has {len(active_processes)} active generation processes")
        
        # 各プロセスにアラートを送信
        for process in active_processes:
            await send_process_alert(
                process.id,
                "company_info_updated",
                "会社情報が更新されました。現在の生成プロセスに反映されない可能性があります。"
            )
    
    # キャッシュを無効化
    company_cache.invalidate_user_cache(user_id)
    
    logger.info(f"Company info updated for user {user_id}, company {company_id}")
```

### 2. パフォーマンス監視

プロンプト生成処理のパフォーマンス監視：

```python
import time
from functools import wraps

def monitor_prompt_generation(func):
    """プロンプト生成処理の監視デコレータ"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            
            # 成功時のメトリクス記録
            duration = time.time() - start_time
            logger.info(f"Prompt generation completed: {func.__name__} took {duration:.3f}s")
            
            return result
            
        except Exception as e:
            # エラー時のメトリクス記録
            duration = time.time() - start_time
            logger.error(f"Prompt generation failed: {func.__name__} failed after {duration:.3f}s: {e}")
            raise
    
    return wrapper

@monitor_prompt_generation
async def generate_enhanced_prompt(ctx: ArticleContext, agent_type: str) -> str:
    """拡張プロンプト生成"""
    optimized_contexts = optimize_prompt_generation(ctx)
    
    # エージェントタイプに応じたプロンプト生成
    if agent_type == "theme":
        return create_theme_instructions_with_context(ctx, optimized_contexts)
    elif agent_type == "section_writer":
        return create_section_writer_instructions_with_context(ctx, optimized_contexts)
    # 他のエージェントタイプ...
```

### 3. A/Bテスト対応

異なるスタイル設定での効果測定：

```python
class StyleTestManager:
    def __init__(self):
        self.test_variants = {}
    
    async def create_style_test(
        self, 
        user_id: str, 
        test_name: str, 
        variant_a: Dict[str, Any], 
        variant_b: Dict[str, Any],
        traffic_split: float = 0.5
    ):
        """スタイルA/Bテストを作成"""
        test_id = f"{user_id}_{test_name}_{int(time.time())}"
        
        self.test_variants[test_id] = {
            "user_id": user_id,
            "test_name": test_name,
            "variant_a": variant_a,
            "variant_b": variant_b,
            "traffic_split": traffic_split,
            "created_at": time.time(),
            "results": {"a": [], "b": []}
        }
        
        return test_id
    
    def get_variant_for_user(self, test_id: str, session_id: str) -> str:
        """ユーザーセッションに対するバリアントを決定"""
        # セッションIDを基にしたハッシュで一貫した振り分け
        import hashlib
        hash_value = int(hashlib.md5(session_id.encode()).hexdigest(), 16)
        
        test_info = self.test_variants.get(test_id)
        if not test_info:
            return "a"  # デフォルト
        
        return "a" if (hash_value % 100) < (test_info["traffic_split"] * 100) else "b"
    
    async def record_result(self, test_id: str, variant: str, metrics: Dict[str, Any]):
        """テスト結果を記録"""
        if test_id in self.test_variants:
            self.test_variants[test_id]["results"][variant].append({
                "timestamp": time.time(),
                "metrics": metrics
            })
```

## まとめ

会社情報とスタイルガイドの活用システムは、以下の特徴を持ちます：

### 1. 統合的なデータ管理
- 会社情報とスタイルテンプレートの一元管理
- ArticleContextでの統合的な保持
- キャッシュ機能による効率的なデータアクセス

### 2. 柔軟なプロンプト生成
- エージェントごとの最適化されたプロンプト
- 動的コンテキスト構築による関連性の向上
- 階層的な設定（カスタム > 会社 > デフォルト）

### 3. 品質保証機能
- 設定内容のバリデーション
- 進行中プロセスへの影響管理
- パフォーマンス監視とA/Bテスト対応

この仕組みにより、企業固有の価値観やブランディングが記事生成プロセス全体に一貫して反映され、高品質で企業らしいコンテンツの自動生成を実現します。