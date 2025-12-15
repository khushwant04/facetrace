"""
Face recognition API endpoints - AWS Rekognition only.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import io
from PIL import Image, ImageDraw, ImageFont

from app.database import get_db
from app.core.permissions import require_org_admin, require_faculty, require_student
from app.core.context import get_organization_id
from app.models.student import Student
from app.models.user import User
from app.services.s3_service import s3_service
from app.services.aws_rekognition_service import rekognition_service

router = APIRouter()


@router.post("/upload/{usn}")
async def upload_student_face(
    usn: str,
    file: UploadFile = File(...),
    org_id=Depends(get_organization_id),
    current_user: dict = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Upload and register student face in AWS Rekognition."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")
    
    # Get student
    result = await db.execute(
        select(Student).where(Student.usn == usn, Student.organization_id == org_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(404, f"Student {usn} not found")
    
    image_bytes = await file.read()
    
    # Validate face quality
    validation = rekognition_service.validate_face_quality(image_bytes)
    if not validation['valid']:
        raise HTTPException(400, validation['message'])
    
    # Upload to S3
    s3_result = await s3_service.upload_face_image(image_bytes, str(student.id), str(org_id))
    s3_key = s3_result.get('s3_key') if isinstance(s3_result, dict) else s3_result
    
    if not s3_key:
        raise HTTPException(500, "S3 upload failed")
    
    # Index in Rekognition
    rek_result = rekognition_service.index_face(image_bytes, str(student.id))
    
    if not rek_result or not rek_result.get('success'):
        await s3_service.delete_file(s3_key)
        raise HTTPException(400, f"Face registration failed: {rek_result.get('error', 'Unknown')}")
    
    # Update student record
    student.face_registered = True
    student.face_image_s3_key = s3_key
    student.face_registered_at = datetime.utcnow()
    await db.commit()
    
    return {
        "success": True,
        "message": f"Face registered for {student.usn}",
        "student_id": str(student.id),
        "s3_key": s3_key,
        "rekognition": {
            "face_id": rek_result['face_id'],
            "confidence": rek_result['confidence']
        }
    }


@router.post("/upload/self")
async def upload_own_face(
    file: UploadFile = File(...),
    org_id=Depends(get_organization_id),
    current_user: dict = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Student uploads their own face (self-registration).
    Used in mobile app during onboarding.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")
    
    # Get student record for current user
    user_result = await db.execute(
        select(User).where(User.auth0_user_id == current_user.get("auth0_user_id"))
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(404, "User not found")
    
    student_result = await db.execute(
        select(Student).where(Student.user_id == user.id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(404, "Student profile not found")
    
    if student.face_registered:
        raise HTTPException(400, "Face already registered. Contact admin to update.")
    
    image_bytes = await file.read()
    
    # Validate face quality
    validation = rekognition_service.validate_face_quality(image_bytes)
    if not validation['valid']:
        raise HTTPException(400, validation['message'])
    
    # Upload to S3
    s3_result = await s3_service.upload_face_image(image_bytes, str(student.id), str(org_id))
    s3_key = s3_result.get('s3_key') if isinstance(s3_result, dict) else s3_result
    
    if not s3_key:
        raise HTTPException(500, "S3 upload failed")
    
    # Index in Rekognition
    rek_result = rekognition_service.index_face(image_bytes, str(student.id))
    
    if not rek_result or not rek_result.get('success'):
        await s3_service.delete_file(s3_key)
        raise HTTPException(400, f"Face registration failed: {rek_result.get('error', 'Unknown')}")
    
    # Update student record
    student.face_registered = True
    student.face_image_s3_key = s3_key
    student.face_registered_at = datetime.utcnow()
    
    # Update onboarding status
    from app.models.invitation import UserOnboarding, OnboardingStatus
    onboarding_result = await db.execute(
        select(UserOnboarding).where(UserOnboarding.user_id == user.id)
    )
    onboarding = onboarding_result.scalar_one_or_none()
    if onboarding:
        onboarding.face_registered = True
        onboarding.status = OnboardingStatus.ACTIVE.value
    
    await db.commit()
    
    return {
        "success": True,
        "message": "Face registered successfully",
        "student_id": str(student.id)
    }


@router.post("/validate")
async def validate_face(file: UploadFile = File(...)):
    """Validate face image quality before upload (public endpoint)."""
    image_bytes = await file.read()
    result = rekognition_service.validate_face_quality(image_bytes)
    return result


@router.post("/search")
async def search_face(
    file: UploadFile = File(...),
    org_id=Depends(get_organization_id),
    current_user: dict = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Search for a face match."""
    image_bytes = await file.read()
    
    match = rekognition_service.search_single_face(image_bytes)
    if not match:
        return {"found": False, "message": "No matching face found"}
    
    # Get student info
    result = await db.execute(select(Student).where(Student.id == match['student_id']))
    student = result.scalar_one_or_none()
    
    if not student:
        return {"found": False, "message": "Student record not found"}
    
    user_result = await db.execute(select(User).where(User.id == student.user_id))
    user = user_result.scalar_one_or_none()
    
    return {
        "found": True,
        "student": {
            "id": str(student.id),
            "usn": student.usn,
            "name": f"{user.first_name} {user.last_name}" if user else "Unknown",
            "semester": student.current_semester
        },
        "similarity": match['similarity'],
        "confidence": match['confidence']
    }


