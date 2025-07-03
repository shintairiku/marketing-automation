# -*- coding: utf-8 -*-
"""
画像生成API エンドポイント
"""

import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, File, UploadFile, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from core.config import settings
from core.logger import logger
from services.image_generation_service import (
    image_generation_service, 
    ImageGenerationRequest, 
    ImageGenerationResponse
)

router = APIRouter(prefix="/api/images", tags=["Image Generation"])


class GenerateImageFromPlaceholderRequest(BaseModel):
    """プレースホルダーから画像を生成するリクエスト"""
    placeholder_id: str = Field(description="プレースホルダーID")
    description_jp: str = Field(description="画像の説明（日本語）")
    prompt_en: str = Field(description="画像生成用の英語プロンプト")
    additional_context: Optional[str] = Field(default=None, description="追加のコンテキスト情報")
    aspect_ratio: Optional[str] = Field(default="16:9", description="アスペクト比")
    quality: Optional[int] = Field(default=85, description="JPEG品質 (0-100)")


class UploadImageRequest(BaseModel):
    """画像アップロードレスポンス"""
    success: bool = Field(description="アップロード成功フラグ")
    image_url: Optional[str] = Field(default=None, description="アップロードされた画像のURL")
    image_path: Optional[str] = Field(default=None, description="アップロードされた画像のローカルパス")
    error_message: Optional[str] = Field(default=None, description="エラーメッセージ")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="画像メタデータ")


@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenerationRequest):
    """
    Vertex AI Imagen 4.0を使用して画像を生成する
    """
    try:
        result = await image_generation_service.generate_image(request)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error_message)
        
        return result
        
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-from-placeholder", response_model=ImageGenerationResponse)
async def generate_image_from_placeholder(request: GenerateImageFromPlaceholderRequest):
    """
    画像プレースホルダーの情報から画像を生成する
    """
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


@router.post("/upload", response_model=UploadImageRequest)
async def upload_image(file: UploadFile = File(...)):
    """
    画像をアップロードして保存する
    """
    try:
        # ファイルタイプの検証
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Only image files are allowed")
        
        # ファイルサイズの検証 (10MB制限)
        max_size = 10 * 1024 * 1024  # 10MB
        file_size = 0
        content = bytearray()
        
        while chunk := await file.read(1024):
            file_size += len(chunk)
            if file_size > max_size:
                raise HTTPException(status_code=413, detail="File too large (max 10MB)")
            content.extend(chunk)
        
        # ファイル名の生成
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        image_filename = f"uploaded_{uuid.uuid4().hex}.{file_extension}"
        
        # 保存先パスの設定
        storage_path = Path(settings.image_storage_path if hasattr(settings, 'image_storage_path') else "./generated_images")
        storage_path.mkdir(exist_ok=True)
        image_path = storage_path / image_filename
        
        # ファイルを保存
        with open(image_path, "wb") as f:
            f.write(content)
        
        # 画像情報を取得
        image_info = await image_generation_service.get_image_info(str(image_path))
        
        return UploadImageRequest(
            success=True,
            image_path=str(image_path),
            image_url=f"/images/{image_filename}",
            metadata={
                "original_filename": file.filename,
                "content_type": file.content_type,
                "file_size": file_size,
                "image_info": image_info
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/serve/{image_filename}")
async def serve_image(image_filename: str):
    """
    保存された画像を提供する
    """
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
            media_type="image/jpeg",  # デフォルト、実際のファイルタイプに応じて調整可能
            filename=image_filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to serve image {image_filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{image_filename}")
async def delete_image(image_filename: str, background_tasks: BackgroundTasks):
    """
    保存された画像を削除する
    """
    try:
        storage_path = Path(settings.image_storage_path if hasattr(settings, 'image_storage_path') else "./generated_images")
        image_path = storage_path / image_filename
        
        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Image not found")
        
        # セキュリティチェック
        if not str(image_path.resolve()).startswith(str(storage_path.resolve())):
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        # バックグラウンドで削除を実行
        background_tasks.add_task(image_generation_service.delete_image, str(image_path))
        
        return {"success": True, "message": f"Image {image_filename} scheduled for deletion"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete image {image_filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info/{image_filename}")
async def get_image_info(image_filename: str):
    """
    画像の情報を取得する
    """
    try:
        storage_path = Path(settings.image_storage_path if hasattr(settings, 'image_storage_path') else "./generated_images")
        image_path = storage_path / image_filename
        
        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Image not found")
        
        # セキュリティチェック
        if not str(image_path.resolve()).startswith(str(storage_path.resolve())):
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        image_info = await image_generation_service.get_image_info(str(image_path))
        
        if image_info is None:
            raise HTTPException(status_code=500, detail="Failed to get image information")
        
        return {
            "filename": image_filename,
            "path": str(image_path),
            "url": f"/images/{image_filename}",
            **image_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get image info for {image_filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))