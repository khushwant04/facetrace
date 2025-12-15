"""
Invitation and onboarding schemas.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class OnboardingStatus(str, Enum):
    INVITED = "invited"
    REGISTERED = "registered"
    PROFILE_COMPLETE = "profile_complete"
    FACE_REGISTERED = "face_registered"
    ACTIVE = "active"


# ============ Invitation Schemas ============

class InvitationCreate(BaseModel):
    """Create single invitation."""
    email: EmailStr
    role: str = Field(..., pattern="^(student|faculty|org_admin)$")
    usn: Optional[str] = None
    department_id: Optional[int] = None
    section_id: Optional[int] = None
    semester: Optional[int] = None
    employee_id: Optional[str] = None


class BulkInvitationCreate(BaseModel):
    """Bulk invite students/faculty."""
    invitations: List[InvitationCreate]


class InvitationResponse(BaseModel):
    id: UUID
    email: str
    role: str
    usn: Optional[str] = None
    status: str
    expires_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class InvitationAccept(BaseModel):
    """Accept invitation with Auth0 token."""
    token: str


class InvitationVerify(BaseModel):
    """Verify invitation token."""
    token: str


class InvitationVerifyResponse(BaseModel):
    valid: bool
    organization_name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    usn: Optional[str] = None
    message: str


# ============ Join Code Schemas ============

class JoinCodeCreate(BaseModel):
    """Create organization join code."""
    code: str = Field(..., min_length=4, max_length=50)
    role: str = "student"
    department_id: Optional[int] = None
    max_uses: Optional[int] = None
    expires_at: Optional[datetime] = None
    requires_approval: bool = False


class JoinCodeResponse(BaseModel):
    id: UUID
    code: str
    role: str
    department_id: Optional[int] = None
    max_uses: Optional[int] = None
    current_uses: int
    is_active: bool
    expires_at: Optional[datetime] = None
    requires_approval: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class JoinWithCode(BaseModel):
    """Join organization with code."""
    code: str
    usn: Optional[str] = None  # Student provides their USN
    employee_id: Optional[str] = None  # Faculty provides employee ID


class JoinCodeVerify(BaseModel):
    """Verify join code."""
    code: str


class JoinCodeVerifyResponse(BaseModel):
    valid: bool
    organization_name: Optional[str] = None
    role: Optional[str] = None
    department_name: Optional[str] = None
    requires_approval: bool = False
    message: str


# ============ Onboarding Schemas ============

class OnboardingStatusResponse(BaseModel):
    status: str
    email_verified: bool
    profile_completed: bool
    face_registered: bool
    requires_approval: bool
    approved: bool
    next_step: str
    face_registration_deadline: Optional[datetime] = None


class ProfileComplete(BaseModel):
    """Complete user profile."""
    first_name: str
    last_name: str
    phone: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    # Student specific
    usn: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    # Address
    current_address: Optional[str] = None


class PendingApprovalResponse(BaseModel):
    id: UUID
    user_id: UUID
    email: str
    name: str
    role: str
    usn: Optional[str] = None
    requested_at: datetime
    
    class Config:
        from_attributes = True


class ApprovalAction(BaseModel):
    """Approve or reject user."""
    user_id: UUID
    action: str = Field(..., pattern="^(approve|reject)$")
    rejection_reason: Optional[str] = None
