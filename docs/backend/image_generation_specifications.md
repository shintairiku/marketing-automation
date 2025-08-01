# 画像生成モードと画像生成機能の仕様

## 概要

本文書では、画像生成モードの仕様について詳細に解説します。有効化した場合にAIが記事内に`<!-- IMAGE_PLACEHOLDER: id|description_jp|prompt_en -->`形式のコメントを挿入する仕組み、`image_placeholders`テーブルでの管理方法、Vertex AI Imagen 4.0を用いた画像生成フロー、およびGCSへの保存と記事への反映プロセスを詳述します。

## システム構成

```
┌─────────────────────────┐
│    画像生成モード       │
├─────────────────────────┤
│  • ArticleContextで管理 │
│  • image_modeフラグ     │
│  • image_settings設定   │
└─────────────────────────┘
           │
           ▼
┌─────────────────────────┐
│    記事生成中           │
├─────────────────────────┤
│  • エージェントが       │
│    プレースホルダー挿入 │
│  • 記事内容に自然配置   │
└─────────────────────────┘
           │
           ▼
┌─────────────────────────┐
│  プレースホルダー抽出   │
├─────────────────────────┤
│  • 正規表現による解析   │
│  • image_placeholders   │
│    テーブルに保存       │
└─────────────────────────┘
           │
           ▼
┌─────────────────────────┐
│    画像生成実行         │
├─────────────────────────┤
│  • Vertex AI Imagen 4.0 │
│  • GCSへの自動アップロード│
│  • ローカル保存併用     │
└─────────────────────────┘
           │
           ▼
┌─────────────────────────┐
│   プレースホルダー      │
│   置き換え              │
├─────────────────────────┤
│  • HTMLの<img>タグに変更│
│  • 記事内容更新         │
│  • 状態管理テーブル更新 │
└─────────────────────────┘
```

## データベース構造

### 1. generated_articles_state テーブル拡張

画像生成モードの管理のための追加カラム：

```sql
-- 画像生成モードフラグ
ALTER TABLE generated_articles_state 
ADD COLUMN IF NOT EXISTS image_mode BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS image_settings JSONB DEFAULT '{}'::jsonb;
```

**フィールド詳細:**

| カラム名 | 型 | 説明 |
|----------|----|----|
| `image_mode` | BOOLEAN | 画像生成モードが有効かどうか |
| `image_settings` | JSONB | 画像生成設定（アスペクト比、品質等） |

### 2. images テーブル

生成・アップロードされた画像を管理：

```sql
CREATE TABLE IF NOT EXISTS images (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT NOT NULL,
  organization_id UUID REFERENCES organizations(id),
  article_id UUID REFERENCES articles(id),
  generation_process_id UUID REFERENCES generated_articles_state(id),
  original_filename TEXT,
  file_path TEXT NOT NULL,
  image_type TEXT CHECK (image_type IN ('uploaded', 'generated')) NOT NULL,
  alt_text TEXT,
  caption TEXT,
  generation_prompt TEXT,
  generation_params JSONB,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, now()) NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, now()) NOT NULL
);
```

**主要フィールド:**

| フィールド | 説明 | 画像生成での役割 |
|-----------|------|----------------|
| `file_path` | 画像ファイルのパス | ローカル保存パスまたはGCS URL |
| `image_type` | 画像タイプ | `generated`（AI生成）または`uploaded`（アップロード） |
| `generation_prompt` | 生成プロンプト | Vertex AIに送信された英語プロンプト |
| `generation_params` | 生成パラメータ | アスペクト比、品質、安全フィルタ等の設定 |
| `metadata` | メタデータ | GCS情報、ファイルサイズ、画像寸法等 |

### 3. image_placeholders テーブル

記事内のプレースホルダーを管理：

