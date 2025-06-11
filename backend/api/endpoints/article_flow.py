# -*- coding: utf-8 -*-
"""
Article Flow Management API Endpoints

This module provides REST API endpoints for article generation flow management including:
- Flow CRUD operations
- Flow execution and state management
- Template flow access
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional
import logging

from services.article_flow_service import (
    article_flow_service,
    ArticleFlowCreate,
    ArticleFlowRead,
    GeneratedArticleStateRead,
    FlowExecutionRequest
)

logger = logging.getLogger(__name__)
router = APIRouter()

# TODO: Add authentication dependency
# For now, we'll use a placeholder for user_id
# In production, this should come from JWT token validation
async def get_current_user_id() -> str:
    """Get current user ID from authentication token"""
    # This is a placeholder - implement proper JWT validation
    return "placeholder-user-id"

# Flow management endpoints
@router.post("/", response_model=ArticleFlowRead, status_code=status.HTTP_201_CREATED)
async def create_flow(
    flow_data: ArticleFlowCreate,
    organization_id: Optional[str] = Query(None, description="Organization ID for organization-level flows"),
    current_user_id: str = Depends(get_current_user_id)
):
    """Create a new article generation flow"""
    try:
        flow = await article_flow_service.create_flow(current_user_id, organization_id, flow_data)
        return flow
    except Exception as e:
        logger.error(f"Error creating flow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create flow"
        )

@router.get("/", response_model=List[ArticleFlowRead])
async def get_flows(
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    include_templates: bool = Query(True, description="Include template flows"),
    current_user_id: str = Depends(get_current_user_id)
):
    """Get flows accessible to the current user"""
    try:
        flows = await article_flow_service.get_user_flows(current_user_id, organization_id)
        
        # Filter templates if requested
        if not include_templates:
            flows = [flow for flow in flows if not flow.is_template]
        
        return flows
    except Exception as e:
        logger.error(f"Error getting flows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve flows"
        )

@router.get("/{flow_id}", response_model=ArticleFlowRead)
async def get_flow(
    flow_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get flow by ID"""
    try:
        flow = await article_flow_service.get_flow(flow_id, current_user_id)
        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flow not found or access denied"
            )
        return flow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting flow {flow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve flow"
        )

@router.put("/{flow_id}", response_model=ArticleFlowRead)
async def update_flow(
    flow_id: str,
    update_data: dict,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update flow (only owner or organization admin can update)"""
    try:
        flow = await article_flow_service.update_flow(flow_id, current_user_id, update_data)
        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flow not found or access denied"
            )
        return flow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating flow {flow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update flow"
        )

@router.delete("/{flow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flow(
    flow_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Delete flow (only owner or organization admin can delete)"""
    try:
        success = await article_flow_service.delete_flow(flow_id, current_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flow not found or access denied"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting flow {flow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete flow"
        )

# Flow execution endpoints
@router.post("/{flow_id}/execute")
async def execute_flow(
    flow_id: str,
    execution_request: FlowExecutionRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """Start executing a flow"""
    try:
        # Set the flow_id from the path parameter
        execution_request.flow_id = flow_id
        
        process_id = await article_flow_service.start_flow_execution(current_user_id, execution_request)
        if not process_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flow not found or access denied"
            )
        
        return {
            "process_id": process_id,
            "message": "Flow execution started",
            "status": "in_progress"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing flow {flow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start flow execution"
        )

# Generation state management endpoints
@router.get("/generations/{process_id}", response_model=GeneratedArticleStateRead)
async def get_generation_state(
    process_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get generation process state"""
    try:
        state = await article_flow_service.get_generation_state(process_id, current_user_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation process not found or access denied"
            )
        return state
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting generation state {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve generation state"
        )

@router.post("/generations/{process_id}/pause")
async def pause_generation(
    process_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Pause generation process"""
    try:
        success = await article_flow_service.pause_generation(process_id, current_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation process not found or access denied"
            )
        
        return {"message": "Generation process paused"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing generation {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pause generation"
        )

@router.post("/generations/{process_id}/cancel")
async def cancel_generation(
    process_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Cancel generation process"""
    try:
        success = await article_flow_service.cancel_generation(process_id, current_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation process not found or access denied"
            )
        
        return {"message": "Generation process cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling generation {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel generation"
        )

# Template flow endpoints
@router.get("/templates/", response_model=List[ArticleFlowRead])
async def get_template_flows(
    current_user_id: str = Depends(get_current_user_id)
):
    """Get all template flows available for copying"""
    try:
        flows = await article_flow_service.get_user_flows(current_user_id)
        template_flows = [flow for flow in flows if flow.is_template]
        return template_flows
    except Exception as e:
        logger.error(f"Error getting template flows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template flows"
        )

@router.post("/templates/{template_id}/copy", response_model=ArticleFlowRead)
async def copy_template_flow(
    template_id: str,
    name: str = Query(..., description="Name for the new flow"),
    organization_id: Optional[str] = Query(None, description="Organization ID for organization-level flow"),
    current_user_id: str = Depends(get_current_user_id)
):
    """Copy a template flow to create a new customizable flow"""
    try:
        # Get template flow
        template = await article_flow_service.get_flow(template_id, current_user_id)
        if not template or not template.is_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template flow not found"
            )
        
        # Create flow data from template
        flow_data = ArticleFlowCreate(
            name=name,
            description=f"Copied from template: {template.name}",
            is_template=False,
            steps=[
                {
                    "step_order": step.step_order,
                    "step_type": step.step_type,
                    "agent_name": step.agent_name,
                    "prompt_template_id": step.prompt_template_id,
                    "tool_config": step.tool_config,
                    "output_schema": step.output_schema,
                    "is_interactive": step.is_interactive,
                    "skippable": step.skippable,
                    "config": step.config
                }
                for step in template.steps
            ]
        )
        
        # Create new flow
        new_flow = await article_flow_service.create_flow(current_user_id, organization_id, flow_data)
        return new_flow
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error copying template flow {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to copy template flow"
        )