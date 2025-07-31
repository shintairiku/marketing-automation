# Supabase Realtime 状態管理システム 完全解析

## 📋 概要

この文書は、記事生成システムにおけるSupabase Realtimeを使用した状態管理システムの完全な解析結果です。
実際のコードベースを詳細に調査し、すべてのファクトチェックを行った正確な情報を記録しています。

## 🗄️ Supabase Realtime Publication設定

### 監視対象テーブル一覧

```sql
CREATE PUBLICATION supabase_realtime FOR TABLE 
  products, 
  prices, 
  organizations, 
  organization_members, 
  invitations,
  article_generation_flows, 
  flow_steps, 
  generated_articles_state,    -- ⭐ メイン状態テーブル
  articles,
  process_events,              -- ⭐ リアルタイムイベントテーブル
  background_tasks,
  task_dependencies,
  image_placeholders,
  company_info,
  style_guide_templates;
```

**重要な設定:**
```sql
-- 完全レプリケーション設定（全カラム変更を検知）
ALTER TABLE process_events REPLICA IDENTITY FULL;
ALTER TABLE background_tasks REPLICA IDENTITY FULL;
ALTER TABLE task_dependencies REPLICA IDENTITY FULL;
```

## 🔌 フロントエンド Subscription設定

### 1. Process Events 監視
```typescript
supabase.channel(`process_events:process_id=eq.${processId}`)
  .on('postgres_changes', {
    event: 'INSERT',              // 新しいイベントの挿入のみ監視
    schema: 'public', 
    table: 'process_events',
    filter: `process_id=eq.${processId}`
  })
```

### 2. Generated Articles State 監視
```typescript
.on('postgres_changes', {
  event: 'UPDATE',                // 状態更新の監視
  schema: 'public',
  table: 'generated_articles_state', 
  filter: `id=eq.${processId}`
})
```

## ⚡ 自動トリガーシステム

### データベーストリガー関数: `publish_process_event()`

```sql
CREATE TRIGGER trigger_publish_process_event
  AFTER INSERT OR UPDATE ON generated_articles_state
  FOR EACH ROW EXECUTE FUNCTION publish_process_event();
```

**トリガー条件判定ロジック:**
```sql
IF TG_OP = 'INSERT' THEN
  event_type_name := 'process_created';
ELSIF TG_OP = 'UPDATE' THEN
  IF OLD.status IS DISTINCT FROM NEW.status THEN
    event_type_name := 'status_changed';
  ELSIF OLD.current_step_name IS DISTINCT FROM NEW.current_step_name THEN
    event_type_name := 'step_changed';
  ELSIF OLD.progress_percentage IS DISTINCT FROM NEW.progress_percentage THEN
    event_type_name := 'progress_updated';
  ELSIF OLD.is_waiting_for_input IS DISTINCT FROM NEW.is_waiting_for_input THEN
    event_type_name := CASE 
      WHEN NEW.is_waiting_for_input THEN 'input_required' 
      ELSE 'input_resolved' 
    END;
  ELSE
    event_type_name := 'process_updated';
  END IF;
ELSE
  event_type_name := 'process_changed';
END IF;
```

## 🎯 記事生成ワークフロー 全ステップ解析

### Backend実行ステップ → Frontend表示ステップ 完全マッピング

