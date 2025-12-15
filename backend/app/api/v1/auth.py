"""
Authentication endpoints - Auth0 integration with SaaS onboarding.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.core.security import verify_token, get_user_from_bearer_token
from app.models.user import User
from app.models.organization import Organization
from app.models.invitation import UserOnboarding
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.common import MessageResponse

router = APIRouter()


# ============ Bootstrap Schema ============

class BootstrapRequest(BaseModel):
    """Request to bootstrap the system with first org and super admin."""
    # Organization details
    org_name: str
    org_slug: str
    org_email: EmailStr
    auth0_org_id: Optional[str] = None
    
    # Super admin will be created from the Auth0 token


class BootstrapResponse(BaseModel):
    """Response after bootstrap."""
    message: str
    organization_id: str
    organization_name: str
    user_id: str
    user_email: str
    role: str


class DirectBootstrapRequest(BaseModel):
    """Direct bootstrap without token verification (first-time setup only)."""
    org_name: str
    org_slug: str
    org_email: EmailStr
    auth0_user_id: str  # The 'sub' claim from Auth0
    user_email: EmailStr
    auth0_org_id: Optional[str] = None


# ============ Bootstrap Endpoint ============

@router.post("/bootstrap", response_model=BootstrapResponse)
async def bootstrap_system(
    data: BootstrapRequest,
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Bootstrap the system with the first organization and super admin.
    
    This endpoint only works when:
    1. No organizations exist in the system, OR
    2. No super_admin users exist
    
    The authenticated Auth0 user becomes the super admin.
    """
    # Get Auth0 user from token
    auth_user = await get_user_from_bearer_token(authorization)
    
    # Check if system already has organizations
    org_count = await db.execute(select(func.count()).select_from(Organization))
    total_orgs = org_count.scalar()
    
    # Check if super admin exists
    admin_result = await db.execute(
        select(User).where(User.role == "super_admin")
    )
    existing_admin = admin_result.scalar_one_or_none()
    
    if total_orgs > 0 and existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System already bootstrapped. Use normal registration flow."
        )
    
    # Check if user already exists
    existing_user = await db.execute(
        select(User).where(User.auth0_user_id == auth_user.get("sub"))
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already registered in the system."
        )
    
    # Check if org slug already exists
    slug_check = await db.execute(
        select(Organization).where(Organization.slug == data.org_slug)
    )
    if slug_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization slug already exists."
        )
    
    # Create organization
    org = Organization(
        name=data.org_name,
        slug=data.org_slug,
        email=data.org_email,
        auth0_org_id=data.auth0_org_id or auth_user.get("org_id"),
        is_active=True,
        subscription_plan="enterprise",  # First org gets enterprise
        max_students=10000,
        max_faculty=500,
        max_departments=50
    )
    db.add(org)
    await db.flush()  # Get org.id
    
    # Create super admin user
    user = User(
        organization_id=org.id,
        auth0_user_id=auth_user.get("sub"),
        email=auth_user.get("email"),
        role="super_admin",
        is_active=True,
        is_verified=True,
        email_verified=auth_user.get("email_verified", False),
        last_login=datetime.utcnow()
    )
    db.add(user)
    await db.flush()
    
    # Create onboarding record
    onboarding = UserOnboarding(
        user_id=user.id,
        organization_id=org.id,
        status="completed",
        email_verified=True,
        profile_completed=True
    )
    db.add(onboarding)
    
    await db.commit()
    await db.refresh(org)
    await db.refresh(user)
    
    return BootstrapResponse(
        message="System bootstrapped successfully! You are now the super admin.",
        organization_id=str(org.id),
        organization_name=org.name,
        user_id=str(user.id),
        user_email=user.email,
        role=user.role
    )


