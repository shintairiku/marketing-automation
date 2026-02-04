# セキュリティ修正の詳細分析

セキュリティレポートの各問題について、何をすれば解決するのかを分類しました。

---

## TL;DR (結論)

| 解決方法 | 対象の問題 | 必要な作業 |
|---------|-----------|-----------|
| **インフラ設定変更** | CRIT-01 | Cloud Run IAM設定、またはAPI Gateway追加 |
| **マイグレーション追加** | CRIT-02 | 新しいRLSポリシーを定義するSQLファイル作成 |
| **コード修正** | HIGH-01〜07, MED, LOW | ソースコードの修正 |
| **設定ファイル変更** | HIGH-04, MED-05, MED-06 | next.config.js, Dockerfile, pyproject.toml |
| **CI/CD追加** | LOW-03 | GitHub Actions ワークフロー追加 |

**「BFFを追加する」必要はない** — 既にNext.js API Routesが BFF として機能している。問題は既存のBFF（プロキシ）に認証チェックがないこと。

---

## 問題別の詳細分析

### 🔴 CRIT-01: Cloud Runへの直接アクセス

**現状の問題:**
```
攻撃者 → Cloud Run URL を直接叩く → バックエンドAPI → データベース
         ↑ Next.js middleware をバイパス
```

**解決オプション:**

| オプション | 方法 | 難易度 | 推奨 |
|-----------|------|--------|------|
| A | Cloud Run を「認証が必要」に変更 + Next.jsにサービスアカウント付与 | 中 | ⭐⭐⭐ |
| B | バックエンドにAPIキー認証を追加（プロキシが固定キーを付与） | 低 | ⭐⭐ |
| C | Cloud Load Balancer + IAP を前段に配置 | 高 | ⭐ |

**推奨: オプションB（最も簡単）**

```python
# backend/main.py に追加
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

@app.middleware("http")
async def verify_internal_key(request: Request, call_next):
    if request.url.path not in ["/health", "/"]:
        api_key = request.headers.get("X-Internal-API-Key")
        if api_key != INTERNAL_API_KEY:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)
```

```typescript
// frontend/src/app/api/proxy/[...path]/route.ts に追加
headers['X-Internal-API-Key'] = process.env.INTERNAL_API_KEY;
```

**これはマイグレーションでは解決できない。コード修正 + 環境変数追加が必要。**

---

### 🔴 CRIT-02: RLSポリシーの削除

**現状の問題:**
- `20260130000003_fix_org_clerk_compat.sql` で全てのRLSポリシーが削除された
- RLSは有効だがポリシーがない = 全アクセス拒否（anon key）または全アクセス許可（service_role）

**解決方法: 新しいマイグレーションファイルを作成**

```sql
-- shared/supabase/migrations/20260203000001_restore_rls_policies.sql

-- Clerk JWT の sub クレームを使用する RLS ポリシー

-- organizations: メンバーのみ参照可能
CREATE POLICY "Organization members can view their organizations" ON organizations
  FOR SELECT USING (
    id IN (
      SELECT organization_id FROM organization_members
      WHERE user_id = (current_setting('request.jwt.claims', true)::json->>'sub')
    )
  );

-- articles: 自身の記事のみ参照/更新可能
CREATE POLICY "Users can manage their own articles" ON articles
  FOR ALL USING (
    user_id = (current_setting('request.jwt.claims', true)::json->>'sub')
  );

-- generated_articles_state: 自身のプロセスのみ参照/更新可能
CREATE POLICY "Users can manage their own generation processes" ON generated_articles_state
  FOR ALL USING (
    user_id = (current_setting('request.jwt.claims', true)::json->>'sub')
  );

-- blog_generation_state: 自身のプロセスのみ参照/更新可能
CREATE POLICY "Users can manage their own blog processes" ON blog_generation_state
  FOR ALL USING (
    user_id = (current_setting('request.jwt.claims', true)::json->>'sub')
  );

-- wordpress_sites: 自身のサイトのみ参照可能
CREATE POLICY "Users can manage their own sites" ON wordpress_sites
  FOR ALL USING (
    user_id = (current_setting('request.jwt.claims', true)::json->>'sub')
  );

-- 他のテーブルも同様に...
```

**ただし注意点:**
1. バックエンドは `service_role_key` を使っているので、RLSポリシーはバイパスされる
2. RLSが効くのは `anon_key` を使った場合（フロントエンドの Realtime など）
3. 既存の Realtime サブスクリプションが壊れないか検証が必要

**これはマイグレーションで解決できる。**

```bash
# マイグレーション適用
cd shared/supabase
npx supabase db push
```

---

### 🟠 HIGH-01: DEBUGモードの署名スキップ

**解決方法: コード削除**

```python
# backend/app/common/auth.py から以下を削除
if DEBUG_MODE:
    logger.warning("⚠️ [AUTH] DEBUG MODE: Skipping JWT signature verification!")
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
```

**これはコード修正。マイグレーション不要。**

---

### 🟠 HIGH-02: レート制限の欠如

**解決方法: slowapi ライブラリ追加 + コード修正**

```bash
cd backend
uv add slowapi
```

```python
# backend/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# エンドポイントに適用
@router.post("/blog/generation/start")
@limiter.limit("5/minute")  # 1分5回まで
async def start_blog_generation(...):
    ...
```

**これはパッケージ追加 + コード修正。マイグレーション不要。**

---

### 🟠 HIGH-03: プロキシのCORS問題

**解決方法: コード修正**

