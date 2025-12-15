"""
Subjects/Courses management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.core.permissions import require_org_admin
from app.core.context import get_organization_id
from app.models.subject import Subject
from app.schemas.common import PaginatedResponse, MessageResponse
from uuid import UUID

router = APIRouter()

# Placeholder schemas
from pydantic import BaseModel

class SubjectCreate(BaseModel):
    organization_id: UUID
    code: str
    name: str
    department_id: int = None
    semester_number: int
    credits: int = 3
    subject_type: str = "theory"

class SubjectResponse(BaseModel):
    id: int
    code: str
    name: str
    semester_number: int
    credits: int
    subject_type: str
    is_active: bool
    
    class Config:
        from_attributes = True


@router.post("/", response_model=SubjectResponse, status_code=201)
async def create_subject(
    data: SubjectCreate,
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create subject."""
    result = await db.execute(select(Subject).where(Subject.code == data.code))
    if result.scalar_one_or_none():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Subject code already exists")
    
    subject = Subject(**data.model_dump())
    db.add(subject)
    await db.commit()
    await db.refresh(subject)
    return subject


@router.get("/", response_model=PaginatedResponse)
async def list_subjects(
    skip: int = 0, limit: int = 100,
    semester_number: int = Query(None),
    department_id: int = Query(None),
    org_id: UUID = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db)
):
    """List subjects."""
    query = select(Subject).where(Subject.organization_id == org_id, Subject.is_active == True)
    if semester_number:
        query = query.where(Subject.semester_number == semester_number)
    if department_id:
        query = query.where(Subject.department_id == department_id)
    
    count = await db.execute(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.offset(skip).limit(limit))
    return {"total": count.scalar(), "skip": skip, "limit": limit, "items": result.scalars().all()}


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: int,
    org_id: UUID = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db)
):
    """Get subject by ID."""
    result = await db.execute(
        select(Subject).where(Subject.id == subject_id, Subject.organization_id == org_id)
    )
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return subject
