"""
Faculty model.
"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.models.base import BaseModel, TimestampMixin


class Faculty(BaseModel, TimestampMixin):
    """Faculty entity."""
    __tablename__ = "faculty"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    employee_id = Column(String(50), nullable=False, unique=True)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=False)
    
    designation = Column(String(100))
    specialization = Column(String(255))
    qualification = Column(String(255))
    experience_years = Column(Integer)
    
    date_of_joining = Column(Date)
    date_of_leaving = Column(Date)
    
    office_location = Column(String(100))
    
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", backref="faculty_profile")
    department = relationship("Department", backref="faculty_members")
