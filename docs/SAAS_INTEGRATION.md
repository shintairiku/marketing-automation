# SaaS 連携実装ガイド

このドキュメントでは、WordPress MCP Ability Suite プラグインと連携する SaaS サービスの実装方法を詳しく説明します。

## 目次

1. [概要](#概要)
2. [連携フロー](#連携フロー)
3. [エンドポイント実装](#エンドポイント実装)
4. [MCP 通信](#mcp-通信)
5. [データベース設計](#データベース設計)
6. [セキュリティ考慮事項](#セキュリティ考慮事項)
7. [エラーハンドリング](#エラーハンドリング)
8. [実装例](#実装例)
9. [トラブルシューティング](#トラブルシューティング)

---

## 概要

WordPress MCP Ability Suite は、ワンクリックで SaaS サービスと連携できる仕組みを提供します。

### 連携の特徴

- **ユーザー体験**: ボタンを押すだけで連携完了
- **セキュリティ**: 一時的な登録コードによる安全なクレデンシャル交換
- **永続性**: アクセストークンは期限切れしない
- **フルアクセス**: read / write / admin のすべての権限を取得

### 前提条件

- SaaS サービスは HTTPS でホストされていること
- WordPress サイトも HTTPS を推奨
- SaaS は外部への HTTP リクエストを発行できること

---

## 連携フロー

### シーケンス図

```
┌────────────┐     ┌────────────┐     ┌────────────┐
│   User     │     │ WordPress  │     │   SaaS     │
│  Browser   │     │   Plugin   │     │  Service   │
└─────┬──────┘     └─────┬──────┘     └─────┬──────┘
      │                  │                  │
      │ 1. 「連携する」クリック              │
      ├─────────────────>│                  │
      │                  │                  │
      │ 2. registration_code 生成           │
      │                  │                  │
      │ 3. SaaS にリダイレクト               │
      │<─────────────────┤                  │
      │ Location: {saas_url}/connect/wordpress?...
      │                  │                  │
      ├──────────────────────────────────────>
      │                  │                  │
      │                  │ 4. register API 呼出
      │                  │<─────────────────┤
      │                  │ POST /register   │
      │                  │                  │
      │                  │ 5. credentials 返却
      │                  ├─────────────────>│
      │                  │                  │
      │                  │ 6. 認証情報を保存 │
      │                  │                  │
      │ 7. callback にリダイレクト           │
      │<──────────────────────────────────────
      │ Location: /connection-callback?status=success
      │                  │                  │
      ├─────────────────>│                  │
      │ 8. 連携完了表示  │                  │
      │                  │                  │
      │                  │                  │
      │                  │ 9. MCP 通信開始  │
      │                  │<=================>
      │                  │                  │
```

### フロー詳細

| ステップ | アクター | 説明 |
|---------|---------|------|
| 1 | User | WordPress 管理画面で「SaaS と連携する」ボタンをクリック |
| 2 | WordPress | 一時的な `registration_code`（有効期限 10 分）を生成 |
| 3 | WordPress | SaaS の `/connect/wordpress` にリダイレクト |
| 4 | SaaS | WordPress の `/wp-mcp/v1/register` API を呼び出し |
| 5 | WordPress | クレデンシャル（access_token, api_key, api_secret）を返却 |
| 6 | SaaS | 受け取った認証情報をデータベースに保存 |
| 7 | SaaS | WordPress の `callback_url` にリダイレクト |
| 8 | WordPress | 「連携完了」メッセージを表示 |
| 9 | SaaS | 保存した認証情報で MCP 通信を開始 |

---

## エンドポイント実装

### 重要: URL 設定について

WordPress プラグインは、管理画面で設定された URL に `/connect/wordpress` を **自動的に追加** してリダイレクトします。

```php
// プラグイン内部の処理（class-admin-settings.php:153）
trailingslashit( $saas_url ) . 'connect/wordpress'
```

| WordPress で設定する URL | リダイレクト先 |
|-------------------------|---------------|
| `https://your-saas.com` | `https://your-saas.com/connect/wordpress?...` |
| `https://your-saas.com/api` | `https://your-saas.com/api/connect/wordpress?...` |

**ユーザーへの案内**:
- ✅ `https://your-saas.com` または `https://your-saas.com/api`
- ❌ `https://your-saas.com/connect/wordpress`（二重パスになる）

### 1. 連携開始エンドポイント

WordPress からのリダイレクトを受け取るエンドポイントを実装します。

**URL**: `GET /connect/wordpress`

**受信パラメータ**:

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| `action` | string | 常に `wordpress_mcp_connect` |
| `site_url` | string | WordPress サイトの URL（URL エンコード済み） |
| `site_name` | string | WordPress サイト名（URL エンコード済み） |
| `mcp_endpoint` | string | MCP サーバーエンドポイント（URL エンコード済み） |
| `register_endpoint` | string | 登録 API エンドポイント（URL エンコード済み） |
| `registration_code` | string | 一時登録コード（64 文字、英数字） |
| `callback_url` | string | 完了後のコールバック URL（URL エンコード済み） |

**実装例（Node.js/Express）**:

```javascript
app.get('/connect/wordpress', async (req, res) => {
  const {
    action,
    site_url,
    site_name,
    mcp_endpoint,
    register_endpoint,
    registration_code,
    callback_url
  } = req.query;

  // 1. パラメータ検証
  if (action !== 'wordpress_mcp_connect') {
    return res.status(400).send('Invalid action');
  }

  if (!registration_code || !register_endpoint || !callback_url) {
    return res.status(400).send('Missing required parameters');
  }

  // 2. URL デコード
  const decodedSiteUrl = decodeURIComponent(site_url);
  const decodedSiteName = decodeURIComponent(site_name);
  const decodedMcpEndpoint = decodeURIComponent(mcp_endpoint);
  const decodedRegisterEndpoint = decodeURIComponent(register_endpoint);
  const decodedCallbackUrl = decodeURIComponent(callback_url);

  try {
    // 3. WordPress に登録リクエストを送信（タイムアウト設定推奨）
    const credentials = await registerWithWordPress(
      decodedRegisterEndpoint,
      registration_code
    );

    // 4. 認証情報をデータベースに保存
    await saveWordPressSite({
      siteUrl: decodedSiteUrl,
      siteName: decodedSiteName,
      mcpEndpoint: decodedMcpEndpoint,
      accessToken: credentials.access_token,
      apiKey: credentials.api_key,
      apiSecret: credentials.api_secret,
      connectedAt: new Date()
    });

    // 5. 成功コールバックにリダイレクト
    res.redirect(`${decodedCallbackUrl}?status=success`);

  } catch (error) {
    console.error('WordPress connection failed:', error);

    // 6. エラーコールバックにリダイレクト
    const errorCode = error.code || 'registration_failed';
    const errorMessage = encodeURIComponent(error.message || '連携に失敗しました');
    res.redirect(`${decodedCallbackUrl}?status=error&error=${errorMessage}`);
  }
});
```

### 2. 登録 API 呼び出し

WordPress の `/wp-mcp/v1/register` エンドポイントを呼び出してクレデンシャルを取得します。

**リクエスト**:

```http
POST /wp-json/wp-mcp/v1/register
Content-Type: application/json

{
  "registration_code": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "saas_identifier": "Your SaaS Name"
}
```

**リクエストパラメータ**:

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `registration_code` | string | Yes | WordPress から受け取った一時登録コード（64文字） |
| `saas_identifier` | string | No | SaaS サービスの識別名（WordPress 管理画面に表示される） |

**成功レスポンス（200 OK）**:

```json
{
  "success": true,
  "mcp_endpoint": "https://example.com/wp-json/mcp/mcp-adapter-default-server",
  "access_token": "a1b2c3d4e5f6g7h8i9j0...",
  "api_key": "mcp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "api_secret": "yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
  "site_url": "https://example.com",
  "site_name": "My WordPress Site"
}
```

**レスポンスフィールド**:

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `success` | boolean | 常に `true` |
| `mcp_endpoint` | string | MCP サーバーの URL |
| `access_token` | string | Bearer 認証用アクセストークン（**永久有効**） |
| `api_key` | string | API キー（Basic 認証用） |
| `api_secret` | string | API シークレット（Basic 認証用） |
| `site_url` | string | WordPress サイトの URL |
| `site_name` | string | WordPress サイト名 |

**エラーレスポンス**:

| ステータス | コード | 説明 |
|-----------|--------|------|
| 400 | `missing_code` | registration_code が未指定 |
| 401 | `invalid_code` | 無効な登録コード（一度使用済み含む） |
| 401 | `expired_code` | 登録コードの有効期限切れ（10 分） |

```json
{
  "code": "expired_code",
  "message": "登録コードの有効期限が切れています。",
  "data": {
    "status": 401
  }
}
```

### 登録コードの特性

登録コードには以下の特性があります：

- **ワンタイム**: 一度使用すると即座に無効化されます（成功・失敗に関わらず検証後に削除）
- **有効期限**: 生成から **10 分間** のみ有効
- **ハッシュ保存**: WordPress 側では SHA-256 ハッシュで保存されています
- **長さ**: 64 文字の英数字

⚠️ **重要**: 登録処理でエラーが発生した場合でも、登録コードは無効化されている可能性があります。
ユーザーには WordPress 管理画面から「再度連携する」よう案内してください。**リトライ処理は行わないでください。**

**実装例（Node.js）**:

```javascript
async function registerWithWordPress(registerEndpoint, registrationCode) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000); // 30秒タイムアウト

  try {
    const response = await fetch(registerEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        registration_code: registrationCode,
        saas_identifier: 'My SaaS Service'
      }),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const error = await response.json();
      const err = new Error(error.message || 'Registration failed');
      err.code = error.code;
      throw err;
    }

    return response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      const err = new Error('WordPress への接続がタイムアウトしました');
      err.code = 'timeout';
      throw err;
    }
    throw error;
  }
}
```

### コールバック URL のパラメータ

SaaS から WordPress の `callback_url` にリダイレクトする際のパラメータ：

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| `status` | `success` | 連携成功 |
| `status` | `error` | 連携失敗 |
| `error` | エラーメッセージ | status=error の場合のみ（URL エンコード必須） |

**推奨エラーメッセージ**:

| 状況 | エラーメッセージ |
|------|-----------------|
| action が不正 | `不正なリクエストです` |
| 登録コードが無効 | `登録コードが無効です。再度連携をお試しください。` |
| 登録コードが期限切れ | `登録コードの有効期限が切れています。再度連携をお試しください。` |
| タイムアウト | `接続がタイムアウトしました。再度お試しください。` |
| その他 | `連携に失敗しました。再度お試しください。` |

---

## MCP 通信

### 認証方法

取得したクレデンシャルを使用して MCP サーバーと通信します。

#### 方法 1: Bearer Token（推奨）

```http
Authorization: Bearer {access_token}
```

```javascript
const response = await fetch(mcpEndpoint, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(mcpRequest)
});
```

#### 方法 2: Basic Auth

```http
Authorization: Basic base64({api_key}:{api_secret})
```

```javascript
const credentials = Buffer.from(`${apiKey}:${apiSecret}`).toString('base64');
const response = await fetch(mcpEndpoint, {
  method: 'POST',
  headers: {
    'Authorization': `Basic ${credentials}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(mcpRequest)
});
```

### MCP セッション管理

MCP 通信にはセッション管理が必要です。

#### セッション ID ヘッダーの注意事項

MCP セッション ID は HTTP ヘッダーで管理されます。

| 方向 | ヘッダー名 |
|------|-----------|
| レスポンス（WordPress → SaaS） | `Mcp-Session-Id` または `mcp-session-id` |
| リクエスト（SaaS → WordPress） | `Mcp-Session-Id` |

⚠️ HTTP ヘッダー名は大文字小文字を区別しませんが、ライブラリによっては小文字で返される場合があります。**両方のケースに対応してください**：

```javascript
const sessionId = response.headers.get('Mcp-Session-Id')
               || response.headers.get('mcp-session-id');
```

#### 1. セッション初期化

```javascript
async function initializeMcpSession(mcpEndpoint, accessToken) {
  const response = await fetch(mcpEndpoint, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      jsonrpc: '2.0',
      method: 'initialize',
      params: {
        protocolVersion: '2024-11-05',
        capabilities: {},
        clientInfo: {
          name: 'your-saas-name',
          version: '1.0.0'
        }
      },
      id: 1
    })
  });

  // レスポンスヘッダーからセッション ID を取得（大文字小文字両対応）
  const sessionId = response.headers.get('Mcp-Session-Id')
                 || response.headers.get('mcp-session-id');
  const result = await response.json();

  return {
    sessionId,
    serverInfo: result.result
  };
}
```

#### 2. MCP リクエスト送信

```javascript
async function sendMcpRequest(mcpEndpoint, accessToken, sessionId, method, params) {
  const response = await fetch(mcpEndpoint, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      'Mcp-Session-Id': sessionId
    },
    body: JSON.stringify({
      jsonrpc: '2.0',
      method: method,
      params: params,
      id: Date.now()
    })
  });

  return response.json();
}
```

### MCP クライアント実装例

```javascript
class WordPressMcpClient {
  constructor(credentials) {
    this.mcpEndpoint = credentials.mcp_endpoint;
    this.accessToken = credentials.access_token;
    this.sessionId = null;
    this.requestId = 0;
  }

  async connect() {
    const response = await fetch(this.mcpEndpoint, {
      method: 'POST',
      headers: this._getHeaders(),
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'initialize',
        params: {
          protocolVersion: '2024-11-05',
          capabilities: {},
          clientInfo: {
            name: 'your-saas',
            version: '1.0.0'
          }
        },
        id: ++this.requestId
      })
    });

    // 大文字小文字両対応
    this.sessionId = response.headers.get('Mcp-Session-Id')
                  || response.headers.get('mcp-session-id');
    return response.json();
  }

  async listTools() {
    return this._request('tools/list', {});
  }

  async callTool(name, args) {
    return this._request('tools/call', {
      name: name,
      arguments: args
    });
  }

  async listResources() {
    return this._request('resources/list', {});
  }

  async readResource(uri) {
    return this._request('resources/read', { uri });
  }

  async listPrompts() {
    return this._request('prompts/list', {});
  }

  async getPrompt(name, args) {
    return this._request('prompts/get', {
      name: name,
      arguments: args
    });
  }

  async _request(method, params) {
    if (!this.sessionId) {
      throw new Error('Not connected. Call connect() first.');
    }

    const response = await fetch(this.mcpEndpoint, {
      method: 'POST',
      headers: {
        ...this._getHeaders(),
        'Mcp-Session-Id': this.sessionId
      },
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: method,
        params: params,
        id: ++this.requestId
      })
    });

    return response.json();
  }

  _getHeaders() {
    return {
      'Authorization': `Bearer ${this.accessToken}`,
      'Content-Type': 'application/json'
    };
  }
}

