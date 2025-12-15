"""
Script to set up CSE AIML department with full academic structure and timetable.
Academic Year: 2025-26
Run from backend directory: python ../scripts/setup_academic_data.py
"""
import asyncio
import sys
sys.path.insert(0, '.')

from datetime import date, time
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.organization import Organization
from app.models.academic import Department, AcademicYear, Semester, Section
from app.models.subject import Subject
from app.models.timetable import TimetableSlot


# ============ DATA ============

CLASSES_DATA = [
    {"semester": 3, "section": "A", "room_no": "409", "class_teacher": "Mrs. Kavita Reddy"},
    {"semester": 3, "section": "B", "room_no": "404", "class_teacher": "Mrs. Mackal Rajawat"},
    {"semester": 3, "section": "C", "room_no": "405", "class_teacher": "Mrs. Vinaya S Kavalgi"},
    {"semester": 5, "section": "A", "room_no": "412", "class_teacher": "Mrs. Kavya P"},
    {"semester": 5, "section": "B", "room_no": "410", "class_teacher": "Mrs. Ambili K"},
    {"semester": 5, "section": "C", "room_no": "403", "class_teacher": "Mr. Ramakrishna Reddy"},
    {"semester": 7, "section": "A", "room_no": "406", "class_teacher": "Mrs. Swathi Srikanth A"},
    {"semester": 7, "section": "B", "room_no": "407", "class_teacher": "Mr. Roshan U"},
]

SUBJECTS_DATA = [
    # Semester 3
    {"code": "BCS301", "name": "Mathematics for Computer Science", "semester": 3, "credits": 4, "type": "theory"},
    {"code": "BCS302", "name": "Digital Design & Computer Organization", "semester": 3, "credits": 4, "type": "theory"},
    {"code": "BCS303", "name": "Operating Systems", "semester": 3, "credits": 4, "type": "theory"},
    {"code": "BCS304", "name": "Data Structures and Applications", "semester": 3, "credits": 4, "type": "theory"},
    {"code": "BCSL305", "name": "Data Structures Lab", "semester": 3, "credits": 1, "type": "lab"},
    {"code": "BCS306A", "name": "Object Oriented Programming with Java", "semester": 3, "credits": 3, "type": "theory"},
    {"code": "BCS358C", "name": "Project Management with Git Lab", "semester": 3, "credits": 1, "type": "lab"},
    {"code": "BSCK307", "name": "Social Connect and Responsibility / PBL", "semester": 3, "credits": 1, "type": "theory"},
    # Semester 5
    {"code": "BCS501", "name": "Software Engineering & Project Management", "semester": 5, "credits": 4, "type": "theory"},
    {"code": "BCS502", "name": "Computer Networks", "semester": 5, "credits": 4, "type": "theory"},
    {"code": "BCS503", "name": "Theory of Computation", "semester": 5, "credits": 4, "type": "theory"},
    {"code": "BAI515A", "name": "Computer Vision", "semester": 5, "credits": 3, "type": "theory"},
    {"code": "BAIL504", "name": "Data Visualization Lab", "semester": 5, "credits": 1, "type": "lab"},
    {"code": "BRMK557", "name": "Research Methodology and IPR", "semester": 5, "credits": 2, "type": "theory"},
    {"code": "BCI586", "name": "Mini Project", "semester": 5, "credits": 2, "type": "project"},
    {"code": "BCS508", "name": "Environmental Studies", "semester": 5, "credits": 1, "type": "theory"},
    # Semester 7
    {"code": "BCA701", "name": "Deep Learning", "semester": 7, "credits": 4, "type": "theory"},
    {"code": "BAI702", "name": "Machine Learning II", "semester": 7, "credits": 4, "type": "theory"},
    {"code": "BCS703", "name": "Cryptography & Network Security", "semester": 7, "credits": 4, "type": "theory"},
    {"code": "BCS714D", "name": "Big Data Analytics", "semester": 7, "credits": 3, "type": "theory"},
    {"code": "BCI755X", "name": "Open Elective Course", "semester": 7, "credits": 3, "type": "theory"},
    {"code": "BCI786", "name": "Major Project Phase II", "semester": 7, "credits": 8, "type": "project"},
]

