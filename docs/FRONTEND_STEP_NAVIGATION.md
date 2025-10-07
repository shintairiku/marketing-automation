# フロントエンド ステップナビゲーション実装完了

## 実装コンポーネント

### 1. カスタムフック: `useStepSnapshots`

**ファイル**: `/frontend/src/hooks/useStepSnapshots.ts`

```typescript
export function useStepSnapshots({ processId, autoFetch }: UseStepSnapshotsOptions) {
  return {
    snapshots,          // スナップショット一覧
    isLoading,          // 読み込み中フラグ
    error,              // エラーメッセージ
    isRestoring,        // 復元中フラグ
    fetchSnapshots,     // スナップショット再取得
    restoreFromSnapshot // スナップショット復元
  };
}
```

**機能**:
- スナップショット一覧の自動取得
- 復元処理の実行
- エラーハンドリング
- ローディング状態管理

### 2. ステップ履歴パネル: `StepHistoryPanel`

**ファイル**: `/frontend/src/features/tools/seo/generate/new-article/component/StepHistoryPanel.tsx`

```tsx
<StepHistoryPanel
  processId={processId}
  currentStep={currentStep}
  onRestoreSuccess={() => window.location.reload()}
/>
```

**主な機能**:

1. **展開/折りたたみ機能**
   - 初期状態は折りたたみ
   - クリックで展開/折りたたみ
   - スナップショット数をバッジ表示

2. **スナップショット一覧表示**
   - 時系列順（古い順）に表示
   - タイムライン形式のUI
   - 現在のステップをハイライト

3. **各スナップショットの情報**
   - ステップ説明（日本語）
   - 作成日時（相対時間表示）
   - ステップカテゴリ（バッジ）
   - 再実行回数（2回目以降の場合）

4. **復元ボタン**
   - 現在のステップ以外に表示
   - 復元可能なステップのみ
   - クリックで確認ダイアログを表示

**UI/UX**:
- Framer Motionによるスムーズなアニメーション
- レスポンシブデザイン
- アクセシビリティ対応

### 3. 復元確認ダイアログ: `RestoreConfirmDialog`

**ファイル**: `/frontend/src/features/tools/seo/generate/new-article/component/RestoreConfirmDialog.tsx`

```tsx
<RestoreConfirmDialog
  isOpen={showDialog}
  snapshot={selectedSnapshot}
  processId={processId}
  onSuccess={handleSuccess}
  onCancel={handleCancel}
/>
```

**主な機能**:

1. **スナップショット情報表示**
   - ステップ説明
   - 作成日時
   - 再実行回数

2. **影響の説明**
   - プロセスが戻ること
   - ステップから再開されること
   - 後続データは保持されること
   - 異なる選択ができること

3. **ステップ別のヒント**
   - ユーザー入力ステップ: 選択画面が再表示される説明
   - 自律実行ステップ: 自動実行される説明

4. **復元処理**
   - 復元ボタンクリックで処理開始
   - ローディング表示
   - エラーハンドリング
   - 成功時のコールバック

**UI/UX**:
- モーダルダイアログ形式
- 視覚的に分かりやすいアイコン
- ステップカテゴリ別の色分け
- エラーメッセージの表示

### 4. GenerationProcessPage への統合

**ファイル**: `/frontend/src/features/tools/seo/generate/new-article/display/GenerationProcessPage.tsx`

**統合箇所**:
```tsx
{/* ステップ履歴パネル */}
<AnimatePresence>
  {state.currentStep !== 'start' && !isLoading && (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
    >
      <StepHistoryPanel
        processId={jobId}
        currentStep={state.currentStep}
        onRestoreSuccess={() => {
          // ページをリロードして状態を更新
          window.location.reload();
        }}
      />
    </motion.div>
  )}
</AnimatePresence>
```

**表示条件**:
- `start` ステップ以外
- ページ読み込み完了後
- エラー処理パネルの後に表示

## 使用例

### 1. ペルソナ選択のやり直し

1. ユーザーがテーマ選択まで進行
2. ステップ履歴パネルを展開
3. 「ペルソナ生成完了（選択待ち）」を選択
4. 確認ダイアログで「このステップに戻る」をクリック
5. ペルソナ選択画面が再表示される
6. 異なるペルソナを選択可能

### 2. テーマの再検討

1. アウトライン生成まで完了
2. ステップ履歴から「テーマ提案完了（選択待ち）」を選択
3. 確認ダイアログで復元を承認
4. テーマ選択画面に戻る
5. 別のテーマを試せる

### 3. エラーからの回復

1. リサーチ実行中にエラー
2. ステップ履歴から「リサーチ計画承認済み」を選択
3. 復元を実行
4. リサーチ計画承認済みの状態に戻る
5. リサーチを再実行

