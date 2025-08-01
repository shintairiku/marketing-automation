# Clerk認証とデータベース連携の詳細仕様

## 概要

このドキュメントでは、Clerk認証システムとSupabaseデータベースの統合について詳細に解説します。フロントエンドでの認証UI実装、バックエンドでのJWT検証、そしてSupabase RLSポリシーとの連携によるデータアクセス制御の仕組みを説明します。

## Clerk認証システムの構成

### 1. フロントエンド認証実装

#### Clerk Provider設定

**ファイル**: `/frontend/src/app/layout.tsx` または Client Layout

```typescript
import { ClerkProvider } from '@clerk/nextjs';
import { dark } from '@clerk/themes';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider
      appearance={{
        baseTheme: dark,
        variables: {
          colorPrimary: '#667eea',
          colorBackground: '#111827',
          colorInputBackground: '#374151',
          colorInputText: '#f9fafb',
        },
        elements: {
          formButtonPrimary: 'bg-blue-600 hover:bg-blue-700',
          card: 'bg-gray-800 shadow-xl',
        },
      }}
    >
      <html lang="ja">
        <body>{children}</body>
      </html>
    </ClerkProvider>
  );
}
```

#### 認証コンポーネントの実装

**サインインページ**: `/frontend/src/app/sign-in/[[...sign-in]]/page.tsx`

```typescript
import { SignIn } from '@clerk/nextjs';

export default function SignInPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            アカウントにサインイン
          </h2>
        </div>
        <SignIn 
          path="/sign-in"
          routing="path"
          signUpUrl="/sign-up"
          afterSignInUrl="/dashboard"
          appearance={{
            elements: {
              rootBox: "w-full",
              card: "shadow-lg",
            }
          }}
        />
      </div>
    </div>
  );
}
```

**サインアップページ**: `/frontend/src/app/sign-up/[[...sign-up]]/page.tsx`

```typescript
import { SignUp } from '@clerk/nextjs';

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            新しいアカウントを作成
          </h2>
        </div>
        <SignUp 
          path="/sign-up"
          routing="path"
          signInUrl="/sign-in"
          afterSignUpUrl="/dashboard"
        />
      </div>
    </div>
  );
}
```

#### ユーザープロファイル

```typescript
import { UserProfile } from '@clerk/nextjs';

export default function UserProfilePage() {
  return (
    <div className="flex justify-center p-8">
      <UserProfile 
        path="/user-profile"
        routing="path"
        appearance={{
          elements: {
            rootBox: "w-full max-w-4xl",
            card: "shadow-xl",
          }
        }}
      />
    </div>
  );
}
```

### 2. 認証状態の管理

#### useUser フックの利用

```typescript
import { useUser } from '@clerk/nextjs';

export function ProfileComponent() {
  const { isLoaded, isSignedIn, user } = useUser();

  if (!isLoaded) {
    return <div>読み込み中...</div>;
  }

  if (!isSignedIn) {
    return <div>サインインしてください</div>;
  }

  return (
    <div>
      <h1>こんにちは、{user.firstName}さん！</h1>
      <p>メール: {user.primaryEmailAddress?.emailAddress}</p>
      <p>ユーザーID: {user.id}</p>
      <p>作成日: {user.createdAt?.toLocaleDateString()}</p>
    </div>
  );
}
```

#### useAuth フックによるトークン取得

```typescript
import { useAuth } from '@clerk/nextjs';

export function ApiCallComponent() {
  const { getToken, userId, isLoaded } = useAuth();

  const callAPI = async () => {
    if (!isLoaded || !userId) return;

    try {
      const token = await getToken();
      
      const response = await fetch('/api/proxy/articles', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        console.log('API Response:', data);
      }
    } catch (error) {
      console.error('API call failed:', error);
    }
  };

  return (
    <button onClick={callAPI} disabled={!isLoaded || !userId}>
      APIを呼び出す
    </button>
  );
}
```

## バックエンド認証実装

### 1. JWT検証とユーザーID抽出

**ファイル**: `/backend/app/common/auth.py`