```sql
CREATE TABLE IF NOT EXISTS image_placeholders (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  article_id UUID REFERENCES articles(id),
  generation_process_id UUID REFERENCES generated_articles_state(id),
  placeholder_id TEXT NOT NULL,
  description_jp TEXT NOT NULL,
  prompt_en TEXT NOT NULL,
  position_index INTEGER NOT NULL,
  replaced_with_image_id UUID REFERENCES images(id),
  status TEXT CHECK (status IN ('pending', 'replaced', 'generating')) DEFAULT 'pending',
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, now()) NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, now()) NOT NULL,
  
  UNIQUE(article_id, placeholder_id)
);
```

**ステータス管理:**

| ステータス | 説明 |
|-----------|------|
| `pending` | プレースホルダーが挿入されただけの状態 |
| `generating` | 画像生成処理中 |
| `replaced` | 画像で置き換え済み |

## プレースホルダーシステム

### 1. プレースホルダー形式

記事内に挿入されるプレースホルダーの形式：

```html
<!-- IMAGE_PLACEHOLDER: placeholder_id|日本語説明|英語プロンプト -->
```

**具体例:**

```html
<!-- IMAGE_PLACEHOLDER: living_room_01|札幌の住宅内装の写真。カラマツ無垢材の床や家具が暖かさを演出し、珪藻土の壁が柔らかな質感を醸し出している。薪ストーブが置かれ、冬も快適に過ごせる工夫が見られるリビングの様子。|A photo of a residential interior in Sapporo. The solid larch wood flooring and furniture create a warm atmosphere, while the diatomaceous earth walls add a soft texture. A wood-burning stove is placed in the living room, providing comfort and warmth during the winter months. -->
```

### 2. プレースホルダー抽出処理

ファイル位置: `/frontend/supabase/migrations/20250620000000_add_image_placeholders.sql`

```sql
CREATE OR REPLACE FUNCTION extract_image_placeholders(
  article_content TEXT,
  process_id UUID DEFAULT NULL,
  article_id_param UUID DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
  placeholder_pattern TEXT := '<!-- IMAGE_PLACEHOLDER: ([^|]+)\|([^|]+)\|([^>]+) -->';
  match RECORD;
  counter INTEGER := 0;
BEGIN
  -- Extract all image placeholders using regex
  FOR match IN
    SELECT 
      (regexp_matches(article_content, placeholder_pattern, 'g'))[1] as placeholder_id,
      (regexp_matches(article_content, placeholder_pattern, 'g'))[2] as description_jp,
      (regexp_matches(article_content, placeholder_pattern, 'g'))[3] as prompt_en,
      (regexp_match_indices(article_content, placeholder_pattern, 'g'))[1] as position
  LOOP
    counter := counter + 1;
    
    -- Insert placeholder into image_placeholders table
    INSERT INTO image_placeholders (
      article_id, 
      generation_process_id, 
      placeholder_id, 
      description_jp, 
      prompt_en, 
      position_index
    ) VALUES (
      article_id_param,
      process_id,
      match.placeholder_id,
      match.description_jp,
      match.prompt_en,
      counter
    )
    ON CONFLICT (article_id, placeholder_id) 
    DO UPDATE SET
      description_jp = EXCLUDED.description_jp,
      prompt_en = EXCLUDED.prompt_en,
      position_index = EXCLUDED.position_index,
      updated_at = TIMEZONE('utc'::text, now());
  END LOOP;
END;
$$ LANGUAGE plpgsql;
```

### 3. エージェントによるプレースホルダー挿入

ファイル位置: `/backend/app/domains/seo_article/agents/definitions.py`

エージェントには以下の指示が含まれます：

```python
--- **【画像プレースホルダーについて】** ---
このセクションでは、内容に応じて画像プレースホルダーを適切に配置してください。
画像プレースホルダーは以下の形式で記述してください:
```html
<!-- IMAGE_PLACEHOLDER: placeholder_id|日本語での画像説明|英語での画像生成プロンプト -->
```

**配置ガイドライン:**
- セクションの内容を視覚的に補強する画像を配置
- プレースホルダーIDは一意性を保つ（例: section1_img01）
- 日本語説明は具体的で詳細に記述
- 英語プロンプトは画像生成に最適化された表現
- 記事全体で最低1つのプレースホルダーを配置
```

