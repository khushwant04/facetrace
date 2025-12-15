"""
Organization management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from app.core.cache_decorator import cache_response
from app.services.cache_service import cache_service
from app.database import get_db
from app.core.permissions import require_super_admin, require_org_admin
from app.models.organization import Organization
from app.schemas.organization import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse, OrganizationStats
)
from app.schemas.common import PaginatedResponse, MessageResponse

router = APIRouter()


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_create: OrganizationCreate,
    current_user: dict = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create new organization (super admin only)."""
    result = await db.execute(
        select(Organization).where(Organization.slug == org_create.slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Organization slug already exists")
    
    org = Organization(**org_create.model_dump())
    db.add(org)
    await db.commit()
    await db.refresh(org)
    cache_service.clear_pattern("organizations:*")
    return org

# @cache_response(ttl=300, key_prefix="organizations")
@router.get("/", response_model=PaginatedResponse)
async def list_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: bool = Query(None),
    current_user: dict = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all organizations (paginated)."""
    query = select(Organization)
    if is_active is not None:
        query = query.where(Organization.is_active == is_active)
    
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()
    
    result = await db.execute(query.offset(skip).limit(limit))
    items = result.scalars().all()  # Convert to list
    
    # Convert SQLAlchemy models to dicts for serialization
    items_list = [OrganizationResponse.model_validate(item) for item in items]
    
    return {"total": total, "skip": skip, "limit": limit, "items": items_list}


@router.get("/{slug}", response_model=OrganizationResponse)
async def get_organization_by_slug(
    slug: str,
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get organization by slug."""
    result = await db.execute(select(Organization).where(Organization.slug == slug))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: UUID,
    org_update: OrganizationUpdate,
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update organization."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    for field, value in org_update.model_dump(exclude_unset=True).items():
        setattr(org, field, value)
    
    await db.commit()
    await db.refresh(org)
    cache_service.clear_pattern("organizations:*")
    return org


@router.delete("/{org_id}", response_model=MessageResponse)
async def delete_organization(
    org_id: UUID,
    current_user: dict = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete organization."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    org.is_active = False
    await db.commit()
    cache_service.clear_pattern("organizations:*")
    return MessageResponse(message="Organization deactivated", success=True)


@router.get("/{org_id}/stats", response_model=OrganizationStats)
async def get_organization_stats(
    org_id: UUID,
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get organization statistics."""
    return OrganizationStats(
        total_students=0,
        total_faculty=0,
        total_departments=0,
        total_sections=0,
        active_detections=0,
        storage_used_mb=0.0
    )
