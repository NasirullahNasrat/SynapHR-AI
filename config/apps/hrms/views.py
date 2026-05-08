"""
Views for the HRMS app.

Provides REST API endpoints for all HRMS models with proper
permissions, filtering, search, and pagination.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from rest_framework import filters, generics, permissions, serializers, status, views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from config.pagination import LargeResultsPagination, StandardPagination

from .models import (
    Attendance,
    AttendanceSettings,
    AutomationRule,
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
    SystemSettings,
)
from .serializers import (
    AttendanceSerializer,
    AttendanceSettingsSerializer,
    AutomationRuleSerializer,
    DepartmentListSerializer,
    DepartmentSerializer,
    DesignationSerializer,
    EmployeeListSerializer,
    EmployeeSerializer,
    GoalSerializer,
    HolidaySerializer,
    LeaveAllocationSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
    NotificationSerializer,
    PayrollSerializer,
    PerformanceReviewSerializer,
    SalaryStructureSerializer,
    SystemSettingsSerializer,
)

User = get_user_model()


# =============================================================================
# Permission Classes
# =============================================================================


class IsHRManager(permissions.BasePermission):
    """Permission to only allow HR managers and admins."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type in [
            "ADMIN", "HR", "MANAGER",
        ]


class IsAdminOrHR(permissions.BasePermission):
    """Permission to only allow admins and HR."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type in [
            "ADMIN", "HR",
        ]


class IsAdminOrHRForWrite(permissions.BasePermission):
    """
    Permission: Read for all authenticated users, write only for ADMIN/HR.

    Used for views where employees should be able to view data
    but only admins/HR can create, update, or delete.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        # Safe methods (GET, HEAD, OPTIONS) allowed for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        # Write methods restricted to ADMIN/HR
        return request.user.user_type in ("ADMIN", "HR")

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.user_type in ("ADMIN", "HR")


class IsAdminOrHRForWriteOrManagerForRead(permissions.BasePermission):
    """
    Permission: Read for authenticated users, write for ADMIN/HR/MANAGER.

    Used for views where employees can view but managers can also manage.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.user_type in ("ADMIN", "HR", "MANAGER")

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.user_type in ("ADMIN", "HR", "MANAGER")


class IsAdminOrHRForChatbot(permissions.BasePermission):
    """
    Permission for AI Chatbot features.

    ADMIN, HR, and MANAGER can use the AI chatbot.
    Regular EMPLOYEE role is restricted from AI features.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type in (
            "ADMIN", "HR", "MANAGER",
        )