## 画像生成サービス

### 1. ImageGenerationService の構成

ファイル位置: `/backend/app/domains/image_generation/service.py`

```python
class ImageGenerationService:
    """Vertex AI Imagen 4.0を使用した画像生成サービス"""
    
    def __init__(self, model_name: Optional[str] = None):
        # 環境変数からモデル設定を取得
        self.model_name = model_name or settings.imagen_model_name
        self.aspect_ratio = settings.imagen_aspect_ratio
        self.output_format = settings.imagen_output_format
        self.quality = settings.imagen_quality
        self.safety_filter = settings.imagen_safety_filter
        self.person_generation = settings.imagen_person_generation
        self.add_japan_prefix = settings.imagen_add_japan_prefix
```

### 2. 主要設定パラメータ

ファイル位置: `/backend/app/core/config.py`

```python
# Vertex AI Imagen 4.0 設定
imagen_model_name: str = "imagen-4.0-generate-preview-06-06"
imagen_aspect_ratio: str = "4:3"
imagen_output_format: str = "JPEG"
imagen_quality: int = 85
imagen_safety_filter: str = "block_only_high"
imagen_person_generation: str = "allow_all"
imagen_add_japan_prefix: bool = True

# ストレージ設定
image_storage_path: str = "/tmp/images"
gcs_bucket_name: str = ""
gcs_public_url_base: str = ""
```

**パラメータ詳細:**

| パラメータ | デフォルト値 | 説明 |
|-----------|------------|------|
| `imagen_model_name` | `imagen-4.0-generate-preview-06-06` | 使用するImagen 4.0モデル |
| `imagen_aspect_ratio` | `4:3` | 生成画像のアスペクト比 |
| `imagen_output_format` | `JPEG` | 出力画像フォーマット |
| `imagen_quality` | `85` | JPEG品質（0-100） |
| `imagen_safety_filter` | `block_only_high` | 安全フィルタレベル |
| `imagen_person_generation` | `allow_all` | 人物生成の許可レベル |
| `imagen_add_japan_prefix` | `true` | 日本語コンテキストの自動追加 |

### 3. 画像生成フロー

```python
async def generate_image_detailed(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
    """詳細なレスポンスを返す画像生成メソッド"""
    
    # 1. Japanプレフィックスの処理
    if self.add_japan_prefix:
        japan_prompt = f"In Japan. {request.prompt}"
    else:
        japan_prompt = request.prompt
    
    # 2. Imagen 4.0モデルの初期化
    model = ImageGenerationModel.from_pretrained(self.model_name)
    
    # 3. 生成パラメータの設定
    generation_params = {
        "prompt": japan_prompt,
        "number_of_images": 1,
        "aspect_ratio": request.aspect_ratio or self.aspect_ratio,
        "safety_filter_level": self.safety_filter,
        "person_generation": self.person_generation,
    }
    
    # 4. 画像生成実行
    response = model.generate_images(**generation_params)
    generated_image = response.images[0]
    image_data = generated_image._image_bytes
    
    # 5. 品質調整（JPEGの場合）
    if output_format.upper() == "JPEG" and quality:
        pil_image = Image.open(io.BytesIO(image_data))
        with open(image_path, "wb") as f:
            pil_image.save(f, "JPEG", quality=quality)
    
    # 6. GCSアップロード（利用可能な場合）
    if gcs_service.is_available():
        success, gcs_url, gcs_path, error = gcs_service.upload_image(
            image_data=image_data,
            filename=image_filename,
            content_type=f"image/{output_format.lower()}",
            metadata=gcs_metadata
        )
    
    return ImageGenerationResponse(
        success=True,
        image_path=str(image_path),
        image_url=primary_url,  # GCS URL優先
        image_data=image_data,
        metadata=metadata
    )
```

