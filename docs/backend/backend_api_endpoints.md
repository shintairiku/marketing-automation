# バックエンドAPIエンドポイント仕様

## 概要

このドキュメントでは、Marketing Automation APIが提供する全てのRESTfulエンドポイントを網羅的に解説します。APIは5つの主要ドメインに分かれており、それぞれが独自の責務を持ちながら統合されたマーケティング自動化プラットフォームを構成しています。

## API基本情報

### ベースURL構成
- **本番環境**: `https://your-domain.com/api`
- **開発環境**: `http://localhost:8000`
- **認証方式**: Bearer Token (Clerk JWT)
- **レスポンス形式**: JSON
- **文字エンコーディング**: UTF-8

### 共通HTTPステータスコード
- `200 OK`: 成功
- `201 Created`: 作成成功
- `204 No Content`: 削除成功
- `400 Bad Request`: リクエストエラー
- `401 Unauthorized`: 認証エラー
- `403 Forbidden`: 権限エラー
- `404 Not Found`: リソース未発見
- `500 Internal Server Error`: サーバーエラー

### 共通レスポンス形式
```json
{
  "data": {...},           // 成功時のデータ
  "error": "...",          // エラー時のメッセージ
  "message": "...",        // 追加メッセージ
  "status": 200            // HTTPステータスコード
}
```

## 1. 基本エンドポイント

### システム状態確認

#### `GET /`
**概要**: APIルートエンドポイント。API稼働状況の確認。

**パラメータ**: なし

**レスポンス例**:
```json
{
  "message": "Welcome to the SEO Article Generation API (WebSocket)!"
}
```

#### `GET /health`
**概要**: ヘルスチェックエンドポイント。APIの正常性確認。

**パラメータ**: なし

**レスポンス例**:
```json
{
  "status": "healthy",
  "message": "API is running",
  "version": "2.0.0"
}
```

#### `OPTIONS /{path:path}`
**概要**: CORS プリフライトリクエストの処理。

**パラメータ**:
- `path` (string): 任意のパス

**レスポンス例**:
```json
{
  "message": "OK"
}
```

---

## 2. SEO記事生成ドメイン (`/articles`)

### 記事管理基本操作

#### `GET /articles/`
**概要**: ユーザーの記事一覧を取得。

**認証**: 必須 (Bearer Token)

**クエリパラメータ**:
- `status_filter` (string, optional): ステータスでフィルタリング
- `limit` (integer, default: 20): 取得件数上限
- `offset` (integer, default: 0): スキップ件数

**レスポンス例**:
```json
[
  {
    "id": "uuid",
    "title": "記事タイトル",
    "status": "completed",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T01:00:00Z"
  }
]
```

#### `GET /articles/all-processes`
**概要**: 完了記事と進行中プロセスの統合リストを取得。

**認証**: 必須 (Bearer Token)

**クエリパラメータ**:
- `status_filter` (string, optional): ステータスフィルタ
- `limit` (integer, default: 20): 取得件数上限
- `offset` (integer, default: 0): スキップ件数

**レスポンス例**:
```json
[
  {
    "id": "uuid",
    "type": "completed_article",
    "title": "完成記事",
    "status": "completed",
    "progress_percentage": 100
  },
  {
    "id": "uuid",
    "type": "in_progress",
    "current_step": "writing_sections",
    "status": "in_progress",
    "progress_percentage": 75
  }
]
```

#### `GET /articles/recoverable-processes`
**概要**: 復帰可能な中断プロセスの一覧を取得。

**認証**: 必須 (Bearer Token)

**クエリパラメータ**:
- `limit` (integer, default: 10): 取得件数上限

**レスポンス例**:
```json
[
  {
    "id": "uuid",
    "current_step": "outline_generating",
    "error_message": "Timeout occurred",
    "updated_at": "2025-01-01T00:00:00Z",
    "can_recover": true
  }
]
```

### 記事生成プロセス管理

#### `POST /articles/generation/create`
**概要**: 新しい記事生成プロセスを開始。

**認証**: 必須 (Bearer Token)

**リクエストボディ**:
```json
{
  "seo_keywords": ["キーワード1", "キーワード2"],
  "topic": "記事トピック",
  "target_audience": "ターゲットオーディエンス",
  "image_mode_enabled": true,
  "style_preferences": {...}
}
```

**レスポンス例**:
```json
{
  "process_id": "uuid",
  "status": "started",
  "message": "記事生成プロセスが開始されました"
}
```

#### `GET /articles/generation/{process_id}`
**概要**: 記事生成プロセスの現在状態を取得。

**認証**: 必須 (Bearer Token)

**パスパラメータ**:
- `process_id` (string): プロセスID

