# SEO記事生成におけるデータベース更新フロー

## 概要

本文書では、SEO記事生成プロセス中のデータベース更新フローについて詳細に解説します。各ステップ完了時に`ProcessPersistenceService`を通じて`generated_articles_state`テーブルの`article_context`がどのように更新・永続化されるか、そして最終的に`articles`テーブルに完成記事が保存されるまでのデータフローを詳述します。

## システム構成

```
┌─────────────────────────┐
│  記事生成プロセス開始   │
├─────────────────────────┤
│  • API呼び出し          │
│  • ArticleContext生成   │
└─────────────────────────┘
           │
           ▼
┌─────────────────────────┐
│  初期状態DB保存         │
├─────────────────────────┤
│  • generated_articles_  │
│    state テーブル        │
│  • process_events       │
│    テーブル             │
└─────────────────────────┘
           │
           ▼
┌─────────────────────────┐
│  各ステップ実行ループ   │
├─────────────────────────┤
│  • エージェント実行     │
│  • ArticleContext更新   │
│  • 永続化サービス呼び出し │
└─────────────────────────┘
           │
           ▼
┌─────────────────────────┐
│  ステップ完了後の更新   │
├─────────────────────────┤
│  • article_context更新  │
│  • process_events追加   │
│  • Realtime通知        │
└─────────────────────────┘
           │
           ▼
┌─────────────────────────┐
│  最終完成時の処理       │
├─────────────────────────┤
│  • articles テーブル    │
│    保存                 │
│  • 画像プレースホルダー │
│    更新                 │
└─────────────────────────┘
```

## 中核サービス: ProcessPersistenceService

### 1. 基本構造

ファイル位置: `/backend/app/domains/seo_article/services/_process_persistence_service.py`

```python
class ProcessPersistenceService:
    """プロセスの永続化とデータベース操作を担当するクラス"""
    
    def __init__(self, service):
        self.service = service  # ArticleGenerationServiceへの参照
```

### 2. 主要メソッド

| メソッド名 | 目的 | 呼び出しタイミング |
|-----------|------|------------------|
| `save_context_to_db()` | ArticleContextをDBに保存 | 各ステップ完了時 |
| `load_context_from_db()` | DBからArticleContextを復元 | プロセス再開時 |
| `update_process_status()` | プロセス状態を更新 | 状態変更時 |
| `add_step_to_history()` | ステップ履歴を追加 | ステップ完了時 |

## データベース更新フローの詳細

### 1. 初期プロセス作成

#### 1.1 新規プロセス作成

```python
async def save_context_to_db(self, context: ArticleContext, process_id: Optional[str] = None, user_id: Optional[str] = None, organization_id: Optional[str] = None) -> str:
    """Save ArticleContext to database and return process_id"""
    
    if not process_id:
        # 新規プロセス作成
        # Get default flow ID for new states
        flow_result = supabase.table("article_generation_flows").select("id").eq("name", "Default SEO Article Generation").eq("is_template", True).execute()
        
        if not flow_result.data:
            raise Exception("Default flow template not found")
        
        default_flow_id = flow_result.data[0]["id"]
        
        # Create new state
        state_data = {
            "flow_id": default_flow_id,
            "user_id": user_id,
            "organization_id": organization_id,
            "status": map_step_to_status(context.current_step),
            "article_context": context_dict,
            "generated_content": {}
        }
        
        result = supabase.table("generated_articles_state").insert(state_data).execute()
        if result.data:
            return result.data[0]["id"]
```

#### 1.2 ステップ状態マッピング

```python
def map_step_to_status(step: str) -> str:
    """Map context step to valid generation_status enum value"""
    if step in ["start", "keyword_analyzing", "keyword_analyzed", "persona_generating", 
               "persona_selected", "theme_generating", "theme_selected", "research_planning", 
               "research_plan_approved", "researching", "research_synthesizing", 
               "outline_generating", "writing_sections", "editing"]:
        return "in_progress"
    elif step == "completed":
        return "completed"
    elif step == "error":
        return "error"
    elif step in ["persona_generated", "theme_proposed", "research_plan_generated", 
                 "outline_generated"]:
        return "user_input_required"
    else:
        return "in_progress"  # Default fallback
```

