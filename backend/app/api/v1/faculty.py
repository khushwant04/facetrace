"""
Faculty management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.core.cache_decorator import cache_response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

from app.database import get_db
from app.services.cache_service import cache_service
from app.core.permissions import require_org_admin
from app.core.context import get_organization_id
from app.models.faculty import Faculty
from app.schemas.common import PaginatedResponse, MessageResponse

router = APIRouter()


# Placeholder schemas (add to schemas/faculty.py later)
from pydantic import BaseModel

class FacultyCreate(BaseModel):
    organization_id: UUID
    user_id: UUID
    employee_id: str
    department_id: int
    designation: str = None
    specialization: str = None

class FacultyUpdate(BaseModel):
    designation: str = None
    specialization: str = None
    is_active: bool = None

class FacultyResponse(BaseModel):
    id: UUID
    employee_id: str
    department_id: int
    designation: str = None
    is_active: bool
    
    class Config:
        from_attributes = True


@router.post("/", response_model=FacultyResponse, status_code=201)
async def create_faculty(
    data: FacultyCreate,
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create faculty member."""
    result = await db.execute(select(Faculty).where(Faculty.employee_id == data.employee_id))
    if result.scalar_one_or_none():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Employee ID already exists")
    
    faculty = Faculty(**data.model_dump())
    db.add(faculty)
    await db.commit()
    await db.refresh(faculty)
    cache_service.clear_pattern("faculty:*")
    return faculty


@router.get("/", response_model=PaginatedResponse)
@cache_response(ttl=300, key_prefix="faculty")
async def list_faculty(
    skip: int = 0, limit: int = 100,
    department_id: int = Query(None),
    org_id: UUID = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db)
):
    """List faculty members."""
    query = select(Faculty).where(Faculty.organization_id == org_id, Faculty.is_active == True)
    if department_id:
        query = query.where(Faculty.department_id == department_id)
    
    count = await db.execute(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.offset(skip).limit(limit))
    return {"total": count.scalar(), "skip": skip, "limit": limit, "items": result.scalars().all()}


@router.get("/{faculty_id}", response_model=FacultyResponse)
async def get_faculty(
    faculty_id: UUID,
    org_id: UUID = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db)
):
    """Get faculty by ID."""
    result = await db.execute(
        select(Faculty).where(Faculty.id == faculty_id, Faculty.organization_id == org_id)
    )
    faculty = result.scalar_one_or_none()
    if not faculty:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Faculty not found")
    return faculty


@router.put("/{faculty_id}", response_model=FacultyResponse)
async def update_faculty(
    faculty_id: UUID,
    data: FacultyUpdate,
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update faculty."""
    result = await db.execute(
        select(Faculty).where(Faculty.id == faculty_id, Faculty.organization_id == org_id)
    )
    faculty = result.scalar_one_or_none()
    if not faculty:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Faculty not found")
    
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(faculty, field, value)
    
    await db.commit()
    await db.refresh(faculty)
    cache_service.clear_pattern("faculty:*")
    return faculty


@router.delete("/{faculty_id}", response_model=MessageResponse)
async def delete_faculty(
    faculty_id: UUID,
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete faculty."""
    result = await db.execute(
        select(Faculty).where(Faculty.id == faculty_id, Faculty.organization_id == org_id)
    )
    faculty = result.scalar_one_or_none()
    if not faculty:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Faculty not found")
    
    faculty.is_active = False
    await db.commit()
    cache_service.clear_pattern("faculty:*")
    return MessageResponse(message="Faculty deactivated", success=True)