**レスポンス例**:
```json
{
  "id": "uuid",
  "status": "in_progress",
  "current_step_name": "writing_sections",
  "progress_percentage": 75,
  "is_waiting_for_input": false,
  "article_context": {...},
  "step_history": [...]
}
```

#### `POST /articles/generation/{process_id}/user-input`
**概要**: プロセスへのユーザー入力を送信。

**認証**: 必須 (Bearer Token)

**パスパラメータ**:
- `process_id` (string): プロセスID

**リクエストボディ**:
```json
{
  "response_type": "persona_selection",
  "payload": {
    "selected_persona": "professional_marketer"
  }
}
```

**レスポンス例**:
```json
{
  "success": true,
  "message": "ユーザー入力が正常に処理されました"
}
```

#### `GET /articles/generation/{process_id}/events`
**概要**: プロセスのイベント履歴を取得。

**認証**: 必須 (Bearer Token)

**パスパラメータ**:
- `process_id` (string): プロセスID

**クエリパラメータ**:
- `since_sequence` (integer, optional): 指定シーケンス以降のイベント
- `limit` (integer, default: 50): 取得件数上限

**レスポンス例**:
```json
[
  {
    "id": "uuid",
    "process_id": "uuid",
    "event_type": "step_completed",
    "event_data": {...},
    "event_sequence": 5,
    "created_at": "2025-01-01T00:00:00Z"
  }
]
```

### AI編集機能

#### `POST /articles/{article_id}/ai-edit`
**概要**: AIによる記事ブロックの編集。

**認証**: 必須 (Bearer Token)

**パスパラメータ**:
- `article_id` (string): 記事ID

**リクエストボディ**:
```json
{
  "content": "<p>編集対象のHTMLブロック</p>",
  "instruction": "よりカジュアルな文体に書き換えてください"
}
```

**レスポンス例**:
```json
{
  "success": true,
  "edited_content": "<p>編集されたHTMLブロック</p>",
  "changes_made": ["文体をカジュアルに変更", "表現を簡潔に調整"]
}
```

---

## 3. 会社情報管理ドメイン (`/companies`)

### 会社情報CRUD操作

#### `POST /companies/`
**概要**: 新しい会社情報を作成。

**認証**: 必須 (Bearer Token)

**リクエストボディ**:
```json
{
  "company_name": "株式会社サンプル",
  "business_description": "サンプル事業",
  "target_persona": "30代のビジネスパーソン",
  "company_tone": "フォーマル",
  "contact_info": {...}
}
```

**レスポンス例**:
```json
{
  "id": "uuid",
  "company_name": "株式会社サンプル",
  "business_description": "サンプル事業",
  "created_at": "2025-01-01T00:00:00Z",
  "is_default": false
}
```

#### `GET /companies/`
**概要**: ユーザーの会社情報一覧を取得。

**認証**: 必須 (Bearer Token)

**パラメータ**: なし

**レスポンス例**:
```json
{
  "companies": [
    {
      "id": "uuid",
      "company_name": "株式会社サンプル",
      "business_description": "サンプル事業",
      "is_default": true
    }
  ],
  "total": 1
}
```

#### `GET /companies/default`
**概要**: デフォルト会社情報を取得。

**認証**: 必須 (Bearer Token)

**パラメータ**: なし

**レスポンス例**:
```json
{
  "id": "uuid",
  "company_name": "株式会社サンプル",
  "business_description": "サンプル事業",
  "target_persona": "30代のビジネスパーソン",
  "is_default": true
}
```

#### `GET /companies/{company_id}`
**概要**: 特定の会社情報を取得。

**認証**: 必須 (Bearer Token)

**パスパラメータ**:
- `company_id` (string): 会社ID

**レスポンス例**:
```json
{
  "id": "uuid",
  "company_name": "株式会社サンプル",
  "business_description": "サンプル事業",
  "target_persona": "30代のビジネスパーソン",
  "company_tone": "フォーマル"
}
```

#### `PUT /companies/{company_id}`
**概要**: 会社情報を更新。

**認証**: 必須 (Bearer Token)

**パスパラメータ**:
- `company_id` (string): 会社ID

**リクエストボディ**:
```json
{
  "company_name": "株式会社サンプル更新",
  "business_description": "更新されたサンプル事業"
}
```

#### `DELETE /companies/{company_id}`
**概要**: 会社情報を削除。

**認証**: 必須 (Bearer Token)

**パスパラメータ**:
- `company_id` (string): 会社ID

**レスポンス**: `204 No Content`

#### `POST /companies/set-default`
**概要**: デフォルト会社を設定。

**認証**: 必須 (Bearer Token)

**リクエストボディ**:
```json
{
  "company_id": "uuid"
}
```

---

## 4. 組織管理ドメイン (`/organizations`)

### 組織管理基本操作

#### `POST /organizations/`
**概要**: 新しい組織を作成。