## GCP統合

### 1. 認証システム

ファイル位置: `/backend/app/infrastructure/gcp_auth.py`

```python
class GCPAuthManager:
    """Google Cloud Platform認証管理"""
    
    def _setup_credentials(self) -> None:
        """環境に応じた認証設定"""
        
        # サービスアカウントJSONファイル（開発環境）
        json_file_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON_FILE')
        
        if json_file_path and os.path.exists(json_file_path):
            self._credentials = service_account.Credentials.from_service_account_file(
                json_file_path
            )
        else:
            # デフォルト認証情報（本番環境）
            self._credentials, self._project_id = default()
    
    def initialize_aiplatform(self, location: str = "us-central1") -> None:
        """Vertex AI Platform初期化"""
        aiplatform.init(
            project=self._project_id,
            location=location,
            credentials=self._credentials
        )
```

### 2. GCSサービス

ファイル位置: `/backend/app/infrastructure/external_apis/gcs_service.py`

```python
class GCSService:
    """Google Cloud Storage サービス"""
    
    def upload_image(
        self, 
        image_data: bytes, 
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """画像をGCSにアップロード"""
        
        # ファイル名の生成（UUIDベース）
        if not filename:
            file_extension = self._guess_extension_from_data(image_data, content_type)
            filename = f"generated_{uuid.uuid4().hex}{file_extension}"
        
        # 日付ベースの階層構造
        from datetime import datetime
        date_str = datetime.now().strftime("%Y/%m/%d")
        gcs_path = f"images/{date_str}/{filename}"
        
        # GCSにアップロード
        blob = self._bucket.blob(gcs_path)
        if metadata:
            blob.metadata = metadata
        
        blob.upload_from_string(image_data, content_type=content_type)
        
        # 公開URLの生成
        if self.public_url_base:
            gcs_url = f"{self.public_url_base}/{gcs_path}"
        else:
            gcs_url = f"https://storage.googleapis.com/{self.bucket_name}/{gcs_path}"
        
        return True, gcs_url, gcs_path, None
```

### 3. ハイブリッドストレージ戦略

生成された画像は以下の戦略で保存されます：

```python
# 1. ローカル保存（必須）
image_path = self.storage_path / image_filename
with open(image_path, "wb") as f:
    f.write(image_data)

# 2. GCSアップロード（利用可能な場合）
if gcs_service.is_available():
    success, gcs_url, gcs_path, error = gcs_service.upload_image(...)
    if success:
        storage_type = "hybrid"  # ローカル + GCS
        primary_url = gcs_url    # GCS URLを優先
    else:
        storage_type = "local"
        primary_url = f"http://localhost:8008/images/{image_filename}"
else:
    storage_type = "local"
    primary_url = f"http://localhost:8008/images/{image_filename}"
```

## APIエンドポイント

### 1. 画像生成エンドポイント

ファイル位置: `/backend/app/domains/image_generation/endpoints.py`

#### 1.1 基本画像生成

```python
@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image(
    request: ImageGenerationRequest,
    current_user_id: str = Depends(get_current_user_id_from_token)
):
    """Google Vertex AI Imagen-4を使用して画像を生成"""
    
    # 画像生成サービスを初期化
    image_service = ImageGenerationService()
    
    # 詳細な画像生成を実行
    gen_request = GenRequest(
        prompt=request.prompt_en,
        aspect_ratio="4:3",
        output_format="JPEG",
        quality=85
    )
    
    result = await image_service.generate_image_detailed(gen_request)
    
    # データベースに画像情報を保存
    image_data = {
        "id": str(uuid.uuid4()),
        "user_id": current_user_id,
        "article_id": request.article_id,
        "file_path": result.image_path,
        "image_type": "generated",
        "alt_text": request.alt_text or request.description_jp,
        "generation_prompt": request.prompt_en,
        "generation_params": result.metadata,
        "metadata": {
            **(result.metadata or {}),
            "placeholder_id": request.placeholder_id,
            "description_jp": request.description_jp,
            "prompt_en": request.prompt_en
        }
    }
    
    # GCS情報の追加
    if result.metadata and result.metadata.get("gcs_url"):
        image_data.update({
            "gcs_url": result.metadata.get("gcs_url"),
            "gcs_path": result.metadata.get("gcs_path"),
            "storage_type": "hybrid"
        })
    
    db_result = supabase.table("images").insert(image_data).execute()
    
    return ImageGenerationResponse(
        image_url=result.image_url,
        placeholder_id=request.placeholder_id
    )
```

