# 記事生成システム - 完全フロー仕様書

## 概要

この文書は、WebSocketからSupabase Realtimeに移行した記事生成システムの完全なフローを詳細に記述します。

## システムアーキテクチャ

### 構成要素
- **フロントエンド**: Next.js + TypeScript + Supabase Realtime
- **バックエンド**: FastAPI + BackgroundTasks + Supabase
- **データベース**: Supabase PostgreSQL + Realtime subscriptions
- **AIエージェント**: OpenAI Agents SDK

### データフロー
```
ユーザー操作 → HTTP API → BackgroundTasks → AIエージェント → データベース更新 → Supabase Realtime → フロントエンドUI更新
```

## 詳細フロー仕様

### 1. 初期化フェーズ

#### 1.1 プロセス開始
**ユーザー操作**: 新規記事生成ボタンクリック

**フロントエンド処理**:
```typescript
// NewArticleStartPage.tsx
POST /api/proxy/articles/generation/start
Headers: Authorization: Bearer <clerk_token>
Body: {
  initial_keywords: string[],
  target_age_group: string,
  persona_type: string,
  custom_persona: string,
  target_length: number,
  company_name: string,
  company_description: string,
  company_style_guide: string,
  image_mode: boolean,
  image_settings: object
}
```

**バックエンド処理**:
```python
# endpoints.py: /generation/start
1. create_generation_process() - ArticleContextの作成
2. save_context_to_db() - データベースへの初期保存
3. publish_process_created_event() - Realtime通知
4. background_tasks.add_task() - バックグラウンドタスク開始
5. return { process_id, realtime_channel, status }
```

**データベース更新**:
```sql
INSERT INTO generated_articles_state (
  id, user_id, organization_id, status,
  current_step_name, article_context,
  process_metadata, created_at
) VALUES (
  process_id, user_id, org_id, 'in_progress',
  'start', initial_context, metadata, now()
)
```

**Realtime通知**:
```json
{
  "event_type": "process_created",
  "event_data": {
    "process_id": "uuid",
    "status": "in_progress",
    "current_step": "start",
    "message": "Process created successfully"
  }
}
```

**フロントエンド状態更新**:
```typescript
// useArticleGenerationRealtime.ts
case 'process_created':
  newState.currentStep = 'start'
  redirect to /seo/generate/new-article/{process_id}
```

### 2. キーワード分析フェーズ

#### 2.1 キーワード分析実行
**バックグラウンドタスク開始**: `run_generation_background_task()`

**処理ステップ**:
```python
# background_task_manager.py
1. load_context_from_db() - コンテキスト読み込み
2. execute_single_step() - 'keyword_analyzing'実行
3. KeywordAnalysisAgent.run() - キーワード分析
4. save_context_to_db() - 結果保存
5. publish_step_events() - Realtime通知
```

**AIエージェント実行**:
```python
# KeywordAnalysisAgent
Input: initial_keywords, target_age_group
Output: {
  "analyzed_keywords": ["keyword1", "keyword2"],
  "search_intent": "informational",
  "competition_level": "medium",
  "seo_opportunities": ["opportunity1", "opportunity2"]
}
```

**データベース更新**:
```sql
UPDATE generated_articles_state 
SET article_context = jsonb_set(
  article_context, 
  '{analyzed_keywords}', 
  analyzed_result
),
current_step_name = 'keyword_analyzed',
updated_at = now()
WHERE id = process_id
```

**Realtime通知**:
```json
[
  {
    "event_type": "step_started",
    "event_data": { "step_name": "keyword_analyzing" }
  },
  {
    "event_type": "step_completed", 
    "event_data": { "step_name": "keyword_analyzing", "next_step": "persona_generating" }
  }
]
```

**フロントエンド状態更新**:
```typescript
case 'step_started':
  newState.currentStep = 'keyword_analyzing'
  updateStepStatus(newState, 'keyword_analyzing', 'in_progress')

case 'step_completed':
  updateStepStatus(newState, 'keyword_analyzing', 'completed')
```

