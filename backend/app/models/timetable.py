"""
Timetable model.
"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Time, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel, TimestampMixin


class TimetableSlot(BaseModel, TimestampMixin):
    """Timetable slot entity."""
    __tablename__ = "timetable_slots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    
    section_id = Column(Integer, ForeignKey('sections.id'))
    lab_group_id = Column(Integer, ForeignKey('lab_groups.id'))
    
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    faculty_id = Column(UUID(as_uuid=True), ForeignKey('faculty.id'), nullable=True)  # Nullable - assign later
    
    day_of_week = Column(String(10), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    
    room_no = Column(String(50))
    building = Column(String(100))
    
    slot_type = Column(String(50), default='lecture')
    
    notes = Column(Text)
    
    is_active = Column(Boolean, default=True)
