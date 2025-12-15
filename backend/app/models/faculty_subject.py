"""
Faculty-Subject mapping model.
Supports multiple faculty teaching the same subject.
"""
from sqlalchemy import Column, Integer, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, TimestampMixin


class FacultySubjectMapping(BaseModel, TimestampMixin):
    """
    Maps faculty to subjects they teach.
    One subject can have multiple faculty (e.g., BCS301 taught by Miss Chandana M C and Miss Farheen Fathima S)
    """
    __tablename__ = "faculty_subject_mappings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    
    faculty_id = Column(UUID(as_uuid=True), ForeignKey('faculty.id', ondelete='CASCADE'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False)
    
    # For which section this faculty teaches this subject (optional)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    
    is_active = Column(Boolean, default=True)
    
    # Relationships
    faculty = relationship("Faculty", backref="subject_mappings")
    subject = relationship("Subject", backref="faculty_mappings")
    section = relationship("Section", backref="faculty_subject_mappings")