// 使用例
const client = new WordPressMcpClient(credentials);
await client.connect();

// ツール一覧を取得
const tools = await client.listTools();
console.log(tools.result.tools);

// 記事を作成
const result = await client.callTool('wp-mcp-create-draft-post', {
  title: 'AIが生成した記事',
  content: '<!-- wp:paragraph --><p>記事の本文...</p><!-- /wp:paragraph -->'
});
console.log(result.result);
```

### 接続テスト機能

連携完了後、接続が正常か確認する機能の実装を推奨します：

```javascript
async function testConnection(site) {
  const credentials = decrypt(site.encryptedCredentials);

  try {
    const response = await fetch(site.mcpEndpoint, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${credentials.access_token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'initialize',
        params: {
          protocolVersion: '2024-11-05',
          capabilities: {},
          clientInfo: { name: 'your-saas', version: '1.0.0' }
        },
        id: 1
      }),
      signal: AbortSignal.timeout(10000) // 10秒タイムアウト
    });

    const result = await response.json();

    if (result.error) {
      return { success: false, message: result.error.message };
    }

    const serverInfo = result.result?.serverInfo;
    return {
      success: true,
      message: '接続成功',
      serverInfo: {
        name: serverInfo?.name,
        version: serverInfo?.version
      }
    };
  } catch (error) {
    return {
      success: false,
      message: error.message || '接続に失敗しました'
    };
  }
}
```

---

## データベース設計

### 必要なテーブル

```sql
CREATE TABLE wordpress_sites (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),

  -- サイト情報
  site_url VARCHAR(500) UNIQUE NOT NULL,  -- ユニーク制約推奨
  site_name VARCHAR(255),
  mcp_endpoint VARCHAR(500) NOT NULL,

  -- 認証情報（暗号化して保存）
  encrypted_credentials TEXT NOT NULL,

  -- 接続状態
  connection_status VARCHAR(20) DEFAULT 'connected',  -- connected, disconnected, error
  is_active BOOLEAN DEFAULT FALSE,  -- 現在使用中のサイト（複数サイト対応時）
  last_connected_at TIMESTAMP,
  last_used_at TIMESTAMP,  -- 最後にMCP通信した日時
  last_error TEXT,

  -- メタデータ
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_wordpress_sites_user_id ON wordpress_sites(user_id);
CREATE INDEX idx_wordpress_sites_status ON wordpress_sites(connection_status);
CREATE UNIQUE INDEX idx_wordpress_sites_site_url ON wordpress_sites(site_url);
```

### 認証情報の暗号化

認証情報は必ず暗号化して保存してください。**AES-256-GCM（認証付き暗号化）を推奨します。**

#### Node.js (AES-256-GCM 推奨)

```javascript
const crypto = require('crypto');

