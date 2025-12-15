"""
Subject/Course model.
"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel, TimestampMixin


class Subject(BaseModel, TimestampMixin):
    """Subject/Course entity."""
    __tablename__ = "subjects"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    
    code = Column(String(20), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    
    department_id = Column(Integer, ForeignKey('departments.id'))
    semester_number = Column(Integer, nullable=False)
    
    credits = Column(Integer, default=3)
    subject_type = Column(String(50))  # theory, lab, project, seminar
    is_elective = Column(Boolean, default=False)
    
    syllabus_url = Column(String(500))
    
    is_active = Column(Boolean, default=True)
