"""
Test suite for backend/app/infrastructure/external_apis/gcs_service.py
"""
import pytest
from unittest.mock import patch, MagicMock
import uuid
from datetime import datetime

from app.infrastructure.external_apis.gcs_service import GCSService

@pytest.fixture(autouse=True)
def mock_settings():
    with patch('app.infrastructure.external_apis.gcs_service.settings') as mock_settings:
        mock_settings.gcs_bucket_name = "test-bucket"
        mock_settings.gcs_public_url_base = "https://storage.googleapis.com/test-bucket"
        yield mock_settings

@pytest.fixture
def mock_storage_client():
    with patch('app.infrastructure.external_apis.gcs_service.get_storage_client') as mock_client:
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        yield mock_client_instance

@pytest.fixture
def gcs_service(mock_storage_client):
    with patch('app.infrastructure.external_apis.gcs_service.get_storage_client', return_value=mock_storage_client):
        service = GCSService()
        service._bucket = MagicMock()
        service._initialized = True
        return service

@pytest.fixture
def sample_image_data():
    return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00'

def test_gcs_service_initialization_success(mock_storage_client):
    with patch('app.infrastructure.external_apis.gcs_service.get_storage_client', return_value=mock_storage_client):
        service = GCSService()
        assert service.is_available()
        assert service.bucket_name == "test-bucket"

def test_gcs_service_initialization_failure():
    with patch('app.infrastructure.external_apis.gcs_service.get_storage_client', side_effect=Exception("Auth failed")):
        service = GCSService()
        assert not service.is_available()

def test_gcs_service_not_available():
    service = GCSService()
    service._initialized = False
    service._bucket = None
    assert not service.is_available()

@pytest.mark.asyncio
async def test_upload_image_success(gcs_service, sample_image_data):
    mock_blob = MagicMock()
    gcs_service._bucket.blob.return_value = mock_blob
    
    success, url, path, error = gcs_service.upload_image(sample_image_data, "test.jpg")
    
    assert success is True
    assert url is not None
    assert path is not None
    assert error is None
    assert "images/" in path
    assert "test.jpg" in path
    mock_blob.upload_from_string.assert_called_once()

@pytest.mark.asyncio
async def test_upload_image_with_metadata(gcs_service, sample_image_data):
    mock_blob = MagicMock()
    gcs_service._bucket.blob.return_value = mock_blob
    
    metadata = {"source": "test", "user_id": "123"}
    success, url, path, error = gcs_service.upload_image(
        sample_image_data, 
        "test.jpg", 
        "image/jpeg", 
        metadata
    )
    
    assert success is True
    assert mock_blob.metadata == metadata

@pytest.mark.asyncio
async def test_upload_image_auto_filename(gcs_service, sample_image_data):
    mock_blob = MagicMock()
    gcs_service._bucket.blob.return_value = mock_blob
    
    success, url, path, error = gcs_service.upload_image(sample_image_data)
    
    assert success is True
    assert "generated_" in path
    assert path.endswith(".jpg")

@pytest.mark.asyncio
async def test_upload_image_service_unavailable():
    service = GCSService()
    service._initialized = False
    
    success, url, path, error = service.upload_image(b"test")
    
    assert success is False
    assert url is None
    assert path is None
    assert error == "GCS service not available"

@pytest.mark.asyncio
async def test_upload_image_gcs_error(gcs_service, sample_image_data):
    from google.cloud.exceptions import GoogleCloudError
    
    mock_blob = MagicMock()
    mock_blob.upload_from_string.side_effect = GoogleCloudError("Upload failed")
    gcs_service._bucket.blob.return_value = mock_blob
    
    success, url, path, error = gcs_service.upload_image(sample_image_data)
    
    assert success is False
    assert "GCS upload error" in error

