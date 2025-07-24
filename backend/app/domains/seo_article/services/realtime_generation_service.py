"""
Realtime Generation Service for SEO Article Generation.

This service handles article generation using Supabase Realtime for progress sync
instead of WebSocket connections. It integrates with Cloud Tasks for background
processing and uses the existing ArticleGenerationService core logic.
"""

import logging
from typing import Dict, Any
from app.domains.seo_article.services.generation_service import ArticleGenerationService
from app.infrastructure.realtime_sync import get_realtime_sync
from app.infrastructure.cloud_tasks import create_step_continuation_task

logger = logging.getLogger(__name__)


class RealtimeGenerationService:
    """Service for managing article generation with Supabase Realtime sync."""
    
    def __init__(self):
        self.generation_service = ArticleGenerationService()
        self.realtime_sync = get_realtime_sync()
    
    async def start_generation_process(
        self,
        process_id: str,
        user_id: str,
        generation_params: Dict[str, Any]
    ) -> bool:
        """
        Start the article generation process.
        
        Args:
            process_id: UUID of the generation process
            user_id: User ID from Clerk
            generation_params: Parameters for article generation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Starting generation process {process_id} for user {user_id}")
            
            # Update process status to running
            self.realtime_sync.update_step_progress(
                process_id=process_id,
                step_name="keyword_analyzing",
                step_display_name="キーワード分析",
                status="in_progress",
                progress_percentage=5,
                message="記事生成を開始しています..."
            )
            
            # Run the keyword analysis step
            await self._execute_keyword_analysis(process_id, user_id, generation_params)
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting generation process {process_id}: {e}")
            
            # Record error in database
            self.realtime_sync.handle_error(
                process_id=process_id,
                error_message=str(e),
                step_name="keyword_analyzing"
            )
            
            return False
    
    async def _execute_keyword_analysis(
        self,
        process_id: str,
        user_id: str,
        generation_params: Dict[str, Any]
    ) -> None:
        """Execute keyword analysis step."""
        try:
            # Update progress
            self.realtime_sync.update_step_progress(
                process_id=process_id,
                step_name="keyword_analyzing",
                step_display_name="キーワード分析中...",
                status="in_progress",
                progress_percentage=10
            )
            
            # Perform keyword analysis using existing service
            initial_keywords = generation_params.get("initial_keywords", [])
            
            # Use the existing keyword analysis logic
            # For now, we'll simulate the process and move to persona generation
            analysis_result = {
                "keywords": initial_keywords,
                "analysis_complete": True,
                "timestamp": "2024-01-01T00:00:00Z"  # This would be real analysis result
            }
            
            # Update progress and move to next step
            self.realtime_sync.update_step_progress(
                process_id=process_id,
                step_name="keyword_analyzing",
                step_display_name="キーワード分析完了",
                status="completed",
                progress_percentage=15,
                step_data=analysis_result
            )
            
            # Schedule next step
            create_step_continuation_task(
                process_id=process_id,
                step_name="persona_generating",
                step_data={"analysis_result": analysis_result},
                delay_seconds=2
            )
            
        except Exception as e:
            logger.error(f"Error in keyword analysis for process {process_id}: {e}")
            raise
    
    async def continue_from_step(
        self,
        process_id: str,
        step_name: str,
        step_data: Dict[str, Any]
    ) -> bool:
        """
        Continue processing from a specific step.
        
        Args:
            process_id: UUID of the generation process
            step_name: Name of the step to continue from
            step_data: Data from the previous step
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Continuing process {process_id} from step {step_name}")
            
            if step_name == "persona_generating":
                await self._execute_persona_generation(process_id, step_data)
            elif step_name == "theme_generating":
                await self._execute_theme_generation(process_id, step_data)
            elif step_name == "research_planning":
                await self._execute_research_planning(process_id, step_data)
            elif step_name == "researching":
                await self._execute_research(process_id, step_data)
            elif step_name == "outline_generating":
                await self._execute_outline_generation(process_id, step_data)
            elif step_name == "writing_sections":
                await self._execute_section_writing(process_id, step_data)
            elif step_name == "editing":
                await self._execute_editing(process_id, step_data)
            else:
                logger.warning(f"Unknown step name: {step_name}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error continuing from step {step_name} for process {process_id}: {e}")
            
            # Record error
            self.realtime_sync.handle_error(
                process_id=process_id,
                error_message=str(e),
                step_name=step_name
            )
            
            return False
    
    async def _execute_persona_generation(
        self,
        process_id: str,
        step_data: Dict[str, Any]
    ) -> None:
        """Execute persona generation step."""
        try:
            # Update progress
            self.realtime_sync.update_step_progress(
                process_id=process_id,
                step_name="persona_generating",
                step_display_name="ペルソナ生成中...",
                status="in_progress",
                progress_percentage=25
            )
            
            # Generate personas (simulated for now)
            personas = [
                {"id": 0, "description": "30代夫婦で子育て中の共働き世帯"},
                {"id": 1, "description": "40代単身者でマンション購入を検討中"},
                {"id": 2, "description": "50代夫婦で老後の住まいを考える世代"}
            ]
            
            # Set user input required
            input_data = {
                "personas": personas,
                "message": "以下のペルソナから選択してください"
            }
            
            self.realtime_sync.set_user_input_required(
                process_id=process_id,
                input_type="select_persona",
                input_data=input_data,
                step_name="persona_generating"
            )
            
        except Exception as e:
            logger.error(f"Error in persona generation for process {process_id}: {e}")
            raise
    
    async def _execute_theme_generation(
        self,
        process_id: str,
        step_data: Dict[str, Any]
    ) -> None:
        """Execute theme generation step."""
        try:
            # Update progress
            self.realtime_sync.update_step_progress(
                process_id=process_id,
                step_name="theme_generating",
                step_display_name="テーマ生成中...",
                status="in_progress",
                progress_percentage=40
            )
            
            # Generate themes (simulated for now)
            themes = [
                {"id": 0, "title": "札幌での注文住宅の魅力", "description": "札幌の特色を活かした住宅設計"},
                {"id": 1, "title": "自然素材を使った家づくり", "description": "健康的で持続可能な住宅"},
                {"id": 2, "title": "冬の暮らしを快適にする住宅設備", "description": "北海道の厳しい冬に対応"}
            ]
            
            # Set user input required
            input_data = {
                "themes": themes,
                "message": "以下のテーマから選択してください"
            }
            
            self.realtime_sync.set_user_input_required(
                process_id=process_id,
                input_type="select_theme",
                input_data=input_data,
                step_name="theme_generating"
            )
            
        except Exception as e:
            logger.error(f"Error in theme generation for process {process_id}: {e}")
            raise
    
    async def _execute_research_planning(
        self,
        process_id: str,
        step_data: Dict[str, Any]
    ) -> None:
        """Execute research planning step."""
        try:
            # Update progress
            self.realtime_sync.update_step_progress(
                process_id=process_id,
                step_name="research_planning",
                step_display_name="リサーチ計画策定中...",
                status="in_progress",
                progress_percentage=50
            )
            
            # Generate research plan (simulated for now)
            research_plan = {
                "queries": [
                    "札幌 注文住宅 特徴",
                    "北海道 住宅 断熱性能",
                    "札幌 工務店 評判"
                ],
                "focus_areas": ["断熱性能", "デザイン", "価格"],
                "expected_sources": 5
            }
            
            # Set user input required
            input_data = {
                "plan": research_plan,
                "message": "リサーチ計画を確認してください"
            }
            
            self.realtime_sync.set_user_input_required(
                process_id=process_id,
                input_type="approve_plan",
                input_data=input_data,
                step_name="research_planning"
            )
            
        except Exception as e:
            logger.error(f"Error in research planning for process {process_id}: {e}")
            raise
    
    async def _execute_research(
        self,
        process_id: str,
        step_data: Dict[str, Any]
    ) -> None:
        """Execute research step."""
        try:
            # Update progress
            self.realtime_sync.update_step_progress(
                process_id=process_id,
                step_name="researching",
                step_display_name="リサーチ実行中...",
                status="in_progress",
                progress_percentage=60
            )
            
            # Simulate research execution
            queries = step_data.get("research_plan", {}).get("queries", [])
            
            for i, query in enumerate(queries):
                # Update research progress
                self.realtime_sync.update_research_progress(
                    process_id=process_id,
                    current_query=i + 1,
                    total_queries=len(queries),
                    query=query
                )
                
                # Simulate research delay
                import asyncio
                await asyncio.sleep(2)
            
            # Complete research step
            research_results = {
                "queries_completed": len(queries),
                "sources_found": 15,
                "summary": "リサーチが完了しました"
            }
            
            self.realtime_sync.update_step_progress(
                process_id=process_id,
                step_name="researching",
                step_display_name="リサーチ完了",
                status="completed",
                progress_percentage=70,
                step_data=research_results
            )
            
            # Schedule next step
            create_step_continuation_task(
                process_id=process_id,
                step_name="outline_generating",
                step_data={"research_results": research_results},
                delay_seconds=2
            )
            
        except Exception as e:
            logger.error(f"Error in research for process {process_id}: {e}")
            raise
    
    async def _execute_outline_generation(
        self,
        process_id: str,
        step_data: Dict[str, Any]
    ) -> None:
        """Execute outline generation step."""
        try:
            # Update progress
            self.realtime_sync.update_step_progress(
                process_id=process_id,
                step_name="outline_generating",
                step_display_name="アウトライン生成中...",
                status="in_progress",
                progress_percentage=75
            )
            
            # Generate outline (simulated)
            outline = {
                "sections": [
                    {"heading": "札幌の注文住宅の特徴", "description": "札幌ならではの住宅事情"},
                    {"heading": "断熱性能の重要性", "description": "北海道の気候に対応した断熱"},
                    {"heading": "おすすめの工務店選び", "description": "信頼できる工務店の見つけ方"}
                ]
            }
            
            # Set user input required
            input_data = {
                "outline": outline,
                "message": "アウトラインを確認してください"
            }
            
            self.realtime_sync.set_user_input_required(
                process_id=process_id,
                input_type="approve_outline",
                input_data=input_data,
                step_name="outline_generating"
            )
            
        except Exception as e:
            logger.error(f"Error in outline generation for process {process_id}: {e}")
            raise
    
    async def _execute_section_writing(
        self,
        process_id: str,
        step_data: Dict[str, Any]
    ) -> None:
        """Execute section writing step."""
        try:
            # Update progress
            self.realtime_sync.update_step_progress(
                process_id=process_id,
                step_name="writing_sections",
                step_display_name="記事執筆中...",
                status="in_progress",
                progress_percentage=80
            )
            
            # Get outline from step data
            outline = step_data.get("outline", {})
            sections = outline.get("sections", [])
            
            for i, section in enumerate(sections):
                heading = section["heading"]
                
                # Update section progress
                self.realtime_sync.update_section_writing_progress(
                    process_id=process_id,
                    current_section=i + 1,
                    total_sections=len(sections),
                    section_heading=heading
                )
                
                # Simulate section writing with streaming
                content_chunks = [
                    f"<h2>{heading}</h2>",
                    f"<p>{section['description']}に関する詳細な内容をここに記載します。</p>",
                    "<p>追加の説明文がここに続きます。</p>"
                ]
                
                for chunk in content_chunks:
                    self.realtime_sync.update_section_writing_progress(
                        process_id=process_id,
                        current_section=i + 1,
                        total_sections=len(sections),
                        section_heading=heading,
                        html_content_chunk=chunk
                    )
                    
                    # Simulate writing delay
                    import asyncio
                    await asyncio.sleep(1)
                
                # Mark section as complete
                self.realtime_sync.update_section_writing_progress(
                    process_id=process_id,
                    current_section=i + 1,
                    total_sections=len(sections),
                    section_heading=heading,
                    is_complete=True
                )
            
            # Complete writing step
            self.realtime_sync.update_step_progress(
                process_id=process_id,
                step_name="writing_sections",
                step_display_name="記事執筆完了",
                status="completed",
                progress_percentage=90
            )
            
            # Schedule editing step
            create_step_continuation_task(
                process_id=process_id,
                step_name="editing",
                step_data={"sections_complete": True},
                delay_seconds=2
            )
            
        except Exception as e:
            logger.error(f"Error in section writing for process {process_id}: {e}")
            raise
    
    async def _execute_editing(
        self,
        process_id: str,
        step_data: Dict[str, Any]
    ) -> None:
        """Execute editing step."""
        try:
            # Update progress
            self.realtime_sync.update_step_progress(
                process_id=process_id,
                step_name="editing",
                step_display_name="編集・校正中...",
                status="in_progress",
                progress_percentage=95
            )
            
            # Simulate editing process
            import asyncio
            await asyncio.sleep(3)
            
            # Complete the entire process
            article_id = f"article_{process_id}"
            final_content = "<article><h1>札幌での注文住宅完全ガイド</h1><p>記事の完成版がここに表示されます。</p></article>"
            title = "札幌での注文住宅完全ガイド"
            
            self.realtime_sync.complete_process(
                process_id=process_id,
                article_id=article_id,
                final_html_content=final_content,
                title=title
            )
            
        except Exception as e:
            logger.error(f"Error in editing for process {process_id}: {e}")
            raise
    
    async def handle_user_input(
        self,
        process_id: str,
        input_type: str,
        user_response: Dict[str, Any]
    ) -> bool:
        """
        Handle user input and continue the process.
        
        Args:
            process_id: UUID of the generation process
            input_type: Type of input required
            user_response: User's response data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Handling user input for process {process_id}: {input_type}")
            
            # Clear waiting for input state
            from app.common.database import supabase
            supabase.from_("generated_articles_state").update({
                "is_waiting_for_input": False,
                "input_type": None
            }).eq("id", process_id).execute()
            
            # Determine next step based on input type
            next_step_data = {"user_response": user_response}
            
            if input_type == "select_persona":
                next_step = "theme_generating"
                next_step_data["selected_persona"] = user_response.get("payload", {})
            elif input_type == "select_theme":
                next_step = "research_planning"
                next_step_data["selected_theme"] = user_response.get("payload", {})
            elif input_type == "approve_plan":
                next_step = "researching"
                next_step_data["research_plan"] = user_response.get("payload", {})
            elif input_type == "approve_outline":
                next_step = "writing_sections"
                next_step_data["outline"] = user_response.get("payload", {})
            else:
                logger.warning(f"Unknown input type: {input_type}")
                return False
            
            # Schedule next step
            create_step_continuation_task(
                process_id=process_id,
                step_name=next_step,
                step_data=next_step_data,
                delay_seconds=1
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling user input for process {process_id}: {e}")
            return False
    
    async def regenerate_current_step(self, process_id: str) -> bool:
        """
        Regenerate the current step.
        
        Args:
            process_id: UUID of the generation process
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current process state
            from app.common.database import supabase
            process_record = supabase.from_("generated_articles_state").select("*").eq("id", process_id).execute()
            
            if not process_record.data:
                return False
            
            process_data = process_record.data[0]
            current_step = process_data.get("current_step")
            
            logger.info(f"Regenerating step {current_step} for process {process_id}")
            
            # Re-execute the current step
            await self.continue_from_step(
                process_id=process_id,
                step_name=current_step,
                step_data={}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error regenerating step for process {process_id}: {e}")
            return False