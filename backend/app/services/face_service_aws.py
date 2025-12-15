# backend/app/services/face_service_aws.py
"""
Complete face service using AWS Rekognition + Zilliz.
Best for production with multiple faces.
"""
import boto3
import numpy as np
from typing import List, Dict
from app.services.zilliz_service import zilliz_service
from app.services.s3_service import s3_service

class FaceServiceAWS:
    """Production face service using AWS Rekognition."""
    
    def __init__(self):
        self.rekognition = boto3.client('rekognition')
        self.collection_id = "student-faces-prod"
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Create collection if doesn't exist."""
        try:
            self.rekognition.create_collection(CollectionId=self.collection_id)
            print(f"✅ Created collection: {self.collection_id}")
        except self.rekognition.exceptions.ResourceAlreadyExistsException:
            pass
    
    async def register_student_face(
        self, 
        student_id: str, 
        image_bytes: bytes,
        org_id: str
    ) -> Dict:
        """Register face using Rekognition."""
        try:
            # 1. Detect face quality
            detect_response = self.rekognition.detect_faces(
                Image={'Bytes': image_bytes},
                Attributes=['ALL']
            )
            
            if not detect_response['FaceDetails']:
                return {"success": False, "error": "No face detected"}
            
            face = detect_response['FaceDetails'][0]
            
            # Check quality
            if face['Confidence'] < 90:
                return {"success": False, "error": "Low confidence"}
            
            # 2. Index face in Rekognition
            index_response = self.rekognition.index_faces(
                CollectionId=self.collection_id,
                Image={'Bytes': image_bytes},
                ExternalImageId=student_id,
                MaxFaces=1,
                QualityFilter='AUTO'
            )
            
            if not index_response['FaceRecords']:
                return {"success": False, "error": "Failed to index face"}
            
            face_record = index_response['FaceRecords'][0]
            rekognition_face_id = face_record['Face']['FaceId']
            
            # 3. Upload to S3
            s3_key = await s3_service.upload_face_image(image_bytes, student_id, org_id)
            
            # 4. Store metadata in Zilliz (optional, for additional search)
            # You can still use Zilliz for backup or custom features
            
            return {
                "success": True,
                "rekognition_face_id": rekognition_face_id,
                "s3_key": s3_key,
                "confidence": face_record['Face']['Confidence']
            }
            
        except Exception as e:
            print(f"Error registering face: {e}")
            return {"success": False, "error": str(e)}
    
    async def identify_faces(self, image_bytes: bytes) -> List[Dict]:
        """
        Identify ALL faces in image.
        Returns list of identified students.
        """
        try:
            # Search for all faces
            response = self.rekognition.search_faces_by_image(
                CollectionId=self.collection_id,
                Image={'Bytes': image_bytes},
                MaxFaces=10,  # Support up to 10 faces
                FaceMatchThreshold=80
            )
            
            # Also get face locations
            detect_response = self.rekognition.detect_faces(
                Image={'Bytes': image_bytes},
                Attributes=['DEFAULT']
            )
            
            results = []
            for idx, match in enumerate(response.get('FaceMatches', [])):
                student_id = match['Face']['ExternalImageId']
                
                # Get bbox if available
                bbox = None
                if idx < len(detect_response['FaceDetails']):
                    face_detail = detect_response['FaceDetails'][idx]
                    bb = face_detail['BoundingBox']
                    bbox = {
                        "left": bb['Left'],
                        "top": bb['Top'],
                        "width": bb['Width'],
                        "height": bb['Height']
                    }
                
                results.append({
                    "face_index": idx,
                    "student_id": student_id,
                    "similarity": match['Similarity'],
                    "confidence": match['Face']['Confidence'],
                    "bbox": bbox
                })
            
            print(f"✅ AWS Rekognition identified {len(results)} faces")
            return results
            
        except Exception as e:
            print(f"Error identifying faces: {e}")
            return []

# Global instance
face_service_aws = FaceServiceAWS()
