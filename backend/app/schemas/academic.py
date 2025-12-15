"""
Academic structure Pydantic schemas.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import date, time, datetime
from uuid import UUID


# Academic Year Schemas
class AcademicYearBase(BaseModel):
    """Base academic year schema."""
    year_name: str = Field(..., min_length=4, max_length=20, pattern=r"^\d{4}-\d{2}$")
    start_date: date
    end_date: date


class AcademicYearCreate(AcademicYearBase):
    """Schema for creating academic year."""
    organization_id: UUID
    is_current: bool = False


class AcademicYearUpdate(BaseModel):
    """Schema for updating academic year."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None


class AcademicYearResponse(AcademicYearBase):
    """Schema for academic year response."""
    id: int
    organization_id: UUID
    is_current: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Department Schemas
class DepartmentBase(BaseModel):
    """Base department schema."""
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=20)
    description: Optional[str] = None
    total_semesters: int = Field(default=8, ge=4, le=10)


class DepartmentCreate(DepartmentBase):
    """Schema for creating department."""
    organization_id: UUID
    hod_id: Optional[UUID] = None


class DepartmentUpdate(BaseModel):
    """Schema for updating department."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    hod_id: Optional[UUID] = None
    total_semesters: Optional[int] = Field(None, ge=4, le=10)
    is_active: Optional[bool] = None


class DepartmentResponse(DepartmentBase):
    """Schema for department response."""
    id: int
    organization_id: UUID
    hod_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# Semester Schemas
class SemesterBase(BaseModel):
    """Base semester schema."""
    semester_number: int = Field(..., ge=1, le=8)
    semester_type: str = Field(..., pattern="^(odd|even)$")
    start_date: date
    end_date: date


class SemesterCreate(SemesterBase):
    """Schema for creating semester."""
    organization_id: UUID
    academic_year_id: int
    is_active: bool = True


class SemesterUpdate(BaseModel):
    """Schema for updating semester."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


class SemesterResponse(SemesterBase):
    """Schema for semester response."""
    id: int
    organization_id: UUID
    academic_year_id: int
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Section Schemas
class SectionBase(BaseModel):
    """Base section schema."""
    name: str = Field(..., min_length=1, max_length=10)
    batch_year: int = Field(..., ge=2020, le=2030)
    capacity: int = Field(default=60, ge=1, le=100)


class SectionCreate(SectionBase):
    """Schema for creating section."""
    organization_id: UUID
    department_id: int
    semester_id: int
    class_representative_id: Optional[UUID] = None


class SectionUpdate(BaseModel):
    """Schema for updating section."""
    capacity: Optional[int] = Field(None, ge=1, le=100)
    class_representative_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class SectionResponse(SectionBase):
    """Schema for section response."""
    id: int
    organization_id: UUID
    department_id: int
    semester_id: int
    class_representative_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# Lab Group Schemas
class LabGroupBase(BaseModel):
    """Base lab group schema."""
    name: str = Field(..., min_length=1, max_length=10, pattern=r"^[A-Z]\d$")
    capacity: int = Field(default=30, ge=1, le=50)


class LabGroupCreate(LabGroupBase):
    """Schema for creating lab group."""
    organization_id: UUID
    section_id: int


class LabGroupUpdate(BaseModel):
    """Schema for updating lab group."""
    capacity: Optional[int] = Field(None, ge=1, le=50)
    is_active: Optional[bool] = None


class LabGroupResponse(LabGroupBase):
    """Schema for lab group response."""
    id: int
    organization_id: UUID
    section_id: int
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
