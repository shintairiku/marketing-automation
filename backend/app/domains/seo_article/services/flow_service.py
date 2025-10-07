# -*- coding: utf-8 -*-
"""
Article Flow Service

This service handles dynamic execution of article generation flows:
- Flow and step management
- Dynamic flow execution based on database configurations
- State persistence and resumption
- Integration with existing article generation agents
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from supabase import create_client, Client
from pydantic import BaseModel, Field
import logging

from app.core.config import settings
from app.domains.seo_article.context import ArticleContext
from app.domains.seo_article.agents.definitions import (
    theme_agent, research_planner_agent, researcher_agent, research_synthesizer_agent,
    outline_agent, section_writer_agent, editor_agent, persona_generator_agent,
    serp_keyword_analysis_agent
)

logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    """Get Supabase client instance with service role key
    
    Note: Using service role key bypasses RLS, so we implement 
    user access control manually in the query logic
    """
    return create_client(settings.supabase_url, settings.supabase_service_role_key)

# Pydantic models for flow operations
class FlowStepType:
    KEYWORD_ANALYSIS = "keyword_analysis"
    PERSONA_GENERATION = "persona_generation"
    THEME_PROPOSAL = "theme_proposal"
    RESEARCH = "research"
    OUTLINE_GENERATION = "outline_generation"
    SECTION_WRITING = "section_writing"
    EDITING = "editing"
    CUSTOM = "custom"

class FlowStepCreate(BaseModel):
    step_order: int
    step_type: str
    agent_name: Optional[str] = None
    prompt_template_id: Optional[str] = None
    tool_config: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    is_interactive: bool = False
    skippable: bool = False
    config: Optional[Dict[str, Any]] = None

class FlowStepRead(BaseModel):
    id: str
    flow_id: str
    step_order: int
    step_type: str
    agent_name: Optional[str]
    prompt_template_id: Optional[str]
    tool_config: Optional[Dict[str, Any]]
    output_schema: Optional[Dict[str, Any]]
    is_interactive: bool
    skippable: bool
    config: Optional[Dict[str, Any]]

class ArticleFlowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    is_template: bool = False
    steps: List[FlowStepCreate] = Field(default_factory=list)

class ArticleFlowRead(BaseModel):
    id: str
    organization_id: Optional[str]
    user_id: Optional[str]
    name: str
    description: Optional[str]
    is_template: bool
    created_at: datetime
    updated_at: datetime
    steps: List[FlowStepRead] = Field(default_factory=list)

class GeneratedArticleStateRead(BaseModel):
    id: str
    flow_id: str
    user_id: str
    organization_id: Optional[str]
    current_step_id: Optional[str]
    status: str
    article_context: Dict[str, Any]
    generated_content: Optional[Dict[str, Any]]
    article_id: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    image_mode: Optional[bool] = False

class FlowExecutionRequest(BaseModel):
    flow_id: str
    initial_keywords: List[str]
    target_age_group: Optional[str] = None
    persona_type: Optional[str] = None
    custom_persona: Optional[str] = None
    target_length: Optional[int] = None
    company_name: Optional[str] = None
    company_description: Optional[str] = None
    company_style_guide: Optional[str] = None
    organization_id: Optional[str] = None

class ArticleFlowService:
    """Service class for article generation flow operations"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.agent_registry = {
            'serp_keyword_analysis_agent': serp_keyword_analysis_agent,
            'persona_generator_agent': persona_generator_agent,
            'theme_agent': theme_agent,
            'research_planner_agent': research_planner_agent,
            'researcher_agent': researcher_agent,
            'research_synthesizer_agent': research_synthesizer_agent,
            'outline_agent': outline_agent,
            'section_writer_agent': section_writer_agent,
            'editor_agent': editor_agent,
        }
    
    # Flow management methods
    async def create_flow(self, user_id: str, organization_id: Optional[str], flow_data: ArticleFlowCreate) -> ArticleFlowRead:
        """Create a new article generation flow"""
        try:
            # Create flow
            flow_dict = {
                "user_id": user_id if not organization_id else None,
                "organization_id": organization_id,
                "name": flow_data.name,
                "description": flow_data.description,
                "is_template": flow_data.is_template
            }
            
            result = self.supabase.table("article_generation_flows").insert(flow_dict).execute()
            
            if not result.data:
                raise Exception("Failed to create flow")
            
            flow = result.data[0]
            flow_id = flow["id"]
            
            # Create flow steps
            steps = []
            for step_data in flow_data.steps:
                step_dict = {
                    "flow_id": flow_id,
                    **step_data.model_dump()
                }
                
                step_result = self.supabase.table("flow_steps").insert(step_dict).execute()
                if step_result.data:
                    steps.append(FlowStepRead(**step_result.data[0]))
            
            logger.info(f"Created flow {flow_id} with {len(steps)} steps for user {user_id}")
            
            flow_read = ArticleFlowRead(**flow, steps=steps)
            return flow_read
            
        except Exception as e:
            logger.error(f"Error creating flow: {e}")
            raise
    
    async def get_flow(self, flow_id: str, user_id: str) -> Optional[ArticleFlowRead]:
        """Get flow by ID if user has access"""
        try:
            # Get flow with access check
            flow_result = self.supabase.table("article_generation_flows").select("*").eq("id", flow_id).execute()
            
            if not flow_result.data:
                return None
            
            flow = flow_result.data[0]
            
            # Check access
            if not await self._user_has_flow_access(user_id, flow):
                return None
            
            # Get flow steps
            steps_result = self.supabase.table("flow_steps").select("*").eq("flow_id", flow_id).order("step_order").execute()
            steps = [FlowStepRead(**step) for step in steps_result.data]
            
            return ArticleFlowRead(**flow, steps=steps)
            
        except Exception as e:
            logger.error(f"Error getting flow {flow_id}: {e}")
            raise
    
    async def get_user_flows(self, user_id: str, organization_id: Optional[str] = None) -> List[ArticleFlowRead]:
        """Get flows accessible to user"""
        try:
            query = self.supabase.table("article_generation_flows").select("*")
            
            if organization_id:
                # Get organization flows
                query = query.eq("organization_id", organization_id)
            else:
                # Get user's personal flows and templates
                query = query.or_(f"user_id.eq.{user_id},is_template.eq.true")
            
            flow_result = query.execute()
            
            flows = []
            for flow_data in flow_result.data:
                # Get steps for each flow
                steps_result = self.supabase.table("flow_steps").select("*").eq("flow_id", flow_data["id"]).order("step_order").execute()
                steps = [FlowStepRead(**step) for step in steps_result.data]
                
                flows.append(ArticleFlowRead(**flow_data, steps=steps))
            
            return flows
            
        except Exception as e:
            logger.error(f"Error getting user flows: {e}")
            raise
    
    async def update_flow(self, flow_id: str, user_id: str, update_data: Dict[str, Any]) -> Optional[ArticleFlowRead]:
        """Update flow if user has permission"""
        try:
            # Check if user can edit flow
            flow = await self.get_flow(flow_id, user_id)
            if not flow or not await self._user_can_edit_flow(user_id, flow):
                return None
            
            # Update flow
            update_dict = {k: v for k, v in update_data.items() if k in ["name", "description", "is_template"]}
            if update_dict:
                update_dict["updated_at"] = datetime.utcnow().isoformat()
                
                result = self.supabase.table("article_generation_flows").update(update_dict).eq("id", flow_id).execute()
                
                if not result.data:
                    return None
            
            # Return updated flow
            return await self.get_flow(flow_id, user_id)
            
        except Exception as e:
            logger.error(f"Error updating flow {flow_id}: {e}")
            raise
    
    async def delete_flow(self, flow_id: str, user_id: str) -> bool:
        """Delete flow if user has permission"""
        try:
            # Check if user can edit flow
            flow = await self.get_flow(flow_id, user_id)
            if not flow or not await self._user_can_edit_flow(user_id, flow):
                return False
            
            # Delete flow (cascading deletes will handle steps)
            result = self.supabase.table("article_generation_flows").delete().eq("id", flow_id).execute()
            
            logger.info(f"Deleted flow {flow_id} by user {user_id}")
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error deleting flow {flow_id}: {e}")
            raise
    
    # Flow execution methods
    async def start_flow_execution(self, user_id: str, execution_request: FlowExecutionRequest) -> Optional[str]:
        """Start executing a flow and return the generation process ID"""
        try:
            # Get flow
            flow = await self.get_flow(execution_request.flow_id, user_id)
            if not flow:
                return None
            
            # Create initial article context
            initial_context = self._create_initial_context(execution_request)
            
            # Create generation state record
            state_data = {
                "flow_id": execution_request.flow_id,
                "user_id": user_id,
                "organization_id": execution_request.organization_id,
                "status": "in_progress",
                "article_context": initial_context,
                "generated_content": {}
            }
            
            result = self.supabase.table("generated_articles_state").insert(state_data).execute()
            
            if not result.data:
                return None
            
            process_id = result.data[0]["id"]
            logger.info(f"Started flow execution {process_id} for flow {execution_request.flow_id}")
            
            return process_id
            
        except Exception as e:
            logger.error(f"Error starting flow execution: {e}")
            raise
    
    async def get_generation_state(self, process_id: str, user_id: str) -> Optional[GeneratedArticleStateRead]:
        """Get generation process state"""
        try:
            result = self.supabase.table("generated_articles_state").select("*").eq("id", process_id).execute()
            
            if not result.data:
                return None
            
            state = result.data[0]
            
            # Check access
            if state["user_id"] != user_id:
                # Check organization access if applicable
                if state["organization_id"]:
                    if not await self._user_has_org_access(user_id, state["organization_id"]):
                        return None
                else:
                    return None
            
            # Extract image_mode from article_context
            image_mode = False
            if state.get("article_context") and isinstance(state["article_context"], dict):
                image_mode = state["article_context"].get("image_mode", False)
            
            # Create response with image_mode field
            response_data = {**state, "image_mode": image_mode}
            return GeneratedArticleStateRead(**response_data)
            
        except Exception as e:
            logger.error(f"Error getting generation state {process_id}: {e}")
            raise
    
    async def execute_next_step(self, process_id: str, user_id: str, context: ArticleContext) -> bool:
        """Execute the next step in the flow"""
        try:
            # Get generation state
            state = await self.get_generation_state(process_id, user_id)
            if not state:
                return False
            
            # Get flow and steps
            flow = await self.get_flow(state.flow_id, user_id)
            if not flow:
                return False
            
            # Find current step
            current_step_index = 0
            if state.current_step_id:
                for i, step in enumerate(flow.steps):
                    if step.id == state.current_step_id:
                        current_step_index = i + 1
                        break
            
            # Check if flow is complete
            if current_step_index >= len(flow.steps):
                await self._update_generation_status(process_id, "completed")
                return True
            
            # Get next step
            next_step = flow.steps[current_step_index]
            
            # Execute step
            success = await self._execute_step(next_step, context, process_id)
            
            if success:
                # Update current step
                await self._update_current_step(process_id, next_step.id)
                
                # Save context
                await self._save_context(process_id, context)
            
            return success
            
        except Exception as e:
            logger.error(f"Error executing next step for process {process_id}: {e}")
            await self._update_generation_status(process_id, "error", str(e))
            raise
    
    async def pause_generation(self, process_id: str, user_id: str) -> bool:
        """Pause generation process"""
        try:
            state = await self.get_generation_state(process_id, user_id)
            if not state or state.user_id != user_id:
                return False
            
            await self._update_generation_status(process_id, "paused")
            return True
            
        except Exception as e:
            logger.error(f"Error pausing generation {process_id}: {e}")
            raise
    
    async def cancel_generation(self, process_id: str, user_id: str) -> bool:
        """Cancel generation process"""
        try:
            state = await self.get_generation_state(process_id, user_id)
            if not state or state.user_id != user_id:
                return False
            
            await self._update_generation_status(process_id, "cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling generation {process_id}: {e}")
            raise
    
    # Helper methods
    async def _user_has_flow_access(self, user_id: str, flow: Dict[str, Any]) -> bool:
        """Check if user has access to flow"""
        # User owns the flow
        if flow.get("user_id") == user_id:
            return True
        
        # Flow is a template
        if flow.get("is_template"):
            return True
        
        # User is member of organization that owns the flow
        if flow.get("organization_id"):
            return await self._user_has_org_access(user_id, flow["organization_id"])
        
        return False
    
    async def _user_can_edit_flow(self, user_id: str, flow: ArticleFlowRead) -> bool:
        """Check if user can edit flow"""
        # User owns the flow
        if flow.user_id == user_id:
            return True
        
        # User is admin of organization that owns the flow
        if flow.organization_id:
            return await self._user_is_org_admin(user_id, flow.organization_id)
        
        return False
    
    async def _user_has_org_access(self, user_id: str, organization_id: str) -> bool:
        """Check if user is member of organization"""
        try:
            result = self.supabase.table("organization_members").select("user_id").eq(
                "organization_id", organization_id
            ).eq("user_id", user_id).execute()
            
            return len(result.data) > 0
            
        except Exception:
            return False
    
    async def _user_is_org_admin(self, user_id: str, organization_id: str) -> bool:
        """Check if user is admin of organization"""
        try:
            # Check if user is owner
            org_result = self.supabase.table("organizations").select("owner_user_id").eq("id", organization_id).execute()
            if org_result.data and org_result.data[0]["owner_user_id"] == user_id:
                return True
            
            # Check if user is admin
            member_result = self.supabase.table("organization_members").select("role").eq(
                "organization_id", organization_id
            ).eq("user_id", user_id).execute()
            
            if member_result.data and member_result.data[0]["role"] in ["owner", "admin"]:
                return True
            
            return False
            
        except Exception:
            return False
    
    def _create_initial_context(self, request: FlowExecutionRequest) -> Dict[str, Any]:
        """Create initial ArticleContext from request"""
        context_dict = {
            "initial_keywords": request.initial_keywords,
            "target_age_group": request.target_age_group,
            "persona_type": request.persona_type,
            "custom_persona": request.custom_persona,
            "target_length": request.target_length,
            "company_name": request.company_name,
            "company_description": request.company_description,
            "company_style_guide": request.company_style_guide,
            # Extended company info (if present in request)
            "company_website_url": getattr(request, 'company_website_url', None),
            "company_usp": getattr(request, 'company_usp', None),
            "company_target_persona": getattr(request, 'company_target_persona', None),
            "company_brand_slogan": getattr(request, 'company_brand_slogan', None),
            "company_target_keywords": getattr(request, 'company_target_keywords', None),
            "company_industry_terms": getattr(request, 'company_industry_terms', None),
            "company_avoid_terms": getattr(request, 'company_avoid_terms', None),
            "company_popular_articles": getattr(request, 'company_popular_articles', None),
            "company_target_area": getattr(request, 'company_target_area', None),
            "current_step": "start",
            "generated_detailed_personas": [],
            "research_query_results": [],
            "generated_sections_html": [],
            "section_writer_history": []
        }
        
        return context_dict
    
    async def _execute_step(self, step: FlowStepRead, context: ArticleContext, process_id: str) -> bool:
        """Execute a single flow step"""
        try:
            # Get agent for step
            agent = self.agent_registry.get(step.agent_name)
            if not agent:
                logger.error(f"Unknown agent: {step.agent_name}")
                return False
            
            # Prepare input based on step type
            await self._prepare_step_input(step, context)
            
            # Execute agent (simplified - in practice would use the full Runner.run)
            # This is a placeholder - would need to integrate with the existing agent execution logic
            logger.info(f"Executing step {step.step_type} with agent {step.agent_name}")
            
            # Update context based on step output
            await self._process_step_output(step, None, context)  # output would come from agent
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing step {step.id}: {e}")
            return False
    
    async def _prepare_step_input(self, step: FlowStepRead, context: ArticleContext) -> Union[str, List[Dict[str, Any]]]:
        """Prepare input for agent based on step configuration"""
        # This would prepare the appropriate input format for each step type
        # Simplified implementation
        if step.step_type == FlowStepType.KEYWORD_ANALYSIS:
            return f"キーワード: {', '.join(context.initial_keywords)}"
        elif step.step_type == FlowStepType.PERSONA_GENERATION:
            return f"キーワード: {context.initial_keywords}, 年代: {context.target_age_group}"
        # Add more step types as needed
        
        return "Execute step"
    
    async def _process_step_output(self, step: FlowStepRead, output: Any, context: ArticleContext):
        """Process step output and update context"""
        # This would update the context based on the step output
        # Simplified implementation
        pass
    
    async def _update_generation_status(self, process_id: str, status: str, error_message: Optional[str] = None):
        """Update generation process status"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if error_message:
                update_data["error_message"] = error_message
            
            self.supabase.table("generated_articles_state").update(update_data).eq("id", process_id).execute()
            
        except Exception as e:
            logger.error(f"Error updating generation status: {e}")
    
    async def _update_current_step(self, process_id: str, step_id: str):
        """Update current step in generation process"""
        try:
            update_data = {
                "current_step_id": step_id,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            self.supabase.table("generated_articles_state").update(update_data).eq("id", process_id).execute()
            
        except Exception as e:
            logger.error(f"Error updating current step: {e}")
    
    async def _save_context(self, process_id: str, context: ArticleContext):
        """Save ArticleContext to database"""
        try:
            # Convert context to dict (excluding WebSocket and asyncio objects)
            context_dict = {}
            for key, value in context.__dict__.items():
                if key not in ["websocket", "user_response_event"]:
                    if hasattr(value, "model_dump"):
                        context_dict[key] = value.model_dump()
                    elif isinstance(value, (str, int, float, bool, list, dict, type(None))):
                        context_dict[key] = value
                    else:
                        context_dict[key] = str(value)
            
            update_data = {
                "article_context": context_dict,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            self.supabase.table("generated_articles_state").update(update_data).eq("id", process_id).execute()
            
        except Exception as e:
            logger.error(f"Error saving context: {e}")

# Service instance
article_flow_service = ArticleFlowService()
