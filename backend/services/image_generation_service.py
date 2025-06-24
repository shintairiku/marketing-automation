# -*- coding: utf-8 -*-
"""
Vertex AI Imagen 4.0を使用した画像生成サービス
"""

import asyncio
import base64
import io
import json
import os
import uuid
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from pydantic import BaseModel, Field
from PIL import Image
import aiofiles
import aiohttp

# Google GenAI SDK関連のインポート
try:
    from google import genai
    from google.genai import types
    GENAI_SDK_AVAILABLE = True
except ImportError:
    GENAI_SDK_AVAILABLE = False

# Fallback: 古いVertex AI SDK
try:
    import vertexai
    from vertexai.preview.vision_models import ImageGenerationModel
    from google.cloud import aiplatform
    from google.auth import default
    from google.oauth2 import service_account
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False

from core.config import settings
from core.logger import logger


class ImageGenerationRequest(BaseModel):
    """画像生成リクエスト"""
    prompt: str = Field(description="画像生成用のプロンプト（英語推奨）")
    negative_prompt: Optional[str] = Field(default=None, description="ネガティブプロンプト")
    aspect_ratio: Optional[str] = Field(default="1:1", description="アスペクト比 (1:1, 3:4, 4:3, 9:16, 16:9)")
    output_format: Optional[str] = Field(default="JPEG", description="出力フォーマット")
    quality: Optional[int] = Field(default=75, description="JPEG品質 (0-100)")
    guidance_scale: Optional[float] = Field(default=None, description="ガイダンススケール")
    seed: Optional[int] = Field(default=None, description="シード値")


class ImageGenerationResponse(BaseModel):
    """画像生成レスポンス"""
    success: bool = Field(description="生成成功フラグ")
    image_url: Optional[str] = Field(default=None, description="生成された画像のURL")
    image_path: Optional[str] = Field(default=None, description="生成された画像のローカルパス")
    image_data: Optional[bytes] = Field(default=None, description="画像データ（バイナリ）")
    error_message: Optional[str] = Field(default=None, description="エラーメッセージ")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="生成メタデータ")


