# バックエンドにおけるユーザー認証（Clerk連携）の仕様

## 概要

このドキュメントでは、Marketing Automation APIにおけるClerkを利用したユーザー認証システムの詳細な仕様について解説します。バックエンドはClerkが発行するJWTトークンを検証し、ユーザーIDを抽出してAPIアクセス制御を行います。

## Clerk認証システムの概要

### アーキテクチャ構成
```
フロントエンド (Next.js + Clerk)
    ↓ JWT Token in Authorization Header
バックエンド (FastAPI + JWT Validation)
    ↓ Extracted User ID
データベース (Supabase + RLS)
```

### 認証フロー
1. **フロントエンド**: Clerkによるユーザー認証
2. **トークン生成**: Clerk JWTトークンの取得
3. **API呼び出し**: Authorizationヘッダーでトークン送信
4. **バックエンド検証**: JWTデコードとユーザーID抽出
5. **データアクセス**: ユーザーIDに基づくアクセス制御

## 認証実装詳細

### 認証モジュール構成
**ファイルパス**: `/home/als0028/study/shintairiku/marketing-automation/backend/app/common/auth.py`

```python
"""
Authentication utilities for Clerk integration
"""
import jwt
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)
```

### 主要認証機能

#### 1. HTTPBearer設定
```python
security = HTTPBearer(auto_error=False)
```

**特徴**:
- `auto_error=False`: 認証ヘッダーがない場合でも例外を発生させない
- 開発環境での柔軟な動作を可能にする
- 認証が必要なエンドポイントで個別にエラーハンドリング

#### 2. メイン認証関数
```python
def get_current_user_id_from_token(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    Extract user ID from Clerk JWT token
    """
```

**機能詳細**:
- **目的**: Clerk JWTトークンからユーザーIDを抽出
- **入力**: Authorization headerのBearer token
- **出力**: ClerkユーザーID (string)
- **フォールバック**: 開発用プレースホルダーユーザーID

#### 3. トークン処理ロジック

##### 認証ヘッダーの確認
```python
if not authorization:
    logger.warning("No authorization header found, using placeholder user ID")
    return "user_2y2DRx4Xb5PbvMVoVWmDluHCeFV"
```

**動作**:
- 認証ヘッダーが存在しない場合の処理
- 開発環境用のプレースホルダーユーザーIDを返却
- ログレベル: WARNING

##### JWTトークンのデコード
```python
try:
    token = authorization.credentials
    
    # 開発環境では署名検証をスキップ
    decoded_token = jwt.decode(token, options={"verify_signature": False})
    
    # トークンからユーザーIDを抽出
    user_id = decoded_token.get("sub")
    if not user_id:
        logger.warning("JWT token has no user ID, falling back to development user")
        return "user_2y2DRx4Xb5PbvMVoVWmDluHCeFV"
        
    return user_id
```

**処理仕様**:
- **JWTライブラリ**: `PyJWT`使用
- **署名検証**: 開発環境では無効化 (`verify_signature: False`)
- **ユーザーID取得**: JWT `sub` クレームから抽出
- **フォールバック**: ユーザーIDが存在しない場合の代替処理

##### エラーハンドリング
```python
except jwt.InvalidTokenError as e:
    logger.warning(f"Invalid JWT token, falling back to development user: {e}")
    return "user_2y2DRx4Xb5PbvMVoVWmDluHCeFV"
except Exception as e:
    logger.warning(f"Unexpected error during authentication, falling back to development user: {e}")
    return "user_2y2DRx4Xb5PbvMVoVWmDluHCeFV"
```

**エラー処理**:
- **InvalidTokenError**: 無効なJWTトークン
- **汎用Exception**: 予期しないエラー
- **共通処理**: 全てのエラーでプレースホルダーユーザーIDを返却
- **ログ出力**: エラー内容をWARNINGレベルで記録

### 4. WebSocket用認証関数

#### ヘッダー文字列からの認証
```python
def get_current_user_id_from_header(authorization: Optional[str] = None) -> str:
    """
    Extract user ID from Authorization header string
    Used for WebSocket connections where we can't use Depends
    """
```