### 3. ペルソナ生成フェーズ

#### 3.1 ペルソナ生成実行
**処理ステップ**:
```python
# PersonaGeneratorAgent実行
1. generate_detailed_personas() - 複数ペルソナ生成
2. context.generated_detailed_personas = personas
3. set_user_input_required('select_persona') - ユーザー選択待ち
```

**AIエージェント出力**:
```json
{
  "generated_detailed_personas": [
    "45歳の建築会社経営者。新築とリフォームを手掛ける...",
    "42歳の経理戦略チームリーダー。社内の経費削減と効率化を推進...",
    "47歳の販売促進担当。Webを活用した集客に熱心で..."
  ]
}
```

**データベース更新**:
```sql
UPDATE generated_articles_state 
SET article_context = jsonb_set(
  article_context, 
  '{generated_detailed_personas}', 
  personas_array
),
current_step_name = 'persona_generated',
status = 'user_input_required',
process_metadata = jsonb_build_object('input_type', 'select_persona'),
updated_at = now()
WHERE id = process_id
```

**Realtime通知**:
```json
[
  {
    "event_type": "step_completed",
    "event_data": { "step_name": "persona_generating" }
  },
  {
    "event_type": "user_input_required",
    "event_data": {
      "input_type": "select_persona",
      "data": { "personas": [...] }
    }
  }
]
```

**フロントエンド状態更新**:
```typescript
case 'user_input_required':
  newState.isWaitingForInput = true
  newState.inputType = 'select_persona'
  newState.personas = personas.map((p, i) => ({id: i, description: p}))
```

#### 3.2 ペルソナ選択処理
**ユーザー操作**: ペルソナ選択ボタンクリック

**フロントエンド処理**:
```typescript
// CompactUserInteraction.tsx
selectPersona(index) ->
POST /api/proxy/articles/generation/{process_id}/user-input
Body: {
  response_type: 'select_persona',
  payload: { selected_id: index }
}
```

**バックエンド処理**:
```python
# endpoints.py: /{process_id}/user-input
1. process_user_input() - 入力データ処理
2. apply_user_input_to_context() - コンテキスト更新
3. resolve_user_input() - 待機状態解除
4. continue_generation_after_input() - 生成再開
```

**データベース更新**:
```sql
-- ユーザー入力記録
UPDATE generated_articles_state 
SET article_context = jsonb_set(
  article_context, 
  '{selected_detailed_persona}', 
  selected_persona
),
status = 'in_progress',
process_metadata = null,
interaction_history = array_append(
  interaction_history,
  jsonb_build_object('action', 'input_resolved', 'response', user_input)
),
updated_at = now()
WHERE id = process_id
```

**Realtime通知**:
```json
{
  "event_type": "user_input_resolved",
  "event_data": {
    "resolved_at": "2025-01-27T14:03:14.545012+00:00",
    "user_response": { "response_type": "select_persona", "payload": {...} }
  }
}
```

### 4. テーマ生成フェーズ

#### 4.1 テーマ生成・選択
**処理ステップ**: ペルソナ選択と同様のパターン

**AIエージェント出力**:
```json
{
  "generated_themes": [
    {
      "title": "生成AIで始めるWeb集客効率化入門",
      "description": "建築業界向けの実践的なAI活用ガイド",
      "keywords": ["生成AI", "Web集客", "建築業"]
    }
  ]
}
```

### 5. リサーチフェーズ

#### 5.1 リサーチ計画生成
**AIエージェント実行**: `ResearchPlannerAgent`

**出力データ**:
```json
{
  "research_plan": {
    "topic": "建築会社経営者向け：生成AIで始めるWeb集客効率化入門",
    "queries": [
      "生成AI 初心者向け Web集客 建築業 チュートリアル",
      "生成AIツール 比較 料金 無料プラン 建築業 Web集客", 
      "生成AI 法的リスク 著作権 Web集客 建築業 事例"
    ]
  }
}
```

