"""
User model with Auth0 integration.
"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.models.base import BaseModel, TimestampMixin


class User(BaseModel, TimestampMixin):
    """User entity (linked to Auth0)."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    
    # Auth0 integration
    auth0_user_id = Column(String(255), unique=True)  # Auth0 sub claim
    email = Column(String(255), nullable=False)
    username = Column(String(100))
    
    # Profile
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(20))
    profile_image_url = Column(String(500))
    
    # Role & Status
    role = Column(String(50), nullable=False)  # super_admin, org_admin, faculty, student, staff
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    
    # Security
    last_login = Column(TIMESTAMP(timezone=True))
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(TIMESTAMP(timezone=True))
    
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    
    # Relationships
    organization = relationship("Organization", backref="users")