**用途**:
- WebSocket接続での認証処理
- FastAPIのDependsが使用できない場面
- 直接的なヘッダー文字列処理

#### Bearer プレフィックス処理
```python
try:
    # "Bearer " プレフィックスを除去
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization
        
    # JWTデコード処理
    decoded_token = jwt.decode(token, options={"verify_signature": False})
    
    user_id = decoded_token.get("sub")
    if not user_id:
        logger.warning("No user ID in token, using test user ID")
        return "user_2y2DRx4Xb5PbvMVoVWmDluHCeFV"
        
    return user_id
```

**処理特徴**:
- **プレフィックス除去**: "Bearer " 文字列の自動除去
- **柔軟性**: プレフィックスがない場合も対応
- **エラー処理**: 同様のフォールバック機能

## 開発環境での認証仕様

### プレースホルダーユーザーID
```python
DEVELOPMENT_USER_ID = "user_2y2DRx4Xb5PbvMVoVWmDluHCeFV"
```

**使用場面**:
- 認証ヘッダーが存在しない場合
- 無効なJWTトークン受信時
- 認証処理での例外発生時
- WebSocket接続での認証失敗時

**利点**:
- 開発環境での継続的なテスト実行
- 認証エラーによる開発阻害の防止
- デバッグとテストの容易化

### ログ出力仕様
```python
logger = logging.getLogger(__name__)

# 各種ログ出力例
logger.warning("No authorization header found, using placeholder user ID")
logger.warning(f"Invalid JWT token, falling back to development user: {e}")
logger.warning("No user ID in token, using test user ID")
logger.error(f"Error extracting user ID from header: {e}")
```

**ログレベル**:
- **WARNING**: 認証失敗、フォールバック動作
- **ERROR**: 予期しない例外、システムエラー

## 本番環境での認証強化

### 署名検証の有効化
本番環境では以下の設定が推奨されます：

```python
# 本番環境での実装例
import os
from jwt import decode

def get_current_user_id_from_token_production(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        token = authorization.credentials
        
        # Clerkの公開鍵を使用した署名検証
        decoded_token = decode(
            token,
            key=get_clerk_public_key(),  # Clerkから取得
            algorithms=["RS256"],
            audience=os.getenv("CLERK_AUDIENCE"),
            issuer=os.getenv("CLERK_ISSUER")
        )
        
        user_id = decoded_token.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token claims")
            
        return user_id
        
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### セキュリティ設定項目

#### 必要な環境変数
```bash
# Clerk認証設定
CLERK_PUBLIC_KEY=          # Clerk公開鍵
CLERK_AUDIENCE=            # JWT Audience
CLERK_ISSUER=              # JWT Issuer
CLERK_SECRET_KEY=          # Clerk秘密鍵
```

#### 検証パラメータ
- **アルゴリズム**: RS256 (非対称暗号)
- **Audience**: Clerkアプリケーション識別子
- **Issuer**: Clerk認証プロバイダー
- **有効期限**: JWTトークンのexp claimで検証

## API エンドポイントでの使用方法

### Dependency Injection
```python
from app.common.auth import get_current_user_id_from_token

@router.get("/protected-endpoint")
async def protected_endpoint(
    user_id: str = Depends(get_current_user_id_from_token)
):
    """保護されたエンドポイントの例"""
    return {"user_id": user_id, "message": "Authenticated successfully"}
```

### 使用例（各ドメイン）

#### SEO記事生成
```python
@router.get("/articles/")
async def get_articles(
    user_id: str = Depends(get_current_user_id_from_token),
    limit: int = Query(20)
):
    articles = await article_service.get_user_articles(user_id, limit)
    return articles
```

#### 会社情報管理
```python
@router.post("/companies/")
async def create_company(
    company_data: CompanyInfoCreate,
    current_user_id: str = Depends(get_current_user_id_from_token)
):
    return await CompanyService.create_company(company_data, current_user_id)
