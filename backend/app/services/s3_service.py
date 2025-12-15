"""
AWS S3 service for face image storage.
"""
import boto3
import aioboto3
from botocore.exceptions import ClientError
from typing import Optional
import io
from datetime import datetime
from uuid import uuid4

from app.config import settings


class S3Service:
    """Service for managing face images in S3."""
    
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.AWS_REGION
        
        # Synchronous client
        self.s3_client = boto3.client(
            's3',
            region_name=self.region,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
    
    def generate_face_key(self, student_id: str, org_id: str) -> str:
        """Generate unique S3 key for face image."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid4())[:8]
        return f"faces/{org_id}/{student_id}/{timestamp}_{unique_id}.jpg"
    
    async def upload_face_image(
        self,
        image_bytes: bytes,
        student_id: str,
        org_id: str,
        content_type: str = "image/jpeg"
    ) -> dict:
        """
        Upload face image to S3.
        
        Returns:
            dict: {
                "s3_key": str,
                "s3_url": str,
                "bucket": str
            }
        """
        s3_key = self.generate_face_key(student_id, org_id)
        
        try:
            # Use aioboto3 for async upload
            session = aioboto3.Session()
            async with session.client(
                's3',
                region_name=self.region,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            ) as s3:
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=image_bytes,
                    ContentType=content_type,
                    Metadata={
                        "student_id": student_id,
                        "org_id": org_id,
                        "uploaded_at": datetime.utcnow().isoformat()
                    }
                )
            
            s3_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
            
            return {
                "s3_key": s3_key,
                "s3_url": s3_url,
                "bucket": self.bucket_name
            }
        
        except ClientError as e:
            raise Exception(f"Failed to upload to S3: {str(e)}")
    
    async def delete_face_image(self, s3_key: str) -> bool:
        """Delete face image from S3."""
        try:
            session = aioboto3.Session()
            async with session.client(
                's3',
                region_name=self.region,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            ) as s3:
                await s3.delete_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
            return True
        except ClientError as e:
            print(f"Error deleting from S3: {e}")
            return False
    
    async def delete_file(self, s3_key: str) -> bool:
        """Alias for delete_face_image."""
        return await self.delete_face_image(s3_key)
    
    def get_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """Generate presigned URL for face image."""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")


# Global instance
s3_service = S3Service()
