"""
User Pydantic schemas.
"""
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role: str = Field(..., pattern="^(super_admin|org_admin|faculty|student|staff)$")


class UserCreate(UserBase):
    """Schema for creating a user."""
    organization_id: UUID
    auth0_user_id: Optional[str] = None
    profile_image_url: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    profile_image_url: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: UUID
    organization_id: UUID
    auth0_user_id: Optional[str] = None
    profile_image_url: Optional[str] = None
    
    is_active: bool
    is_verified: bool
    email_verified: bool
    
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class CurrentUser(BaseModel):
    """Current authenticated user from Auth0."""
    auth0_user_id: str
    email: Optional[str] = None  # Optional for M2M tokens
    email_verified: bool = False
    permissions: list[str] = []
    org_id: Optional[str] = None
    role: Optional[str] = "super_admin"  # Default for M2M tokens