# =============================================================================
# Dashboard
# =============================================================================


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    """
    GET api/v1/hr/dashboard/
    Get HRMS dashboard statistics with AI-enhanced analytics.
    """
    today = timezone.now().date()
    active_employee_qs = Employee.objects.filter(
        employment_status__in=["ACTIVE", "PROBATION"]
    )
    total_employees = active_employee_qs.count()
    active_employees = Employee.objects.filter(
        employment_status="ACTIVE"
    ).count()

    # Leave-based on_leave count
    on_leave_today = LeaveRequest.objects.filter(
        status="APPROVED",
        start_date__lte=today,
        end_date__gte=today,
    ).count()

    pending_leaves = LeaveRequest.objects.filter(
        status="PENDING"
    ).count()

    # Today's attendance breakdown — includes "not_marked" for employees without records
    attendance_records = Attendance.objects.filter(date=today)
    present_count = attendance_records.filter(status="PRESENT").count()
    absent_count = attendance_records.filter(status="ABSENT").count()
    late_count = attendance_records.filter(status="LATE").count()
    half_day_count = attendance_records.filter(status="HALF_DAY").count()
    on_leave_count = attendance_records.filter(status="ON_LEAVE").count()
    marked_total = present_count + absent_count + late_count + half_day_count + on_leave_count
    not_marked_count = max(0, total_employees - marked_total)

    # AI Insight: attendance completion rate
    attendance_rate = round((marked_total / total_employees * 100), 1) if total_employees > 0 else 0

    departments_count = Department.objects.filter(is_active=True).count()

    # Monthly payroll summary
    current_month = timezone.now().month
    current_year = timezone.now().year
    payroll_qs = Payroll.objects.filter(
        month=current_month,
        year=current_year,
        status__in=["PROCESSED", "PAID"],
    )
    payroll_agg = payroll_qs.aggregate(
        total_payroll=Sum("net_pay"),
        total_earnings=Sum("total_earnings"),
        total_deductions=Sum("total_deductions"),
        payroll_count=Count("id"),
    )
    avg_salary = payroll_qs.aggregate(avg=Avg("net_pay"))["avg"]

    # AI-powered insights
    insights = []
    if pending_leaves > 0:
        insights.append({
            "type": "warning",
            "icon": "CalendarCheck",
            "title": f"{pending_leaves} pending leave request(s)",
            "description": "Requires your approval action.",
        })
    if attendance_rate < 80:
        insights.append({
            "type": "info",
            "icon": "Clock",
            "title": f"Attendance is {attendance_rate}% complete",
            "description": f"{not_marked_count} employee(s) haven't been marked today.",
        })
    if on_leave_today > 0:
        insights.append({
            "type": "info",
            "icon": "Users",
            "title": f"{on_leave_today} employee(s) on leave today",
            "description": "Plan resources accordingly.",
        })
    if payroll_agg["total_payroll"] is None or payroll_agg["total_payroll"] == 0:
        insights.append({
            "type": "action",
            "icon": "DollarSign",
            "title": "Payroll not yet processed",
            "description": "Process this month's payroll to keep records up to date.",
        })

    return Response(
        {
            "success": True,
            "data": {
                "total_employees": total_employees,
                "active_employees": active_employees,
                "on_leave_today": on_leave_today,
                "pending_leaves": pending_leaves,
                "today_attendance": {
                    "present": present_count,
                    "absent": absent_count,
                    "late": late_count,
                    "half_day": half_day_count,
                    "on_leave": on_leave_count,
                    "not_marked": not_marked_count,
                    "total_marked": marked_total,
                    "completion_rate": attendance_rate,
                },
                "departments": departments_count,
                "payroll_summary": {
                    "total_payroll": payroll_agg["total_payroll"] or 0,
                    "total_net_pay": payroll_agg["total_payroll"] or 0,
                    "average_salary": avg_salary or 0,
                },
                "insights": insights,
            },
        }
    )


# =============================================================================
# Department Views
# =============================================================================


class DepartmentListCreateView(generics.ListCreateAPIView):
    """GET/POST api/v1/hr/departments/"""

    queryset = Department.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHRForWrite]
    pagination_class = StandardPagination
    search_fields = ["name", "code", "description"]
    filterset_fields = ["is_active"]

    def get_serializer_class(self):
        if self.request.method == "GET" and self.request.query_params.get("list", False):
            return DepartmentListSerializer
        return DepartmentSerializer

    def get_queryset(self):
        return Department.objects.select_related("head").prefetch_related(
            "employees", "children"
        ).all()


class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE api/v1/hr/departments/{id}/"""

    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHRForWrite]


# =============================================================================
# Designation Views
# =============================================================================


class DesignationListCreateView(generics.ListCreateAPIView):
    """GET/POST api/v1/hr/designations/"""

    queryset = Designation.objects.select_related("department").all()
    serializer_class = DesignationSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHRForWrite]
    pagination_class = StandardPagination
    search_fields = ["title", "description"]
    filterset_fields = ["department", "is_active", "level"]


class DesignationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE api/v1/hr/designations/{id}/"""

    queryset = Designation.objects.all()
    serializer_class = DesignationSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHRForWrite]


# =============================================================================
# Employee Views
# =============================================================================


class EmployeeListCreateView(generics.ListCreateAPIView):
    """GET/POST api/v1/hr/employees/"""

    permission_classes = [permissions.IsAuthenticated, IsAdminOrHRForWrite]
    pagination_class = StandardPagination
    search_fields = [
        "user__first_name", "user__last_name", "user__email",
        "user__employee_id", "user__username",
    ]
    filterset_fields = [
        "department", "designation", "employment_status",
        "employment_type", "marital_status",
    ]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return EmployeeListSerializer
        return EmployeeSerializer

    def get_queryset(self):
        return Employee.objects.select_related(
            "user", "department", "designation", "reporting_to__user"
        ).all()


class EmployeeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE api/v1/hr/employees/{id}/"""

    queryset = Employee.objects.select_related(
        "user", "department", "designation", "reporting_to__user"
    ).all()
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHRForWrite]


# =============================================================================
# Attendance Views
# =============================================================================


class AttendanceListCreateView(generics.ListCreateAPIView):
    """GET/POST api/v1/hr/attendance/"""

    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]
    pagination_class = StandardPagination
    search_fields = ["employee__user__first_name", "employee__user__last_name"]
    filterset_fields = ["status", "date", "employee", "is_late"]

    def get_serializer_class(self):
        return AttendanceSerializer

    def get_queryset(self):
        return Attendance.objects.select_related(
            "employee__user", "employee__department"
        ).all()

    def perform_create(self, serializer):
        # If employee is passed as a string (employee_id like EMP-001), resolve it
        employee_id = self.request.data.get("employee", "")
        if employee_id and not isinstance(employee_id, uuid.UUID):
            try:
                from config.apps.accounts.models import User
                user = User.objects.get(employee_id=employee_id)
                employee = Employee.objects.get(user=user)
                serializer.save(employee=employee)
                return
            except (User.DoesNotExist, Employee.DoesNotExist):
                pass
        serializer.save()


class AttendanceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE api/v1/hr/attendance/{id}/"""

    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, IsAdminOrHR])
def mark_attendance_bulk(request):
    """
    POST api/v1/hr/attendance/bulk/
    Mark attendance for multiple employees at once on the same date.
    
    Request body:
    {
        "date": "2026-05-06",
        "status": "PRESENT",
        "employees": ["emp-uuid-1", "EMP-001", "emp-uuid-2"],
        "check_in": "09:00",   # optional
        "check_out": "18:00",  # optional
        "notes": ""            # optional
    }
    """
    date_str = request.data.get("date")
    status_val = request.data.get("status", "PRESENT")
    employee_ids = request.data.get("employees", [])
    check_in = request.data.get("check_in")
    check_out = request.data.get("check_out")
    notes = request.data.get("notes", "")

    if not date_str or not employee_ids:
        return Response(
            {"success": False, "message": "date and employees are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from datetime import datetime
    from uuid import UUID

    created = 0
    skipped = 0
    errors = []

    for emp_id in employee_ids:
        try:
            # Resolve employee by UUID or employee_id string
            try:
                uuid_obj = UUID(str(emp_id))
                employee = Employee.objects.get(id=uuid_obj)
            except (ValueError, AttributeError):
                user = User.objects.get(employee_id=str(emp_id))
                employee = Employee.objects.get(user=user)

            # Check if attendance already exists for this date
            if Attendance.objects.filter(employee=employee, date=date_str).exists():
                skipped += 1
                continue

            payload = {
                "employee": employee,
                "date": date_str,
                "status": status_val,
                "notes": notes,
            }

            if check_in:
                payload["check_in"] = datetime.strptime(f"{date_str}T{check_in}", "%Y-%m-%dT%H:%M").isoformat()
            if check_out:
                payload["check_out"] = datetime.strptime(f"{date_str}T{check_out}", "%Y-%m-%dT%H:%M").isoformat()

            Attendance.objects.create(**payload)
            created += 1
        except (User.DoesNotExist, Employee.DoesNotExist):
            errors.append(f"Employee not found: {emp_id}")
        except Exception as e:
            errors.append(f"Error for {emp_id}: {str(e)}")

    return Response({
        "success": True,
        "message": f"Attendance marked for {created} employee(s). {skipped} already existed.",
        "data": {"created": created, "skipped": skipped, "errors": errors},
    })


class AttendanceSettingsView(generics.RetrieveUpdateAPIView):
    """GET/PUT api/v1/hr/attendance/settings/"""

    queryset = AttendanceSettings.objects.all()
    serializer_class = AttendanceSettingsSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]

    def get_object(self):
        obj, created = AttendanceSettings.objects.get_or_create(
            defaults={"updated_by": self.request.user}
        )
        return obj


# =============================================================================
# Leave Views
# =============================================================================


class LeaveTypeListCreateView(generics.ListCreateAPIView):
    """GET/POST api/v1/hr/leave-types/"""

    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHRForWrite]
    pagination_class = StandardPagination
    search_fields = ["name", "code"]
    filterset_fields = ["is_active", "is_paid", "is_carry_forward"]


class LeaveTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE api/v1/hr/leave-types/{id}/"""

    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHRForWrite]


class LeaveAllocationListCreateView(generics.ListCreateAPIView):
    """GET/POST api/v1/hr/leave-allocations/"""

    queryset = LeaveAllocation.objects.select_related(
        "employee__user", "leave_type"
    ).all()
    serializer_class = LeaveAllocationSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHRForWrite]
    pagination_class = StandardPagination
    filterset_fields = ["employee", "leave_type", "year"]


class LeaveAllocationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE api/v1/hr/leave-allocations/{id}/"""

    queryset = LeaveAllocation.objects.all()
    serializer_class = LeaveAllocationSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHRForWrite]


