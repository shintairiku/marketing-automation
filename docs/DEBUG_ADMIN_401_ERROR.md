# Admin API 401エラー 調査レポート

## 問題の概要

本番環境（Cloud Run）で `/admin/*` エンドポイントが 401 Unauthorized を返す。ローカル環境では正常に動作していた。

## エラーログ

```
🔒 [ADMIN_AUTH] User not found in Clerk: user_2y2DRx4Xb5PbvMVoVWmDluHCeFV
INFO: 169.254.169.126:22740 - "GET /admin/usage/users HTTP/1.1" 401 Unauthorized
```

## 症状の詳細

| エンドポイント | ステータス | 認証方式 |
|---------------|-----------|---------|
| `/blog/sites` | ✅ 200 OK | `get_current_user_id_from_token()` |
| `/admin/stats/overview` | ❌ 401 | `get_admin_user_email_from_token()` |
| `/admin/usage/users` | ❌ 401 | `get_admin_user_email_from_token()` |
| `/admin/activity/recent` | ❌ 401 | `get_admin_user_email_from_token()` |

---

## 根本原因

**フロントエンドとバックエンドで異なるClerkプロジェクトを使用している**

### 認証フローの違い

#### `/blog/sites` (成功するケース)
```
1. Frontend → Clerk JWT発行 (プロジェクトA)
2. Backend → JWT署名検証 (公開鍵 = JWKS) → 成功
3. Backend → JWTから user_id 抽出 → 成功
4. → 認証完了、リクエスト処理
```

#### `/admin/*` (失敗するケース)
```
1. Frontend → Clerk JWT発行 (プロジェクトA)
2. Backend → JWT署名検証 (公開鍵 = JWKS) → 成功
3. Backend → JWTから user_id 抽出 → 成功
4. Backend → Clerk API呼び出し (CLERK_SECRET_KEY = プロジェクトB)
   → GET https://api.clerk.com/v1/users/{user_id}
   → 404 Not Found (ユーザーはプロジェクトBに存在しない)
5. → 401 Unauthorized
```

### なぜJWT署名検証は成功するのか？

JWT署名検証は **公開鍵（JWKS）** を使用します。
- `_get_clerk_jwks_url()` は `CLERK_PUBLISHABLE_KEY` から JWKS URLを生成
- または `CLERK_FRONTEND_API` 環境変数から直接取得

**重要**: フロントエンドとバックエンドの `CLERK_PUBLISHABLE_KEY` が同じであれば、JWT署名検証は成功します。

### なぜClerk API呼び出しは失敗するのか？

Clerk Backend API (`https://api.clerk.com/v1/users/{user_id}`) は **Secret Key** で認証します。

```python
# admin_auth.py:52-59
async with httpx.AsyncClient(timeout=10.0) as client:
    response = await client.get(
        f"https://api.clerk.com/v1/users/{user_id}",
        headers={
            "Authorization": f"Bearer {clerk_secret_key}",  # ← これ
            "Content-Type": "application/json"
        }
    )
```

- `clerk_secret_key` が **異なるClerkプロジェクト** のものだと
- そのプロジェクトには `user_2y2DRx4Xb5PbvMVoVWmDluHCeFV` は存在しない
- → 404 Not Found

---

## ローカルで動作した理由

ローカル環境では:
- フロントエンド (`frontend/.env.local`) と バックエンド (`backend/.env`) の両方で
- **同じClerkプロジェクト** のキーを使用していた
- → ユーザーIDが一致する

---

## 確認すべき項目

### 1. Vercel (フロントエンド) の環境変数
```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_xxx または pk_test_xxx
CLERK_SECRET_KEY=sk_live_xxx または sk_test_xxx
```

### 2. Cloud Run (バックエンド) の環境変数
```
CLERK_PUBLISHABLE_KEY=pk_live_xxx または pk_test_xxx
CLERK_SECRET_KEY=sk_live_xxx または sk_test_xxx
```

### 確認方法

1. **Clerk Dashboard** (https://dashboard.clerk.com/) にアクセス
2. 使用しているアプリケーションを選択
3. **API Keys** セクションで:
   - Publishable Key (`pk_live_xxx` または `pk_test_xxx`)
   - Secret Key (`sk_live_xxx` または `sk_test_xxx`)
4. **両方の環境（Vercel/Cloud Run）で同じプロジェクトのキー**が設定されていることを確認

---

## 解決策

### オプション1: Cloud Runの環境変数を修正

Cloud Run のコンソール、または `gcloud` CLI で:

```bash
gcloud run services update <SERVICE_NAME> \
  --set-env-vars="CLERK_SECRET_KEY=sk_live_正しいキー,CLERK_PUBLISHABLE_KEY=pk_live_正しいキー" \
  --region=asia-northeast1
```

### オプション2: Secret Managerを使用している場合

Secret Managerの該当シークレットを更新:

```bash
# 現在の値を確認
gcloud secrets versions access latest --secret="CLERK_SECRET_KEY"

# 新しい値を追加
echo -n "sk_live_正しいキー" | gcloud secrets versions add CLERK_SECRET_KEY --data-file=-
```

---

## 追加の確認ポイント

### JWTの issuer を確認

ログに出力されている `iss` (issuer) を確認:
```
🔒 [ADMIN_AUTH] JWT claims: iss=xxx, azp=xxx
```

- `iss` はJWTを発行したClerkのURL
- これがCloud Runの `CLERK_PUBLISHABLE_KEY` から生成されるURLと一致しているか確認

### Test環境 vs Live環境

- `pk_test_xxx` / `sk_test_xxx` → Development環境
- `pk_live_xxx` / `sk_live_xxx` → Production環境

**フロントエンドとバックエンドで環境（test/live）を揃える**

---

## コード改善の提案

将来的な問題を防ぐため、起動時にキーの整合性をチェックするコードを追加することを検討:

```python
# backend/main.py または config.py
def validate_clerk_configuration():
    """Clerkの設定が整合しているか確認"""
    import base64

    pk = os.getenv("CLERK_PUBLISHABLE_KEY", "")
    sk = os.getenv("CLERK_SECRET_KEY", "")

    if not pk or not sk:
        logger.warning("⚠️ Clerk keys not fully configured")
        return

    # pk_test_ と sk_live_ の混在をチェック
    pk_is_test = pk.startswith("pk_test_")
    sk_is_test = sk.startswith("sk_test_")

    if pk_is_test != sk_is_test:
        logger.error("🚨 CLERK KEY MISMATCH: Publishable key is %s but Secret key is %s",
                    "test" if pk_is_test else "live",
                    "test" if sk_is_test else "live")
```

---

## まとめ

| 項目 | 状況 |
|------|------|
| 根本原因 | フロントエンドとバックエンドで異なるClerkプロジェクトを使用 |
| 影響範囲 | `/admin/*` エンドポイント（Clerk APIでメール取得が必要なもの） |
| 解決策 | Cloud Run の `CLERK_SECRET_KEY` をフロントエンドと同じプロジェクトのものに変更 |
| 緊急度 | 高（管理機能が完全に使用不可） |

---

*調査日時: 2026-02-03*