```typescript
// frontend/src/app/api/proxy/[...path]/route.ts

// 削除: 'Access-Control-Allow-Origin': '*'
// 追加: Clerk認証チェック
import { auth } from '@clerk/nextjs/server';

export async function GET(request: NextRequest, ...) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }
  // ... 既存のプロキシロジック
}
```

**これはコード修正。マイグレーション不要。**

---

### 🟠 HIGH-04: セキュリティヘッダーの欠如

**解決方法: 設定ファイル修正**

```javascript
// frontend/next.config.js
module.exports = {
  async headers() {
    return [{
      source: '/(.*)',
      headers: [
        { key: 'X-Frame-Options', value: 'DENY' },
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
        { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
      ],
    }];
  },
  // ... 既存の設定
};
```

**これは設定ファイル修正。マイグレーション不要。**

---

### 🟠 HIGH-05: XSS脆弱性

**解決方法: ライブラリ追加 + コード修正**

```bash
cd frontend
bun add dompurify @types/dompurify
```

```tsx
// 使用箇所で
import DOMPurify from 'dompurify';

// Before
dangerouslySetInnerHTML={{ __html: block.content }}

// After
dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(block.content) }}
```

**これはパッケージ追加 + コード修正。マイグレーション不要。**

---

### 🟠 HIGH-06: service_role キーの乱用

**解決方法: アーキテクチャ変更（大規模）**

現状:
```
全てのDB操作 → service_role_key → RLSバイパス
```

理想:
```
読み取り操作 → anon_key + ユーザーJWT → RLS適用
書き込み操作 → service_role_key (必要な場合のみ)
```

**これは大規模なコード修正。優先度を下げてもよい（RLSポリシー復活が先）。**

---

### 🟠 HIGH-07: Stripe Webhook シークレット

**解決方法: コード修正**

```typescript
// frontend/src/app/api/subscription/webhook/route.ts
const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
if (!webhookSecret || webhookSecret.trim() === '') {
  console.error('STRIPE_WEBHOOK_SECRET is not configured');
  return NextResponse.json({ error: 'Server configuration error' }, { status: 500 });
}
```

**これはコード修正。マイグレーション不要。**

---

## 解決アクションのサマリー

### 今すぐやるべき（Critical + High）

| # | 作業 | 種類 | 工数 |
|---|------|------|------|
| 1 | バックエンドにAPIキー認証追加 | コード修正 | 2時間 |
| 2 | RLSポリシーのマイグレーション作成 | SQL作成 + `db push` | 8時間 |
| 3 | DEBUGモード署名スキップ削除 | コード修正 | 30分 |
| 4 | レート制限追加（slowapi） | パッケージ + コード | 4時間 |
| 5 | プロキシに認証チェック追加 | コード修正 | 2時間 |
| 6 | セキュリティヘッダー追加 | 設定ファイル | 1時間 |
| 7 | XSSサニタイズ（DOMPurify） | パッケージ + コード | 4時間 |

### マイグレーションで解決できるもの

**CRIT-02のみ**。新しいマイグレーションファイルを作成してRLSポリシーを定義する必要がある。

```bash
# 実行コマンド
cd shared/supabase
# 1. マイグレーションファイルを作成（手動で .sql ファイルを書く）
# 2. 適用
npx supabase db push
# 3. 検証
npx supabase db diff
```

### BFFについて

**既にBFF（Backend For Frontend）パターンは実装されている:**

```
ブラウザ → Next.js API Routes (/api/proxy/*) → FastAPI バックエンド
            ↑ これがBFF
```

問題は:
1. BFF（プロキシ）に認証チェックがない → **コード修正で解決**
2. BFFをバイパスしてバックエンドに直接アクセスできる → **インフラ設定で解決**

**新しくBFFを追加する必要はない。既存のBFFを強化する。**

---

## 優先順位付きアクションプラン

### Phase 1: 緊急対応（1-2日）

1. [ ] `backend/main.py` にAPIキー認証ミドルウェア追加
2. [ ] `frontend/src/app/api/proxy/[...path]/route.ts` にAPIキーヘッダー追加
3. [ ] Cloud Run の環境変数に `INTERNAL_API_KEY` 追加
4. [ ] `DEBUG=false` を本番環境で確認
5. [ ] DEBUGモードの署名スキップコードを削除

### Phase 2: RLS復活（3-5日）

1. [ ] 新しいマイグレーションファイル作成
2. [ ] Clerk JWT を使う RLS ポリシーを全テーブルに定義
3. [ ] ローカルでテスト
4. [ ] 本番環境に適用

### Phase 3: 追加対策（1週間）

1. [ ] slowapi でレート制限追加
2. [ ] セキュリティヘッダー追加
3. [ ] DOMPurify で XSS 対策
4. [ ] プロキシに Clerk 認証チェック追加

### Phase 4: 継続的改善

1. [ ] CI/CD にセキュリティスキャン追加
2. [ ] 依存パッケージのバージョン固定
3. [ ] Dockerfile の非root実行

---

## 結論

**「BFFやマイグレーション実行すればいい」は部分的にしか正しくない:**

- ✅ マイグレーション → RLSポリシー復活（CRIT-02）に有効
- ❌ BFF追加 → 不要。既存のBFFを修正する
- ⚠️ それだけでは不十分 → コード修正、インフラ設定変更も必要

最も重要なのは:
1. **バックエンドへの直接アクセスを防ぐ**（APIキー認証 or IAM設定）
2. **RLSポリシーを復活させる**（マイグレーション）
3. **DEBUGモードの署名スキップを削除**（コード修正）

この3つで Critical + High の主要な問題は解決できます。