class ImageGenerationService:
    """Vertex AI Imagen 4.0を使用した画像生成サービス"""
    
    def __init__(self, model_name: Optional[str] = None):
        # Imagen 4.0 のみ使用
        self.model_name = model_name or "imagen-4.0-generate-preview-06-06"
        self.project_id = settings.google_cloud_project if hasattr(settings, 'google_cloud_project') else None
        self.location = settings.google_cloud_location if hasattr(settings, 'google_cloud_location') else "us-central1"
        self.service_account_json = settings.google_service_account_json if hasattr(settings, 'google_service_account_json') else None
        self.storage_path = Path(settings.image_storage_path if hasattr(settings, 'image_storage_path') else "./generated_images")
        
        # ストレージディレクトリを作成
        self.storage_path.mkdir(exist_ok=True)
        
        # Vertex AI の初期化
        self._initialized = False
        self._credentials = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Vertex AI の初期化"""
        if not VERTEX_AI_AVAILABLE:
            logger.error("Vertex AI SDK not available")
            return
            
        try:
            self._initialize_vertex_ai()
        except Exception as e:
            logger.error(f"Vertex AI initialization failed: {e}")
    
    def _initialize_vertex_ai(self):
        """Vertex AI の初期化"""
        if not self.project_id:
            logger.warning("Google Cloud project ID not configured.")
            return
                
        if not self.service_account_json:
            logger.warning("Google service account JSON not configured.")
            return
        
        try:
            # サービスアカウントJSONをパース
            service_account_info = json.loads(self.service_account_json)
            
            # 認証情報を作成
            self._credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            
            # Vertex AIを初期化
            vertexai.init(
                project=self.project_id, 
                location=self.location,
                credentials=self._credentials
            )
            self._initialized = True
            logger.info(f"Vertex AI initialized for project: {self.project_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
    
    async def generate_image(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """画像を生成する"""
        if not self._initialized:
            return ImageGenerationResponse(
                success=False,
                error_message="Vertex AI not initialized or not available"
            )
        
        try:
            # 非同期でモデルを使用するため、同期処理をthread poolで実行
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._generate_sync, request)
            return result
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return ImageGenerationResponse(
                success=False,
                error_message=str(e)
            )
    
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
    
    def _generate_with_vertex_ai(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """Vertex AI SDKを使用した画像生成"""
        try:
            logger.info(f"Generating image with Vertex AI SDK using model: {self.model_name}")
            
            # "In Japan." プレフィックスを追加
            japan_prompt = f"In Japan. {request.prompt}"
            logger.info(f"Modified prompt with Japan prefix: {japan_prompt}")
            
            # Imagen 4.0モデルを取得
            model = ImageGenerationModel.from_pretrained(self.model_name)
            
            # 生成パラメータの準備（テストスクリプトと同じ設定）
            generation_params = {
                "prompt": japan_prompt,
                "number_of_images": 1,
                "aspect_ratio": "4:3",  # 必須設定
                "safety_filter_level": "block_only_high",  # 必須設定
                "person_generation": "allow_all",  # 必須設定
            }
            
            # ネガティブプロンプトの設定
            if request.negative_prompt:
                generation_params["negative_prompt"] = request.negative_prompt
            
            # その他のパラメータ
            if request.guidance_scale is not None:
                generation_params["guidance_scale"] = request.guidance_scale
            
            if request.seed is not None:
                generation_params["seed"] = request.seed
            
            logger.info(f"Generation parameters: {generation_params}")
            
            # 画像生成を実行
            response = model.generate_images(**generation_params)
            
            if not response.images or len(response.images) == 0:
                return ImageGenerationResponse(
                    success=False,
                    error_message="No images generated by Vertex AI"
                )
            
            # 最初の画像を取得
            generated_image = response.images[0]
            
            # 画像データの取得
            image_data = generated_image._image_bytes
            
            # 画像を保存
            image_filename = f"generated_{uuid.uuid4().hex}.{request.output_format.lower()}"
            image_path = self.storage_path / image_filename
            
            # 画像品質の調整（JPEGの場合）
            if request.output_format.upper() == "JPEG" and request.quality:
                # PILを使用して品質を調整
                pil_image = Image.open(io.BytesIO(image_data))
                
                # 品質調整して保存
                with open(image_path, "wb") as f:
                    pil_image.save(f, "JPEG", quality=request.quality)
                
                # 調整後の画像データを読み込み
                with open(image_path, "rb") as f:
                    image_data = f.read()
            else:
                # 元の画像データを保存
                with open(image_path, "wb") as f:
                    f.write(image_data)
            
            return ImageGenerationResponse(
                success=True,
                image_path=str(image_path),
                image_url=f"http://localhost:8008/images/{image_filename}",
                image_data=image_data,
                metadata={
                    "model": self.model_name,
                    "prompt": japan_prompt,
                    "aspect_ratio": "4:3",
                    "safety_filter_level": "block_only_high",
                    "person_generation": "allow_all",
                    "format": request.output_format,
                    "quality": request.quality,
                    "file_size": len(image_data),
                    "sdk": "vertex_ai"
                }
            )
            
        except Exception as e:
            logger.error(f"Vertex AI image generation failed: {e}")
            return ImageGenerationResponse(
                success=False,
                error_message=f"Vertex AI error: {str(e)}"
            )
    
    async def generate_image(
        self, 
        prompt: str,
        placeholder_id: str,
        user_id: Optional[str] = None
    ) -> str:
        """簡素化された画像生成メソッド（URLを返す）"""
        
        if not self._initialized:
            raise Exception("Vertex AI not initialized or not available")
        
        try:
            # "In Japan." プレフィックスを追加
            japan_prompt = f"In Japan. {prompt}"
            
            request = ImageGenerationRequest(
                prompt=japan_prompt,
                aspect_ratio="4:3",  # 必須設定
                output_format="JPEG",
                quality=85
            )
            
            # 非同期でモデルを使用するため、同期処理をthread poolで実行
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._generate_sync, request)
            
            if not result.success:
                raise Exception(result.error_message or "画像生成に失敗しました")
            
            return result.image_url
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise Exception(f"画像生成に失敗しました: {str(e)}")
    
    async def generate_image_from_placeholder(
        self, 
        placeholder_id: str,
        description_jp: str,
        prompt_en: str,
        additional_context: Optional[str] = None
    ) -> ImageGenerationResponse:
        """画像プレースホルダーから画像を生成する"""
        
        # "In Japan." プレフィックスを追加
        japan_prompt = f"In Japan. {prompt_en}"
        
        request = ImageGenerationRequest(
            prompt=japan_prompt,
            aspect_ratio="4:3",  # 必須設定
            output_format="JPEG",
            quality=85
        )
        
        result = await self.generate_image_detailed(request)
        
        if result.success:
            # メタデータにプレースホルダー情報を追加
            result.metadata.update({
                "placeholder_id": placeholder_id,
                "description_jp": description_jp,
                "original_prompt_en": prompt_en,
                "japan_prompt": japan_prompt
            })
        
        return result
    
    async def generate_image_detailed(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """詳細なレスポンスを返す画像生成メソッド"""
        if not self._initialized:
            return ImageGenerationResponse(
                success=False,
                error_message="Vertex AI not initialized or not available"
            )
        
        try:
            # 非同期でモデルを使用するため、同期処理をthread poolで実行
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._generate_sync, request)
            return result
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return ImageGenerationResponse(
                success=False,
                error_message=str(e)
            )
    
    
    async def delete_image(self, image_path: str) -> bool:
        """生成された画像を削除する"""
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
                logger.info(f"Deleted image: {image_path}")
                return True
            else:
                logger.warning(f"Image not found for deletion: {image_path}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete image {image_path}: {e}")
            return False
    
    async def get_image_info(self, image_path: str) -> Optional[Dict[str, Any]]:
        """画像情報を取得する"""
        try:
            if not os.path.exists(image_path):
                return None
            
            # PILで画像情報を取得
            with Image.open(image_path) as img:
                return {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                    "file_size": os.path.getsize(image_path)
                }
        except Exception as e:
            logger.error(f"Failed to get image info for {image_path}: {e}")
            return None


# シングルトンインスタンス（Imagen-4.0を使用）
image_generation_service = ImageGenerationService("imagen-4.0-generate-preview-06-06")