#### 1.2 プレースホルダーから画像生成

```python
@router.post("/generate-from-placeholder", response_model=ImageGenerationResponse)
async def generate_image_from_placeholder(request: GenerateImageFromPlaceholderRequest):
    """画像プレースホルダーの情報から画像を生成する"""
    
    result = await image_generation_service.generate_image_from_placeholder(
        placeholder_id=request.placeholder_id,
        description_jp=request.description_jp,
        prompt_en=request.prompt_en,
        additional_context=request.additional_context
    )
    
    return result
```

#### 1.3 画像アップロード

```python
@router.post("/upload", response_model=UploadImageResponse)
async def upload_image(
    file: UploadFile = File(...),
    article_id: str = Form(...),
    placeholder_id: str = Form(...),
    alt_text: str = Form(...),
    current_user_id: str = Depends(get_current_user_id_from_token)
):
    """画像をアップロードしてGCSに保存し、記事のプレースホルダーを置き換える"""
    
    # 画像データを読み込み
    image_data = await file.read()
    
    # GCSにアップロード
    success, gcs_url, gcs_path, error = gcs_service.upload_image(
        image_data=image_data,
        filename=file.filename,
        content_type=file.content_type,
        metadata={
            "article_id": article_id, 
            "placeholder_id": placeholder_id, 
            "uploader": current_user_id
        }
    )
    
    # データベースに画像情報を保存
    image_id = str(uuid.uuid4())
    db_result = supabase.table("images").insert({
        "id": image_id,
        "user_id": current_user_id,
        "article_id": article_id,
        "original_filename": file.filename,
        "file_path": gcs_path,
        "gcs_url": gcs_url,
        "gcs_path": gcs_path,
        "image_type": "uploaded",
        "alt_text": alt_text,
        "storage_type": "gcs",
        "metadata": {"placeholder_id": placeholder_id}
    }).execute()
    
    # プレースホルダーを画像で置き換え
    return await replace_placeholder_in_article(article_id, placeholder_id, gcs_url, alt_text, image_id)
```

#### 1.4 プレースホルダー置き換え

```python
@router.post("/replace-placeholder")
async def replace_placeholder_with_image(
    request: ImageReplaceRequest,
    current_user_id: str = Depends(get_current_user_id_from_token)
):
    """記事内のプレースホルダーを画像で置き換える"""
    
    # 記事の取得
    article_result = supabase.table("articles").select("*").eq("id", request.article_id).eq("user_id", current_user_id).execute()
    article = article_result.data[0]
    current_content = article["content"]
    
    # プレースホルダーパターンの作成
    placeholder_pattern = f'<!-- IMAGE_PLACEHOLDER: {request.placeholder_id}\\|[^>]+ -->'
    
    # 置き換えHTML
    replacement_html = f'<img src="{request.image_url}" alt="{request.alt_text}" class="article-image" data-placeholder-id="{request.placeholder_id}" data-image-id="{image_id}" />'
    
    # 正規表現で置換
    updated_content = re.sub(placeholder_pattern, replacement_html, current_content)
    
    # 記事内容を更新
    update_result = supabase.table("articles").update({"content": updated_content}).eq("id", request.article_id).execute()
    
    # プレースホルダーの状態を更新
    supabase.table("image_placeholders").update({
        "replaced_with_image_id": image_id,
        "status": "replaced"
    }).eq("article_id", request.article_id).eq("placeholder_id", request.placeholder_id).execute()
    
    return {
        "success": True,
        "message": "プレースホルダーが画像で置き換えられました",
        "image_id": image_id,
        "updated_content": updated_content
    }
```