### 2. 各ステップでの更新プロセス

#### 2.1 ArticleContextのシリアライゼーション

```python
def safe_serialize_value(value):
    """Recursively serialize any object to JSON-serializable format"""
    if value is None:
        return None
    elif isinstance(value, (str, int, float, bool)):
        return value
    elif isinstance(value, list):
        return [safe_serialize_value(item) for item in value]
    elif isinstance(value, dict):
        return {k: safe_serialize_value(v) for k, v in value.items()}
    elif hasattr(value, "model_dump"):
        # Pydantic models
        return value.model_dump()
    elif hasattr(value, "__dict__"):
        # Regular objects with attributes
        return {k: safe_serialize_value(v) for k, v in value.__dict__.items()}
    else:
        # Fallback to string representation
        return str(value)

# Convert context to dict (excluding WebSocket and asyncio objects)
context_dict = {}
for key, value in context.__dict__.items():
    if key not in ["websocket", "user_response_event"]:
        try:
            context_dict[key] = safe_serialize_value(value)
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to serialize {key}: {e}. Using string representation.[/yellow]")
            context_dict[key] = str(value)
```

#### 2.2 既存プロセスの更新

```python
if process_id:
    # Update existing state
    update_data = {
        "article_context": context_dict,
        "status": map_step_to_status(context.current_step),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Add error message if in error state
    if context.current_step == "error" and hasattr(context, 'error_message'):
        update_data["error_message"] = context.error_message
    
    supabase.table("generated_articles_state").update(update_data).eq("id", process_id).execute()
    return process_id
```

### 3. 自動トリガーによるプロセスイベント生成

データベースレベルでトリガーが設定されており、`generated_articles_state`の更新時に自動的に`process_events`が生成されます。

#### 3.1 データベース関数

ファイル位置: `/frontend/supabase/migrations/*.sql` (関連マイグレーション)

```sql
-- プロセス状態更新時に自動的にイベントを発行
CREATE OR REPLACE FUNCTION publish_process_event()
RETURNS TRIGGER AS $$
DECLARE
    event_data JSONB;
    channel_name TEXT;
    next_sequence INTEGER;
    event_type_name TEXT;
BEGIN
    -- チャンネル名決定
    channel_name := 'process_' || NEW.id::text;
    
    -- イベントタイプ決定
    IF TG_OP = 'INSERT' THEN
        event_type_name := 'process_created';
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.status IS DISTINCT FROM NEW.status THEN
            event_type_name := 'status_changed';
        ELSIF OLD.current_step_name IS DISTINCT FROM NEW.current_step_name THEN
            event_type_name := 'step_changed';
        ELSE
            event_type_name := 'process_updated';
        END IF;
    ELSE
        event_type_name := 'process_changed';
    END IF;
    
    -- イベントデータ構築
    event_data := jsonb_build_object(
        'process_id', NEW.id,
        'status', NEW.status,
        'current_step', NEW.current_step_name,
        'progress_percentage', NEW.progress_percentage,
        'is_waiting_for_input', NEW.is_waiting_for_input,
        'input_type', NEW.input_type,
        'updated_at', NEW.updated_at,
        'event_type', event_type_name,
        'user_id', NEW.user_id,
        'article_context', NEW.article_context
    );
    
    -- 次のシーケンス番号を取得
    SELECT COALESCE(MAX(event_sequence), 0) + 1 
    INTO next_sequence
    FROM process_events 
    WHERE process_id = NEW.id;
    
    -- イベントレコード挿入
    INSERT INTO process_events (
        process_id, 
        event_type, 
        event_data, 
        event_sequence,
        event_category,
        event_source,
        published_at
    ) VALUES (
        NEW.id,
        event_type_name,
        event_data,
        next_sequence,
        'process_state',
        'database_trigger',
        NOW()
    );
    
    -- Realtime フィールド更新
    NEW.realtime_channel := channel_name;
    NEW.last_realtime_event := event_data;
    NEW.updated_at := NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- トリガー作成
CREATE TRIGGER trigger_publish_process_event
    BEFORE INSERT OR UPDATE ON generated_articles_state
    FOR EACH ROW EXECUTE FUNCTION publish_process_event();
```

