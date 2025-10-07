# ステップナビゲーション機能実装ドキュメント

## 概要

SEO記事生成システムにステップ間ナビゲーション機能を実装しました。ユーザーは生成プロセスの任意のステップに戻り、そのステップから再度実行することができます。

## 主な機能

### 1. ステップスナップショット機能

各ステップ完了時に、以下の情報を自動的にスナップショットとして保存します：

- **ステップ情報**: ステップ名、説明、カテゴリ
- **ArticleContext**: 記事生成コンテキスト全体（ペルソナ、テーマ、リサーチ結果など）
- **メタデータ**: 復元可能性、作成日時など

### 2. ステップ復元機能

ユーザーは以下の操作が可能です：

- **スナップショット一覧表示**: プロセスのすべてのステップ履歴を時系列で表示
- **任意のステップに復元**: 選択したステップにプロセスを復元
- **後続データ保持**: 復元しても後続ステップのデータは保持される（参照可能）

### 3. 自動復元ロジック

復元されたステップに応じて、適切な状態に自動設定されます：

- **ユーザー入力ステップ**: 選択画面を再表示（persona_generated, theme_proposed等）
- **自律実行ステップ**: 通常のフローに従って自動実行
- **エラー処理**: 復元不可能な状態のチェックとエラーハンドリング

## 技術仕様

### データベース設計

#### 新規テーブル: `article_generation_step_snapshots`

```sql
CREATE TABLE article_generation_step_snapshots (
    id UUID PRIMARY KEY,
    process_id UUID REFERENCES generated_articles_state(id),
    step_name TEXT NOT NULL,
    step_index INTEGER NOT NULL,
    step_category TEXT,
    step_description TEXT,
    article_context JSONB NOT NULL,
    snapshot_metadata JSONB DEFAULT '{}',
    can_restore BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(process_id, step_name, step_index)
);
```

#### データベース関数

- **`save_step_snapshot()`**: スナップショット保存
- **`get_available_snapshots()`**: 復元可能なスナップショット一覧取得
- **`restore_from_snapshot()`**: スナップショットから復元

### バックエンドアーキテクチャ

#### PersistenceService拡張

```python
class ProcessPersistenceService:
    async def save_step_snapshot(
        self, process_id: str, step_name: str,
        article_context: ArticleContext, ...
    ) -> str:
        """ステップスナップショットを保存"""

    async def get_snapshots_for_process(
        self, process_id: str, user_id: str
    ) -> List[Dict[str, Any]]:
        """プロセスのスナップショット一覧を取得"""

    async def restore_from_snapshot(
        self, snapshot_id: str, user_id: str
    ) -> Dict[str, Any]:
        """スナップショットから復元"""
```

#### GenerationFlowManager拡張

```python
class GenerationFlowManager:
    async def run_generation_loop(self, ...):
        while context.current_step not in ["completed", "error"]:
            previous_step = context.current_step
            await self.execute_step(...)

            # 自動スナップショット保存
            if context.current_step != previous_step:
                await self.save_step_snapshot_if_applicable(
                    context, previous_step, process_id, user_id
                )
```

#### APIエンドポイント

```python
# スナップショット一覧取得
GET /articles/generation/{process_id}/snapshots

# スナップショットから復元
POST /articles/generation/{process_id}/snapshots/{snapshot_id}/restore
```

### フロントエンド実装

#### APIクライアント

```typescript
// /frontend/src/lib/api.ts
class ApiClient {
  async getProcessSnapshots(processId: string, token?: string) {
    // スナップショット一覧を取得
  }

  async restoreFromSnapshot(
    processId: string,
    snapshotId: string,
    token?: string
  ) {
    // スナップショットから復元
  }
}
```

#### UIコンポーネント（実装予定）

```tsx
// ステップ履歴表示コンポーネント
<StepHistoryPanel
  processId={processId}
  currentStep={currentStep}
  onRestore={(snapshotId) => handleRestore(snapshotId)}
/>

// 復元確認ダイアログ
<RestoreConfirmDialog
  snapshot={selectedSnapshot}
  onConfirm={() => restoreFromSnapshot(snapshotId)}
  onCancel={() => setShowDialog(false)}
/>
```

## 使用シナリオ

### シナリオ1: ペルソナ選択のやり直し

1. ユーザーがテーマ選択まで進んだ後、ペルソナを変更したいと判断
2. ステップ履歴から「ペルソナ生成完了」を選択
3. システムが`persona_generated`ステップに復元
4. ペルソナ選択画面が再表示され、ユーザーが別のペルソナを選択
5. テーマ生成から再開

