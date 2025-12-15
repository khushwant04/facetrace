"""
Script to set up CSE AIML department and basic academic structure.
Run from backend directory: python ../scripts/setup_department.py
"""
import asyncio
import sys
sys.path.insert(0, '.')

from sqlalchemy import select
from app.database import async_session
from app.models.organization import Organization
from app.models.academic import Department, AcademicYear, Semester, Section


async def setup_cse_aiml():
    async with async_session() as db:
        # Get the organization
        result = await db.execute(
            select(Organization).where(Organization.slug == "amcec")
        )
        org = result.scalar_one_or_none()
        
        if not org:
            print("❌ Organization 'amcec' not found!")
            return
        
        print(f"✅ Found organization: {org.name} (ID: {org.id})")
        
        # Check if department already exists
        dept_check = await db.execute(
            select(Department).where(
                Department.organization_id == org.id,
                Department.code == "CSE-AIML"
            )
        )
        existing_dept = dept_check.scalar_one_or_none()
        
        if existing_dept:
            print(f"⚠️  Department already exists: {existing_dept.name} (ID: {existing_dept.id})")
            dept = existing_dept
        else:
            # Create CSE AIML Department
            dept = Department(
                organization_id=org.id,
                name="Computer Science and Engineering (AI & ML)",
                code="CSE-AIML",
                description="Department of Computer Science and Engineering with specialization in Artificial Intelligence and Machine Learning",
                total_semesters=8,
                is_active=True
            )
            db.add(dept)
            await db.flush()
            print(f"✅ Created department: {dept.name} (ID: {dept.id})")
        
        # Create Academic Year 2024-25 if not exists
        ay_check = await db.execute(
            select(AcademicYear).where(
                AcademicYear.organization_id == org.id,
                AcademicYear.year_name == "2024-25"
            )
        )
        existing_ay = ay_check.scalar_one_or_none()
        
        if existing_ay:
            print(f"⚠️  Academic year already exists: {existing_ay.year_name} (ID: {existing_ay.id})")
            academic_year = existing_ay
        else:
            from datetime import date
            academic_year = AcademicYear(
                organization_id=org.id,
                year_name="2024-25",
                start_date=date(2024, 8, 1),
                end_date=date(2025, 7, 31),
                is_current=True
            )
            db.add(academic_year)
            await db.flush()
            print(f"✅ Created academic year: {academic_year.year_name} (ID: {academic_year.id})")
        
        # Create semesters (odd semesters: 1, 3, 5, 7 for current period)
        from datetime import date
        semesters_to_create = [
            {"semester_number": 1, "semester_type": "odd"},
            {"semester_number": 3, "semester_type": "odd"},
            {"semester_number": 5, "semester_type": "odd"},
            {"semester_number": 7, "semester_type": "odd"},
        ]
        
        created_semesters = []
        for sem_data in semesters_to_create:
            sem_check = await db.execute(
                select(Semester).where(
                    Semester.organization_id == org.id,
                    Semester.academic_year_id == academic_year.id,
                    Semester.semester_number == sem_data["semester_number"]
                )
            )
            existing_sem = sem_check.scalar_one_or_none()
            
            if existing_sem:
                print(f"⚠️  Semester {sem_data['semester_number']} already exists (ID: {existing_sem.id})")
                created_semesters.append(existing_sem)
            else:
                semester = Semester(
                    organization_id=org.id,
                    academic_year_id=academic_year.id,
                    semester_number=sem_data["semester_number"],
                    semester_type=sem_data["semester_type"],
                    start_date=date(2024, 8, 1),
                    end_date=date(2024, 12, 31),
                    is_active=True
                )
                db.add(semester)
                await db.flush()
                created_semesters.append(semester)
                print(f"✅ Created semester {semester.semester_number} (ID: {semester.id})")
        
        # Create sections for each semester (A, B, C sections)
        section_names = ["A", "B", "C"]
        batch_years = {1: 2024, 3: 2023, 5: 2022, 7: 2021}  # Based on semester
        
        for semester in created_semesters:
            for section_name in section_names:
                sec_check = await db.execute(
                    select(Section).where(
                        Section.organization_id == org.id,
                        Section.department_id == dept.id,
                        Section.semester_id == semester.id,
                        Section.name == section_name
                    )
                )
                existing_sec = sec_check.scalar_one_or_none()
                
                if existing_sec:
                    print(f"⚠️  Section {section_name} for Sem {semester.semester_number} already exists")
                else:
                    section = Section(
                        organization_id=org.id,
                        department_id=dept.id,
                        semester_id=semester.id,
                        name=section_name,
                        batch_year=batch_years.get(semester.semester_number, 2024),
                        capacity=60,
                        is_active=True
                    )
                    db.add(section)
                    print(f"✅ Created section {section_name} for Semester {semester.semester_number}")
        
        await db.commit()
        
        print("\n" + "="*50)
        print("🎉 Setup complete!")
        print("="*50)
        print(f"Organization: {org.name}")
        print(f"Department: {dept.name} ({dept.code})")
        print(f"Academic Year: {academic_year.year_name}")
        print(f"Semesters: 1, 3, 5, 7 (odd)")
        print(f"Sections per semester: A, B, C")
        print("="*50)


if __name__ == "__main__":
    asyncio.run(setup_cse_aiml())
