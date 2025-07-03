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
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False

from core.config import settings
from core.logger import logger
from services.gcs_service import gcs_service
from utils.gcp_auth import get_aiplatform_credentials, initialize_aiplatform


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
        # 環境変数からモデル設定を取得
        self.model_name = model_name or settings.imagen_model_name
        self.aspect_ratio = settings.imagen_aspect_ratio
        self.output_format = settings.imagen_output_format
        self.quality = settings.imagen_quality
        self.safety_filter = settings.imagen_safety_filter
        self.person_generation = settings.imagen_person_generation
        self.add_japan_prefix = settings.imagen_add_japan_prefix
        
        # Google Cloud設定
        self.location = settings.google_cloud_location
        self.storage_path = Path(settings.image_storage_path)
        
        # ストレージディレクトリを作成
        self.storage_path.mkdir(exist_ok=True)
        
        # Vertex AI の初期化
        self._initialized = False
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
        try:
            # 統一認証システムを使用してVertex AIを初期化
            from utils.gcp_auth import get_auth_manager
            auth_manager = get_auth_manager()
            logger.info(f"Initializing Vertex AI with project: {auth_manager.project_id}, location: {self.location}")
            
            initialize_aiplatform(location=self.location)
            self._initialized = True
            logger.info(f"Vertex AI initialized successfully for location: {self.location}")
            
        except Exception as e:
            import traceback
            logger.error(f"Failed to initialize Vertex AI: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            self._initialized = False
    
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
            
            # Japanプレフィックスの処理
            if self.add_japan_prefix:
                japan_prompt = f"In Japan. {request.prompt}"
                logger.info(f"Modified prompt with Japan prefix: {japan_prompt}")
            else:
                japan_prompt = request.prompt
                logger.info(f"Using original prompt: {japan_prompt}")
            
            # Imagen 4.0モデルを取得
            model = ImageGenerationModel.from_pretrained(self.model_name)
            
            # 生成パラメータの準備（環境変数から設定を取得）
            generation_params = {
                "prompt": japan_prompt,
                "number_of_images": 1,
                "aspect_ratio": request.aspect_ratio or self.aspect_ratio,
                "safety_filter_level": self.safety_filter,
                "person_generation": self.person_generation,
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
            output_format = request.output_format or self.output_format
            image_filename = f"generated_{uuid.uuid4().hex}.{output_format.lower()}"
            image_path = self.storage_path / image_filename
            
            # 画像品質の調整（JPEGの場合）
            quality = request.quality if request.quality is not None else self.quality
            if output_format.upper() == "JPEG" and quality:
                # PILを使用して品質を調整
                pil_image = Image.open(io.BytesIO(image_data))
                
                # 品質調整して保存
                with open(image_path, "wb") as f:
                    pil_image.save(f, "JPEG", quality=quality)
                
                # 調整後の画像データを読み込み
                with open(image_path, "rb") as f:
                    image_data = f.read()
            else:
                # 元の画像データを保存
                with open(image_path, "wb") as f:
                    f.write(image_data)
            
            # GCSアップロードを試行
            gcs_url = None
            gcs_path = None
            storage_type = "local"
            
            if gcs_service.is_available():
                try:
                    # GCSメタデータの準備
                    gcs_metadata = {
                        "model": self.model_name,
                        "prompt": japan_prompt[:500],  # プロンプトを短縮
                        "aspect_ratio": generation_params["aspect_ratio"],
                        "format": output_format,
                        "user_generated": "true"
                    }
                    
                    # GCSにアップロード
                    success, uploaded_gcs_url, uploaded_gcs_path, error = gcs_service.upload_image(
                        image_data=image_data,
                        filename=image_filename,
                        content_type=f"image/{output_format.lower()}",
                        metadata=gcs_metadata
                    )
                    
                    if success:
                        gcs_url = uploaded_gcs_url
                        gcs_path = uploaded_gcs_path
                        storage_type = "hybrid"  # ローカル + GCS
                        logger.info(f"Image uploaded to GCS: {gcs_url}")
                    else:
                        logger.warning(f"GCS upload failed: {error}")
                        
                except Exception as e:
                    logger.error(f"Unexpected error during GCS upload: {e}")
            else:
                logger.info("GCS service not available, using local storage only")
            
            # 優先URL（GCS URL > ローカルURL）
            primary_url = gcs_url if gcs_url else f"http://localhost:8008/images/{image_filename}"
            
            # メタデータの構築
            metadata = {
                "model": self.model_name,
                "prompt": japan_prompt,
                "aspect_ratio": generation_params["aspect_ratio"],
                "safety_filter_level": generation_params["safety_filter_level"],
                "person_generation": generation_params["person_generation"],
                "format": output_format,
                "quality": quality,
                "file_size": len(image_data),
                "sdk": "vertex_ai",
                "storage_type": storage_type,
                "local_path": str(image_path),
                "local_url": f"http://localhost:8008/images/{image_filename}"
            }
            
            # GCS情報を追加
            if gcs_url:
                metadata.update({
                    "gcs_url": gcs_url,
                    "gcs_path": gcs_path
                })
            
            return ImageGenerationResponse(
                success=True,
                image_path=str(image_path),
                image_url=primary_url,  # GCS URL優先
                image_data=image_data,
                metadata=metadata
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
            # Japanプレフィックスの処理
            if self.add_japan_prefix:
                final_prompt = f"In Japan. {prompt}"
            else:
                final_prompt = prompt
            
            request = ImageGenerationRequest(
                prompt=final_prompt,
                aspect_ratio=self.aspect_ratio,
                output_format=self.output_format,
                quality=self.quality
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
        
        # Japanプレフィックスの処理
        if self.add_japan_prefix:
            final_prompt = f"In Japan. {prompt_en}"
        else:
            final_prompt = prompt_en
        
        request = ImageGenerationRequest(
            prompt=final_prompt,
            aspect_ratio=self.aspect_ratio,
            output_format=self.output_format,
            quality=self.quality
        )
        
        result = await self.generate_image_detailed(request)
        
        if result.success:
            # メタデータにプレースホルダー情報を追加
            result.metadata.update({
                "placeholder_id": placeholder_id,
                "description_jp": description_jp,
                "original_prompt_en": prompt_en,
                "final_prompt": final_prompt
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


# シングルトンインスタンス（環境変数からモデル名を取得）
image_generation_service = ImageGenerationService()