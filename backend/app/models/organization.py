"""
Organization model for multi-tenancy with Auth0 Organizations.
"""
from sqlalchemy import Column, String, Boolean, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.models.base import BaseModel, TimestampMixin


class Organization(BaseModel, TimestampMixin):
    """
    Organization/College entity.
    Each organization maps to an Auth0 Organization.
    """
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Auth0 Organization ID (e.g., "org_abc123")
    # This links our org to Auth0 Organization
    auth0_org_id = Column(String(50), unique=True, nullable=True, index=True)
    
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    type = Column(String(50), default='college')
    email = Column(String(255), nullable=False)
    phone = Column(String(20))
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100), default='India')
    website = Column(String(255))
    
    subscription_plan = Column(String(50), default='free')
    subscription_status = Column(String(50), default='active')
    subscription_started_at = Column(TIMESTAMP(timezone=True))
    subscription_expires_at = Column(TIMESTAMP(timezone=True))
    
    max_students = Column(Integer, default=500)
    max_faculty = Column(Integer, default=50)
    max_departments = Column(Integer, default=10)
    
    features = Column(JSONB, default={"face_recognition": True, "attendance": True})
    
    is_active = Column(Boolean, default=True)