```python
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from typing import Optional

security = HTTPBearer()

def get_current_user_id_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    ClerkのJWTトークンからユーザーIDを抽出する
    """
    try:
        token = credentials.credentials
        
        # Clerk JWTの公開鍵で検証（実際の実装では適切な検証が必要）
        # 開発環境では簡易的なデコード
        if os.getenv("ENVIRONMENT") == "development":
            decoded = jwt.decode(token, options={"verify_signature": False})
        else:
            # 本番環境では適切な署名検証を実装
            jwks_url = f"https://clerk.{os.getenv('CLERK_DOMAIN')}/.well-known/jwks.json"
            # JWKSを使った検証ロジック
            decoded = jwt.decode(token, options={"verify_signature": True})
        
        user_id = decoded.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
        
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    現在のユーザーIDを取得する（非同期版）
    """
    return get_current_user_id_from_token(credentials)

def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[str]:
    """
    オプショナルなユーザーID取得（認証が必須でない場合）
    """
    if not credentials:
        return None
    
    try:
        return get_current_user_id_from_token(credentials)
    except HTTPException:
        return None
```

### 2. APIエンドポイントでの認証利用

```python
from fastapi import APIRouter, Depends
from app.common.auth import get_current_user_id

router = APIRouter(prefix="/articles", tags=["articles"])

@router.get("/")
async def get_articles(
    user_id: str = Depends(get_current_user_id),
    db: Database = Depends(get_database)
):
    """
    ユーザーの記事一覧を取得
    """
    articles = await db.fetch_all(
        "SELECT * FROM articles WHERE user_id = :user_id ORDER BY created_at DESC",
        {"user_id": user_id}
    )
    return articles

@router.post("/")
async def create_article(
    article_data: ArticleCreateSchema,
    user_id: str = Depends(get_current_user_id),
    db: Database = Depends(get_database)
):
    """
    新しい記事を作成
    """
    article_id = await db.fetch_val(
        """
        INSERT INTO articles (user_id, title, content, created_at)
        VALUES (:user_id, :title, :content, NOW())
        RETURNING id
        """,
        {
            "user_id": user_id,
            "title": article_data.title,
            "content": article_data.content
        }
    )
    return {"id": article_id, "message": "Article created successfully"}
```

## データベース統合

### 1. ユーザーIDフィールドの設計

#### マイグレーション例

**ファイル**: `/frontend/supabase/migrations/20250105000000_fix_user_id_for_clerk.sql`

```sql
-- ClerkのユーザーID形式に対応するためuser_idカラムをTEXT型に変更
ALTER TABLE articles ALTER COLUMN user_id TYPE TEXT;
ALTER TABLE companies ALTER COLUMN user_id TYPE TEXT;
ALTER TABLE generated_articles_state ALTER COLUMN user_id TYPE TEXT;
ALTER TABLE customers ALTER COLUMN id TYPE TEXT;

-- インデックスの再作成
DROP INDEX IF EXISTS idx_articles_user_id;
CREATE INDEX idx_articles_user_id ON articles(user_id);

DROP INDEX IF EXISTS idx_companies_user_id;
CREATE INDEX idx_companies_user_id ON companies(user_id);

-- RLSポリシーの更新
DROP POLICY IF EXISTS "Users can only see their own articles" ON articles;
CREATE POLICY "Users can only see their own articles" ON articles
    FOR ALL USING (auth.jwt() ->> 'sub' = user_id);

DROP POLICY IF EXISTS "Users can only see their own companies" ON companies;
CREATE POLICY "Users can only see their own companies" ON companies
    FOR ALL USING (auth.jwt() ->> 'sub' = user_id);
```

### 2. Supabase RLSポリシーの設定

#### 基本的なRLSポリシー

```sql
-- RLSを有効化
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_articles_state ENABLE ROW LEVEL SECURITY;

-- ユーザー固有データのアクセス制御
CREATE POLICY "Users can manage their own articles" ON articles
    FOR ALL 
    USING (auth.jwt() ->> 'sub' = user_id)
    WITH CHECK (auth.jwt() ->> 'sub' = user_id);

CREATE POLICY "Users can manage their own companies" ON companies
    FOR ALL 
    USING (auth.jwt() ->> 'sub' = user_id)
    WITH CHECK (auth.jwt() ->> 'sub' = user_id);

CREATE POLICY "Users can manage their own generation processes" ON generated_articles_state
    FOR ALL 
    USING (auth.jwt() ->> 'sub' = user_id)
    WITH CHECK (auth.jwt() ->> 'sub' = user_id);
```

#### 高度なRLSポリシー例

