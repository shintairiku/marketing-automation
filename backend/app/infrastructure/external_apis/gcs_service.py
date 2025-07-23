# -*- coding: utf-8 -*-
"""
Google Cloud Storage (GCS) サービス
画像ファイルのクラウドストレージ管理を行う
"""

import io
import json
import uuid
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import mimetypes

from google.api_core import exceptions as gcs_exceptions

from app.core.config import settings
from app.core.logger import logger
from app.infrastructure.gcp_auth import get_storage_client


class GCSService:
    """Google Cloud Storage サービスクラス"""
    
    def __init__(self):
        self.bucket_name = settings.gcs_bucket_name if hasattr(settings, 'gcs_bucket_name') else None
        self.public_url_base = settings.gcs_public_url_base if hasattr(settings, 'gcs_public_url_base') else None
        
        self._client = None
        self._bucket = None
        self._initialized = False
        self._initialize_client()
    
    def _initialize_client(self):
        """GCSクライアントを初期化"""
        if not self.bucket_name:
            logger.warning("GCS bucket name not configured")
            return
        
        try:
            # 統一認証システムを使用してGCSクライアントを取得
            self._client = get_storage_client()
            
            # バケットを取得
            self._bucket = self._client.bucket(self.bucket_name)
            
            self._initialized = True
            logger.info(f"GCS service initialized for bucket: {self.bucket_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}")
            self._initialized = False
    
    def is_available(self) -> bool:
        """GCSサービスが利用可能かチェック"""
        return self._initialized and self._bucket is not None
    
    def upload_image(
        self, 
        image_data: bytes, 
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        画像をGCSにアップロード
        
        Args:
            image_data: 画像のバイナリデータ
            filename: ファイル名（指定しない場合はUUIDで生成）
            content_type: MIMEタイプ（指定しない場合は自動推定）
            metadata: 追加のメタデータ
            
        Returns:
            (成功フラグ, GCS_URL, GCSパス, エラーメッセージ)
        """
        if not self.is_available():
            return False, None, None, "GCS service not available"
        
        try:
            # ファイル名の生成
            if not filename:
                file_extension = self._guess_extension_from_data(image_data, content_type)
                filename = f"generated_{uuid.uuid4().hex}{file_extension}"
            
            # パスの構築（日付ベースの階層構造）
            from datetime import datetime
            date_str = datetime.now().strftime("%Y/%m/%d")
            gcs_path = f"images/{date_str}/{filename}"
            
            # コンテンツタイプの推定
            if not content_type:
                content_type = self._guess_content_type(filename)
            
            # GCSにアップロード
            blob = self._bucket.blob(gcs_path)
            
            # メタデータの設定
            if metadata:
                blob.metadata = metadata
            
            # ファイルをアップロード
            blob.upload_from_string(
                image_data,
                content_type=content_type
            )
            
            # 公開URLを生成
            if self.public_url_base:
                gcs_url = f"{self.public_url_base}/{gcs_path}"
            else:
                gcs_url = f"https://storage.googleapis.com/{self.bucket_name}/{gcs_path}"
            
            logger.info(f"Image uploaded to GCS: {gcs_path}")
            return True, gcs_url, gcs_path, None
            
        except gcs_exceptions.GoogleCloudError as e:
            logger.error(f"GCS upload failed: {e}")
            return False, None, None, f"GCS upload error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error during GCS upload: {e}")
            return False, None, None, f"Upload error: {str(e)}"
    
    def delete_image(self, gcs_path: str) -> Tuple[bool, Optional[str]]:
        """
        GCSから画像を削除
        
        Args:
            gcs_path: GCS内のパス
            
        Returns:
            (成功フラグ, エラーメッセージ)
        """
        if not self.is_available():
            return False, "GCS service not available"
        
        try:
            blob = self._bucket.blob(gcs_path)
            blob.delete()
            logger.info(f"Image deleted from GCS: {gcs_path}")
            return True, None
            
        except gcs_exceptions.NotFound:
            logger.warning(f"Image not found in GCS: {gcs_path}")
            return False, "Image not found"
        except gcs_exceptions.GoogleCloudError as e:
            logger.error(f"GCS delete failed: {e}")
            return False, f"GCS delete error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error during GCS delete: {e}")
            return False, f"Delete error: {str(e)}"
    
    def image_exists(self, gcs_path: str) -> bool:
        """
        GCSに画像が存在するかチェック
        
        Args:
            gcs_path: GCS内のパス
            
        Returns:
            存在フラグ
        """
        if not self.is_available():
            return False
        
        try:
            blob = self._bucket.blob(gcs_path)
            return blob.exists()
        except Exception as e:
            logger.error(f"Error checking image existence: {e}")
            return False
    
    def get_image_info(self, gcs_path: str) -> Optional[Dict[str, Any]]:
        """
        GCS画像の情報を取得
        
        Args:
            gcs_path: GCS内のパス
            
        Returns:
            画像情報の辞書
        """
        if not self.is_available():
            return None
        
        try:
            blob = self._bucket.blob(gcs_path)
            blob.reload()
            
            return {
                "name": blob.name,
                "size": blob.size,
                "content_type": blob.content_type,
                "created": blob.time_created,
                "updated": blob.updated,
                "metadata": blob.metadata or {},
                "public_url": blob.public_url
            }
        except Exception as e:
            logger.error(f"Error getting image info: {e}")
            return None
    
    def _guess_content_type(self, filename: str) -> str:
        """ファイル名からコンテンツタイプを推定"""
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or 'application/octet-stream'
    
    def _guess_extension_from_data(self, data: bytes, content_type: Optional[str] = None) -> str:
        """画像データまたはコンテンツタイプから拡張子を推定"""
        if content_type:
            extension_map = {
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'image/gif': '.gif',
                'image/webp': '.webp',
                'image/bmp': '.bmp',
                'image/tiff': '.tiff'
            }
            return extension_map.get(content_type, '.jpg')
        
        # バイナリデータのマジックナンバーから判定
        if data.startswith(b'\xff\xd8\xff'):
            return '.jpg'
        elif data.startswith(b'\x89PNG\r\n\x1a\n'):
            return '.png'
        elif data.startswith(b'GIF87a') or data.startswith(b'GIF89a'):
            return '.gif'
        elif data.startswith(b'RIFF') and b'WEBP' in data[:12]:
            return '.webp'
        else:
            return '.jpg'  # デフォルト
    
    def get_bucket_info(self) -> Optional[Dict[str, Any]]:
        """バケット情報を取得（デバッグ用）"""
        if not self.is_available():
            return None
        
        try:
            self._bucket.reload()
            return {
                "name": self._bucket.name,
                "location": self._bucket.location,
                "storage_class": self._bucket.storage_class,
                "created": self._bucket.time_created,
                "project": self._bucket.project,
            }
        except Exception as e:
            logger.error(f"Error getting bucket info: {e}")
            return None


# シングルトンインスタンス
gcs_service = GCSService()