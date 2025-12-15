"""
Organization Pydantic schemas.
"""
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


class OrganizationBase(BaseModel):
    """Base organization schema."""
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100, pattern="^[a-z0-9-]+$")
    type: str = Field(default="college")
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: str = Field(default="India", max_length=100)
    website: Optional[str] = Field(None, max_length=255)


class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization."""
    subscription_plan: str = Field(default="free", pattern="^(free|basic|premium|enterprise)$")
    max_students: int = Field(default=500, ge=1, le=10000)
    max_faculty: int = Field(default=50, ge=1, le=500)
    max_departments: int = Field(default=10, ge=1, le=50)


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=255)
    
    subscription_plan: Optional[str] = Field(None, pattern="^(free|basic|premium|enterprise)$")
    subscription_status: Optional[str] = Field(None, pattern="^(active|trial|suspended|cancelled)$")
    
    max_students: Optional[int] = Field(None, ge=1, le=10000)
    max_faculty: Optional[int] = Field(None, ge=1, le=500)
    max_departments: Optional[int] = Field(None, ge=1, le=50)
    
    is_active: Optional[bool] = None


class OrganizationResponse(OrganizationBase):
    """Schema for organization response."""
    id: UUID
    subscription_plan: str
    subscription_status: str
    subscription_started_at: Optional[datetime] = None
    subscription_expires_at: Optional[datetime] = None
    
    max_students: int
    max_faculty: int
    max_departments: int
    
    features: dict
    
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class OrganizationStats(BaseModel):
    """Organization statistics."""
    total_students: int
    total_faculty: int
    total_departments: int
    total_sections: int
    active_detections: int
    storage_used_mb: float
