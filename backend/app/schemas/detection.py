"""
Detection session Pydantic schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class SessionType(str, Enum):
    """Types of detection sessions."""
    CLASS = "class"
    LAB = "lab"
    EVENT = "event"
    EXAM = "exam"


class SessionStatus(str, Enum):
    """Session status."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DetectionSessionCreate(BaseModel):
    """Create detection session."""
    organization_id: UUID
    session_type: SessionType
    subject_id: Optional[int] = None
    section_id: Optional[int] = None
    lab_group_id: Optional[int] = None
    faculty_id: UUID
    scheduled_start: datetime
    scheduled_end: datetime
    location: Optional[str] = None
    description: Optional[str] = None


class DetectionSessionResponse(BaseModel):
    """Detection session response."""
    id: UUID
    session_type: SessionType
    status: SessionStatus
    subject_id: Optional[int]
    section_id: Optional[int]
    faculty_id: UUID
    scheduled_start: datetime
    scheduled_end: datetime
    actual_start: Optional[datetime]
    actual_end: Optional[datetime]
    location: Optional[str]
    total_students: int
    present_count: int
    absent_count: int
    late_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class AttendanceRecordCreate(BaseModel):
    """Create attendance record."""
    session_id: UUID
    student_id: UUID
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(..., ge=0.0, le=1.0)
    is_late: bool = False


class AttendanceRecordResponse(BaseModel):
    """Attendance record response."""
    id: UUID
    session_id: UUID
    student_id: UUID
    student_name: Optional[str]
    usn: Optional[str]
    detected_at: datetime
    confidence: float
    is_late: bool
    
    class Config:
        from_attributes = True


class SessionSummary(BaseModel):
    """Session attendance summary."""
    session_id: UUID
    session_type: SessionType
    total_students: int
    present: int
    absent: int
    late: int
    attendance_rate: float
    start_time: datetime
    end_time: Optional[datetime]