| Backend Step | Frontend UI Step | Database Status | UI Status | User Action Required | Auto Transition |
|--------------|------------------|-----------------|-----------|---------------------|-----------------|
| `start` | `keyword_analyzing` | `in_progress` | 🔄 Loading | ❌ | ✅ |
| `keyword_analyzing` | `keyword_analyzing` | `in_progress` | 🔄 Loading | ❌ | ❌ |
| `keyword_analyzed` | `persona_generating` | `in_progress` | 🔄 Loading | ❌ | ✅ |
| `persona_generating` | `persona_generating` | `in_progress` | 🔄 Loading | ❌ | ❌ |
| `persona_generated` | `persona_generating` | `user_input_required` | ✅ Completed | ✅ Select Persona | ❌ |
| `persona_selected` | `theme_generating` | `in_progress` | 🔄 Loading | ❌ | ✅ |
| `theme_generating` | `theme_generating` | `in_progress` | 🔄 Loading | ❌ | ❌ |
| `theme_proposed` | `theme_generating` | `user_input_required` | ✅ Completed | ✅ Select Theme | ❌ |
| `theme_selected` | `research_planning` | `in_progress` | 🔄 Loading | ❌ | ✅ |
| `research_planning` | `research_planning` | `in_progress` | 🔄 Loading | ❌ | ❌ |
| `research_plan_generated` | `research_planning` | `user_input_required` | ✅ Completed | ✅ Approve Plan | ❌ |
| `research_plan_approved` | `researching` | `in_progress` | 🔄 Loading | ❌ | ✅ |
| `researching` | `researching` | `in_progress` | 🔄 Loading | ❌ | ❌ |
| `research_synthesizing` | `researching` | `in_progress` | 🔄 Loading | ❌ | ❌ |
| `research_report_generated` | `outline_generating` | `in_progress` | 🔄 Loading | ❌ | ✅ |
| `outline_generating` | `outline_generating` | `in_progress` | 🔄 Loading | ❌ | ❌ |
| `outline_generated` | `outline_generating` | `user_input_required` | ✅ Completed | ✅ Approve Outline | ❌ |
| `outline_approved` | `writing_sections` | `in_progress` | 🔄 Loading | ❌ | ✅ |
| `writing_sections` | `writing_sections` | `in_progress` | 🔄 Loading | ❌ | ❌ |
| `all_sections_completed` | `editing` | `in_progress` | 🔄 Loading | ❌ | ✅ |
| `editing` | `editing` | `in_progress` | 🔄 Loading | ❌ | ❌ |
| `editing_completed` | `editing` | `in_progress` | 🔄 Loading | ❌ | ❌ |
| `completed` | `editing` | `completed` | ✅ Completed | ❌ | ❌ |
| `error` | `keyword_analyzing` | `error` | ❌ Error | ❌ | ❌ |
| `paused` | `keyword_analyzing` | `paused` | ⏸️ Paused | ❌ | ❌ |
| `cancelled` | `keyword_analyzing` | `cancelled` | ⏹️ Cancelled | ❌ | ❌ |

## 📨 Realtime Event Types 完全一覧

### 1. データベーストリガー自動生成イベント

| Event Type | 発生条件 | 送信データ | フロントエンド処理 |
|------------|----------|------------|-------------------|
| `process_created` | `generated_articles_state` INSERT | 完全なプロセス状態 | 初期状態設定 |
| `status_changed` | `status`フィールド変更 | 完全なプロセス状態 + 変更差分 | ステータス更新 |
| `step_changed` | `current_step_name`フィールド変更 | 完全なプロセス状態 + 変更差分 | ステップ遷移 |
| `progress_updated` | `progress_percentage`フィールド変更 | 完全なプロセス状態 + 変更差分 | 進捗バー更新 |
| `input_required` | `is_waiting_for_input` FALSE→TRUE | 完全なプロセス状態 + 変更差分 | 入力UI表示 |
| `input_resolved` | `is_waiting_for_input` TRUE→FALSE | 完全なプロセス状態 + 変更差分 | 入力UI非表示 |
| `process_updated` | その他の一般的更新 | 完全なプロセス状態 + 変更差分 | 汎用状態更新 |

### 2. フロントエンド合成イベント

| Event Type | 生成条件 | 送信データ | 処理内容 |
|------------|----------|------------|----------|
| `process_state_updated` | `generated_articles_state` UPDATE受信 | プロセス状態全体 | 状態同期 |

### 3. フロントエンド処理専用イベント

