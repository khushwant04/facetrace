"""
Role-Based Access Control using Auth0 Organizations.
- org_id comes from Auth0 token (Auth0 Organizations)
- role comes from database (our User table)
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.core.security import get_auth0_user
from app.database import get_db
from app.models.user import User
from app.models.organization import Organization


async def get_current_user(
    auth0_user: dict = Depends(get_auth0_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get current user with database role.
    - auth0_user_id: from Auth0 token
    - org_id: from Auth0 Organizations (in token)
    - role: from our database
    """
    auth0_org_id = auth0_user.get("org_id")
    
    # Find user in database
    result = await db.execute(
        select(User).where(User.auth0_user_id == auth0_user.get("sub"))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not registered. Complete registration first."
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account inactive. Contact administrator."
        )
    
    # Verify org_id matches (if user logged in via Auth0 org)
    if auth0_org_id:
        # Get org by Auth0 org_id
        org_result = await db.execute(
            select(Organization).where(Organization.auth0_org_id == auth0_org_id)
        )
        org = org_result.scalar_one_or_none()
        
        if org and user.organization_id != org.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not belong to this organization"
            )
    
    return {
        "sub": user.auth0_user_id,
        "auth0_user_id": user.auth0_user_id,
        "email": user.email,
        "role": user.role,
        "user_id": str(user.id),
        "organization_id": str(user.organization_id),
        "auth0_org_id": auth0_org_id,
    }


class RoleChecker:
    """Check if user has required role."""
    
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles
    
    async def __call__(
        self, 
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        if current_user.get("role") not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required: {', '.join(self.allowed_roles)}"
            )
        return current_user


# Role checkers
require_super_admin = RoleChecker(["super_admin"])
require_org_admin = RoleChecker(["super_admin", "org_admin"])
require_faculty = RoleChecker(["super_admin", "org_admin", "faculty"])
require_student = RoleChecker(["super_admin", "org_admin", "faculty", "student"])