### 4. 各ステップでの具体的更新パターン

#### 4.1 ペルソナ生成完了時

```python
async def handle_persona_generating_step(self, context: ArticleContext, run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
    """ペルソナ生成ステップの処理"""
    current_agent = persona_generator_agent
    agent_output = await self.run_agent(current_agent, agent_input, context, run_config)

    if isinstance(agent_output, GeneratedPersonasResponse):
        context.generated_detailed_personas = [p.description for p in agent_output.personas]
        context.current_step = "persona_generated"
        
        # Save context after persona generation
        if process_id and user_id:
            try:
                await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                logger.info("Context saved successfully after persona generation")
            except Exception as save_err:
                logger.error(f"Failed to save context after persona generation: {save_err}")
```

**更新内容:**
- `context.generated_detailed_personas`: 生成されたペルソナリスト
- `context.current_step`: "persona_generated"
- データベース状態: "user_input_required"
- イベント: "step_changed" が自動生成

#### 4.2 テーマ選択完了時

```python
async def handle_theme_selection(self, context: ArticleContext, payload: SelectThemePayload, process_id: Optional[str] = None, user_id: Optional[str] = None):
    """テーマ選択の処理"""
    selected_index = payload.selected_index
    if 0 <= selected_index < len(context.generated_themes):
        context.selected_theme = context.generated_themes[selected_index]
        context.current_step = "theme_selected"
        
        # Save context after theme selection
        if process_id and user_id:
            await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
```

**更新内容:**
- `context.selected_theme`: 選択されたテーマ
- `context.current_step`: "theme_selected"
- データベース状態: "in_progress"
- イベント: "step_changed" + ユーザー入力解決イベント

#### 4.3 リサーチ完了時

```python
async def handle_research_synthesizing_step(self, context: ArticleContext, run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
    """リサーチ統合ステップの処理"""
    current_agent = research_synthesizer_agent
    agent_output = await self.run_agent(current_agent, agent_input, context, run_config)

    if isinstance(agent_output, ResearchReport):
        context.research_report = agent_output
        context.current_step = "research_report_generated"
        
        # Save context with research report
        if process_id and user_id:
            await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
```

**更新内容:**
- `context.research_report`: 統合されたリサーチレポート
- `context.research_query_results`: 個別クエリ結果
- `context.current_step`: "research_report_generated"
- データベース状態: "in_progress"

### 5. 最終記事保存プロセス

#### 5.1 完成時の特別処理

```python
if context.current_step == "completed":
    # Use final_article_html if available, otherwise fallback to full_draft_html
    final_content = getattr(context, 'final_article_html', None) or getattr(context, 'full_draft_html', None)
    
    if final_content:
        article_data = {
            "user_id": user_id,
            "organization_id": organization_id,
            "generation_process_id": process_id,
            "title": context.generated_outline.title if context.generated_outline else "Generated Article",
            "content": final_content,
            "keywords": context.initial_keywords,
            "target_audience": context.selected_detailed_persona,
            "status": "completed"
        }
        
        try:
            # 手動でのチェック・挿入・更新（UPSERT制約に依存しない）
            console.print(f"[cyan]Saving final article for process {process_id}[/cyan]")
            
            # 既存記事をチェック
            existing_article = supabase.table("articles").select("id").eq("generation_process_id", process_id).execute()
            
            if existing_article.data and len(existing_article.data) > 0:
                # 既存記事を更新
                article_id = existing_article.data[0]["id"]
                article_result = supabase.table("articles").update(article_data).eq("id", article_id).execute()
            else:
                # 新規記事を作成
                article_result = supabase.table("articles").insert(article_data).execute()
                article_id = article_result.data[0]["id"]
            
            update_data["article_id"] = article_id
```