@router.post("/detect-multiple")
async def detect_multiple_faces(
    file: UploadFile = File(...),
    org_id=Depends(get_organization_id),
    current_user: dict = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Detect and identify multiple faces in an image."""
    image_bytes = await file.read()
    
    matches = rekognition_service.search_faces_by_image(image_bytes, max_faces=10)
    detected = rekognition_service.detect_faces(image_bytes)
    
    results = []
    for match in matches:
        result = await db.execute(select(Student).where(Student.id == match['student_id']))
        student = result.scalar_one_or_none()
        
        if student:
            user_result = await db.execute(select(User).where(User.id == student.user_id))
            user = user_result.scalar_one_or_none()
            
            results.append({
                "face_index": match['face_index'],
                "name": f"{user.first_name} {user.last_name}" if user else "Unknown",
                "usn": student.usn,
                "similarity": match['similarity'],
                "bbox": match['bbox']
            })
    
    return {
        "total_detected": len(detected),
        "total_identified": len(results),
        "faces": results
    }


@router.post("/detect-multiple-image")
async def detect_multiple_faces_annotated(
    file: UploadFile = File(...),
    org_id=Depends(get_organization_id),
    current_user: dict = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Return annotated image with bounding boxes and names."""
    image_bytes = await file.read()
    
    detected = rekognition_service.detect_faces(image_bytes)
    matches = rekognition_service.search_faces_by_image(image_bytes, max_faces=10)
    
    # Build face info map
    face_info = {}
    for match in matches:
        result = await db.execute(select(Student).where(Student.id == match['student_id']))
        student = result.scalar_one_or_none()
        if student:
            user_result = await db.execute(select(User).where(User.id == student.user_id))
            user = user_result.scalar_one_or_none()
            face_info[match['face_index']] = {
                "name": f"{user.first_name} {user.last_name}" if user else "Unknown",
                "usn": student.usn,
                "similarity": match['similarity']
            }
    
    # Draw annotations
    img = Image.open(io.BytesIO(image_bytes))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    for face in detected:
        bbox = face['bbox']
        idx = face['face_index']
        
        if idx in face_info:
            color = '#00FF00'
            info = face_info[idx]
            label = f"{info['name']} ({info['similarity']:.1f}%)"
        else:
            color = '#FF0000'
            label = "Unknown"
        
        draw.rectangle([bbox['left'], bbox['top'], bbox['right'], bbox['bottom']], outline=color, width=3)
        draw.text((bbox['left'], bbox['top'] - 30), label, fill=color, font=font)
    
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=95)
    output.seek(0)
    
    return StreamingResponse(output, media_type="image/jpeg")


@router.delete("/{student_id}")
async def delete_student_face(
    student_id: str,
    org_id=Depends(get_organization_id),
    current_user: dict = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete student's face from Rekognition and S3."""
    result = await db.execute(
        select(Student).where(Student.id == student_id, Student.organization_id == org_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(404, "Student not found")
    
    # Delete from S3
    if student.face_image_s3_key:
        await s3_service.delete_file(student.face_image_s3_key)
    
    # Update student
    student.face_registered = False
    student.face_image_s3_key = None
    await db.commit()
    
    return {"success": True, "message": "Face deleted"}


@router.get("/stats")
async def get_face_stats(current_user: dict = Depends(require_org_admin)):
    """Get Rekognition collection statistics."""
    return rekognition_service.get_collection_stats()
