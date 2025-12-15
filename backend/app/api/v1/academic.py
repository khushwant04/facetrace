"""
Academic structure endpoints (departments, semesters, sections, lab groups).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.core.cache_decorator import cache_response
from app.services.cache_service import cache_service
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

from app.database import get_db
from app.core.permissions import require_org_admin
from app.core.context import get_organization_id
from app.models.academic import Department, Semester, Section, LabGroup, AcademicYear
from app.schemas.academic import *
from app.schemas.common import PaginatedResponse, MessageResponse

router = APIRouter()

# Academic Years
@router.post("/academic-years/", response_model=AcademicYearResponse, status_code=201)
async def create_academic_year(
    data: AcademicYearCreate,
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create academic year."""
    year = AcademicYear(**data.model_dump())
    db.add(year)
    await db.commit()
    await db.refresh(year)
    cache_service.clear_pattern("academic_years:*")
    return year

@router.get("/academic-years/", response_model=PaginatedResponse)
@cache_response(ttl=300, key_prefix="academic_years")
async def list_academic_years(
    skip: int = 0, limit: int = 100,
    org_id: UUID = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db)
):
    """List academic years."""
    query = select(AcademicYear).where(AcademicYear.organization_id == org_id)
    count = await db.execute(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.offset(skip).limit(limit))
    return {"total": count.scalar(), "skip": skip, "limit": limit, "items": result.scalars().all()}

# Departments
@router.post("/departments/", response_model=DepartmentResponse, status_code=201)
async def create_department(
    data: DepartmentCreate,
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create department."""
    dept = Department(**data.model_dump())
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    cache_service.clear_pattern("departments:*")
    return dept

@router.get("/departments/", response_model=PaginatedResponse)
@cache_response(ttl=300, key_prefix="departments")
async def list_departments(
    skip: int = 0, limit: int = 100,
    org_id: UUID = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db)
):
    """List departments."""
    query = select(Department).where(Department.organization_id == org_id, Department.is_active == True)
    count = await db.execute(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.offset(skip).limit(limit))
    return {"total": count.scalar(), "skip": skip, "limit": limit, "items": result.scalars().all()}

# Semesters
@router.post("/semesters/", response_model=SemesterResponse, status_code=201)
async def create_semester(
    data: SemesterCreate,
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create semester."""
    sem = Semester(**data.model_dump())
    db.add(sem)
    await db.commit()
    await db.refresh(sem)
    cache_service.clear_pattern("semesters:*")
    return sem

@router.get("/semesters/active", response_model=list[SemesterResponse])
@cache_response(ttl=300, key_prefix="semesters")
async def get_active_semesters(
    org_id: UUID = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db)
):
    """Get active semesters (max 4: either odd or even)."""
    result = await db.execute(
        select(Semester).where(
            Semester.organization_id == org_id,
            Semester.is_active == True
        )
    )
    return result.scalars().all()

# Sections
@router.post("/sections/", response_model=SectionResponse, status_code=201)
async def create_section(
    data: SectionCreate,
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create section."""
    section = Section(**data.model_dump())
    db.add(section)
    await db.commit()
    await db.refresh(section)
    cache_service.clear_pattern("sections:*")
    return section

@router.get("/sections/", response_model=PaginatedResponse)
@cache_response(ttl=300, key_prefix="sections")
async def list_sections(
    skip: int = 0, limit: int = 100,
    org_id: UUID = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db)
):
    """List sections."""
    query = select(Section).where(Section.organization_id == org_id, Section.is_active == True)
    count = await db.execute(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.offset(skip).limit(limit))
    return {"total": count.scalar(), "skip": skip, "limit": limit, "items": result.scalars().all()}

# Lab Groups
@router.post("/lab-groups/", response_model=LabGroupResponse, status_code=201)
async def create_lab_group(
    data: LabGroupCreate,
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create lab group (e.g., A1, A2, B1, B2)."""
    group = LabGroup(**data.model_dump())
    db.add(group)
    await db.commit()
    await db.refresh(group)
    cache_service.clear_pattern("lab_groups:*")
    return group

@router.get("/lab-groups/by-section/{section_id}", response_model=list[LabGroupResponse])
@cache_response(ttl=300, key_prefix="lab_groups")
async def get_lab_groups_by_section(
    section_id: int,
    org_id: UUID = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db)
):
    """Get lab groups for a section."""
    result = await db.execute(
        select(LabGroup).where(
            LabGroup.section_id == section_id,
            LabGroup.organization_id == org_id,
            LabGroup.is_active == True
        )
    )
    return result.scalars().all()
