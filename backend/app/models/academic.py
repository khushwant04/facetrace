"""
Academic structure models (Years, Departments, Semesters, Sections, Lab Groups).
"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Date, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, TimestampMixin


class AcademicYear(BaseModel, TimestampMixin):
    """Academic year entity."""
    __tablename__ = "academic_years"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    
    year_name = Column(String(20), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_current = Column(Boolean, default=False)


class Department(BaseModel, TimestampMixin):
    """Department/Branch entity."""
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    
    name = Column(String(255), nullable=False)
    code = Column(String(20), nullable=False)
    description = Column(String)
    
    hod_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    total_semesters = Column(Integer, default=8)
    
    is_active = Column(Boolean, default=True)


class Semester(BaseModel, TimestampMixin):
    """Semester entity (odd/even)."""
    __tablename__ = "semesters"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id', ondelete='CASCADE'), nullable=False)
    
    semester_number = Column(Integer, nullable=False)  # 1-8
    semester_type = Column(String(10), nullable=False)  # odd, even
    
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    is_active = Column(Boolean, default=True)


class Section(BaseModel, TimestampMixin):
    """
    Section entity (A, B, C).
    Maps to classes.csv: CSE-AIML-3-A, CSE-AIML-5-B, etc.
    """
    __tablename__ = "sections"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    department_id = Column(Integer, ForeignKey('departments.id', ondelete='CASCADE'), nullable=False)
    
    # Section identifier (e.g., "CSE-AIML-3-A")
    class_id = Column(String(50), unique=True, nullable=True)
    
    name = Column(String(10), nullable=False)  # A, B, C
    semester = Column(Integer, nullable=False)  # 3, 5, 7
    batch_year = Column(Integer, nullable=False)
    
    # Room assigned to this section
    room_no = Column(String(20))
    
    # Class teacher (faculty)
    class_teacher_id = Column(UUID(as_uuid=True), ForeignKey('faculty.id'))
    
    capacity = Column(Integer, default=60)
    class_representative_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    
    is_active = Column(Boolean, default=True)
    
    # Relationships
    class_teacher = relationship("Faculty", foreign_keys=[class_teacher_id])


class LabGroup(BaseModel, TimestampMixin):
    """Lab group entity (A1, A2, B1, B2)."""
    __tablename__ = "lab_groups"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id', ondelete='CASCADE'), nullable=False)
    
    name = Column(String(10), nullable=False)
    capacity = Column(Integer, default=30)
    
    is_active = Column(Boolean, default=True)
