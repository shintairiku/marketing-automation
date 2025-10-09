# test_image_generation_endpoints.py
# -*- coding: utf-8 -*-
"""
画像生成エンドポイントのテスト
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from io import BytesIO

from main import app
from app.domains.image_generation.endpoints import (
    ImageGenerationRequest,
    ImageGenerationResponse,
    GenerateImageFromPlaceholderRequest,
    ImageReplaceRequest,
    ImageRestoreRequest,
    UploadImageResponse
)
from app.common.auth import get_current_user_id_from_token

client = TestClient(app)

# テストで使うユーザーIDを定義
test_user_id = "test-user-123"
test_article_id = "test-article-123"
test_placeholder_id = "test-placeholder-123"


class TestImageGenerationEndpoints:
    """画像生成エンドポイントのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行されるセットアップ"""
        # 認証のモック設定
        app.dependency_overrides[get_current_user_id_from_token] = lambda: test_user_id

    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ"""
        # モックのクリア
        app.dependency_overrides.clear()

    def test_test_config_endpoint(self):
        """設定テストエンドポイントのテスト"""
        with patch('app.domains.image_generation.endpoints.ImageGenerationService') as mock_service_class:
            mock_service = MagicMock()
            mock_service._initialized = True
            mock_service.project_id = "test-project"
            mock_service.location = "us-central1"
            mock_service._credentials = "test-credentials"
            mock_service._client = "test-client"
            mock_service_class.return_value = mock_service

            response = client.get("/images/test-config")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["config"]["service_initialized"] is True
            assert data["config"]["project_id"] == "test-project"

    def test_test_config_endpoint_error(self):
        """設定テストエンドポイントのエラーテスト"""
        with patch('app.domains.image_generation.endpoints.ImageGenerationService') as mock_service_class:
            mock_service_class.side_effect = Exception("Test error")

            response = client.get("/images/test-config")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "Test error" in data["error"]

    @pytest.mark.asyncio
    async def test_generate_image_success(self):
        """画像生成成功のテスト"""
        with patch('app.domains.image_generation.endpoints.ImageGenerationService') as mock_service_class, \
                patch('app.domains.image_generation.endpoints.supabase') as mock_supabase:

            # モックの設定
            mock_service = AsyncMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.image_url = "http://example.com/test-image.jpg"
            mock_result.image_path = "/path/to/test-image.jpg"
            mock_result.metadata = {"test": "metadata"}
            mock_service.generate_image_detailed.return_value = mock_result
            mock_service_class.return_value = mock_service

            # データベースのモック
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "test-id"}]

            request_data = {
                "placeholder_id": test_placeholder_id,
                "description_jp": "テスト画像",
                "prompt_en": "test image",
                "alt_text": "テスト画像の説明",
                "article_id": test_article_id
            }

            response = client.post("/images/generate", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["image_url"] == "http://example.com/test-image.jpg"
            assert data["placeholder_id"] == test_placeholder_id

    @pytest.mark.asyncio
    async def test_generate_image_failure(self):
        """画像生成失敗のテスト"""
        with patch('app.domains.image_generation.endpoints.ImageGenerationService') as mock_service_class:
            # モックの設定
            mock_service = AsyncMock()
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.error_message = "Generation failed"
            mock_service.generate_image_detailed.return_value = mock_result
            mock_service_class.return_value = mock_service

            request_data = {
                "placeholder_id": test_placeholder_id,
                "description_jp": "テスト画像",
                "prompt_en": "test image",
                "alt_text": "テスト画像の説明",
                "article_id": test_article_id
            }

            response = client.post("/images/generate", json=request_data)

            assert response.status_code == 500
            data = response.json()
            assert "画像生成に失敗しました" in data["detail"]

    @pytest.mark.asyncio
    async def test_generate_and_link_image_success(self):
        """画像生成・関連付け成功のテスト"""
        with patch('app.domains.image_generation.endpoints.ImageGenerationService') as mock_service_class, \
                patch('app.domains.image_generation.endpoints.supabase') as mock_supabase:

            # モックの設定
            mock_service = AsyncMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.image_url = "http://example.com/test-image.jpg"
            mock_result.image_path = "/path/to/test-image.jpg"
            mock_result.metadata = {"test": "metadata"}
            mock_service.generate_image_detailed.return_value = mock_result
            mock_service_class.return_value = mock_service

            # データベースのモック
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "test-id"}]

            request_data = {
                "placeholder_id": test_placeholder_id,
                "description_jp": "テスト画像",
                "prompt_en": "test image",
                "alt_text": "テスト画像の説明",
                "article_id": test_article_id
            }

            response = client.post("/images/generate-and-link", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["image_url"] == "http://example.com/test-image.jpg"
            assert data["image_id"] is not None
            assert data["placeholder_id"] == test_placeholder_id

    @pytest.mark.asyncio
    async def test_generate_image_from_placeholder_success(self):
        """プレースホルダーからの画像生成成功のテスト"""
        with patch('app.domains.image_generation.endpoints.image_generation_service') as mock_service:
            # モックの設定（非同期関数なのでAsyncMockを使用）
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.image_url = "http://example.com/test-image.jpg"
            mock_result.placeholder_id = test_placeholder_id
            mock_service.generate_image_from_placeholder = AsyncMock(return_value=mock_result)

            request_data = {
                "placeholder_id": test_placeholder_id,
                "description_jp": "テスト画像",
                "prompt_en": "test image",
                "additional_context": "追加コンテキスト",
                "aspect_ratio": "16:9",
                "quality": 85
            }

            response = client.post("/images/generate-from-placeholder", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["image_url"] == "http://example.com/test-image.jpg"
            assert data["placeholder_id"] == test_placeholder_id

    @pytest.mark.asyncio
    async def test_generate_image_from_placeholder_failure(self):
        """プレースホルダーからの画像生成失敗のテスト"""
        with patch('app.domains.image_generation.endpoints.image_generation_service') as mock_service:
            # モックの設定（非同期関数なのでAsyncMockを使用）
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.error_message = "Placeholder generation failed"
            mock_service.generate_image_from_placeholder = AsyncMock(return_value=mock_result)

            request_data = {
                "placeholder_id": test_placeholder_id,
                "description_jp": "テスト画像",
                "prompt_en": "test image"
            }

            response = client.post("/images/generate-from-placeholder", json=request_data)

            assert response.status_code == 500
            data = response.json()
            assert "Placeholder generation failed" in data["detail"]

    def test_upload_image_success(self):
        """画像アップロード成功のテスト"""
        with patch('app.domains.image_generation.endpoints.gcs_service') as mock_gcs, \
                patch('app.domains.image_generation.endpoints.supabase') as mock_supabase:

            # GCSサービスのモック
            mock_gcs.is_available.return_value = True
            mock_gcs.upload_image.return_value = (True, "http://gcs.example.com/test.jpg", "test/path.jpg", None)

            # データベースのモック（各テーブル操作を個別に設定）
            # imagesテーブルのinsert
            mock_images_insert = MagicMock()
            mock_images_insert.execute.return_value.data = [{"id": "test-id"}]

            # articlesテーブルのselect
            mock_articles_select = MagicMock()
            mock_articles_select.eq.return_value.eq.return_value.execute.return_value.data = [
                {"content": f"Some text here. More text."}
            ]

            # articlesテーブルのupdate
            mock_articles_update = MagicMock()
            mock_articles_update.eq.return_value.execute.return_value.data = [{"id": "test-id"}]

            # image_placeholdersテーブルのupdate
            mock_placeholders_update = MagicMock()
            mock_placeholders_update.eq.return_value.eq.return_value.execute.return_value.data = [{"id": "test-id"}]

            # supabase.tableのモック設定
            def mock_table(table_name):
                if table_name == "images":
                    mock_table_instance = MagicMock()
                    mock_table_instance.insert.return_value = mock_images_insert
                    return mock_table_instance
                elif table_name == "articles":
                    mock_table_instance = MagicMock()
                    mock_table_instance.select.return_value = mock_articles_select
                    mock_table_instance.update.return_value = mock_articles_update
                    return mock_table_instance
                elif table_name == "image_placeholders":
                    mock_table_instance = MagicMock()
                    mock_table_instance.update.return_value = mock_placeholders_update
                    return mock_table_instance

            mock_supabase.table = mock_table

            # テスト用の画像ファイル
            test_image = BytesIO(b"fake image data")
            test_image.name = "test.jpg"

            files = {"file": ("test.jpg", test_image, "image/jpeg")}
            data = {
                "article_id": test_article_id,
                "placeholder_id": test_placeholder_id,
                "alt_text": "テスト画像"
            }

            response = client.post("/images/upload", files=files, data=data)

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["success"] is True
            assert "image_id" in response_data
            assert response_data["image_url"] == "http://gcs.example.com/test.jpg"

    def test_upload_image_gcs_unavailable(self):
        """GCSサービスが利用できない場合のテスト"""
        with patch('app.domains.image_generation.endpoints.gcs_service') as mock_gcs:
            mock_gcs.is_available.return_value = False

            test_image = BytesIO(b"fake image data")
            test_image.name = "test.jpg"

            files = {"file": ("test.jpg", test_image, "image/jpeg")}
            data = {
                "article_id": test_article_id,
                "placeholder_id": test_placeholder_id,
                "alt_text": "テスト画像"
            }

            response = client.post("/images/upload", files=files, data=data)

            assert response.status_code == 500
            data = response.json()
            assert "GCSサービスが利用できません" in data["detail"]

    def test_replace_placeholder_success(self):
        """プレースホルダー置き換え成功のテスト"""
        with patch('app.domains.image_generation.endpoints.supabase') as mock_supabase:
            # データベースのモック（各テーブル操作を個別に設定）
            # articlesテーブルのselect
            mock_articles_select = MagicMock()
            mock_articles_select.eq.return_value.eq.return_value.execute.return_value.data = [
                {"id": test_article_id, "content": "test content"}
            ]

            # imagesテーブルのinsert
            mock_images_insert = MagicMock()
            mock_images_insert.execute.return_value.data = [{"id": "test-id"}]

            # articlesテーブルのupdate
            mock_articles_update = MagicMock()
            mock_articles_update.eq.return_value.execute.return_value.data = [{"id": "test-id"}]

            # image_placeholdersテーブルのupdate
            mock_placeholders_update = MagicMock()
            mock_placeholders_update.eq.return_value.eq.return_value.execute.return_value.data = [{"id": "test-id"}]

            # supabase.tableのモック設定
            def mock_table(table_name):
                if table_name == "articles":
                    mock_table_instance = MagicMock()
                    mock_table_instance.select.return_value = mock_articles_select
                    mock_table_instance.update.return_value = mock_articles_update
                    return mock_table_instance
                elif table_name == "images":
                    mock_table_instance = MagicMock()
                    mock_table_instance.insert.return_value = mock_images_insert
                    return mock_table_instance
                elif table_name == "image_placeholders":
                    mock_table_instance = MagicMock()
                    mock_table_instance.update.return_value = mock_placeholders_update
                    return mock_table_instance

            mock_supabase.table = mock_table

            request_data = {
                "article_id": test_article_id,
                "placeholder_id": test_placeholder_id,
                "image_url": "http://example.com/test-image.jpg",
                "alt_text": "テスト画像"
            }

            response = client.post("/images/replace-placeholder", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "image_id" in data

    def test_replace_placeholder_article_not_found(self):
        """記事が見つからない場合のテスト"""
        with patch('app.domains.image_generation.endpoints.supabase') as mock_supabase:
            # データベースのモック（記事が見つからない）
            mock_articles_select = MagicMock()
            mock_articles_select.eq.return_value.eq.return_value.execute.return_value.data = []

            def mock_table(table_name):
                if table_name == "articles":
                    mock_table_instance = MagicMock()
                    mock_table_instance.select.return_value = mock_articles_select
                    return mock_table_instance

            mock_supabase.table = mock_table

            request_data = {
                "article_id": test_article_id,
                "placeholder_id": test_placeholder_id,
                "image_url": "http://example.com/test-image.jpg",
                "alt_text": "テスト画像"
            }

            response = client.post("/images/replace-placeholder", json=request_data)

            assert response.status_code == 404
            data = response.json()
            assert "記事が見つからないか、アクセス権限がありません" in data["detail"]

    def test_restore_placeholder_success(self):
        """プレースホルダー復元成功のテスト"""
        with patch('app.domains.image_generation.endpoints.supabase') as mock_supabase:
            # データベースのモック（各テーブル操作を個別に設定）
            # articlesテーブルのselect
            mock_articles_select = MagicMock()
            mock_articles_select.eq.return_value.eq.return_value.execute.return_value.data = [
                {"id": test_article_id, "content": "test content"}
            ]

            # articlesテーブルのupdate
            mock_articles_update = MagicMock()
            mock_articles_update.eq.return_value.execute.return_value.data = [{"id": "test-id"}]

            # image_placeholdersテーブルのupdate
            mock_placeholders_update = MagicMock()
            mock_placeholders_update.eq.return_value.eq.return_value.execute.return_value.data = [{"id": "test-id"}]

            # supabase.tableのモック設定
            def mock_table(table_name):
                if table_name == "articles":
                    mock_table_instance = MagicMock()
                    mock_table_instance.select.return_value = mock_articles_select
                    mock_table_instance.update.return_value = mock_articles_update
                    return mock_table_instance
                elif table_name == "image_placeholders":
                    mock_table_instance = MagicMock()
                    mock_table_instance.update.return_value = mock_placeholders_update
                    return mock_table_instance

            mock_supabase.table = mock_table

            request_data = {
                "article_id": test_article_id,
                "placeholder_id": test_placeholder_id
            }

            response = client.post("/images/restore-placeholder", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "placeholder_comment" in data

    def test_get_article_images_success(self):
        """記事画像取得成功のテスト"""
        with patch('app.domains.image_generation.endpoints.supabase') as mock_supabase:
            # データベースのモック（各テーブル操作を個別に設定）
            # articlesテーブルのselect
            mock_articles_select = MagicMock()
            mock_articles_select.eq.return_value.eq.return_value.execute.return_value.data = [
                {"id": test_article_id, "content": "test content"}
            ]

            # image_placeholdersテーブルのselect
            mock_placeholders_select = MagicMock()
            mock_placeholders_select.eq.return_value.execute.return_value.data = [
                {"placeholder_id": test_placeholder_id, "description_jp": "テスト", "prompt_en": "test", "status": "pending"}
            ]

            # imagesテーブルのselect
            mock_images_select = MagicMock()
            mock_images_select.eq.return_value.eq.return_value.execute.return_value.data = []

            # supabase.tableのモック設定
            def mock_table(table_name):
                if table_name == "articles":
                    mock_table_instance = MagicMock()
                    mock_table_instance.select.return_value = mock_articles_select
                    return mock_table_instance
                elif table_name == "image_placeholders":
                    mock_table_instance = MagicMock()
                    mock_table_instance.select.return_value = mock_placeholders_select
                    return mock_table_instance
                elif table_name == "images":
                    mock_table_instance = MagicMock()
                    mock_table_instance.select.return_value = mock_images_select
                    return mock_table_instance

            mock_supabase.table = mock_table

            response = client.get(f"/images/article-images/{test_article_id}")

            assert response.status_code == 200
            data = response.json()
            assert "placeholders" in data
            assert "all_images" in data
            assert "restored_content" in data

    def test_get_placeholder_history_success(self):
        """プレースホルダー履歴取得成功のテスト"""
        with patch('app.domains.image_generation.endpoints.supabase') as mock_supabase:
            # データベースのモック（各テーブル操作を個別に設定）
            # articlesテーブルのselect
            mock_articles_select = MagicMock()
            mock_articles_select.eq.return_value.eq.return_value.execute.return_value.data = [
                {"id": test_article_id}
            ]

            # imagesテーブルのselect
            mock_images_select = MagicMock()
            mock_images_select.eq.return_value.eq.return_value.execute.return_value.data = [
                {
                    "id": "image-1",
                    "metadata": {"placeholder_id": test_placeholder_id},
                    "created_at": "2024-01-01T00:00:00Z"
                }
            ]

            # supabase.tableのモック設定
            def mock_table(table_name):
                if table_name == "articles":
                    mock_table_instance = MagicMock()
                    mock_table_instance.select.return_value = mock_articles_select
                    return mock_table_instance
                elif table_name == "images":
                    mock_table_instance = MagicMock()
                    mock_table_instance.select.return_value = mock_images_select
                    return mock_table_instance

            mock_supabase.table = mock_table

            response = client.get(f"/images/placeholder-history/{test_article_id}/{test_placeholder_id}")

            assert response.status_code == 200
            data = response.json()
            assert "images_history" in data

    def test_serve_image_success(self):
        """画像配信成功のテスト"""
        with patch('app.domains.image_generation.endpoints.FileResponse') as mock_file_response:
            # Pathオブジェクトとsettingsをモック化
            with patch('app.domains.image_generation.endpoints.Path') as mock_path, \
                 patch('app.domains.image_generation.endpoints.settings') as mock_settings:
                
                # パスが存在することをシミュレート
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path_instance.resolve.return_value = "/test/storage/test-image.jpg"
                mock_path_instance.__str__.return_value = "/test/storage/test-image.jpg"
                mock_path_instance.is_absolute.return_value = False

                # パスのコンストラクタのモック
                def mock_path_constructor(path):
                    if str(path).endswith("test-image.jpg"):
                        return mock_path_instance
                    # `settings.image_storage_path`のPathオブジェクトをモック
                    elif str(path) == "./generated_images":
                        mock_storage = MagicMock()
                        mock_storage.resolve.return_value = "/test/storage"
                        mock_storage.is_absolute.return_value = False
                        return mock_storage
                    else:
                        return MagicMock()

                mock_path.side_effect = mock_path_constructor
                mock_settings.image_storage_path = "./generated_images"
                mock_file_response.return_value = "file response"

                response = client.get("/images/serve/test-image.jpg")
                assert response.status_code == 200

    def test_serve_image_not_found(self):
        """画像が見つからない場合のテスト"""
        with patch('app.domains.image_generation.endpoints.Path') as mock_path, \
             patch('app.domains.image_generation.endpoints.settings') as mock_settings:

            # パスのモック（ファイルが存在しない）
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path_instance.resolve.return_value = "/test/storage/nonexistent.jpg"
            mock_path_instance.is_absolute.return_value = False

            def mock_path_constructor(path):
                if str(path).endswith("nonexistent.jpg"):
                    return mock_path_instance
                elif str(path) == "./generated_images":
                    mock_storage = MagicMock()
                    mock_storage.resolve.return_value = "/test/storage"
                    mock_storage.is_absolute.return_value = False
                    return mock_storage
                else:
                    return MagicMock()

            mock_path.side_effect = mock_path_constructor
            mock_settings.image_storage_path = "./generated_images"

            response = client.get("/images/serve/nonexistent.jpg")

            assert response.status_code == 404
            data = response.json()
            assert "Image not found" in data["detail"]

    def test_serve_image_invalid_path(self):
        """無効なパスの場合のテスト (400)"""
        with patch('app.domains.image_generation.endpoints.Path') as mock_path_class, \
             patch('app.domains.image_generation.endpoints.settings') as mock_settings:
            
            # settingsのモック設定
            mock_settings.image_storage_path = "./generated_images"
            
            # `Path('..')`などの呼び出しをモック
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.resolve.return_value = "/etc/passwd"
            mock_path_instance.is_absolute.return_value = True

            # Pathのコンストラクタのモック
            def mock_path_constructor(path):
                # 危険なパスの場合
                if ".." in str(path) or str(path).startswith("/") or str(path).startswith("\\"):
                    return mock_path_instance
                # 通常のストレージパスの場合
                elif str(path) == "./generated_images":
                    mock_storage = MagicMock()
                    mock_storage.resolve.return_value = "/test/storage"
                    mock_storage.is_absolute.return_value = False
                    return mock_storage
                else:
                    return MagicMock()

            mock_path_class.side_effect = mock_path_constructor
            
            # `..`が含まれるパスをリクエスト
            response = client.get("/images/serve/..%2F..%2F..%2Fetc%2Fpasswd")
            
            assert response.status_code == 400
            data = response.json()
            assert "Invalid file path" in data["detail"]


class TestImageGenerationModels:
    """画像生成モデルのテストクラス"""

    def test_image_generation_request_validation(self):
        """ImageGenerationRequestのバリデーションテスト"""
        # 正常なケース
        request = ImageGenerationRequest(
            placeholder_id=test_placeholder_id,
            description_jp="テスト画像",
            prompt_en="test image",
            alt_text="テスト画像の説明",
            article_id=test_article_id
        )
        assert request.placeholder_id == test_placeholder_id
        assert request.description_jp == "テスト画像"
        assert request.prompt_en == "test image"
        assert request.alt_text == "テスト画像の説明"
        assert request.article_id == test_article_id

    def test_generate_image_from_placeholder_request_validation(self):
        """GenerateImageFromPlaceholderRequestのバリデーションテスト"""
        request = GenerateImageFromPlaceholderRequest(
            placeholder_id=test_placeholder_id,
            description_jp="テスト画像",
            prompt_en="test image",
            additional_context="追加コンテキスト",
            aspect_ratio="16:9",
            quality=85
        )
        assert request.placeholder_id == test_placeholder_id
        assert request.description_jp == "テスト画像"
        assert request.prompt_en == "test image"
        assert request.additional_context == "追加コンテキスト"
        assert request.aspect_ratio == "16:9"
        assert request.quality == 85

    def test_image_replace_request_validation(self):
        """ImageReplaceRequestのバリデーションテスト"""
        request = ImageReplaceRequest(
            article_id=test_article_id,
            placeholder_id=test_placeholder_id,
            image_url="http://example.com/test-image.jpg",
            alt_text="テスト画像"
        )
        assert request.article_id == test_article_id
        assert request.placeholder_id == test_placeholder_id
        assert request.image_url == "http://example.com/test-image.jpg"
        assert request.alt_text == "テスト画像"

    def test_image_restore_request_validation(self):
        """ImageRestoreRequestのバリデーションテスト"""
        request = ImageRestoreRequest(
            article_id=test_article_id,
            placeholder_id=test_placeholder_id
        )
        assert request.article_id == test_article_id
        assert request.placeholder_id == test_placeholder_id

    def test_upload_image_response_validation(self):
        """UploadImageResponseのバリデーションテスト"""
        response = UploadImageResponse(
            success=True,
            image_url="http://example.com/test-image.jpg",
            image_path="/path/to/test-image.jpg",
            error_message=None,
            metadata={"test": "metadata"}
        )
        assert response.success is True
        assert response.image_url == "http://example.com/test-image.jpg"
        assert response.image_path == "/path/to/test-image.jpg"
        assert response.error_message is None
        assert response.metadata == {"test": "metadata"}


if __name__ == "__main__":
    pytest.main([__file__])