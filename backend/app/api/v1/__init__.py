# backend/app/api/v1/__init__.py
"""
API v1 router - Student Face Recognition SaaS
"""
from fastapi import APIRouter
from app.api.v1 import (
    auth, users, organizations, academic, students,
    faculty, subjects, timetable, faces, onboarding, scan
)

api_router = APIRouter()

# Authentication & Onboarding
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["Onboarding"])

# Organization Management
api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])

# Academic Structure
api_router.include_router(academic.router, prefix="/academic", tags=["Academic"])
api_router.include_router(students.router, prefix="/students", tags=["Students"])
api_router.include_router(faculty.router, prefix="/faculty", tags=["Faculty"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["Subjects"])
api_router.include_router(timetable.router, prefix="/timetable", tags=["Timetable"])

# Face Recognition
api_router.include_router(faces.router, prefix="/faces", tags=["Face Registration"])
api_router.include_router(scan.router, prefix="/scan", tags=["Face Scanning"])
