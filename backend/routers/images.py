# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging

from core.config import settings
from services.image_generation_service import ImageGenerationService, image_generation_service
from core.auth import get_current_user_id_from_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/images", tags=["images"])

class ImageGenerationRequest(BaseModel):
    placeholder_id: str
    description_jp: str
    prompt_en: str
    alt_text: Optional[str] = None

class ImageGenerationResponse(BaseModel):
    image_url: str
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
        
        # 画像生成を実行
        image_url = await image_service.generate_image(
            prompt=request.prompt_en,
            placeholder_id=request.placeholder_id,
            user_id=current_user_id
        )
        
        logger.info(f"画像生成成功 - image_url: {image_url}")
        
        return ImageGenerationResponse(
            image_url=image_url,
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