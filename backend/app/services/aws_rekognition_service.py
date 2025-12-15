"""
AWS Rekognition service - Optimized for multi-face detection and recognition.
Single source of truth for all face operations.
"""
import boto3
from botocore.exceptions import ClientError
from typing import List, Dict, Optional
import io
from PIL import Image

from app.config import settings


class AWSRekognitionService:
    """Unified service for AWS Rekognition face operations."""
    
    def __init__(self):
        self.rekognition = boto3.client(
            'rekognition',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.collection_id = settings.REKOGNITION_COLLECTION_ID
        self.min_confidence = 90.0
        self.similarity_threshold = 80.0
    
    def ensure_collection(self) -> bool:
        """Create Rekognition collection if it doesn't exist."""
        try:
            self.rekognition.describe_collection(CollectionId=self.collection_id)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                try:
                    self.rekognition.create_collection(CollectionId=self.collection_id)
                    print(f"✅ Created Rekognition collection: {self.collection_id}")
                    return True
                except ClientError as create_error:
                    print(f"❌ Failed to create collection: {create_error}")
                    return False
            return False
    
    def detect_faces(self, image_bytes: bytes) -> List[Dict]:
        """Detect all faces in image with quality metrics."""
        try:
            response = self.rekognition.detect_faces(
                Image={'Bytes': image_bytes},
                Attributes=['ALL']
            )
            
            if not response['FaceDetails']:
                return []
            
            img = Image.open(io.BytesIO(image_bytes))
            img_width, img_height = img.size
            
            faces = []
            for idx, face in enumerate(response['FaceDetails']):
                bbox = face['BoundingBox']
                left = int(bbox['Left'] * img_width)
                top = int(bbox['Top'] * img_height)
                width = int(bbox['Width'] * img_width)
                height = int(bbox['Height'] * img_height)
                
                faces.append({
                    "face_index": idx,
                    "bbox": {
                        "left": left, "top": top,
                        "right": left + width, "bottom": top + height,
                        "width": width, "height": height
                    },
                    "confidence": face['Confidence'],
                    "quality": {
                        "brightness": face['Quality']['Brightness'],
                        "sharpness": face['Quality']['Sharpness']
                    }
                })
            
            return faces
        except ClientError as e:
            print(f"❌ Error detecting faces: {e}")
            return []
    
    def index_face(self, image_bytes: bytes, student_id: str) -> Optional[Dict]:
        """Index a face in the Rekognition collection."""
        try:
            response = self.rekognition.index_faces(
                CollectionId=self.collection_id,
                Image={'Bytes': image_bytes},
                ExternalImageId=student_id,
                MaxFaces=1,
                QualityFilter='AUTO',
                DetectionAttributes=['ALL']
            )
            
            if not response['FaceRecords']:
                return {"success": False, "error": "No face detected or quality too low"}
            
            face = response['FaceRecords'][0]['Face']
            return {
                "success": True,
                "face_id": face['FaceId'],
                "image_id": face['ImageId'],
                "confidence": face['Confidence']
            }
        except ClientError as e:
            return {"success": False, "error": str(e)}
    
    def delete_face(self, face_id: str) -> bool:
        """Delete a face from the collection."""
        try:
            self.rekognition.delete_faces(
                CollectionId=self.collection_id,
                FaceIds=[face_id]
            )
            return True
        except ClientError:
            return False
    
    def search_faces_by_image(self, image_bytes: bytes, max_faces: int = 10) -> List[Dict]:
        """Search for all matching faces by detecting and searching each face."""
        try:
            detected_faces = self.detect_faces(image_bytes)
            if not detected_faces:
                return []
            
            img = Image.open(io.BytesIO(image_bytes))
            matches = []
            
            for face in detected_faces:
                bbox = face['bbox']
                padding = 30
                
                left = max(0, bbox['left'] - padding)
                top = max(0, bbox['top'] - padding)
                right = min(img.width, bbox['right'] + padding)
                bottom = min(img.height, bbox['bottom'] + padding)
                
                face_img = img.crop((left, top, right, bottom))
                face_bytes_io = io.BytesIO()
                face_img.save(face_bytes_io, format='JPEG', quality=95)
                face_bytes = face_bytes_io.getvalue()
                
                try:
                    response = self.rekognition.search_faces_by_image(
                        CollectionId=self.collection_id,
                        Image={'Bytes': face_bytes},
                        MaxFaces=1,
                        FaceMatchThreshold=self.similarity_threshold
                    )
                    
                    if response.get('FaceMatches'):
                        match = response['FaceMatches'][0]
                        matches.append({
                            "face_index": face['face_index'],
                            "student_id": match['Face']['ExternalImageId'],
                            "face_id": match['Face']['FaceId'],
                            "similarity": match['Similarity'],
                            "confidence": match['Face']['Confidence'],
                            "bbox": bbox
                        })
                except ClientError:
                    continue
            
            return matches
        except Exception as e:
            print(f"❌ Error in search: {e}")
            return []
    
    def search_single_face(self, image_bytes: bytes) -> Optional[Dict]:
        """Search for a single face match (optimized for 1:1 verification)."""
        try:
            response = self.rekognition.search_faces_by_image(
                CollectionId=self.collection_id,
                Image={'Bytes': image_bytes},
                MaxFaces=1,
                FaceMatchThreshold=self.similarity_threshold
            )
            
            if not response.get('FaceMatches'):
                return None
            
            match = response['FaceMatches'][0]
            return {
                "student_id": match['Face']['ExternalImageId'],
                "face_id": match['Face']['FaceId'],
                "similarity": match['Similarity'],
                "confidence": match['Face']['Confidence']
            }
        except ClientError:
            return None
    
    def validate_face_quality(self, image_bytes: bytes) -> Dict:
        """Validate face image quality before registration."""
        try:
            faces = self.detect_faces(image_bytes)
            
            if not faces:
                return {"valid": False, "message": "No face detected", "face_count": 0}
            
            if len(faces) > 1:
                return {
                    "valid": False, 
                    "message": f"Multiple faces detected ({len(faces)}). Use single face image.",
                    "face_count": len(faces)
                }
            
            face = faces[0]
            quality = face['quality']
            
            if quality['brightness'] < 30:
                return {"valid": False, "message": "Image too dark", "face_count": 1}
            if quality['sharpness'] < 30:
                return {"valid": False, "message": "Image too blurry", "face_count": 1}
            if face['confidence'] < 90:
                return {"valid": False, "message": "Face not clearly visible", "face_count": 1}
            
            return {
                "valid": True,
                "message": "Face quality acceptable",
                "face_count": 1,
                "confidence": face['confidence'],
                "quality": quality
            }
        except Exception as e:
            return {"valid": False, "message": str(e), "face_count": 0}
    
    def list_faces(self, max_results: int = 100) -> List[Dict]:
        """List all indexed faces in collection."""
        try:
            response = self.rekognition.list_faces(
                CollectionId=self.collection_id,
                MaxResults=max_results
            )
            return [
                {
                    "face_id": face['FaceId'],
                    "student_id": face['ExternalImageId'],
                    "confidence": face['Confidence']
                }
                for face in response['Faces']
            ]
        except ClientError:
            return []
    
    def get_collection_stats(self) -> Dict:
        """Get collection statistics."""
        try:
            response = self.rekognition.describe_collection(CollectionId=self.collection_id)
            return {
                "face_count": response['FaceCount'],
                "created": str(response['CreationTimestamp'])
            }
        except ClientError:
            return {"face_count": 0}


# Global instance
rekognition_service = AWSRekognitionService()