// 環境変数から 32 バイトのキーを取得（Base64 エンコード）
const ENCRYPTION_KEY = Buffer.from(process.env.ENCRYPTION_KEY, 'base64');
const NONCE_SIZE = 12; // GCM 推奨サイズ

function encrypt(data) {
  const nonce = crypto.randomBytes(NONCE_SIZE);
  const cipher = crypto.createCipheriv('aes-256-gcm', ENCRYPTION_KEY, nonce);

  const plaintext = JSON.stringify(data);
  const encrypted = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
  const tag = cipher.getAuthTag(); // 認証タグ（改ざん検知用）

  // nonce + tag + encrypted を Base64 エンコード
  return Buffer.concat([nonce, tag, encrypted]).toString('base64');
}

function decrypt(encryptedBase64) {
  const data = Buffer.from(encryptedBase64, 'base64');
  const nonce = data.subarray(0, NONCE_SIZE);
  const tag = data.subarray(NONCE_SIZE, NONCE_SIZE + 16);
  const encrypted = data.subarray(NONCE_SIZE + 16);

  const decipher = crypto.createDecipheriv('aes-256-gcm', ENCRYPTION_KEY, nonce);
  decipher.setAuthTag(tag);

  const decrypted = decipher.update(encrypted) + decipher.final('utf8');
  return JSON.parse(decrypted);
}

