"""
SQLAlchemy models - import all models here.
"""
from app.models.user import User
from app.models.organization import Organization
from app.models.academic import AcademicYear, Department, Semester, Section, LabGroup
from app.models.student import Student
from app.models.faculty import Faculty
from app.models.subject import Subject
from app.models.timetable import TimetableSlot
from app.models.faculty_subject import FacultySubjectMapping
from app.models.invitation import Invitation, OrganizationJoinCode, UserOnboarding

__all__ = [
    "User",
    "Organization",
    "AcademicYear",
    "Department",
    "Semester",
    "Section",
    "LabGroup",
    "Student",
    "Faculty",
    "Subject",
    "TimetableSlot",
    "FacultySubjectMapping",
    "Invitation",
    "OrganizationJoinCode",
    "UserOnboarding",
]