# Timetable slots from the CSV
TIMETABLE_SLOTS = [
    # 3rd Sem A - Monday
    {"class_id": "CSE-AIML-3-A", "day": "MON", "start": "09:15", "end": "10:10", "subject": "BCS302", "type": "theory"},
    {"class_id": "CSE-AIML-3-A", "day": "MON", "start": "10:10", "end": "11:05", "subject": "BCS301", "type": "theory"},
    {"class_id": "CSE-AIML-3-A", "day": "MON", "start": "11:20", "end": "12:15", "subject": "BCS304", "type": "theory"},
    {"class_id": "CSE-AIML-3-A", "day": "MON", "start": "12:15", "end": "13:10", "subject": "BCS303", "type": "theory"},
    {"class_id": "CSE-AIML-3-A", "day": "MON", "start": "14:00", "end": "16:45", "subject": "BCS358C", "type": "lab"},
    # 5th Sem A - Thursday
    {"class_id": "CSE-AIML-5-A", "day": "THU", "start": "09:15", "end": "10:10", "subject": "BCS502", "type": "theory"},
    {"class_id": "CSE-AIML-5-A", "day": "THU", "start": "10:10", "end": "11:05", "subject": "BCS503", "type": "theory"},
    # 7th Sem A - Monday
    {"class_id": "CSE-AIML-7-A", "day": "MON", "start": "09:15", "end": "10:10", "subject": "BCA701", "type": "theory"},
    {"class_id": "CSE-AIML-7-A", "day": "MON", "start": "10:10", "end": "11:05", "subject": "BAI702", "type": "theory"},
    # 7th Sem B - Friday
    {"class_id": "CSE-AIML-7-B", "day": "FRI", "start": "14:00", "end": "16:45", "subject": "BAI702", "type": "lab"},
]


def parse_time(time_str: str) -> time:
    """Parse time string to time object."""
    parts = time_str.split(":")
    return time(int(parts[0]), int(parts[1]))