// 使用例
const credentials = {
  access_token: 'xxx',
  api_key: 'yyy',
  api_secret: 'zzz'
};
const encrypted = encrypt(credentials);
const decrypted = decrypt(encrypted);
```

#### Python (AES-256-GCM)

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
import os
import json

# 環境変数から 32 バイトのキーを取得（Base64 エンコード）
ENCRYPTION_KEY = base64.b64decode(os.environ['ENCRYPTION_KEY'])
NONCE_SIZE = 12

def encrypt_credentials(credentials: dict) -> str:
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(ENCRYPTION_KEY)
    plaintext = json.dumps(credentials).encode()
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return base64.b64encode(nonce + ciphertext).decode()

def decrypt_credentials(encrypted: str) -> dict:
    data = base64.b64decode(encrypted)
    nonce, ciphertext = data[:NONCE_SIZE], data[NONCE_SIZE:]
    aesgcm = AESGCM(ENCRYPTION_KEY)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode())
```

### 再連携時の処理

同じ WordPress サイトから再度連携リクエストが来た場合の推奨処理：

```javascript
// 既存サイトの確認（site_url ベース）
const existingSite = await db.findOne({ where: { site_url: decoded.siteUrl } });

if (existingSite) {
  // 既存レコードを更新
  existingSite.mcp_endpoint = credentials.mcp_endpoint;
  existingSite.encrypted_credentials = encrypt(credentials);
  existingSite.connection_status = 'connected';
  existingSite.last_connected_at = new Date();
  existingSite.last_error = null;
  await existingSite.save();
} else {
  // 新規作成
  await db.create({ ... });
}
```