class LeaveRequestListCreateView(generics.ListCreateAPIView):
    """GET/POST api/v1/hr/leave-requests/"""

    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = [
        "employee__user__first_name", "employee__user__last_name",
        "reason",
    ]
    filterset_fields = ["status", "leave_type", "employee", "is_emergency"]

    def get_serializer_class(self):
        return LeaveRequestSerializer

    def get_queryset(self):
        return LeaveRequest.objects.select_related(
            "employee__user", "leave_type", "approved_by"
        ).all()

    def perform_create(self, serializer):
        # Auto-assign employee from the logged-in user.
        # The validate method may have already set the employee on attrs,
        # but if not (e.g., for updates or other flows), look it up here.
        if "employee" not in serializer.validated_data:
            from datetime import date
            try:
                employee = Employee.objects.get(
                    user=serializer.context["request"].user
                )
                serializer.save(employee=employee)
            except Employee.DoesNotExist:
                # Auto-create an Employee record for users without one
                employee = Employee.objects.create(
                    user=serializer.context["request"].user,
                    joining_date=date.today(),
                    employment_status=Employee.EmploymentStatus.ACTIVE,
                    employment_type=Employee.EmploymentType.FULL_TIME,
                )
                serializer.save(employee=employee)
        else:
            serializer.save()


class LeaveRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE api/v1/hr/leave-requests/{id}/"""

    queryset = LeaveRequest.objects.select_related(
        "employee__user", "leave_type", "approved_by"
    ).all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, IsHRManager])
def approve_leave_request(request, pk):
    """
    POST api/v1/hr/leave-requests/{id}/approve/
    Approve a pending leave request.
    """
    try:
        leave_request = LeaveRequest.objects.get(pk=pk, status="PENDING")
    except LeaveRequest.DoesNotExist:
        return Response(
            {"success": False, "message": "Leave request not found or already processed."},
            status=status.HTTP_404_NOT_FOUND,
        )

    leave_request.status = "APPROVED"
    leave_request.approved_by = request.user
    leave_request.approval_date = timezone.now()
    leave_request.save()

    # Update leave allocation
    try:
        allocation = LeaveAllocation.objects.get(
            employee=leave_request.employee,
            leave_type=leave_request.leave_type,
            year=leave_request.start_date.year,
        )
        allocation.used_days += leave_request.total_days
        allocation.pending_days -= leave_request.total_days
        allocation.save()
    except LeaveAllocation.DoesNotExist:
        pass

    return Response(
        {"success": True, "message": "Leave request approved.", "data": LeaveRequestSerializer(leave_request).data}
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, IsHRManager])
def reject_leave_request(request, pk):
    """
    POST api/v1/hr/leave-requests/{id}/reject/
    Reject a pending leave request.
    """
    try:
        leave_request = LeaveRequest.objects.get(pk=pk, status="PENDING")
    except LeaveRequest.DoesNotExist:
        return Response(
            {"success": False, "message": "Leave request not found or already processed."},
            status=status.HTTP_404_NOT_FOUND,
        )

    rejection_reason = request.data.get("rejection_reason", "")
    leave_request.status = "REJECTED"
    leave_request.approved_by = request.user
    leave_request.approval_date = timezone.now()
    leave_request.rejection_reason = rejection_reason
    leave_request.save()

    # Update pending days in allocation
    try:
        allocation = LeaveAllocation.objects.get(
            employee=leave_request.employee,
            leave_type=leave_request.leave_type,
            year=leave_request.start_date.year,
        )
        allocation.pending_days -= leave_request.total_days
        allocation.save()
    except LeaveAllocation.DoesNotExist:
        pass

    return Response(
        {"success": True, "message": "Leave request rejected.", "data": LeaveRequestSerializer(leave_request).data}
    )


class HolidayListCreateView(generics.ListCreateAPIView):
    """GET/POST api/v1/hr/holidays/"""

    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHRForWrite]
    pagination_class = StandardPagination
    search_fields = ["name", "description"]
    filterset_fields = ["type", "is_recurring", "is_active"]


class HolidayDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE api/v1/hr/holidays/{id}/"""

    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHRForWrite]


