"""
Face embedding SQLAlchemy model.
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.database import Base


class FaceEmbedding(Base):
    """Face embedding metadata model."""
    __tablename__ = "face_embeddings"
    
    id = Column(String(100), primary_key=True)  # UUID string to match Zilliz
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    
    # S3 storage
    s3_bucket = Column(String(200), nullable=False)
    s3_key = Column(String(500), nullable=False)
    
    # Embedding info
    embedding_dimension = Column(Integer, default=128, nullable=False)  # face_recognition uses 128
    face_confidence = Column(Float, default=1.0, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
