# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging

from core.config import settings
from services.image_generation_service import ImageGenerationService, image_generation_service
from services.gcs_service import gcs_service
from core.auth import get_current_user_id_from_token
from supabase import create_client, Client
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/images", tags=["images"])

# Supabaseクライアントを初期化
supabase: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)

class ImageGenerationRequest(BaseModel):
    placeholder_id: str
    description_jp: str
    prompt_en: str
    alt_text: Optional[str] = None
    article_id: Optional[str] = None

class ImageGenerationResponse(BaseModel):
    image_url: str
    placeholder_id: str

class ImageReplaceRequest(BaseModel):
    article_id: str
    placeholder_id: str
    image_url: str
    alt_text: Optional[str] = ""

class ImageRestoreRequest(BaseModel):
    article_id: str
    placeholder_id: str

@router.get("/test-config")
async def test_config():
    """
    Google Cloud設定のテスト
    """
    try:
        from services.image_generation_service import ImageGenerationService
        
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

@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image(
    request: ImageGenerationRequest,
    current_user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Google Vertex AI Imagen-4を使用して画像を生成（フォールバック付き）
    """
    try:
        logger.info(f"画像生成リクエスト - placeholder_id: {request.placeholder_id}, user_id: {current_user_id}")
        
        # 画像生成サービスを初期化（デフォルトでImagen-4.0）
        image_service = ImageGenerationService()
        
        # 詳細な画像生成を実行
        from services.image_generation_service import ImageGenerationRequest as GenRequest
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

@router.post("/test-imagen4", response_model=ImageGenerationResponse)
async def test_imagen4(
    request: ImageGenerationRequest,
    current_user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Imagen-4.0を直接テスト
    """
    try:
        logger.info(f"Imagen-4.0テスト - placeholder_id: {request.placeholder_id}, user_id: {current_user_id}")
        
        # 画像生成を実行
        image_url = await image_generation_service.generate_image(
            prompt=request.prompt_en,
            placeholder_id=request.placeholder_id,
            user_id=current_user_id
        )
        
        logger.info(f"Imagen-4.0テスト成功 - image_url: {image_url}")
        
        return ImageGenerationResponse(
            image_url=image_url,
            placeholder_id=request.placeholder_id
        )
        
    except Exception as e:
        logger.error(f"Imagen-4.0テストエラー - placeholder_id: {request.placeholder_id}, error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Imagen-4.0テストに失敗しました: {str(e)}"
        )


@router.post("/test-direct")
async def test_direct():
    """
    認証なしで直接画像生成をテスト
    """
    try:
        from services.image_generation_service import ImageGenerationRequest
        
        logger.info("=== 直接テスト開始 ===")
        
        # テスト用リクエスト
        test_request = ImageGenerationRequest(
            prompt="A beautiful mountain landscape with snow-capped peaks, professional photography",
            aspect_ratio="16:9",
            output_format="JPEG",
            quality=85
        )
        
        # Imagen-4.0テスト
        logger.info("Imagen-4.0テスト開始")
        try:
            imagen4_result = await image_generation_service.generate_image_detailed(test_request)
            result = {
                "success": imagen4_result.success,
                "model": "imagen-4.0-generate-preview-06-06",
                "image_url": imagen4_result.image_url if imagen4_result.success else None,
                "error": imagen4_result.error_message if not imagen4_result.success else None
            }
            logger.info(f"Imagen-4.0結果: {result}")
            return {
                "status": "test_completed",
                "result": result
            }
        except Exception as e:
            result = {
                "success": False,
                "model": "imagen-4.0-generate-preview-06-06",
                "error": str(e)
            }
            logger.error(f"Imagen-4.0エラー: {e}")
            return {
                "status": "test_failed",
                "result": result
            }
        
    except Exception as e:
        logger.error(f"直接テストエラー: {e}")
        return {
            "status": "test_failed",
            "error": str(e)
        }

@router.post("/test-frontend")
async def test_frontend():
    """
    フロントエンド用の画像生成をテスト（認証なし）
    """
    try:
        logger.info("=== フロントエンド用画像生成テスト開始 ===")
        
        # フロントエンドと同じ方法で画像生成サービスを使用
        image_service = ImageGenerationService()
        
        # フロントエンドからの呼び出しと同じ形式
        image_url = await image_service.generate_image(
            prompt="A beautiful landscape with mountains and blue sky",
            placeholder_id="test_placeholder_frontend",
            user_id="test_user"
        )
        
        logger.info(f"フロントエンド用テスト成功 - image_url: {image_url}")
        
        return {
            "status": "success",
            "image_url": image_url,
            "method": "frontend_style"
        }
        
    except Exception as e:
        logger.error(f"フロントエンド用テストエラー: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@router.get("/test-gcs")
async def test_gcs():
    """
    Google Cloud Storage設定とサービスをテスト
    """
    try:
        logger.info("=== GCS統合テスト開始 ===")
        
        # GCSサービスの状態を確認
        gcs_status = {
            "service_available": gcs_service.is_available(),
            "bucket_name": gcs_service.bucket_name,
            "public_url_base": gcs_service.public_url_base,
            "project_id": gcs_service.project_id,
            "initialized": gcs_service._initialized
        }
        
        # バケット情報を取得（利用可能な場合）
        bucket_info = None
        if gcs_service.is_available():
            bucket_info = gcs_service.get_bucket_info()
        
        result = {
            "status": "ok",
            "gcs_status": gcs_status,
            "bucket_info": bucket_info,
            "message": "GCS service is available" if gcs_service.is_available() else "GCS service not available"
        }
        
        logger.info(f"GCS テスト結果: {result}")
        return result
        
    except Exception as e:
        logger.error(f"GCS テストエラー: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "GCS test failed"
        }

@router.post("/test-gcs-upload")
async def test_gcs_upload():
    """
    GCSへのテスト画像アップロード
    """
    try:
        logger.info("=== GCS アップロードテスト開始 ===")
        
        if not gcs_service.is_available():
            return {
                "status": "error",
                "message": "GCS service not available"
            }
        
        # テスト用のダミー画像データ作成（1x1ピクセルのJPEG）
        test_image_data = bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x11, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0x02, 0x11, 0x01, 0x03, 0x11, 0x01,
            0xFF, 0xC4, 0x00, 0x14, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0xFF, 0xC4,
            0x00, 0x14, 0x10, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xDA, 0x00, 0x0C,
            0x03, 0x01, 0x00, 0x02, 0x11, 0x03, 0x11, 0x00, 0x3F, 0x00, 0x9F, 0xFF, 0xD9
        ])
        
        # GCSにアップロード
        success, gcs_url, gcs_path, error = gcs_service.upload_image(
            image_data=test_image_data,
            filename="test_image.jpg",
            content_type="image/jpeg",
            metadata={"test": "true", "purpose": "gcs_integration_test"}
        )
        
        result = {
            "status": "success" if success else "error",
            "upload_success": success,
            "gcs_url": gcs_url,
            "gcs_path": gcs_path,
            "error": error,
            "test_data_size": len(test_image_data)
        }
        
        # アップロードが成功した場合、画像情報も取得
        if success and gcs_path:
            image_info = gcs_service.get_image_info(gcs_path)
            result["image_info"] = image_info
        
        logger.info(f"GCS アップロードテスト結果: {result}")
        return result
        
    except Exception as e:
        logger.error(f"GCS アップロードテストエラー: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "GCS upload test failed"
        }