### 2. データモデル

```python
class ImageGenerationRequest(BaseModel):
    placeholder_id: str
    description_jp: str
    prompt_en: str
    alt_text: Optional[str] = None
    article_id: Optional[str] = None

class ImageGenerationResponse(BaseModel):
    image_url: str
    placeholder_id: str

class GenerateImageFromPlaceholderRequest(BaseModel):
    placeholder_id: str = Field(description="プレースホルダーID")
    description_jp: str = Field(description="画像の説明（日本語）")
    prompt_en: str = Field(description="画像生成用の英語プロンプト")
    additional_context: Optional[str] = Field(default=None, description="追加のコンテキスト情報")
    aspect_ratio: Optional[str] = Field(default="16:9", description="アスペクト比")
    quality: Optional[int] = Field(default=85, description="JPEG品質 (0-100)")

class UploadImageResponse(BaseModel):
    success: bool = Field(description="アップロード成功フラグ")
    image_url: Optional[str] = Field(default=None, description="アップロードされた画像のURL")
    image_path: Optional[str] = Field(default=None, description="アップロードされた画像のローカルパス")
    error_message: Optional[str] = Field(default=None, description="エラーメッセージ")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="画像メタデータ")
```

## プレースホルダー管理フロー

### 1. 記事生成時のプレースホルダー挿入

```python
# ProcessPersistenceServiceでの処理
async def extract_and_save_placeholders(self, supabase, article_id: str, content: str) -> None:
    """記事内容から画像プレースホルダーを抽出してデータベースに保存する"""
    
    # 画像プレースホルダーのパターン
    pattern = r'<!-- IMAGE_PLACEHOLDER: ([^|]+)\|([^|]+)\|([^>]+) -->'
    matches = re.findall(pattern, content)
    
    # 各プレースホルダーをデータベースに保存
    for index, (placeholder_id, description_jp, prompt_en) in enumerate(matches):
        placeholder_data = {
            "article_id": article_id,
            "placeholder_id": placeholder_id.strip(),
            "description_jp": description_jp.strip(),
            "prompt_en": prompt_en.strip(),
            "position_index": index + 1,
            "status": "pending"
        }
        
        # ON CONFLICT DO UPDATEでupsert
        result = supabase.table("image_placeholders").upsert(
            placeholder_data,
            on_conflict="article_id,placeholder_id"
        ).execute()
```

### 2. データベース関数による自動処理

```sql
-- プレースホルダーを画像で置き換える関数
CREATE OR REPLACE FUNCTION replace_placeholder_with_image(
  article_id_param UUID,
  placeholder_id_param TEXT,
  image_id_param UUID,
  image_url TEXT,
  alt_text_param TEXT DEFAULT ''
)
RETURNS VOID AS $$
DECLARE
  current_content TEXT;
  placeholder_pattern TEXT;
  replacement_html TEXT;
  updated_content TEXT;
BEGIN
  -- 記事内容を取得
  SELECT content INTO current_content FROM articles WHERE id = article_id_param;
  
  -- プレースホルダーパターンを作成
  placeholder_pattern := '<!-- IMAGE_PLACEHOLDER: ' || placeholder_id_param || '\|[^>]+ -->';
  
  -- 置き換えHTMLを作成
  replacement_html := '<img src="' || image_url || '" alt="' || alt_text_param || '" class="article-image" />';
  
  -- プレースホルダーを画像HTMLで置き換え
  updated_content := regexp_replace(current_content, placeholder_pattern, replacement_html, 'g');
  
  -- 記事内容を更新
  UPDATE articles SET content = updated_content WHERE id = article_id_param;
  
  -- プレースホルダーの状態を更新
  UPDATE image_placeholders 
  SET 
    replaced_with_image_id = image_id_param,
    status = 'replaced',
    updated_at = TIMEZONE('utc'::text, now())
  WHERE article_id = article_id_param AND placeholder_id = placeholder_id_param;
END;
$$ LANGUAGE plpgsql;
```

