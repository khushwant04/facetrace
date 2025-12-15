"""
Invitation and onboarding models for SaaS multi-tenancy.
"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DateTime, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timedelta
import enum
import secrets


class InvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class OnboardingStatus(str, enum.Enum):
    INVITED = "invited"
    REGISTERED = "registered"
    PROFILE_COMPLETE = "profile_complete"
    FACE_REGISTERED = "face_registered"
    ACTIVE = "active"


from app.models.base import BaseModel, TimestampMixin


class Invitation(BaseModel, TimestampMixin):
    """
    Invitation for users to join an organization.
    Supports bulk invitations for students/faculty.
    """
    __tablename__ = "invitations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    
    # Invitation details
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # student, faculty, org_admin
    
    # For students - pre-fill data
    usn = Column(String(50), nullable=True)  # Pre-assigned USN
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    semester = Column(Integer, nullable=True)
    
    # For faculty
    employee_id = Column(String(50), nullable=True)
    
    # Invitation token
    token = Column(String(100), unique=True, nullable=False, index=True)
    
    # Status tracking
    status = Column(String(20), default=InvitationStatus.PENDING.value)
    expires_at = Column(DateTime, nullable=False)
    
    # Tracking
    invited_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    accepted_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    
    # Relationships
    organization = relationship("Organization", backref="invitations")
    inviter = relationship("User", foreign_keys=[invited_by], backref="sent_invitations")
    
    @classmethod
    def generate_token(cls) -> str:
        return secrets.token_urlsafe(32)
    
    @classmethod
    def default_expiry(cls) -> datetime:
        return datetime.utcnow() + timedelta(days=7)
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        return self.status == InvitationStatus.PENDING.value and not self.is_expired


class OrganizationJoinCode(BaseModel, TimestampMixin):
    """
    Self-service join codes for organizations.
    Students can use this to join their college without individual invites.
    """
    __tablename__ = "organization_join_codes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    
    # Join code (e.g., "RVCE2024", "PESIT-CSE")
    code = Column(String(50), unique=True, nullable=False, index=True)
    
    # Restrictions
    role = Column(String(50), default="student")  # What role users get
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True)  # Restrict to department
    
    # Limits
    max_uses = Column(Integer, nullable=True)  # None = unlimited
    current_uses = Column(Integer, default=0)
    
    # Validity
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)  # None = never expires
    
    # Requires approval?
    requires_approval = Column(Boolean, default=False)
    
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Relationships
    organization = relationship("Organization", backref="join_codes")
    
    @property
    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        return True


class UserOnboarding(BaseModel, TimestampMixin):
    """
    Track user onboarding progress.
    """
    __tablename__ = "user_onboarding"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    
    # Onboarding status
    status = Column(String(30), default=OnboardingStatus.INVITED.value)
    
    # Step completion tracking
    email_verified = Column(Boolean, default=False)
    profile_completed = Column(Boolean, default=False)
    face_registered = Column(Boolean, default=False)
    
    # For students requiring face registration
    face_registration_deadline = Column(DateTime, nullable=True)
    face_registration_reminder_sent = Column(Boolean, default=False)
    
    # Approval workflow (if requires_approval)
    requires_approval = Column(Boolean, default=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="onboarding")