@router.post("/test-full-integration")
async def test_full_integration():
    """
    GCS統合を含む完全な画像生成テスト
    """
    try:
        logger.info("=== 完全統合テスト開始 ===")
        
        from services.image_generation_service import ImageGenerationRequest
        
        # テスト用リクエスト
        test_request = ImageGenerationRequest(
            prompt="A simple test image for GCS integration",
            aspect_ratio="4:3",
            output_format="JPEG",
            quality=85
        )
        
        # 画像生成（GCS統合済み）
        result = await image_generation_service.generate_image_detailed(test_request)
        
        integration_result = {
            "status": "success" if result.success else "error",
            "generation_success": result.success,
            "image_url": result.image_url,
            "local_path": result.image_path if result.success else None,
            "metadata": result.metadata if result.success else None,
            "error": result.error_message if not result.success else None,
            "gcs_info": {
                "gcs_url": result.metadata.get("gcs_url") if result.success and result.metadata else None,
                "gcs_path": result.metadata.get("gcs_path") if result.success and result.metadata else None,
                "storage_type": result.metadata.get("storage_type") if result.success and result.metadata else None
            }
        }
        
        logger.info(f"完全統合テスト結果: {integration_result}")
        return integration_result
        
    except Exception as e:
        logger.error(f"完全統合テストエラー: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Full integration test failed"
        }