---

## セキュリティ考慮事項

### 1. HTTPS 必須

- SaaS サービスは必ず HTTPS でホストしてください
- WordPress サイトへのリクエストも HTTPS を使用してください

### 2. 認証情報の保護

- `access_token`、`api_key`、`api_secret` は **暗号化して保存**
- **ログに認証情報を出力しない**
- 環境変数で暗号化キーを管理
- 暗号化キーは 32 バイト（256 ビット）の強力なランダム値を使用

### 3. 登録コードの検証

- 登録コードは **10 分で期限切れ**
- 一度使用された登録コードは **再利用不可**（ワンタイム）
- タイムアウト処理を実装（推奨: 30 秒）

### 4. レート制限

- MCP リクエストにはレート制限を設けることを推奨
- WordPress 側でもレート制限を有効にできます

### 5. エラーメッセージ

- 詳細なエラー情報をユーザーに表示しない
- 内部ログにのみ詳細を記録

---

## エラーハンドリング

### 接続時のエラー

| エラー | 原因 | 対処法 |
|--------|------|--------|
| `missing_code` | registration_code が未指定 | パラメータを確認 |
| `invalid_code` | 登録コードが無効（使用済み含む） | ユーザーに再試行を促す |
| `expired_code` | 登録コードが期限切れ | ユーザーに再試行を促す（10 分以内に完了） |
| ネットワークエラー | WordPress への接続失敗 | ユーザーに通知（リトライ不可） |
| タイムアウト | 応答がない | ユーザーに通知 |

### MCP 通信時のエラー

| エラー | 原因 | 対処法 |
|--------|------|--------|
| 401 Unauthorized | トークン無効 | 再接続が必要（WordPress で連携解除された可能性） |
| 403 Forbidden | 権限不足 | 接続状態を確認 |
| セッションエラー | セッション期限切れ | セッション再初期化（`connect()` を再実行） |
| JSON-RPC エラー | リクエスト形式エラー | リクエストを確認 |

### エラー処理の実装例