| Event Type | 発生タイミング | データソース | UI効果 |
|------------|----------------|--------------|--------|
| `generation_started` | 生成開始時 | WebSocket/API | keyword_analyzing開始表示 |
| `step_started` | ステップ開始時 | WebSocket/API | 該当ステップをin_progress状態に |
| `step_completed` | ステップ完了時 | WebSocket/API | 該当ステップをcompleted状態に + auto-progression |
| `user_input_required` | ユーザー入力待ち | WebSocket/API | isWaitingForInput=true + inputType設定 |
| `user_input_resolved` | ユーザー入力完了 | WebSocket/API | isWaitingForInput=false + auto-progression |
| `content_chunk_generated` | コンテンツストリーミング | WebSocket/API | リアルタイムコンテンツ表示 |
| `generation_completed` | 生成完了 | WebSocket/API | completed状態遷移 |
| `article_created` | 記事作成完了 | WebSocket/API | completed状態遷移 |
| `article_saved` | 記事保存完了 | WebSocket/API | completed状態遷移 |
| `generation_error` | エラー発生 | WebSocket/API | error状態 + エラーメッセージ表示 |
| `generation_paused` | 一時停止 | WebSocket/API | paused状態遷移 |
| `generation_cancelled` | 処理中止 | WebSocket/API | cancelled状態遷移 |

### 4. 進捗追跡イベント

| Event Type | 用途 | データ構造 | UI反映箇所 |
|------------|------|------------|------------|
| `research_progress` | リサーチ進捗 | `{current_query, total_queries, progress}` | リサーチ進捗バー |
| `section_progress` | セクション執筆進捗 | `{current_section, total_sections, section_heading}` | セクション進捗表示 |
| `image_placeholders_generated` | 画像プレースホルダー生成 | `{placeholders: Array}` | 画像プレースホルダー表示 |

### 5. 詳細フェーズイベント

| Event Type | 発生フェーズ | 具体処理 | UI変化 |
|------------|--------------|----------|--------|
| `research_synthesis_started` | リサーチ後 | 研究結果統合開始 | ログ出力のみ |
| `research_synthesis_completed` | リサーチ後 | 研究結果統合完了 | researching→completed |
| `outline_generation_started` | アウトライン作成開始 | アウトライン生成開始 | outline_generating開始 |
| `outline_generation_completed` | アウトライン作成完了 | アウトライン生成完了 | outline_generating→completed |
| `section_writing_started` | セクション執筆開始 | セクション執筆開始 | writing_sections開始 |
| `section_writing_progress` | セクション執筆中 | セクション執筆進捗 | セクション進捗更新 |
| `editing_started` | 編集開始 | 最終編集開始 | editing開始 |
| `section_completed` | セクション完了 | 個別セクション完了 | completedSections配列更新 |
| `all_sections_completed` | 全セクション完了 | すべてのセクション完了 | editing状態遷移 |

### 6. ユーザーアクション完了イベント

| Event Type | トリガーアクション | Backend処理 | Frontend効果 |
|------------|-------------------|------------|--------------|
| `keyword_analysis_completed` | 自動 | キーワード分析完了 | persona_generating自動遷移 |
| `persona_selection_completed` | ペルソナ選択 | ペルソナ選択処理 | theme_generating自動遷移 |
| `theme_selection_completed` | テーマ選択 | テーマ選択処理 | research_planning自動遷移 |
| `research_plan_approval_completed` | 計画承認 | リサーチ計画承認処理 | researching自動遷移 |
| `outline_approval_completed` | アウトライン承認 | アウトライン承認処理 | writing_sections自動遷移 |

## 🔄 状態更新フロー詳細

### 完全な状態同期チェーン

1. **Backend処理実行**
   ```python
   # _process_persistence_service.py
   await self.service.persistence_service.save_context_to_db(
       context, process_id=process_id, user_id=user_id
   )
   ```

2. **Database更新**
   ```python
   supabase.table("generated_articles_state").update(update_data).eq("id", process_id).execute()
   ```

3. **トリガー自動発火**
   ```sql
   -- generated_articles_state更新時に自動実行
   AFTER INSERT OR UPDATE ON generated_articles_state
   ```

