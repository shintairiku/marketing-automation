# -*- coding: utf-8 -*-
# 統合された画像生成エンドポイント（routers/images.py + routers/image_generation.py）

import uuid
from pathlib import Path
from typing import Dict, Optional, Any

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import logging

from app.core.config import settings
from .service import ImageGenerationService, image_generation_service
from app.infrastructure.external_apis.gcs_service import gcs_service
from app.common.auth import get_current_user_id_from_token
from app.common.database import supabase

logger = logging.getLogger(__name__)

router = APIRouter()

# Supabaseクライアントは共通データベースから使用

# --- Request/Response Models ---

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
    """プレースホルダーから画像を生成するリクエスト"""
    placeholder_id: str = Field(description="プレースホルダーID")
    description_jp: str = Field(description="画像の説明（日本語）")
    prompt_en: str = Field(description="画像生成用の英語プロンプト")
    additional_context: Optional[str] = Field(default=None, description="追加のコンテキスト情報")
    aspect_ratio: Optional[str] = Field(default="16:9", description="アスペクト比")
    quality: Optional[int] = Field(default=85, description="JPEG品質 (0-100)")

class ImageReplaceRequest(BaseModel):
    article_id: str
    placeholder_id: str
    image_url: str
    alt_text: Optional[str] = ""

class ImageRestoreRequest(BaseModel):
    article_id: str
    placeholder_id: str

class UploadImageResponse(BaseModel):
    """画像アップロードレスポンス"""
    success: bool = Field(description="アップロード成功フラグ")
    image_url: Optional[str] = Field(default=None, description="アップロードされた画像のURL")
    image_path: Optional[str] = Field(default=None, description="アップロードされた画像のローカルパス")
    error_message: Optional[str] = Field(default=None, description="エラーメッセージ")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="画像メタデータ")

# --- Test Endpoints ---

@router.get("/test-config")
async def test_config():
    """Google Cloud設定のテスト"""
    try:
        service = ImageGenerationService()
        
        # 初期化状況を確認
        config_status = {
            "service_initialized": service._initialized,
            "project_id": service.project_id or "Not configured",
            "location": service.location,
            "has_credentials": service._credentials is not None,
            "client_type": "genai" if service._client else "vertex_ai_legacy",
        }
        
        return {
            "status": "ok",
            "config": config_status
        }
        
    except Exception as e:
        logger.error(f"設定テストエラー: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

# --- Main Generation Endpoints ---

@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image(
    request: ImageGenerationRequest,
    current_user_id: str = Depends(get_current_user_id_from_token)
):
    """Google Vertex AI Imagen-4を使用して画像を生成（フォールバック付き）"""
    try:
        logger.info(f"画像生成リクエスト - placeholder_id: {request.placeholder_id}, user_id: {current_user_id}")
        
        # 画像生成サービスを初期化（デフォルトでImagen-4.0）
        image_service = ImageGenerationService()
        
        # 詳細な画像生成を実行
        from app.domains.image_generation.service import ImageGenerationRequest as GenRequest
        gen_request = GenRequest(
            prompt=request.prompt_en,
            aspect_ratio="4:3",
            output_format="JPEG",
            quality=85
        )
        
        result = await image_service.generate_image_detailed(gen_request)
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=f"画像生成に失敗しました: {result.error_message}"
            )
        
        # データベースに画像情報を保存
        try:
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
            
            # GCS情報がある場合は追加
            if result.metadata and result.metadata.get("gcs_url"):
                image_data.update({
                    "gcs_url": result.metadata.get("gcs_url"),
                    "gcs_path": result.metadata.get("gcs_path"),
                    "storage_type": result.metadata.get("storage_type", "hybrid")
                })
            else:
                image_data["storage_type"] = "local"
            
            # imagesテーブルに挿入
            db_result = supabase.table("images").insert(image_data).execute()
            
            if db_result.data:
                logger.info(f"画像生成・保存成功 - image_url: {result.image_url}, image_id: {image_data['id']}")
            else:
                logger.warning(f"画像データベース保存に失敗: {db_result}")
                
        except Exception as db_error:
            logger.error(f"画像データベース保存エラー: {db_error}")
            # データベース保存に失敗しても画像生成は成功しているので続行
        
        return ImageGenerationResponse(
            image_url=result.image_url,
            placeholder_id=request.placeholder_id
        )
        
    except Exception as e:
        logger.error(f"画像生成エラー - placeholder_id: {request.placeholder_id}, error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"画像生成に失敗しました: {str(e)}"
        )

