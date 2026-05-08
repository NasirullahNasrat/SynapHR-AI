"""
Management command to seed the database with demo data for development/testing.

Creates departments, designations, employees, attendance records, leave types,
leave allocations, leave requests, salary structures, payroll, performance reviews,
goals, holidays, and notifications with realistic demo data.
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from config.apps.hrms.models import (
    Attendance,
    Department,
    Designation,
    Employee,
    Goal,
    Holiday,
    LeaveAllocation,
    LeaveRequest,
    LeaveType,
    Notification,
    Payroll,
    PerformanceReview,
    SalaryStructure,
)

User = get_user_model()


class Command(BaseCommand):
    """Seed the database with demo data."""

    help = "Seed the database with demo data for development"

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write("Seeding database with demo data...")

        # Create admin user if not exists
        self._create_admin_user()

        # Create departments
        departments = self._create_departments()

        # Create designations
        designations = self._create_designations(departments)

        # Create employees
        employees = self._create_employees(departments, designations)

        # Create leave types
        leave_types = self._create_leave_types()

        # Create leave allocations
        self._create_leave_allocations(employees, leave_types)

        # Create leave requests
        self._create_leave_requests(employees, leave_types)

        # Create attendance records
        self._create_attendance(employees)

        # Create holidays
        self._create_holidays()

        # Create salary structures
        salary_structures = self._create_salary_structures(employees)

        # Create payroll
        self._create_payroll(employees, salary_structures)

        # Create performance reviews
        self._create_performance_reviews(employees)

        # Create goals
        self._create_goals(employees)

        # Create notifications
        self._create_notifications()

        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))

    def _create_admin_user(self) -> None:
        """Create admin user if not exists."""
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin",
                email="admin@hrms.com",
                password="admin123",
                first_name="Admin",
                last_name="User",
                user_type="ADMIN",
                employee_id="ADM-0001",
                phone_number="+1-555-0100",
            )

        # Create HR user
        if not User.objects.filter(username="hr_manager").exists():
            User.objects.create_user(
                username="hr_manager",
                email="hr@hrms.com",
                password="hr123",
                first_name="Sarah",
                last_name="Johnson",
                user_type="HR",
                employee_id="HR-0001",
                phone_number="+1-555-0101",
            )
            self.stdout.write("  [OK] HR user created (hr_manager/hr123)")

    def _create_departments(self) -> dict[str, Department]:
        """Create departments and return a dict by name."""
        dept_data = [
            {"name": "Engineering", "code": "ENG", "description": "Software engineering and development"},
            {"name": "Human Resources", "code": "HR", "description": "Human resources management"},
            {"name": "Marketing", "code": "MKT", "description": "Marketing and communications"},
            {"name": "Finance", "code": "FIN", "description": "Financial management and accounting"},
            {"name": "Sales", "code": "SAL", "description": "Sales and business development"},
            {"name": "Operations", "code": "OPS", "description": "Operations and logistics"},
            {"name": "Design", "code": "DES", "description": "UI/UX and graphic design"},
            {"name": "Legal", "code": "LEG", "description": "Legal and compliance"},
        ]
        departments = {}
        for data in dept_data:
            dept, created = Department.objects.get_or_create(
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "description": data["description"],
                    "is_active": True,
                },
            )
            departments[data["name"]] = dept
            if created:
                self.stdout.write(f"  [OK] Department created: {dept.name}")
        return departments

    def _create_designations(self, departments: dict[str, Department]) -> list[Designation]:
        """Create designations for each department."""
        designations_data = [
            {"title": "Software Engineer", "department": "Engineering", "level": 2, "salary_min": 60000, "salary_max": 90000},
            {"title": "Senior Software Engineer", "department": "Engineering", "level": 3, "salary_min": 90000, "salary_max": 130000},
            {"title": "Lead Engineer", "department": "Engineering", "level": 4, "salary_min": 130000, "salary_max": 170000},
            {"title": "Engineering Manager", "department": "Engineering", "level": 5, "salary_min": 150000, "salary_max": 200000},
            {"title": "Junior Developer", "department": "Engineering", "level": 1, "salary_min": 40000, "salary_max": 60000},
            {"title": "HR Coordinator", "department": "Human Resources", "level": 2, "salary_min": 35000, "salary_max": 50000},
            {"title": "HR Manager", "department": "Human Resources", "level": 4, "salary_min": 60000, "salary_max": 85000},
            {"title": "Recruiter", "department": "Human Resources", "level": 2, "salary_min": 40000, "salary_max": 55000},
            {"title": "Marketing Specialist", "department": "Marketing", "level": 2, "salary_min": 45000, "salary_max": 65000},
            {"title": "Marketing Manager", "department": "Marketing", "level": 4, "salary_min": 70000, "salary_max": 100000},
            {"title": "Content Writer", "department": "Marketing", "level": 1, "salary_min": 35000, "salary_max": 50000},
            {"title": "Accountant", "department": "Finance", "level": 2, "salary_min": 45000, "salary_max": 60000},
            {"title": "Finance Manager", "department": "Finance", "level": 4, "salary_min": 75000, "salary_max": 110000},
            {"title": "Financial Analyst", "department": "Finance", "level": 3, "salary_min": 55000, "salary_max": 75000},
            {"title": "Sales Representative", "department": "Sales", "level": 2, "salary_min": 40000, "salary_max": 60000},
            {"title": "Sales Manager", "department": "Sales", "level": 4, "salary_min": 70000, "salary_max": 100000},
            {"title": "Account Executive", "department": "Sales", "level": 3, "salary_min": 55000, "salary_max": 80000},
            {"title": "Operations Analyst", "department": "Operations", "level": 2, "salary_min": 40000, "salary_max": 55000},
            {"title": "Operations Manager", "department": "Operations", "level": 4, "salary_min": 65000, "salary_max": 90000},
            {"title": "UI/UX Designer", "department": "Design", "level": 2, "salary_min": 50000, "salary_max": 75000},
            {"title": "Senior Designer", "department": "Design", "level": 3, "salary_min": 75000, "salary_max": 100000},
            {"title": "Design Lead", "department": "Design", "level": 4, "salary_min": 100000, "salary_max": 140000},
            {"title": "Legal Counsel", "department": "Legal", "level": 3, "salary_min": 80000, "salary_max": 120000},
            {"title": "Compliance Officer", "department": "Legal", "level": 2, "salary_min": 50000, "salary_max": 70000},
        ]
        created_list = []
        for data in designations_data:
            desig, created = Designation.objects.get_or_create(
                title=data["title"],
                department=departments[data["department"]],
                defaults={
                    "level": data["level"],
                    "salary_range_min": data["salary_min"],
                    "salary_range_max": data["salary_max"],
                    "is_active": True,
                },
            )
            created_list.append(desig)
            if created:
                self.stdout.write(f"  [OK] Designation created: {desig.title}")
        return created_list

    def _create_employees(self, departments: dict[str, Department], designations: list[Designation]) -> list[Employee]:
        """Create employees with associated users."""
        employee_data = [
            {"username": "john.doe", "first": "John", "last": "Doe", "email": "john.doe@hrms.com", "phone": "+1-555-1001", "dept": "Engineering", "desig": "Senior Software Engineer", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2022-03-15", "gender": "M", "marital": "MARRIED", "nationality": "American", "blood": "O+", "city": "San Francisco", "state": "CA", "country": "USA"},
            {"username": "jane.smith", "first": "Jane", "last": "Smith", "email": "jane.smith@hrms.com", "phone": "+1-555-1002", "dept": "Engineering", "desig": "Engineering Manager", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2021-06-01", "gender": "F", "marital": "SINGLE", "nationality": "American", "blood": "A+", "city": "San Francisco", "state": "CA", "country": "USA"},
            {"username": "bob.wilson", "first": "Bob", "last": "Wilson", "email": "bob.wilson@hrms.com", "phone": "+1-555-1003", "dept": "Engineering", "desig": "Software Engineer", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2023-01-10", "gender": "M", "marital": "SINGLE", "nationality": "American", "blood": "B+", "city": "San Francisco", "state": "CA", "country": "USA"},
            {"username": "alice.chen", "first": "Alice", "last": "Chen", "email": "alice.chen@hrms.com", "phone": "+1-555-1004", "dept": "Engineering", "desig": "Lead Engineer", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2022-09-20", "gender": "F", "marital": "MARRIED", "nationality": "Chinese", "blood": "AB+", "city": "San Francisco", "state": "CA", "country": "USA"},
            {"username": "mike.brown", "first": "Mike", "last": "Brown", "email": "mike.brown@hrms.com", "phone": "+1-555-1005", "dept": "Engineering", "desig": "Junior Developer", "status": "PROBATION", "type": "FULL_TIME", "joining": "2024-08-01", "gender": "M", "marital": "SINGLE", "nationality": "American", "blood": "O-", "city": "San Francisco", "state": "CA", "country": "USA"},
            {"username": "emma.davis", "first": "Emma", "last": "Davis", "email": "emma.davis@hrms.com", "phone": "+1-555-2001", "dept": "Human Resources", "desig": "HR Manager", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2021-11-15", "gender": "F", "marital": "MARRIED", "nationality": "American", "blood": "A-", "city": "New York", "state": "NY", "country": "USA"},
            {"username": "ryan.garcia", "first": "Ryan", "last": "Garcia", "email": "ryan.garcia@hrms.com", "phone": "+1-555-2002", "dept": "Human Resources", "desig": "HR Coordinator", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2023-04-10", "gender": "M", "marital": "SINGLE", "nationality": "American", "blood": "B-", "city": "New York", "state": "NY", "country": "USA"},
            {"username": "sophia.lee", "first": "Sophia", "last": "Lee", "email": "sophia.lee@hrms.com", "phone": "+1-555-2003", "dept": "Human Resources", "desig": "Recruiter", "status": "ACTIVE", "type": "CONTRACT", "joining": "2024-01-15", "gender": "F", "marital": "SINGLE", "nationality": "Korean", "blood": "A+", "city": "New York", "state": "NY", "country": "USA"},
            {"username": "olivia.taylor", "first": "Olivia", "last": "Taylor", "email": "olivia.taylor@hrms.com", "phone": "+1-555-3001", "dept": "Marketing", "desig": "Marketing Manager", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2022-02-01", "gender": "F", "marital": "MARRIED", "nationality": "American", "blood": "O+", "city": "Chicago", "state": "IL", "country": "USA"},
            {"username": "liam.martinez", "first": "Liam", "last": "Martinez", "email": "liam.martinez@hrms.com", "phone": "+1-555-3002", "dept": "Marketing", "desig": "Marketing Specialist", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2023-06-20", "gender": "M", "marital": "SINGLE", "nationality": "American", "blood": "AB-", "city": "Chicago", "state": "IL", "country": "USA"},
            {"username": "ava.anderson", "first": "Ava", "last": "Anderson", "email": "ava.anderson@hrms.com", "phone": "+1-555-3003", "dept": "Marketing", "desig": "Content Writer", "status": "ACTIVE", "type": "PART_TIME", "joining": "2024-03-01", "gender": "F", "marital": "SINGLE", "nationality": "American", "blood": "B+", "city": "Chicago", "state": "IL", "country": "USA"},
            {"username": "noah.thomas", "first": "Noah", "last": "Thomas", "email": "noah.thomas@hrms.com", "phone": "+1-555-4001", "dept": "Finance", "desig": "Finance Manager", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2021-08-15", "gender": "M", "marital": "MARRIED", "nationality": "American", "blood": "O+", "city": "Boston", "state": "MA", "country": "USA"},
            {"username": "mia.jackson", "first": "Mia", "last": "Jackson", "email": "mia.jackson@hrms.com", "phone": "+1-555-4002", "dept": "Finance", "desig": "Accountant", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2023-09-01", "gender": "F", "marital": "SINGLE", "nationality": "American", "blood": "A+", "city": "Boston", "state": "MA", "country": "USA"},
            {"username": "ethan.white", "first": "Ethan", "last": "White", "email": "ethan.white@hrms.com", "phone": "+1-555-4003", "dept": "Finance", "desig": "Financial Analyst", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2023-02-15", "gender": "M", "marital": "SINGLE", "nationality": "American", "blood": "B-", "city": "Boston", "state": "MA", "country": "USA"},
            {"username": "isabella.harris", "first": "Isabella", "last": "Harris", "email": "isabella.harris@hrms.com", "phone": "+1-555-5001", "dept": "Sales", "desig": "Sales Manager", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2022-05-01", "gender": "F", "marital": "MARRIED", "nationality": "American", "blood": "AB+", "city": "Los Angeles", "state": "CA", "country": "USA"},
            {"username": "james.clark", "first": "James", "last": "Clark", "email": "james.clark@hrms.com", "phone": "+1-555-5002", "dept": "Sales", "desig": "Account Executive", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2023-07-10", "gender": "M", "marital": "MARRIED", "nationality": "American", "blood": "O-", "city": "Los Angeles", "state": "CA", "country": "USA"},
            {"username": "charlotte.lewis", "first": "Charlotte", "last": "Lewis", "email": "charlotte.lewis@hrms.com", "phone": "+1-555-5003", "dept": "Sales", "desig": "Sales Representative", "status": "PROBATION", "type": "FULL_TIME", "joining": "2024-09-01", "gender": "F", "marital": "SINGLE", "nationality": "American", "blood": "A+", "city": "Los Angeles", "state": "CA", "country": "USA"},
            {"username": "benjamin.walker", "first": "Benjamin", "last": "Walker", "email": "benjamin.walker@hrms.com", "phone": "+1-555-6001", "dept": "Operations", "desig": "Operations Manager", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2022-01-15", "gender": "M", "marital": "MARRIED", "nationality": "American", "blood": "B+", "city": "Seattle", "state": "WA", "country": "USA"},
            {"username": "amelia.hall", "first": "Amelia", "last": "Hall", "email": "amelia.hall@hrms.com", "phone": "+1-555-6002", "dept": "Operations", "desig": "Operations Analyst", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2023-11-01", "gender": "F", "marital": "SINGLE", "nationality": "American", "blood": "O+", "city": "Seattle", "state": "WA", "country": "USA"},
            {"username": "elijah.young", "first": "Elijah", "last": "Young", "email": "elijah.young@hrms.com", "phone": "+1-555-7001", "dept": "Design", "desig": "Design Lead", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2022-04-01", "gender": "M", "marital": "MARRIED", "nationality": "American", "blood": "AB-", "city": "Austin", "state": "TX", "country": "USA"},
            {"username": "harper.king", "first": "Harper", "last": "King", "email": "harper.king@hrms.com", "phone": "+1-555-7002", "dept": "Design", "desig": "UI/UX Designer", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2023-05-15", "gender": "F", "marital": "SINGLE", "nationality": "American", "blood": "A-", "city": "Austin", "state": "TX", "country": "USA"},
            {"username": "logan.wright", "first": "Logan", "last": "Wright", "email": "logan.wright@hrms.com", "phone": "+1-555-7003", "dept": "Design", "desig": "Senior Designer", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2022-11-01", "gender": "M", "marital": "SINGLE", "nationality": "American", "blood": "B+", "city": "Austin", "state": "TX", "country": "USA"},
            {"username": "ella.scott", "first": "Ella", "last": "Scott", "email": "ella.scott@hrms.com", "phone": "+1-555-8001", "dept": "Legal", "desig": "Legal Counsel", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2022-07-01", "gender": "F", "marital": "MARRIED", "nationality": "American", "blood": "O+", "city": "Washington", "state": "DC", "country": "USA"},
            {"username": "aiden.green", "first": "Aiden", "last": "Green", "email": "aiden.green@hrms.com", "phone": "+1-555-8002", "dept": "Legal", "desig": "Compliance Officer", "status": "ACTIVE", "type": "FULL_TIME", "joining": "2023-08-15", "gender": "M", "marital": "SINGLE", "nationality": "American", "blood": "AB+", "city": "Washington", "state": "DC", "country": "USA"},
        ]

        hr_user = User.objects.get(username="hr_manager")
        admin_user = User.objects.get(username="admin")

        employees = []
        for data in employee_data:
            username = data["username"]
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": data["first"],
                    "last_name": data["last"],
                    "email": data["email"],
                    "phone_number": data["phone"],
                    "user_type": "EMPLOYEE",
                    "gender": data["gender"],
                    "is_active": True,
                },
            )
            if created:
                user.set_password("emp123")
                user.save()

            dept = departments[data["dept"]]
            desig = Designation.objects.get(title=data["desig"], department=dept)

            emp, created = Employee.objects.get_or_create(
                user=user,
                defaults={
                    "department": dept,
                    "designation": desig,
                    "employment_status": data["status"],
                    "employment_type": data["type"],
                    "joining_date": data["joining"],
                    "marital_status": data["marital"],
                    "nationality": data["nationality"],
                    "blood_group": data["blood"],
                    "city": data["city"],
                    "state": data["state"],
                    "country": data["country"],
                    "present_address": f"123 Main St, {data['city']}, {data['state']}",
                    "permanent_address": f"456 Oak Ave, {data['city']}, {data['state']}",
                    "emergency_contact_name": f"Emergency Contact for {data['first']}",
                    "emergency_contact_phone": "+1-555-9999",
                    "emergency_contact_relation": "Spouse",
                    "highest_education": "Bachelor's Degree",
                    "institution": "State University",
                    "year_of_passing": 2018,
                    "skills": ["Python", "JavaScript", "Project Management", "Communication"],
                },
            )
            # Update designation/department if employee already existed without one
            if not created and (emp.designation is None or emp.department is None):
                emp.designation = desig
                emp.department = dept
                emp.save(update_fields=["designation", "department"])
            employees.append(emp)
            if created:
                self.stdout.write(f"  [OK] Employee created: {emp.full_name}")

        # Set department heads
        departments["Engineering"].head = User.objects.get(username="jane.smith")
        departments["Engineering"].save()
        departments["Human Resources"].head = hr_user
        departments["Human Resources"].save()
        departments["Marketing"].head = User.objects.get(username="olivia.taylor")
        departments["Marketing"].save()
        departments["Finance"].head = User.objects.get(username="noah.thomas")
        departments["Finance"].save()
        departments["Sales"].head = User.objects.get(username="isabella.harris")
        departments["Sales"].save()
        departments["Operations"].head = User.objects.get(username="benjamin.walker")
        departments["Operations"].save()
        departments["Design"].head = User.objects.get(username="elijah.young")
        departments["Design"].save()
        departments["Legal"].head = User.objects.get(username="ella.scott")
        departments["Legal"].save()

        # Set reporting relationships
        emp_map = {e.user.username: e for e in employees}
        for uname in ["john.doe", "bob.wilson", "alice.chen", "mike.brown"]:
            if uname in emp_map:
                emp_map[uname].reporting_to = emp_map.get("jane.smith")
                emp_map[uname].save()

        return employees

    def _create_leave_types(self) -> list[LeaveType]:
        """Create leave types."""
        leave_types_data = [
            {"name": "Annual Leave", "code": "AL", "days": 20, "carry_forward": True, "max_carry": 5, "paid": True},
            {"name": "Sick Leave", "code": "SL", "days": 12, "carry_forward": False, "max_carry": 0, "paid": True},
            {"name": "Personal Leave", "code": "PL", "days": 5, "carry_forward": False, "max_carry": 0, "paid": True},
            {"name": "Maternity Leave", "code": "ML", "days": 90, "carry_forward": False, "max_carry": 0, "paid": True},
            {"name": "Paternity Leave", "code": "PAT", "days": 10, "carry_forward": False, "max_carry": 0, "paid": True},
            {"name": "Compensatory Off", "code": "COMP", "days": 10, "carry_forward": True, "max_carry": 10, "paid": True},
            {"name": "Unpaid Leave", "code": "UL", "days": 30, "carry_forward": False, "max_carry": 0, "paid": False},
        ]
        created_list = []
        for data in leave_types_data:
            lt, created = LeaveType.objects.get_or_create(
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "days_per_year": data["days"],
                    "is_carry_forward": data["carry_forward"],
                    "max_carry_forward_days": data["max_carry"],
                    "is_paid": data["paid"],
                    "requires_approval": True,
                    "is_active": True,
                },
            )
            created_list.append(lt)
            if created:
                self.stdout.write(f"  [OK] Leave type created: {lt.name}")
        return created_list

    def _create_leave_allocations(self, employees: list[Employee], leave_types: list[LeaveType]) -> None:
        """Create leave allocations for each employee."""
        current_year = timezone.now().year
        for emp in employees:
            for lt in leave_types:
                if lt.code in ["ML", "PAT"]:
                    continue
                if lt.code == "ML" and emp.user.gender != "F":
                    continue
                if lt.code == "PAT" and emp.user.gender == "F":
                    continue

                LeaveAllocation.objects.get_or_create(
                    employee=emp,
                    leave_type=lt,
                    year=current_year,
                    defaults={
                        "total_days": lt.days_per_year,
                        "used_days": random.randint(0, max(0, lt.days_per_year - 5)),
                        "pending_days": random.choice([0, 0, 0, 1, 2]),
                        "carried_forward": 0,
                    },
                )

    def _create_leave_requests(self, employees: list[Employee], leave_types: list[LeaveType]) -> None:
        """Create some leave requests."""
        today = timezone.now().date()
        statuses = ["PENDING", "APPROVED", "APPROVED", "REJECTED"]
        admin_user = User.objects.get(username="admin")

        for i, emp in enumerate(employees[:8]):
            lt = random.choice(leave_types[:3])
            start_date = today + timedelta(days=random.randint(-30, 30))
            end_date = start_date + timedelta(days=random.randint(1, 3))
            status = random.choice(statuses)

            LeaveRequest.objects.get_or_create(
                employee=emp,
                leave_type=lt,
                start_date=start_date,
                end_date=end_date,
                defaults={
                    "total_days": (end_date - start_date).days + 1,
                    "reason": f"Leave request for {lt.name.lower()}",
                    "status": status,
                    "approved_by": admin_user if status != "PENDING" else None,
                    "approval_date": timezone.now() if status != "PENDING" else None,
                },
            )

    def _create_attendance(self, employees: list[Employee]) -> None:
        """Create attendance records for the last 30 days."""
        today = timezone.now().date()
        statuses = ["PRESENT", "PRESENT", "PRESENT", "PRESENT", "LATE", "ABSENT", "HALF_DAY"]

        for emp in employees:
            for days_ago in range(30):
                date = today - timedelta(days=days_ago)
                if date.weekday() >= 5:
                    continue

                status = random.choice(statuses)
                check_in_hour = 8 if status == "PRESENT" else 9 if status == "LATE" else 8
                check_in = timezone.make_aware(datetime(date.year, date.month, date.day, check_in_hour, random.randint(0, 59)))
                check_out = timezone.make_aware(datetime(date.year, date.month, date.day, 17, random.randint(0, 59)))

                Attendance.objects.get_or_create(
                    employee=emp,
                    date=date,
                    defaults={
                        "check_in": check_in if status != "ABSENT" else None,
                        "check_out": check_out if status != "ABSENT" else None,
                        "status": status,
                        "is_late": status == "LATE",
                        "late_minutes": random.randint(15, 60) if status == "LATE" else 0,
                        "work_hours": Decimal("8.00") if status == "PRESENT" else Decimal("4.00") if status == "HALF_DAY" else Decimal("0.00"),
                    },
                )

    def _create_holidays(self) -> None:
        """Create holidays for the current year."""
        current_year = timezone.now().year
        holidays_data = [
            {"name": "New Year's Day", "date": f"{current_year}-01-01", "type": "NATIONAL"},
            {"name": "Independence Day", "date": f"{current_year}-07-04", "type": "NATIONAL"},
            {"name": "Labor Day", "date": f"{current_year}-09-01", "type": "NATIONAL"},
            {"name": "Thanksgiving", "date": f"{current_year}-11-27", "type": "NATIONAL"},
            {"name": "Christmas", "date": f"{current_year}-12-25", "type": "NATIONAL"},
            {"name": "Company Foundation Day", "date": f"{current_year}-03-15", "type": "COMPANY"},
            {"name": "Year-End Holiday", "date": f"{current_year}-12-31", "type": "COMPANY"},
        ]
        for data in holidays_data:
            Holiday.objects.get_or_create(
                name=data["name"],
                date=data["date"],
                defaults={
                    "type": data["type"],
                    "is_recurring": data["type"] == "NATIONAL",
                    "is_active": True,
                },
            )

    def _create_salary_structures(self, employees: list[Employee]) -> list[SalaryStructure]:
        """Create salary structures for each employee."""
        salary_configs = {
            "Senior Software Engineer": {"basic": 80000, "hra": 30000, "da": 5000, "travel": 8000, "medical": 6000, "special": 10000, "pf": 12000, "ptax": 2500, "itax": 15000, "insurance": 5000},
            "Engineering Manager": {"basic": 100000, "hra": 40000, "da": 8000, "travel": 12000, "medical": 8000, "special": 15000, "pf": 15000, "ptax": 2500, "itax": 25000, "insurance": 6000},
            "Software Engineer": {"basic": 55000, "hra": 22000, "da": 4000, "travel": 6000, "medical": 5000, "special": 7000, "pf": 8000, "ptax": 2000, "itax": 10000, "insurance": 4000},
            "Lead Engineer": {"basic": 95000, "hra": 35000, "da": 7000, "travel": 10000, "medical": 7000, "special": 12000, "pf": 14000, "ptax": 2500, "itax": 22000, "insurance": 5500},
            "Junior Developer": {"basic": 40000, "hra": 15000, "da": 3000, "travel": 5000, "medical": 4000, "special": 5000, "pf": 6000, "ptax": 1500, "itax": 5000, "insurance": 3000},
            "HR Manager": {"basic": 55000, "hra": 20000, "da": 4000, "travel": 6000, "medical": 5000, "special": 8000, "pf": 8000, "ptax": 2000, "itax": 10000, "insurance": 4000},
            "HR Coordinator": {"basic": 35000, "hra": 12000, "da": 2500, "travel": 4000, "medical": 3000, "special": 4000, "pf": 5000, "ptax": 1500, "itax": 3000, "insurance": 2500},
            "Recruiter": {"basic": 40000, "hra": 15000, "da": 3000, "travel": 5000, "medical": 4000, "special": 5000, "pf": 6000, "ptax": 1500, "itax": 5000, "insurance": 3000},
            "Marketing Manager": {"basic": 65000, "hra": 25000, "da": 5000, "travel": 8000, "medical": 6000, "special": 10000, "pf": 10000, "ptax": 2000, "itax": 12000, "insurance": 4500},
            "Marketing Specialist": {"basic": 45000, "hra": 18000, "da": 3500, "travel": 5000, "medical": 4000, "special": 6000, "pf": 7000, "ptax": 1500, "itax": 6000, "insurance": 3500},
            "Content Writer": {"basic": 35000, "hra": 12000, "da": 2500, "travel": 4000, "medical": 3000, "special": 4000, "pf": 5000, "ptax": 1500, "itax": 3000, "insurance": 2500},
            "Finance Manager": {"basic": 70000, "hra": 28000, "da": 5500, "travel": 8000, "medical": 6000, "special": 10000, "pf": 10000, "ptax": 2500, "itax": 15000, "insurance": 5000},
            "Accountant": {"basic": 45000, "hra": 18000, "da": 3500, "travel": 5000, "medical": 4000, "special": 6000, "pf": 7000, "ptax": 1500, "itax": 6000, "insurance": 3500},
            "Financial Analyst": {"basic": 55000, "hra": 22000, "da": 4000, "travel": 6000, "medical": 5000, "special": 7000, "pf": 8000, "ptax": 2000, "itax": 10000, "insurance": 4000},
            "Sales Manager": {"basic": 65000, "hra": 25000, "da": 5000, "travel": 8000, "medical": 6000, "special": 10000, "pf": 10000, "ptax": 2000, "itax": 12000, "insurance": 4500},
            "Account Executive": {"basic": 55000, "hra": 22000, "da": 4000, "travel": 6000, "medical": 5000, "special": 7000, "pf": 8000, "ptax": 2000, "itax": 10000, "insurance": 4000},
            "Sales Representative": {"basic": 40000, "hra": 15000, "da": 3000, "travel": 5000, "medical": 4000, "special": 5000, "pf": 6000, "ptax": 1500, "itax": 5000, "insurance": 3000},
            "Operations Manager": {"basic": 60000, "hra": 24000, "da": 4500, "travel": 7000, "medical": 5000, "special": 8000, "pf": 9000, "ptax": 2000, "itax": 11000, "insurance": 4000},
            "Operations Analyst": {"basic": 40000, "hra": 15000, "da": 3000, "travel": 5000, "medical": 4000, "special": 5000, "pf": 6000, "ptax": 1500, "itax": 5000, "insurance": 3000},
            "Design Lead": {"basic": 90000, "hra": 35000, "da": 6000, "travel": 10000, "medical": 7000, "special": 12000, "pf": 13000, "ptax": 2500, "itax": 20000, "insurance": 5500},
            "Senior Designer": {"basic": 70000, "hra": 28000, "da": 5000, "travel": 8000, "medical": 6000, "special": 10000, "pf": 10000, "ptax": 2000, "itax": 14000, "insurance": 4500},
            "UI/UX Designer": {"basic": 50000, "hra": 20000, "da": 4000, "travel": 6000, "medical": 5000, "special": 7000, "pf": 8000, "ptax": 2000, "itax": 8000, "insurance": 3500},
            "Legal Counsel": {"basic": 80000, "hra": 32000, "da": 6000, "travel": 10000, "medical": 7000, "special": 12000, "pf": 12000, "ptax": 2500, "itax": 18000, "insurance": 5000},
            "Compliance Officer": {"basic": 50000, "hra": 20000, "da": 4000, "travel": 6000, "medical": 5000, "special": 7000, "pf": 8000, "ptax": 2000, "itax": 8000, "insurance": 3500},
        }

        created_list = []
        for emp in employees:
            if not emp.designation:
                continue
            desig_title = emp.designation.title
            if desig_title not in salary_configs:
                continue
            config = salary_configs[desig_title]
            ss, created = SalaryStructure.objects.get_or_create(
                employee=emp,
                effective_from=date(2025, 1, 1),
                defaults={
                    "name": f"{desig_title} - Standard",
                    "basic_salary": config["basic"],
                    "house_rent_allowance": config["hra"],
                    "dearness_allowance": config["da"],
                    "travel_allowance": config["travel"],
                    "medical_allowance": config["medical"],
                    "special_allowance": config["special"],
                    "provident_fund": config["pf"],
                    "professional_tax": config["ptax"],
                    "income_tax": config["itax"],
                    "insurance": config["insurance"],
                    "is_active": True,
                },
            )
            created_list.append(ss)
        return created_list

    def _create_payroll(self, employees: list[Employee], salary_structures: list[SalaryStructure]) -> None:
        """Create payroll records for the current month."""
        current_month = timezone.now().month
        current_year = timezone.now().year
        admin_user = User.objects.get(username="admin")

        for emp in employees:
            ss = SalaryStructure.objects.filter(employee=emp, is_active=True).first()
            if not ss:
                continue

            Payroll.objects.get_or_create(
                employee=emp,
                month=current_month,
                year=current_year,
                defaults={
                    "salary_structure": ss,
                    "status": "PROCESSED",
                    "basic_salary": ss.basic_salary,
                    "house_rent_allowance": ss.house_rent_allowance,
                    "dearness_allowance": ss.dearness_allowance,
                    "travel_allowance": ss.travel_allowance,
                    "medical_allowance": ss.medical_allowance,
                    "special_allowance": ss.special_allowance,
                    "bonus": Decimal("0.00"),
                    "overtime_pay": Decimal("0.00"),
                    "other_earnings": Decimal("0.00"),
                    "provident_fund": ss.provident_fund,
                    "professional_tax": ss.professional_tax,
                    "income_tax": ss.income_tax,
                    "insurance": ss.insurance,
                    "loan_deduction": Decimal("0.00"),
                    "leave_deduction": Decimal("0.00"),
                    "other_deductions": Decimal("0.00"),
                    "total_earnings": ss.total_earnings,
                    "total_deductions": ss.total_deductions,
                    "net_pay": ss.net_salary,
                    "payment_date": timezone.now().date(),
                    "payment_method": "BANK_TRANSFER",
                    "processed_by": admin_user,
                    "processed_at": timezone.now(),
                },
            )

    def _create_performance_reviews(self, employees: list[Employee]) -> None:
        """Create performance reviews for some employees."""
        current_year = timezone.now().year
        ratings = [3, 4, 4, 5, 3, 4, 5]

        for emp in employees[1:12]:  # 11 employees get reviews
            reviewer = random.choice([e for e in employees if e != emp])
            PerformanceReview.objects.get_or_create(
                employee=emp,
                reviewer=reviewer,
                review_period_start=date(current_year, 1, 1),
                review_period_end=date(current_year, 6, 30),
                defaults={
                    "due_date": date(current_year, 7, 15),
                    "status": "COMPLETED",
                    "technical_skills": random.choice(ratings),
                    "communication": random.choice(ratings),
                    "teamwork": random.choice(ratings),
                    "leadership": random.choice(ratings),
                    "productivity": random.choice(ratings),
                    "punctuality": random.choice(ratings),
                    "overall_rating": Decimal(str(round(random.uniform(3.0, 5.0), 1))),
                    "strengths": "Strong technical skills, excellent team player, proactive problem solver.",
                    "areas_for_improvement": "Could improve documentation practices and knowledge sharing.",
                    "goals": "Complete advanced certification, mentor junior team members.",
                    "reviewer_comments": "Consistently delivers high-quality work. Meets all deadlines.",
                    "employee_comments": "Enjoy working at the company. Looking forward to more challenges.",
                    "is_acknowledged": True,
                    "acknowledged_at": timezone.now(),
                    "completed_at": timezone.now(),
                },
            )

    def _create_goals(self, employees: list[Employee]) -> None:
        """Create goals for employees."""
        current_year = timezone.now().year
        goal_templates = [
            {"title": "Complete Project Milestone", "type": "PROJECT", "progress": 75},
            {"title": "Improve Code Quality Metrics", "type": "QUARTERLY", "progress": 60},
            {"title": "Team Mentoring Program", "type": "ANNUAL", "progress": 40},
            {"title": "Learn New Technology Stack", "type": "PERSONAL", "progress": 50},
            {"title": "Reduce Response Time by 20%", "type": "QUARTERLY", "progress": 80},
            {"title": "Complete Documentation Overhaul", "type": "PROJECT", "progress": 30},
            {"title": "Achieve Sales Target", "type": "ANNUAL", "progress": 65},
            {"title": "Improve Customer Satisfaction Score", "type": "QUARTERLY", "progress": 55},
        ]

        admin_user = User.objects.get(username="admin")
        for emp in employees[:15]:
            template = random.choice(goal_templates)
            Goal.objects.get_or_create(
                employee=emp,
                title=template["title"],
                defaults={
                    "description": f"Work towards {template['title'].lower()} as part of professional development.",
                    "goal_type": template["type"],
                    "status": "IN_PROGRESS",
                    "start_date": date(current_year, 1, 1),
                    "end_date": date(current_year, 12, 31),
                    "progress_percentage": template["progress"],
                    "key_results": [
                        {"title": "Milestone 1", "completed": True},
                        {"title": "Milestone 2", "completed": template["progress"] > 50},
                        {"title": "Milestone 3", "completed": False},
                    ],
                    "created_by": admin_user,
                },
            )

    def _create_notifications(self) -> None:
        """Create sample notifications."""
        admin_user = User.objects.get(username="admin")
        hr_user = User.objects.get(username="hr_manager")

        notifications_data = [
            {"recipient": admin_user, "type": "SYSTEM", "title": "Welcome to SynapHR AI", "message": "Your account has been created successfully. Welcome aboard!"},
            {"recipient": admin_user, "type": "PAYROLL", "title": "Payroll Processed", "message": "Monthly payroll for May 2025 has been processed successfully."},
            {"recipient": admin_user, "type": "PERFORMANCE", "title": "Review Reminder", "message": "You have 3 pending performance reviews to complete."},
            {"recipient": hr_user, "type": "LEAVE_REQUEST", "title": "New Leave Request", "message": "John Doe has submitted a new leave request for Annual Leave."},
            {"recipient": hr_user, "type": "LEAVE_APPROVED", "title": "Leave Approved", "message": "Your leave request for Sick Leave has been approved."},
            {"recipient": hr_user, "type": "ATTENDANCE", "title": "Attendance Summary", "message": "Weekly attendance report is now available."},
        ]

        for data in notifications_data:
            Notification.objects.get_or_create(
                recipient=data["recipient"],
                title=data["title"],
                defaults={
                    "notification_type": data["type"],
                    "message": data["message"],
                    "is_read": False,
                },
            )