```sql
-- 組織レベルのアクセス制御
CREATE POLICY "Organization members can access shared articles" ON articles
    FOR SELECT
    USING (
        user_id = (auth.jwt() ->> 'sub')
        OR 
        organization_id IN (
            SELECT organization_id 
            FROM organization_members 
            WHERE user_id = (auth.jwt() ->> 'sub')
        )
    );

-- 読み取り専用ユーザーへの制限
CREATE POLICY "Read-only users cannot modify articles" ON articles
    FOR UPDATE
    USING (
        auth.jwt() ->> 'sub' = user_id
        AND 
        (auth.jwt() ->> 'role')::jsonb ? 'write'
    );

-- 管理者による全データアクセス
CREATE POLICY "Admins can access all articles" ON articles
    FOR ALL
    USING (
        (auth.jwt() ->> 'role')::jsonb ? 'admin'
    );
```

### 3. データベースファンクションの活用

#### ユーザー認証ファンクション

```sql
-- ユーザー認証状態を確認するファンクション
CREATE OR REPLACE FUNCTION auth.user_id()
RETURNS TEXT AS $$
    SELECT COALESCE(
        current_setting('request.jwt.claims', true)::json ->> 'sub',
        (current_setting('request.jwt.claims', true)::json ->> 'user_id')
    );
$$ LANGUAGE sql STABLE;

-- 組織メンバーシップを確認するファンクション
CREATE OR REPLACE FUNCTION auth.is_organization_member(org_id UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM organization_members
        WHERE user_id = auth.user_id()
        AND organization_id = org_id
        AND status = 'active'
    );
$$ LANGUAGE sql STABLE SECURITY DEFINER;
```

## フロントエンド・バックエンド連携

### 1. APIプロキシの実装

**ファイル**: `/frontend/src/app/api/proxy/[...path]/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path: pathArray } = await params;
  const pathString = pathArray.join('/');
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${API_BASE_URL}/${pathString}${searchParams ? `?${searchParams}` : ''}`;

  // Authorization ヘッダーの転送
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  
  const authHeader = request.headers.get('Authorization');
  if (authHeader) {
    headers.Authorization = authHeader;
  }

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers,
    });

    const data = await response.json();

    return NextResponse.json(data, { 
      status: response.status,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      },
    });
  } catch (error) {
    console.error('Proxy API error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch from backend API' },
      { status: 500 }
    );
  }
}

// POST, PUT, DELETE メソッドも同様に実装
```

### 2. 認証付きAPIクライアント

```typescript
import { useAuth } from '@clerk/nextjs';

export class AuthenticatedApiClient {
  private getToken: () => Promise<string | null>;
  private baseURL: string;

