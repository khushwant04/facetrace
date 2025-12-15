"""
Multi-tenant context using Auth0 Organizations.
Organization ID comes from user's database record.
"""
from fastapi import Depends, HTTPException
from uuid import UUID

from app.core.permissions import get_current_user


async def get_organization_id(
    current_user: dict = Depends(get_current_user)
) -> UUID:
    """
    Get organization ID from authenticated user.
    The org_id is stored in our database when user registers.
    """
    org_id = current_user.get("organization_id")
    
    if not org_id:
        raise HTTPException(
            status_code=400,
            detail="User not associated with any organization"
        )
    
    return UUID(org_id)