#### 5.2 リサーチ実行
**処理ステップ**:
```python
# ResearchExecutorAgent
for query in research_plan.queries:
    1. search_web(query) - Web検索実行
    2. publish_progress_event() - 進捗通知
    3. analyze_results() - 結果分析
    4. store_research_data() - データ蓄積
```

**Realtime通知**:
```json
{
  "event_type": "research_progress",
  "event_data": {
    "query": "生成AI 初心者向け Web集客 建築業 チュートリアル",
    "current_query": 1,
    "total_queries": 3,
    "progress_percentage": 33
  }
}
```

**フロントエンド状態更新**:
```typescript
case 'research_progress':
  newState.researchProgress = {
    currentQuery: event.event_data.current_query,
    totalQueries: event.event_data.total_queries,
    query: event.event_data.query
  }
```

### 6. アウトライン生成フェーズ

#### 6.1 アウトライン生成
**AIエージェント実行**: `OutlineGeneratorAgent`

**入力データ**:
```json
{
  "selected_persona": "45歳の建築会社経営者...",
  "selected_theme": {...},
  "research_results": [...],
  "research_plan": {...}
}
```

**出力データ**:
```json
{
  "generated_outline": {
    "title": "生成AIで始めるWeb集客効率化入門",
    "sections": [
      {
        "heading": "1. 生成AIとは？建築業界での活用メリット",
        "subheadings": ["1.1 基本概念", "1.2 業界特有の利点"],
        "key_points": ["効率化", "コスト削減"]
      },
      {
        "heading": "2. Web集客における生成AI活用法",
        "subheadings": ["2.1 コンテンツ作成", "2.2 SEO対策"],
        "key_points": ["記事作成", "キーワード最適化"]
      }
    ]
  }
}
```

#### 6.2 アウトライン承認待ち
**データベース更新**:
```sql
UPDATE generated_articles_state 
SET article_context = jsonb_set(
  article_context, 
  '{generated_outline}', 
  outline_data
),
current_step_name = 'outline_generated',
status = 'user_input_required',
process_metadata = jsonb_build_object('input_type', 'approve_outline')
WHERE id = process_id
```

**フロントエンド状態更新**:
```typescript
// article_context.generated_outline を context.outline として設定
const outlineData = context.outline || context.generated_outline
if (outlineData) {
  newState.outline = outlineData
}
```

### 7. セクション執筆フェーズ

#### 7.1 セクション順次執筆
**処理ステップ**:
```python
# SectionWriterAgent を各セクションに対して実行
for section_index, section in enumerate(outline.sections):
    1. prepare_section_context() - セクション固有データ準備
    2. SectionWriterAgent.run() - セクション執筆
    3. save_section_html() - HTMLコンテンツ保存
    4. publish_section_progress() - 進捗通知
    5. publish_section_completed() - セクション完了通知
```

**AIエージェント入力**:
```json
{
  "section_outline": {
    "heading": "1. 生成AIとは？建築業界での活用メリット",
    "subheadings": [...],
    "key_points": [...]
  },
  "research_context": [...],
  "persona": "45歳の建築会社経営者...",
  "style_guide": "..."
}
```

**AIエージェント出力**:
```html
<section>
  <h2>1. 生成AIとは？建築業界での活用メリット</h2>
  <p>建築業界において、生成AI（Generative AI）は...</p>
  <h3>1.1 基本概念</h3>
  <p>生成AIは、テキスト、画像、音声などのコンテンツを...</p>
</section>
```

**データベース更新**:
```sql
UPDATE generated_articles_state 
SET article_context = jsonb_set(
  article_context, 
  '{generated_sections_html}', 
  sections_array
),
article_context = jsonb_set(
  article_context,
  '{current_section_index}',
  section_index
),
updated_at = now()
WHERE id = process_id
```

