"""
Clerk Organization Validator

Focused responsibilities:
- Decode and minimally validate Clerk JWT
- Extract organization membership with common claim shapes
- Ensure membership in configured admin organization with admin-level role
"""

import jwt
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from app.core.config import settings
from .exceptions import (
    InvalidJWTTokenError,
    OrganizationMembershipRequiredError,
    InvalidOrganizationError,
    InsufficientPermissionsError
)

logger = logging.getLogger(__name__)


@dataclass
class OrganizationMembership:
    """Represents a user's membership in a Clerk organization"""
    organization_id: str
    organization_slug: str
    role: str
    permissions: List[str]
    metadata: Dict[str, Any]


@dataclass
class AdminUser:
    """Represents an authenticated admin user"""
    user_id: str
    email: str
    organization_memberships: List[OrganizationMembership]
    admin_organization_membership: Optional[OrganizationMembership]
    token_claims: Dict[str, Any]


class ClerkOrganizationValidator:
    """
    Validates Clerk JWT tokens and organization memberships for admin authentication.
    
    This class handles:
    - JWT token parsing and validation
    - Organization membership extraction from token claims
    - Admin organization membership verification
    - Comprehensive error handling for authentication failures
    """
    
    def __init__(self):
        self.admin_organization_id = settings.admin_organization_id
        self.admin_organization_slug = settings.admin_organization_slug
        self.jwt_verification_enabled = settings.clerk_jwt_verification_enabled
        
        logger.debug("ClerkOrganizationValidator initialized")
    
    def parse_jwt_token(self, token: str) -> Dict[str, Any]:
        """
        Parse and validate a Clerk JWT token.
        
        Args:
            token: The JWT token string
            
        Returns:
            Dict containing the decoded token claims
            
        Raises:
            InvalidJWTTokenError: If token is invalid, malformed, or expired
        """
        try:
            # NOTE: Signature verification intentionally disabled until Clerk public key wiring is added
            decoded_token = jwt.decode(token, options={"verify_signature": False})
            self._validate_token_structure(decoded_token)
            return decoded_token
        except jwt.ExpiredSignatureError as e:
            raise InvalidJWTTokenError("JWT token has expired", str(e))
        except jwt.InvalidTokenError as e:
            raise InvalidJWTTokenError("Invalid JWT token", str(e))
        except Exception as e:
            raise InvalidJWTTokenError(f"Token parsing failed: {str(e)}", str(e))
    
    def _validate_token_structure(self, token_claims: Dict[str, Any]) -> None:
        """
        Validate that the JWT token has the required structure and claims.
        
        Args:
            token_claims: Decoded JWT claims
            
        Raises:
            InvalidJWTTokenError: If token structure is invalid
        """
        # minimal requirements: user identifier and non-expired token
        required_fields = ['sub', 'exp']
        missing_fields = [field for field in required_fields if not token_claims.get(field)]
        
        if missing_fields:
            raise InvalidJWTTokenError(f"JWT token missing required fields: {', '.join(missing_fields)}")
        
        # Validate expiration
        exp = token_claims.get('exp')
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise InvalidJWTTokenError("JWT token has expired")
    
    def extract_organization_memberships(self, token_claims: Dict[str, Any]) -> List[OrganizationMembership]:
        """
        Extract organization membership data from JWT token claims.
        
        Args:
            token_claims: Decoded JWT claims
            
        Returns:
            List of OrganizationMembership objects
            
        Raises:
            InvalidOrganizationError: If organization data is malformed
        """
        try:
            memberships: List[OrganizationMembership] = []

            # Active organization fields (most common single-org case)
            active_org_id = token_claims.get('org_id') or token_claims.get('organization_id')
            if active_org_id:
                memberships.append(
                    OrganizationMembership(
                        organization_id=active_org_id,
                        organization_slug=(
                            token_claims.get('org_slug')
                            or token_claims.get('organization_slug')
                            or active_org_id
                        ),
                        role=(token_claims.get('org_role') or token_claims.get('organization_role') or 'member'),
                        permissions=token_claims.get('org_permissions', []),
                        metadata={}
                    )
                )

            # Fallback: array-based memberships
            org_membership_data = (
                token_claims.get('org_memberships')
                or token_claims.get('organization_memberships')
            )
            if org_membership_data:
                raw_list = org_membership_data if isinstance(org_membership_data, list) else [org_membership_data]
                for item in raw_list:
                    org_info = item.get('organization') or item.get('org') or {}
                    org_id = org_info.get('id') or org_info.get('organization_id') or org_info.get('org_id')
                    if not org_id:
                        continue
                    memberships.append(
                        OrganizationMembership(
                            organization_id=org_id,
                            organization_slug=(
                                org_info.get('slug')
                                or org_info.get('organization_slug')
                                or org_info.get('org_slug')
                                or org_id
                            ),
                            role=item.get('role', 'member'),
                            permissions=item.get('permissions', []),
                            metadata={}
                        )
                    )

            return memberships
        except Exception as e:
            raise InvalidOrganizationError(
                "Failed to extract organization data",
                validation_error=str(e)
            )
    
    def _parse_membership_data(self, membership_data: Dict[str, Any]) -> Optional[OrganizationMembership]:
        """
        Parse individual membership data from token claims.
        
        Args:
            membership_data: Raw membership data from token
            
        Returns:
            OrganizationMembership object or None if parsing fails
        """
        try:
            org_info = membership_data.get('organization') or membership_data.get('org') or membership_data
            org_id = org_info.get('id') or org_info.get('organization_id') or org_info.get('org_id')
            if not org_id:
                return None
            return OrganizationMembership(
                organization_id=org_id,
                organization_slug=(
                    org_info.get('slug')
                    or org_info.get('organization_slug')
                    or org_info.get('org_slug')
                    or org_id
                ),
                role=membership_data.get('role', 'member'),
                permissions=membership_data.get('permissions', []),
                metadata={}
            )
        except Exception:
            return None
    
    def validate_admin_organization_membership(
        self, 
        memberships: List[OrganizationMembership]
    ) -> OrganizationMembership:
        """
        Validate that the user has membership in the admin organization.
        
        Args:
            memberships: List of user's organization memberships
            
        Returns:
            The admin organization membership
            
        Raises:
            OrganizationMembershipRequiredError: If user is not a member of admin organization
        """
        # Find admin organization membership by ID or slug
        admin_membership: Optional[OrganizationMembership] = None
        for membership in memberships:
            if (
                membership.organization_id == self.admin_organization_id
                or membership.organization_slug == self.admin_organization_slug
            ):
                admin_membership = membership
                break
        
        if not admin_membership:
            raise OrganizationMembershipRequiredError(
                message="Admin organization membership required",
                required_organization_id=self.admin_organization_id,
                user_organizations=[m.organization_id for m in memberships]
            )
        
        # Validate admin permissions within the organization
        self._validate_admin_permissions(admin_membership)
        
        return admin_membership
    
    def _validate_admin_permissions(self, admin_membership: OrganizationMembership) -> None:
        """
        Validate that the user has sufficient permissions within the admin organization.
        
        Args:
            admin_membership: The user's admin organization membership
            
        Raises:
            InsufficientPermissionsError: If user lacks required admin permissions
        """
        admin_roles = ['owner', 'admin']
        user_role = (admin_membership.role or '').lower()
        if user_role not in admin_roles:
            raise InsufficientPermissionsError(
                message=f"User role '{user_role}' does not have admin privileges",
                organization_id=admin_membership.organization_id,
                required_role="admin or owner",
                user_role=user_role
            )
    
    def validate_token_and_extract_admin_user(self, token: str) -> AdminUser:
        """
        Complete validation flow: parse token, extract memberships, validate admin access.
        
        Args:
            token: JWT token string
            
        Returns:
            AdminUser object with validated admin access
            
        Raises:
            InvalidJWTTokenError: If token is invalid
            OrganizationMembershipRequiredError: If user lacks admin organization membership
            InvalidOrganizationError: If organization data is malformed
            InsufficientPermissionsError: If user lacks admin permissions
        """
        try:
            token_claims = self.parse_jwt_token(token)
            user_id = token_claims.get('sub')
            user_email = token_claims.get('email') or token_claims.get('email_address') or ''
            memberships = self.extract_organization_memberships(token_claims)
            admin_membership = self.validate_admin_organization_membership(memberships)
            admin_user = AdminUser(
                user_id=user_id,
                email=user_email,
                organization_memberships=memberships,
                admin_organization_membership=admin_membership,
                token_claims=token_claims
            )
            return admin_user
            
        except Exception as e:
            raise
    
    def get_user_organizations(self, token: str) -> List[str]:
        """
        Get a list of organization IDs that the user belongs to.
        
        Args:
            token: JWT token string
            
        Returns:
            List of organization IDs
            
        Raises:
            InvalidJWTTokenError: If token is invalid
        """
        token_claims = self.parse_jwt_token(token)
        memberships = self.extract_organization_memberships(token_claims)
        return [membership.organization_id for membership in memberships]