### シナリオ2: エラーからの回復

1. リサーチ実行中にエラーが発生
2. ユーザーがステップ履歴から「リサーチ計画承認済み」を選択
3. システムがリサーチ計画承認済みの状態に復元
4. リサーチ実行を再試行

### シナリオ3: 異なるテーマの試行

1. アウトライン生成まで完了
2. ユーザーが別のテーマを試したいと判断
3. ステップ履歴から「テーマ提案完了」を選択
4. テーマ選択画面が再表示
5. 別のテーマを選択して再度進行

## 実装の特徴

### 1. 拡張性

- 新しいステップを追加しても互換性を維持
- ステップの順序を変更しても対応可能
- カテゴリベースの柔軟な管理

### 2. データ保持

- 復元後も後続ステップのデータを保持
- ユーザーは以前の選択を参照可能
- 履歴としてデータを残す設計

### 3. 安全性

- RLS (Row Level Security) による適切なアクセス制御
- 復元不可能なステップの明確な定義
- エラーハンドリングの充実

### 4. パフォーマンス

- スナップショット保存は非同期・非ブロッキング
- 保存失敗してもプロセスは継続
- データベース関数による効率的な操作

## セットアップ手順

### 1. データベースマイグレーション実行

```bash
# Supabase環境でマイグレーションを実行
npx supabase migration up
# または
psql [connection_string] -f shared/supabase/migrations/20251002000000_add_step_snapshots.sql
```

### 2. 環境変数確認

既存の環境変数で動作します。追加の設定は不要です。

### 3. バックエンド再起動

```bash
cd backend
poetry run uvicorn app.main:app --reload
```

### 4. フロントエンドビルド

```bash
cd frontend
npm run build
npm run dev
```

## テスト方法

### 1. スナップショット保存のテスト

```bash
# 記事生成を開始
curl -X POST http://localhost:8000/articles/generation/start \
  -H "Authorization: Bearer [token]" \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["test"], ...}'

# スナップショット一覧を確認
curl http://localhost:8000/articles/generation/[process_id]/snapshots \
  -H "Authorization: Bearer [token]"
```

### 2. 復元機能のテスト

```bash
# スナップショットから復元
curl -X POST http://localhost:8000/articles/generation/[process_id]/snapshots/[snapshot_id]/restore \
  -H "Authorization: Bearer [token]"

# プロセス状態を確認
curl http://localhost:8000/articles/generation/[process_id]/state \
  -H "Authorization: Bearer [token]"
```

## トラブルシューティング

### 問題1: スナップショットが保存されない

**原因**: データベース関数が存在しない、またはRLSポリシーの問題

**解決策**:
```sql
-- 関数の存在確認
SELECT routine_name FROM information_schema.routines
WHERE routine_name = 'save_step_snapshot';

-- RLSポリシー確認
SELECT * FROM pg_policies
WHERE tablename = 'article_generation_step_snapshots';
```

### 問題2: 復元後にプロセスが進まない

**原因**: ステップ状態が正しく設定されていない

**解決策**:
```sql
-- プロセス状態を確認
SELECT current_step_name, status, is_waiting_for_input, input_type
FROM generated_articles_state
WHERE id = '[process_id]';

-- 必要に応じて手動で修正
UPDATE generated_articles_state
SET status = 'user_input_required', is_waiting_for_input = true
WHERE id = '[process_id]';
```

## 今後の拡張予定

### フロントエンドUI実装

1. **ステップ履歴パネル**
   - タイムライン形式での表示
   - 各ステップの詳細情報表示
   - 「戻る」ボタンの実装

2. **復元確認ダイアログ**
   - 復元の影響を説明
   - 後続データの保持を明示
   - キャンセル機能

3. **視覚的フィードバック**
   - 復元アニメーション
   - ステップ遷移の可視化
   - 現在位置の強調表示

### 高度な機能

1. **ブランチ管理**
   - 複数の試行を並行管理
   - 異なる選択の比較

2. **スナップショット注釈**
   - ユーザーコメント追加
   - ステップの目印機能

3. **自動復元**
   - エラー時の自動リトライ
   - 最適なステップへの自動復元

## まとめ

ステップナビゲーション機能により、ユーザーは記事生成プロセスを柔軟に制御できるようになりました。エラーからの回復、異なる選択の試行、段階的な改善が容易になり、ユーザーエクスペリエンスが大幅に向上します。

バックエンドの実装は完了しており、フロントエンドUIの実装を追加することで、完全に機能する状態になります。