#### 5.2 画像プレースホルダーの処理

```python
async def extract_and_save_placeholders(self, supabase, article_id: str, content: str) -> None:
    """記事内容から画像プレースホルダーを抽出してデータベースに保存する"""
    import re
    
    try:
        # 画像プレースホルダーのパターン: <!-- IMAGE_PLACEHOLDER: id|description_jp|prompt_en -->
        pattern = r'<!-- IMAGE_PLACEHOLDER: ([^|]+)\|([^|]+)\|([^>]+) -->'
        matches = re.findall(pattern, content)
        
        if not matches:
            logger.info(f"No image placeholders found in article {article_id}")
            return
        
        # 各プレースホルダーをデータベースに保存
        for index, (placeholder_id, description_jp, prompt_en) in enumerate(matches):
            placeholder_data = {
                "article_id": article_id,
                "placeholder_id": placeholder_id.strip(),
                "description_jp": description_jp.strip(),
                "prompt_en": prompt_en.strip(),
                "position_index": index + 1,
                "status": "pending"
            }
            
            # ON CONFLICT DO UPDATEでupsert
            result = supabase.table("image_placeholders").upsert(
                placeholder_data,
                on_conflict="article_id,placeholder_id"
            ).execute()
```

## フロー管理との統合

### 1. GenerationFlowManager との連携

ファイル位置: `/backend/app/domains/seo_article/services/_generation_flow_manager.py`

```python
async def run_generation_loop(self, context: ArticleContext, run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
    """記事生成のメインループ（WebSocketインタラクティブ版）"""
    
    try:
        while context.current_step not in ["completed", "error"]:
            console.print(f"[green]生成ループ開始: {context.current_step} (process_id: {process_id})[/green]")
            
            # 非同期yield pointを追加してWebSocketループに制御を戻す
            await asyncio.sleep(0.1)
            
            # データベースに現在の状態を保存
            if process_id and user_id:
                await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
            
            # ステップ実行
            await self.execute_step(context, run_config, process_id, user_id)
```

### 2. エラーハンドリングとリカバリ

```python
async def handle_generation_error(self, context: ArticleContext, error: Exception, process_id: Optional[str] = None):
    """生成エラーの処理"""
    error_message = str(error)
    context.error_message = error_message
    context.current_step = "error"
    
    # エラー状態をデータベースに保存
    if process_id:
        try:
            await self.service.persistence_service.save_context_to_db(context, process_id=process_id)
            logger.info(f"Error state saved to database for process {process_id}")
        except Exception as save_error:
            logger.error(f"Failed to save error state: {save_error}")
```

## データベース整合性とパフォーマンス

### 1. トランザクション管理

```python
async def update_process_with_transaction(self, process_id: str, updates: Dict[str, Any]):
    """トランザクションを使用したプロセス更新"""
    try:
        # Begin transaction
        supabase.rpc('begin_transaction').execute()
        
        # Update main state
        supabase.table("generated_articles_state").update(updates).eq("id", process_id).execute()
        
        # Add to history
        await self.add_step_to_history(process_id, updates.get('current_step'), 'completed')
        
        # Commit transaction
        supabase.rpc('commit_transaction').execute()
        
    except Exception as e:
        # Rollback on error
        supabase.rpc('rollback_transaction').execute()
        logger.error(f"Transaction failed for process {process_id}: {e}")
        raise
```

### 2. バッチ更新の最適化