**Realtime通知**:
```json
[
  {
    "event_type": "section_writing_progress",
    "event_data": {
      "current_section": 1,
      "total_sections": 7,
      "section_heading": "1. 生成AIとは？"
    }
  },
  {
    "event_type": "section_completed",
    "event_data": {
      "section_index": 0,
      "section_heading": "1. 生成AIとは？",
      "section_content": "<section>...</section>"
    }
  }
]
```

**フロントエンド状態更新**:
```typescript
case 'section_writing_progress':
  newState.sectionsProgress = {
    currentSection: event.event_data.current_section,
    totalSections: event.event_data.total_sections,
    sectionHeading: event.event_data.section_heading
  }

case 'section_completed':
  newState.completedSections.push({
    index: event.event_data.section_index,
    heading: event.event_data.section_heading,
    content: event.event_data.section_content
  })
  newState.generatedContent = newState.completedSections
    .sort((a, b) => a.index - b.index)
    .map(section => section.content)
    .join('\n\n')
```

### 8. 最終編集フェーズ

#### 8.1 EditorAgent実行
**処理ステップ**:
```python
# EditorAgent による最終編集
1. compile_full_article() - 全セクション統合
2. EditorAgent.run() - 文章校正・構成調整
3. generate_final_html() - 最終HTML生成
4. save_final_article() - 完成記事保存
```

**AIエージェント入力**:
```json
{
  "full_draft_html": "<article>...</article>",
  "target_persona": "45歳の建築会社経営者...",
  "style_requirements": "...",
  "seo_keywords": [...]
}
```

**AIエージェント出力**:
```html
<!DOCTYPE html>
<article>
  <header>
    <h1>生成AIで始めるWeb集客効率化入門</h1>
    <meta name="description" content="建築会社経営者向けの実践的AI活用ガイド">
  </header>
  <section>...</section>
  <section>...</section>
  ...
</article>
```

**データベース更新**:
```sql
UPDATE generated_articles_state 
SET article_context = jsonb_set(
  article_context, 
  '{final_article_html}', 
  final_html
),
current_step_name = 'completed',
status = 'completed',
updated_at = now()
WHERE id = process_id
```

### 9. 記事保存・完了フェーズ

#### 9.1 記事エンティティ作成
**処理ステップ**:
```python
# save_final_article_with_placeholders()
1. extract_metadata() - タイトル、概要抽出
2. create_article_record() - articlesテーブルに保存
3. extract_image_placeholders() - 画像プレースホルダー抽出
4. update_process_status() - プロセス完了状態更新
```

**データベース更新**:
```sql
-- 記事エンティティ作成
INSERT INTO articles (
  id, user_id, title, content, 
  status, metadata, created_at
) VALUES (
  article_id, user_id, title, final_html,
  'completed', metadata, now()
)

-- プロセス状態更新
UPDATE generated_articles_state 
SET article_id = article_id,
    status = 'completed',
    current_step_name = 'completed'
WHERE id = process_id
```

**Realtime通知**:
```json
{
  "event_type": "generation_completed",
  "event_data": {
    "article_id": "e956cb86-19c4-4a2d-a146-4d9d631c9187",
    "title": "生成AIで始めるWeb集客効率化入門",
    "final_html_content": "<article>...</article>",
    "status": "completed"
  }
}
```

**フロントエンド状態更新**:
```typescript
case 'generation_completed':
case 'article_created':
case 'article_saved':
  newState.currentStep = 'completed'
  newState.finalArticle = {
    title: articleData.title || 'Generated Article',
    content: articleData.final_html_content || newState.generatedContent
  }
  newState.articleId = articleData.article_id || articleData.id
  newState.steps = newState.steps.map(step => ({
    ...step,
    status: 'completed'
  }))
```

