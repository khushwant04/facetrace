"""
Face recognition Pydantic schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from uuid import UUID


class FaceUploadResponse(BaseModel):
    """Response after face image upload."""
    success: bool
    message: str
    embedding_id: Optional[str] = None
    s3_key: Optional[str] = None
    s3_url: Optional[str] = None
    embedding_dimension: Optional[int] = None
    face_quality: Optional[Dict] = None


class FaceSearchRequest(BaseModel):
    """Request for face search."""
    image: str = Field(..., description="Base64 encoded image")
    top_k: int = Field(5, ge=1, le=20)
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0)


class FaceMatch(BaseModel):
    """Single face match result."""
    student_id: UUID
    student_name: Optional[str] = None
    usn: Optional[str] = None
    similarity: float
    embedding_id: str
    matched_at: datetime = Field(default_factory=datetime.utcnow)


class FaceSearchResponse(BaseModel):
    """Response for face search."""
    success: bool
    matches_found: int
    matches: List[FaceMatch]
    query_face_detected: bool
    processing_time_ms: float


class FaceValidationResponse(BaseModel):
    """Response for face validation."""
    is_valid: bool
    message: str
    face_count: int
    confidence: Optional[float] = None
    recommendations: List[str] = []