## デザイン仕様

### カラースキーム

- **現在のステップ**: `bg-primary/5 border-primary`
- **過去のステップ**: `bg-card hover:bg-accent/30 border-border`
- **ユーザー入力ステップ**: `bg-blue-50` (ヒント表示)
- **自律実行ステップ**: `bg-green-50` (ヒント表示)

### アイコン

- **History**: 履歴パネルアイコン
- **ChevronDown/Up**: 展開/折りたたみ
- **RotateCcw**: 復元ボタン
- **Clock**: 時刻表示
- **CheckCircle2**: 現在のステップマーカー
- **AlertTriangle**: 警告メッセージ
- **Loader2**: ローディング

### アニメーション

- **パネル展開**: `height: 0 → auto` (200ms)
- **スナップショット項目**: 順次フェードイン (50ms遅延)
- **ダイアログ**: フェードイン
- **ボタン**: ホバー効果

## テスト方法

### ローカル開発環境

1. **バックエンド起動**:
```bash
cd backend
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

2. **フロントエンド起動**:
```bash
cd frontend
npm run dev
```

3. **記事生成開始**:
   - `/seo/generate/new-article` にアクセス
   - キーワードを入力して生成開始
   - プロセスページが表示される

4. **ステップ履歴確認**:
   - ペルソナ生成完了まで待機
   - ステップ履歴パネルが表示される
   - パネルをクリックして展開
   - スナップショットが時系列で表示される

5. **復元テスト**:
   - テーマ選択まで進む
   - ステップ履歴から「ペルソナ生成完了」を選択
   - 「戻る」ボタンをクリック
   - 確認ダイアログが表示される
   - 「このステップに戻る」をクリック
   - ページがリロードされ、ペルソナ選択画面が表示される

### ブラウザ開発者ツールでの確認

```javascript
// コンソールでスナップショット一覧を確認
const response = await fetch('/api/proxy/articles/generation/[process_id]/snapshots', {
  headers: {
    'Authorization': 'Bearer [token]'
  }
});
const snapshots = await response.json();
console.log(snapshots);

// 復元APIのテスト
const restoreResponse = await fetch(
  '/api/proxy/articles/generation/[process_id]/snapshots/[snapshot_id]/restore',
  {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer [token]'
    }
  }
);
const result = await restoreResponse.json();
console.log(result);
```

## トラブルシューティング

### 問題1: ステップ履歴パネルが表示されない

**原因**:
- プロセスIDが正しくない
- スナップショットがまだ作成されていない
- `currentStep` が `start` のまま

**解決策**:
```tsx
// GenerationProcessPage.tsx で確認
console.log('Process ID:', jobId);
console.log('Current Step:', state.currentStep);
console.log('Is Loading:', isLoading);
```

### 問題2: スナップショットが空

**原因**:
- バックエンドでスナップショットが保存されていない
- データベースマイグレーションが未実行

**解決策**:
1. バックエンドログを確認: `📸 Snapshot saved for step...`
2. データベースを確認:
```sql
SELECT * FROM article_generation_step_snapshots
WHERE process_id = '[process_id]';
```

### 問題3: 復元後にプロセスが進まない

**原因**:
- ページリロードが実行されていない
- Realtime接続が切れている

**解決策**:
```tsx
// onRestoreSuccess コールバックを確認
onRestoreSuccess={() => {
  console.log('Restore success, reloading page...');
  window.location.reload();
}}
```

## パフォーマンス考慮事項

### 最適化

1. **自動取得の制御**:
   - `autoFetch=true` でマウント時のみ取得
   - 手動更新は `fetchSnapshots()` を呼び出し

2. **アニメーション**:
   - AnimatePresenceで不要な要素を削除
   - リスト項目の遅延アニメーション (50ms × index)

3. **API呼び出し**:
   - スナップショット一覧: 1回のみ（手動更新時を除く）
   - 復元処理: ユーザーアクション時のみ

### メモリ管理

- コンポーネントアンマウント時に状態をクリア
- ダイアログクローズ時に選択状態をリセット

## まとめ

フロントエンドのステップナビゲーション実装が完了しました！

**実装内容**:
✅ カスタムフック (`useStepSnapshots`)
✅ ステップ履歴パネル (`StepHistoryPanel`)
✅ 復元確認ダイアログ (`RestoreConfirmDialog`)
✅ GenerationProcessPage への統合

**主な機能**:
- すべてのステップで戻れる
- 直感的なUI/UX
- スムーズなアニメーション
- 包括的なエラーハンドリング
- レスポンシブデザイン

ユーザーは記事生成プロセスを柔軟に制御でき、異なる選択を試したり、エラーから簡単に回復できるようになりました！
