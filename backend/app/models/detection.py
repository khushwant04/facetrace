"""
Detection session and attendance SQLAlchemy models.
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum

from app.database import Base


class SessionType(str, enum.Enum):
    """Types of detection sessions."""
    CLASS = "class"
    LAB = "lab"
    EVENT = "event"
    EXAM = "exam"


class SessionStatus(str, enum.Enum):
    """Session status."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DetectionSession(Base):
    """Detection session model."""
    __tablename__ = "detection_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    session_type = Column(SQLEnum(SessionType), nullable=False, default=SessionType.CLASS)
    status = Column(SQLEnum(SessionStatus), nullable=False, default=SessionStatus.SCHEDULED)
    
    # References
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True)
    lab_group_id = Column(Integer, ForeignKey("lab_groups.id"), nullable=True)
    faculty_id = Column(UUID(as_uuid=True), ForeignKey("faculty.id"), nullable=False)
    
    # Timing
    scheduled_start = Column(DateTime, nullable=False)
    scheduled_end = Column(DateTime, nullable=False)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)
    
    # Additional info
    location = Column(String(200), nullable=True)
    description = Column(String(500), nullable=True)
    
    # Statistics
    total_students = Column(Integer, default=0)
    present_count = Column(Integer, default=0)
    absent_count = Column(Integer, default=0)
    late_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    attendance_records = relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan")


class AttendanceRecord(Base):
    """Attendance record model."""
    __tablename__ = "attendance_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    session_id = Column(UUID(as_uuid=True), ForeignKey("detection_sessions.id"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    
    # Detection info
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    confidence = Column(Float, nullable=False)  # Face recognition confidence
    is_late = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    session = relationship("DetectionSession", back_populates="attendance_records")