**認証**: 必須 (Bearer Token)

**リクエストボディ**:
```json
{
  "name": "サンプル組織",
  "description": "組織の説明",
  "settings": {...}
}
```

**レスポンス例**:
```json
{
  "id": "uuid",
  "name": "サンプル組織",
  "description": "組織の説明",
  "created_at": "2025-01-01T00:00:00Z",
  "owner_id": "user_uuid"
}
```

#### `GET /organizations/`
**概要**: ユーザーが所属する組織一覧を取得。

**認証**: 必須 (Bearer Token)

**パラメータ**: なし

**レスポンス例**:
```json
[
  {
    "id": "uuid",
    "name": "サンプル組織",
    "role": "owner",
    "member_count": 5
  }
]
```

#### `GET /organizations/{organization_id}`
**概要**: 特定の組織情報を取得。

**認証**: 必須 (Bearer Token)

**パスパラメータ**:
- `organization_id` (string): 組織ID

#### `PUT /organizations/{organization_id}`
**概要**: 組織情報を更新（オーナー・管理者のみ）。

**認証**: 必須 (Bearer Token)

#### `DELETE /organizations/{organization_id}`
**概要**: 組織を削除（オーナーのみ）。

**認証**: 必須 (Bearer Token)

### メンバー管理

#### `GET /organizations/{organization_id}/members`
**概要**: 組織メンバー一覧を取得。

**認証**: 必須 (Bearer Token)

**レスポンス例**:
```json
[
  {
    "user_id": "user_uuid",
    "email": "user@example.com",
    "role": "member",
    "joined_at": "2025-01-01T00:00:00Z"
  }
]
```

#### `PUT /organizations/{organization_id}/members/{member_user_id}/role`
**概要**: メンバーの役割を更新。

**認証**: 必須 (Bearer Token)

**リクエストボディ**:
```json
{
  "new_role": "admin"
}
```

#### `DELETE /organizations/{organization_id}/members/{member_user_id}`
**概要**: メンバーを組織から削除。

**認証**: 必須 (Bearer Token)

### 招待システム

#### `POST /organizations/{organization_id}/invitations`
**概要**: 組織への招待を作成。

**認証**: 必須 (Bearer Token)

**リクエストボディ**:
```json
{
  "email": "invite@example.com",
  "role": "member",
  "message": "招待メッセージ"
}
```

#### `GET /organizations/invitations`
**概要**: 現在のユーザーへの招待一覧を取得。

**認証**: 必須 (Bearer Token)

#### `POST /organizations/invitations/respond`
**概要**: 招待に対する応答（承諾・拒否）。

**認証**: 必須 (Bearer Token)

**リクエストボディ**:
```json
{
  "token": "invitation_token",
  "accepted": true
}
```

---

## 5. スタイルテンプレート管理ドメイン (`/style-templates`)

### テンプレート管理操作

#### `GET /style-templates/`
**概要**: アクセス可能なスタイルテンプレート一覧を取得。

**認証**: 必須 (Bearer Token)

**パラメータ**: なし

**レスポンス例**:
```json
[
  {
    "id": "uuid",
    "name": "フォーマルビジネス",
    "description": "ビジネス文書向けのフォーマルなスタイル",
    "template_type": "custom",
    "is_default": true,
    "settings": {...}
  }
]
```

#### `GET /style-templates/{template_id}`
**概要**: 特定のスタイルテンプレートを取得。

**認証**: 必須 (Bearer Token)

**パスパラメータ**:
- `template_id` (string): テンプレートID

#### `POST /style-templates/`
**概要**: 新しいスタイルテンプレートを作成。

**認証**: 必須 (Bearer Token)

**リクエストボディ**:
```json
{
  "name": "カジュアルブログ",
  "description": "カジュアルなブログ記事用スタイル",
  "template_type": "custom",
  "settings": {
    "tone": "casual",
    "sentence_structure": "simple",
    "vocabulary_level": "conversational"
  },
  "is_default": false,
  "organization_id": null
}
```

#### `PUT /style-templates/{template_id}`
**概要**: スタイルテンプレートを更新。

**認証**: 必須 (Bearer Token)

#### `DELETE /style-templates/{template_id}`
**概要**: スタイルテンプレートを削除（ソフトデリート）。

**認証**: 必須 (Bearer Token)

#### `POST /style-templates/{template_id}/set-default`
**概要**: テンプレートをデフォルトに設定。

**認証**: 必須 (Bearer Token)

---

## 6. 画像生成ドメイン (`/images`)

### 画像生成機能

#### `GET /images/test-config`
**概要**: Google Cloud設定のテスト。

**認証**: 必須 (Bearer Token)

