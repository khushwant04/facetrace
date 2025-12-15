"""
Timetable management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import time
from uuid import UUID

from app.database import get_db
from app.core.permissions import require_org_admin, require_faculty
from app.core.context import get_organization_id
from app.models.timetable import TimetableSlot
from app.schemas.common import PaginatedResponse, MessageResponse

router = APIRouter()

# Placeholder schemas
from pydantic import BaseModel

class TimetableCreate(BaseModel):
    organization_id: UUID
    section_id: int = None
    lab_group_id: int = None
    subject_id: int
    faculty_id: UUID
    day_of_week: str
    start_time: time
    end_time: time
    room_no: str = None
    slot_type: str = "lecture"

class TimetableResponse(BaseModel):
    id: int
    section_id: int = None
    lab_group_id: int = None
    subject_id: int
    faculty_id: UUID
    day_of_week: str
    start_time: time
    end_time: time
    room_no: str = None
    is_active: bool
    
    class Config:
        from_attributes = True


@router.post("/", response_model=TimetableResponse, status_code=201)
async def create_timetable_slot(
    data: TimetableCreate,
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create timetable slot."""
    slot = TimetableSlot(**data.model_dump())
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return slot


@router.get("/", response_model=PaginatedResponse)
async def list_timetable_slots(
    skip: int = 0, limit: int = 100,
    section_id: int = Query(None),
    faculty_id: UUID = Query(None),
    day_of_week: str = Query(None),
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """List timetable slots."""
    query = select(TimetableSlot).where(
        TimetableSlot.organization_id == org_id,
        TimetableSlot.is_active == True
    )
    if section_id:
        query = query.where(TimetableSlot.section_id == section_id)
    if faculty_id:
        query = query.where(TimetableSlot.faculty_id == faculty_id)
    if day_of_week:
        query = query.where(TimetableSlot.day_of_week == day_of_week)
    
    count = await db.execute(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.offset(skip).limit(limit))
    return {"total": count.scalar(), "skip": skip, "limit": limit, "items": result.scalars().all()}


@router.get("/section/{section_id}", response_model=list[TimetableResponse])
async def get_section_timetable(
    section_id: int,
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Get complete timetable for a section."""
    result = await db.execute(
        select(TimetableSlot).where(
            TimetableSlot.section_id == section_id,
            TimetableSlot.organization_id == org_id,
            TimetableSlot.is_active == True
        ).order_by(TimetableSlot.day_of_week, TimetableSlot.start_time)
    )
    return result.scalars().all()


@router.get("/faculty/{faculty_id}", response_model=list[TimetableResponse])
async def get_faculty_timetable(
    faculty_id: UUID,
    org_id: UUID = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db)
):
    """Get faculty's teaching schedule."""
    result = await db.execute(
        select(TimetableSlot).where(
            TimetableSlot.faculty_id == faculty_id,
            TimetableSlot.organization_id == org_id,
            TimetableSlot.is_active == True
        ).order_by(TimetableSlot.day_of_week, TimetableSlot.start_time)
    )
    return result.scalars().all()


@router.delete("/{slot_id}", response_model=MessageResponse)
async def delete_timetable_slot(
    slot_id: int,
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete timetable slot."""
    result = await db.execute(
        select(TimetableSlot).where(
            TimetableSlot.id == slot_id,
            TimetableSlot.organization_id == org_id
        )
    )
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Timetable slot not found")
    
    slot.is_active = False
    await db.commit()
    return MessageResponse(message="Timetable slot deleted", success=True)
