"""
Celery tasks for the HRMS app.

Handles background operations like payroll processing and attendance reminders.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="process_pending_payroll")
def process_pending_payroll() -> dict:
    """
    Process pending payroll records.

    This task runs daily to process any payroll records that are in PENDING status.
    It calculates totals and moves them to PROCESSED status.

    Returns:
        dict: Summary of the operation
    """
    from .models import Payroll

    today = timezone.now()
    pending_payrolls = Payroll.objects.filter(status="PENDING")

    processed_count = 0
    for payroll in pending_payrolls:
        try:
            # Calculate totals from individual components
            payroll.total_earnings = (
                payroll.basic_salary
                + payroll.house_rent_allowance
                + payroll.dearness_allowance
                + payroll.travel_allowance
                + payroll.medical_allowance
                + payroll.special_allowance
                + payroll.bonus
                + payroll.overtime_pay
                + payroll.other_earnings
            )
            payroll.total_deductions = (
                payroll.provident_fund
                + payroll.professional_tax
                + payroll.income_tax
                + payroll.insurance
                + payroll.loan_deduction
                + payroll.leave_deduction
                + payroll.other_deductions
            )
            payroll.net_pay = payroll.total_earnings - payroll.total_deductions
            payroll.status = "PROCESSED"
            payroll.processed_at = today
            payroll.save()
            processed_count += 1
        except Exception as e:
            logger.error(
                "Failed to process payroll %s: %s", payroll.id, str(e)
            )

    logger.info("Processed %d pending payroll records", processed_count)
    return {
        "status": "success",
        "processed_count": processed_count,
    }


@shared_task(name="send_attendance_reminders")
def send_attendance_reminders() -> dict:
    """
    Send reminders to employees who haven't marked attendance.

    This task runs hourly during working hours to remind employees
    who haven't checked in yet.

    Returns:
        dict: Summary of the operation
    """
    from .models import Attendance, AttendanceSettings, Employee, Notification

    today = date.today()
    now = datetime.now().time()

    # Get attendance settings
    settings = AttendanceSettings.objects.first()
    if not settings:
        return {"status": "skipped", "reason": "No attendance settings configured"}

    # Check if today is a working day
    weekday = today.weekday()
    if settings.working_days and weekday not in settings.working_days:
        return {"status": "skipped", "reason": "Today is not a working day"}

    # Get employees who haven't checked in yet
    checked_in_employees = Attendance.objects.filter(
        date=today, check_in__isnull=False
    ).values_list("employee_id", flat=True)

    employees_to_remind = Employee.objects.filter(
        employment_status__in=["ACTIVE", "PROBATION"]
    ).exclude(id__in=checked_in_employees)

    reminder_count = 0
    for employee in employees_to_remind:
        try:
            Notification.objects.create(
                recipient=employee.user,
                notification_type=Notification.NotificationType.ATTENDANCE,
                title="Attendance Reminder",
                message=(
                    f"Dear {employee.full_name}, you haven't marked your "
                    f"attendance for today ({today}). Please check in."
                ),
                link="/hr/attendance",
                metadata={"date": str(today)},
            )
            reminder_count += 1
        except Exception as e:
            logger.error(
                "Failed to send attendance reminder to %s: %s",
                employee.user.email,
                str(e),
            )

    logger.info("Sent %d attendance reminders", reminder_count)
    return {
        "status": "success",
        "reminder_count": reminder_count,
    }


@shared_task(name="auto_mark_absent")
def auto_mark_absent() -> dict:
    """
    Auto-mark absent employees who didn't check in.

    This task runs at the end of each working day to mark employees
    as absent if they didn't check in.

    Returns:
        dict: Summary of the operation
    """
    from .models import Attendance, AttendanceSettings, Employee

    today = date.today()

    settings = AttendanceSettings.objects.first()
    if not settings:
        return {"status": "skipped", "reason": "No attendance settings configured"}

    # Get employees who don't have attendance records for today
    employees_with_attendance = Attendance.objects.filter(
        date=today
    ).values_list("employee_id", flat=True)

    employees_to_mark = Employee.objects.filter(
        employment_status__in=["ACTIVE", "PROBATION"]
    ).exclude(id__in=employees_with_attendance)

    marked_count = 0
    for employee in employees_to_mark:
        try:
            Attendance.objects.create(
                employee=employee,
                date=today,
                status="ABSENT",
                notes="Auto-marked absent",
            )
            marked_count += 1
        except Exception as e:
            logger.error(
                "Failed to mark absent for %s: %s",
                employee.user.email,
                str(e),
            )

    logger.info("Auto-marked %d employees as absent", marked_count)
    return {
        "status": "success",
        "marked_absent_count": marked_count,
    }


@shared_task(name="generate_monthly_payroll")
def generate_monthly_payroll() -> dict:
    """
    Generate payroll records for all active employees for the current month.

    This task runs on the 1st of each month to create payroll records.

    Returns:
        dict: Summary of the operation
    """
    from .models import Employee, Payroll, SalaryStructure

    today = timezone.now().date()
    # Generate for previous month
    if today.month == 1:
        month = 12
        year = today.year - 1
    else:
        month = today.month - 1
        year = today.year

    active_employees = Employee.objects.filter(
        employment_status__in=["ACTIVE", "PROBATION"]
    )

    created_count = 0
    skipped_count = 0

    for employee in active_employees:
        # Skip if payroll already exists
        if Payroll.objects.filter(
            employee=employee, month=month, year=year
        ).exists():
            skipped_count += 1
            continue

        # Get active salary structure
        salary_structure = SalaryStructure.objects.filter(
            employee=employee, is_active=True
        ).first()

        if not salary_structure:
            logger.warning(
                "No salary structure for %s, skipping payroll",
                employee.full_name,
            )
            skipped_count += 1
            continue

        try:
            Payroll.objects.create(
                employee=employee,
                salary_structure=salary_structure,
                month=month,
                year=year,
                status="DRAFT",
                basic_salary=salary_structure.basic_salary,
                house_rent_allowance=salary_structure.house_rent_allowance,
                dearness_allowance=salary_structure.dearness_allowance,
                travel_allowance=salary_structure.travel_allowance,
                medical_allowance=salary_structure.medical_allowance,
                special_allowance=salary_structure.special_allowance,
                bonus=salary_structure.bonus,
                other_earnings=salary_structure.other_earnings,
                provident_fund=salary_structure.provident_fund,
                professional_tax=salary_structure.professional_tax,
                income_tax=salary_structure.income_tax,
                insurance=salary_structure.insurance,
                loan_deduction=salary_structure.loan_deduction,
                other_deductions=salary_structure.other_deductions,
                total_earnings=salary_structure.total_earnings,
                total_deductions=salary_structure.total_deductions,
                net_pay=salary_structure.net_salary,
            )
            created_count += 1
        except Exception as e:
            logger.error(
                "Failed to create payroll for %s: %s",
                employee.full_name,
                str(e),
            )

    logger.info(
        "Generated %d payroll records, skipped %d",
        created_count,
        skipped_count,
    )
    return {
        "status": "success",
        "created": created_count,
        "skipped": skipped_count,
    }