**レスポンス例**:
```json
{
  "status": "ok",
  "config": {
    "service_initialized": true,
    "project_id": "project-id",
    "location": "us-central1",
    "has_credentials": true,
    "client_type": "genai"
  }
}
```

#### `POST /images/generate`
**概要**: Vertex AI Imagen-4を使用して画像を生成。

**認証**: 必須 (Bearer Token)

**リクエストボディ**:
```json
{
  "placeholder_id": "img_001",
  "description_jp": "美しい風景画像",
  "prompt_en": "beautiful landscape with mountains and lake at sunset",
  "alt_text": "夕日に照らされた山と湖の風景",
  "article_id": "article_uuid"
}
```

**レスポンス例**:
```json
{
  "image_url": "https://storage.googleapis.com/bucket/image.jpg",
  "placeholder_id": "img_001"
}
```

#### `POST /images/generate-from-placeholder`
**概要**: プレースホルダー情報から画像を生成。

**認証**: 必須 (Bearer Token)

**リクエストボディ**:
```json
{
  "placeholder_id": "img_001",
  "description_jp": "商品紹介画像",
  "prompt_en": "professional product photography",
  "additional_context": "企業ブログ用",
  "aspect_ratio": "16:9",
  "quality": 90
}
```

### 画像アップロードと管理

#### `POST /images/upload`
**概要**: 画像をアップロードしてGCSに保存。

**認証**: 必須 (Bearer Token)

**リクエスト形式**: `multipart/form-data`

**フォームフィールド**:
- `file` (file): 画像ファイル
- `article_id` (string): 記事ID
- `placeholder_id` (string): プレースホルダーID
- `alt_text` (string): ALTテキスト

**レスポンス例**:
```json
{
  "success": true,
  "message": "画像が正常にアップロードされ、記事が更新されました。",
  "image_id": "uuid",
  "image_url": "https://storage.googleapis.com/bucket/uploaded_image.jpg",
  "gcs_path": "images/uploaded_image.jpg",
  "updated_content": "更新されたHTML内容"
}
```

#### `POST /images/replace-placeholder`
**概要**: 記事内のプレースホルダーを画像で置き換え。

**認証**: 必須 (Bearer Token)

**リクエストボディ**:
```json
{
  "article_id": "article_uuid",
  "placeholder_id": "img_001",
  "image_url": "https://storage.googleapis.com/bucket/image.jpg",
  "alt_text": "画像の説明"
}
```

#### `GET /images/serve/{image_filename}`
**概要**: 保存された画像を配信。

**パスパラメータ**:
- `image_filename` (string): 画像ファイル名

**レスポンス**: 画像ファイル（JPEG）

---

## 認証・セキュリティ

### 認証ヘッダー
全ての保護されたエンドポイントで必須：
```
Authorization: Bearer <clerk_jwt_token>
```

### ユーザーID抽出
JWTトークンから`sub`クレームを抽出してユーザーIDとして使用。

### アクセス制御
- **個人リソース**: 作成者のみアクセス可能
- **組織リソース**: 組織メンバーのみアクセス可能
- **管理者操作**: オーナー・管理者のみ実行可能

## エラーハンドリング

### 共通エラーレスポンス
```json
{
  "error": "エラーメッセージ",
  "detail": "詳細な説明",
  "status": 400
}
```

### バリデーションエラー
```json
{
  "error": "Validation Error",
  "details": [
    {
      "field": "email",
      "message": "Invalid email format"
    }
  ]
}
```

## レート制限・制約

### 画像生成
- **制限**: 1分間に10リクエスト
- **ファイルサイズ**: 最大10MB
- **対応形式**: JPEG, PNG, WebP

### API呼び出し
- **一般**: 1分間に60リクエスト
- **記事生成**: 1日に50プロセス

## API使用例

### 記事生成の基本フロー
```bash
# 1. 記事生成開始
curl -X POST "http://localhost:8000/articles/generation/create" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "seo_keywords": ["マーケティング", "自動化"],
    "topic": "マーケティング自動化の基礎",
    "target_audience": "マーケティング担当者"
  }'

# 2. プロセス状態確認
curl -X GET "http://localhost:8000/articles/generation/{process_id}" \
  -H "Authorization: Bearer $TOKEN"

# 3. ユーザー入力送信（必要時）
curl -X POST "http://localhost:8000/articles/generation/{process_id}/user-input" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "response_type": "persona_selection",
    "payload": {"selected_persona": "professional_marketer"}
  }'
```

## まとめ

Marketing Automation APIは、RESTful設計原則に基づき、包括的なマーケティング自動化機能を提供します。各エンドポイントは適切に分離されており、明確な責務を持ちながら、統合されたユーザー体験を実現しています。Supabase Realtimeとの統合により、リアルタイムな状態更新とユーザーインタラクションを支援し、現代的なWebアプリケーションの要求を満たすAPIとして設計されています。