## 運用・管理機能

### 1. 画像配信エンドポイント

```python
@router.get("/serve/{image_filename}")
async def serve_image(image_filename: str):
    """保存された画像を提供する"""
    
    storage_path = Path(settings.image_storage_path)
    image_path = storage_path / image_filename
    
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    
    # セキュリティチェック: パストラバーサル攻撃を防ぐ
    if not str(image_path.resolve()).startswith(str(storage_path.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    return FileResponse(
        path=str(image_path),
        media_type="image/jpeg",
        filename=image_filename
    )
```

### 2. 設定テストエンドポイント

```python
@router.get("/test-config")
async def test_config():
    """Google Cloud設定のテスト"""
    
    service = ImageGenerationService()
    
    config_status = {
        "service_initialized": service._initialized,
        "project_id": service.project_id or "Not configured",
        "location": service.location,
        "has_credentials": service._credentials is not None,
        "client_type": "vertex_ai_legacy",
    }
    
    return {
        "status": "ok",
        "config": config_status
    }
```

### 3. 画像メタデータ管理

生成された画像には詳細なメタデータが付与されます：

```python
metadata = {
    "model": self.model_name,                    # 使用モデル
    "prompt": japan_prompt,                      # 生成プロンプト
    "aspect_ratio": generation_params["aspect_ratio"],
    "safety_filter_level": generation_params["safety_filter_level"],
    "person_generation": generation_params["person_generation"],
    "format": output_format,                     # 画像フォーマット
    "quality": quality,                          # JPEG品質
    "file_size": len(image_data),               # ファイルサイズ
    "sdk": "vertex_ai",                         # 使用SDK
    "storage_type": storage_type,               # ストレージタイプ
    "local_path": str(image_path),              # ローカルパス
    "local_url": f"http://localhost:8008/images/{image_filename}",
    "gcs_url": gcs_url,                         # GCS URL
    "gcs_path": gcs_path                        # GCSパス
}
```

## セキュリティとアクセス制御

### 1. Row Level Security (RLS) ポリシー

```sql
-- 画像テーブルのRLSポリシー
CREATE POLICY "Users can manage their own images" ON images
  FOR ALL USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

-- 組織メンバーは組織の画像を閲覧可能
CREATE POLICY "Organization members can view organization images" ON images
  FOR SELECT USING (
    organization_id IS NOT NULL AND
    EXISTS (
      SELECT 1 FROM organization_members 
      WHERE organization_members.organization_id = images.organization_id 
      AND organization_members.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

-- プレースホルダーテーブルのRLSポリシー
CREATE POLICY "Users can manage placeholders for their own articles" ON image_placeholders
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM articles 
      WHERE articles.id = image_placeholders.article_id 
      AND articles.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );
```

### 2. ファイルアクセス制御

```python
# パストラバーサル攻撃防止
def serve_image(image_filename: str):
    storage_path = Path(settings.image_storage_path)
    image_path = storage_path / image_filename
    
    # セキュリティチェック
    if not str(image_path.resolve()).startswith(str(storage_path.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file path")
```

### 3. 安全フィルタ

Vertex AI Imagen 4.0の安全フィルタが適用されます：

```python
generation_params = {
    "safety_filter_level": "block_only_high",  # 高リスクコンテンツのみブロック
    "person_generation": "allow_all",          # 人物生成を許可
}
```

## パフォーマンス最適化

### 1. 非同期処理

