# -*- coding: utf-8 -*-
import logging
from typing import List, Dict, Any, Optional
from rich.console import Console

# 内部モジュールのインポート
from app.core.config import settings
from app.domains.seo_article.context import ArticleContext

console = Console()
logger = logging.getLogger(__name__)

class ProcessPersistenceService:
    """プロセスの永続化とデータベース操作を担当するクラス"""
    
    def __init__(self, service):
        self.service = service  # ArticleGenerationServiceへの参照

    async def save_context_to_db(self, context: ArticleContext, process_id: Optional[str] = None, user_id: Optional[str] = None, organization_id: Optional[str] = None) -> str:
        """Save ArticleContext to database and return process_id"""
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            from datetime import datetime, timezone
            import json
            supabase = get_supabase_client()
            
            def safe_serialize_value(value):
                """Recursively serialize any object to JSON-serializable format"""
                if value is None:
                    return None
                elif isinstance(value, (str, int, float, bool)):
                    return value
                elif isinstance(value, list):
                    return [safe_serialize_value(item) for item in value]
                elif isinstance(value, dict):
                    return {k: safe_serialize_value(v) for k, v in value.items()}
                elif hasattr(value, "model_dump"):
                    # Pydantic models
                    return value.model_dump()
                elif hasattr(value, "__dict__"):
                    # Regular objects with attributes
                    return {k: safe_serialize_value(v) for k, v in value.__dict__.items()}
                else:
                    # Fallback to string representation
                    return str(value)
            
            # Convert context to dict (excluding WebSocket and asyncio objects)
            context_dict = {}
            for key, value in context.__dict__.items():
                if key not in ["websocket", "user_response_event"]:
                    try:
                        context_dict[key] = safe_serialize_value(value)
                        # デバッグ: image_mode の値をログ出力
                        if key == "image_mode":
                            console.print(f"[cyan]DEBUG: Saving image_mode = {value} (type: {type(value)})[/cyan]")
                    except Exception as e:
                        console.print(f"[yellow]Warning: Failed to serialize {key}: {e}. Using string representation.[/yellow]")
                        context_dict[key] = str(value)
            
            # Verify JSON serialization works
            try:
                json.dumps(context_dict)
            except Exception as e:
                console.print(f"[red]Error: Context still not JSON serializable after processing: {e}[/red]")
                raise e
            
            # Map current_step to valid generation_status enum values
            def map_step_to_status(step: str) -> str:
                """Map context step to valid generation_status enum value"""
                if step in ["start", "keyword_analyzing", "keyword_analyzed", "persona_generating", 
                           "persona_selected", "theme_generating", "theme_selected", "research_planning", 
                           "research_plan_approved", "researching", "research_synthesizing", 
                           "outline_generating", "writing_sections", "editing"]:
                    return "in_progress"
                elif step == "completed":
                    return "completed"
                elif step == "error":
                    return "error"
                elif step in ["persona_generated", "theme_proposed", "research_plan_generated", 
                             "outline_generated"]:
                    return "user_input_required"
                else:
                    return "in_progress"  # Default fallback
            
            if process_id:
                # Update existing state
                update_data = {
                    "article_context": context_dict,
                    "status": map_step_to_status(context.current_step),
                    "current_step_name": context.current_step,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Add error message if in error state
                if context.current_step == "error" and hasattr(context, 'error_message'):
                    update_data["error_message"] = context.error_message
                    
                # Add style template ID if available
                if context.style_template_id:
                    update_data["style_template_id"] = context.style_template_id
                    
                # Add final article if completed
                if context.current_step == "completed":
                    # Use final_article_html if available, otherwise fallback to full_draft_html
                    final_content = getattr(context, 'final_article_html', None) or getattr(context, 'full_draft_html', None)
                    
                    if final_content:
                        article_data = {
                            "user_id": user_id,
                            "organization_id": organization_id,
                            "generation_process_id": process_id,
                            "title": context.generated_outline.title if context.generated_outline else "Generated Article",
                            "content": final_content,
                            "keywords": context.initial_keywords,
                            "target_audience": context.selected_detailed_persona,
                            "status": "completed"
                        }
                    else:
                        # If no content available, combine generated sections as fallback
                        fallback_content = '\n\n'.join(context.generated_sections_html) if hasattr(context, 'generated_sections_html') and context.generated_sections_html else ""
                        if fallback_content:
                            article_data = {
                                "user_id": user_id,
                                "organization_id": organization_id,
                                "generation_process_id": process_id,
                                "title": context.generated_outline.title if context.generated_outline else "Generated Article",
                                "content": fallback_content,
                                "keywords": context.initial_keywords,
                                "target_audience": context.selected_detailed_persona,
                                "status": "completed"
                            }
                        else:
                            # No content available at all, skip article save
                            article_data = None
                            console.print(f"[yellow]Warning: No content available for process {process_id}, skipping article save[/yellow]")
                    
                    if article_data:
                        try:
                            # 手動でのチェック・挿入・更新（UPSERT制約に依存しない）
                            console.print(f"[cyan]Saving final article for process {process_id}[/cyan]")
                            
                            # 既存記事をチェック
                            existing_article = supabase.table("articles").select("id").eq("generation_process_id", process_id).execute()
                            
                            if existing_article.data and len(existing_article.data) > 0:
                                # 既存記事を更新
                                article_id = existing_article.data[0]["id"]
                                console.print(f"[yellow]Updating existing article {article_id}[/yellow]")
                                article_result = supabase.table("articles").update(article_data).eq("id", article_id).execute()
                                
                                if article_result.data:
                                    update_data["article_id"] = article_id
                                    console.print(f"[green]Successfully updated article {article_id} for process {process_id}[/green]")
                                else:
                                    console.print(f"[red]Failed to update article {article_id}: {article_result}[/red]")
                            else:
                                # 新規記事を作成
                                console.print(f"[yellow]Creating new article for process {process_id}[/yellow]")
                                article_result = supabase.table("articles").insert(article_data).execute()
                                
                                if article_result.data:
                                    article_id = article_result.data[0]["id"]
                                    update_data["article_id"] = article_id
                                    console.print(f"[green]Successfully created article {article_id} for process {process_id}[/green]")
                                else:
                                    console.print(f"[red]Failed to create article: {article_result}[/red]")
                                
                        except Exception as article_save_error:
                            console.print(f"[red]Error saving article for process {process_id}: {article_save_error}[/red]")
                            # 最後の試み: 強制的に挿入
                            try:
                                console.print(f"[yellow]Attempting force insert for process {process_id}[/yellow]")
                                article_result = supabase.table("articles").insert(article_data).execute()
                                if article_result.data:
                                    article_id = article_result.data[0]["id"]
                                    update_data["article_id"] = article_id
                                    console.print(f"[green]Force insert successful: {article_id}[/green]")
                            except Exception as fallback_error:
                                console.print(f"[red]Fallback article save also failed: {fallback_error}[/red]")
                
                supabase.table("generated_articles_state").update(update_data).eq("id", process_id).execute()
                return process_id
            else:
                # Get default flow ID for new states
                flow_result = supabase.table("article_generation_flows").select("id").eq("name", "Default SEO Article Generation").eq("is_template", True).execute()
                
                if not flow_result.data:
                    raise Exception("Default flow template not found")
                
                default_flow_id = flow_result.data[0]["id"]
                
                # Create new state
                state_data = {
                    "flow_id": default_flow_id,
                    "user_id": user_id,
                    "organization_id": organization_id,
                    "status": map_step_to_status(context.current_step),
                    "article_context": context_dict,
                    "generated_content": {},
                    "style_template_id": context.style_template_id  # Add style template ID to dedicated column
                }
                
                result = supabase.table("generated_articles_state").insert(state_data).execute()
                if result.data:
                    return result.data[0]["id"]
                else:
                    raise Exception("Failed to create generation state")
            
        except Exception as e:
            logger.error(f"Error saving context to database: {e}")
            raise

    async def load_context_from_db(self, process_id: str, user_id: str) -> Optional[ArticleContext]:
        """Load context from database for process persistence"""
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            from app.domains.seo_article.schemas import AgeGroup, PersonaType
            supabase = get_supabase_client()
            
            # Get the process state with user access control
            result = supabase.table("generated_articles_state").select("*").eq("id", process_id).eq("user_id", user_id).execute()
            
            if not result.data:
                logger.warning(f"Process {process_id} not found for user {user_id}")
                return None
            
            state = result.data[0]
            context_dict = state.get("article_context", {})
            
            # デバッグ: image_mode の値をログ出力
            console.print(f"[cyan]DEBUG: Loading image_mode from DB = {context_dict.get('image_mode')} (type: {type(context_dict.get('image_mode'))})[/cyan]")
            console.print(f"[cyan]DEBUG: Full context_dict keys = {list(context_dict.keys())}[/cyan]")
            
            if not context_dict:
                logger.warning(f"No context data found for process {process_id}")
                return None
            
            # Helper function to safely convert string to enum
            def safe_convert_enum(value, enum_class):
                if value is None:
                    return None
                try:
                    if isinstance(value, str):
                        # Try to find enum by value
                        for enum_item in enum_class:
                            if enum_item.value == value:
                                return enum_item
                        # If not found, try direct conversion
                        return enum_class(value)
                    return value  # Already an enum or valid type
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to convert {value} to {enum_class.__name__}: {e}")
                    return None
            
            # Convert enum fields back from strings
            target_age_group = safe_convert_enum(context_dict.get("target_age_group"), AgeGroup)
            persona_type = safe_convert_enum(context_dict.get("persona_type"), PersonaType)
            
            # Reconstruct ArticleContext from stored data
            raw_outline_level = context_dict.get("outline_top_level_heading", 2)
            try:
                outline_top_level = int(raw_outline_level)
            except (TypeError, ValueError):
                outline_top_level = 2
            if outline_top_level not in (2, 3):
                outline_top_level = 2

            context = ArticleContext(
                initial_keywords=context_dict.get("initial_keywords", []),
                target_age_group=target_age_group,
                persona_type=persona_type,
                custom_persona=context_dict.get("custom_persona"),
                target_length=context_dict.get("target_length"),
                num_theme_proposals=context_dict.get("num_theme_proposals", 3),
                num_research_queries=context_dict.get("num_research_queries", 3),
                num_persona_examples=context_dict.get("num_persona_examples", 3),
                company_name=context_dict.get("company_name"),
                company_description=context_dict.get("company_description"),
                company_style_guide=context_dict.get("company_style_guide"),
                # Extended company info
                company_website_url=context_dict.get("company_website_url"),
                company_usp=context_dict.get("company_usp"),
                company_target_persona=context_dict.get("company_target_persona"),
                company_brand_slogan=context_dict.get("company_brand_slogan"),
                company_target_keywords=context_dict.get("company_target_keywords"),
                company_industry_terms=context_dict.get("company_industry_terms"),
                company_avoid_terms=context_dict.get("company_avoid_terms"),
                company_popular_articles=context_dict.get("company_popular_articles"),
                company_target_area=context_dict.get("company_target_area"),
                past_articles_summary=context_dict.get("past_articles_summary"),
                # 画像モード関連の復元
                image_mode=context_dict.get("image_mode", False),
                image_settings=context_dict.get("image_settings", {}),
                # スタイルテンプレート関連の復元
                style_template_id=context_dict.get("style_template_id"),
                style_template_settings=context_dict.get("style_template_settings", {}),
                # SerpAPI設定の復元
                has_serp_api_key=context_dict.get("has_serp_api_key", bool(settings.serpapi_key)),
                # アウトラインモード設定
                advanced_outline_mode=context_dict.get("advanced_outline_mode", False),
                outline_top_level_heading=outline_top_level,
                websocket=None,  # Will be set when WebSocket connects
                user_response_event=None,  # Will be set when WebSocket connects
                user_id=user_id  # Set user_id from method parameter
            )
            
            # Restore other context state
            context.current_step = context_dict.get("current_step", "start")
            context.generated_detailed_personas = context_dict.get("generated_detailed_personas", [])
            context.selected_detailed_persona = context_dict.get("selected_detailed_persona")
            
            # Restore complex objects with error handling
            try:
                await self.restore_complex_objects(context, context_dict)
            except Exception as e:
                logger.warning(f"Error restoring complex objects for process {process_id}: {e}")
            
            # Restore other state
            context.research_query_results = context_dict.get("research_query_results", [])
            context.current_research_query_index = context_dict.get("current_research_query_index", 0)
            context.generated_sections_html = context_dict.get("generated_sections_html", [])
            context.current_section_index = context_dict.get("current_section_index", 0)
            context.full_draft_html = context_dict.get("full_draft_html")
            context.final_article_html = context_dict.get("final_article_html")
            context.section_writer_history = context_dict.get("section_writer_history", [])
            # Restore conversation continuity fields (optional)
            try:
                context.responses_conversation_id = context_dict.get("responses_conversation_id")
                context.last_response_id = context_dict.get("last_response_id")
            except Exception:
                pass
            context.expected_user_input = context_dict.get("expected_user_input")
            
            # Safety net: If style_template_id exists but style_template_settings is empty, hydrate from database
            if context.style_template_id and not context.style_template_settings:
                try:
                    logger.info(f"🔄 [LOAD_CONTEXT] Auto-hydrating style template {context.style_template_id}")
                    res = supabase.table("style_guide_templates")\
                        .select("settings")\
                        .eq("id", context.style_template_id)\
                        .single()\
                        .execute()
                    if res.data and res.data.get("settings"):
                        context.style_template_settings = res.data["settings"]
                        logger.info(f"✅ [LOAD_CONTEXT] Auto-hydrated style template settings: {list(context.style_template_settings.keys())}")
                except Exception as e:
                    logger.warning(f"⚠️ [LOAD_CONTEXT] Failed to auto-hydrate style settings for {context.style_template_id}: {e}")

            # Auto-hydrate missing company info fields from default company_info
            try:
                missing_company_core = not (getattr(context, 'company_name', None) and getattr(context, 'company_description', None))
                missing_extended = not any([
                    getattr(context, 'company_website_url', None), getattr(context, 'company_usp', None), getattr(context, 'company_target_persona', None),
                    getattr(context, 'company_brand_slogan', None), getattr(context, 'company_target_keywords', None), getattr(context, 'company_industry_terms', None),
                    getattr(context, 'company_avoid_terms', None), getattr(context, 'company_popular_articles', None), getattr(context, 'company_target_area', None)
                ])
                if missing_company_core or missing_extended:
                    console.print("[cyan]DEBUG: Attempting company_info auto-hydration (missing fields detected)\n[/cyan]")
                    c_res = supabase.table("company_info").select("*").eq("user_id", user_id).eq("is_default", True).single().execute()
                    if c_res.data:
                        ci = c_res.data
                        context.company_name = context.company_name or ci.get("name")
                        context.company_description = context.company_description or ci.get("description")
                        context.company_website_url = context.company_website_url or ci.get("website_url")
                        context.company_usp = context.company_usp or ci.get("usp")
                        context.company_target_persona = context.company_target_persona or ci.get("target_persona")
                        context.company_brand_slogan = context.company_brand_slogan or ci.get("brand_slogan")
                        context.company_target_keywords = context.company_target_keywords or ci.get("target_keywords")
                        context.company_industry_terms = context.company_industry_terms or ci.get("industry_terms")
                        context.company_avoid_terms = context.company_avoid_terms or ci.get("avoid_terms")
                        context.company_popular_articles = context.company_popular_articles or ci.get("popular_articles")
                        context.company_target_area = context.company_target_area or ci.get("target_area")
                        logger.info("[LOAD_CONTEXT] Auto-hydrated default company_info into context (including target_area)")
            except Exception as e:
                logger.warning(f"[LOAD_CONTEXT] company_info auto-hydration failed: {e}")

            logger.info(f"Successfully loaded context for process {process_id} from step {context.current_step}")
            return context
            
        except Exception as e:
            logger.error(f"Error loading context from database for process {process_id}: {e}")
            return None

    async def restore_complex_objects(self, context: ArticleContext, context_dict: Dict[str, Any]):
        """Restore complex objects from context dictionary"""
        if context_dict.get("selected_theme"):
            from app.domains.seo_article.schemas import ThemeProposalData
            context.selected_theme = ThemeProposalData(**context_dict["selected_theme"])
        
        if context_dict.get("generated_themes"):
            from app.domains.seo_article.schemas import ThemeProposalData
            context.generated_themes = [ThemeProposalData(**theme_data) for theme_data in context_dict["generated_themes"]]
            
        if context_dict.get("research_plan"):
            from app.domains.seo_article.schemas import ResearchPlan
            context.research_plan = ResearchPlan(**context_dict["research_plan"])
            
        if context_dict.get("research_report"):
            from app.domains.seo_article.schemas import ResearchReport
            context.research_report = ResearchReport(**context_dict["research_report"])
            
        if context_dict.get("generated_outline"):
            from app.domains.seo_article.schemas import Outline
            context.generated_outline = Outline(**context_dict["generated_outline"])
            
        if context_dict.get("serp_analysis_report"):
            from app.domains.seo_article.schemas import SerpKeywordAnalysisReport
            context.serp_analysis_report = SerpKeywordAnalysisReport(**context_dict["serp_analysis_report"])

    async def get_generation_process_state(self, process_id: str, user_id: str, user_jwt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get generation process state from database"""
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            # Get the process state with user access control
            logger.info(f"🔍 [DB_ACCESS] Looking for process {process_id} with user_id: {user_id}")
            result = supabase.table("generated_articles_state").select("*").eq("id", process_id).eq("user_id", user_id).execute()
            
            if not result.data:
                logger.warning(f"🚫 [DB_ACCESS] Process {process_id} not found for user {user_id}")
                # Additional debug: check if process exists with any user
                all_result = supabase.table("generated_articles_state").select("id, user_id").eq("id", process_id).execute()
                if all_result.data:
                    existing_user = all_result.data[0].get("user_id")
                    logger.warning(f"🔍 [DB_ACCESS] Process {process_id} EXISTS but with different user_id: {existing_user} (expected: {user_id})")
                else:
                    logger.warning(f"🔍 [DB_ACCESS] Process {process_id} does NOT exist in database at all")
                return None
            
            state = result.data[0]
            context_dict = state.get("article_context", {})
            
            # デバッグ: image_mode の値をログ出力 (get_generation_process_state)
            console.print(f"[magenta]DEBUG (get_generation_process_state): image_mode from DB = {context_dict.get('image_mode')} (type: {type(context_dict.get('image_mode'))})[/magenta]")
            
            # Return a formatted response that matches frontend expectations
            return {
                "id": state["id"],
                "flow_id": state.get("flow_id"),
                "user_id": state["user_id"],
                "organization_id": state.get("organization_id"),
                "current_step_id": state.get("current_step_id"),
                "current_step_name": context_dict.get("current_step", "start"),
                "status": state.get("status", "in_progress"),
                "article_context": context_dict,
                "generated_content": state.get("generated_content", {}),
                "article_id": state.get("article_id"),
                "error_message": state.get("error_message"),
                "is_waiting_for_input": context_dict.get("current_step") in ["persona_generated", "theme_proposed", "research_plan_generated", "outline_generated"],
                "input_type": self.get_input_type_for_step(context_dict.get("current_step")),
                # 画像モード関連情報を含める
                "image_mode": context_dict.get("image_mode", False),
                "image_settings": context_dict.get("image_settings", {}),
                "image_placeholders": context_dict.get("image_placeholders", []),
                "created_at": state.get("created_at"),
                "updated_at": state.get("updated_at")
            }
            
        except Exception as e:
            logger.error(f"Error getting generation process state: {e}")
            raise

    def get_input_type_for_step(self, step: str) -> Optional[str]:
        """Get expected input type for a given step"""
        step_input_map = {
            "persona_generated": "select_persona",
            "theme_proposed": "select_theme", 
            "research_plan_generated": "approve_plan",
            "outline_generated": "approve_outline"
        }
        return step_input_map.get(step)

    async def get_user_articles(
        self, 
        user_id: str, 
        status_filter: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get articles for a specific user.
        
        Args:
            user_id: User ID to filter articles
            status_filter: Optional status filter ('completed', 'in_progress', etc.)
            limit: Maximum number of articles to return
            offset: Number of articles to skip for pagination
            
        Returns:
            List of article dictionaries with basic information
        """
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            # Query for articles created by the user
            query = supabase.table("articles").select(
                "id, title, content, keywords, target_audience, status, created_at, updated_at"
            ).eq("user_id", user_id)
            
            # Apply status filter if provided
            if status_filter:
                query = query.eq("status", status_filter)
            
            # Apply pagination
            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
            
            result = query.execute()
            
            articles = []
            for article in result.data:
                # Extract short description from content (first 150 characters)
                content = article.get("content", "")
                # Strip HTML tags for short description
                import re
                plain_text = re.sub(r'<[^>]+>', '', content)
                short_description = plain_text[:150] + "..." if len(plain_text) > 150 else plain_text
                
                articles.append({
                    "id": article["id"],
                    "title": article["title"],
                    "shortdescription": short_description,
                    "postdate": article["created_at"].split("T")[0] if article["created_at"] else None,
                    "status": article["status"],
                    "keywords": article.get("keywords", []),
                    "target_audience": article.get("target_audience"),
                    "updated_at": article["updated_at"]
                })
            
            return articles
            
        except Exception as e:
            logger.error(f"Error retrieving articles for user {user_id}: {e}")
            raise
    
    async def get_article(self, article_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed article information by ID.
        
        Args:
            article_id: Article ID
            user_id: User ID for access control
            
        Returns:
            Article dictionary with detailed information or None if not found
        """
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            # Query for article with user access control
            result = supabase.table("articles").select("*").eq("id", article_id).eq("user_id", user_id).execute()
            
            # If no direct match, check if this might be a generation_process_id
            if not result.data:
                # Try to find by generation_process_id (in case user is using wrong ID)
                process_result = supabase.table("articles").select("*").eq("generation_process_id", article_id).eq("user_id", user_id).order("updated_at", desc=True).execute()
                if process_result.data:
                    result = process_result
            
            if not result.data:
                return None
            
            # If multiple articles exist for the same generation_process_id (shouldn't happen with constraint),
            # select the one with the most content
            articles = result.data
            if len(articles) > 1:
                logger.warning(f"Multiple articles found for ID {article_id}, selecting the most complete one")
                articles.sort(key=lambda x: (len(x.get("content", "")), x.get("updated_at", "")), reverse=True)
            
            article = articles[0]
            
            # Extract short description from content
            content = article.get("content", "")
            import re
            plain_text = re.sub(r'<[^>]+>', '', content)
            short_description = plain_text[:300] + "..." if len(plain_text) > 300 else plain_text
            
            return {
                "id": article["id"],
                "title": article["title"],
                "content": article["content"],
                "shortdescription": short_description,
                "postdate": article["created_at"].split("T")[0] if article["created_at"] else None,
                "status": article["status"],
                "keywords": article.get("keywords", []),
                "target_audience": article.get("target_audience"),
                "created_at": article["created_at"],
                "updated_at": article["updated_at"],
                "generation_process_id": article.get("generation_process_id")
            }
            
        except Exception as e:
            logger.error(f"Error retrieving article {article_id}: {e}")
            raise

    async def get_all_user_processes(
        self, 
        user_id: str, 
        status_filter: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all processes (completed articles + in-progress/failed generation processes) for a user.
        
        Args:
            user_id: User ID to filter processes
            status_filter: Optional status filter ('completed', 'in_progress', 'error', etc.)
            limit: Maximum number of items to return
            offset: Number of items to skip for pagination
            
        Returns:
            List of unified process dictionaries (articles + generation processes)
        """
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            import re
            supabase = get_supabase_client()
            
            all_processes = []
            
            # 1. Get completed articles
            articles_query = supabase.table("articles").select(
                "id, title, content, keywords, target_audience, status, created_at, updated_at, generation_process_id"
            ).eq("user_id", user_id)
            
            if status_filter and status_filter == "completed":
                articles_query = articles_query.eq("status", "completed")
            
            articles_result = articles_query.order("created_at", desc=True).execute()
            
            for article in articles_result.data:
                # Extract short description from content
                content = article.get("content", "")
                plain_text = re.sub(r'<[^>]+>', '', content)
                short_description = plain_text[:150] + "..." if len(plain_text) > 150 else plain_text
                
                all_processes.append({
                    "id": article["id"],
                    "process_id": article.get("generation_process_id"),
                    "title": article["title"],
                    "shortdescription": short_description,
                    "postdate": article["created_at"].split("T")[0] if article["created_at"] else None,
                    "status": "completed",  # Articles are always completed
                    "process_type": "article",
                    "keywords": article.get("keywords", []),
                    "target_audience": article.get("target_audience"),
                    "updated_at": article["updated_at"],
                    "can_resume": False,
                    "is_recoverable": False
                })
            
            # Collect generation_process_ids from articles to avoid duplication
            existing_process_ids = set()
            for article in articles_result.data:
                if article.get("generation_process_id"):
                    existing_process_ids.add(article["generation_process_id"])

            # 2. Get generation processes (including incomplete ones)
            processes_query = supabase.table("generated_articles_state").select(
                "id, status, article_context, current_step_name, progress_percentage, is_waiting_for_input, created_at, updated_at, error_message"
            ).eq("user_id", user_id)
            
            # Only get non-completed processes (since completed ones have articles)
            # Also exclude processes that already have corresponding articles
            processes_query = processes_query.neq("status", "completed")
            
            if status_filter and status_filter != "completed":
                processes_query = processes_query.eq("status", status_filter)
            
            processes_result = processes_query.order("updated_at", desc=True).execute()
            
            for process in processes_result.data:
                # Skip processes that already have corresponding articles
                if process["id"] in existing_process_ids:
                    continue
                    
                # Skip completed processes (they should have articles)
                if process["status"] == "completed":
                    continue
                    
                context = process.get("article_context", {})
                keywords = context.get("initial_keywords", [])
                
                # Generate title from keywords or step
                if keywords:
                    title = f"SEO記事: {', '.join(keywords[:3])}"
                else:
                    title = f"記事生成プロセス (ID: {process['id'][:8]}...)"
                
                # Generate description based on current step
                current_step = process.get("current_step_name", "start")
                step_descriptions = {
                    "start": "生成開始",
                    "keyword_analyzing": "キーワード分析中",
                    "persona_generating": "ペルソナ生成中",
                    "theme_generating": "テーマ生成中",
                    "theme_proposed": "テーマ選択待ち",
                    "research_planning": "リサーチ計画策定中",
                    "research_plan_generated": "リサーチ計画承認待ち",
                    "researching": "リサーチ実行中",
                    "outline_generating": "アウトライン生成中",
                    "outline_generated": "アウトライン承認待ち",
                    "writing_sections": "記事執筆中",
                    "editing": "編集中",
                    "error": "エラーが発生しました"
                }
                description = step_descriptions.get(current_step, f"ステップ: {current_step}")
                
                # Determine if process is recoverable
                is_recoverable = process["status"] in ["user_input_required", "paused", "error"]
                can_resume = is_recoverable and process.get("is_waiting_for_input", False)
                
                all_processes.append({
                    "id": process["id"],
                    "process_id": process["id"],
                    "title": title,
                    "shortdescription": description,
                    "postdate": process["created_at"].split("T")[0] if process["created_at"] else None,
                    "status": process["status"],
                    "process_type": "generation",
                    "keywords": keywords,
                    "target_audience": context.get("custom_persona") or context.get("persona_type"),
                    "updated_at": process["updated_at"],
                    "current_step": current_step,
                    "progress_percentage": process.get("progress_percentage", 0),
                    "can_resume": can_resume,
                    "is_recoverable": is_recoverable,
                    "error_message": process.get("error_message")
                })
            
            # 3. Sort all processes by updated_at (most recent first)
            all_processes.sort(key=lambda x: x["updated_at"] or "", reverse=True)
            
            # 4. Apply pagination
            paginated_processes = all_processes[offset:offset + limit]
            
            return paginated_processes
            
        except Exception as e:
            logger.error(f"Error retrieving all processes for user {user_id}: {e}")
            raise

    async def get_recoverable_processes(self, user_id: str, limit: int = 10) -> List[dict]:
        """
        Get processes that can be recovered/resumed for a user.
        
        Args:
            user_id: User ID to filter processes
            limit: Maximum number of recoverable processes to return
            
        Returns:
            List of recoverable process dictionaries with recovery metadata
        """
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            from datetime import datetime, timezone
            supabase = get_supabase_client()
            
            # Define recoverable statuses
            recoverable_statuses = ['user_input_required', 'paused', 'error', 'resuming', 'auto_progressing']
            
            # Query for recoverable processes
            query = supabase.table("generated_articles_state").select(
                "id, status, article_context, current_step_name, progress_percentage, "
                "is_waiting_for_input, created_at, updated_at, error_message, last_activity_at"
            ).eq("user_id", user_id).in_("status", recoverable_statuses)
            
            result = query.order("updated_at", desc=True).limit(limit).execute()
            
            recoverable_processes = []
            current_time = datetime.now(timezone.utc)
            
            for process in result.data:
                context = process.get("article_context", {})
                keywords = context.get("initial_keywords", [])
                current_step = process.get("current_step_name", "start")
                status = process["status"]
                updated_at = process.get("updated_at")
                
                # Calculate time since last activity
                time_since_activity = None
                if updated_at:
                    try:
                        last_activity = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        time_since_activity = int((current_time - last_activity).total_seconds())
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error parsing updated_at for process {process['id']}: {e}")
                        time_since_activity = None
                
                # Determine recovery metadata
                recovery_metadata = self.get_recovery_metadata(status, current_step, process)
                
                # Generate title from keywords or context
                if keywords:
                    title = f"SEO記事: {', '.join(keywords[:3])}"
                elif context.get("title"):
                    title = context["title"]
                else:
                    title = f"記事生成プロセス (ID: {process['id'][:8]}...)"
                
                # Get step description
                step_descriptions = {
                    "start": "生成開始",
                    "keyword_analyzing": "キーワード分析中",
                    "persona_generating": "ペルソナ生成中",
                    "theme_generating": "テーマ生成中",
                    "theme_proposed": "テーマ選択待ち",
                    "research_planning": "リサーチ計画策定中",
                    "research_plan_generated": "リサーチ計画承認待ち",
                    "researching": "リサーチ実行中",
                    "outline_generating": "アウトライン生成中",
                    "outline_generated": "アウトライン承認待ち",
                    "writing_sections": "記事執筆中",
                    "editing": "編集中",
                    "error": "エラーが発生しました"
                }
                description = step_descriptions.get(current_step, f"ステップ: {current_step}")
                
                process_data = {
                    "id": process["id"],
                    "process_id": process["id"],
                    "title": title,
                    "description": description,
                    "status": status,
                    "current_step": current_step,
                    "progress_percentage": process.get("progress_percentage", 0),
                    "keywords": keywords,
                    "target_audience": context.get("custom_persona") or context.get("persona_type"),
                    "created_at": process["created_at"],
                    "updated_at": updated_at,
                    "time_since_last_activity": time_since_activity,
                    "error_message": process.get("error_message"),
                    
                    # Recovery metadata
                    "resume_step": recovery_metadata["resume_step"],
                    "auto_resume_possible": recovery_metadata["auto_resume_possible"],
                    "recovery_notes": recovery_metadata["recovery_notes"],
                    "requires_user_input": recovery_metadata["requires_user_input"]
                }
                
                recoverable_processes.append(process_data)
            
            return recoverable_processes
            
        except Exception as e:
            logger.error(f"Error retrieving recoverable processes for user {user_id}: {e}")
            raise
    
    def get_recovery_metadata(self, status: str, current_step: str, process: dict) -> dict:
        """
        Generate recovery metadata for a process based on its current state.
        
        Args:
            status: Current process status
            current_step: Current step name
            process: Full process data
            
        Returns:
            Dictionary containing recovery metadata
        """
        metadata = {
            "resume_step": current_step,
            "auto_resume_possible": False,
            "recovery_notes": "",
            "requires_user_input": False
        }
        
        try:
            if status == "paused":
                # Paused processes can usually auto-resume from current step
                metadata["auto_resume_possible"] = True
                metadata["recovery_notes"] = "一時停止中です。自動復旧可能です。"
                
            elif status == "user_input_required":
                # User input required - cannot auto-resume
                metadata["auto_resume_possible"] = False
                metadata["requires_user_input"] = True
                
                # Determine what type of input is needed based on current step
                if current_step == "theme_proposed":
                    metadata["recovery_notes"] = "テーマの選択が必要です。"
                elif current_step == "research_plan_generated":
                    metadata["recovery_notes"] = "リサーチ計画の承認が必要です。"
                elif current_step == "outline_generated":
                    metadata["recovery_notes"] = "アウトラインの承認が必要です。"
                else:
                    metadata["recovery_notes"] = "ユーザーの入力が必要です。"
                    
            elif status == "in_progress":
                # In-progress processes might be resumable depending on step
                if current_step in ["researching", "writing_sections", "editing"]:
                    metadata["auto_resume_possible"] = True
                    metadata["recovery_notes"] = "処理が中断されました。自動復旧可能です。"
                else:
                    metadata["auto_resume_possible"] = False
                    metadata["recovery_notes"] = "処理が中断されました。手動での確認が必要です。"
                    
            elif status == "error":
                # Error processes need manual intervention
                metadata["auto_resume_possible"] = False
                error_message = process.get("error_message", "")
                
                # Try to provide more specific recovery guidance based on error
                if "connection" in error_message.lower():
                    metadata["recovery_notes"] = "接続エラーが発生しました。再試行可能です。"
                    metadata["auto_resume_possible"] = True
                elif "timeout" in error_message.lower():
                    metadata["recovery_notes"] = "タイムアウトエラーが発生しました。再試行可能です。"
                    metadata["auto_resume_possible"] = True
                elif "authentication" in error_message.lower():
                    metadata["recovery_notes"] = "認証エラーが発生しました。設定を確認してください。"
                elif "quota" in error_message.lower() or "limit" in error_message.lower():
                    metadata["recovery_notes"] = "API制限に達しました。時間をおいて再試行してください。"
                else:
                    metadata["recovery_notes"] = f"エラーが発生しました: {error_message[:100]}..."
            
            return metadata
            
        except Exception as e:
            logger.warning(f"Error generating recovery metadata: {e}")
            metadata["recovery_notes"] = "復旧情報の取得中にエラーが発生しました。"
            return metadata

    async def update_article(
        self, 
        article_id: str, 
        user_id: str, 
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        記事を更新します。
        
        Args:
            article_id: 記事ID
            user_id: ユーザーID（アクセス制御用）
            update_data: 更新するデータの辞書
            
        Returns:
            更新された記事の情報
        """
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            from datetime import datetime, timezone
            supabase = get_supabase_client()
            
            # まず記事が存在し、ユーザーがアクセス権限を持つことを確認
            existing_result = supabase.table("articles").select("*").eq("id", article_id).eq("user_id", user_id).execute()
            
            if not existing_result.data:
                raise ValueError("Article not found or access denied")
            
            # 更新データを準備
            update_fields = {}
            allowed_fields = ["title", "content", "shortdescription", "target_audience", "keywords"]
            
            for field, value in update_data.items():
                if field in allowed_fields and value is not None:
                    update_fields[field] = value
            
            # 更新時刻を追加
            update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # 更新が必要なフィールドがない場合
            if not update_fields:
                return await self.get_article(article_id, user_id)
            
            # **重要**: コンテンツの更新で空のimgタグを上書きしないようにチェック
            if "content" in update_fields:
                new_content = update_fields["content"]
                # 空のimgタグを含むコンテンツのチェック
                if "<img />" in new_content or "<img/>" in new_content:
                    existing_article = existing_result.data[0]
                    existing_content = existing_article.get("content", "")
                    
                    # 既存のコンテンツの方が充実している場合は更新しない
                    if len(existing_content) > len(new_content) and "data-image-id" in existing_content:
                        logger.warning(f"Preventing content update with empty img tags for article {article_id}. Existing content is more complete.")
                        del update_fields["content"]
                        
                        # コンテント以外のフィールドだけ更新
                        if len(update_fields) == 1:  # updated_atだけ残っている場合
                            return await self.get_article(article_id, user_id)
            
            # データベースを更新
            logger.info(f"Updating article {article_id} with fields: {list(update_fields.keys())}")
            result = supabase.table("articles").update(update_fields).eq("id", article_id).eq("user_id", user_id).execute()
            
            if not result.data:
                raise Exception(f"Failed to update article {article_id} - no rows affected")
            
            # コンテンツが更新された場合、画像プレースホルダーを抽出・保存
            if "content" in update_fields:
                try:
                    await self.extract_and_save_placeholders(supabase, article_id, update_fields["content"])
                    logger.info(f"Successfully extracted and saved placeholders for article {article_id}")
                except Exception as e:
                    logger.warning(f"Failed to extract image placeholders for article {article_id}: {e}")
            
            # 更新された記事情報を返す
            return await self.get_article(article_id, user_id)
            
        except Exception as e:
            logger.error(f"Error updating article {article_id}: {e}")
            raise

    async def extract_and_save_placeholders(self, supabase, article_id: str, content: str) -> None:
        """
        記事内容から画像プレースホルダーを抽出してデータベースに保存する
        
        Args:
            supabase: Supabaseクライアント
            article_id: 記事ID
            content: 記事内容（HTML）
        """
        import re
        
        try:
            # 画像プレースホルダーのパターン: <!-- IMAGE_PLACEHOLDER: id|description_jp|prompt_en -->
            pattern = r'<!-- IMAGE_PLACEHOLDER: ([^|]+)\|([^|]+)\|([^>]+) -->'
            matches = re.findall(pattern, content)
            
            if not matches:
                logger.info(f"No image placeholders found in article {article_id}")
                return
            
            logger.info(f"Found {len(matches)} image placeholders in article {article_id}")
            
            # 各プレースホルダーをデータベースに保存
            for index, (placeholder_id, description_jp, prompt_en) in enumerate(matches):
                placeholder_data = {
                    "article_id": article_id,
                    "placeholder_id": placeholder_id.strip(),
                    "description_jp": description_jp.strip(),
                    "prompt_en": prompt_en.strip(),
                    "position_index": index + 1,
                    "status": "pending"
                }
                
                try:
                    # ON CONFLICT DO UPDATEでupsert
                    result = supabase.table("image_placeholders").upsert(
                        placeholder_data,
                        on_conflict="article_id,placeholder_id"
                    ).execute()
                    
                    if result.data:
                        logger.info(f"Saved placeholder {placeholder_id} for article {article_id}")
                    else:
                        logger.warning(f"Failed to save placeholder {placeholder_id}: {result}")
                        
                except Exception as placeholder_error:
                    logger.error(f"Error saving placeholder {placeholder_id} for article {article_id}: {placeholder_error}")
                    # 個別のプレースホルダーエラーは継続可能
                    continue
            
        except Exception as e:
            logger.error(f"Error extracting placeholders for article {article_id}: {e}")
            raise

    async def update_process_status(self, process_id: str, status: str, current_step: str = None, metadata: dict = None) -> None:
        """Update process status in database"""
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            from datetime import datetime, timezone
            supabase = get_supabase_client()
            
            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            if current_step:
                update_data["current_step_name"] = current_step
            
            if metadata:
                update_data["process_metadata"] = metadata
            
            result = supabase.table("generated_articles_state").update(update_data).eq("id", process_id).execute()
            
            if result.data:
                logger.info(f"Successfully updated process {process_id} status to {status}")
                
                # Add status update to history
                await self.add_step_to_history(
                    process_id=process_id,
                    step_name="status_update",
                    status=status,
                    data={"old_status": result.data[0].get("status"), "new_status": status}
                )
            else:
                logger.warning(f"No data returned when updating status for process {process_id}")
                
        except Exception as e:
            logger.error(f"Error updating process status for {process_id}: {e}")
            raise

    async def add_step_to_history(self, process_id: str, step_name: str, status: str, data: dict = None) -> None:
        """Add step to history using database function for process tracking"""
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            # Safe serialization function for history data
            def safe_serialize_history_data(value):
                """Safely serialize data for JSON storage"""
                if value is None:
                    return None
                elif isinstance(value, (str, int, float, bool)):
                    return value
                elif isinstance(value, list):
                    return [safe_serialize_history_data(item) for item in value]
                elif isinstance(value, dict):
                    return {k: safe_serialize_history_data(v) for k, v in value.items()}
                elif hasattr(value, "model_dump"):
                    return value.model_dump()
                elif hasattr(value, "__dict__"):
                    return {k: safe_serialize_history_data(v) for k, v in value.__dict__.items()}
                else:
                    return str(value)
            
            # Safely serialize the data parameter
            safe_data = safe_serialize_history_data(data or {})
            
            # Use the database function instead of direct table insert
            supabase.rpc('add_step_to_history', {
                'process_id': process_id,
                'step_name': step_name,
                'step_status': status,
                'step_data': safe_data
            }).execute()
            
            logger.debug(f"Added step {step_name} to history for process {process_id}")
                
        except Exception as e:
            logger.warning(f"Could not add step to history for process {process_id}: {e}")
            # Don't raise here as this is a non-critical operation
            pass

    async def save_image_placeholders_to_db(self, context: ArticleContext, image_placeholders: list, section_index: int):
        """
        画像プレースホルダー情報をデータベースに保存
        """
        try:
            from app.core.config import get_supabase_client
            supabase = get_supabase_client()
            from datetime import datetime, timezone
            
            # 記事IDを取得（完成した記事から、または生成プロセスIDから推測）
            article_id = getattr(context, 'final_article_id', None)
            generation_process_id = getattr(context, 'process_id', None)
            
            for i, placeholder in enumerate(image_placeholders):
                try:
                    placeholder_data = {
                        "article_id": article_id,
                        "generation_process_id": generation_process_id,
                        "placeholder_id": placeholder.placeholder_id,
                        "description_jp": placeholder.description_jp,
                        "prompt_en": placeholder.prompt_en,
                        "position_index": (section_index * 100) + i,  # セクション内での相対位置
                        "status": "pending",
                        "metadata": {
                            "section_index": section_index,
                            "section_position": i,
                            "generated_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                    
                    # プレースホルダーをデータベースに保存（UPSERT）
                    result = supabase.table("image_placeholders").upsert(
                        placeholder_data,
                        on_conflict="article_id,placeholder_id"
                    ).execute()
                    
                    if result.data:
                        logger.info(f"Image placeholder saved to database - placeholder_id: {placeholder.placeholder_id}")
                    else:
                        logger.warning(f"Image placeholder save returned no data - placeholder_id: {placeholder.placeholder_id}")
                        
                except Exception as placeholder_error:
                    logger.error(f"Failed to save individual placeholder - placeholder_id: {placeholder.placeholder_id}, error: {placeholder_error}")
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to save image placeholders to database - section_index: {section_index}, error: {e}")
            # プレースホルダー保存エラーは非致命的なので、エラーを投げずに続行

    async def save_final_article_with_placeholders(self, context: ArticleContext, process_id: str, user_id: str) -> str:
        """
        最終記事をデータベースに保存し、プレースホルダー情報も更新
        """
        try:
            from app.core.config import get_supabase_client
            supabase = get_supabase_client()
            import uuid
            from datetime import datetime, timezone
            
            # 記事データを準備
            article_data = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "title": context.selected_theme.title if context.selected_theme else "タイトル未設定",
                "content": context.full_draft_html,
                "status": "draft",
                "target_audience": context.selected_detailed_persona if hasattr(context, 'selected_detailed_persona') else None,
                "keywords": context.initial_keywords,
                "seo_analysis": context.serp_analysis_report.dict() if hasattr(context, 'serp_analysis_report') and context.serp_analysis_report else None,
                "generation_process_id": process_id,
                "metadata": {
                    "image_mode": getattr(context, 'image_mode', False),
                    "image_settings": getattr(context, 'image_settings', {}),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "total_sections": len(context.generated_sections_html) if hasattr(context, 'generated_sections_html') else 0,
                    "total_placeholders": len(context.image_placeholders) if hasattr(context, 'image_placeholders') else 0
                }
            }
            
            # 記事をデータベースに保存
            result = supabase.table("articles").insert(article_data).execute()
            
            if not result.data:
                raise Exception("記事の保存に失敗しました")
            
            article_id = result.data[0]["id"]
            context.final_article_id = article_id
            
            # プレースホルダー情報のarticle_idを更新
            if hasattr(context, 'image_placeholders') and context.image_placeholders:
                await self.update_placeholders_article_id(context, article_id, process_id)
            
            logger.info(f"Final article saved successfully - article_id: {article_id}, process_id: {process_id}")
            return article_id
            
        except Exception as e:
            logger.error(f"Failed to save final article - process_id: {process_id}, error: {e}")
            raise

    async def update_placeholders_article_id(self, context: ArticleContext, article_id: str, process_id: str):
        """
        プレースホルダーのarticle_idを更新
        """
        try:
            from app.core.config import get_supabase_client
            supabase = get_supabase_client()
            
            # generation_process_idで検索してarticle_idを更新
            result = supabase.table("image_placeholders").update({
                "article_id": article_id
            }).eq("generation_process_id", process_id).execute()
            
            if result.data:
                logger.info(f"Updated {len(result.data)} placeholders with article_id - article_id: {article_id}")
            else:
                logger.warning(f"No placeholders found to update - process_id: {process_id}")
                
        except Exception as e:
            logger.error(f"Failed to update placeholders article_id - article_id: {article_id}, process_id: {process_id}, error: {e}")
