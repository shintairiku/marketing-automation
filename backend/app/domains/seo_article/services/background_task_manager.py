# -*- coding: utf-8 -*-
"""
Background Task Manager for Supabase Realtime Migration

This module provides background task management for article generation processes,
replacing the previous WebSocket-based approach with database-driven background tasks
and Supabase Realtime event publishing.
"""

import asyncio
import logging
import uuid
from typing import Dict, Optional, Any, List
from datetime import datetime, timezone, timedelta

from app.domains.seo_article.context import ArticleContext
from app.domains.seo_article.schemas import GenerateArticleRequest

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    """Manages background task execution for article generation"""
    
    def __init__(self, service):
        self.service = service
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.task_registry: Dict[str, Dict[str, Any]] = {}
        
    async def create_background_task(
        self,
        process_id: str,
        task_type: str,
        task_data: Dict[str, Any],
        priority: int = 5,
        max_retries: int = 3,
        depends_on: List[str] = None
    ) -> str:
        """Create a new background task in the database"""
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            task_id = str(uuid.uuid4())
            
            # Insert task into database
            task_record = {
                "id": task_id,
                "process_id": process_id,
                "task_type": task_type,
                "task_data": task_data,
                "status": "pending",
                "priority": priority,
                "max_retries": max_retries,
                "depends_on": depends_on or [],
                "scheduled_for": datetime.now(timezone.utc).isoformat(),
                "created_by": "background_task_manager"
            }
            
            result = supabase.table("background_tasks").insert(task_record).execute()
            
            if result.data:
                logger.info(f"Created background task {task_id} for process {process_id}")
                return task_id
            else:
                raise Exception("Failed to create task record")
                
        except Exception as e:
            logger.error(f"Error creating background task: {e}")
            raise
    
    async def start_generation_process(
        self, 
        process_id: str, 
        user_id: str, 
        organization_id: Optional[str],
        request_data: GenerateArticleRequest
    ) -> str:
        """Start a new generation process as a background task"""
        try:
            logger.info(f"🎯 [BGT] Starting generation process for {process_id}, user: {user_id}")
            
            # Create the main generation task
            logger.info(f"📝 [BGT] Creating background task for process {process_id}")
            task_id = await self.create_background_task(
                process_id=process_id,
                task_type="generation_start",
                task_data={
                    "user_id": user_id,
                    "organization_id": organization_id,
                    "request_data": request_data.dict()
                },
                priority=5,
                max_retries=3
            )
            logger.info(f"✅ [BGT] Background task created with ID: {task_id}")
            
            # Start task execution in background with proper error handling
            logger.info("🚀 [BGT] Creating asyncio task for execution loop")
            task = asyncio.create_task(self._execute_task_loop(task_id))
            self.active_tasks[task_id] = task
            logger.info("✅ [BGT] Asyncio task created and added to active_tasks")
            
            # Add done callback for cleanup
            def cleanup_task(t):
                logger.info(f"🧹 [BGT] Cleaning up task {task_id}")
                self.active_tasks.pop(task_id, None)
                if t.exception():
                    logger.error(f"💥 [BGT] Background task {task_id} failed with exception: {t.exception()}")
                else:
                    logger.info(f"✅ [BGT] Background task {task_id} completed successfully")
            
            task.add_done_callback(cleanup_task)
            logger.info(f"🏁 [BGT] Started background task {task_id} for process {process_id}")
            
            return task_id
            
        except Exception as e:
            logger.error(f"💀 [BGT] Error starting generation process {process_id}: {e}")
            logger.exception("[BGT] Full exception details:")
            raise
    
    async def resume_generation_process(
        self, 
        process_id: str, 
        user_id: str
    ) -> str:
        """Resume a paused or failed generation process"""
        try:
            task_id = await self.create_background_task(
                process_id=process_id,
                task_type="generation_resume",
                task_data={
                    "user_id": user_id
                },
                priority=6,  # Higher priority for resumes
                max_retries=3
            )
            
            # Start task execution in background with proper error handling
            task = asyncio.create_task(self._execute_task_loop(task_id))
            self.active_tasks[task_id] = task
            
            # Add done callback for cleanup
            def cleanup_task(t):
                self.active_tasks.pop(task_id, None)
                if t.exception():
                    logger.error(f"Background task {task_id} failed with exception: {t.exception()}")
            
            task.add_done_callback(cleanup_task)
            logger.info(f"Started background task {task_id} for process {process_id}")
            
            return task_id
            
        except Exception as e:
            logger.error(f"Error resuming generation process {process_id}: {e}")
            raise
    
    async def continue_generation_after_input(
        self, 
        process_id: str, 
        user_id: str, 
        user_input: Dict[str, Any]
    ) -> str:
        """Continue generation after receiving user input"""
        try:
            task_id = await self.create_background_task(
                process_id=process_id,
                task_type="generation_continue",
                task_data={
                    "user_id": user_id,
                    "user_input": user_input
                },
                priority=7,  # Highest priority for user responses
                max_retries=3
            )
            
            # Start task execution in background with proper error handling
            task = asyncio.create_task(self._execute_task_loop(task_id))
            self.active_tasks[task_id] = task
            
            # Add done callback for cleanup
            def cleanup_task(t):
                self.active_tasks.pop(task_id, None)
                if t.exception():
                    logger.error(f"Background task {task_id} failed with exception: {t.exception()}")
            
            task.add_done_callback(cleanup_task)
            logger.info(f"Started background task {task_id} for process {process_id}")
            
            return task_id
            
        except Exception as e:
            logger.error(f"Error continuing generation process {process_id}: {e}")
            raise
    
    async def _execute_task_loop(self, task_id: str):
        """Execute a background task with proper error handling and retries"""
        try:
            logger.info(f"🚀 [TASK {task_id}] Starting execution of background task")
            
            # Get task details from database
            task_data = await self._get_task_data(task_id)
            if not task_data:
                logger.error(f"❌ [TASK {task_id}] Task not found in database")
                return
            
            process_id = task_data["process_id"]
            task_type = task_data["task_type"]
            
            logger.info(f"📋 [TASK {task_id}] Executing task of type '{task_type}' for process {process_id}")
            
            # Update task status to running
            await self._update_task_status(task_id, "running")
            logger.info(f"✅ [TASK {task_id}] Task status updated to running")
            
            # Execute based on task type
            try:
                if task_type == "generation_start":
                    logger.info(f"🎬 [TASK {task_id}] Starting generation_start execution")
                    await self._execute_generation_start(task_id, task_data)
                    logger.info(f"🏁 [TASK {task_id}] generation_start execution completed")
                elif task_type == "generation_continue":
                    logger.info(f"▶️ [TASK {task_id}] Starting generation_continue execution")
                    await self._execute_generation_continue(task_id, task_data)
                    logger.info(f"🏁 [TASK {task_id}] generation_continue execution completed")
                elif task_type == "generation_resume":
                    logger.info(f"🔄 [TASK {task_id}] Starting generation_resume execution")
                    await self._execute_generation_resume(task_id, task_data)
                    logger.info(f"🏁 [TASK {task_id}] generation_resume execution completed")
                else:
                    logger.error(f"❌ [TASK {task_id}] Unknown task type: {task_type}")
                    raise Exception(f"Unknown task type: {task_type}")
                
                # Mark task as completed
                await self._update_task_status(task_id, "completed")
                logger.info(f"✅ [TASK {task_id}] Task completed successfully")
                
            except Exception as execution_error:
                logger.error(f"💥 [TASK {task_id}] Error executing task: {execution_error}")
                logger.exception(f"[TASK {task_id}] Full exception details:")
                await self._handle_task_failure(task_id, task_data, str(execution_error))
                
        except Exception as e:
            logger.error(f"💀 [TASK {task_id}] Fatal error in task execution loop: {e}")
            logger.exception(f"[TASK {task_id}] Fatal error full details:")
            try:
                await self._update_task_status(task_id, "failed", str(e))
            except Exception:
                pass  # Don't raise on cleanup errors
    
    async def _execute_generation_start(self, task_id: str, task_data: Dict[str, Any]):
        """Execute generation start task"""
        try:
            process_id = task_data["process_id"]
            request_params = task_data["task_data"]
            user_id = request_params["user_id"]
            
            logger.info(f"🔄 [TASK {task_id}] Starting generation for process {process_id}, user: {user_id}")
            
            # Load context from database
            logger.info(f"📖 [TASK {task_id}] Loading context for process {process_id}")
            context = await self.service.persistence_service.load_context_from_db(process_id, user_id)
            if not context:
                raise Exception(f"Failed to load context for process {process_id}")
            
            logger.info(f"✅ [TASK {task_id}] Context loaded successfully, current step: {context.current_step}")
            
            # Set up context for background execution
            logger.info(f"⚙️ [TASK {task_id}] Setting up context for background execution")
            context.websocket = None  # No WebSocket in background mode
            context.user_response_event = asyncio.Event()
            context.process_id = process_id
            context.user_id = user_id
            
            # Publish start event
            logger.info(f"📢 [TASK {task_id}] Publishing generation_started event")
            await self._publish_realtime_event(
                process_id=process_id,
                event_type="generation_started",
                event_data={
                    "task_id": task_id,
                    "current_step": context.current_step,
                    "message": "Background generation started"
                }
            )
            logger.info(f"✅ [TASK {task_id}] generation_started event published")
            
            # Start generation flow
            logger.info(f"🚀 [TASK {task_id}] Starting generation flow")
            await self._run_generation_flow(
                context=context,
                process_id=process_id,
                user_id=user_id,
                task_id=task_id
            )
            logger.info(f"🏁 [TASK {task_id}] Generation flow completed")
            
        except Exception as e:
            logger.error(f"💥 [TASK {task_id}] Error in generation start task: {e}")
            logger.exception(f"[TASK {task_id}] Full exception details:")
            raise
    
    async def _execute_generation_continue(self, task_id: str, task_data: Dict[str, Any]):
        """Execute generation continue after user input"""
        try:
            process_id = task_data["process_id"]
            request_params = task_data["task_data"]
            user_id = request_params["user_id"]
            user_input = request_params["user_input"]
            
            # Load context and apply user input
            context = await self.service.persistence_service.load_context_from_db(process_id, user_id)
            if not context:
                raise Exception(f"Failed to load context for process {process_id}")
            
            # Apply user input to context
            await self._apply_user_input_to_context(context, user_input)
            
            # Save updated context
            await self.service.persistence_service.save_context_to_db(
                context, process_id=process_id, user_id=user_id
            )
            
            # Continue generation
            await self._run_generation_flow(
                context=context,
                process_id=process_id,
                user_id=user_id,
                task_id=task_id
            )
            
        except Exception as e:
            logger.error(f"Error in generation continue task {task_id}: {e}")
            raise
    
    async def _execute_generation_resume(self, task_id: str, task_data: Dict[str, Any]):
        """Execute generation resume task"""
        try:
            process_id = task_data["process_id"]
            request_params = task_data["task_data"]
            user_id = request_params["user_id"]
            
            # Load context
            context = await self.service.persistence_service.load_context_from_db(process_id, user_id)
            if not context:
                raise Exception(f"Failed to load context for process {process_id}")
            
            # Resume from current step
            await self._run_generation_flow(
                context=context,
                process_id=process_id,
                user_id=user_id,
                task_id=task_id
            )
            
        except Exception as e:
            logger.error(f"Error in generation resume task {task_id}: {e}")
            raise
    
    async def _run_generation_flow(
        self, 
        context: ArticleContext, 
        process_id: str, 
        user_id: str,
        task_id: str
    ):
        """Run the main generation flow with realtime events"""
        
        try:
            logger.info(f"🔄 [TASK {task_id}] Starting generation flow for process {process_id}")
            logger.info(f"📍 [TASK {task_id}] Initial step: {context.current_step}")
            
            # Set up context for background execution
            context.websocket = None
            context.user_response_event = asyncio.Event()
            context.process_id = process_id
            context.user_id = user_id
            
            step_counter = 0
            while context.current_step not in ['completed', 'error']:
                step_counter += 1
                current_step = context.current_step
                logger.info(f"🔄 [TASK {task_id}] Loop iteration {step_counter}, current step: {current_step}")
                
                try:
                    # Check if current step requires user input
                    if context.current_step in ['persona_generated', 'theme_proposed', 'research_plan_generated', 'outline_generated']:
                        logger.info(f"👤 [TASK {task_id}] Step {current_step} requires user input, waiting...")
                        await self._handle_user_input_step(context, process_id, user_id, task_id)
                        break  # Exit loop and wait for user input
                    
                    # Publish step start event
                    logger.info(f"📢 [TASK {task_id}] Publishing step_started event for {current_step}")
                    await self._publish_realtime_event(
                        process_id=process_id,
                        event_type="step_started",
                        event_data={
                            "step_name": context.current_step,
                            "message": f"Starting step: {context.current_step}",
                            "task_id": task_id
                        }
                    )
                    
                    # Execute the step
                    logger.info(f"⚡ [TASK {task_id}] Executing step: {current_step}")
                    await self._execute_single_step_with_events(context, process_id, user_id, task_id)
                    logger.info(f"✅ [TASK {task_id}] Step execution completed, new step: {context.current_step}")
                    
                    # Publish step completion event
                    await self._publish_realtime_event(
                        process_id=process_id,
                        event_type="step_completed",
                        event_data={
                            "step_name": current_step,  # Use the original step name
                            "next_step": context.current_step,  # Show the new step
                            "message": f"Completed step: {current_step}, next: {context.current_step}",
                            "task_id": task_id
                        }
                    )
                    
                    # Save progress to database
                    logger.info(f"💾 [TASK {task_id}] Saving context to database")
                    await self.service.persistence_service.save_context_to_db(
                        context, process_id=process_id, user_id=user_id
                    )
                    logger.info(f"✅ [TASK {task_id}] Context saved successfully")
                    
                    # Small delay to prevent overwhelming the system
                    await asyncio.sleep(0.5)
                    
                    # Safety check to prevent infinite loops
                    if step_counter > 20:
                        logger.error(f"⚠️ [TASK {task_id}] Too many step iterations ({step_counter}), breaking loop")
                        break
                    
                except Exception as e:
                    logger.error(f"💥 [TASK {task_id}] Error executing step {context.current_step}: {e}")
                    logger.exception(f"[TASK {task_id}] Step execution exception details:")
                    await self._handle_generation_error(process_id, str(e), context.current_step)
                    break
            
            # Handle completion
            if context.current_step == 'completed':
                logger.info(f"🎉 [TASK {task_id}] Generation completed successfully")
                await self._handle_generation_completion(context, process_id, user_id)
            else:
                logger.info(f"⏸️ [TASK {task_id}] Generation flow ended at step: {context.current_step}")
                
        except Exception as e:
            logger.error(f"💀 [TASK {task_id}] Error in generation flow for process {process_id}: {e}")
            logger.exception(f"[TASK {task_id}] Generation flow exception details:")
            await self._handle_generation_error(process_id, str(e), context.current_step)
            raise
    
    async def _execute_single_step_with_events(
        self, 
        context: ArticleContext, 
        process_id: str, 
        user_id: str,
        task_id: str
    ):
        """Execute a single step and publish relevant events"""
        
        step_name = context.current_step
        logger.info(f"[TASK {task_id}] Executing step: {step_name} for process {process_id}")
        
        try:
            # Use the existing flow manager from the service
            flow_manager = self.service.flow_manager
            
            if step_name == "start":
                logger.info(f"[TASK {task_id}] Starting keyword analysis for process {process_id}")
                context.current_step = "keyword_analyzing"
                # Actually execute keyword analysis in the same step
                await flow_manager.execute_keyword_analysis_step(context)
                logger.info(f"[TASK {task_id}] Completed keyword analysis, current step: {context.current_step}")
                
            elif step_name == "keyword_analyzing":
                logger.info(f"[TASK {task_id}] Executing keyword analysis step")
                await flow_manager.execute_keyword_analysis_step(context)
                logger.info(f"[TASK {task_id}] Keyword analysis completed, current step: {context.current_step}")
                
            elif step_name == "persona_generating":
                logger.info(f"[TASK {task_id}] Executing persona generation step")
                await flow_manager.execute_persona_generation_step(context)
                logger.info(f"[TASK {task_id}] Persona generation completed, current step: {context.current_step}")
                
            elif step_name == "theme_generating":
                logger.info(f"[TASK {task_id}] Executing theme generation step")
                await flow_manager.execute_theme_generation_step(context)
                logger.info(f"[TASK {task_id}] Theme generation completed, current step: {context.current_step}")
                
            elif step_name == "researching":
                logger.info(f"[TASK {task_id}] Executing comprehensive research")
                await flow_manager.execute_research_step(context)
                logger.info(f"[TASK {task_id}] Research completed, current step: {context.current_step}")
                
            elif step_name == "outline_generating":
                logger.info(f"[TASK {task_id}] Executing outline generation step")
                await flow_manager.execute_outline_generation_step(context)
                logger.info(f"[TASK {task_id}] Outline generation completed, current step: {context.current_step}")
                
            elif step_name == "writing_sections":
                logger.info(f"[TASK {task_id}] Executing section writing step")
                await self._execute_section_writing_with_progress(context, process_id)
                logger.info(f"[TASK {task_id}] Section writing completed, current step: {context.current_step}")
                
            elif step_name == "editing":
                logger.info(f"[TASK {task_id}] Executing editing step")
                await flow_manager.execute_editing_step(context)
                logger.info(f"[TASK {task_id}] Editing completed, current step: {context.current_step}")
                
            else:
                logger.warning(f"[TASK {task_id}] Unknown step: {step_name}")
                # For unknown steps, mark as error
                context.current_step = "error"
                raise Exception(f"Unknown step: {step_name}")
                
        except Exception as e:
            logger.error(f"[TASK {task_id}] Error in step {step_name}: {e}")
            raise
    
    async def _execute_research_with_progress(self, context: ArticleContext, process_id: str):
        """Execute research with progress events (parallel execution)"""
        
        if not context.research_plan or not hasattr(context.research_plan, 'queries'):
            raise Exception("No research plan available")
        
        total_queries = len(context.research_plan.queries)
        
        # Initialize research query results
        if not hasattr(context, 'research_query_results'):
            context.research_query_results = []
        
        # Publish research start event
        await self._publish_realtime_event(
            process_id=process_id,
            event_type="research_started",
            event_data={
                "message": f"Starting parallel research execution for {total_queries} queries",
                "total_queries": total_queries
            }
        )
        
        # Shared progress tracker for efficient updates
        completed_queries = 0
        progress_lock = asyncio.Lock()
        
        async def update_shared_progress():
            """Update progress to frontend periodically"""
            nonlocal completed_queries
            async with progress_lock:
                completed_queries += 1
                await self._publish_realtime_event(
                    process_id=process_id,
                    event_type="research_progress",
                    event_data={
                        "completed_queries": completed_queries,
                        "total_queries": total_queries,
                        "progress_percentage": int((completed_queries / total_queries) * 100),
                        "status": "executing" if completed_queries < total_queries else "completed"
                    }
                )
        
        # Create tasks for parallel execution
        async def execute_query_with_progress(query, query_index: int):
            """Execute a single query with optimized progress reporting"""
            try:
                # Execute the research query using flow manager
                await self.service.flow_manager.execute_single_research_query(context, query, query_index)
                
                # Update shared progress counter
                await update_shared_progress()
                
                return query_index, True
                
            except Exception as e:
                logger.error(f"Error in research query {query_index + 1}: {e}")
                # Still update progress for failed queries
                await update_shared_progress()
                return query_index, False
        
        # Execute all queries in parallel with concurrency limit
        # Limit concurrent requests to prevent API rate limiting
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent research queries
        
        async def execute_with_semaphore(query, query_index: int):
            """Execute query with concurrency control"""
            async with semaphore:
                return await execute_query_with_progress(query, query_index)
        
        tasks = [
            execute_with_semaphore(query, i) 
            for i, query in enumerate(context.research_plan.queries)
        ]
        
        # Wait for all queries to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle any failures
        successful_queries = 0
        failed_queries = []
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Research query failed with exception: {result}")
                failed_queries.append(str(result))
            elif isinstance(result, tuple):
                query_index, success = result
                if success:
                    successful_queries += 1
                else:
                    failed_queries.append(f"Query {query_index + 1}")
        
        # Publish completion summary
        await self._publish_realtime_event(
            process_id=process_id,
            event_type="research_synthesis_completed",
            event_data={
                "message": f"Research execution completed: {successful_queries}/{total_queries} queries successful",
                "successful_queries": successful_queries,
                "total_queries": total_queries,
                "failed_queries": failed_queries,
                "total_results": len(context.research_query_results) if hasattr(context, 'research_query_results') else 0
            }
        )
        
        # Move to synthesis
        context.current_step = "research_synthesizing"
        
        # Publish synthesis start event
        await self._publish_realtime_event(
            process_id=process_id,
            event_type="research_synthesis_started",
            event_data={
                "message": "Starting research synthesis",
                "total_results": len(context.research_query_results) if hasattr(context, 'research_query_results') else 0
            }
        )
    
    async def _execute_section_writing_with_progress(self, context: ArticleContext, process_id: str):
        """Execute section writing with progress events"""
        
        if not context.generated_outline or not hasattr(context.generated_outline, 'sections'):
            raise Exception("No outline available for section writing")
        
        total_sections = len(context.generated_outline.sections)
        if not hasattr(context, 'generated_sections_html'):
            context.generated_sections_html = []
        
        for i, section in enumerate(context.generated_outline.sections):
            # Publish section progress event
            await self._publish_realtime_event(
                process_id=process_id,
                event_type="section_progress",
                event_data={
                    "current_section": i + 1,
                    "total_sections": total_sections,
                    "section_heading": section.heading if hasattr(section, 'heading') else f"Section {i+1}",
                    "progress_percentage": int((i / total_sections) * 100)
                }
            )
            
            # Write the section using flow manager
            section_content = await self.service.flow_manager.write_single_section(context, section, i)
            context.generated_sections_html.append(section_content)
            
            # Publish section completion event
            await self._publish_realtime_event(
                process_id=process_id,
                event_type="section_completed",
                event_data={
                    "section_index": i,
                    "section_heading": section.heading if hasattr(section, 'heading') else f"Section {i+1}",
                    "section_content": section_content,
                    "image_placeholders": getattr(context, 'image_placeholders', [])
                }
            )
        
        # Combine all sections
        context.full_draft_html = '\n\n'.join(context.generated_sections_html)
        context.current_step = "editing"
    
    async def _handle_user_input_step(
        self, 
        context: ArticleContext, 
        process_id: str, 
        user_id: str,
        task_id: str
    ):
        """Handle steps that require user input"""
        
        try:
            # Determine input type and data
            input_type = None
            input_data = {}
            
            if context.current_step == "persona_generated":
                input_type = "select_persona"
                if hasattr(context, 'generated_detailed_personas') and context.generated_detailed_personas:
                    input_data = {
                        "personas": [
                            {"id": i, "description": desc} 
                            for i, desc in enumerate(context.generated_detailed_personas)
                        ]
                    }
            elif context.current_step == "theme_proposed":
                input_type = "select_theme"
                if hasattr(context, 'generated_themes') and context.generated_themes:
                    input_data = {
                        "themes": [
                            {
                                "title": theme.title if hasattr(theme, 'title') else f"Theme {i}",
                                "description": theme.description if hasattr(theme, 'description') else "",
                                "keywords": theme.keywords if hasattr(theme, 'keywords') else []
                            }
                            for i, theme in enumerate(context.generated_themes)
                        ]
                    }
            elif context.current_step == "research_plan_generated":
                input_type = "approve_plan"
                if hasattr(context, 'research_plan') and context.research_plan:
                    input_data = {"plan": context.research_plan.dict() if hasattr(context.research_plan, 'dict') else str(context.research_plan)}
            elif context.current_step == "outline_generated":
                input_type = "approve_outline"
                if hasattr(context, 'generated_outline') and context.generated_outline:
                    input_data = {"outline": context.generated_outline.dict() if hasattr(context.generated_outline, 'dict') else str(context.generated_outline)}
            
            # Update process state
            await self.service.persistence_service.update_process_status(
                process_id=process_id,
                status="user_input_required",
                current_step=context.current_step,
                metadata={
                    "input_type": input_type,
                    "waiting_since": datetime.now(timezone.utc).isoformat(),
                    "task_id": task_id
                }
            )
            
            # Publish user input required event
            await self._publish_realtime_event(
                process_id=process_id,
                event_type="user_input_required",
                event_data={
                    "input_type": input_type,
                    "data": input_data,
                    "message": f"User input required: {input_type}",
                    "timeout_minutes": 30  # Configurable timeout
                }
            )
            
            logger.info(f"Process {process_id} waiting for user input: {input_type}")
            
        except Exception as e:
            logger.error(f"Error handling user input step for process {process_id}: {e}")
            raise
    
    async def _handle_generation_completion(
        self, 
        context: ArticleContext, 
        process_id: str, 
        user_id: str
    ):
        """Handle successful generation completion"""
        
        try:
            # Save final article
            final_content = getattr(context, 'final_article_html', None) or getattr(context, 'full_draft_html', '')
            
            # Update process status
            await self.service.persistence_service.update_process_status(
                process_id=process_id,
                status="completed",
                current_step="completed",
                metadata={
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "total_sections": len(getattr(context, 'generated_sections_html', [])),
                    "final_length": len(final_content) if final_content else 0
                }
            )
            
            # Publish completion event
            await self._publish_realtime_event(
                process_id=process_id,
                event_type="generation_completed",
                event_data={
                    "title": context.generated_outline.title if hasattr(context, 'generated_outline') and context.generated_outline and hasattr(context.generated_outline, 'title') else "Generated Article",
                    "final_html_content": final_content,
                    "article_id": getattr(context, 'final_article_id', None),
                    "message": "Article generation completed successfully",
                    "completion_time": datetime.now(timezone.utc).isoformat()
                }
            )
            
            logger.info(f"Generation completed successfully for process {process_id}")
            
        except Exception as e:
            logger.error(f"Error handling generation completion for process {process_id}: {e}")
            raise
    
    async def _handle_generation_error(self, process_id: str, error_message: str, current_step: str):
        """Handle generation errors"""
        
        try:
            # Update process status
            await self.service.persistence_service.update_process_status(
                process_id=process_id,
                status="error",
                current_step="error",
                metadata={
                    "error_message": error_message,
                    "failed_step": current_step,
                    "error_time": datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Publish error event
            await self._publish_realtime_event(
                process_id=process_id,
                event_type="generation_error",
                event_data={
                    "error_message": error_message,
                    "step_name": current_step,
                    "message": f"Generation failed at step: {current_step}",
                    "error_time": datetime.now(timezone.utc).isoformat()
                }
            )
            
            logger.error(f"Generation failed for process {process_id}: {error_message}")
            
        except Exception as e:
            logger.error(f"Error handling generation error for process {process_id}: {e}")
    
    async def _apply_user_input_to_context(self, context: ArticleContext, user_input: Dict[str, Any]):
        """Apply user input to context state"""
        try:
            response_type = user_input.get("response_type")
            payload = user_input.get("payload", {})
            
            logger.info(f"📝 Applying user input - response_type: {response_type}, current_step: {context.current_step}")
            
            if response_type == "select_persona":
                selected_id = payload.get("selected_id")
                if selected_id is not None and hasattr(context, 'generated_detailed_personas') and context.generated_detailed_personas:
                    context.selected_detailed_persona = context.generated_detailed_personas[selected_id]
                    context.current_step = "theme_generating"
                    
            elif response_type == "select_theme":
                selected_index = payload.get("selected_index")
                if selected_index is not None and hasattr(context, 'generated_themes') and context.generated_themes:
                    context.selected_theme = context.generated_themes[selected_index]
                    
                    # フロー設定に応じて次のステップを決定
                    from app.core.config import settings
                    if settings.use_reordered_flow:
                        context.current_step = "outline_generating"
                        logger.info("Reordered flow: Moving from theme selection to outline_generating")
                    else:
                        context.current_step = "researching"
                        logger.info("Classic flow: Moving from theme selection to researching")
                    
            elif response_type == "approve_plan":
                approved = payload.get("approved", False)
                if approved:
                    context.current_step = "researching"
                else:
                    context.current_step = "researching"  # Regenerate
                    
            elif response_type == "approve_outline":
                approved = payload.get("approved", False)
                if approved:
                    # フロー設定に応じて次のステップを決定
                    from app.core.config import settings
                    if settings.use_reordered_flow:
                        context.current_step = "researching"
                        logger.info("Reordered flow: Moving from outline approval to researching")
                    else:
                        context.current_step = "writing_sections"
                        logger.info("Classic flow: Moving from outline approval to writing_sections")
                else:
                    context.current_step = "outline_generating"  # Regenerate
            
            # Handle regeneration requests
            elif response_type == "regenerate":
                # Determine what to regenerate based on current step
                if context.current_step == "persona_generated":
                    context.current_step = "persona_generating"
                    context.generated_detailed_personas = []
                    logger.info("Regenerating personas from persona_generated step")
                elif context.current_step == "theme_proposed":
                    context.current_step = "theme_generating"
                    context.generated_themes = []
                    logger.info("Regenerating themes from theme_proposed step")
                elif context.current_step == "research_plan_generated":
                    context.current_step = "researching"
                    context.research_plan = None
                    logger.info("Regenerating research from research_plan_generated step")
                elif context.current_step == "outline_generated":
                    context.current_step = "outline_generating"
                    context.generated_outline = None
                    context.outline = None
                    logger.info("Regenerating outline from outline_generated step")
                else:
                    logger.warning(f"Regeneration not supported for step: {context.current_step}")
            
            # Handle edit and proceed requests
            elif response_type == "edit_and_proceed":
                edited_content = payload.get("edited_content", {})
                
                if context.current_step == "persona_generated":
                    # Edit persona
                    persona_description = edited_content.get("description")
                    if persona_description and isinstance(persona_description, str):
                        context.selected_detailed_persona = persona_description
                        context.current_step = "theme_generating"
                        logger.info("Applied persona edit and proceeding to theme generation")
                    else:
                        logger.error("Invalid persona description in edit_and_proceed")
                        
                elif context.current_step == "theme_proposed":
                    # Edit theme
                    logger.info(f"🎨 [EDIT_THEME] Processing theme edit: {edited_content}")
                    logger.info(f"🔍 [EDIT_THEME] Validation - title: {type(edited_content.get('title'))}, description: {type(edited_content.get('description'))}, keywords: {type(edited_content.get('keywords'))}")
                    
                    if (isinstance(edited_content.get("title"), str) and 
                        isinstance(edited_content.get("description"), str) and 
                        isinstance(edited_content.get("keywords"), list)):
                        
                        try:
                            # Import ThemeProposalData from schemas
                            from app.domains.seo_article.schemas import ThemeProposalData
                            context.selected_theme = ThemeProposalData(**edited_content)
                            context.current_step = "researching"
                            logger.info("✅ [EDIT_THEME] Applied theme edit and proceeding to research")
                        except Exception as theme_error:
                            logger.error(f"💥 [EDIT_THEME] Error creating ThemeProposalData: {theme_error}")
                            raise
                    else:
                        logger.error(f"❌ [EDIT_THEME] Invalid theme structure in edit_and_proceed: {edited_content}")
                        
                elif context.current_step == "research_plan_generated":
                    # Edit research plan
                    logger.info(f"📋 [EDIT_RESEARCH_PLAN] Processing research plan edit: {edited_content}")
                    topic = edited_content.get("topic")
                    queries = edited_content.get("queries", [])
                    
                    logger.info(f"🔍 [EDIT_RESEARCH_PLAN] Validation - topic: {type(topic)}, queries: {type(queries)}")
                    
                    if topic and isinstance(queries, list):
                        try:
                            # Import ResearchPlanData and ResearchPlanQueryData from schemas
                            from app.domains.seo_article.schemas import ResearchPlanData, ResearchPlanQueryData
                            
                            # Convert queries to proper format
                            processed_queries = []
                            for query_item in queries:
                                if isinstance(query_item, dict):
                                    processed_queries.append(ResearchPlanQueryData(
                                        query=query_item.get("query", ""),
                                        focus=query_item.get("focus", "")
                                    ))
                                elif isinstance(query_item, str):
                                    processed_queries.append(ResearchPlanQueryData(
                                        query=query_item,
                                        focus=""
                                    ))
                            
                            context.research_plan = ResearchPlanData(
                                topic=topic,
                                queries=processed_queries
                            )
                            context.current_step = "researching"
                            logger.info("✅ [EDIT_RESEARCH_PLAN] Applied research plan edit and proceeding to research execution")
                        except Exception as research_error:
                            logger.error(f"💥 [EDIT_RESEARCH_PLAN] Error creating ResearchPlanData: {research_error}")
                            raise
                    else:
                        logger.error(f"❌ [EDIT_RESEARCH_PLAN] Invalid research plan structure in edit_and_proceed: topic={topic}, queries={queries}")
                        
                elif context.current_step == "outline_generated":
                    # Edit outline
                    logger.info(f"📋 [EDIT_OUTLINE] Processing outline edit: {edited_content}")
                    title = edited_content.get("title")
                    suggested_tone = edited_content.get("suggested_tone", "")
                    sections = edited_content.get("sections", [])
                    
                    logger.info(f"🔍 [EDIT_OUTLINE] Validation - title: {type(title)}, suggested_tone: {type(suggested_tone)}, sections: {type(sections)}")
                    
                    top_level_heading = edited_content.get("top_level_heading")
                    if isinstance(top_level_heading, int) and top_level_heading in (2, 3):
                        new_top_level = top_level_heading
                    else:
                        new_top_level = getattr(context, 'outline_top_level_heading', 2)

                    if title and isinstance(sections, list):
                        try:
                            normalized_outline = self.service.utils.normalize_outline_structure(
                                {
                                    "title": title,
                                    "suggested_tone": suggested_tone,
                                    "top_level_heading": new_top_level,
                                    "sections": sections,
                                },
                                top_level_hint=new_top_level,
                            )
                            context.generated_outline = normalized_outline
                            context.outline_top_level_heading = normalized_outline.top_level_heading
                            context.outline = context.generated_outline
                            
                            # フロー設定に応じて次のステップを決定
                            from app.core.config import settings
                            if settings.use_reordered_flow:
                                context.current_step = "researching"
                                logger.info("✅ [EDIT_OUTLINE] Applied outline edit and proceeding to research (reordered flow)")
                            else:
                                context.current_step = "writing_sections"
                                logger.info("✅ [EDIT_OUTLINE] Applied outline edit and proceeding to section writing (classic flow)")
                        except Exception as outline_error:
                            logger.error(f"💥 [EDIT_OUTLINE] Error creating OutlineData: {outline_error}")
                            raise
                    else:
                        logger.error(f"❌ [EDIT_OUTLINE] Invalid outline structure in edit_and_proceed: title={title}, sections={sections}")
                        
                else:
                    logger.warning(f"Edit and proceed not supported for step: {context.current_step}")
            
            # Clear user input waiting state
            if hasattr(context, 'expected_user_input'):
                context.expected_user_input = None
            if hasattr(context, 'user_response'):
                context.user_response = None
            
            logger.info(f"Applied user input {response_type} to context, new step: {context.current_step}")
            
        except Exception as e:
            logger.error(f"Error applying user input to context: {e}")
            raise
    
    async def _publish_realtime_event(self, process_id: str, event_type: str, event_data: Dict[str, Any]):
        """Publish event to realtime subscribers using database function"""
        
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            # Use the database function to create process event
            result = supabase.rpc('create_process_event', {
                'p_process_id': process_id,
                'p_event_type': event_type,
                'p_event_data': event_data,
                'p_event_category': 'generation',
                'p_event_source': 'background_task'
            }).execute()
            
            if result.data:
                logger.debug(f"Published realtime event {event_type} for process {process_id}")
            else:
                logger.warning(f"Failed to publish realtime event {event_type} for process {process_id}")
                
        except Exception as e:
            logger.error(f"Error publishing realtime event {event_type} for process {process_id}: {e}")
            # Don't raise here as this is not critical for generation to continue
    
    async def _get_task_data(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task data from database"""
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            result = supabase.table("background_tasks").select("*").eq("id", task_id).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting task data for {task_id}: {e}")
            return None
    
    async def _update_task_status(
        self, 
        task_id: str, 
        status: str, 
        error_message: Optional[str] = None
    ):
        """Update task status in database"""
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            if status == "running":
                update_data["started_at"] = datetime.now(timezone.utc).isoformat()
                update_data["worker_id"] = "background_task_manager"
                update_data["heartbeat_at"] = datetime.now(timezone.utc).isoformat()
            elif status in ["completed", "failed", "cancelled"]:
                update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
            
            if error_message:
                update_data["error_message"] = error_message
            
            result = supabase.table("background_tasks").update(update_data).eq("id", task_id).execute()
            
            if result.data:
                logger.debug(f"Updated task {task_id} status to {status}")
            
        except Exception as e:
            logger.error(f"Error updating task status for {task_id}: {e}")
    
    async def _handle_task_failure(self, task_id: str, task_data: Dict[str, Any], error_message: str):
        """Handle task failure with retry logic"""
        try:
            retry_count = task_data.get("retry_count", 0)
            max_retries = task_data.get("max_retries", 3)
            
            if retry_count < max_retries:
                # Schedule retry
                new_retry_count = retry_count + 1
                delay_minutes = min(2 ** new_retry_count, 30)  # Exponential backoff
                
                from app.domains.seo_article.services.flow_service import get_supabase_client
                supabase = get_supabase_client()
                
                supabase.table("background_tasks").update({
                    "retry_count": new_retry_count,
                    "status": "pending",
                    "scheduled_for": (datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)).isoformat(),
                    "error_message": f"Retry {new_retry_count}/{max_retries}: {error_message}"
                }).eq("id", task_id).execute()
                
                logger.info(f"Scheduled retry {new_retry_count}/{max_retries} for task {task_id} in {delay_minutes} minutes")
                
                # Schedule retry execution
                await asyncio.sleep(delay_minutes * 60)
                await self._execute_task_loop(task_id)
                
            else:
                # Max retries exceeded, mark as permanently failed
                process_id = task_data["process_id"]
                await self.service.persistence_service.update_process_status(
                    process_id, 
                    "error", 
                    metadata={"error_message": f"Task failed after {max_retries} retries: {error_message}"}
                )
                
                await self._update_task_status(task_id, "failed", f"Max retries exceeded: {error_message}")
                
                logger.error(f"Task {task_id} failed permanently after {max_retries} retries")
                
        except Exception as e:
            logger.error(f"Error handling task failure for {task_id}: {e}")
    
    async def pause_generation_process(self, process_id: str, user_id: str) -> bool:
        """Pause a running generation process"""
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            # Update process status to paused
            await self.service.persistence_service.update_process_status(
                process_id=process_id,
                status="paused",
                metadata={
                    "paused_at": datetime.now(timezone.utc).isoformat(),
                    "paused_by": user_id
                }
            )
            
            # Cancel any running background tasks for this process
            supabase.table("background_tasks").update({
                "status": "cancelled"
            }).eq("process_id", process_id).eq("status", "pending").execute()
            
            # Publish pause event
            await self._publish_realtime_event(
                process_id=process_id,
                event_type="generation_paused",
                event_data={
                    "message": "Generation process paused by user",
                    "paused_at": datetime.now(timezone.utc).isoformat()
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error pausing generation process {process_id}: {e}")
            return False
    
    async def cancel_generation_process(self, process_id: str, user_id: str) -> bool:
        """Cancel a generation process"""
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            # Update process status to cancelled
            await self.service.persistence_service.update_process_status(
                process_id=process_id,
                status="cancelled",
                metadata={
                    "cancelled_at": datetime.now(timezone.utc).isoformat(),
                    "cancelled_by": user_id
                }
            )
            
            # Cancel all background tasks for this process
            supabase.table("background_tasks").update({
                "status": "cancelled"
            }).eq("process_id", process_id).in_("status", ["pending", "running"]).execute()
            
            # Publish cancellation event
            await self._publish_realtime_event(
                process_id=process_id,
                event_type="generation_cancelled",
                event_data={
                    "message": "Generation process cancelled by user",
                    "cancelled_at": datetime.now(timezone.utc).isoformat()
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling generation process {process_id}: {e}")
            return False