```python
async def generate_image(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
    """非同期画像生成"""
    
    # 非同期でモデルを使用するため、同期処理をthread poolで実行
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, self._generate_sync, request)
    
    return result
```

### 2. インデックス最適化

```sql
-- パフォーマンス向上のためのインデックス
CREATE INDEX IF NOT EXISTS idx_images_user_id ON images(user_id);
CREATE INDEX IF NOT EXISTS idx_images_article_id ON images(article_id);
CREATE INDEX IF NOT EXISTS idx_images_generation_process_id ON images(generation_process_id);
CREATE INDEX IF NOT EXISTS idx_images_image_type ON images(image_type);

CREATE INDEX IF NOT EXISTS idx_image_placeholders_article_id ON image_placeholders(article_id);
CREATE INDEX IF NOT EXISTS idx_image_placeholders_generation_process_id ON image_placeholders(generation_process_id);
CREATE INDEX IF NOT EXISTS idx_image_placeholders_status ON image_placeholders(status);
```

### 3. 画像品質最適化

```python
# JPEG品質の調整
if output_format.upper() == "JPEG" and quality:
    pil_image = Image.open(io.BytesIO(image_data))
    
    # 品質調整して保存
    with open(image_path, "wb") as f:
        pil_image.save(f, "JPEG", quality=quality)
```

## エラー処理とフォールバック

### 1. 段階的フォールバック

```python
def _generate_sync(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
    """同期的な画像生成処理"""
    try:
        if VERTEX_AI_AVAILABLE:
            return self._generate_with_vertex_ai(request)
        else:
            return ImageGenerationResponse(
                success=False,
                error_message="Vertex AI SDK not available"
            )
    except Exception as e:
        logger.error(f"Sync image generation failed: {e}")
        return ImageGenerationResponse(
            success=False,
            error_message=str(e)
        )
```

### 2. ストレージ障害への対応

```python
# GCSアップロードが失敗してもローカル保存は維持
if gcs_service.is_available():
    try:
        success, gcs_url, gcs_path, error = gcs_service.upload_image(...)
        if success:
            storage_type = "hybrid"
            primary_url = gcs_url
        else:
            logger.warning(f"GCS upload failed: {error}")
            storage_type = "local"
            primary_url = f"http://localhost:8008/images/{image_filename}"
    except Exception as e:
        logger.error(f"Unexpected error during GCS upload: {e}")
        storage_type = "local"
        primary_url = f"http://localhost:8008/images/{image_filename}"
```

### 3. 包括的エラーログ

```python
try:
    # 画像生成処理
    result = await self.generate_image_detailed(gen_request)
except Exception as e:
    logger.error(f"画像生成エラー - placeholder_id: {request.placeholder_id}, error: {e}")
    raise HTTPException(
        status_code=500,
        detail=f"画像生成に失敗しました: {str(e)}"
    )
```

## まとめ

画像生成モードと画像生成機能は、以下の特徴を持ちます：

### 1. 統合されたワークフロー
- エージェントによる自動プレースホルダー挿入
- データベースでの一元管理
- 生成から配置まで完全自動化

### 2. 高品質な画像生成
- Vertex AI Imagen 4.0による最新AI画像生成
- 日本語コンテキストの自動追加
- 柔軟な品質・フォーマット設定

### 3. 堅牢なストレージシステム
- GCSとローカルのハイブリッド保存
- 自動フォールバック機能
- セキュアなファイルアクセス制御

### 4. 包括的な管理機能
- プレースホルダーの状態追跡
- 詳細なメタデータ管理
- 柔軟な置き換え・復元機能

### 5. スケーラブルな設計
- 非同期処理による高性能
- RLSによるマルチテナント対応
- 詳細なエラー処理とログ

この設計により、SEO記事生成において視覚的に魅力的で関連性の高い画像を自動的に生成・配置し、ユーザーエクスペリエンスを大幅に向上させます。