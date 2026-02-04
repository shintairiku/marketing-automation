# Agent-05: Backend Usage API - Security Investigation Report

調査完了: 2026-02-04

## 調査対象ファイル
- backend/app/domains/usage/endpoints.py (166行)
- backend/app/domains/usage/schemas.py (44行)
- backend/app/domains/usage/service.py (297行)
- shared/supabase/migrations/20260202000001_add_usage_limits.sql (increment_usage_if_allowed関数)

---

## 発見事項サマリー

| 深刻度 | ID | 問題 |
|--------|-----|------|
| HIGH | USAGE-001 | TOCTOU競合条件（check_can_generate と record_success の分離） |
| MEDIUM | USAGE-002 | 特権ユーザーの上限超過許可ロジックで原子性バイパス |
| MEDIUM | USAGE-003 | organization_members経由のアクセスで認可チェック不十分 |
| MEDIUM | USAGE-004 | 請求期間推定の不正確さ（30日固定） |
| LOW | USAGE-005 | 管理者エンドポイントでのSQL効率問題 |
| LOW | USAGE-006 | usage_logsへの重複記録の可能性 |

---

## 詳細分析

### [HIGH] USAGE-001: TOCTOU競合条件（Time-of-check to Time-of-use）

**ファイル**:
- `backend/app/domains/usage/service.py`
- `backend/app/domains/blog/endpoints.py`

**問題**:
`check_can_generate()`（読み取り専用チェック）と `record_success()`（インクリメント）が分離されている。

**コード箇所**:
```python
# blog/endpoints.py:960
usage_result = usage_service.check_can_generate(user_id=user_id, organization_id=org_id)
if not usage_result.allowed:
    raise HTTPException(...)
# その後、生成処理が実行される（数分かかる可能性あり）

# generation_service.py:1425 - 生成成功後にカウント
usage_service.record_success(...)
```

**影響**:
複数の同時リクエストでチェックをパスした後、全てが生成を開始できる。
- 例: 残り1記事の状態で3つの同時リクエスト → 全てがcheck_can_generate()をパス → 3記事生成

**攻撃シナリオ**:
攻撃者が並列リクエスト（curl, スクリプト等）を送信することで上限を超過可能。

**緩和要因**:
record_success()内のincrement_usage_if_allowed()はFOR UPDATEロック付きなので、カウント自体は正確に記録される。ただし生成は実行されてしまう。

**推奨修正**:
- オプション1（推奨）: 生成開始時に「予約」としてincrement_usage_if_allowed()を呼び、失敗したら処理を開始しない
- オプション2: 楽観的ロック（バージョン番号）を追加して検証
- オプション3: 生成キューを導入して順次処理

---

### [MEDIUM] USAGE-002: 特権ユーザーの上限超過許可ロジック

**ファイル**: `backend/app/domains/usage/service.py:83-97`

**問題**:
特権ユーザーは上限到達後も生成を許可し、手動でカウントをインクリメントしている。

**コード**:
```python
if not was_allowed and is_privileged:
    # 特権ユーザーが上限超過しても許可（手動インクリメント）
    self.db.table("usage_tracking").update({
        "articles_generated": row.get("new_count", 0) + 1,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", tracking["id"]).execute()
```

**影響**:
DB関数の`increment_usage_if_allowed()`をバイパスするため、原子性保証が失われる。

**推奨修正**:
- 特権ユーザーでもDB関数経由でインクリメントする
- または、特権ユーザーは制限を設けない設計に統一（カウントしない）

---

### [MEDIUM] USAGE-003: organization_members経由のアクセスで認可チェック不十分

**ファイル**: `backend/app/domains/usage/endpoints.py:133-153`

**問題**:
`_get_user_active_org()`で組織メンバーシップを確認するが、退会済みや招待中のステータスを考慮していない。

**コード**:
```python
memberships = supabase.table("organization_members").select(
    "organization_id"
).eq("user_id", user_id).execute()
# statusやroleの確認なし
```

**影響**:
退会処理中のメンバーや、まだ招待を受諾していないユーザーが使用量にアクセス可能な可能性。

**推奨修正**:
```python
memberships = supabase.table("organization_members").select(
    "organization_id"
).eq("user_id", user_id).eq("status", "active").execute()
```

---

### [MEDIUM] USAGE-004: 請求期間推定の不正確さ

