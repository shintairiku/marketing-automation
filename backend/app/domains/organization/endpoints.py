# -*- coding: utf-8 -*-
"""
Organization Management API Endpoints

This module provides REST API endpoints for organization management including:
- Organization CRUD operations
- Member management
- Invitation system
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
import logging

from .service import (
    organization_service, 
    OrganizationCreate, 
    OrganizationUpdate, 
    OrganizationRead,
    OrganizationMemberRead,
    InvitationCreate,
    InvitationRead,
    InvitationResponse
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

async def get_current_user_email() -> str:
    """Get current user email from authentication token"""
    # This is a placeholder - implement proper JWT validation
    return "user@example.com"

# Organization endpoints
@router.post("/", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    organization_data: OrganizationCreate,
    current_user_id: str = Depends(get_current_user_id)
):
    """Create a new organization with the current user as owner"""
    try:
        organization = await organization_service.create_organization(current_user_id, organization_data)
        return organization
    except Exception as e:
        logger.error(f"Error creating organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create organization"
        )

@router.get("/", response_model=List[OrganizationRead])
async def get_user_organizations(
    current_user_id: str = Depends(get_current_user_id)
):
    """Get all organizations where the current user is a member"""
    try:
        organizations = await organization_service.get_user_organizations(current_user_id)
        return organizations
    except Exception as e:
        logger.error(f"Error getting user organizations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organizations"
        )

@router.get("/{organization_id}", response_model=OrganizationRead)
async def get_organization(
    organization_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get organization by ID"""
    try:
        organization = await organization_service.get_organization(organization_id, current_user_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or access denied"
            )
        return organization
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization {organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organization"
        )

@router.put("/{organization_id}", response_model=OrganizationRead)
async def update_organization(
    organization_id: str,
    update_data: OrganizationUpdate,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update organization (only owner or admin can update)"""
    try:
        organization = await organization_service.update_organization(organization_id, current_user_id, update_data)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or access denied"
            )
        return organization
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating organization {organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update organization"
        )

@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Delete organization (only owner can delete)"""
    try:
        success = await organization_service.delete_organization(organization_id, current_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or access denied"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting organization {organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete organization"
        )

# Member management endpoints
@router.get("/{organization_id}/members", response_model=List[OrganizationMemberRead])
async def get_organization_members(
    organization_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get all members of an organization"""
    try:
        members = await organization_service.get_organization_members(organization_id, current_user_id)
        return members
    except Exception as e:
        logger.error(f"Error getting organization members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organization members"
        )

@router.put("/{organization_id}/members/{member_user_id}/role")
async def update_member_role(
    organization_id: str,
    member_user_id: str,
    new_role: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update a member's role (only owner or admin can update)"""
    try:
        # Validate role
        valid_roles = ["owner", "admin", "member"]
        if new_role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {valid_roles}"
            )
        
        success = await organization_service.update_member_role(organization_id, member_user_id, new_role, current_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization, member not found, or access denied"
            )
        
        return {"message": "Member role updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating member role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update member role"
        )

@router.delete("/{organization_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    organization_id: str,
    member_user_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Remove a member from organization"""
    try:
        success = await organization_service.remove_member(organization_id, member_user_id, current_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization, member not found, or access denied"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove member"
        )

# Invitation endpoints
@router.post("/{organization_id}/invitations", response_model=InvitationRead, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    organization_id: str,
    invitation_data: InvitationCreate,
    current_user_id: str = Depends(get_current_user_id)
):
    """Create an invitation to join organization"""
    try:
        invitation = await organization_service.create_invitation(organization_id, invitation_data, current_user_id)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create invitation. User may already be a member or invitation already exists."
            )
        return invitation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating invitation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create invitation"
        )

@router.get("/invitations", response_model=List[InvitationRead])
async def get_user_invitations(
    current_user_email: str = Depends(get_current_user_email)
):
    """Get pending invitations for the current user"""
    try:
        invitations = await organization_service.get_user_invitations(current_user_email)
        return invitations
    except Exception as e:
        logger.error(f"Error getting user invitations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve invitations"
        )

@router.post("/invitations/respond")
async def respond_to_invitation(
    response: InvitationResponse,
    current_user_id: str = Depends(get_current_user_id)
):
    """Accept or decline an invitation"""
    try:
        success = await organization_service.respond_to_invitation(response.token, response, current_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid invitation token or invitation has expired"
            )
        
        message = "Invitation accepted" if response.accepted else "Invitation declined"
        return {"message": message}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error responding to invitation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to respond to invitation"
        )

# Subscription endpoint
@router.get("/{organization_id}/subscription")
async def get_organization_subscription(
    organization_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get organization's subscription information"""
    try:
        subscription = await organization_service.get_organization_subscription(organization_id, current_user_id)
        if subscription is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found, no subscription, or access denied"
            )
        return subscription
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organization subscription"
        )