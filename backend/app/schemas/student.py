"""
Student Pydantic schemas.
"""
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import date, datetime
from uuid import UUID
from app.schemas.common import PaginatedResponse


class StudentBase(BaseModel):
    """Base student schema."""
    usn: str = Field(..., min_length=5, max_length=50)
    current_semester: int = Field(..., ge=1, le=8)
    admission_year: int = Field(..., ge=2020, le=2030)
    batch_year: int = Field(..., ge=2020, le=2035)
    admission_type: Optional[str] = Field(None, max_length=50)
    
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=20)
    blood_group: Optional[str] = Field(None, max_length=5)
    
    permanent_address: Optional[str] = None
    current_address: Optional[str] = None
    
    parent_name: Optional[str] = Field(None, max_length=255)
    parent_phone: Optional[str] = Field(None, max_length=20)
    parent_email: Optional[EmailStr] = None
    parent_occupation: Optional[str] = Field(None, max_length=100)


class StudentCreate(StudentBase):
    """Schema for creating student."""
    organization_id: UUID
    user_id: UUID
    department_id: int
    section_id: Optional[int] = None
    lab_group_id: Optional[int] = None


class StudentUpdate(BaseModel):
    """Schema for updating student."""
    current_semester: Optional[int] = Field(None, ge=1, le=8)
    section_id: Optional[int] = None
    lab_group_id: Optional[int] = None
    
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=20)
    blood_group: Optional[str] = Field(None, max_length=5)
    
    permanent_address: Optional[str] = None
    current_address: Optional[str] = None
    
    parent_name: Optional[str] = Field(None, max_length=255)
    parent_phone: Optional[str] = Field(None, max_length=20)
    parent_email: Optional[EmailStr] = None
    
    enrollment_status: Optional[str] = Field(None, pattern="^(active|suspended|graduated|dropout)$")
    is_active: Optional[bool] = None


class StudentResponse(StudentBase):
    """Schema for student response."""
    id: UUID
    organization_id: UUID
    user_id: UUID
    department_id: int
    section_id: Optional[int] = None
    lab_group_id: Optional[int] = None
    
    face_registered: bool
    face_image_s3_key: Optional[str] = None
    face_registered_at: Optional[datetime] = None
    
    enrollment_status: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class StudentBulkUpload(BaseModel):
    """Schema for bulk student upload."""
    students: list[StudentCreate]


class StudentSectionAssignment(BaseModel):
    """Schema for assigning student to section."""
    section_id: int
    lab_group_id: Optional[int] = None
    reason: Optional[str] = None


class PaginatedStudentResponse(PaginatedResponse):
    """Paginated response for students."""
    items: list[StudentResponse]
