"""
Onboarding API - Works with Auth0 Organizations.
- Super admin creates org in Auth0 + our DB
- Users are invited via Auth0 Organization invitations
- Or use join codes for self-service registration
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from datetime import datetime
from typing import List

from app.database import get_db
from app.core.security import get_user_from_bearer_token
from app.core.permissions import get_current_user, require_org_admin, require_super_admin
from app.core.context import get_organization_id
from app.models.user import User
from app.models.student import Student
from app.models.faculty import Faculty
from app.models.organization import Organization
from app.models.academic import Department
from app.models.invitation import (
    Invitation, OrganizationJoinCode, UserOnboarding,
    InvitationStatus, OnboardingStatus
)
from app.schemas.invitation import (
    InvitationCreate, BulkInvitationCreate, InvitationResponse,
    InvitationVerify, InvitationVerifyResponse,
    JoinCodeCreate, JoinCodeResponse, JoinWithCode,
    JoinCodeVerify, JoinCodeVerifyResponse,
    OnboardingStatusResponse, ProfileComplete,
    PendingApprovalResponse, ApprovalAction
)
from app.schemas.common import MessageResponse

router = APIRouter()


# ============ USER REGISTRATION (After Auth0 Login) ============

@router.post("/register", response_model=MessageResponse)
async def register_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Register user after Auth0 login.
    Called when user logs in via Auth0 Organization for first time.
    Auth0 org_id in token determines which organization.
    """
    auth_user = await get_user_from_bearer_token(authorization)
    
    auth0_org_id = auth_user.get("org_id")
    if not auth0_org_id:
        raise HTTPException(400, "Login via organization required. Use organization login URL.")
    
    # Check if already registered
    existing = await db.execute(
        select(User).where(User.auth0_user_id == auth_user.get("sub"))
    )
    if existing.scalar_one_or_none():
        return MessageResponse(message="Already registered", success=True)
    
    # Find organization by Auth0 org_id
    org_result = await db.execute(
        select(Organization).where(Organization.auth0_org_id == auth0_org_id)
    )
    org = org_result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(404, "Organization not found. Contact administrator.")
    
    # Check for pending invitation (optional - for role assignment)
    invite_result = await db.execute(
        select(Invitation).where(
            and_(
                Invitation.email == auth_user.get("email"),
                Invitation.organization_id == org.id,
                Invitation.status == InvitationStatus.PENDING.value
            )
        )
    )
    invitation = invite_result.scalar_one_or_none()
    
    # Determine role
    role = "student"  # Default
    usn = None
    department_id = None
    
    if invitation:
        role = invitation.role
        usn = invitation.usn
        department_id = invitation.department_id
        invitation.status = InvitationStatus.ACCEPTED.value
        invitation.accepted_at = datetime.utcnow()
    
    # Create user
    user = User(
        organization_id=org.id,
        auth0_user_id=auth_user.get("sub"),
        email=auth_user.get("email"),
        role=role,
        email_verified=auth_user.get("email_verified", False),
        is_active=True,
        is_verified=True
    )
    db.add(user)
    await db.flush()
    
    # Create role-specific record
    if role == "student":
        student = Student(
            organization_id=org.id,
            user_id=user.id,
            usn=usn or f"PENDING-{str(user.id)[:8]}",
            department_id=department_id or 1,
            current_semester=1,
            admission_year=datetime.now().year,
            batch_year=datetime.now().year + 4
        )
        db.add(student)
    elif role == "faculty":
        faculty = Faculty(
            organization_id=org.id,
            user_id=user.id,
            employee_id=f"FAC-{str(user.id)[:8]}",
            department_id=department_id or 1
        )
        db.add(faculty)
    
    # Create onboarding tracker
    onboarding = UserOnboarding(
        user_id=user.id,
        organization_id=org.id,
        status=OnboardingStatus.REGISTERED.value,
        email_verified=auth_user.get("email_verified", False)
    )
    db.add(onboarding)
    
    if invitation:
        invitation.accepted_by_user_id = user.id
    
    await db.commit()
    
    return MessageResponse(message="Registration complete. Please complete your profile.", success=True)


# ============ INVITATION ENDPOINTS (For pre-assigning roles) ============