@router.post("/test-replace")
async def test_replace_endpoint():
    """
    テスト用の簡単なエンドポイント
    """
    logger.info("=== TEST REPLACE ENDPOINT REACHED ===")
    return {"success": True, "message": "Test endpoint working"}

@router.post("/replace-placeholder")
async def replace_placeholder_with_image(
    request: ImageReplaceRequest,
    current_user_id: str = Depends(get_current_user_id_from_token)
):
    """
    記事内のプレースホルダーを画像で置き換える
    """
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
            
            placeholder = {
                "placeholder_id": request.placeholder_id,
                "description_jp": description_jp,
                "prompt_en": prompt_en
            }
        else:
            placeholder = placeholder_result.data[0]
        
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
        placeholder_update = supabase.table("image_placeholders").update({
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

@router.post("/restore-placeholder")
async def restore_placeholder(
    request: ImageRestoreRequest,
    current_user_id: str = Depends(get_current_user_id_from_token)
):
    """
    画像をプレースホルダーに戻す
    """
    try:
        logger.info(f"プレースホルダー復元開始 - article_id: {request.article_id}, placeholder_id: {request.placeholder_id}")
        
        # 記事の取得と権限確認
        article_result = supabase.table("articles").select("*").eq("id", request.article_id).eq("user_id", current_user_id).execute()
        
        if not article_result.data:
            raise HTTPException(status_code=404, detail="記事が見つからないか、アクセス権限がありません")
        
        article = article_result.data[0]
        current_content = article["content"]
        
        # プレースホルダー情報を取得
        placeholder_result = supabase.table("image_placeholders").select("*").eq("article_id", request.article_id).eq("placeholder_id", request.placeholder_id).execute()
        
        if not placeholder_result.data:
            raise HTTPException(status_code=404, detail="プレースホルダーが見つかりません")
        
        placeholder = placeholder_result.data[0]
        
        # 画像タグパターンを作成（data-placeholder-id属性を使用）
        image_pattern = f'<img[^>]*data-placeholder-id="{request.placeholder_id}"[^>]*/?>'
        
        # プレースホルダーHTMLを復元
        placeholder_html = f'<!-- IMAGE_PLACEHOLDER: {placeholder["placeholder_id"]}|{placeholder["description_jp"]}|{placeholder["prompt_en"]} -->'
        
        # 正規表現で置換
        import re
        updated_content = re.sub(image_pattern, placeholder_html, current_content)
        
        # 記事内容を更新
        update_result = supabase.table("articles").update({"content": updated_content}).eq("id", request.article_id).execute()
        
        if not update_result.data:
            raise HTTPException(status_code=500, detail="記事の更新に失敗しました")
        
        # プレースホルダーの状態を復元
        placeholder_update = supabase.table("image_placeholders").update({
            "replaced_with_image_id": None,
            "status": "pending"
        }).eq("article_id", request.article_id).eq("placeholder_id", request.placeholder_id).execute()
        
        logger.info(f"プレースホルダー復元成功 - article_id: {request.article_id}, placeholder_id: {request.placeholder_id}")
        
        return {
            "success": True,
            "message": "画像がプレースホルダーに戻されました",
            "updated_content": updated_content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"プレースホルダー復元エラー - article_id: {request.article_id}, error: {e}")
        raise HTTPException(status_code=500, detail=f"プレースホルダー復元に失敗しました: {str(e)}")

@router.get("/placeholders/{article_id}")
async def get_article_placeholders(
    article_id: str,
    current_user_id: str = Depends(get_current_user_id_from_token)
):
    """
    記事のプレースホルダー情報を取得
    """
    try:
        # 記事の権限確認
        article_result = supabase.table("articles").select("id").eq("id", article_id).eq("user_id", current_user_id).execute()
        
        if not article_result.data:
            raise HTTPException(status_code=404, detail="記事が見つからないか、アクセス権限がありません")
        
        # プレースホルダー情報を取得
        placeholders_result = supabase.table("image_placeholders").select("*, images(*)").eq("article_id", article_id).execute()
        
        return {
            "article_id": article_id,
            "placeholders": placeholders_result.data or []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"プレースホルダー取得エラー - article_id: {article_id}, error: {e}")
        raise HTTPException(status_code=500, detail=f"プレースホルダー情報の取得に失敗しました: {str(e)}")

@router.get("/article-images/{article_id}")
async def get_article_images(
    article_id: str,
    current_user_id: str = Depends(get_current_user_id_from_token)
):
    """
    記事に関連する画像とプレースホルダーの情報を取得（記事読み込み時の画像復元用）
    """
    try:
        # 入力値の検証
        if not article_id:
            raise HTTPException(status_code=400, detail="記事IDが指定されていません")
        
        # 記事の権限確認
        try:
            article_result = supabase.table("articles").select("id, content").eq("id", article_id).eq("user_id", current_user_id).execute()
        except Exception as db_error:
            logger.error(f"記事データベースクエリエラー - article_id: {article_id}, error: {str(db_error)}")
            raise HTTPException(status_code=500, detail="記事情報の取得に失敗しました")
        
        if not article_result.data:
            raise HTTPException(status_code=404, detail="記事が見つからないか、アクセス権限がありません")
        
        article_content = article_result.data[0]["content"]
        
        # プレースホルダー情報を取得（関連する画像情報も含む）
        placeholders_query = """
            placeholder_id,
            description_jp,
            prompt_en,
            status,
            replaced_with_image_id,
            position_index,
            images!image_placeholders_replaced_with_image_id_fkey (
                id,
                file_path,
                gcs_url,
                alt_text,
                metadata,
                created_at
            )
        """
        
        try:
            placeholders_result = supabase.table("image_placeholders").select(placeholders_query).eq("article_id", article_id).order("position_index").execute()
        except Exception as db_error:
            logger.error(f"プレースホルダークエリエラー - article_id: {article_id}, error: {str(db_error)}")
            # エラーでも処理を継続（プレースホルダーなしとして扱う）
            placeholders_result = type('obj', (object,), {'data': []})
        
        # 記事に関連するすべての画像（プレースホルダーに関連付けられていないものも含む）
        try:
            all_images_result = supabase.table("images").select("*").eq("article_id", article_id).eq("user_id", current_user_id).order("created_at", desc=True).execute()
        except Exception as db_error:
            logger.error(f"画像クエリエラー - article_id: {article_id}, error: {str(db_error)}")
            all_images_result = type('obj', (object,), {'data': []})
        
        # プレースホルダーIDごとに生成された画像履歴を取得
        placeholder_images_history = {}
        for placeholder in placeholders_result.data or []:
            placeholder_id = placeholder["placeholder_id"]
            
            # このプレースホルダーで生成された全画像を取得
            try:
                # JSONB フィールドに対する正しいクエリ方法を使用
                images_for_placeholder = supabase.table("images").select("*").eq("article_id", article_id).eq("user_id", current_user_id).contains("metadata", {"placeholder_id": placeholder_id}).order("created_at", desc=True).execute()
            except Exception as db_error:
                logger.error(f"プレースホルダー画像履歴クエリエラー - placeholder_id: {placeholder_id}, error: {str(db_error)}")
                images_for_placeholder = type('obj', (object,), {'data': []})
            
            placeholder_images_history[placeholder_id] = images_for_placeholder.data or []
        
        return {
            "article_id": article_id,
            "article_content": article_content,
            "placeholders": placeholders_result.data or [],
            "all_images": all_images_result.data or [],
            "placeholder_images_history": placeholder_images_history,
            "restored_content": await _restore_article_images(article_id, article_content, placeholders_result.data or [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"記事画像情報取得エラー - article_id: {article_id}, error: {e}")
        raise HTTPException(status_code=500, detail=f"記事画像情報の取得に失敗しました: {str(e)}")

async def _restore_article_images(article_id: str, article_content: str, placeholders: list) -> str:
    """
    記事コンテンツ内のプレースホルダーを、関連付けられた画像があれば置き換える
    """
    import re
    
    restored_content = article_content
    
    for placeholder in placeholders:
        placeholder_id = placeholder["placeholder_id"]
        
        # 置き換えられた画像があるかチェック
        if placeholder["status"] == "replaced" and placeholder["replaced_with_image_id"] and placeholder.get("images"):
            image_data = placeholder["images"]
            
            # プレースホルダーパターンを検索
            placeholder_pattern = f'<!-- IMAGE_PLACEHOLDER: {re.escape(placeholder_id)}\\|[^>]+ -->'
            
            # 画像URL（GCSを優先、なければローカルパス）
            image_url = image_data.get("gcs_url") or image_data.get("file_path", "")
            alt_text = image_data.get("alt_text", placeholder["description_jp"])
            image_id = image_data["id"]
            
            # 画像HTMLを作成
            image_html = f'<img src="{image_url}" alt="{alt_text}" class="article-image" data-placeholder-id="{placeholder_id}" data-image-id="{image_id}" />'
            
            # プレースホルダーを画像で置き換え
            restored_content = re.sub(placeholder_pattern, image_html, restored_content)
    
    return restored_content

@router.post("/generate-and-link")
async def generate_and_link_image(
    request: ImageGenerationRequest,
    current_user_id: str = Depends(get_current_user_id_from_token)
):
    """
    画像を生成してプレースホルダーと関連付け（記事更新は行わない）
    """
    try:
        logger.info(f"画像生成・関連付けリクエスト - placeholder_id: {request.placeholder_id}, user_id: {current_user_id}")
        
        # 画像生成サービスを初期化
        image_service = ImageGenerationService()
        
        # 画像生成を実行
        from services.image_generation_service import ImageGenerationRequest as GenRequest
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
        image_data = {
            "id": str(uuid.uuid4()),
            "user_id": current_user_id,
            "file_path": result.image_path,
            "image_type": "generated",
            "alt_text": request.alt_text or request.description_jp,
            "generation_prompt": request.prompt_en,
            "generation_params": result.metadata,
            "metadata": {
                **(result.metadata or {}),
                "placeholder_id": request.placeholder_id,
                "description_jp": request.description_jp
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
        
        if not db_result.data:
            raise HTTPException(status_code=500, detail="画像データベース保存に失敗しました")
        
        logger.info(f"画像生成・関連付け成功 - image_url: {result.image_url}, image_id: {image_data['id']}")
        
        return {
            "success": True,
            "image_id": image_data["id"],
            "image_url": result.image_url,
            "placeholder_id": request.placeholder_id,
            "alt_text": image_data["alt_text"],
            "created_at": db_result.data[0]["created_at"]
        }
        
    except Exception as e:
        logger.error(f"画像生成・関連付けエラー - placeholder_id: {request.placeholder_id}, error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"画像生成・関連付けに失敗しました: {str(e)}"
        )

@router.get("/placeholder-history/{article_id}/{placeholder_id}")
async def get_placeholder_image_history(
    article_id: str,
    placeholder_id: str,
    current_user_id: str = Depends(get_current_user_id_from_token)
):
    """
    特定のプレースホルダーで生成された画像履歴を取得
    """
    try:
        # 記事の権限確認
        article_result = supabase.table("articles").select("id").eq("id", article_id).eq("user_id", current_user_id).execute()
        
        if not article_result.data:
            raise HTTPException(status_code=404, detail="記事が見つからないか、アクセス権限がありません")
        
        # プレースホルダーに関連する画像履歴を取得
        images_result = supabase.table("images").select("*").eq("article_id", article_id).eq("user_id", current_user_id).contains("metadata", {"placeholder_id": placeholder_id}).order("created_at", desc=True).execute()
        
        # プレースホルダー情報も取得
        placeholder_result = supabase.table("image_placeholders").select("*").eq("article_id", article_id).eq("placeholder_id", placeholder_id).execute()
        
        return {
            "article_id": article_id,
            "placeholder_id": placeholder_id,
            "placeholder_info": placeholder_result.data[0] if placeholder_result.data else None,
            "images_history": images_result.data or [],
            "total_images": len(images_result.data or [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"プレースホルダー画像履歴取得エラー - article_id: {article_id}, placeholder_id: {placeholder_id}, error: {e}")
        raise HTTPException(status_code=500, detail=f"プレースホルダー画像履歴の取得に失敗しました: {str(e)}")