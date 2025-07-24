"""
Google Cloud Tasks integration for background task processing.

This module provides Cloud Tasks functionality for running article generation
processes in the background, allowing the REST API to return immediately
while the generation process continues asynchronously.
"""

import os
import json
import logging
from typing import Dict, Any
from google.cloud import tasks_v2
from google.cloud.tasks_v2 import CloudTasksClient
from google.protobuf import timestamp_pb2
from datetime import datetime, timedelta
from app.infrastructure.gcp_auth import get_auth_manager

logger = logging.getLogger(__name__)


class CloudTasksManager:
    """Manages Google Cloud Tasks for background processing."""
    
    def __init__(self):
        self._client = None
        self._project_id = None
        self._location = None
        self._queue_name = None
        self._setup_client()
    
    def _setup_client(self) -> None:
        """Setup Cloud Tasks client with proper authentication."""
        try:
            auth_manager = get_auth_manager()
            self._project_id = auth_manager.project_id
            self._location = os.getenv('CLOUD_TASKS_LOCATION', 'asia-northeast1')  # Tokyo region
            self._queue_name = os.getenv('CLOUD_TASKS_QUEUE', 'article-generation-queue')
            
            if auth_manager.credentials:
                self._client = CloudTasksClient(credentials=auth_manager.credentials)
            else:
                self._client = CloudTasksClient()
            
            logger.info(f"Initialized Cloud Tasks client for project {self._project_id} in {self._location}")
            
        except Exception as e:
            logger.error(f"Failed to setup Cloud Tasks client: {e}")
            raise
    
    @property
    def queue_path(self) -> str:
        """Get the full queue path."""
        return self._client.queue_path(self._project_id, self._location, self._queue_name)
    
    def create_article_generation_task(
        self,
        process_id: str,
        user_id: str,
        generation_params: Dict[str, Any],
        delay_seconds: int = 0
    ) -> str:
        """
        Create a Cloud Task for article generation.
        
        Args:
            process_id: UUID of the generation process
            user_id: User ID from Clerk
            generation_params: Parameters for article generation
            delay_seconds: Delay before executing the task
            
        Returns:
            Task name/ID for tracking
        """
        try:
            # Prepare task payload
            task_payload = {
                "process_id": process_id,
                "user_id": user_id,
                "generation_params": generation_params,
                "created_at": datetime.utcnow().isoformat(),
                "task_type": "article_generation"
            }
            
            # Create HTTP task
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": f"{os.getenv('BACKEND_URL', 'http://localhost:8000')}/articles/background/generate",
                    "headers": {
                        "Content-Type": "application/json",
                        "X-Task-Type": "article-generation",
                        "X-Process-ID": process_id
                    },
                    "body": json.dumps(task_payload).encode()
                }
            }
            
            # Add delay if specified
            if delay_seconds > 0:
                d = datetime.utcnow() + timedelta(seconds=delay_seconds)
                timestamp = timestamp_pb2.Timestamp()
                timestamp.FromDatetime(d)
                task["schedule_time"] = timestamp
            
            # Create the task
            response = self._client.create_task(
                parent=self.queue_path,
                task=task
            )
            
            task_name = response.name
            logger.info(f"Created Cloud Task {task_name} for process {process_id}")
            
            return task_name
            
        except Exception as e:
            logger.error(f"Failed to create Cloud Task for process {process_id}: {e}")
            raise
    
    def create_step_continuation_task(
        self,
        process_id: str,
        step_name: str,
        step_data: Dict[str, Any],
        delay_seconds: int = 5
    ) -> str:
        """
        Create a task to continue processing after a step completion.
        
        Args:
            process_id: UUID of the generation process
            step_name: Name of the step to continue from
            step_data: Data from the completed step
            delay_seconds: Delay before executing the task
            
        Returns:
            Task name/ID for tracking
        """
        try:
            task_payload = {
                "process_id": process_id,
                "step_name": step_name,
                "step_data": step_data,
                "created_at": datetime.utcnow().isoformat(),
                "task_type": "step_continuation"
            }
            
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": f"{os.getenv('BACKEND_URL', 'http://localhost:8000')}/articles/background/continue-step",
                    "headers": {
                        "Content-Type": "application/json",
                        "X-Task-Type": "step-continuation",
                        "X-Process-ID": process_id,
                        "X-Step-Name": step_name
                    },
                    "body": json.dumps(task_payload).encode()
                }
            }
            
            # Add delay
            if delay_seconds > 0:
                d = datetime.utcnow() + timedelta(seconds=delay_seconds)
                timestamp = timestamp_pb2.Timestamp()
                timestamp.FromDatetime(d)
                task["schedule_time"] = timestamp
            
            response = self._client.create_task(
                parent=self.queue_path,
                task=task
            )
            
            task_name = response.name
            logger.info(f"Created step continuation task {task_name} for process {process_id}, step {step_name}")
            
            return task_name
            
        except Exception as e:
            logger.error(f"Failed to create step continuation task for process {process_id}: {e}")
            raise


# Global instance
_tasks_manager = None


def get_tasks_manager() -> CloudTasksManager:
    """Get the global Cloud Tasks manager instance."""
    global _tasks_manager
    if _tasks_manager is None:
        _tasks_manager = CloudTasksManager()
    return _tasks_manager


def create_article_generation_task(
    process_id: str,
    user_id: str,
    generation_params: Dict[str, Any],
    delay_seconds: int = 0
) -> str:
    """Create a Cloud Task for article generation."""
    return get_tasks_manager().create_article_generation_task(
        process_id, user_id, generation_params, delay_seconds
    )


def create_step_continuation_task(
    process_id: str,
    step_name: str,
    step_data: Dict[str, Any],
    delay_seconds: int = 5
) -> str:
    """Create a task to continue processing after a step completion."""
    return get_tasks_manager().create_step_continuation_task(
        process_id, step_name, step_data, delay_seconds
    )