@router.post("/invitations", response_model=InvitationResponse, status_code=201)
async def create_invitation(
    data: InvitationCreate,
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create invitation to pre-assign role/USN before user registers.
    User still needs to be invited via Auth0 Organization.
    """
    # Check if already invited
    existing = await db.execute(
        select(Invitation).where(
            and_(
                Invitation.email == data.email,
                Invitation.organization_id == org_id,
                Invitation.status == InvitationStatus.PENDING.value
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Invitation already exists for this email")
    
    invitation = Invitation(
        organization_id=org_id,
        email=data.email,
        role=data.role,
        usn=data.usn,
        department_id=data.department_id,
        section_id=data.section_id,
        semester=data.semester,
        employee_id=data.employee_id,
        token=Invitation.generate_token(),
        expires_at=Invitation.default_expiry(),
        invited_by=UUID(current_user.get("user_id"))
    )
    
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    
    # Note: Actual Auth0 invitation should be sent via Auth0 Management API
    # This just pre-registers the role assignment
    
    return invitation


@router.post("/invitations/bulk", response_model=MessageResponse)
async def bulk_invite(
    data: BulkInvitationCreate,
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Bulk create invitations (pre-assign roles for multiple users)."""
    created = 0
    skipped = 0
    
    for inv_data in data.invitations:
        existing = await db.execute(
            select(Invitation).where(
                and_(
                    Invitation.email == inv_data.email,
                    Invitation.organization_id == org_id,
                    Invitation.status == InvitationStatus.PENDING.value
                )
            )
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        
        invitation = Invitation(
            organization_id=org_id,
            email=inv_data.email,
            role=inv_data.role,
            usn=inv_data.usn,
            department_id=inv_data.department_id,
            section_id=inv_data.section_id,
            semester=inv_data.semester,
            employee_id=inv_data.employee_id,
            token=Invitation.generate_token(),
            expires_at=Invitation.default_expiry(),
            invited_by=UUID(current_user.get("user_id"))
        )
        db.add(invitation)
        created += 1
    
    await db.commit()
    
    return MessageResponse(
        message=f"Created {created} invitations, skipped {skipped} duplicates",
        success=True
    )


@router.get("/invitations", response_model=List[InvitationResponse])
async def list_invitations(
    status: str = None,
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all invitations for organization."""
    query = select(Invitation).where(Invitation.organization_id == org_id)
    if status:
        query = query.where(Invitation.status == status)
    
    result = await db.execute(query.order_by(Invitation.created_at.desc()))
    return result.scalars().all()


@router.delete("/invitations/{invitation_id}", response_model=MessageResponse)
async def revoke_invitation(
    invitation_id: UUID,
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Revoke a pending invitation."""
    result = await db.execute(
        select(Invitation).where(
            and_(Invitation.id == invitation_id, Invitation.organization_id == org_id)
        )
    )
    invitation = result.scalar_one_or_none()
    
    if not invitation:
        raise HTTPException(404, "Invitation not found")
    
    invitation.status = InvitationStatus.REVOKED.value
    await db.commit()
    
    return MessageResponse(message="Invitation revoked", success=True)


# ============ JOIN CODE ENDPOINTS (Self-service) ============

@router.post("/join-codes", response_model=JoinCodeResponse, status_code=201)
async def create_join_code(
    data: JoinCodeCreate,
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create join code for self-service registration."""
    existing = await db.execute(
        select(OrganizationJoinCode).where(OrganizationJoinCode.code == data.code.upper())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Join code already exists")
    
    join_code = OrganizationJoinCode(
        organization_id=org_id,
        code=data.code.upper(),
        role=data.role,
        department_id=data.department_id,
        max_uses=data.max_uses,
        expires_at=data.expires_at,
        requires_approval=data.requires_approval,
        created_by=UUID(current_user.get("user_id"))
    )
    
    db.add(join_code)
    await db.commit()
    await db.refresh(join_code)
    
    return join_code


@router.get("/join-codes", response_model=List[JoinCodeResponse])
async def list_join_codes(
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all join codes for organization."""
    result = await db.execute(
        select(OrganizationJoinCode).where(OrganizationJoinCode.organization_id == org_id)
    )
    return result.scalars().all()


@router.post("/join-codes/verify", response_model=JoinCodeVerifyResponse)
async def verify_join_code(
    data: JoinCodeVerify,
    db: AsyncSession = Depends(get_db)
):
    """Verify join code (public endpoint)."""
    result = await db.execute(
        select(OrganizationJoinCode).where(OrganizationJoinCode.code == data.code.upper())
    )
    join_code = result.scalar_one_or_none()
    
    if not join_code:
        return JoinCodeVerifyResponse(valid=False, message="Invalid join code")
    
    if not join_code.is_valid:
        return JoinCodeVerifyResponse(valid=False, message="Join code expired or limit reached")
    
    org_result = await db.execute(
        select(Organization).where(Organization.id == join_code.organization_id)
    )
    org = org_result.scalar_one()
    
    dept_name = None
    if join_code.department_id:
        dept_result = await db.execute(
            select(Department).where(Department.id == join_code.department_id)
        )
        dept = dept_result.scalar_one_or_none()
        dept_name = dept.name if dept else None
    
    return JoinCodeVerifyResponse(
        valid=True,
        organization_name=org.name,
        role=join_code.role,
        department_name=dept_name,
        requires_approval=join_code.requires_approval,
        message="Valid join code"
    )


@router.post("/join-codes/use", response_model=MessageResponse)
async def use_join_code(
    data: JoinWithCode,
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Use join code to set role after Auth0 registration.
    User must already be logged in via Auth0 Organization.
    """
    auth_user = await get_user_from_bearer_token(authorization)
    
    # Get join code
    result = await db.execute(
        select(OrganizationJoinCode).where(OrganizationJoinCode.code == data.code.upper())
    )
    join_code = result.scalar_one_or_none()
    
    if not join_code or not join_code.is_valid:
        raise HTTPException(400, "Invalid or expired join code")
    
    # Find user
    user_result = await db.execute(
        select(User).where(User.auth0_user_id == auth_user.get("sub"))
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(404, "User not found. Register first.")
    
    # Verify org matches
    if user.organization_id != join_code.organization_id:
        raise HTTPException(400, "Join code is for a different organization")
    
    # Update role if student and USN provided
    if join_code.role == "student" and data.usn:
        student_result = await db.execute(
            select(Student).where(Student.user_id == user.id)
        )
        student = student_result.scalar_one_or_none()
        if student:
            # Check USN uniqueness
            usn_check = await db.execute(
                select(Student).where(
                    and_(Student.usn == data.usn, Student.id != student.id)
                )
            )
            if usn_check.scalar_one_or_none():
                raise HTTPException(400, "USN already registered")
            
            student.usn = data.usn
            if join_code.department_id:
                student.department_id = join_code.department_id
    
    # Increment usage
    join_code.current_uses += 1
    await db.commit()
    
    return MessageResponse(message="Join code applied successfully", success=True)


@router.delete("/join-codes/{code_id}", response_model=MessageResponse)
async def deactivate_join_code(
    code_id: UUID,
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate a join code."""
    result = await db.execute(
        select(OrganizationJoinCode).where(
            and_(OrganizationJoinCode.id == code_id, OrganizationJoinCode.organization_id == org_id)
        )
    )
    join_code = result.scalar_one_or_none()
    
    if not join_code:
        raise HTTPException(404, "Join code not found")
    
    join_code.is_active = False
    await db.commit()
    
    return MessageResponse(message="Join code deactivated", success=True)


# ============ ONBOARDING STATUS ============

@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's onboarding status."""
    user_id = UUID(current_user.get("user_id"))
    
    onboarding_result = await db.execute(
        select(UserOnboarding).where(UserOnboarding.user_id == user_id)
    )
    onboarding = onboarding_result.scalar_one_or_none()
    
    if not onboarding:
        # Create onboarding record if missing
        onboarding = UserOnboarding(
            user_id=user_id,
            organization_id=UUID(current_user.get("organization_id")),
            status=OnboardingStatus.REGISTERED.value
        )
        db.add(onboarding)
        await db.commit()
        await db.refresh(onboarding)
    
    # Determine next step
    next_step = "dashboard"
    if onboarding.requires_approval and not onboarding.approved_at:
        next_step = "awaiting_approval"
    elif not onboarding.profile_completed:
        next_step = "complete_profile"
    elif not onboarding.face_registered and current_user.get("role") == "student":
        next_step = "register_face"
    
    return OnboardingStatusResponse(
        status=onboarding.status,
        email_verified=onboarding.email_verified,
        profile_completed=onboarding.profile_completed,
        face_registered=onboarding.face_registered,
        requires_approval=onboarding.requires_approval,
        approved=onboarding.approved_at is not None,
        next_step=next_step,
        face_registration_deadline=onboarding.face_registration_deadline
    )


@router.post("/complete-profile", response_model=MessageResponse)
async def complete_profile(
    data: ProfileComplete,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Complete user profile during onboarding."""
    user_id = UUID(current_user.get("user_id"))
    
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one()
    
    # Update user profile
    user.first_name = data.first_name
    user.last_name = data.last_name
    user.phone = data.phone
    
    # Update student-specific fields
    if current_user.get("role") == "student":
        student_result = await db.execute(
            select(Student).where(Student.user_id == user_id)
        )
        student = student_result.scalar_one_or_none()
        
        if student:
            if data.usn and student.usn.startswith("PENDING"):
                # Check USN uniqueness
                usn_check = await db.execute(
                    select(Student).where(
                        and_(Student.usn == data.usn, Student.id != student.id)
                    )
                )
                if usn_check.scalar_one_or_none():
                    raise HTTPException(400, "USN already registered")
                student.usn = data.usn
            
            student.date_of_birth = data.date_of_birth
            student.gender = data.gender
            student.parent_name = data.parent_name
            student.parent_phone = data.parent_phone
            student.current_address = data.current_address
    
    # Update onboarding status
    onboarding_result = await db.execute(
        select(UserOnboarding).where(UserOnboarding.user_id == user_id)
    )
    onboarding = onboarding_result.scalar_one_or_none()
    
    if onboarding:
        onboarding.profile_completed = True
        onboarding.status = OnboardingStatus.PROFILE_COMPLETE.value
        
        if current_user.get("role") == "student":
            from datetime import timedelta
            onboarding.face_registration_deadline = datetime.utcnow() + timedelta(days=7)
    
    await db.commit()
    
    if current_user.get("role") == "student":
        return MessageResponse(message="Profile complete. Register your face within 7 days.", success=True)
    
    return MessageResponse(message="Profile complete.", success=True)


# ============ APPROVAL ENDPOINTS ============

@router.get("/approvals/pending", response_model=List[PendingApprovalResponse])
async def list_pending_approvals(
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """List users pending approval."""
    result = await db.execute(
        select(UserOnboarding, User).join(User, UserOnboarding.user_id == User.id).where(
            and_(
                UserOnboarding.organization_id == org_id,
                UserOnboarding.requires_approval == True,
                UserOnboarding.approved_at == None
            )
        )
    )
    
    pending = []
    for onboarding, user in result.all():
        pending.append(PendingApprovalResponse(
            id=onboarding.id,
            user_id=user.id,
            email=user.email,
            name=f"{user.first_name or ''} {user.last_name or ''}".strip() or "Not provided",
            role=user.role,
            requested_at=onboarding.created_at
        ))
    
    return pending


@router.post("/approvals/action", response_model=MessageResponse)
async def process_approval(
    data: ApprovalAction,
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Approve or reject a user."""
    result = await db.execute(
        select(UserOnboarding).where(
            and_(
                UserOnboarding.user_id == data.user_id,
                UserOnboarding.organization_id == org_id
            )
        )
    )
    onboarding = result.scalar_one_or_none()
    
    if not onboarding:
        raise HTTPException(404, "User not found")
    
    user_result = await db.execute(select(User).where(User.id == data.user_id))
    user = user_result.scalar_one()
    
    if data.action == "approve":
        onboarding.approved_by = UUID(current_user.get("user_id"))
        onboarding.approved_at = datetime.utcnow()
        user.is_active = True
        user.is_verified = True
        message = "User approved"
    else:
        onboarding.rejection_reason = data.rejection_reason
        user.is_active = False
        message = "User rejected"
    
    await db.commit()
    
    return MessageResponse(message=message, success=True)