```javascript
class McpConnectionError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

async function handleMcpRequest(client, method, params) {
  try {
    const result = await client._request(method, params);

    if (result.error) {
      // JSON-RPC エラー
      throw new McpConnectionError(
        result.error.code,
        result.error.message
      );
    }

    return result.result;

  } catch (error) {
    if (error.message?.includes('401') || error.code === 401) {
      // 認証エラー - 再接続が必要
      await markSiteDisconnected(client.siteId, error.message);
      throw new McpConnectionError('AUTH_FAILED', '認証に失敗しました。WordPress で再連携が必要です。');
    }

    if (error.code === -32600 || error.message?.includes('session')) {
      // セッションエラー - 再初期化
      await client.connect();
      return client._request(method, params);
    }

    throw error;
  }
}
```

---

## 実装例

### Node.js (Express) 完全実装

```javascript
// routes/wordpress.js
const express = require('express');
const router = express.Router();
const { WordPressSite } = require('../models');
const { encrypt, decrypt } = require('../utils/crypto');
const WordPressMcpClient = require('../lib/mcp-client');

// 連携開始エンドポイント
router.get('/connect/wordpress', async (req, res) => {
  const {
    action,
    site_url,
    site_name,
    mcp_endpoint,
    register_endpoint,
    registration_code,
    callback_url
  } = req.query;

  // バリデーション
  if (action !== 'wordpress_mcp_connect') {
    const decodedCallback = decodeURIComponent(callback_url);
    return res.redirect(`${decodedCallback}?status=error&error=${encodeURIComponent('不正なリクエストです')}`);
  }

  const requiredParams = ['site_url', 'mcp_endpoint', 'register_endpoint', 'registration_code', 'callback_url'];
  for (const param of requiredParams) {
    if (!req.query[param]) {
      return res.status(400).send(`Missing parameter: ${param}`);
    }
  }

  // デコード
  const decoded = {
    siteUrl: decodeURIComponent(site_url),
    siteName: decodeURIComponent(site_name || ''),
    mcpEndpoint: decodeURIComponent(mcp_endpoint),
    registerEndpoint: decodeURIComponent(register_endpoint),
    callbackUrl: decodeURIComponent(callback_url)
  };

  try {
    // WordPress に登録リクエスト（タイムアウト付き）
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    const response = await fetch(decoded.registerEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        registration_code: registration_code,
        saas_identifier: 'My SaaS Service'
      }),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Registration failed');
    }

    const credentials = await response.json();

    // 既存サイトの確認（site_url ベース）
    let site = await WordPressSite.findOne({ where: { siteUrl: decoded.siteUrl } });

    const encryptedCreds = encrypt({
      access_token: credentials.access_token,
      api_key: credentials.api_key,
      api_secret: credentials.api_secret
    });

    if (site) {
      // 既存レコードを更新
      site.mcpEndpoint = credentials.mcp_endpoint;
      site.siteName = credentials.site_name || decoded.siteName;
      site.encryptedCredentials = encryptedCreds;
      site.connectionStatus = 'connected';
      site.lastConnectedAt = new Date();
      site.lastError = null;
      await site.save();
    } else {
      // 新規作成
      site = await WordPressSite.create({
        userId: req.user?.id || null,
        siteUrl: decoded.siteUrl,
        siteName: credentials.site_name || decoded.siteName,
        mcpEndpoint: credentials.mcp_endpoint,
        encryptedCredentials: encryptedCreds,
        connectionStatus: 'connected',
        lastConnectedAt: new Date()
      });
    }

    // 成功コールバック
    res.redirect(`${decoded.callbackUrl}?status=success`);

  } catch (error) {
    console.error('WordPress connection error:', error);

    let errorMessage = '連携に失敗しました。再度お試しください。';
    if (error.name === 'AbortError') {
      errorMessage = '接続がタイムアウトしました。再度お試しください。';
    } else if (error.message) {
      errorMessage = error.message;
    }

    res.redirect(`${decoded.callbackUrl}?status=error&error=${encodeURIComponent(errorMessage)}`);
  }
});

// 接続済みサイト一覧
router.get('/sites', async (req, res) => {
  const sites = await WordPressSite.findAll({
    where: { userId: req.user.id },
    attributes: ['id', 'siteUrl', 'siteName', 'connectionStatus', 'lastConnectedAt', 'isActive']
  });
  res.json(sites);
});

// サイトとの通信テスト
router.post('/sites/:id/test', async (req, res) => {
  const site = await WordPressSite.findByPk(req.params.id);
  if (!site) {
    return res.status(404).json({ error: 'Site not found' });
  }

  try {
    const credentials = decrypt(site.encryptedCredentials);
    const client = new WordPressMcpClient({
      mcp_endpoint: site.mcpEndpoint,
      access_token: credentials.access_token
    });

    await client.connect();
    const siteInfo = await client.callTool('wp-mcp-get-site-info', {});

    // 最終使用日時を更新
    site.lastUsedAt = new Date();
    await site.save();

    res.json({
      success: true,
      siteInfo: siteInfo.result
    });

  } catch (error) {
    // エラー状態を記録
    site.connectionStatus = 'error';
    site.lastError = error.message;
    await site.save();

    res.json({
      success: false,
      error: error.message
    });
  }
});

// サイト削除（連携解除）
router.delete('/sites/:id', async (req, res) => {
  await WordPressSite.destroy({
    where: {
      id: req.params.id,
      userId: req.user.id
    }
  });
  res.json({ deleted: true });
});

module.exports = router;
```

