# -*- coding: utf-8 -*-
"""
test_image_generation_service.py
Vertex AI Imagen 4.0を使用した画像生成サービスの単体テスト
"""

import io
import os
import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

from PIL import Image as PILImage

# app モジュールのインポート
from app.domains.image_generation.service import (
    ImageGenerationService,
    ImageGenerationRequest,
    ImageGenerationResponse,
)

@pytest.fixture
def service():
    """テスト用のサービスインスタンス"""
    svc = ImageGenerationService()
    svc._initialized = True  # Vertex AI 初期化済みにする
    return svc

def test_service_initialization(service):
    """サービス初期化が正しく行われるか"""
    assert service.model_name is not None
    assert service.storage_path.exists()

@pytest.mark.asyncio
async def test_generate_image_not_initialized():
    """Vertex AI 未初期化の場合のエラー"""
    svc = ImageGenerationService()
    svc._initialized = False
    request = ImageGenerationRequest(prompt="test image")

    result = await svc.generate_image(request)
    assert result.success is False
    assert "not initialized" in result.error_message

@pytest.mark.asyncio
async def test_generate_image_success(service, tmp_path):
    """Vertex AI SDK 経由での画像生成成功ケース"""
    # 実際にPillowで生成した1x1ピクセルの画像バイトを作る
    img_buffer = io.BytesIO()
    from PIL import Image
    image = Image.new("RGB", (1, 1), color="white")
    image.save(img_buffer, format="PNG")
    img_bytes = img_buffer.getvalue()

    mock_model = MagicMock()
    mock_generated_image = MagicMock()
    mock_generated_image._image_bytes = img_bytes  # ← 実画像データを渡す
    mock_model.generate_images.return_value.images = [mock_generated_image]

    with patch(
        "app.domains.image_generation.service.ImageGenerationModel.from_pretrained",
        return_value=mock_model,
    ):
        request = ImageGenerationRequest(prompt="a cute cat")
        result = await service.generate_image(request)

        # ---- 検証 ----
        assert result.success, f"Error: {result.error_message}"
        assert isinstance(result.image_data, bytes)
        assert "image_url" in result.model_dump()

@pytest.mark.asyncio
async def test_generate_image_no_vertexai(monkeypatch):
    """Vertex AI が利用不可のときにエラーとなること"""
    from app.domains.image_generation import service as service_module

    monkeypatch.setattr(service_module, "VERTEX_AI_AVAILABLE", False)
    svc = ImageGenerationService()
    svc._initialized = True

    request = ImageGenerationRequest(prompt="test")
    result = await svc.generate_image(request)

    assert result.success is False
    assert "not available" in result.error_message

@pytest.mark.asyncio
async def test_delete_image_success(service, tmp_path):
    """画像削除成功"""
    test_file = tmp_path / "delete_test.jpg"
    test_file.write_bytes(b"testdata")

    result = await service.delete_image(str(test_file))
    assert result is True
    assert not test_file.exists()

@pytest.mark.asyncio
async def test_delete_image_not_found(service):
    """削除対象が存在しない場合"""
    result = await service.delete_image("non_existing_file.jpg")
    assert result is False

@pytest.mark.asyncio
async def test_get_image_info_success(tmp_path):
    """画像情報取得成功"""

    # ① テスト画像ファイルを生成
    image_path = tmp_path / "test_image.jpg"
    img = PILImage.new("RGB", (100, 200), color="red")
    img.save(image_path)

    # ② 実際の Image を使用するように patch
    from app.domains.image_generation import service as service_module

    with patch.object(service_module, "Image", PILImage):  # ← ★ 修正箇所
        svc = service_module.ImageGenerationService()
        result = await svc.get_image_info(str(image_path))

    # ③ 結果を検証
    assert result is not None
    assert result["width"] == 100
    assert result["height"] == 200
    assert result["format"] == "JPEG"
    assert result["file_size"] > 0

@pytest.mark.asyncio
async def test_get_image_info_not_found(service):
    """ファイルが存在しない場合 None を返す"""
    result = await service.get_image_info("nonexistent.jpg")
    assert result is None

@pytest.mark.asyncio
async def test_get_image_info_exception(monkeypatch, service):
    """例外発生時に None を返す"""
    def raise_error(path):
        raise Exception("Mocked error")

    monkeypatch.setattr("app.domains.image_generation.service.os.path.exists", lambda x: True)
    monkeypatch.setattr("app.domains.image_generation.service.Image.open", raise_error)

    result = await service.get_image_info("dummy.jpg")
    assert result is None

@pytest.mark.asyncio
async def test_generate_image_url_success(service):
    """generate_image_url 成功時"""
    mock_response = ImageGenerationResponse(
        success=True,
        image_url="http://test_url"
    )

    with patch.object(service, "_generate_sync", return_value=mock_response):
        url = await service.generate_image_url(prompt="dog", placeholder_id="123")
        assert url == "http://test_url"

@pytest.mark.asyncio
async def test_generate_image_url_fail(service):
    """generate_image_url 失敗時"""
    mock_response = ImageGenerationResponse(
        success=False,
        error_message="error"
    )

    with patch.object(service, "_generate_sync", return_value=mock_response):
        with pytest.raises(Exception):
            await service.generate_image_url(prompt="cat", placeholder_id="xyz")