  constructor(getToken: () => Promise<string | null>, baseURL: string = '/api/proxy') {
    this.getToken = getToken;
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = await this.getToken();
    
    const url = `${this.baseURL}/${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers,
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  async post<T>(endpoint: string, data: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async put<T>(endpoint: string, data: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

// 使用例
export function useApiClient() {
  const { getToken } = useAuth();
  
  return useMemo(() => new AuthenticatedApiClient(getToken), [getToken]);
}
```

### 3. カスタムフックの実装

```typescript
import { useAuth } from '@clerk/nextjs';
import { useState, useEffect } from 'react';

export function useArticles() {
  const { getToken, userId } = useAuth();
  const [articles, setArticles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchArticles = async () => {
    if (!userId) return;

    try {
      setIsLoading(true);
      const token = await getToken();
      
      const response = await fetch('/api/proxy/articles', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch articles');
      }

      const data = await response.json();
      setArticles(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const createArticle = async (articleData: any) => {
    const token = await getToken();
    
    const response = await fetch('/api/proxy/articles', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(articleData),
    });

    if (!response.ok) {
      throw new Error('Failed to create article');
    }

    const newArticle = await response.json();
    setArticles(prev => [newArticle, ...prev]);
    return newArticle;
  };

  useEffect(() => {
    fetchArticles();
  }, [userId]);

  return {
    articles,
    isLoading,
    error,
    createArticle,
    refetch: fetchArticles,
  };
}
```

## セキュリティ最適化

### 1. JWT検証の強化

```python
import requests
import jwt
from jwt import PyJWKClient
from functools import lru_cache

class ClerkJWTValidator:
    def __init__(self, domain: str):
        self.domain = domain
        self.jwks_url = f"https://{domain}/.well-known/jwks.json"
        self.jwks_client = PyJWKClient(self.jwks_url)
    
    @lru_cache(maxsize=100)
    def get_signing_key(self, kid: str):
        """JWKSから署名キーを取得（キャッシュ付き）"""
        return self.jwks_client.get_signing_key(kid)
    
    def validate_token(self, token: str) -> dict:
        """JWT トークンを検証し、ペイロードを返す"""
        try:
            # ヘッダーを取得してkidを確認
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')
            
            if not kid:
                raise ValueError("Token missing 'kid' in header")
            
            # 署名キーを取得
            signing_key = self.get_signing_key(kid)
            
            # トークンを検証
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=f"https://{self.domain}",
                options={"require": ["exp", "iat", "sub"]}
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidAudienceError:
            raise ValueError("Invalid token audience")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")

# 使用例
jwt_validator = ClerkJWTValidator(os.getenv('CLERK_DOMAIN'))

def get_current_user_id_secure(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    try:
        payload = jwt_validator.validate_token(credentials.credentials)
        return payload['sub']
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
```

### 2. レート制限の実装

```python
from fastapi import Request
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, user_id: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds
        
        # 古いリクエストを削除
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if req_time > window_start
        ]
        
        # リクエスト数をチェック
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # 新しいリクエストを記録
        self.requests[user_id].append(now)
        return True

rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

def rate_limit_dependency(
    user_id: str = Depends(get_current_user_id)
) -> str:
    if not rate_limiter.is_allowed(user_id):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    return user_id
```

## 監視とログ

### 1. 認証ログの実装

```python
import logging
from datetime import datetime

# 認証専用ログ設定
auth_logger = logging.getLogger('auth')
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
auth_logger.addHandler(handler)
auth_logger.setLevel(logging.INFO)

def log_authentication_event(
    event_type: str,
    user_id: str = None,
    request: Request = None,
    additional_data: dict = None
):
    """認証イベントをログに記録"""
    log_data = {
        'event_type': event_type,
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
    }
    
    if request:
        log_data.update({
            'ip_address': request.client.host,
            'user_agent': request.headers.get('user-agent'),
            'endpoint': str(request.url),
            'method': request.method,
        })
    
    if additional_data:
        log_data.update(additional_data)
    
    auth_logger.info(f"Auth Event: {log_data}")

# 使用例
async def get_current_user_id_with_logging(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    try:
        user_id = get_current_user_id_from_token(credentials)
        log_authentication_event('auth_success', user_id, request)
        return user_id
    except HTTPException as e:
        log_authentication_event(
            'auth_failure', 
            None, 
            request, 
            {'error': str(e.detail)}
        )
        raise
```

### 2. メトリクス収集

```python
from prometheus_client import Counter, Histogram, generate_latest
import time

# メトリクス定義
auth_requests_total = Counter(
    'auth_requests_total',
    'Total authentication requests',
    ['status', 'endpoint']
)

auth_duration_seconds = Histogram(
    'auth_duration_seconds',
    'Authentication request duration'
)

def collect_auth_metrics(
    status: str,
    endpoint: str,
    duration: float
):
    """認証メトリクスを収集"""
    auth_requests_total.labels(status=status, endpoint=endpoint).inc()
    auth_duration_seconds.observe(duration)

# デコレータとしての使用
def with_auth_metrics(func):
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        status = 'success'
        
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            status = 'failure'
            raise
        finally:
            duration = time.time() - start_time
            endpoint = kwargs.get('request', {}).get('url', {}).get('path', 'unknown')
            collect_auth_metrics(status, endpoint, duration)
    
    return wrapper
```

## トラブルシューティング

### よくある問題と解決方法

1. **JWT署名検証エラー**
   ```python
   # 問題: 署名検証に失敗する
   # 解決: JWKSエンドポイントの確認
   jwks_url = f"https://clerk.{domain}/.well-known/jwks.json"
   response = requests.get(jwks_url)
   print("JWKS Response:", response.json())
   ```

2. **ユーザーIDの不整合**
   ```sql
   -- 問題: user_idの型が一致しない
   -- 解決: データ型の統一
   ALTER TABLE articles ALTER COLUMN user_id TYPE TEXT;
   ```

3. **RLSポリシーの設定ミス**
   ```sql
   -- 問題: ポリシーが適用されない
   -- 解決: ポリシーの確認と修正
   SELECT schemaname, tablename, policyname, cmd, qual 
   FROM pg_policies 
   WHERE tablename = 'articles';
   ```

## 結論

このClerk認証とデータベース連携システムにより、以下の利点を実現しています：

1. **統合認証**: フロントエンドとバックエンドの一貫した認証
2. **セキュリティ**: JWT検証とRLSによる多層防御
3. **スケーラビリティ**: 効率的なトークン管理とキャッシュ
4. **監視可能性**: 包括的なログとメトリクス
5. **保守性**: 明確な責任分離と設定管理
6. **ユーザビリティ**: シームレスな認証体験

この設計により、安全で使いやすい認証システムを構築し、アプリケーション全体のセキュリティを確保しています。