### Python (FastAPI) 完全実装

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import httpx
import base64
import os
import json
from datetime import datetime
from urllib.parse import urlencode

router = APIRouter()

# AES-256-GCM 暗号化
ENCRYPTION_KEY = base64.b64decode(os.environ['CREDENTIAL_ENCRYPTION_KEY'])
NONCE_SIZE = 12

def encrypt_credentials(credentials: dict) -> str:
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(ENCRYPTION_KEY)
    plaintext = json.dumps(credentials).encode()
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return base64.b64encode(nonce + ciphertext).decode()

def decrypt_credentials(encrypted: str) -> dict:
    data = base64.b64decode(encrypted)
    nonce, ciphertext = data[:NONCE_SIZE], data[NONCE_SIZE:]
    aesgcm = AESGCM(ENCRYPTION_KEY)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode())

@router.get("/connect/wordpress")
async def connect_wordpress(
    action: str = Query(...),
    site_url: str = Query(...),
    site_name: str = Query(""),
    mcp_endpoint: str = Query(...),
    register_endpoint: str = Query(...),
    registration_code: str = Query(...),
    callback_url: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """WordPress 連携開始エンドポイント"""

    # URL デコードは FastAPI が自動的に行う

    if action != "wordpress_mcp_connect":
        return RedirectResponse(
            f"{callback_url}?status=error&error={urlencode({'': '不正なリクエストです'})[1:]}"
        )

    try:
        # WordPress に登録リクエスト（30秒タイムアウト）
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                register_endpoint,
                json={
                    "registration_code": registration_code,
                    "saas_identifier": "your-saas-name"
                }
            )

        if response.status_code != 200:
            error_data = response.json()
            error_msg = error_data.get("message", "連携に失敗しました")
            return RedirectResponse(
                f"{callback_url}?status=error&error={urlencode({'': error_msg})[1:]}"
            )

        credentials = response.json()

        # 暗号化
        encrypted = encrypt_credentials({
            "access_token": credentials["access_token"],
            "api_key": credentials["api_key"],
            "api_secret": credentials["api_secret"]
        })

        # 既存サイトの確認
        existing_site = await db.execute(
            select(WordPressSite).where(WordPressSite.site_url == site_url)
        )
        site = existing_site.scalar_one_or_none()

        if site:
            # 更新
            site.mcp_endpoint = credentials["mcp_endpoint"]
            site.site_name = credentials.get("site_name") or site_name
            site.encrypted_credentials = encrypted
            site.connection_status = "connected"
            site.last_connected_at = datetime.utcnow()
            site.last_error = None
        else:
            # 新規作成
            site = WordPressSite(
                site_url=site_url,
                site_name=credentials.get("site_name") or site_name,
                mcp_endpoint=credentials["mcp_endpoint"],
                encrypted_credentials=encrypted,
                connection_status="connected",
                last_connected_at=datetime.utcnow()
            )
            db.add(site)

        await db.commit()

        return RedirectResponse(f"{callback_url}?status=success", status_code=302)

    except httpx.TimeoutException:
        return RedirectResponse(
            f"{callback_url}?status=error&error={urlencode({'': '接続がタイムアウトしました'})[1:]}"
        )
    except Exception as e:
        return RedirectResponse(
            f"{callback_url}?status=error&error={urlencode({'': '連携に失敗しました'})[1:]}"
        )

@router.get("/sites")
async def list_sites(db: AsyncSession = Depends(get_db)):
    """接続済みサイト一覧"""
    result = await db.execute(select(WordPressSite))
    sites = result.scalars().all()
    return [
        {
            "id": site.id,
            "site_url": site.site_url,
            "site_name": site.site_name,
            "connection_status": site.connection_status,
            "is_active": site.is_active,
            "last_connected_at": site.last_connected_at
        }
        for site in sites
    ]

