## 概要

`ClerkOrganizationValidator` は、Clerk の JWT を最小限にデコードし、組織メンバーシップを抽出して、管理者用の組織に所属しているかつ十分なロール（owner / admin）を持つかを検証するためのユーティリティです。

- JWT の最小検証（`sub` と未失効の `exp` を要求）
- 一般的なクレーム形式からの組織メンバーシップ抽出（単一のアクティブ組織 + 配列クレーム）
- 設定済みの管理者組織 ID/Slug とロールのチェック
- 例外クラスは `backend/app/domains/admin/auth/exceptions.py` を参照

注意: 現状、JWT 署名検証は未接続（`verify_signature=False`）。本番運用では Clerk の公開鍵/JWKS を用いた署名検証の導入が推奨

## 前提設定（環境変数）

- `ADMIN_ORGANIZATION_ID`（管理者組織の ID）
- `ADMIN_ORGANIZATION_SLUG`（管理者組織の Slug）
- `CLERK_JWT_VERIFICATION_ENABLED`（将来の署名検証切り替え用フラグ／現状はログ用途）

上記２つの値は、Clerk の Organization の設定から取得できます。
これらは `backend/app/core/config.py` の `settings` から読み込まれます。

## 基本的な使い方（バリデータを直接使用）

```python
from app.domains.admin.auth.clerk_validator import ClerkOrganizationValidator
from app.domains.admin.auth.exceptions import (
    InvalidJWTTokenError,
    OrganizationMembershipRequiredError,
    InsufficientPermissionsError,
    InvalidOrganizationError,
)

validator = ClerkOrganizationValidator()

try:
    admin_user = validator.validate_token_and_extract_admin_user(token)
    # 利用例
    print(admin_user.user_id)
    print(admin_user.email)
    print(admin_user.admin_organization_membership.organization_id)
    print(admin_user.admin_organization_membership.role)
except InvalidJWTTokenError as e:
    # 401 相当: トークン不正/失効
    ...
except OrganizationMembershipRequiredError as e:
    # 403 相当: 管理者組織のメンバーでない
    ...
except InsufficientPermissionsError as e:
    # 403 相当: ロールが admin/owner ではない
    ...
except InvalidOrganizationError as e:
    # 組織クレームの形式異常等
    ...
```

組織一覧だけが必要な場合は、次のヘルパーを使えます。

```python
org_ids = validator.get_user_organizations(token)  # List[str]
```

## FastAPI での利用（推奨）

共通の依存関数は `backend/app/common/auth.py` に用意されています。これを使うと、エラーハンドリングが HTTP レスポンスにマッピングされます。

```python
from fastapi import APIRouter, Depends
from app.domains.admin.auth.clerk_validator import AdminUser
from app.common.auth import get_current_admin_user

router = APIRouter()

@router.get("/admin/secure")
def secured_endpoint(admin: AdminUser = Depends(get_current_admin_user)):
    return {
        "user_id": admin.user_id,
        "email": admin.email,
        "org_id": admin.admin_organization_membership.organization_id,
        "role": admin.admin_organization_membership.role,
    }
```

`get_current_admin_user` は内部で `ClerkOrganizationValidator` を使用し、以下を実施します。
- JWT の最小検証とクレームの抽出
- 管理者組織メンバーシップの有無チェック
- ロール（owner/admin）の検証
- エラーを `HTTPException(401/403/500)` に変換

管理者ユーザーの ID のみが必要な場合は、`get_current_admin_user_id` を利用できます。

```python
from app.common.auth import get_current_admin_user_id

@router.get("/admin/user-id")
def admin_user_id(user_id: str = Depends(get_current_admin_user_id)):
    return {"user_id": user_id}
```

## 例外クラス（概要）

- `InvalidJWTTokenError`: トークンが不正・形式異常・失効
- `OrganizationMembershipRequiredError`: 管理者組織に所属していない
- `InsufficientPermissionsError`: 所属しているがロール不足（admin/owner 以外）
- `InvalidOrganizationError`: 組織クレームの構造が不正

## 実装メモ

- 現状、署名検証は未接続（`jwt.decode(..., options={"verify_signature": False})`）。将来、Clerk の公開鍵/JWKS 連携により有効化予定。
- トークンからの組織抽出は以下を優先：
  - 単一アクティブ組織: `org_id|organization_id`, `org_slug|organization_slug`, `org_role|organization_role`
  - 配列形式: `org_memberships|organization_memberships`
- 必須クレームは `sub` と未失効の `exp` のみ。その他は極力シンプルに保ち、必要に応じて拡張する。