# =============================================================================
# Payroll Views
# =============================================================================


class SalaryStructureListCreateView(generics.ListCreateAPIView):
    """GET/POST api/v1/hr/salary-structures/"""

    queryset = SalaryStructure.objects.select_related("employee__user").all()
    serializer_class = SalaryStructureSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]
    pagination_class = StandardPagination
    filterset_fields = ["employee", "is_active"]


class SalaryStructureDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE api/v1/hr/salary-structures/{id}/"""

    queryset = SalaryStructure.objects.all()
    serializer_class = SalaryStructureSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]


class PayrollListCreateView(generics.ListCreateAPIView):
    """GET/POST api/v1/hr/payroll/"""

    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filterset_fields = ["employee", "month", "year", "status"]

    def get_serializer_class(self):
        return PayrollSerializer

    def get_queryset(self):
        user = self.request.user
        # HR/Admin can see all payroll records; employees see only their own
        if user.user_type in ("ADMIN", "HR", "MANAGER"):
            return Payroll.objects.select_related(
                "employee__user", "salary_structure", "processed_by"
            ).all()
        return Payroll.objects.select_related(
            "employee__user", "salary_structure", "processed_by"
        ).filter(employee__user=user)

    def perform_create(self, serializer):
        # Only ADMIN/HR can create payroll records
        if self.request.user.user_type not in ("ADMIN", "HR"):
            self.permission_denied(self.request)
        serializer.save()


class PayrollDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE api/v1/hr/payroll/{id}/"""

    queryset = Payroll.objects.all()
    serializer_class = PayrollSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, IsAdminOrHR])
def process_payroll(request):
    """
    POST api/v1/hr/payroll/process/
    Process payroll for all active employees for a given month/year.
    """
    month = request.data.get("month", timezone.now().month)
    year = request.data.get("year", timezone.now().year)

    active_employees = Employee.objects.filter(
        employment_status__in=["ACTIVE", "PROBATION"]
    )

    processed = 0
    errors = []

    for employee in active_employees:
        # Check if payroll already exists
        if Payroll.objects.filter(employee=employee, month=month, year=year).exists():
            continue

        # Get active salary structure
        salary_structure = SalaryStructure.objects.filter(
            employee=employee, is_active=True
        ).first()

        if not salary_structure:
            errors.append(f"No salary structure for {employee.full_name}")
            continue

        # Create payroll entry
        payroll = Payroll(
            employee=employee,
            salary_structure=salary_structure,
            month=month,
            year=year,
            status="PROCESSED",
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
            processed_by=request.user,
            processed_at=timezone.now(),
        )
        payroll.save()
        processed += 1

    return Response(
        {
            "success": True,
            "message": f"Payroll processed for {processed} employees.",
            "data": {"processed": processed, "errors": errors},
        }
    )


# =============================================================================
# Performance Views
# =============================================================================


class PerformanceReviewListCreateView(generics.ListCreateAPIView):
    """GET/POST api/v1/hr/performance-reviews/"""

    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]
    pagination_class = StandardPagination
    filterset_fields = ["employee", "reviewer", "status"]

    def get_serializer_class(self):
        return PerformanceReviewSerializer

    def get_queryset(self):
        return PerformanceReview.objects.select_related(
            "employee__user", "reviewer__user"
        ).all()


class PerformanceReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE api/v1/hr/performance-reviews/{id}/"""

    queryset = PerformanceReview.objects.all()
    serializer_class = PerformanceReviewSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]


class GoalListCreateView(generics.ListCreateAPIView):
    """GET/POST api/v1/hr/goals/"""

    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]
    pagination_class = StandardPagination
    search_fields = ["title", "description"]
    filterset_fields = ["employee", "status", "goal_type"]

    def get_serializer_class(self):
        return GoalSerializer

    def get_queryset(self):
        return Goal.objects.select_related("employee__user").all()


class GoalDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE api/v1/hr/goals/{id}/"""

    queryset = Goal.objects.all()
    serializer_class = GoalSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]


# =============================================================================
# Notification Views
# =============================================================================


