from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime, timezone

from core.auth import verify_clerk_jwt, ClerkJWTPayload
from services.organization_service import OrganizationService
from schemas.request import InviteMemberRequest, UpdateSeatsRequest
from schemas.response import (
    OrganizationResponse,
    MemberResponse,
    InvitationResponse,
    MemberUsageResponse
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: str,
    jwt_payload: ClerkJWTPayload = Depends(verify_clerk_jwt)
):
    """組織情報を取得"""
    if jwt_payload.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
    org_service = OrganizationService()
    organization = await org_service.get_organization(organization_id)
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return OrganizationResponse(**organization)


@router.get("/{organization_id}/members", response_model=List[MemberResponse])
async def get_organization_members(
    organization_id: str,
    jwt_payload: ClerkJWTPayload = Depends(verify_clerk_jwt)
):
    """組織のメンバー一覧を取得"""
    if jwt_payload.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
    org_service = OrganizationService()
    members = await org_service.get_organization_members(organization_id)
    
    return [MemberResponse(**member) for member in members]


@router.get("/{organization_id}/members/usage", response_model=List[MemberUsageResponse])
async def get_member_usage(
    organization_id: str,
    jwt_payload: ClerkJWTPayload = Depends(verify_clerk_jwt)
):
    """メンバーの使用量情報を取得"""
    if jwt_payload.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
    org_service = OrganizationService()
    usage_data = await org_service.get_member_usage(organization_id)
    
    return [MemberUsageResponse(**usage) for usage in usage_data]


@router.get("/{organization_id}/invitations", response_model=List[InvitationResponse])
async def get_organization_invitations(
    organization_id: str,
    jwt_payload: ClerkJWTPayload = Depends(verify_clerk_jwt)
):
    """組織の招待一覧を取得"""
    if jwt_payload.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
    # 管理者権限チェック
    if jwt_payload.organization_role not in ['admin', 'org:admin', 'owner']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    org_service = OrganizationService()
    invitations = await org_service.get_pending_invitations(organization_id)
    
    return [InvitationResponse(**invitation) for invitation in invitations]


@router.post("/{organization_id}/invitations")
async def invite_member(
    organization_id: str,
    request: InviteMemberRequest,
    jwt_payload: ClerkJWTPayload = Depends(verify_clerk_jwt)
):
    """メンバーを招待"""
    if jwt_payload.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
    # 管理者権限チェック
    if jwt_payload.organization_role not in ['admin', 'org:admin', 'owner']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    org_service = OrganizationService()
    
    try:
        invitation = await org_service.invite_member(
            organization_id=organization_id,
            email=request.email,
            role=request.role or 'member',
            invited_by=jwt_payload.user_id
        )
        
        return {"message": "Invitation sent successfully", "invitation_id": invitation["id"]}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send invitation"
        )


@router.delete("/{organization_id}/invitations/{invitation_id}")
async def cancel_invitation(
    organization_id: str,
    invitation_id: str,
    jwt_payload: ClerkJWTPayload = Depends(verify_clerk_jwt)
):
    """招待をキャンセル"""
    if jwt_payload.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
    # 管理者権限チェック
    if jwt_payload.organization_role not in ['admin', 'org:admin', 'owner']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    org_service = OrganizationService()
    
    try:
        await org_service.cancel_invitation(invitation_id, organization_id)
        return {"message": "Invitation cancelled successfully"}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/{organization_id}/members/{member_id}")
async def remove_member(
    organization_id: str,
    member_id: str,
    jwt_payload: ClerkJWTPayload = Depends(verify_clerk_jwt)
):
    """メンバーを削除"""
    if jwt_payload.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
    # オーナー権限チェック
    if jwt_payload.organization_role != 'owner':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner privileges required"
        )
    
    org_service = OrganizationService()
    
    try:
        await org_service.remove_member(member_id, organization_id)
        return {"message": "Member removed successfully"}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/{organization_id}/seats")
async def update_seat_count(
    organization_id: str,
    request: UpdateSeatsRequest,
    jwt_payload: ClerkJWTPayload = Depends(verify_clerk_jwt)
):
    """シート数を更新"""
    if jwt_payload.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
    # オーナー権限チェック
    if jwt_payload.organization_role != 'owner':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner privileges required"
        )
    
    org_service = OrganizationService()
    
    try:
        updated_org = await org_service.update_seat_count(
            organization_id=organization_id,
            new_max_seats=request.max_seats
        )
        
        return {
            "message": "Seat count updated successfully",
            "organization": OrganizationResponse(**updated_org)
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )