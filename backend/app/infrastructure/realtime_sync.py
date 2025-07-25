"""
Supabase Realtime synchronization service for article generation progress.

This module replaces WebSocket communication with Supabase Realtime database sync,
allowing multiple clients to receive real-time updates of article generation progress
through database change notifications.
"""

import json
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from app.common.database import supabase

logger = logging.getLogger(__name__)


class RealtimeSyncService:
    """Service for synchronizing article generation progress via Supabase Realtime."""
    
    def __init__(self):
        self.supabase = supabase
    
    def initialize_process(
        self,
        process_id: str,
        user_id: str,
        generation_params: Dict[str, Any],
        flow_id: Optional[str] = None
    ) -> bool:
        """
        Initialize a new article generation process in the database.
        
        Args:
            process_id: UUID of the generation process
            user_id: User ID from Clerk
            generation_params: Parameters for article generation
            flow_id: Optional flow ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare initial process data
            # Ensure process_id is a valid UUID
            if isinstance(process_id, str):
                try:
                    uuid.UUID(process_id)  # Validate UUID format
                except ValueError:
                    logger.error(f"Invalid UUID format: {process_id}")
                    return False
            
            process_data = {
                "id": process_id,
                "user_id": user_id,
                "flow_id": flow_id,
                "status": "in_progress",
                "current_step": "keyword_analyzing",
                "current_step_name": "キーワード分析",
                "progress_percentage": 0,
                "is_waiting_for_input": False,
                "auto_resume_eligible": False,
                "step_history": [],
                "process_metadata": {
                    "generation_params": generation_params,
                    "started_at": datetime.utcnow().isoformat(),
                    "image_mode": generation_params.get("image_mode", False)
                },
                "generated_content": {
                    "initial_params": generation_params
                },
                # Add potential missing required fields
                "article_context": {},
                "image_mode": generation_params.get("image_mode", False),
                "image_settings": generation_params.get("image_settings"),
                "style_template_id": generation_params.get("style_template_id")
            }
            
            # Insert into database
            logger.info(f"Attempting to insert process data: {process_data}")
            result = self.supabase.from_("generated_articles_state").insert(process_data).execute()
            
            if result.data:
                logger.info(f"Initialized process {process_id} for user {user_id}")
                return True
            else:
                logger.error(f"Failed to initialize process {process_id}: No data returned")
                logger.error(f"Result: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing process {process_id}: {e}")
            logger.error(f"Process data was: {process_data}")
            return False
    
    def update_step_progress(
        self,
        process_id: str,
        step_name: str,
        step_display_name: str,
        status: str = "in_progress",
        progress_percentage: Optional[int] = None,
        message: Optional[str] = None,
        step_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update the current step progress in the database.
        
        Args:
            process_id: UUID of the generation process
            step_name: Technical step name
            step_display_name: Human-readable step name
            status: Current status
            progress_percentage: Overall progress (0-100)
            message: Status message
            step_data: Additional step data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_data = {
                "current_step": step_name,
                "current_step_name": step_display_name,
                "status": status,
                "last_activity_at": datetime.utcnow().isoformat()
            }
            
            if progress_percentage is not None:
                update_data["progress_percentage"] = progress_percentage
            
            if message:
                # Get current metadata and update it
                current_record = self.supabase.from_("generated_articles_state").select("process_metadata").eq("id", process_id).execute().data[0]
                metadata = current_record["process_metadata"] or {}
                metadata["current_message"] = message
                update_data["process_metadata"] = metadata
            
            # Update the record
            self.supabase.from_("generated_articles_state").update(update_data).eq("id", process_id).execute()
            
            # Add to step history
            if step_data:
                self.supabase.rpc(
                    "add_step_to_history",
                    {
                        "process_id": process_id,
                        "step_name": step_name,
                        "step_status": status,
                        "step_data": json.dumps(step_data) if step_data else "{}"
                    }
                ).execute()
            
            logger.info(f"Updated step progress for process {process_id}: {step_name} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating step progress for process {process_id}: {e}")
            return False
    
    def set_user_input_required(
        self,
        process_id: str,
        input_type: str,
        input_data: Dict[str, Any],
        step_name: str
    ) -> bool:
        """
        Set the process to require user input.
        
        Args:
            process_id: UUID of the generation process
            input_type: Type of input required (select_persona, approve_plan, etc.)
            input_data: Data for user selection/approval
            step_name: Current step name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update process state
            update_data = {
                "status": "user_input_required",
                "is_waiting_for_input": True,
                "input_type": input_type,
                "resume_from_step": step_name,
                "auto_resume_eligible": True,
                "last_activity_at": datetime.utcnow().isoformat()
            }
            
            # Update generated_content with input options
            current_data = self.supabase.from_("generated_articles_state").select("generated_content").eq("id", process_id).execute().data[0]["generated_content"]
            current_data["user_input_request"] = {
                "type": input_type,
                "data": input_data,
                "requested_at": datetime.utcnow().isoformat()
            }
            update_data["generated_content"] = current_data
            
            self.supabase.from_("generated_articles_state").update(update_data).eq("id", process_id).execute()
            
            logger.info(f"Set user input required for process {process_id}: {input_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting user input required for process {process_id}: {e}")
            return False
    
    def update_research_progress(
        self,
        process_id: str,
        current_query: int,
        total_queries: int,
        query: str
    ) -> bool:
        """
        Update research progress in the database.
        
        Args:
            process_id: UUID of the generation process
            current_query: Current query number
            total_queries: Total number of queries
            query: Current query text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current metadata
            current_record = self.supabase.from_("generated_articles_state").select("process_metadata").eq("id", process_id).execute().data[0]
            metadata = current_record["process_metadata"]
            
            # Update research progress
            metadata["research_progress"] = {
                "currentQuery": current_query,
                "totalQueries": total_queries,
                "query": query,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Update in database
            self.supabase.from_("generated_articles_state").update({
                "process_metadata": metadata,
                "last_activity_at": datetime.utcnow().isoformat()
            }).eq("id", process_id).execute()
            
            logger.info(f"Updated research progress for process {process_id}: {current_query}/{total_queries}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating research progress for process {process_id}: {e}")
            return False
    
    def update_section_writing_progress(
        self,
        process_id: str,
        current_section: int,
        total_sections: int,
        section_heading: str,
        html_content_chunk: Optional[str] = None,
        is_complete: bool = False
    ) -> bool:
        """
        Update section writing progress.
        
        Args:
            process_id: UUID of the generation process
            current_section: Current section number
            total_sections: Total number of sections
            section_heading: Current section heading
            html_content_chunk: HTML content chunk (for streaming)
            is_complete: Whether the section is complete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current metadata and content
            current_record = self.supabase.from_("generated_articles_state").select("process_metadata, generated_content").eq("id", process_id).execute().data[0]
            metadata = current_record["process_metadata"]
            content = current_record["generated_content"]
            
            # Update sections progress
            metadata["sections_progress"] = {
                "currentSection": current_section,
                "totalSections": total_sections,
                "sectionHeading": section_heading,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Update content if provided
            if html_content_chunk:
                if "sections" not in content:
                    content["sections"] = {}
                
                section_key = f"section_{current_section}"
                if section_key not in content["sections"]:
                    content["sections"][section_key] = {
                        "heading": section_heading,
                        "content": "",
                        "is_complete": False
                    }
                
                content["sections"][section_key]["content"] += html_content_chunk
                content["sections"][section_key]["is_complete"] = is_complete
            
            # Update in database
            self.supabase.from_("generated_articles_state").update({
                "process_metadata": metadata,
                "generated_content": content,
                "last_activity_at": datetime.utcnow().isoformat()
            }).eq("id", process_id).execute()
            
            logger.info(f"Updated section progress for process {process_id}: {current_section}/{total_sections}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating section progress for process {process_id}: {e}")
            return False
    
    def complete_process(
        self,
        process_id: str,
        article_id: str,
        final_html_content: str,
        title: str
    ) -> bool:
        """
        Mark the process as completed with final results.
        
        Args:
            process_id: UUID of the generation process
            article_id: Final article ID
            final_html_content: Complete HTML content
            title: Article title
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current content
            current_record = self.supabase.from_("generated_articles_state").select("generated_content").eq("id", process_id).execute().data[0]
            content = current_record["generated_content"]
            
            # Update final content
            content["final_results"] = {
                "article_id": article_id,
                "title": title,
                "final_html_content": final_html_content,
                "completed_at": datetime.utcnow().isoformat()
            }
            
            # Update process state
            update_data = {
                "status": "completed",
                "current_step": "finished",
                "current_step_name": "完了",
                "progress_percentage": 100,
                "is_waiting_for_input": False,
                "auto_resume_eligible": False,
                "generated_content": content,
                "last_activity_at": datetime.utcnow().isoformat()
            }
            
            self.supabase.from_("generated_articles_state").update(update_data).eq("id", process_id).execute()
            
            logger.info(f"Completed process {process_id} with article {article_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing process {process_id}: {e}")
            return False
    
    def handle_error(
        self,
        process_id: str,
        error_message: str,
        step_name: str
    ) -> bool:
        """
        Handle process error and update database.
        
        Args:
            process_id: UUID of the generation process
            error_message: Error message
            step_name: Step where error occurred
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current metadata
            current_record = self.supabase.from_("generated_articles_state").select("process_metadata").eq("id", process_id).execute().data[0]
            metadata = current_record["process_metadata"]
            
            # Add error information
            metadata["error"] = {
                "message": error_message,
                "step": step_name,
                "occurred_at": datetime.utcnow().isoformat()
            }
            
            # Update process state
            update_data = {
                "status": "error",
                "current_step_name": f"エラー ({step_name})",
                "is_waiting_for_input": False,
                "auto_resume_eligible": False,
                "process_metadata": metadata,
                "last_activity_at": datetime.utcnow().isoformat()
            }
            
            self.supabase.from_("generated_articles_state").update(update_data).eq("id", process_id).execute()
            
            logger.error(f"Recorded error for process {process_id}: {error_message}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording error for process {process_id}: {e}")
            return False


# Global instance
_realtime_sync = None


def get_realtime_sync() -> RealtimeSyncService:
    """Get the global Realtime sync service instance."""
    global _realtime_sync
    if _realtime_sync is None:
        _realtime_sync = RealtimeSyncService()
    return _realtime_sync