async def setup_academic_data():
    async with AsyncSessionLocal() as db:
        # Get the organization
        result = await db.execute(
            select(Organization).where(Organization.slug == "amcec")
        )
        org = result.scalar_one_or_none()
        
        if not org:
            print("❌ Organization 'amcec' not found!")
            return
        
        print(f"✅ Found organization: {org.name}")
        print("="*60)
        
        # ============ DEPARTMENT ============
        dept_check = await db.execute(
            select(Department).where(
                Department.organization_id == org.id,
                Department.code == "CSE-AIML"
            )
        )
        dept = dept_check.scalar_one_or_none()
        
        if not dept:
            dept = Department(
                organization_id=org.id,
                name="Computer Science and Engineering (AI & ML)",
                code="CSE-AIML",
                description="Department of CSE with specialization in AI and Machine Learning",
                total_semesters=8,
                is_active=True
            )
            db.add(dept)
            await db.flush()
            print(f"✅ Created department: {dept.name}")
        else:
            print(f"⚠️  Department exists: {dept.name} (ID: {dept.id})")
        
        # ============ ACADEMIC YEAR 2025-26 ============
        ay_check = await db.execute(
            select(AcademicYear).where(
                AcademicYear.organization_id == org.id,
                AcademicYear.year_name == "2025-26"
            )
        )
        academic_year = ay_check.scalar_one_or_none()
        
        if not academic_year:
            academic_year = AcademicYear(
                organization_id=org.id,
                year_name="2025-26",
                start_date=date(2025, 8, 1),
                end_date=date(2026, 7, 31),
                is_current=True
            )
            db.add(academic_year)
            await db.flush()
            print(f"✅ Created academic year: {academic_year.year_name}")
        else:
            print(f"⚠️  Academic year exists: {academic_year.year_name}")
        
        # ============ SEMESTERS (3, 5, 7 - odd) ============
        semester_map = {}
        for sem_num in [3, 5, 7]:
            sem_check = await db.execute(
                select(Semester).where(
                    Semester.organization_id == org.id,
                    Semester.academic_year_id == academic_year.id,
                    Semester.semester_number == sem_num
                )
            )
            semester = sem_check.scalar_one_or_none()
            
            if not semester:
                semester = Semester(
                    organization_id=org.id,
                    academic_year_id=academic_year.id,
                    semester_number=sem_num,
                    semester_type="odd",
                    start_date=date(2025, 8, 1),
                    end_date=date(2025, 12, 31),
                    is_active=True
                )
                db.add(semester)
                await db.flush()
                print(f"✅ Created semester {sem_num}")
            else:
                print(f"⚠️  Semester {sem_num} exists")
            
            semester_map[sem_num] = semester
        
        # ============ SECTIONS ============
        section_map = {}
        batch_years = {3: 2024, 5: 2023, 7: 2022}
        
        for class_data in CLASSES_DATA:
            sem_num = class_data["semester"]
            sec_name = class_data["section"]
            class_id = f"CSE-AIML-{sem_num}-{sec_name}"
            
            sec_check = await db.execute(
                select(Section).where(
                    Section.organization_id == org.id,
                    Section.class_id == class_id
                )
            )
            section = sec_check.scalar_one_or_none()
            
            if not section:
                section = Section(
                    organization_id=org.id,
                    department_id=dept.id,
                    class_id=class_id,
                    name=sec_name,
                    semester=sem_num,
                    batch_year=batch_years[sem_num],
                    room_no=class_data["room_no"],
                    capacity=60,
                    is_active=True
                )
                db.add(section)
                await db.flush()
                print(f"✅ Created section: {class_id} (Room: {class_data['room_no']})")
            else:
                print(f"⚠️  Section exists: {class_id}")
            
            section_map[class_id] = section
        
        # ============ SUBJECTS ============
        subject_map = {}
        
        for subj_data in SUBJECTS_DATA:
            subj_check = await db.execute(
                select(Subject).where(Subject.code == subj_data["code"])
            )
            subject = subj_check.scalar_one_or_none()
            
            if not subject:
                subject = Subject(
                    organization_id=org.id,
                    department_id=dept.id,
                    code=subj_data["code"],
                    name=subj_data["name"],
                    credits=subj_data["credits"],
                    subject_type=subj_data["type"],
                    semester_number=subj_data["semester"],
                    is_active=True
                )
                db.add(subject)
                await db.flush()
                print(f"✅ Created subject: {subj_data['code']} - {subj_data['name']}")
            else:
                print(f"⚠️  Subject exists: {subj_data['code']}")
            
            subject_map[subj_data["code"]] = subject
        
        # ============ TIMETABLE SLOTS ============
        print("\n--- Creating Timetable Slots ---")
        slots_created = 0
        
        for slot_data in TIMETABLE_SLOTS:
            class_id = slot_data["class_id"]
            if class_id not in section_map:
                print(f"⚠️  Section not found for {class_id}")
                continue
            
            section = section_map[class_id]
            subject = subject_map.get(slot_data["subject"])
            
            if not subject:
                print(f"⚠️  Subject not found: {slot_data['subject']}")
                continue
            
            start_t = parse_time(slot_data["start"])
            
            # Check if slot exists
            slot_check = await db.execute(
                select(TimetableSlot).where(
                    TimetableSlot.organization_id == org.id,
                    TimetableSlot.section_id == section.id,
                    TimetableSlot.day_of_week == slot_data["day"],
                    TimetableSlot.start_time == start_t
                )
            )
            existing_slot = slot_check.scalar_one_or_none()
            
            if not existing_slot:
                slot = TimetableSlot(
                    organization_id=org.id,
                    section_id=section.id,
                    subject_id=subject.id,
                    day_of_week=slot_data["day"],
                    start_time=start_t,
                    end_time=parse_time(slot_data["end"]),
                    room_no=section.room_no,
                    slot_type=slot_data["type"],
                    is_active=True
                )
                db.add(slot)
                slots_created += 1
                print(f"✅ Created slot: {class_id} {slot_data['day']} {slot_data['start']}-{slot_data['end']} {slot_data['subject']}")
            else:
                print(f"⚠️  Slot exists: {class_id} {slot_data['day']} {slot_data['start']}")
        
        await db.commit()
        
        # ============ SUMMARY ============
        print("\n" + "="*60)
        print("🎉 SETUP COMPLETE!")
        print("="*60)
        print(f"Organization: {org.name}")
        print(f"Department: {dept.name} ({dept.code})")
        print(f"Academic Year: {academic_year.year_name}")
        print(f"Semesters: 3, 5, 7 (odd)")
        print(f"Sections: {len(section_map)}")
        print(f"Subjects: {len(subject_map)}")
        print(f"Timetable slots created: {slots_created}")
        print("="*60)
        print("\nNext steps:")
        print("1. Faculty register via Auth0 → assign to timetable slots")
        print("2. Create join codes for students")
        print("3. Students register and complete face recognition")


if __name__ == "__main__":
    asyncio.run(setup_academic_data())