```python
async def batch_update_contexts(self, contexts_data: List[Dict[str, Any]]):
    """複数のコンテキストを効率的に更新"""
    try:
        # Prepare batch update data
        batch_updates = []
        for data in contexts_data:
            batch_updates.append({
                "id": data["process_id"],
                "article_context": data["context"],
                "status": data["status"],
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
        
        # Execute batch update
        if batch_updates:
            supabase.table("generated_articles_state").upsert(batch_updates).execute()
            logger.info(f"Batch updated {len(batch_updates)} contexts")
            
    except Exception as e:
        logger.error(f"Batch update failed: {e}")
        # Fallback to individual updates
        for data in contexts_data:
            try:
                await self.save_context_to_db(data["context"], data["process_id"])
            except Exception as individual_error:
                logger.error(f"Individual update failed for {data['process_id']}: {individual_error}")
```

### 3. インデックス最適化

主要なクエリパフォーマンス向上のためのインデックス：

```sql
-- 頻繁な検索パターンに対応
CREATE INDEX idx_generated_articles_state_user_status ON generated_articles_state(user_id, status);
CREATE INDEX idx_generated_articles_state_process_step ON generated_articles_state(id, current_step_name);
CREATE INDEX idx_process_events_process_sequence ON process_events(process_id, event_sequence DESC);

-- JSONB フィールドの検索最適化
CREATE INDEX idx_article_context_gin ON generated_articles_state USING GIN (article_context);
CREATE INDEX idx_article_context_step ON generated_articles_state ((article_context->>'current_step'));
```

## 監視とデバッグ

### 1. リアルタイム監視

```python
async def monitor_database_updates():
    """データベース更新の監視"""
    try:
        # 更新頻度の監視
        recent_updates = supabase.table("generated_articles_state")\
            .select("id, updated_at, current_step_name")\
            .gte("updated_at", (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat())\
            .execute()
        
        logger.info(f"Recent updates: {len(recent_updates.data)} processes updated in last 5 minutes")
        
        # 長時間更新されていないプロセスの検出
        stale_processes = supabase.table("generated_articles_state")\
            .select("id, current_step_name, updated_at")\
            .eq("status", "in_progress")\
            .lt("updated_at", (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat())\
            .execute()
        
        if stale_processes.data:
            logger.warning(f"Found {len(stale_processes.data)} stale processes")
            
    except Exception as e:
        logger.error(f"Monitoring error: {e}")
```

### 2. デバッグ用ログ

```python
async def log_context_changes(self, old_context: ArticleContext, new_context: ArticleContext, process_id: str):
    """コンテキスト変更の詳細ログ"""
    changes = {}
    
    for key in new_context.__dict__:
        if key not in ["websocket", "user_response_event"]:
            old_value = getattr(old_context, key, None)
            new_value = getattr(new_context, key, None)
            
            if old_value != new_value:
                changes[key] = {
                    "old": str(old_value)[:100] if old_value else None,
                    "new": str(new_value)[:100] if new_value else None
                }
    
    if changes:
        logger.info(f"Context changes for process {process_id}: {json.dumps(changes, ensure_ascii=False, indent=2)}")
```

## まとめ

SEO記事生成におけるデータベース更新フローは、以下の特徴を持ちます：

### 1. 段階的永続化
- 各ステップ完了時にArticleContextを完全にシリアライズ
- WebSocketやasyncioオブジェクトを除外した安全な永続化
- エラー情報の適切な保存

### 2. 自動イベント生成
- データベーストリガーによる自動process_events生成
- Supabase Realtimeとの連携による即座の通知
- イベントシーケンス管理による順序保証

### 3. 最終成果物の統合
- 完成時のarticlesテーブルへの自動保存
- 画像プレースホルダーの抽出・管理
- 重複防止とUPSERT処理

### 4. 堅牢性の確保
- トランザクション管理による整合性保証
- エラー時の適切な状態保存
- プロセス復旧のための十分な情報保持

この設計により、記事生成プロセスの完全な追跡可能性と、障害時の適切な復旧機能を実現しています。