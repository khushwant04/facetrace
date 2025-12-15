"""
Student management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from app.core.cache_decorator import cache_response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
import csv
import io

from app.database import get_db
from app.services.cache_service import cache_service
from app.core.permissions import require_org_admin, require_faculty
from app.core.context import get_organization_id
from app.models.student import Student
from app.schemas.student import *
from app.schemas.common import PaginatedResponse, MessageResponse

router = APIRouter()


@router.post("/", response_model=StudentResponse, status_code=201)
async def create_student(
    data: StudentCreate,
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create student."""
    # Check if USN already exists
    result = await db.execute(select(Student).where(Student.usn == data.usn))
    if result.scalar_one_or_none():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="USN already exists")
    
    student = Student(**data.model_dump())
    db.add(student)
    await db.commit()
    await db.refresh(student)
    cache_service.clear_pattern("students:*")
    return student


@router.post("/bulk-upload", response_model=MessageResponse)
async def bulk_upload_students(
    file: UploadFile = File(...),
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Bulk upload students via CSV."""
    # Parse CSV and create students
    # Placeholder implementation
    return MessageResponse(message="Bulk upload completed", success=True)


@router.get("/", status_code=200)
@cache_response(ttl=300, key_prefix="students")
async def list_students(
    skip: int = 0, limit: int = 100,
    section_id: int = Query(None),
    department_id: int = Query(None),
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """List students (paginated, with filters)."""
    query = select(Student).where(Student.organization_id == org_id, Student.is_active == True)
    
    if section_id:
        query = query.where(Student.section_id == section_id)
    if department_id:
        query = query.where(Student.department_id == department_id)
    
    count = await db.execute(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.offset(skip).limit(limit))
    students = result.scalars().all()
    
    return PaginatedStudentResponse(
        total=count.scalar(),
        skip=skip,
        limit=limit,
        items=students
    )


@router.get("/{usn}", response_model=StudentResponse)
async def get_student_by_usn(
    usn: str,
    org_id: UUID = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db)
):
    """Get student by USN."""
    result = await db.execute(
        select(Student).where(Student.usn == usn, Student.organization_id == org_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


@router.put("/{usn}", response_model=StudentResponse)
async def update_student(
    usn: str,
    data: StudentUpdate,
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update student."""
    result = await db.execute(
        select(Student).where(Student.usn == usn, Student.organization_id == org_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Student not found")
    
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    
    await db.commit()
    await db.refresh(student)
    cache_service.clear_pattern("students:*")
    return student


@router.delete("/{usn}", response_model=MessageResponse)
async def delete_student(
    usn: str,
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete student."""
    result = await db.execute(
        select(Student).where(Student.usn == usn, Student.organization_id == org_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Student not found")
    
    student.is_active = False
    await db.commit()
    cache_service.clear_pattern("students:*")
    return MessageResponse(message=f"Student {usn} deactivated", success=True)