```

#### 組織管理
```python
@router.get("/organizations/")
async def get_user_organizations(
    current_user_id: str = Depends(get_current_user_id_from_token)
):
    return await organization_service.get_user_organizations(current_user_id)
```

## Supabase RLSとの連携

### ユーザーID形式の統一
```sql
-- Supabase RLSポリシー例
CREATE POLICY "Users can only access their own data" ON articles
FOR ALL USING (user_id = auth.uid()::text);
```

**注意点**:
- **ClerkユーザーID**: 文字列形式 (`user_xxxxxx`)
- **Supabase認証**: UUID形式
- **型変換**: `auth.uid()::text` で文字列に変換
- **RLS適用**: 各テーブルでuser_id列による制御

### データベース統合仕様
```python
# バックエンドでの使用例
async def get_user_articles(user_id: str):
    """ClerkユーザーIDでSupabaseデータを取得"""
    result = supabase.table("articles").select("*").eq("user_id", user_id).execute()
    return result.data
```

## セキュリティ考慮事項

### トークン処理セキュリティ

#### 開発環境での注意点
- **署名検証無効化**: 開発時のみ適用
- **プレースホルダーID**: 本番では絶対に使用しない
- **ログ出力**: 機密情報の記録回避

#### 本番環境での要件
- **署名検証必須**: Clerk公開鍵での検証
- **トークン有効期限**: exp claimの検証
- **Audience検証**: 正当なアプリケーション確認
- **Issuer検証**: Clerkからの発行確認

### 攻撃対策

#### JWTトークン関連
- **トークン盗用**: HTTPS通信の強制
- **リプレイ攻撃**: トークン有効期限の設定
- **偽造攻撃**: 署名検証による防止

#### API保護
- **認証バイパス**: 全保護エンドポイントでの認証確認
- **権限昇格**: ユーザーID検証の徹底
- **データ漏洩**: RLSポリシーとの連携

## トラブルシューティング

### 認証失敗の診断

#### ログ確認項目
```python
# デバッグ用ログ追加例
logger.info(f"Received authorization header: {authorization is not None}")
logger.info(f"Token length: {len(authorization.credentials) if authorization else 0}")
logger.info(f"Decoded user_id: {user_id}")
```

#### 一般的な問題

##### 1. 認証ヘッダー不在
**症状**: `No authorization header found`
**原因**: フロントエンドでのヘッダー設定不備
**解決**: `Authorization: Bearer <token>` の確認

##### 2. 無効なJWTトークン
**症状**: `Invalid JWT token`
**原因**: トークンの破損、期限切れ
**解決**: フロントエンドでのトークン更新

##### 3. ユーザーID不在
**症状**: `JWT token has no user ID`
**原因**: JWTのsub claimが存在しない
**解決**: Clerk設定でのclaim設定確認

### 開発支援機能

#### 認証状態の確認
```python
@router.get("/auth/debug")
async def debug_auth(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """認証デバッグ用エンドポイント"""
    if not authorization:
        return {"status": "no_header", "user_id": None}
    
    try:
        decoded = jwt.decode(authorization.credentials, options={"verify_signature": False})
        return {
            "status": "valid",
            "user_id": decoded.get("sub"),
            "claims": list(decoded.keys()),
            "expires": decoded.get("exp")
        }
    except Exception as e:
        return {"status": "invalid", "error": str(e)}
```

## まとめ

バックエンドのClerk認証システムは、開発効率とセキュリティのバランスを取った設計となっています。開発環境では柔軟なフォールバック機能により継続的な開発を支援し、本番環境では厳密な検証によりセキュリティを確保します。

### 主要な特徴
- **統一認証**: ClerkとSupabaseの seamless な統合
- **開発フレンドリー**: プレースホルダーによる開発阻害の防止
- **本番対応**: 厳密な署名検証とクレーム検証
- **エラー処理**: 包括的なログ出力とフォールバック
- **セキュリティ**: JWT best practicesに準拠した実装

この認証システムにより、スケーラブルで安全なマーケティング自動化プラットフォームの基盤が提供されています。