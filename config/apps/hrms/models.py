"""
Core HRMS models for the AI-Powered Human Resource Management System.

Includes models for:
- Department & Designation
- Employee (profile extending User)
- Attendance & Leave Management
- Payroll & Compensation
- Performance Reviews
- Documents & Compliance
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.utils.translation import gettext_lazy as _


# =============================================================================
# Department & Designation
# =============================================================================


class Department(models.Model):
    """
    Represents a department within the organization.

    Departments are hierarchical and can have parent-child relationships.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Department Name"))
    code = models.CharField(
        max_length=10,
        unique=True,
        validators=[RegexValidator(r"^[A-Z0-9]+$", "Only uppercase letters and numbers allowed.")],
        verbose_name=_("Department Code"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent Department"),
    )
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_departments",
        verbose_name=_("Department Head"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Department")
        verbose_name_plural = _("Departments")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Designation(models.Model):
    """
    Represents a job title or position within a department.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100, verbose_name=_("Designation Title"))
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="designations",
        verbose_name=_("Department"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))
    level = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        verbose_name=_("Level"),
        help_text=_("Hierarchical level (1 = entry, 20 = executive)"),
    )
    salary_range_min = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_("Minimum Salary"),
    )
    salary_range_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_("Maximum Salary"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Designation")
        verbose_name_plural = _("Designations")
        ordering = ["department", "level", "title"]
        unique_together = ["title", "department"]
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["level"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} - {self.department.name}"


# =============================================================================
# Employee Profile
# =============================================================================


class Employee(models.Model):
    """
    Extended employee profile linked to the User model.

    Contains all HRMS-specific employee information beyond authentication.
    """

    class EmploymentStatus(models.TextChoices):
        ACTIVE = "ACTIVE", _("Active")
        PROBATION = "PROBATION", _("Probation")
        SUSPENDED = "SUSPENDED", _("Suspended")
        TERMINATED = "TERMINATED", _("Terminated")
        RESIGNED = "RESIGNED", _("Resigned")
        RETIRED = "RETIRED", _("Retired")

    class EmploymentType(models.TextChoices):
        FULL_TIME = "FULL_TIME", _("Full-Time")
        PART_TIME = "PART_TIME", _("Part-Time")
        CONTRACT = "CONTRACT", _("Contract")
        INTERN = "INTERN", _("Intern")
        FREELANCE = "FREELANCE", _("Freelance")

    class MaritalStatus(models.TextChoices):
        SINGLE = "SINGLE", _("Single")
        MARRIED = "MARRIED", _("Married")
        DIVORCED = "DIVORCED", _("Divorced")
        WIDOWED = "WIDOWED", _("Widowed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee_profile",
        verbose_name=_("User"),
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
        verbose_name=_("Department"),
    )
    designation = models.ForeignKey(
        Designation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
        verbose_name=_("Designation"),
    )
    reporting_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subordinates",
        verbose_name=_("Reports To"),
    )

    # Employment details
    employment_status = models.CharField(
        max_length=20,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.PROBATION,
        verbose_name=_("Employment Status"),
    )
    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME,
        verbose_name=_("Employment Type"),
    )
    joining_date = models.DateField(verbose_name=_("Joining Date"))
    confirmation_date = models.DateField(
        null=True, blank=True, verbose_name=_("Confirmation Date")
    )
    exit_date = models.DateField(null=True, blank=True, verbose_name=_("Exit Date"))
    exit_reason = models.TextField(blank=True, verbose_name=_("Exit Reason"))

    # Personal details
    marital_status = models.CharField(
        max_length=10,
        choices=MaritalStatus.choices,
        default=MaritalStatus.SINGLE,
        verbose_name=_("Marital Status"),
    )
    nationality = models.CharField(max_length=50, blank=True, verbose_name=_("Nationality"))
    blood_group = models.CharField(max_length=5, blank=True, verbose_name=_("Blood Group"))
    emergency_contact_name = models.CharField(
        max_length=100, blank=True, verbose_name=_("Emergency Contact Name")
    )
    emergency_contact_phone = models.CharField(
        max_length=20, blank=True, verbose_name=_("Emergency Contact Phone")
    )
    emergency_contact_relation = models.CharField(
        max_length=50, blank=True, verbose_name=_("Emergency Contact Relation")
    )

    # Address
    present_address = models.TextField(blank=True, verbose_name=_("Present Address"))
    permanent_address = models.TextField(blank=True, verbose_name=_("Permanent Address"))
    city = models.CharField(max_length=50, blank=True, verbose_name=_("City"))
    state = models.CharField(max_length=50, blank=True, verbose_name=_("State/Province"))
    country = models.CharField(max_length=50, blank=True, verbose_name=_("Country"))
    postal_code = models.CharField(max_length=20, blank=True, verbose_name=_("Postal Code"))

    # Bank details
    bank_name = models.CharField(max_length=100, blank=True, verbose_name=_("Bank Name"))
    bank_account_number = models.CharField(
        max_length=50, blank=True, verbose_name=_("Bank Account Number")
    )
    bank_ifsc_code = models.CharField(max_length=20, blank=True, verbose_name=_("IFSC Code"))
    bank_branch = models.CharField(max_length=100, blank=True, verbose_name=_("Bank Branch"))
    pan_number = models.CharField(max_length=20, blank=True, verbose_name=_("PAN Number"))
    aadhar_number = models.CharField(
        max_length=20, blank=True, verbose_name=_("Aadhar Number")
    )

    # Education
    highest_education = models.CharField(
        max_length=100, blank=True, verbose_name=_("Highest Education")
    )
    institution = models.CharField(
        max_length=200, blank=True, verbose_name=_("Institution")
    )
    year_of_passing = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_("Year of Passing")
    )
    skills = models.JSONField(
        default=list, blank=True, verbose_name=_("Skills"),
        help_text=_("List of skills as JSON array"),
    )

    # Documents
    resume = models.FileField(
        upload_to="documents/resumes/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["pdf", "doc", "docx"])],
        verbose_name=_("Resume"),
    )
    offer_letter = models.FileField(
        upload_to="documents/offer_letters/",
        blank=True,
        null=True,
        verbose_name=_("Offer Letter"),
    )
    other_documents = models.FileField(
        upload_to="documents/other/",
        blank=True,
        null=True,
        verbose_name=_("Other Documents"),
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Employee")
        verbose_name_plural = _("Employees")
        ordering = ["-joining_date"]
        indexes = [
            models.Index(fields=["employment_status"]),
            models.Index(fields=["employment_type"]),
            models.Index(fields=["joining_date"]),
            models.Index(fields=["department", "employment_status"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.get_full_name()} - {self.department}"

    @property
    def full_name(self) -> str:
        """Get the employee's full name from the associated user."""
        return self.user.get_full_name()

    @property
    def employee_id(self) -> str:
        """Get the employee ID from the associated user."""
        return self.user.employee_id

    @property
    def email(self) -> str:
        """Get the employee's email from the associated user."""
        return self.user.email

    @property
    def phone(self) -> str:
        """Get the employee's phone from the associated user."""
        return self.user.phone_number

    @property
    def years_of_service(self) -> float:
        """Calculate years of service."""
        from datetime import date

        if not self.joining_date:
            return 0.0
        delta = (date.today() - self.joining_date).days
        return round(delta / 365.25, 1)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Auto-set user_type on the associated user when employee is created."""
        if not self.pk and self.user:
            self.user.user_type = "EMPLOYEE"
            self.user.save(update_fields=["user_type"])
        super().save(*args, **kwargs)


# =============================================================================
# Attendance
# =============================================================================


class Attendance(models.Model):
    """
    Tracks daily employee attendance with check-in/check-out times.
    """

    class AttendanceStatus(models.TextChoices):
        PRESENT = "PRESENT", _("Present")
        ABSENT = "ABSENT", _("Absent")
        LATE = "LATE", _("Late")
        HALF_DAY = "HALF_DAY", _("Half Day")
        ON_LEAVE = "ON_LEAVE", _("On Leave")
        WORK_FROM_HOME = "WFH", _("Work From Home")
        HOLIDAY = "HOLIDAY", _("Holiday")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="attendances",
        verbose_name=_("Employee"),
    )
    date = models.DateField(verbose_name=_("Date"))
    check_in = models.DateTimeField(null=True, blank=True, verbose_name=_("Check In"))
    check_out = models.DateTimeField(null=True, blank=True, verbose_name=_("Check Out"))
    status = models.CharField(
        max_length=10,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
        verbose_name=_("Status"),
    )
    is_late = models.BooleanField(default=False, verbose_name=_("Is Late"))
    late_minutes = models.PositiveIntegerField(default=0, verbose_name=_("Late Minutes"))
    early_leave_minutes = models.PositiveIntegerField(
        default=0, verbose_name=_("Early Leave Minutes")
    )
    overtime_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Overtime Hours"),
    )
    work_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Work Hours"),
    )
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, verbose_name=_("IP Address")
    )
    location = models.CharField(
        max_length=200, blank=True, verbose_name=_("Location")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Attendance")
        verbose_name_plural = _("Attendance Records")
        ordering = ["-date", "employee"]
        unique_together = ["employee", "date"]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["employee", "date"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee} - {self.date} ({self.status})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Calculate work hours and auto-set status based on check-in/out times."""
        if self.check_in and self.check_out:
            delta = self.check_out - self.check_in
            hours = delta.total_seconds() / 3600
            self.work_hours = Decimal(str(round(hours, 2)))

            if hours >= 8:
                if self.status not in [
                    Attendance.AttendanceStatus.ON_LEAVE,
                    Attendance.AttendanceStatus.HOLIDAY,
                ]:
                    self.status = Attendance.AttendanceStatus.PRESENT
            elif hours >= 4:
                self.status = Attendance.AttendanceStatus.HALF_DAY
            elif hours > 0:
                self.status = Attendance.AttendanceStatus.LATE

        super().save(*args, **kwargs)


class AttendanceSettings(models.Model):
    """
    Global attendance configuration for the organization.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    office_start_time = models.TimeField(
        default="09:00", verbose_name=_("Office Start Time")
    )
    office_end_time = models.TimeField(
        default="18:00", verbose_name=_("Office End Time")
    )
    grace_period_minutes = models.PositiveIntegerField(
        default=15, verbose_name=_("Grace Period (Minutes)")
    )
    half_day_hours = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal("4.00"),
        verbose_name=_("Half Day Hours"),
    )
    full_day_hours = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal("8.00"),
        verbose_name=_("Full Day Hours"),
    )
    working_days = models.JSONField(
        default=list, verbose_name=_("Working Days"),
        help_text=_("List of working days (0=Monday, 6=Sunday)"),
    )
    enable_geo_fencing = models.BooleanField(
        default=False, verbose_name=_("Enable Geo-Fencing")
    )
    office_latitude = models.FloatField(null=True, blank=True)
    office_longitude = models.FloatField(null=True, blank=True)
    geo_fence_radius_meters = models.PositiveIntegerField(
        default=100, verbose_name=_("Geo-Fence Radius (meters)")
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Updated By"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Attendance Setting")
        verbose_name_plural = _("Attendance Settings")

    def __str__(self) -> str:
        return f"Attendance Settings ({self.office_start_time} - {self.office_end_time})"


# =============================================================================
# Leave Management
# =============================================================================


class LeaveType(models.Model):
    """
    Defines types of leaves available in the organization.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, verbose_name=_("Leave Type"))
    code = models.CharField(max_length=10, unique=True, verbose_name=_("Leave Code"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    days_per_year = models.PositiveIntegerField(default=0, verbose_name=_("Days Per Year"))
    is_carry_forward = models.BooleanField(
        default=False, verbose_name=_("Is Carry Forward")
    )
    max_carry_forward_days = models.PositiveIntegerField(
        default=0, verbose_name=_("Max Carry Forward Days")
    )
    is_paid = models.BooleanField(default=True, verbose_name=_("Is Paid"))
    requires_approval = models.BooleanField(
        default=True, verbose_name=_("Requires Approval")
    )
    min_days_before_apply = models.PositiveIntegerField(
        default=1, verbose_name=_("Min Days Before Apply"),
        help_text=_("Minimum days in advance to apply for this leave"),
    )
    max_consecutive_days = models.PositiveIntegerField(
        default=30, verbose_name=_("Max Consecutive Days")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Leave Type")
        verbose_name_plural = _("Leave Types")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class LeaveAllocation(models.Model):
    """
    Tracks leave balance for each employee per leave type.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="leave_allocations"
    )
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.CASCADE, related_name="allocations"
    )
    year = models.PositiveIntegerField(verbose_name=_("Year"))
    total_days = models.DecimalField(
        max_digits=5, decimal_places=1, verbose_name=_("Total Days")
    )
    used_days = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal("0.0"), verbose_name=_("Used Days")
    )
    pending_days = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal("0.0"), verbose_name=_("Pending Days")
    )
    carried_forward = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal("0.0"), verbose_name=_("Carried Forward")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Leave Allocation")
        verbose_name_plural = _("Leave Allocations")
        unique_together = ["employee", "leave_type", "year"]
        indexes = [models.Index(fields=["employee", "year"])]

    @property
    def remaining_days(self) -> Decimal:
        """Calculate remaining leave days."""
        return self.total_days - self.used_days - self.pending_days

    def __str__(self) -> str:
        return f"{self.employee} - {self.leave_type} ({self.year})"


class LeaveRequest(models.Model):
    """
    Employee leave request with approval workflow.
    """

    class LeaveStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")
        CANCELLED = "CANCELLED", _("Cancelled")

    class LeaveHalf(models.TextChoices):
        FULL = "FULL", _("Full Day")
        FIRST_HALF = "FIRST_HALF", _("First Half")
        SECOND_HALF = "SECOND_HALF", _("Second Half")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="leave_requests"
    )
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.CASCADE, related_name="requests"
    )
    start_date = models.DateField(verbose_name=_("Start Date"))
    end_date = models.DateField(verbose_name=_("End Date"))
    half_day = models.CharField(
        max_length=15, choices=LeaveHalf.choices, default=LeaveHalf.FULL
    )
    total_days = models.DecimalField(
        max_digits=4, decimal_places=1, verbose_name=_("Total Days")
    )
    reason = models.TextField(verbose_name=_("Reason"))
    status = models.CharField(
        max_length=15, choices=LeaveStatus.choices, default=LeaveStatus.PENDING
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leaves",
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    is_emergency = models.BooleanField(default=False)
    contact_during_leave = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Leave Request")
        verbose_name_plural = _("Leave Requests")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["employee", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee} - {self.leave_type} ({self.start_date} to {self.end_date})"


class Holiday(models.Model):
    """
    Company holidays and observances.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name=_("Holiday Name"))
    date = models.DateField(verbose_name=_("Date"))
    is_recurring = models.BooleanField(default=False, verbose_name=_("Is Recurring Yearly"))
    type = models.CharField(
        max_length=20,
        choices=[
            ("NATIONAL", _("National Holiday")),
            ("COMPANY", _("Company Holiday")),
            ("RELIGIOUS", _("Religious Holiday")),
            ("OTHER", _("Other")),
        ],
        default="NATIONAL",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Holiday")
        verbose_name_plural = _("Holidays")
        ordering = ["date"]
        unique_together = ["name", "date"]
        indexes = [models.Index(fields=["date"])]

    def __str__(self) -> str:
        return f"{self.name} - {self.date}"


# =============================================================================
# Payroll & Compensation
# =============================================================================


class SalaryStructure(models.Model):
    """
    Defines salary components and structure for employees.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name=_("Structure Name"))
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="salary_structures"
    )
    effective_from = models.DateField(verbose_name=_("Effective From"))
    effective_to = models.DateField(null=True, blank=True, verbose_name=_("Effective To"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    # Earnings
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    house_rent_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    dearness_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    travel_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    medical_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    special_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    other_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    # Deductions
    provident_fund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    professional_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    income_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    insurance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    loan_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Salary Structure")
        verbose_name_plural = _("Salary Structures")
        ordering = ["-effective_from"]
        indexes = [models.Index(fields=["employee", "is_active"])]

    @property
    def total_earnings(self) -> Decimal:
        return (
            self.basic_salary + self.house_rent_allowance + self.dearness_allowance
            + self.travel_allowance + self.medical_allowance + self.special_allowance
            + self.bonus + self.other_earnings
        )

    @property
    def total_deductions(self) -> Decimal:
        return (
            self.provident_fund + self.professional_tax + self.income_tax
            + self.insurance + self.loan_deduction + self.other_deductions
        )

    @property
    def net_salary(self) -> Decimal:
        return self.total_earnings - self.total_deductions

    @property
    def ctc(self) -> Decimal:
        return self.total_earnings * 12

    def __str__(self) -> str:
        return f"{self.employee} - {self.name} ({self.effective_from})"


class Payroll(models.Model):
    """
    Monthly payroll record for each employee.
    """

    class PayrollStatus(models.TextChoices):
        DRAFT = "DRAFT", _("Draft")
        PENDING = "PENDING", _("Pending")
        PROCESSED = "PROCESSED", _("Processed")
        PAID = "PAID", _("Paid")
        CANCELLED = "CANCELLED", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="payrolls"
    )
    salary_structure = models.ForeignKey(
        SalaryStructure, on_delete=models.SET_NULL, null=True, blank=True, related_name="payrolls"
    )
    month = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    year = models.PositiveIntegerField()
    status = models.CharField(
        max_length=15, choices=PayrollStatus.choices, default=PayrollStatus.DRAFT
    )

    # Earnings
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    house_rent_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    dearness_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    travel_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    medical_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    special_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    overtime_pay = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    other_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    # Deductions
    provident_fund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    professional_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    income_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    insurance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    loan_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    leave_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    # Totals
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    # Payment
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ("BANK_TRANSFER", _("Bank Transfer")),
            ("CHEQUE", _("Cheque")),
            ("CASH", _("Cash")),
        ],
        default="BANK_TRANSFER",
    )
    transaction_id = models.CharField(max_length=100, blank=True)
    remarks = models.TextField(blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="processed_payrolls"
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Payroll")
        verbose_name_plural = _("Payroll Records")
        ordering = ["-year", "-month"]
        unique_together = ["employee", "month", "year"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["month", "year"]),
            models.Index(fields=["employee", "month", "year"]),
        ]

    def __str__(self) -> str:
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        return f"{self.employee} - {month_names[self.month - 1]} {self.year}"


# =============================================================================
# Performance Management
# =============================================================================


class PerformanceReview(models.Model):
    """
    Employee performance review record.
    """

    class ReviewStatus(models.TextChoices):
        DRAFT = "DRAFT", _("Draft")
        SUBMITTED = "SUBMITTED", _("Submitted")
        IN_REVIEW = "IN_REVIEW", _("In Review")
        COMPLETED = "COMPLETED", _("Completed")
        CANCELLED = "CANCELLED", _("Cancelled")

    class Rating(models.IntegerChoices):
        EXCELLENT = 5, _("Excellent")
        GOOD = 4, _("Good")
        SATISFACTORY = 3, _("Satisfactory")
        NEEDS_IMPROVEMENT = 2, _("Needs Improvement")
        POOR = 1, _("Poor")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="performance_reviews"
    )
    reviewer = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="reviews_given"
    )
    review_period_start = models.DateField()
    review_period_end = models.DateField()
    due_date = models.DateField()
    status = models.CharField(
        max_length=15, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT
    )

    # Ratings
    technical_skills = models.IntegerField(choices=Rating.choices, null=True, blank=True)
    communication = models.IntegerField(choices=Rating.choices, null=True, blank=True)
    teamwork = models.IntegerField(choices=Rating.choices, null=True, blank=True)
    leadership = models.IntegerField(choices=Rating.choices, null=True, blank=True)
    productivity = models.IntegerField(choices=Rating.choices, null=True, blank=True)
    punctuality = models.IntegerField(choices=Rating.choices, null=True, blank=True)
    overall_rating = models.DecimalField(
        max_digits=3, decimal_places=1, null=True, blank=True
    )
    strengths = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    goals = models.TextField(blank=True)
    reviewer_comments = models.TextField(blank=True)
    employee_comments = models.TextField(blank=True)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Performance Review")
        verbose_name_plural = _("Performance Reviews")
        ordering = ["-review_period_end"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["employee", "status"]),
            models.Index(fields=["reviewer"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee} Review ({self.review_period_start} - {self.review_period_end})"


class Goal(models.Model):
    """
    Employee goals and OKRs.
    """

    class GoalStatus(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", _("Not Started")
        IN_PROGRESS = "IN_PROGRESS", _("In Progress")
        COMPLETED = "COMPLETED", _("Completed")
        ON_HOLD = "ON_HOLD", _("On Hold")
        CANCELLED = "CANCELLED", _("Cancelled")

    class GoalType(models.TextChoices):
        QUARTERLY = "QUARTERLY", _("Quarterly")
        ANNUAL = "ANNUAL", _("Annual")
        PROJECT = "PROJECT", _("Project Based")
        PERSONAL = "PERSONAL", _("Personal Development")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="goals"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    goal_type = models.CharField(
        max_length=15, choices=GoalType.choices, default=GoalType.QUARTERLY
    )
    status = models.CharField(
        max_length=15, choices=GoalStatus.choices, default=GoalStatus.NOT_STARTED
    )
    start_date = models.DateField()
    end_date = models.DateField()
    progress_percentage = models.PositiveIntegerField(
        default=0, validators=[MaxValueValidator(100)]
    )
    key_results = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Goal")
        verbose_name_plural = _("Goals")
        ordering = ["-end_date"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["employee", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee} - {self.title}"


# =============================================================================
# Notifications
# =============================================================================


class Notification(models.Model):
    """
    System notification for employees.
    """

    class NotificationType(models.TextChoices):
        LEAVE_REQUEST = "LEAVE_REQUEST", _("Leave Request")
        LEAVE_APPROVED = "LEAVE_APPROVED", _("Leave Approved")
        LEAVE_REJECTED = "LEAVE_REJECTED", _("Leave Rejected")
        ATTENDANCE = "ATTENDANCE", _("Attendance")
        PAYROLL = "PAYROLL", _("Payroll")
        PERFORMANCE = "PERFORMANCE", _("Performance Review")
        GENERAL = "GENERAL", _("General")
        SYSTEM = "SYSTEM", _("System")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(
        max_length=20, choices=NotificationType.choices, default=NotificationType.GENERAL
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    link = models.CharField(max_length=500, blank=True, help_text=_("Deep link URL"))
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["notification_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.recipient} - {self.title}"


class AutomationRule(models.Model):
    """
    Configurable automation rule for triggering actions on HRMS events.

    When a trigger_event occurs (e.g., LEAVE_APPROVED), the RuleEngine
    evaluates the condition_expression against the event context. If the
    condition matches, the action_type is executed with action_config.
    """

    class TriggerEvent(models.TextChoices):
        EMPLOYEE_CREATED = "EMPLOYEE_CREATED", _("Employee Created")
        LEAVE_REQUESTED = "LEAVE_REQUESTED", _("Leave Requested")
        LEAVE_APPROVED = "LEAVE_APPROVED", _("Leave Approved")
        LEAVE_REJECTED = "LEAVE_REJECTED", _("Leave Rejected")
        ATTENDANCE_MARKED = "ATTENDANCE_MARKED", _("Attendance Marked")
        PAYROLL_PROCESSED = "PAYROLL_PROCESSED", _("Payroll Processed")
        REVIEW_SUBMITTED = "REVIEW_SUBMITTED", _("Review Submitted")

    class ActionType(models.TextChoices):
        SEND_NOTIFICATION = "SEND_NOTIFICATION", _("Send Notification")
        UPDATE_FIELD = "UPDATE_FIELD", _("Update Field")
        CREATE_RECORD = "CREATE_RECORD", _("Create Record")
        TRIGGER_WEBHOOK = "TRIGGER_WEBHOOK", _("Trigger Webhook")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(
        max_length=200,
        verbose_name=_("Rule Name"),
        help_text=_("A human-readable name for this automation rule"),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Optional description of what this rule does"),
    )
    trigger_event = models.CharField(
        max_length=50,
        choices=TriggerEvent.choices,
        verbose_name=_("Trigger Event"),
        help_text=_("The HRMS event that triggers this rule"),
    )
    condition_expression = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Condition Expression"),
        help_text=_("JSON conditions to filter when the action should execute (e.g., {'status': 'ABSENT'})"),
    )
    action_type = models.CharField(
        max_length=50,
        choices=ActionType.choices,
        verbose_name=_("Action Type"),
        help_text=_("The type of action to perform when triggered"),
    )
    action_config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Action Configuration"),
        help_text=_("JSON configuration for the action (e.g., notification message, field to update)"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_("Enable or disable this rule"),
    )
    priority = models.IntegerField(
        default=0,
        verbose_name=_("Priority"),
        help_text=_("Higher priority rules are evaluated first"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Automation Rule")
        verbose_name_plural = _("Automation Rules")
        ordering = ["-priority", "name"]
        indexes = [
            models.Index(fields=["trigger_event", "is_active"]),
            models.Index(fields=["priority"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_trigger_event_display()} → {self.get_action_type_display()})"


class SystemSettings(models.Model):
    """
    Singleton model for system-wide configuration settings.

    Stores AI provider configuration (DeepSeek vs OpenAI), API keys,
    base URLs, model names, and other global settings.
    """

    class AIProvider(models.TextChoices):
        DEEPSEEK = "DEEPSEEK", _("DeepSeek")
        OPENAI = "OPENAI", _("OpenAI")

    # AI Provider Configuration
    ai_provider = models.CharField(
        max_length=20,
        choices=AIProvider.choices,
        default=AIProvider.DEEPSEEK,
        verbose_name=_("AI Provider"),
        help_text=_("Select the AI provider for chatbot and AI features"),
    )
    deepseek_api_key = models.CharField(
        max_length=500, blank=True, verbose_name=_("DeepSeek API Key"),
        help_text=_("API key for DeepSeek (https://api.deepseek.com)"),
    )
    deepseek_base_url = models.CharField(
        max_length=500, blank=True, default="https://api.deepseek.com/v1",
        verbose_name=_("DeepSeek Base URL"),
    )
    deepseek_model = models.CharField(
        max_length=100, blank=True, default="deepseek-chat",
        verbose_name=_("DeepSeek Model"),
    )
    openai_api_key = models.CharField(
        max_length=500, blank=True, verbose_name=_("OpenAI API Key"),
        help_text=_("API key for OpenAI (https://api.openai.com)"),
    )
    openai_base_url = models.CharField(
        max_length=500, blank=True, default="https://api.openai.com/v1",
        verbose_name=_("OpenAI Base URL"),
    )
    openai_model = models.CharField(
        max_length=100, blank=True, default="gpt-4o-mini",
        verbose_name=_("OpenAI Model"),
    )
    embedding_model = models.CharField(
        max_length=100, blank=True, default="text-embedding-ada-002",
        verbose_name=_("Embedding Model"),
    )
    max_tokens = models.IntegerField(default=4096, verbose_name=_("Max Tokens"))
    temperature = models.FloatField(default=0.7, verbose_name=_("Temperature"))

    # Notification Settings
    notify_leave_requests = models.BooleanField(default=True, verbose_name=_("Notify on Leave Requests"))
    notify_payroll_updates = models.BooleanField(default=True, verbose_name=_("Notify on Payroll Updates"))
    notify_attendance_anomalies = models.BooleanField(default=True, verbose_name=_("Notify on Attendance Anomalies"))
    notify_performance_reviews = models.BooleanField(default=True, verbose_name=_("Notify on Performance Reviews"))
    notify_new_employees = models.BooleanField(default=True, verbose_name=_("Notify on New Employees"))

    # Metadata
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_("Updated By"),
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("System Settings")
        verbose_name_plural = _("System Settings")

    def __str__(self) -> str:
        return f"System Settings (AI: {self.get_ai_provider_display()})"

    @classmethod
    def get_settings(cls) -> "SystemSettings":
        """Get or create the singleton settings instance."""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def get_active_api_key(self) -> str:
        """Get the API key for the currently active provider."""
        if self.ai_provider == self.AIProvider.OPENAI:
            return self.openai_api_key
        return self.deepseek_api_key

    def get_active_base_url(self) -> str:
        """Get the base URL for the currently active provider."""
        if self.ai_provider == self.AIProvider.OPENAI:
            return self.openai_base_url or "https://api.openai.com/v1"
        return self.deepseek_base_url or "https://api.deepseek.com/v1"

    def get_active_model(self) -> str:
        """Get the model name for the currently active provider."""
        if self.ai_provider == self.AIProvider.OPENAI:
            return self.openai_model or "gpt-4o-mini"
        return self.deepseek_model or "deepseek-chat"