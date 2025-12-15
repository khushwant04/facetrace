"""
User management endpoints (Admin only).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from typing import List
from uuid import UUID

from app.database import get_db
from app.core.permissions import require_org_admin
from app.core.context import get_organization_id
from app.models.user import User
from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.schemas.common import PaginatedResponse, MessageResponse

router = APIRouter()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_create: UserCreate,
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user (Admin only).
    """
    # Check if email already exists in organization
    result = await db.execute(
        select(User).where(
            User.organization_id == user_create.organization_id,
            User.email == user_create.email
        )
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists in organization"
        )
    
    # Create user
    new_user = User(**user_create.model_dump())
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user


@router.get("/", response_model=PaginatedResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role: str = Query(None),
    is_active: bool = Query(None),
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List users in organization (paginated).
    """
    # Build query
    query = select(User).where(User.organization_id == org_id)
    
    if role:
        query = query.where(User.role == role)
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": users
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user by ID.
    """
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == org_id
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_update: UserUpdate,
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user by ID (Admin only).
    """
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == org_id
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    update_data = user_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    
    return user


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: UUID,
    org_id: UUID = Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete user (set is_active=False).
    """
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == org_id
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Soft delete
    user.is_active = False
    await db.commit()
    
    return MessageResponse(
        message=f"User {user.email} has been deactivated",
        success=True
    )
