"""
Admin configuration for the HRMS app.
"""

from django.contrib import admin

from .models import (
    Attendance,
    AttendanceSettings,
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


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "head", "parent", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "code"]
    prepopulated_fields = {"code": ("name",)}


@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ["title", "department", "level", "is_active"]
    list_filter = ["department", "is_active"]
    search_fields = ["title"]


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        "user", "employee_id", "department", "designation",
        "employment_status", "employment_type", "joining_date",
    ]
    list_filter = [
        "employment_status", "employment_type", "department",
        "marital_status",
    ]
    search_fields = [
        "user__username", "user__email", "user__first_name",
        "user__last_name", "user__employee_id",
    ]
    raw_id_fields = ["user", "reporting_to"]
    autocomplete_fields = ["user"]


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ["employee", "date", "status", "check_in", "check_out", "work_hours"]
    list_filter = ["status", "date"]
    search_fields = ["employee__user__username", "employee__user__first_name"]
    date_hierarchy = "date"


@admin.register(AttendanceSettings)
class AttendanceSettingsAdmin(admin.ModelAdmin):
    list_display = ["office_start_time", "office_end_time", "grace_period_minutes"]


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "days_per_year", "is_paid", "is_carry_forward", "is_active"]
    list_filter = ["is_paid", "is_carry_forward", "is_active"]


@admin.register(LeaveAllocation)
class LeaveAllocationAdmin(admin.ModelAdmin):
    list_display = ["employee", "leave_type", "year", "total_days", "used_days", "remaining_days"]
    list_filter = ["year", "leave_type"]
    search_fields = ["employee__user__username"]


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = [
        "employee", "leave_type", "start_date", "end_date",
        "total_days", "status", "approved_by",
    ]
    list_filter = ["status", "leave_type", "start_date"]
    search_fields = ["employee__user__username", "employee__user__first_name"]
    date_hierarchy = "start_date"


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ["name", "date", "type", "is_recurring", "is_active"]
    list_filter = ["type", "is_recurring", "is_active"]
    date_hierarchy = "date"


@admin.register(SalaryStructure)
class SalaryStructureAdmin(admin.ModelAdmin):
    list_display = ["employee", "name", "effective_from", "net_salary", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["employee__user__username"]


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ["employee", "month", "year", "status", "total_earnings", "total_deductions", "net_pay"]
    list_filter = ["status", "month", "year"]
    search_fields = ["employee__user__username"]
    date_hierarchy = "created_at"


@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = ["employee", "reviewer", "review_period_start", "review_period_end", "status", "overall_rating"]
    list_filter = ["status"]
    search_fields = ["employee__user__username"]


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ["employee", "title", "goal_type", "status", "progress_percentage", "end_date"]
    list_filter = ["status", "goal_type"]
    search_fields = ["employee__user__username", "title"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["recipient", "notification_type", "title", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read"]
    search_fields = ["recipient__username", "title"]
