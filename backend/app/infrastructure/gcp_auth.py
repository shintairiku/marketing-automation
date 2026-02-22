"""
Google Cloud Platform Authentication Utility

This module provides a unified way to authenticate with Google Cloud services
that works both in local development (using service account JSON files)
and in Cloud Run (using default application credentials).
"""

import os
import json
import logging
from typing import Tuple
from google.auth import default
from google.oauth2 import service_account
from google.cloud import storage, aiplatform
import google.generativeai as genai
from google.auth.credentials import Credentials

logger = logging.getLogger(__name__)


class GCPAuthManager:
    """Manages Google Cloud Platform authentication for different environments."""
    
    def __init__(self):
        self._credentials = None
        self._project_id = None
        self._setup_credentials()
    
    def _setup_credentials(self) -> None:
        """Setup credentials based on the environment."""
        try:
            # Try to get credentials from service account JSON file (local development)
            json_file_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON_FILE')
            json_content = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            
            logger.info(f"Environment check - JSON_FILE: {json_file_path}, JSON_CONTENT: {'Present' if json_content else 'None'}")
            
            # If relative path, make it absolute from the project root
            if json_file_path and not os.path.isabs(json_file_path):
                # Get project root (go up from backend/app/infrastructure to project root)
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
                old_path = json_file_path
                json_file_path = os.path.join(project_root, json_file_path)
                logger.info(f"Path resolution: '{old_path}' -> '{json_file_path}'")
            
            if json_file_path and os.path.exists(json_file_path):
                file_size = os.path.getsize(json_file_path)
                logger.info(f"Using service account JSON file for authentication: {json_file_path} (size: {file_size} bytes)")
                
                # First, validate the JSON file content
                try:
                    with open(json_file_path, 'r', encoding='utf-8') as f:
                        service_account_info = json.load(f)
                        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
                        missing_fields = [field for field in required_fields if field not in service_account_info]
                        if missing_fields:
                            raise ValueError(f"Missing required fields in service account JSON: {missing_fields}")
                        
                        self._project_id = service_account_info.get('project_id')
                        logger.info(f"Validated JSON file for project: {self._project_id}")
                
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON format in service account file: {e}")
                except Exception as e:
                    raise ValueError(f"Error reading service account file: {e}")
                
                # Now create credentials
                self._credentials = service_account.Credentials.from_service_account_file(
                    json_file_path
                )
                    
            elif json_content:
                logger.info("Using service account JSON content for authentication")
                try:
                    service_account_info = json.loads(json_content)
                    required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
                    missing_fields = [field for field in required_fields if field not in service_account_info]
                    if missing_fields:
                        raise ValueError(f"Missing required fields in service account JSON content: {missing_fields}")
                    
                    self._project_id = service_account_info.get('project_id')
                    logger.info(f"Validated JSON content for project: {self._project_id}")
                    
                    self._credentials = service_account.Credentials.from_service_account_info(
                        service_account_info
                    )
                    
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON format in service account content: {e}")
                except Exception as e:
                    raise ValueError(f"Error parsing service account content: {e}")
                
            else:
                # Use default credentials (Cloud Run, Compute Engine, etc.)
                logger.info("Using default application credentials")
                self._credentials, self._project_id = default()
                
                # If no project ID from credentials, try environment variable
                if not self._project_id:
                    self._project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
                    
            logger.info(f"Successfully authenticated with GCP project: {self._project_id}")
            
        except Exception as e:
            logger.error(f"Failed to setup GCP credentials: {e}")
            raise
    
    @property
    def credentials(self) -> Credentials:
        """Get the configured credentials."""
        return self._credentials
    
    @property
    def project_id(self) -> str:
        """Get the project ID."""
        return self._project_id
    
    def get_storage_client(self) -> storage.Client:
        """Get an authenticated Google Cloud Storage client."""
        if self._credentials:
            return storage.Client(credentials=self._credentials, project=self._project_id)
        else:
            return storage.Client(project=self._project_id)
    
    def get_aiplatform_credentials(self) -> Tuple[Credentials, str]:
        """Get credentials and project ID for AI Platform."""
        return self._credentials, self._project_id
    
    def setup_genai_client(self) -> None:
        """Setup the Google Generative AI client."""
        from app.core.config import settings as _settings
        api_key = os.getenv('GOOGLE_API_KEY') or _settings.gemini_api_key
        if api_key:
            genai.configure(api_key=api_key)
            logger.info("Configured GenAI with API key")
        else:
            logger.warning("No API key found for Google Generative AI")
    
    def initialize_aiplatform(self, location: str = "us-central1") -> None:
        """Initialize AI Platform with proper credentials."""
        try:
            if self._credentials:
                aiplatform.init(
                    project=self._project_id,
                    location=location,
                    credentials=self._credentials
                )
            else:
                aiplatform.init(
                    project=self._project_id,
                    location=location
                )
            logger.info(f"Initialized AI Platform for project {self._project_id} in {location}")
        except Exception as e:
            logger.error(f"Failed to initialize AI Platform: {e}")
            raise


# Global instance
_auth_manager = None


def get_auth_manager() -> GCPAuthManager:
    """Get the global authentication manager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = GCPAuthManager()
    return _auth_manager


def get_storage_client() -> storage.Client:
    """Get an authenticated Google Cloud Storage client."""
    return get_auth_manager().get_storage_client()


def get_aiplatform_credentials() -> Tuple[Credentials, str]:
    """Get credentials and project ID for AI Platform."""
    return get_auth_manager().get_aiplatform_credentials()


def setup_genai_client() -> None:
    """Setup the Google Generative AI client."""
    return get_auth_manager().setup_genai_client()


def initialize_aiplatform(location: str = "us-central1") -> None:
    """Initialize AI Platform with proper credentials."""
    return get_auth_manager().initialize_aiplatform(location)