4. **Process Event生成**
   ```sql
   INSERT INTO process_events (
     process_id, event_type, event_data, event_sequence,
     event_category, event_source, published_at
   ) VALUES (
     NEW.id, event_type_name, event_data, next_sequence,
     'process_state', 'database_trigger', NOW()
   );
   ```

5. **Realtime配信**
   - Supabaseが`process_events`のINSERTを検知
   - Realtimeチャネルにイベント配信

6. **Frontend受信**
   ```typescript
   // useSupabaseRealtime.ts
   .on('postgres_changes', {
     event: 'INSERT',
     table: 'process_events',
     filter: `process_id=eq.${processId}`
   })
   ```

7. **状態更新**
   ```typescript
   // useArticleGenerationRealtime.ts
   const handleRealtimeEvent = useCallback((event: ProcessEvent) => {
     setState((prev: GenerationState) => {
       // イベントタイプに基づいた状態更新ロジック
     });
   });
   ```

## 🛡️ 重複排除・整合性保証

### イベント重複排除
```typescript
// 500ms間隔でのスロットリング
const timeSinceLastProcess = now - lastProcessedTime;
if (stateFingerprint === lastProcessedState && timeSinceLastProcess < 500) {
  console.log('⏭️ Skipping duplicate state update (throttled)');
  return;
}
```

### シーケンス番号による順序保証
```typescript
if (event.event_sequence > currentSequence) {
  setLastEventSequence(event.event_sequence);
  onEvent?.(event);
} else {
  console.warn('Out-of-order or duplicate event received');
}
```

### ステップ状態保持ロジック
```typescript
// 既存のcompleted状態を保持
const existingStatus = step.status;
if (existingStatus === 'completed' || existingStatus === 'error') {
  return step; // 既存の最終状態を保持
}
```

## 📊 イベントデータ構造

### Process Event完全構造
```typescript
interface ProcessEvent {
  id: string;
  process_id: string;
  event_type: string;
  event_data: {
    process_id: string;
    status: string;                    // generation_status enum値
    current_step: string;              // backend step名
    executing_step?: string;           // 実行中の具体的ステップ
    progress_percentage: number;       // 0-100
    is_waiting_for_input: boolean;     // ユーザー入力待ちフラグ
    input_type?: string;               // select_persona, approve_plan等
    updated_at: string;                // ISO timestamp
    event_type: string;                // イベントタイプ（重複）
    user_id: string;
    organization_id?: string;
    background_task_id?: string;
    retry_count: number;
    error_message?: string;
    article_context: object;           // 記事生成コンテキスト全体
    process_metadata: object;          // プロセスメタデータ
    step_history: Array<object>;       // ステップ履歴
    changes?: {                        // 変更差分（UPDATE時のみ）
      status: {old: string, new: string};
      current_step: {old: string, new: string};
      progress: {old: number, new: number};
    };
  };
  event_sequence: number;              // プロセス内シーケンス番号
  event_category: string;              // 'process_state'等
  event_source: string;                // 'database_trigger'等
  created_at: string;                  // ISO timestamp
  published_at?: string;               // 配信タイムスタンプ
}
```

### Generated Articles State構造
```typescript
interface GeneratedArticleState {
  id: string;                          // プロセスID（UUID）
  user_id: string;
  organization_id?: string;
  status: string;                      // generation_status enum
  current_step_name?: string;          // 現在のステップ名
  progress_percentage: number;         // 進捗パーセンテージ
  is_waiting_for_input: boolean;       // 入力待ちフラグ
  input_type?: string;                 // 必要な入力タイプ
  article_context?: any;               // 記事生成コンテキスト
  process_metadata?: any;              // プロセスメタデータ
  step_history?: any[];                // ステップ履歴
  error_message?: string;              // エラーメッセージ
  created_at: string;
  updated_at: string;
  realtime_channel?: string;           // Realtimeチャネル名
  last_realtime_event?: any;          // 最後のRealtimeイベント
  executing_step?: string;             // 実行中ステップ
  background_task_id?: string;        // バックグラウンドタスクID
  retry_count: number;                 // リトライ回数
  user_input_timeout?: string;        // 入力タイムアウト
  interaction_history?: any[];        // インタラクション履歴
}
```