@router.post("/bootstrap-direct", response_model=BootstrapResponse)
async def bootstrap_system_direct(
    data: DirectBootstrapRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Direct bootstrap endpoint for first-time setup.
    
    WARNING: This endpoint only works when NO organizations or super_admins exist.
    It allows bootstrapping without token verification for encrypted token scenarios.
    
    After first use, this endpoint is disabled.
    """
    # Check if system already has organizations
    org_count = await db.execute(select(func.count()).select_from(Organization))
    total_orgs = org_count.scalar()
    
    # Check if super admin exists
    admin_result = await db.execute(
        select(User).where(User.role == "super_admin")
    )
    existing_admin = admin_result.scalar_one_or_none()
    
    if total_orgs > 0 or existing_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System already bootstrapped. This endpoint is disabled."
        )
    
    # Check if user already exists
    existing_user = await db.execute(
        select(User).where(User.auth0_user_id == data.auth0_user_id)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already registered in the system."
        )
    
    # Check if org slug already exists
    slug_check = await db.execute(
        select(Organization).where(Organization.slug == data.org_slug)
    )
    if slug_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization slug already exists."
        )
    
    # Create organization
    org = Organization(
        name=data.org_name,
        slug=data.org_slug,
        email=data.org_email,
        auth0_org_id=data.auth0_org_id,
        is_active=True,
        subscription_plan="enterprise",
        max_students=10000,
        max_faculty=500,
        max_departments=50
    )
    db.add(org)
    await db.flush()
    
    # Create super admin user
    user = User(
        organization_id=org.id,
        auth0_user_id=data.auth0_user_id,
        email=data.user_email,
        role="super_admin",
        is_active=True,
        is_verified=True,
        email_verified=True,
        last_login=datetime.utcnow()
    )
    db.add(user)
    await db.flush()
    
    # Create onboarding record
    onboarding = UserOnboarding(
        user_id=user.id,
        organization_id=org.id,
        status="completed",
        email_verified=True,
        profile_completed=True
    )
    db.add(onboarding)
    
    await db.commit()
    await db.refresh(org)
    await db.refresh(user)
    
    return BootstrapResponse(
        message="System bootstrapped successfully! You are now the super admin.",
        organization_id=str(org.id),
        organization_name=org.name,
        user_id=str(user.id),
        user_email=user.email,
        role=user.role
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user profile.
    Returns user info including organization and onboarding status.
    """
    user_data = await get_user_from_bearer_token(authorization)
    auth0_user_id = user_data.get("sub")
    
    result = await db.execute(
        select(User).where(User.auth0_user_id == auth0_user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # User authenticated with Auth0 but not registered in system
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not registered. Please use an invitation link or join code."
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Contact your administrator."
        )
    
    # Update last login
    await db.execute(
        update(User).where(User.id == user.id).values(last_login=datetime.utcnow())
    )
    await db.commit()
    await db.refresh(user)
    
    return user


@router.put("/me", response_model=UserResponse)
async def update_profile(
    user_update: UserUpdate,
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile."""
    user_data = await get_user_from_bearer_token(authorization)
    
    result = await db.execute(
        select(User).where(User.auth0_user_id == user_data.get("sub"))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Account inactive")
    
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    
    return user


@router.get("/check")
async def check_registration(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if Auth0 user is registered in the system.
    Used by frontend to determine redirect flow.
    """
    user_data = await get_user_from_bearer_token(authorization)
    
    result = await db.execute(
        select(User).where(User.auth0_user_id == user_data.get("sub"))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return {
            "registered": False,
            "message": "Please use invitation link or join code to register"
        }
    
    # Get onboarding status
    onboarding_result = await db.execute(
        select(UserOnboarding).where(UserOnboarding.user_id == user.id)
    )
    onboarding = onboarding_result.scalar_one_or_none()
    
    # Get organization
    org_result = await db.execute(
        select(Organization).where(Organization.id == user.organization_id)
    )
    org = org_result.scalar_one()
    
    next_step = "dashboard"
    if onboarding:
        if onboarding.requires_approval and not onboarding.approved_at:
            next_step = "awaiting_approval"
        elif not onboarding.profile_completed:
            next_step = "complete_profile"
        elif not onboarding.face_registered and user.role == "student":
            next_step = "register_face"
    
    return {
        "registered": True,
        "user_id": str(user.id),
        "organization_id": str(user.organization_id),
        "organization_name": org.name,
        "role": user.role,
        "is_active": user.is_active,
        "next_step": next_step
    }


@router.post("/logout", response_model=MessageResponse)
async def logout():
    """
    Logout endpoint.
    Client should clear tokens and redirect to Auth0 logout.
    """
    return MessageResponse(
        message="Clear local tokens and redirect to Auth0 logout URL",
        success=True
    )


# ============ Cache Management (Admin Only) ============

from app.services.cache_service import cache_service
from app.core.permissions import require_super_admin


@router.get("/cache/stats")
async def get_cache_stats(current_user: dict = Depends(require_super_admin)):
    """Get Redis cache statistics."""
    if not cache_service.is_connected():
        return {"status": "disconnected", "message": "Redis not connected"}
    
    stats = cache_service.get_stats()
    hits = stats.get("keyspace_hits", 0)
    misses = stats.get("keyspace_misses", 0)
    total = hits + misses
    hit_rate = (hits / total * 100) if total > 0 else 0
    
    return {
        "status": "connected",
        "stats": stats,
        "hit_rate_percent": round(hit_rate, 2)
    }


@router.post("/cache/clear")
async def clear_cache(
    pattern: str = "*",
    current_user: dict = Depends(require_super_admin)
):
    """Clear cache by pattern."""
    if not cache_service.is_connected():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis not connected")
    
    deleted = cache_service.clear_pattern(pattern)
    return {"message": f"Cleared {deleted} keys", "pattern": pattern}
