"""
Face Scan API - Returns user info + current timetable.
Used by faculty/students to scan anyone's face and see their schedule.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, time
from typing import Optional, Dict
import json
import base64

from app.database import get_db, AsyncSessionLocal as async_session_maker
from app.core.permissions import require_student
from app.core.context import get_organization_id
from app.models.student import Student
from app.models.faculty import Faculty
from app.models.user import User
from app.models.timetable import TimetableSlot
from app.models.subject import Subject
from app.models.academic import Department, Section
from app.services.aws_rekognition_service import rekognition_service

router = APIRouter()


async def get_current_timetable(
    section_id: int,
    db: AsyncSession
) -> Optional[Dict]:
    """
    Get current/upcoming class for a section based on timetable.
    Returns what class the student should be in right now.
    """
    now = datetime.now()
    current_time = now.time()
    current_day = now.strftime("%A")  # Monday, Tuesday, etc.
    
    # Find current class (ongoing right now)
    result = await db.execute(
        select(TimetableSlot, Subject, Faculty, User).
        join(Subject, TimetableSlot.subject_id == Subject.id).
        join(Faculty, TimetableSlot.faculty_id == Faculty.id).
        join(User, Faculty.user_id == User.id).
        where(and_(
            TimetableSlot.section_id == section_id,
            TimetableSlot.day_of_week == current_day,
            TimetableSlot.start_time <= current_time,
            TimetableSlot.end_time >= current_time,
            TimetableSlot.is_active == True
        ))
    )
    row = result.first()
    
    if row:
        slot, subject, faculty, faculty_user = row
        return {
            "status": "ongoing",
            "message": "Student should be in this class right now",
            "current_class": {
                "subject_name": subject.name,
                "subject_code": subject.code,
                "type": slot.slot_type,  # lecture/lab
                "room": slot.room_no,
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time": slot.end_time.strftime("%H:%M"),
            },
            "faculty": {
                "name": f"{faculty_user.first_name} {faculty_user.last_name}",
                "employee_id": faculty.employee_id,
                "email": faculty_user.email
            }
        }
    
    # No current class - find next class today
    result = await db.execute(
        select(TimetableSlot, Subject, Faculty, User).
        join(Subject, TimetableSlot.subject_id == Subject.id).
        join(Faculty, TimetableSlot.faculty_id == Faculty.id).
        join(User, Faculty.user_id == User.id).
        where(and_(
            TimetableSlot.section_id == section_id,
            TimetableSlot.day_of_week == current_day,
            TimetableSlot.start_time > current_time,
            TimetableSlot.is_active == True
        )).
        order_by(TimetableSlot.start_time).
        limit(1)
    )
    row = result.first()
    
    if row:
        slot, subject, faculty, faculty_user = row
        return {
            "status": "break",
            "message": "No class right now. Next class coming up.",
            "next_class": {
                "subject_name": subject.name,
                "subject_code": subject.code,
                "type": slot.slot_type,
                "room": slot.room_no,
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time": slot.end_time.strftime("%H:%M"),
            },
            "faculty": {
                "name": f"{faculty_user.first_name} {faculty_user.last_name}",
                "employee_id": faculty.employee_id,
                "email": faculty_user.email
            }
        }
    
    return {
        "status": "free",
        "message": f"No more classes scheduled for today ({current_day})"
    }


async def get_faculty_current_class(
    faculty_id,
    db: AsyncSession
) -> Optional[Dict]:
    """Get current class a faculty is teaching."""
    now = datetime.now()
    current_time = now.time()
    current_day = now.strftime("%A")
    
    result = await db.execute(
        select(TimetableSlot, Subject, Section).
        join(Subject, TimetableSlot.subject_id == Subject.id).
        join(Section, TimetableSlot.section_id == Section.id).
        where(and_(
            TimetableSlot.faculty_id == faculty_id,
            TimetableSlot.day_of_week == current_day,
            TimetableSlot.start_time <= current_time,
            TimetableSlot.end_time >= current_time,
            TimetableSlot.is_active == True
        ))
    )
    row = result.first()
    
    if row:
        slot, subject, section = row
        return {
            "status": "teaching",
            "message": "Faculty should be teaching this class right now",
            "current_class": {
                "subject_name": subject.name,
                "subject_code": subject.code,
                "type": slot.slot_type,
                "room": slot.room_no,
                "section": section.name,
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time": slot.end_time.strftime("%H:%M"),
            }
        }
    
    # Next class
    result = await db.execute(
        select(TimetableSlot, Subject, Section).
        join(Subject, TimetableSlot.subject_id == Subject.id).
        join(Section, TimetableSlot.section_id == Section.id).
        where(and_(
            TimetableSlot.faculty_id == faculty_id,
            TimetableSlot.day_of_week == current_day,
            TimetableSlot.start_time > current_time,
            TimetableSlot.is_active == True
        )).
        order_by(TimetableSlot.start_time).
        limit(1)
    )
    row = result.first()
    
    if row:
        slot, subject, section = row
        return {
            "status": "break",
            "message": "No class right now. Next class coming up.",
            "next_class": {
                "subject_name": subject.name,
                "subject_code": subject.code,
                "type": slot.slot_type,
                "room": slot.room_no,
                "section": section.name,
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time": slot.end_time.strftime("%H:%M"),
            }
        }
    
    return {
        "status": "free",
        "message": f"No classes scheduled for today ({current_day})"
    }


async def identify_person(student_id: str, db: AsyncSession) -> Optional[Dict]:
    """Get complete info for identified person."""
    
    # Try as student first
    result = await db.execute(
        select(Student, User, Department, Section).
        join(User, Student.user_id == User.id).
        join(Department, Student.department_id == Department.id).
        outerjoin(Section, Student.section_id == Section.id).
        where(Student.id == student_id)
    )
    row = result.first()
    
    if row:
        student, user, department, section = row
        
        # Get current timetable
        timetable = None
        if student.section_id:
            timetable = await get_current_timetable(student.section_id, db)
        
        return {
            "type": "student",
            "person": {
                "id": str(student.id),
                "name": f"{user.first_name or ''} {user.last_name or ''}".strip() or "Not set",
                "email": user.email,
                "phone": user.phone,
                "usn": student.usn,
                "semester": student.current_semester,
                "department": department.name,
                "section": section.name if section else None,
                "profile_image": user.profile_image_url
            },
            "timetable": timetable
        }
    
    # Try as faculty
    result = await db.execute(
        select(Faculty, User, Department).
        join(User, Faculty.user_id == User.id).
        join(Department, Faculty.department_id == Department.id).
        where(Faculty.id == student_id)
    )
    row = result.first()
    
    if row:
        faculty, user, department = row
        
        # Get faculty's current class
        timetable = await get_faculty_current_class(faculty.id, db)
        
        return {
            "type": "faculty",
            "person": {
                "id": str(faculty.id),
                "name": f"{user.first_name or ''} {user.last_name or ''}".strip() or "Not set",
                "email": user.email,
                "phone": user.phone,
                "employee_id": faculty.employee_id,
                "designation": faculty.designation,
                "department": department.name,
                "profile_image": user.profile_image_url
            },
            "timetable": timetable
        }
    
    return None


# ============ REST API ENDPOINTS ============

@router.post("/face")
async def scan_face(
    file: UploadFile = File(...),
    org_id=Depends(get_organization_id),
    current_user: dict = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Scan a face and get person info + their current timetable.
    Anyone (student/faculty) can scan anyone's face.
    
    Returns:
    - Person info (name, USN/employee_id, department, section)
    - Current class they should be in
    - Faculty teaching that class
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")
    
    image_bytes = await file.read()
    
    # Search face in Rekognition
    match = rekognition_service.search_single_face(image_bytes)
    
    if not match:
        return {
            "found": False,
            "message": "Face not recognized. Person may not be registered."
        }
    
    # Get person info
    person_info = await identify_person(match['student_id'], db)
    
    if not person_info:
        return {
            "found": False,
            "message": "Person found in face database but profile not found."
        }
    
    return {
        "found": True,
        "similarity": match['similarity'],
        "confidence": match['confidence'],
        **person_info
    }


@router.post("/face/multiple")
async def scan_multiple_faces(
    file: UploadFile = File(...),
    org_id=Depends(get_organization_id),
    current_user: dict = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Scan multiple faces in an image.
    Returns info for each identified person.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")
    
    image_bytes = await file.read()
    
    # Detect all faces
    detected = rekognition_service.detect_faces(image_bytes)
    matches = rekognition_service.search_faces_by_image(image_bytes, max_faces=10)
    
    results = []
    for match in matches:
        person_info = await identify_person(match['student_id'], db)
        if person_info:
            results.append({
                "face_index": match['face_index'],
                "similarity": match['similarity'],
                "bbox": match['bbox'],
                **person_info
            })
    
    return {
        "total_faces_detected": len(detected),
        "total_identified": len(results),
        "persons": results
    }


# ============ WEBSOCKET FOR REAL-TIME SCANNING ============

class ScanConnectionManager:
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
    
    async def connect(self, ws: WebSocket, conn_id: str):
        await ws.accept()
        self.connections[conn_id] = ws
    
    def disconnect(self, conn_id: str):
        self.connections.pop(conn_id, None)


scan_manager = ScanConnectionManager()


@router.websocket("/ws/{org_id}")
async def websocket_scan(websocket: WebSocket, org_id: str):
    """
    Real-time face scanning via WebSocket.
    
    Client sends:
    {
        "frame": "base64_encoded_image",
        "mode": "single" | "multi"
    }
    
    Server returns:
    - Person info + current timetable for each identified face
    """
    conn_id = f"scan_{org_id}_{datetime.now().timestamp()}"
    await scan_manager.connect(websocket, conn_id)
    
    if not rekognition_service.ensure_collection():
        await websocket.send_json({"error": "Face recognition service not available"})
        await websocket.close()
        return
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            frame_b64 = msg.get("frame")
            mode = msg.get("mode", "single")
            
            if not frame_b64:
                await websocket.send_json({"error": "Missing frame"})
                continue
            
            try:
                frame_bytes = base64.b64decode(frame_b64)
            except:
                await websocket.send_json({"error": "Invalid frame encoding"})
                continue
            
            async with async_session_maker() as db:
                if mode == "single":
                    # Single face mode
                    match = rekognition_service.search_single_face(frame_bytes)
                    
                    if not match:
                        await websocket.send_json({
                            "found": False,
                            "message": "No face recognized"
                        })
                        continue
                    
                    person_info = await identify_person(match['student_id'], db)
                    
                    if not person_info:
                        await websocket.send_json({
                            "found": False,
                            "message": "Profile not found"
                        })
                        continue
                    
                    await websocket.send_json({
                        "found": True,
                        "similarity": match['similarity'],
                        "confidence": match['confidence'],
                        **person_info
                    })
                
                else:
                    # Multi-face mode
                    detected = rekognition_service.detect_faces(frame_bytes)
                    matches = rekognition_service.search_faces_by_image(frame_bytes, max_faces=10)
                    
                    results = []
                    for match in matches:
                        person_info = await identify_person(match['student_id'], db)
                        if person_info:
                            results.append({
                                "face_index": match['face_index'],
                                "similarity": match['similarity'],
                                "bbox": match['bbox'],
                                **person_info
                            })
                    
                    await websocket.send_json({
                        "total_faces": len(detected),
                        "identified": len(results),
                        "persons": results
                    })
    
    except WebSocketDisconnect:
        scan_manager.disconnect(conn_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        scan_manager.disconnect(conn_id)