**ファイル**: `backend/app/domains/usage/service.py:268-272`

**問題**:
`current_period_end`から30日前を`start`として推定しており、月によって不正確。

**コード**:
```python
from datetime import timedelta
end_dt = datetime.fromisoformat(period_end.replace("Z", "+00:00"))
start_dt = end_dt - timedelta(days=30)
```

**影響**:
実際の請求期間と異なる期間で使用量が追跡される可能性。31日の月、28日の月で誤差が発生。

**推奨修正**:
- `user_subscriptions`テーブルに`current_period_start`カラムを追加
- Stripe Webhookで更新時に両方の日付を保存

---

### [LOW] USAGE-005: 管理者エンドポイントでのSQL効率

**ファイル**: `backend/app/domains/usage/endpoints.py:70-93, 102-147`

**問題**:
`get_admin_usage_stats()`と`get_admin_user_usage()`で複数のDBクエリを実行。

**影響**:
データ量が増えるとパフォーマンス低下、DoS攻撃に弱くなる可能性。

**推奨修正**:
- JOINを使用した単一クエリに最適化
- ページネーション追加
- キャッシュ導入

---

### [LOW] USAGE-006: usage_logsへの重複記録の可能性

**ファイル**: `backend/app/domains/usage/service.py:294-304`

**問題**:
`_record_usage_log()`に重複チェックがない。

**コード**:
```python
def _record_usage_log(self, tracking_id, user_id, process_id):
    self.db.table("usage_logs").insert({
        "usage_tracking_id": tracking_id,
        "user_id": user_id,
        "generation_process_id": process_id,
    }).execute()
```

**影響**:
同じ`process_id`で複数回呼び出されると重複記録。

**推奨修正**:
```sql
ALTER TABLE usage_logs ADD CONSTRAINT uq_usage_log_process
    UNIQUE (usage_tracking_id, generation_process_id);
```

---

## 良い実装（セキュリティ観点）

### 1. increment_usage_if_allowed() PostgreSQL関数の原子性

**ファイル**: `shared/supabase/migrations/20260202000001_add_usage_limits.sql`

FOR UPDATE行ロックで競合条件を防止。インクリメント処理自体は安全に実装されている。

```sql
SELECT * INTO v_rec FROM usage_tracking WHERE id = p_tracking_id FOR UPDATE;
IF v_rec.articles_generated < (v_rec.articles_limit + v_rec.addon_articles_limit) THEN
    UPDATE usage_tracking SET articles_generated = articles_generated + 1 ...
```

### 2. RLSポリシー

- `usage_tracking`, `usage_logs`テーブルにRLSが有効
- `service_role`でのみ操作可能（バックエンドからのみアクセス）
- フロントエンドからの直接操作を防止

### 3. 特権ユーザーの早期リターン

`check_can_generate()`で特権ユーザーは即座に`allowed=True`を返す。パフォーマンス最適化とDB負荷軽減。

### 4. 認証の適用

- `GET /usage/current`: `get_current_user_id_from_token`で認証必須
- `GET /usage/admin/*`: `get_admin_user_email_from_token`で管理者認証必須
- `@shintairiku.jp`ドメイン制限が管理者APIに適用されている

---

## 推奨修正アクション（優先順位付き）

1. **[HIGH] TOCTOU競合条件の修正**
   - 生成開始時に`increment_usage_if_allowed()`を呼び、失敗したら処理を開始しない（予約方式）
   - 失敗した場合はロールバック用の`decrement_usage()`関数も用意

2. **[MEDIUM] 特権ユーザーのインクリメント処理を修正**
   - DBレベルで無制限を許可するか、別の関数を用意
   - 手動UPDATEではなくDB関数経由に統一

3. **[MEDIUM] organization_membersのステータス確認を追加**
   ```python
   .eq("status", "active")
   ```

4. **[MEDIUM] 請求期間の正確な取得**
   - `user_subscriptions`に`current_period_start`カラムを追加
   - Webhookで更新時に両方の日付を保存

5. **[LOW] usage_logsにUNIQUE制約追加**
   ```sql
   ALTER TABLE usage_logs ADD CONSTRAINT uq_usage_log_process
       UNIQUE (usage_tracking_id, generation_process_id);
   ```

6. **[LOW] 管理者APIにページネーションを追加**