## 🎛️ フロントエンド状態管理

### Generation State構造
```typescript
interface GenerationState {
  // 基本状態
  currentStep: string;                 // 現在のUIステップ
  steps: GenerationStep[];             // ステップ配列（進捗表示用）
  isWaitingForInput: boolean;          // 入力待ち状態
  inputType?: string;                  // 必要な入力タイプ
  error?: string;                      // エラーメッセージ
  
  // データ状態
  personas?: Array<{id: number, description: string}>;
  themes?: Array<ThemeIdea>;
  researchPlan?: any;
  outline?: any;
  generatedContent?: string;
  finalArticle?: {title: string, content: string};
  
  // 進捗状態
  researchProgress?: {
    currentQuery: string;
    totalQueries: number;
    progress: number;
  };
  sectionsProgress?: {
    currentSection: number;
    totalSections: number;
    sectionHeading: string;
  };
  completedSections?: CompletedSection[];
  imagePlaceholders?: any[];
}
```

## 🔒 セキュリティ・アクセス制御

### Row Level Security (RLS)
```sql
-- プロセス所有者のみアクセス可能
CREATE POLICY "Users can access their own processes" ON generated_articles_state
  FOR ALL USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

-- プロセス所有者のみイベント閲覧可能
CREATE POLICY "Users can view their own process events" ON process_events
  FOR SELECT USING (
    process_id IN (
      SELECT id FROM generated_articles_state 
      WHERE user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );
```

## 📈 パフォーマンス最適化

### データベースインデックス
```sql
-- プロセス検索最適化
CREATE INDEX idx_generated_articles_state_user_status 
ON generated_articles_state(user_id, status);

-- イベント検索最適化
CREATE INDEX idx_process_events_process_sequence 
ON process_events(process_id, event_sequence);

-- Realtime最適化
CREATE INDEX idx_process_events_published_at 
ON process_events(published_at DESC);
```

### フロントエンド最適化
- イベント重複排除によるレンダリング最適化
- ステート保持によるUI一貫性確保
- シーケンス番号による順序保証

## 🚨 エラーハンドリング

### Backend Error States
```python
# エラー時の状態遷移
context.current_step = "error"
update_data["error_message"] = context.error_message
update_data["status"] = "error"
```

### Frontend Error Recovery
```typescript
case 'generation_error':
  newState.currentStep = 'error';
  newState.error = event.event_data.error_message;
  // エラー状態の表示とリトライ機能
```

## 📋 運用・監視

### イベント保持ポリシー
```sql
-- 7日後に自動クリーンアップ（重要イベントは除外）
DELETE FROM process_events
WHERE created_at < (NOW() - INTERVAL '7 days')
  AND event_type NOT IN ('process_created', 'generation_completed', 'generation_error')
  AND archived = FALSE;
```

### ログ・メトリクス
- 全イベントはタイムスタンプ付きで永続化
- ユーザーごとのプロセス履歴保持
- エラー発生率・完了率の監視が可能

---

## 📝 検証済み事実

この文書の全ての情報は以下のソースファイルから直接抽出・検証済みです：

- `/frontend/supabase/migrations/20250727000000_supabase_realtime_migration.sql` - トリガー・Publication定義
- `/frontend/src/hooks/useSupabaseRealtime.ts` - フロントエンドサブスクリプション
- `/frontend/src/hooks/useArticleGenerationRealtime.ts` - 状態管理・イベント処理
- `/backend/app/domains/seo_article/services/_generation_flow_manager.py` - Backend状態遷移
- `/backend/app/domains/seo_article/services/_process_persistence_service.py` - データベース更新

**最終更新:** 2025-01-31
**バージョン:** 1.0 (完全版)