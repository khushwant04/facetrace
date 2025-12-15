"""
Student models.
"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Date, TIMESTAMP, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.models.base import BaseModel, TimestampMixin


class Student(BaseModel, TimestampMixin):
    """Student entity."""
    __tablename__ = "students"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    usn = Column(String(50), nullable=False, unique=True)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'))
    lab_group_id = Column(Integer, ForeignKey('lab_groups.id'))
    current_semester = Column(Integer, nullable=False)
    
    admission_year = Column(Integer, nullable=False)
    batch_year = Column(Integer, nullable=False)
    admission_type = Column(String(50))
    
    date_of_birth = Column(Date)
    gender = Column(String(20))
    blood_group = Column(String(5))
    
    permanent_address = Column(Text)
    current_address = Column(Text)
    
    parent_name = Column(String(255))
    parent_phone = Column(String(20))
    parent_email = Column(String(255))
    parent_occupation = Column(String(100))
    
    face_registered = Column(Boolean, default=False)
    face_image_s3_key = Column(String(500))
    face_registered_at = Column(TIMESTAMP(timezone=True))
    
    enrollment_status = Column(String(50), default='active')
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", backref="student_profile")
    department = relationship("Department", backref="students")


class StudentSectionHistory(BaseModel):
    """Student section history."""
    __tablename__ = "student_section_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=False)
    lab_group_id = Column(Integer, ForeignKey('lab_groups.id'))
    semester_id = Column(Integer, ForeignKey('semesters.id'), nullable=False)
    
    assigned_at = Column(TIMESTAMP(timezone=True), server_default='now()')
    unassigned_at = Column(TIMESTAMP(timezone=True))
    is_current = Column(Boolean, default=True)
    reason = Column(Text)
    
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