@router.post("/generate-from-placeholder", response_model=ImageGenerationResponse)
async def generate_image_from_placeholder(request: GenerateImageFromPlaceholderRequest):
    """画像プレースホルダーの情報から画像を生成する"""
    try:
        result = await image_generation_service.generate_image_from_placeholder(
            placeholder_id=request.placeholder_id,
            description_jp=request.description_jp,
            prompt_en=request.prompt_en,
            additional_context=request.additional_context
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error_message)
        
        return result
        
    except Exception as e:
        logger.error(f"Image generation from placeholder failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Upload Endpoints ---

@router.post("/upload", response_model=UploadImageResponse)
async def upload_image(
    file: UploadFile = File(...),
    article_id: str = Form(...),
    placeholder_id: str = Form(...),
    alt_text: str = Form(...),
    current_user_id: str = Depends(get_current_user_id_from_token)
):
    """画像をアップロードしてGCSに保存し、記事のプレースホルダーを置き換える"""
    try:
        logger.info(f"画像アップロード開始 - article_id: {article_id}, placeholder_id: {placeholder_id}, filename: {file.filename}")

        if not gcs_service.is_available():
            raise HTTPException(status_code=500, detail="GCSサービスが利用できません")

        # 画像データを読み込む
        image_data = await file.read()

        # GCSにアップロード
        success, gcs_url, gcs_path, error = gcs_service.upload_image(
            image_data=image_data,
            filename=file.filename,
            content_type=file.content_type,
            metadata={"article_id": article_id, "placeholder_id": placeholder_id, "uploader": current_user_id}
        )

        if not success:
            raise HTTPException(status_code=500, detail=f"GCSへのアップロードに失敗しました: {error}")

        # データベースに画像情報を保存
        image_id = str(uuid.uuid4())
        db_result = supabase.table("images").insert({
            "id": image_id,
            "user_id": current_user_id,
            "article_id": article_id,
            "original_filename": file.filename,
            "file_path": gcs_path,  # NOT NULL制約を満たすためにGCSパスを保存
            "gcs_url": gcs_url,
            "gcs_path": gcs_path,
            "image_type": "uploaded",
            "alt_text": alt_text,
            "storage_type": "gcs",
            "metadata": {"placeholder_id": placeholder_id}
        }).execute()

        if not db_result.data:
            raise HTTPException(status_code=500, detail="画像情報のデータベース保存に失敗しました")

        # 記事のコンテンツを取得
        article_result = supabase.table("articles").select("content").eq("id", article_id).eq("user_id", current_user_id).execute()
        if not article_result.data:
            raise HTTPException(status_code=404, detail="記事が見つかりません")
        
        current_content = article_result.data[0]['content']

        # プレースホルダーを新しい画像で置き換え
        import re
        placeholder_pattern = f'<!-- IMAGE_PLACEHOLDER: {re.escape(placeholder_id)}\\|[^>]+ -->'
        replacement_html = f'<img src="{gcs_url}" alt="{alt_text}" class="article-image" data-placeholder-id="{placeholder_id}" data-image-id="{image_id}" />'
        updated_content, count = re.subn(placeholder_pattern, replacement_html, current_content)

        if count == 0:
            # プレースホルダーが見つからない場合でも、画像はアップロードされているのでエラーにはしない
            logger.warning(f"プレースホルダーが見つからなかったため、記事内容は更新されませんでした。placeholder_id: {placeholder_id}")
            return {
                "success": True,
                "message": "画像はアップロードされましたが、記事内のプレースホルダーが見つかりませんでした。",
                "image_id": image_id,
                "image_url": gcs_url,
                "gcs_path": gcs_path,
                "updated_content": current_content # 変更なしのコンテンツ
            }

        # 記事内容を更新
        update_result = supabase.table("articles").update({"content": updated_content}).eq("id", article_id).execute()
        if not update_result.data:
            raise HTTPException(status_code=500, detail="記事の更新に失敗しました")

        # プレースホルダーの状態を更新
        supabase.table("image_placeholders").update({
            "replaced_with_image_id": image_id,
            "status": "replaced"
        }).eq("article_id", article_id).eq("placeholder_id", placeholder_id).execute()

        logger.info(f"画像アップロード・置き換え成功 - image_id: {image_id}")

        return {
            "success": True,
            "message": "画像が正常にアップロードされ、記事が更新されました。",
            "image_id": image_id,
            "image_url": gcs_url,
            "gcs_path": gcs_path,
            "updated_content": updated_content
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"画像アップロードエラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"予期せぬエラーが発生しました: {str(e)}")

# --- Image Management Endpoints ---

@router.post("/replace-placeholder")
async def replace_placeholder_with_image(
    request: ImageReplaceRequest,
    current_user_id: str = Depends(get_current_user_id_from_token)
):
    """記事内のプレースホルダーを画像で置き換える"""
    try:
        logger.info(f"画像置き換え開始 - article_id: {request.article_id}, placeholder_id: {request.placeholder_id}")
        
        # 記事の取得と権限確認
        article_result = supabase.table("articles").select("*").eq("id", request.article_id).eq("user_id", current_user_id).execute()
        
        if not article_result.data:
            raise HTTPException(status_code=404, detail="記事が見つからないか、アクセス権限がありません")
        
        article = article_result.data[0]
        current_content = article["content"]
        
        # プレースホルダー情報を取得（存在しない場合は記事コンテンツから抽出して作成）
        placeholder_result = supabase.table("image_placeholders").select("*").eq("article_id", request.article_id).eq("placeholder_id", request.placeholder_id).execute()
        
        if not placeholder_result.data:
            # 記事内容からプレースホルダーを検索
            import re
            pattern = f'<!-- IMAGE_PLACEHOLDER: {request.placeholder_id}\\|([^|]+)\\|([^>]+) -->'
            match = re.search(pattern, current_content)
            
            if not match:
                raise HTTPException(status_code=404, detail="プレースホルダーが記事内に見つかりません")
            
            description_jp = match.group(1).strip()
            prompt_en = match.group(2).strip()
            
            # プレースホルダーをデータベースに作成
            placeholder_data = {
                "article_id": request.article_id,
                "placeholder_id": request.placeholder_id,
                "description_jp": description_jp,
                "prompt_en": prompt_en,
                "position_index": 1,
                "status": "pending"
            }
            
            placeholder_insert = supabase.table("image_placeholders").insert(placeholder_data).execute()
            if not placeholder_insert.data:
                logger.warning(f"Failed to create placeholder in database: {placeholder_insert}")
            
        else:
            placeholder_result.data[0]
        
        # 画像情報を取得
        image_result = supabase.table("images").select("*").eq("user_id", current_user_id).or_(f"gcs_url.eq.{request.image_url},file_path.like.%{request.image_url.split('/')[-1]}").execute()
        
        if not image_result.data:
            # 画像が見つからない場合は新しく作成
            image_data = {
                "id": str(uuid.uuid4()),
                "user_id": current_user_id,
                "article_id": request.article_id,
                "file_path": request.image_url,
                "image_type": "generated",
                "alt_text": request.alt_text,
                "metadata": {"source": "placeholder_replacement"}
            }
            
            if request.image_url.startswith("https://storage.googleapis.com/"):
                image_data.update({
                    "gcs_url": request.image_url,
                    "storage_type": "gcs"
                })
            else:
                image_data["storage_type"] = "local"
            
            db_result = supabase.table("images").insert(image_data).execute()
            if db_result.data:
                image_id = image_data["id"]
            else:
                raise HTTPException(status_code=500, detail="画像データの保存に失敗しました")
        else:
            image_id = image_result.data[0]["id"]
        
        # プレースホルダーパターンを作成
        placeholder_pattern = f'<!-- IMAGE_PLACEHOLDER: {request.placeholder_id}\\|[^>]+ -->'
        
        # 置き換えHTML
        replacement_html = f'<img src="{request.image_url}" alt="{request.alt_text}" class="article-image" data-placeholder-id="{request.placeholder_id}" data-image-id="{image_id}" />'
        
        # 正規表現で置換
        import re
        updated_content = re.sub(placeholder_pattern, replacement_html, current_content)
        
        # 記事内容を更新
        update_result = supabase.table("articles").update({"content": updated_content}).eq("id", request.article_id).execute()
        
        if not update_result.data:
            raise HTTPException(status_code=500, detail="記事の更新に失敗しました")
        
        # プレースホルダーの状態を更新
        supabase.table("image_placeholders").update({
            "replaced_with_image_id": image_id,
            "status": "replaced"
        }).eq("article_id", request.article_id).eq("placeholder_id", request.placeholder_id).execute()
        
        logger.info(f"画像置き換え成功 - article_id: {request.article_id}, placeholder_id: {request.placeholder_id}, image_id: {image_id}")
        
        return {
            "success": True,
            "message": "プレースホルダーが画像で置き換えられました",
            "image_id": image_id,
            "updated_content": updated_content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"画像置き換えエラー - article_id: {request.article_id}, error: {e}")
        raise HTTPException(status_code=500, detail=f"画像置き換えに失敗しました: {str(e)}")

# --- Static File Serving ---

@router.get("/serve/{image_filename}")
async def serve_image(image_filename: str):
    """保存された画像を提供する"""
    try:
        storage_path = Path(settings.image_storage_path if hasattr(settings, 'image_storage_path') else "./generated_images")
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to serve image {image_filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Additional endpoints from routers/images.py can be added here as needed ---