class NotificationListView(generics.ListAPIView):
    """GET api/v1/hr/notifications/"""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related("recipient").all()


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def mark_notification_read(request, pk):
    """POST api/v1/hr/notifications/{id}/read/"""
    try:
        notification = Notification.objects.get(pk=pk, recipient=request.user)
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        return Response({"success": True, "message": "Notification marked as read."})
    except Notification.DoesNotExist:
        return Response(
            {"success": False, "message": "Notification not found."},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def mark_all_notifications_read(request):
    """POST api/v1/hr/notifications/read-all/"""
    count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).update(is_read=True, read_at=timezone.now())
    return Response(
        {"success": True, "message": f"{count} notifications marked as read."}
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def unread_notification_count(request):
    """GET api/v1/hr/notifications/unread-count/"""
    count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()
    return Response({"success": True, "data": {"unread_count": count}})


# =============================================================================
# Reports
# =============================================================================


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, IsAdminOrHR])
def attendance_report(request):
    """
    GET api/v1/hr/reports/attendance/
    Generate attendance report for a date range.
    """
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")
    department_id = request.query_params.get("department")

    if not start_date or not end_date:
        return Response(
            {"success": False, "message": "start_date and end_date are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    filters = Q(date__gte=start_date, date__lte=end_date)
    if department_id:
        filters &= Q(employee__department_id=department_id)

    attendance = Attendance.objects.filter(filters).select_related(
        "employee__user", "employee__department"
    )

    summary = attendance.aggregate(
        total_records=Count("id"),
        total_present=Count("id", filter=Q(status="PRESENT")),
        total_absent=Count("id", filter=Q(status="ABSENT")),
        total_late=Count("id", filter=Q(status="LATE")),
        total_half_day=Count("id", filter=Q(status="HALF_DAY")),
        total_wfh=Count("id", filter=Q(status="WFH")),
        total_overtime_hours=Sum("overtime_hours"),
        avg_work_hours=Avg("work_hours"),
    )

    return Response(
        {
            "success": True,
            "data": {
                "summary": summary,
                "records": AttendanceSerializer(attendance[:100], many=True).data,
            },
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, IsAdminOrHR])
def payroll_report(request):
    """
    GET api/v1/hr/reports/payroll/
    Generate payroll report for a given month/year.
    """
    month = request.query_params.get("month", timezone.now().month)
    year = request.query_params.get("year", timezone.now().year)
    department_id = request.query_params.get("department")

    filters = Q(month=month, year=year)
    if department_id:
        filters &= Q(employee__department_id=department_id)

    payrolls = Payroll.objects.filter(filters).select_related(
        "employee__user", "employee__department"
    )

    summary = payrolls.aggregate(
        total_employees=Count("id", distinct=True),
        total_earnings=Sum("total_earnings"),
        total_deductions=Sum("total_deductions"),
        total_net_pay=Sum("net_pay"),
        avg_net_pay=Avg("net_pay"),
        total_bonus=Sum("bonus"),
        total_overtime=Sum("overtime_pay"),
        total_tax=Sum("income_tax"),
        total_pf=Sum("provident_fund"),
    )

    return Response(
        {
            "success": True,
            "data": {
                "month": month,
                "year": year,
                "summary": summary,
                "records": PayrollSerializer(payrolls[:100], many=True).data,
            },
        }
    )


# =============================================================================
# Automation Rule Views
# =============================================================================


class AutomationRuleListCreateView(generics.ListCreateAPIView):
    """List all automation rules or create a new one."""

    queryset = AutomationRule.objects.all()
    serializer_class = AutomationRuleSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]

    def get_queryset(self):
        """Optionally filter by trigger_event query param."""
        qs = super().get_queryset()
        trigger = self.request.query_params.get("trigger_event")
        if trigger:
            qs = qs.filter(trigger_event=trigger)
        return qs


class AutomationRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an automation rule."""

    queryset = AutomationRule.objects.all()
    serializer_class = AutomationRuleSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]


class SystemSettingsView(generics.RetrieveUpdateAPIView):
    """
    GET/PUT api/v1/hr/settings/

    Retrieve or update system-wide settings (AI provider, notifications, etc.).
    Only accessible by ADMIN and HR users.

    After updating settings, the AI client singleton is reloaded so that
    the new provider configuration (API key, base URL, model) takes effect
    immediately without requiring a server restart.
    """

    serializer_class = SystemSettingsSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]

    def get_object(self):
        return SystemSettings.get_settings()

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
        # Reload the AI client singleton so new provider config takes effect immediately
        try:
            from config.apps.chatbot.services import get_deepseek_client
            client = get_deepseek_client()
            client.reload()
        except Exception:
            pass