#### 9.2 自動ページ遷移
**フロントエンド処理**:
```typescript
// GenerationProcessPage.tsx
useEffect(() => {
  if (state.currentStep === 'completed' && state.articleId && !state.error) {
    const timer = setTimeout(() => {
      router.push(`/seo/generate/edit-article/${state.articleId}`)
    }, 2000)
    return () => clearTimeout(timer)
  }
}, [state.currentStep, state.articleId, state.error, router])
```

## データ構造仕様

### ArticleContext構造
```typescript
interface ArticleContext {
  // 基本設定
  user_id: string
  process_id: string
  image_mode: boolean
  current_step: string
  
  // 入力データ
  initial_keywords: string[]
  target_age_group: string
  persona_type: string
  custom_persona: string
  target_length: number
  company_name: string
  company_description: string
  
  // 生成データ
  generated_detailed_personas: string[]
  selected_detailed_persona: string
  generated_themes: ThemeOption[]
  selected_theme: ThemeOption
  research_plan: ResearchPlan
  research_query_results: ResearchResult[]
  generated_outline: Outline
  generated_sections_html: string[]
  final_article_html: string
  
  // 進捗管理
  current_section_index: number
  sections_progress: SectionsProgress
  research_progress: ResearchProgress
}
```

### データベーステーブル構造

#### generated_articles_state
```sql
CREATE TABLE generated_articles_state (
  id UUID PRIMARY KEY,
  user_id TEXT NOT NULL,
  organization_id UUID,
  status TEXT NOT NULL, -- 'in_progress', 'user_input_required', 'completed', 'error'
  current_step_name TEXT, -- 'start', 'keyword_analyzing', 'persona_generated', etc.
  article_context JSONB NOT NULL,
  process_metadata JSONB,
  interaction_history JSONB[],
  article_id UUID REFERENCES articles(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
)
```

#### process_events (Supabase Realtime)
```sql
CREATE TABLE process_events (
  id UUID PRIMARY KEY,
  process_id UUID NOT NULL,
  event_type TEXT NOT NULL,
  event_data JSONB NOT NULL,
  event_sequence BIGSERIAL,
  event_category TEXT,
  event_source TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
)
```

#### articles
```sql
CREATE TABLE articles (
  id UUID PRIMARY KEY,
  user_id TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  status TEXT NOT NULL,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
)
```

## エラーハンドリング

### エラー発生時の処理
```python
# 任意のステップでエラー発生時
try:
    # AI agent execution
    result = agent.run(input_data)
except Exception as e:
    # エラー状態更新
    await update_process_status(
        process_id=process_id,
        status="error", 
        metadata={"error_message": str(e)}
    )
    
    # Realtime通知
    await publish_error_event(process_id, str(e))
    
    # バックグラウンドタスク終了
    raise
```

### フロントエンドエラー表示
```typescript
case 'generation_error':
  newState.currentStep = 'error'
  newState.error = event.event_data.error_message
  newState.isWaitingForInput = false
  
  // エラーUIコンポーネント表示
  <ErrorRecoveryActions 
    error={state.error}
    onRetry={handleRetry}
    onRestart={handleRestart}
  />
```

## パフォーマンス考慮事項

### バックグラウンド処理
- FastAPI BackgroundTasksによる非同期実行
- プロセス間の独立性確保
- リソース使用量の制限

### Realtime通知最適化
- イベントのバッチ処理
- 不要なイベントのフィルタリング
- クライアント側キャッシュ活用

### データベース最適化
- article_contextのJSONB効率的更新
- インデックス最適化
- 古いイベントデータの定期削除

## 監視・ロギング

### ログ収集
```python
# 各ステップで詳細ログ記録
logger.info(f"🎯 [STEP] Starting {step_name} for process {process_id}")
logger.info(f"✅ [STEP] Completed {step_name}")
logger.error(f"💥 [STEP] Error in {step_name}: {error}")
```

### メトリクス監視
- 各ステップの実行時間
- エラー発生率
- ユーザー入力待ち時間
- 全体処理時間

この文書により、記事生成システムの完全なフローが詳細に把握できます。