# -*- coding: utf-8 -*-
"""
Organization Service

This service handles all organization-related operations including:
- Organization CRUD operations
- Member management
- Invitation system
- Organization-level permissions and access control
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from supabase import create_client, Client
from pydantic import BaseModel, EmailStr, Field
import secrets
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Database connection
def get_supabase_client() -> Client:
    """Get Supabase client instance"""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)

# Pydantic models for organization operations
class OrganizationRole:
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"

class InvitationStatus:
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"

class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    clerk_organization_id: Optional[str] = None

class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)

class OrganizationRead(BaseModel):
    id: str
    name: str
    owner_user_id: str
    clerk_organization_id: Optional[str]
    stripe_customer_id: Optional[str]
    created_at: datetime
    updated_at: datetime

class OrganizationMemberRead(BaseModel):
    organization_id: str
    user_id: str
    role: str
    clerk_membership_id: Optional[str]
    joined_at: datetime
    # User details (joined from auth.users if needed)
    user_email: Optional[str] = None
    user_full_name: Optional[str] = None

class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = Field(default=OrganizationRole.MEMBER)

class InvitationRead(BaseModel):
    id: str
    organization_id: str
    email: str
    role: str
    status: str
    invited_by_user_id: str
    token: str
    expires_at: datetime
    created_at: datetime

class InvitationResponse(BaseModel):
    accepted: bool
    token: str

class OrganizationService:
    """Service class for organization operations"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def create_organization(self, user_id: str, organization_data: OrganizationCreate) -> OrganizationRead:
        """Create a new organization with the user as owner"""
        try:
            # Create organization
            org_data = {
                "name": organization_data.name,
                "owner_user_id": user_id,
                "clerk_organization_id": organization_data.clerk_organization_id
            }
            
            result = self.supabase.table("organizations").insert(org_data).execute()
            
            if not result.data:
                raise Exception("Failed to create organization")
            
            organization = result.data[0]
            logger.info(f"Created organization {organization['id']} for user {user_id}")
            
            return OrganizationRead(**organization)
            
        except Exception as e:
            logger.error(f"Error creating organization: {e}")
            raise
    
    async def get_organization(self, organization_id: str, user_id: str) -> Optional[OrganizationRead]:
        """Get organization by ID if user has access"""
        try:
            # Check if user has access to organization
            if not await self._user_has_access_to_org(user_id, organization_id):
                return None
            
            result = self.supabase.table("organizations").select("*").eq("id", organization_id).execute()
            
            if not result.data:
                return None
            
            return OrganizationRead(**result.data[0])
            
        except Exception as e:
            logger.error(f"Error getting organization {organization_id}: {e}")
            raise
    
    async def get_user_organizations(self, user_id: str) -> List[OrganizationRead]:
        """Get all organizations where user is a member"""
        try:
            # Query organizations where user is a member
            result = self.supabase.table("organizations").select("*").in_("id", 
                self.supabase.table("organization_members").select("organization_id").eq("user_id", user_id)
            ).execute()
            
            return [OrganizationRead(**org) for org in result.data]
            
        except Exception as e:
            logger.error(f"Error getting organizations for user {user_id}: {e}")
            raise
    
    async def update_organization(self, organization_id: str, user_id: str, update_data: OrganizationUpdate) -> Optional[OrganizationRead]:
        """Update organization (only owner or admin can update)"""
        try:
            # Check if user is owner or admin
            if not await self._user_is_org_admin(user_id, organization_id):
                return None
            
            update_dict = update_data.model_dump(exclude_unset=True)
            update_dict["updated_at"] = datetime.utcnow().isoformat()
            
            result = self.supabase.table("organizations").update(update_dict).eq("id", organization_id).execute()
            
            if not result.data:
                return None
            
            logger.info(f"Updated organization {organization_id} by user {user_id}")
            return OrganizationRead(**result.data[0])
            
        except Exception as e:
            logger.error(f"Error updating organization {organization_id}: {e}")
            raise
    
    async def delete_organization(self, organization_id: str, user_id: str) -> bool:
        """Delete organization (only owner can delete)"""
        try:
            # Check if user is owner
            result = self.supabase.table("organizations").select("owner_user_id").eq("id", organization_id).execute()
            
            if not result.data or result.data[0]["owner_user_id"] != user_id:
                return False
            
            # Delete organization (cascading deletes will handle related tables)
            delete_result = self.supabase.table("organizations").delete().eq("id", organization_id).execute()
            
            logger.info(f"Deleted organization {organization_id} by user {user_id}")
            return len(delete_result.data) > 0
            
        except Exception as e:
            logger.error(f"Error deleting organization {organization_id}: {e}")
            raise
    
    # Member management methods
    async def get_organization_members(self, organization_id: str, user_id: str) -> List[OrganizationMemberRead]:
        """Get all members of an organization"""
        try:
            # Check if user has access to organization
            if not await self._user_has_access_to_org(user_id, organization_id):
                return []
            
            # Get members with user details
            result = self.supabase.table("organization_members").select(
                "*, users:user_id(email, full_name)"
            ).eq("organization_id", organization_id).execute()
            
            members = []
            for member_data in result.data:
                member = OrganizationMemberRead(
                    organization_id=member_data["organization_id"],
                    user_id=member_data["user_id"],
                    role=member_data["role"],
                    clerk_membership_id=member_data["clerk_membership_id"],
                    joined_at=member_data["joined_at"],
                    user_email=member_data["users"]["email"] if member_data["users"] else None,
                    user_full_name=member_data["users"]["full_name"] if member_data["users"] else None
                )
                members.append(member)
            
            return members
            
        except Exception as e:
            logger.error(f"Error getting members for organization {organization_id}: {e}")
            raise
    
    async def update_member_role(self, organization_id: str, target_user_id: str, new_role: str, requesting_user_id: str) -> bool:
        """Update a member's role (only owner or admin can update)"""
        try:
            # Check if requesting user is owner or admin
            if not await self._user_is_org_admin(requesting_user_id, organization_id):
                return False
            
            # Cannot change owner role or remove owner
            org_result = self.supabase.table("organizations").select("owner_user_id").eq("id", organization_id).execute()
            if org_result.data and org_result.data[0]["owner_user_id"] == target_user_id:
                return False  # Cannot change owner role
            
            # Update member role
            result = self.supabase.table("organization_members").update({
                "role": new_role
            }).eq("organization_id", organization_id).eq("user_id", target_user_id).execute()
            
            logger.info(f"Updated role for user {target_user_id} in org {organization_id} to {new_role}")
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating member role: {e}")
            raise
    
    async def remove_member(self, organization_id: str, target_user_id: str, requesting_user_id: str) -> bool:
        """Remove a member from organization (owner/admin can remove others, members can remove themselves)"""
        try:
            # Check permissions
            is_self_removal = target_user_id == requesting_user_id
            is_admin = await self._user_is_org_admin(requesting_user_id, organization_id)
            
            if not (is_self_removal or is_admin):
                return False
            
            # Cannot remove owner
            org_result = self.supabase.table("organizations").select("owner_user_id").eq("id", organization_id).execute()
            if org_result.data and org_result.data[0]["owner_user_id"] == target_user_id:
                return False  # Cannot remove owner
            
            # Remove member
            result = self.supabase.table("organization_members").delete().eq(
                "organization_id", organization_id
            ).eq("user_id", target_user_id).execute()
            
            logger.info(f"Removed user {target_user_id} from organization {organization_id}")
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error removing member: {e}")
            raise
    
    # Invitation methods
    async def create_invitation(self, organization_id: str, invitation_data: InvitationCreate, inviting_user_id: str) -> Optional[InvitationRead]:
        """Create an invitation to join organization"""
        try:
            # Check if inviting user is owner or admin
            if not await self._user_is_org_admin(inviting_user_id, organization_id):
                return None
            
            # Check if user is already a member
            existing_member = self.supabase.table("organization_members").select("user_id").eq(
                "organization_id", organization_id
            ).execute()
            
            # Get user ID by email to check if already member
            user_result = self.supabase.table("users").select("id").eq("email", invitation_data.email).execute()
            if user_result.data:
                existing_user_id = user_result.data[0]["id"]
                for member in existing_member.data:
                    if member["user_id"] == existing_user_id:
                        return None  # User already a member
            
            # Check if there's already a pending invitation
            existing_invitation = self.supabase.table("invitations").select("id").eq(
                "organization_id", organization_id
            ).eq("email", invitation_data.email).eq("status", InvitationStatus.PENDING).execute()
            
            if existing_invitation.data:
                return None  # Invitation already exists
            
            # Create invitation
            invitation_token = secrets.token_urlsafe(32)
            invitation_dict = {
                "organization_id": organization_id,
                "email": invitation_data.email,
                "role": invitation_data.role,
                "invited_by_user_id": inviting_user_id,
                "token": invitation_token,
                "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
            }
            
            result = self.supabase.table("invitations").insert(invitation_dict).execute()
            
            if not result.data:
                return None
            
            logger.info(f"Created invitation for {invitation_data.email} to org {organization_id}")
            return InvitationRead(**result.data[0])
            
        except Exception as e:
            logger.error(f"Error creating invitation: {e}")
            raise
    
    async def get_user_invitations(self, user_email: str) -> List[InvitationRead]:
        """Get pending invitations for a user"""
        try:
            result = self.supabase.table("invitations").select(
                "*, organizations(name)"
            ).eq("email", user_email).eq("status", InvitationStatus.PENDING).execute()
            
            return [InvitationRead(**inv) for inv in result.data]
            
        except Exception as e:
            logger.error(f"Error getting invitations for {user_email}: {e}")
            raise
    
    async def respond_to_invitation(self, token: str, response: InvitationResponse, user_id: str) -> bool:
        """Accept or decline an invitation"""
        try:
            # Get invitation by token
            result = self.supabase.table("invitations").select("*").eq("token", token).eq("status", InvitationStatus.PENDING).execute()
            
            if not result.data:
                return False  # Invalid or expired token
            
            invitation = result.data[0]
            
            # Check if invitation has expired
            if datetime.fromisoformat(invitation["expires_at"]) < datetime.utcnow():
                # Mark as expired
                self.supabase.table("invitations").update({"status": InvitationStatus.EXPIRED}).eq("id", invitation["id"]).execute()
                return False
            
            # Verify user email matches invitation
            user_result = self.supabase.table("users").select("email").eq("id", user_id).execute()
            if not user_result.data or user_result.data[0]["email"] != invitation["email"]:
                return False
            
            if response.accepted:
                # Add user to organization
                member_data = {
                    "organization_id": invitation["organization_id"],
                    "user_id": user_id,
                    "role": invitation["role"]
                }
                
                self.supabase.table("organization_members").insert(member_data).execute()
                
                # Mark invitation as accepted
                self.supabase.table("invitations").update({"status": InvitationStatus.ACCEPTED}).eq("id", invitation["id"]).execute()
                
                logger.info(f"User {user_id} accepted invitation to org {invitation['organization_id']}")
            else:
                # Mark invitation as declined
                self.supabase.table("invitations").update({"status": InvitationStatus.DECLINED}).eq("id", invitation["id"]).execute()
                
                logger.info(f"User {user_id} declined invitation to org {invitation['organization_id']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error responding to invitation: {e}")
            raise
    
    # Helper methods
    async def _user_has_access_to_org(self, user_id: str, organization_id: str) -> bool:
        """Check if user has access to organization (is a member)"""
        try:
            result = self.supabase.table("organization_members").select("user_id").eq(
                "organization_id", organization_id
            ).eq("user_id", user_id).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error checking user access: {e}")
            return False
    
    async def _user_is_org_admin(self, user_id: str, organization_id: str) -> bool:
        """Check if user is owner or admin of organization"""
        try:
            # Check if user is owner
            org_result = self.supabase.table("organizations").select("owner_user_id").eq("id", organization_id).execute()
            if org_result.data and org_result.data[0]["owner_user_id"] == user_id:
                return True
            
            # Check if user is admin
            member_result = self.supabase.table("organization_members").select("role").eq(
                "organization_id", organization_id
            ).eq("user_id", user_id).execute()
            
            if member_result.data and member_result.data[0]["role"] in [OrganizationRole.OWNER, OrganizationRole.ADMIN]:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking admin access: {e}")
            return False
    
    async def get_organization_subscription(self, organization_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get organization's subscription information"""
        try:
            # Check if user has access to organization
            if not await self._user_is_org_admin(user_id, organization_id):
                return None
            
            result = self.supabase.table("organization_subscriptions").select("*").eq(
                "organization_id", organization_id
            ).execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error getting organization subscription: {e}")
            raise

# Service instance
organization_service = OrganizationService()