@router.post("/sites/{site_id}/test")
async def test_connection(site_id: int, db: AsyncSession = Depends(get_db)):
    """接続テスト"""
    result = await db.execute(
        select(WordPressSite).where(WordPressSite.id == site_id)
    )
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(404, "Site not found")

    credentials = decrypt_credentials(site.encrypted_credentials)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                site.mcp_endpoint,
                headers={
                    "Authorization": f"Bearer {credentials['access_token']}",
                    "Content-Type": "application/json"
                },
                json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "your-saas", "version": "1.0.0"}
                    },
                    "id": 1
                }
            )

        result = response.json()

        if "error" in result:
            site.connection_status = "error"
            site.last_error = result["error"].get("message")
            await db.commit()
            return {"success": False, "error": result["error"]["message"]}

        site.last_used_at = datetime.utcnow()
        await db.commit()

        return {
            "success": True,
            "serverInfo": result.get("result", {}).get("serverInfo")
        }

    except Exception as e:
        site.connection_status = "error"
        site.last_error = str(e)
        await db.commit()
        return {"success": False, "error": str(e)}

@router.post("/sites/{site_id}/call-tool")
async def call_tool(
    site_id: int,
    tool_name: str,
    arguments: dict,
    db: AsyncSession = Depends(get_db)
):
    """MCP ツール呼び出し"""
    result = await db.execute(
        select(WordPressSite).where(WordPressSite.id == site_id)
    )
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(404, "Site not found")

    credentials = decrypt_credentials(site.encrypted_credentials)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Initialize
        init_response = await client.post(
            site.mcp_endpoint,
            headers={
                "Authorization": f"Bearer {credentials['access_token']}",
                "Content-Type": "application/json"
            },
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "your-saas", "version": "1.0.0"}
                },
                "id": 1
            }
        )

        # 大文字小文字両対応
        session_id = (
            init_response.headers.get("Mcp-Session-Id") or
            init_response.headers.get("mcp-session-id")
        )

        # Call tool
        tool_response = await client.post(
            site.mcp_endpoint,
            headers={
                "Authorization": f"Bearer {credentials['access_token']}",
                "Content-Type": "application/json",
                "Mcp-Session-Id": session_id
            },
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                },
                "id": 2
            }
        )

        site.last_used_at = datetime.utcnow()
        await db.commit()

        return tool_response.json()
```

---

## トラブルシューティング

### 404 エラー: `/wp-mcp/v1/register` が見つからない

**原因**: REST API ルートが登録されていない

**解決方法**:
1. WordPress 管理画面 → 設定 → パーマリンク → 「変更を保存」をクリック（変更せずに保存するだけでOK）
2. プラグインを一度無効化して再度有効化
3. `/wp-json/wp-mcp/v1/` にアクセスして利用可能なエンドポイントを確認

### 認証エラー（401）が発生する

**原因**: トークンが無効化されている

**解決方法**:
- WordPress 側で「連携を解除」された可能性があります
- ユーザーに WordPress 管理画面から再度連携するよう案内してください

### セッションエラーが頻発する

**原因**: MCP セッションの有効期限切れ

**解決方法**:
- エラー発生時に `connect()` を再実行してセッションを再初期化
- 長時間のリクエスト間隔がある場合は、事前にセッションを初期化し直す

### コールバックでエラーが表示される

**確認項目**:
1. SaaS 側のログで詳細なエラー内容を確認
2. WordPress への登録リクエストが正しく送信されているか確認
3. タイムアウトが発生していないか確認（推奨: 30 秒）

---

## チェックリスト

SaaS 連携実装が完了したら、以下を確認してください：

### 必須

- [ ] `/connect/wordpress` エンドポイントを実装した
- [ ] `/wp-mcp/v1/register` API を正しく呼び出している
- [ ] クレデンシャルを **AES-256-GCM で暗号化** して保存している
- [ ] コールバック URL に正しくリダイレクトしている（成功時・エラー時両方）
- [ ] MCP セッション初期化を実装した（`Mcp-Session-Id` ヘッダー対応）
- [ ] タイムアウト処理を実装した（推奨: 30 秒）
- [ ] エラーハンドリングを実装した

### 推奨

- [ ] HTTPS を使用している
- [ ] ログに認証情報を出力していない
- [ ] 接続テスト機能を実装した
- [ ] ユーザーへのエラーメッセージを適切に表示している
- [ ] 接続解除機能を実装した
- [ ] 既存サイトの再連携処理を実装した（site_url ベースで更新）
- [ ] セッション ID ヘッダーの大文字小文字両対応

---

## サポート

実装に関する質問やバグ報告は以下まで：

- GitHub Issues: https://github.com/your-org/wordpress-mcp-ability-plugin/issues