def test_delete_image_success(gcs_service):
    mock_blob = MagicMock()
    gcs_service._bucket.blob.return_value = mock_blob
    
    success, error = gcs_service.delete_image("images/2024/01/test.jpg")
    
    assert success is True
    assert error is None
    mock_blob.delete.assert_called_once()

def test_delete_image_not_found(gcs_service):
    from google.api_core import exceptions as gcs_exceptions
    
    mock_blob = MagicMock()
    mock_blob.delete.side_effect = gcs_exceptions.NotFound("Not found")
    gcs_service._bucket.blob.return_value = mock_blob
    
    success, error = gcs_service.delete_image("images/2024/01/nonexistent.jpg")
    
    assert success is False
    assert error == "Image not found"

def test_delete_image_service_unavailable():
    service = GCSService()
    service._initialized = False
    
    success, error = service.delete_image("test.jpg")
    
    assert success is False
    assert error == "GCS service not available"

def test_image_exists_true(gcs_service):
    mock_blob = MagicMock()
    mock_blob.exists.return_value = True
    gcs_service._bucket.blob.return_value = mock_blob
    
    exists = gcs_service.image_exists("images/2024/01/test.jpg")
    
    assert exists is True

def test_image_exists_false(gcs_service):
    mock_blob = MagicMock()
    mock_blob.exists.return_value = False
    gcs_service._bucket.blob.return_value = mock_blob
    
    exists = gcs_service.image_exists("images/2024/01/nonexistent.jpg")
    
    assert exists is False

def test_image_exists_service_unavailable():
    service = GCSService()
    service._initialized = False
    
    exists = service.image_exists("test.jpg")
    
    assert exists is False

def test_get_image_info_success(gcs_service):
    mock_blob = MagicMock()
    mock_blob.name = "images/2024/01/test.jpg"
    mock_blob.size = 1024
    mock_blob.content_type = "image/jpeg"
    mock_blob.time_created = datetime.now()
    mock_blob.updated = datetime.now()
    mock_blob.metadata = {"source": "test"}
    mock_blob.public_url = "https://storage.googleapis.com/test-bucket/images/2024/01/test.jpg"
    gcs_service._bucket.blob.return_value = mock_blob
    
    info = gcs_service.get_image_info("images/2024/01/test.jpg")
    
    assert info is not None
    assert info["name"] == "images/2024/01/test.jpg"
    assert info["size"] == 1024
    assert info["content_type"] == "image/jpeg"

def test_get_image_info_service_unavailable():
    service = GCSService()
    service._initialized = False
    
    info = service.get_image_info("test.jpg")
    
    assert info is None

def test_guess_content_type():
    service = GCSService()
    
    assert service._guess_content_type("test.jpg") == "image/jpeg"
    assert service._guess_content_type("test.png") == "image/png"
    assert service._guess_content_type("test.unknown") == "application/octet-stream"

def test_guess_extension_from_data():
    service = GCSService()
    
    # JPEG data
    jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF'
    assert service._guess_extension_from_data(jpeg_data) == ".jpg"
    
    # PNG data
    png_data = b'\x89PNG\r\n\x1a\n'
    assert service._guess_extension_from_data(png_data) == ".png"
    
    # With content type
    assert service._guess_extension_from_data(b"data", "image/png") == ".png"
    assert service._guess_extension_from_data(b"data", "image/jpeg") == ".jpg"

def test_get_bucket_info_success(gcs_service):
    mock_bucket = gcs_service._bucket
    mock_bucket.name = "test-bucket"
    mock_bucket.location = "US"
    mock_bucket.storage_class = "STANDARD"
    mock_bucket.time_created = datetime.now()
    mock_bucket.project = "test-project"
    
    info = gcs_service.get_bucket_info()
    
    assert info is not None
    assert info["name"] == "test-bucket"
    assert info["location"] == "US"

def test_get_bucket_info_service_unavailable():
    service = GCSService()
    service._initialized = False
    
    info = service.get_bucket_info()
    
    assert info is None
