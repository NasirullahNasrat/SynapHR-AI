"""
URL configuration for the HRMS app.
"""

from django.urls import path

from . import views

app_name = "hrms"

urlpatterns = [
    # Dashboard
    path("dashboard/", views.dashboard_stats, name="dashboard"),
    # Departments
    path("departments/", views.DepartmentListCreateView.as_view(), name="department-list"),
    path("departments/<uuid:pk>/", views.DepartmentDetailView.as_view(), name="department-detail"),
    # Designations
    path("designations/", views.DesignationListCreateView.as_view(), name="designation-list"),
    path("designations/<uuid:pk>/", views.DesignationDetailView.as_view(), name="designation-detail"),
    # Employees
    path("employees/", views.EmployeeListCreateView.as_view(), name="employee-list"),
    path("employees/<uuid:pk>/", views.EmployeeDetailView.as_view(), name="employee-detail"),
    # Attendance
    path("attendance/", views.AttendanceListCreateView.as_view(), name="attendance-list"),
    path("attendance/settings/", views.AttendanceSettingsView.as_view(), name="attendance-settings"),
    path("attendance/bulk/", views.mark_attendance_bulk, name="attendance-bulk"),
    path("attendance/<uuid:pk>/", views.AttendanceDetailView.as_view(), name="attendance-detail"),
    # Leave Types
    path("leave-types/", views.LeaveTypeListCreateView.as_view(), name="leavetype-list"),
    path("leave-types/<uuid:pk>/", views.LeaveTypeDetailView.as_view(), name="leavetype-detail"),
    # Leave Allocations
    path("leave-allocations/", views.LeaveAllocationListCreateView.as_view(), name="leaveallocation-list"),
    path("leave-allocations/<uuid:pk>/", views.LeaveAllocationDetailView.as_view(), name="leaveallocation-detail"),
    # Leave Requests
    path("leave-requests/", views.LeaveRequestListCreateView.as_view(), name="leaverequest-list"),
    path("leave-requests/<uuid:pk>/", views.LeaveRequestDetailView.as_view(), name="leaverequest-detail"),
    path("leave-requests/<uuid:pk>/approve/", views.approve_leave_request, name="leaverequest-approve"),
    path("leave-requests/<uuid:pk>/reject/", views.reject_leave_request, name="leaverequest-reject"),
    # Holidays
    path("holidays/", views.HolidayListCreateView.as_view(), name="holiday-list"),
    path("holidays/<uuid:pk>/", views.HolidayDetailView.as_view(), name="holiday-detail"),
    # Salary Structures
    path("salary-structures/", views.SalaryStructureListCreateView.as_view(), name="salarystructure-list"),
    path("salary-structures/<uuid:pk>/", views.SalaryStructureDetailView.as_view(), name="salarystructure-detail"),
    # Payroll
    path("payroll/", views.PayrollListCreateView.as_view(), name="payroll-list"),
    path("payroll/<uuid:pk>/", views.PayrollDetailView.as_view(), name="payroll-detail"),
    path("payroll/process/", views.process_payroll, name="payroll-process"),
    # Performance Reviews
    path("performance-reviews/", views.PerformanceReviewListCreateView.as_view(), name="performancereview-list"),
    path("performance-reviews/<uuid:pk>/", views.PerformanceReviewDetailView.as_view(), name="performancereview-detail"),
    # Goals
    path("goals/", views.GoalListCreateView.as_view(), name="goal-list"),
    path("goals/<uuid:pk>/", views.GoalDetailView.as_view(), name="goal-detail"),
    # Notifications
    path("notifications/", views.NotificationListView.as_view(), name="notification-list"),
    path("notifications/<uuid:pk>/read/", views.mark_notification_read, name="notification-read"),
    path("notifications/read-all/", views.mark_all_notifications_read, name="notification-read-all"),
    path("notifications/unread-count/", views.unread_notification_count, name="notification-unread-count"),
    # Automation Rules
    path("automation-rules/", views.AutomationRuleListCreateView.as_view(), name="automationrule-list"),
    path("automation-rules/<uuid:pk>/", views.AutomationRuleDetailView.as_view(), name="automationrule-detail"),
    # System Settings
    path("settings/", views.SystemSettingsView.as_view(), name="system-settings"),
    # Reports
    path("reports/attendance/", views.attendance_report, name="report-attendance"),
    path("reports/payroll/", views.payroll_report, name="report-payroll"),
]
