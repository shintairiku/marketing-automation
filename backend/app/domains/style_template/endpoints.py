# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.common.database import supabase
from app.common.auth import get_current_user_id_from_token
from app.domains.style_template.schemas import AutoStyleTemplateRequest, AutoStyleTemplateResponse
from app.domains.style_template.service import StyleTemplateService
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(tags=["style-templates"])

# Pydantic models for API requests/responses
class StyleTemplateCreate(BaseModel):
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    template_type: str = Field("custom", description="Template type")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Template settings")
    is_active: bool = Field(True, description="Whether template is active")
    is_default: bool = Field(False, description="Whether this is the default template")
    organization_id: Optional[str] = Field(None, description="Organization ID for shared templates")

class StyleTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    template_type: Optional[str] = Field(None, description="Template type")
    settings: Optional[Dict[str, Any]] = Field(None, description="Template settings")
    is_active: Optional[bool] = Field(None, description="Whether template is active")
    is_default: Optional[bool] = Field(None, description="Whether this is the default template")

class StyleTemplateResponse(BaseModel):
    id: str
    user_id: str
    organization_id: Optional[str]
    name: str
    description: Optional[str]
    template_type: str
    settings: Dict[str, Any]
    is_active: bool
    is_default: bool
    created_at: str
    updated_at: str


@router.post("/auto-generate", response_model=AutoStyleTemplateResponse)
async def auto_generate_style_template(
    request: AutoStyleTemplateRequest,
    user_id: str = Depends(get_current_user_id_from_token),
):
    """スタイルテンプレートの自動入力"""
    return await StyleTemplateService.auto_generate_style_template(request, user_id)

@router.get("", response_model=List[StyleTemplateResponse])
@router.get("/", response_model=List[StyleTemplateResponse])
async def get_style_templates(
    user_id: str = Depends(get_current_user_id_from_token)
):
    """Get all style templates accessible to the user"""
    try:
        # Build query to get user's personal templates
        query = supabase.table("style_guide_templates").select("*").eq("user_id", user_id)
        
        result = query.eq("is_active", True).order("is_default", desc=True).order("created_at", desc=True).execute()
        
        if result.data:
            return [StyleTemplateResponse(**template) for template in result.data]
        else:
            return []
            
    except Exception as e:
        logger.error(f"Error fetching style templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch style templates"
        )

@router.get("/{template_id}", response_model=StyleTemplateResponse)
async def get_style_template(
    template_id: str,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """Get a specific style template by ID"""
    try:
            
        # Check if user has access to this template
        result = supabase.table("style_guide_templates").select("*").eq("id", template_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Style template not found"
            )
        
        template = result.data[0]
        
        # Check access permissions
        if template["user_id"] != user_id:
            # Check if user is member of the organization
            if template["organization_id"]:
                org_check = supabase.table("organization_members").select("user_id").eq(
                    "organization_id", template["organization_id"]
                ).eq("user_id", user_id).execute()
                
                if not org_check.data:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied to this style template"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this style template"
                )
        
        return StyleTemplateResponse(**template)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching style template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch style template"
        )

@router.post("", response_model=StyleTemplateResponse)
@router.post("/", response_model=StyleTemplateResponse)
async def create_style_template(
    template_data: StyleTemplateCreate,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """Create a new style template"""
    try:
        # Validate organization access if specified
        if template_data.organization_id:
            org_check = supabase.table("organization_members").select("role").eq(
                "organization_id", template_data.organization_id
            ).eq("user_id", user_id).execute()
            
            if not org_check.data:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not a member of the specified organization"
                )
            
            # Check if user has admin permissions for organization templates
            member_role = org_check.data[0]["role"]
            if member_role not in ["owner", "admin"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to create organization templates"
                )
        
        # Prepare data for insertion
        insert_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": template_data.name,
            "description": template_data.description,
            "template_type": template_data.template_type,
            "settings": template_data.settings,
            "is_active": template_data.is_active,
            "is_default": template_data.is_default,
            "organization_id": template_data.organization_id
        }
        
        result = supabase.table("style_guide_templates").insert(insert_data).execute()
        
        if result.data:
            return StyleTemplateResponse(**result.data[0])
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create style template"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating style template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create style template"
        )

@router.put("/{template_id}", response_model=StyleTemplateResponse)
async def update_style_template(
    template_id: str,
    template_data: StyleTemplateUpdate,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """Update an existing style template"""
    try:
        # Check if template exists and user has access
        existing = supabase.table("style_guide_templates").select("*").eq("id", template_id).execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Style template not found"
            )
        
        template = existing.data[0]
        
        # Check permissions
        if template["user_id"] != user_id:
            if template["organization_id"]:
                org_check = supabase.table("organization_members").select("role").eq(
                    "organization_id", template["organization_id"]
                ).eq("user_id", user_id).execute()
                
                if not org_check.data:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied to this style template"
                    )
                
                member_role = org_check.data[0]["role"]
                if member_role not in ["owner", "admin"]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions to modify this template"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this style template"
                )
        
        # Prepare update data (only include non-None fields)
        update_data = {}
        for field, value in template_data.model_dump(exclude_unset=True).items():
            if value is not None:
                update_data[field] = value
        
        if not update_data:
            # No changes to make
            return StyleTemplateResponse(**template)
        
        result = supabase.table("style_guide_templates").update(update_data).eq("id", template_id).execute()
        
        if result.data:
            return StyleTemplateResponse(**result.data[0])
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update style template"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating style template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update style template"
        )

@router.delete("/{template_id}")
async def delete_style_template(
    template_id: str,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """Delete a style template (soft delete by setting is_active to false)"""
    try:
        # Check if template exists and user has access
        existing = supabase.table("style_guide_templates").select("*").eq("id", template_id).execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Style template not found"
            )
        
        template = existing.data[0]
        
        # Check permissions
        if template["user_id"] != user_id:
            if template["organization_id"]:
                org_check = supabase.table("organization_members").select("role").eq(
                    "organization_id", template["organization_id"]
                ).eq("user_id", user_id).execute()
                
                if not org_check.data:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied to this style template"
                    )
                
                member_role = org_check.data[0]["role"]
                if member_role not in ["owner", "admin"]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions to delete this template"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this style template"
                )
        
        # Soft delete by setting is_active to false
        result = supabase.table("style_guide_templates").update({"is_active": False}).eq("id", template_id).execute()
        
        if result.data:
            return {"message": "Style template deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete style template"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting style template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete style template"
        )

@router.post("/{template_id}/set-default")
async def set_default_template(
    template_id: str,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """Set a template as the default for the user"""
    try:
        # Check if template exists and user has access
        existing = supabase.table("style_guide_templates").select("*").eq("id", template_id).execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Style template not found"
            )
        
        template = existing.data[0]
        
        # Check access permissions
        if template["user_id"] != user_id:
            if template["organization_id"]:
                org_check = supabase.table("organization_members").select("user_id").eq(
                    "organization_id", template["organization_id"]
                ).eq("user_id", user_id).execute()
                
                if not org_check.data:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied to this style template"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this style template"
                )
        
        # Set this template as default (trigger will handle unsetting others)
        result = supabase.table("style_guide_templates").update({"is_default": True}).eq("id", template_id).execute()
        
        if result.data:
            return {"message": "Default template updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to set default template"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting default template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set default template"
        )
