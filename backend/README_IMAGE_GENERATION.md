# 画像生成サービス設定ガイド

## 概要

Vertex AI Imagen を使用した画像生成サービスの設定は、環境変数で柔軟に管理できます。

## 環境変数設定

### 基本設定

```bash
# 必須: Google Cloud設定
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'

# 画像生成モデル設定
IMAGEN_MODEL_NAME=imagen-4.0-generate-preview-06-06
IMAGEN_ASPECT_RATIO=4:3
IMAGEN_OUTPUT_FORMAT=JPEG
IMAGEN_QUALITY=85
IMAGEN_SAFETY_FILTER=block_only_high
IMAGEN_PERSON_GENERATION=allow_all
IMAGEN_ADD_JAPAN_PREFIX=true
```

### 利用可能なモデル

現在サポートされているモデル:
- `imagen-4.0-generate-preview-06-06` (推奨)
- その他のImagen 4.0派生モデル

### 設定オプション

#### アスペクト比 (`IMAGEN_ASPECT_RATIO`)
- `1:1` - 正方形
- `4:3` - 横長（デフォルト）
- `3:4` - 縦長
- `16:9` - ワイドスクリーン
- `9:16` - 縦長ワイドスクリーン

#### 出力フォーマット (`IMAGEN_OUTPUT_FORMAT`)
- `JPEG` - 圧縮画像（デフォルト）
- `PNG` - 非圧縮画像

#### 品質設定 (`IMAGEN_QUALITY`)
- `1-100` の範囲（デフォルト: 85）
- JPEG形式のみ適用

#### 安全フィルタ (`IMAGEN_SAFETY_FILTER`)
- `block_only_high` - 高リスクコンテンツのみブロック（デフォルト）
- `block_some` - 一部コンテンツをブロック
- `block_most` - 大部分のコンテンツをブロック

#### 人物生成設定 (`IMAGEN_PERSON_GENERATION`)
- `allow_all` - すべての人物生成を許可（デフォルト）
- `allow_adult` - 成人のみ許可
- `dont_allow` - 人物生成を禁止

#### 日本プレフィックス (`IMAGEN_ADD_JAPAN_PREFIX`)
- `true` - プロンプトに「In Japan.」を自動追加（デフォルト）
- `false` - プロンプトをそのまま使用

## 使用例

### 開発環境
```bash
IMAGEN_MODEL_NAME=imagen-4.0-generate-preview-06-06
IMAGEN_ASPECT_RATIO=4:3
IMAGEN_OUTPUT_FORMAT=JPEG
IMAGEN_QUALITY=75
IMAGEN_ADD_JAPAN_PREFIX=true
```

### 本番環境（高品質）
```bash
IMAGEN_MODEL_NAME=imagen-4.0-generate-preview-06-06
IMAGEN_ASPECT_RATIO=16:9
IMAGEN_OUTPUT_FORMAT=PNG
IMAGEN_QUALITY=95
IMAGEN_SAFETY_FILTER=block_most
```

### 実験環境（新モデル）
```bash
# 新しいモデルが利用可能になった場合
IMAGEN_MODEL_NAME=imagen-5.0-preview
IMAGEN_ASPECT_RATIO=1:1
IMAGEN_ADD_JAPAN_PREFIX=false
```

## 設定の確認

サービス起動時に、以下のログで設定が確認できます:

```
INFO: Generating image with Vertex AI SDK using model: imagen-4.0-generate-preview-06-06
INFO: Modified prompt with Japan prefix: In Japan. [your prompt]
```

## トラブルシューティング

### モデルが見つからない場合
- `IMAGEN_MODEL_NAME` の値を確認
- Google Cloud プロジェクトでのモデルアクセス権限を確認

### 画質が期待と異なる場合
- `IMAGEN_QUALITY` を調整（75-95推奨）
- `IMAGEN_OUTPUT_FORMAT` をPNGに変更

### 安全フィルタで画像が生成されない場合
- `IMAGEN_SAFETY_FILTER` を `block_only_high` に変更
- プロンプトの内容を調整