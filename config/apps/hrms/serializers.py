"""
Serializers for the HRMS app.

Provides serializers for all HRMS models with proper validation,
nested representations, and computed fields.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

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

User = get_user_model()


# =============================================================================
# Department Serializers
# =============================================================================


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department model."""

    head_name = serializers.SerializerMethodField()
    employee_count = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_head_name(self, obj: Department) -> str | None:
        if obj.head:
            return obj.head.get_full_name()
        return None

    def get_employee_count(self, obj: Department) -> int:
        return obj.employees.filter(
            employment_status__in=["ACTIVE", "PROBATION"]
        ).count()

    def get_children_count(self, obj: Department) -> int:
        return obj.children.count()


class DepartmentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for department list views."""

    head_name = serializers.SerializerMethodField()
    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            "id", "name", "code", "head_name",
            "employee_count", "is_active",
        ]

    def get_head_name(self, obj: Department) -> str | None:
        if obj.head:
            return obj.head.get_full_name()
        return None

    def get_employee_count(self, obj: Department) -> int:
        return obj.employees.filter(
            employment_status__in=["ACTIVE", "PROBATION"]
        ).count()


# =============================================================================
# Designation Serializers
# =============================================================================


class DesignationSerializer(serializers.ModelSerializer):
    """Serializer for Designation model."""

    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Designation
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


# =============================================================================
# Employee Serializers
# =============================================================================


class EmployeeSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for Employee model."""

    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    employee_id = serializers.CharField(source="user.employee_id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone_number", read_only=True)
    department_name = serializers.CharField(
        source="department.name", read_only=True
    )
    designation_title = serializers.CharField(
        source="designation.title", read_only=True
    )
    reporting_to_name = serializers.SerializerMethodField()
    years_of_service = serializers.FloatField(read_only=True)

    # User creation fields (write-only, for creating employees with user accounts)
    first_name = serializers.CharField(write_only=True, required=False)
    last_name = serializers.CharField(write_only=True, required=False)
    username = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})

    # The user FK is handled in create() - not required for input validation
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        write_only=True,
    )

    class Meta:
        model = Employee
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_reporting_to_name(self, obj: Employee) -> str | None:
        if obj.reporting_to:
            return obj.reporting_to.full_name
        return None

    def create(self, validated_data: dict) -> Employee:
        """Create a User account and Employee profile together."""
        # Extract user-related fields
        first_name = validated_data.pop("first_name", "")
        last_name = validated_data.pop("last_name", "")
        username = validated_data.pop("username", None)
        password = validated_data.pop("password", None)
        email = validated_data.pop("email", "")
        user_type = validated_data.pop("user_type", "EMPLOYEE")

        # If no username provided, generate one from email or first/last name
        if not username:
            username = f"{first_name.lower()}.{last_name.lower()}".replace(" ", ".")
            # Ensure uniqueness
            from django.contrib.auth import get_user_model
            User = get_user_model()
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

        # Create the User account
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            username=username,
            password=password or "changeme123",
            email=email,
            first_name=first_name,
            last_name=last_name,
            user_type=user_type,
        )

        # Link the user to the employee
        validated_data["user"] = user
        return super().create(validated_data)

    def update(self, instance: Employee, validated_data: dict) -> Employee:
        """Update an Employee profile, including related User fields."""
        # Extract user-related fields that can be updated
        first_name = validated_data.pop("first_name", None)
        last_name = validated_data.pop("last_name", None)
        email = validated_data.pop("email", None)
        user_type = validated_data.pop("user_type", None)

        # Update the related User record if any user fields provided
        if any([first_name, last_name, email, user_type]):
            user = instance.user
            if first_name is not None:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name
            if email is not None:
                user.email = email
            if user_type is not None:
                user.user_type = user_type
            user.save()

        # Update the Employee fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance


class EmployeeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for employee list views."""

    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    employee_id = serializers.CharField(source="user.employee_id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    profile_image = serializers.ImageField(source="user.profile_image", read_only=True)
    department_name = serializers.CharField(
        source="department.name", read_only=True
    )
    designation_title = serializers.CharField(
        source="designation.title", read_only=True
    )
    user_detail = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "id", "full_name", "employee_id", "email", "phone_number",
            "profile_image", "department_name", "designation_title",
            "employment_status", "employment_type",
            "joining_date", "user_detail",
        ]

    def get_user_detail(self, obj: Employee) -> dict:
        """Return user details for frontend compatibility."""
        user = obj.user
        return {
            "id": str(user.id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone_number": user.phone_number or "",
            "profile_image": user.profile_image.url if user.profile_image else None,
            "employee_id": user.employee_id,
            "user_type": user.user_type,
            "username": user.username,
        }


# =============================================================================
# Attendance Serializers
# =============================================================================


class AttendanceSerializer(serializers.ModelSerializer):
    """Serializer for Attendance model."""

    employee_name = serializers.CharField(
        source="employee.full_name", read_only=True
    )
    employee_id = serializers.CharField(
        source="employee.employee_id", read_only=True
    )

    class Meta:
        model = Attendance
        fields = "__all__"
        read_only_fields = ["id", "work_hours", "created_at", "updated_at"]


class AttendanceSettingsSerializer(serializers.ModelSerializer):
    """Serializer for AttendanceSettings model."""

    class Meta:
        model = AttendanceSettings
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


# =============================================================================
# Leave Serializers
# =============================================================================


class LeaveTypeSerializer(serializers.ModelSerializer):
    """Serializer for LeaveType model."""

    class Meta:
        model = LeaveType
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class LeaveAllocationSerializer(serializers.ModelSerializer):
    """Serializer for LeaveAllocation model."""

    leave_type_name = serializers.CharField(
        source="leave_type.name", read_only=True
    )
    remaining_days = serializers.DecimalField(
        max_digits=5, decimal_places=1, read_only=True
    )

    class Meta:
        model = LeaveAllocation
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    """Serializer for LeaveRequest model."""

    employee_name = serializers.CharField(
        source="employee.full_name", read_only=True
    )
    employee_id = serializers.CharField(
        source="employee.employee_id", read_only=True
    )
    leave_type_name = serializers.CharField(
        source="leave_type.name", read_only=True
    )
    approved_by_name = serializers.SerializerMethodField()
    # half_day: accept boolean or string; validated in validate_half_day
    half_day = serializers.JSONField(required=False)
    # total_days and employee are computed in validate(), not sent by frontend
    total_days = serializers.IntegerField(required=False)
    employee = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = [
            "id", "status", "approved_by", "approval_date",
            "created_at", "updated_at",
        ]

    def get_approved_by_name(self, obj: LeaveRequest) -> str | None:
        if obj.approved_by:
            return obj.approved_by.get_full_name()
        return None

    def validate_half_day(self, value):
        """Normalize half_day from boolean/string to valid model choice."""
        valid_choices = {c[0] for c in LeaveRequest.LeaveHalf.choices}
        if isinstance(value, str):
            upper_val = value.upper()
            if upper_val in valid_choices:
                return upper_val
            if value.lower() in {"true", "1", "yes", "half", "half_day", "half-day"}:
                return "FIRST_HALF"
        elif isinstance(value, bool):
            if value:
                return "FIRST_HALF"
        # Default to FULL for False/None/empty
        return "FULL"

    def validate(self, attrs: dict) -> dict:
        """Validate leave request dates and balance."""
        if attrs.get("start_date") and attrs.get("end_date"):
            if attrs["start_date"] > attrs["end_date"]:
                raise serializers.ValidationError(
                    "End date must be after start date."
                )

            # Calculate total days
            delta = attrs["end_date"] - attrs["start_date"]
            attrs["total_days"] = delta.days + 1

            # Check leave balance if this is a create operation
            # Note: employee is NOT in the request data from the frontend;
            # it's only set in perform_create. So we look it up from the
            # request user context here.
            if not self.instance and attrs.get("leave_type"):
                from decimal import Decimal
                from datetime import date
                # Look up employee from the logged-in user (same as perform_create)
                request = self.context.get("request")
                if request and request.user.is_authenticated:
                    try:
                        employee = Employee.objects.get(user=request.user)
                    except Employee.DoesNotExist:
                        # Auto-create an Employee record for users without one
                        employee = Employee.objects.create(
                            user=request.user,
                            joining_date=date.today(),
                            employment_status=Employee.EmploymentStatus.ACTIVE,
                            employment_type=Employee.EmploymentType.FULL_TIME,
                        )
                    attrs["employee"] = employee  # Set it so perform_create can use it

                if attrs.get("employee"):
                    year = attrs["start_date"].year
                    try:
                        allocation = LeaveAllocation.objects.get(
                            employee=attrs["employee"],
                            leave_type=attrs["leave_type"],
                            year=year,
                        )
                        if allocation.remaining_days < Decimal(str(attrs["total_days"])):
                            raise serializers.ValidationError(
                                f"Insufficient leave balance. "
                                f"Available: {allocation.remaining_days} days."
                            )
                    except LeaveAllocation.DoesNotExist:
                        # Auto-create a default leave allocation if none exists
                        try:
                            LeaveAllocation.objects.create(
                                employee=attrs["employee"],
                                leave_type=attrs["leave_type"],
                                year=year,
                                total_days=attrs["leave_type"].days_per_year,
                            )
                        except Exception:
                            raise serializers.ValidationError(
                                "No leave allocation found for this leave type and year. "
                                "Could not auto-create one."
                            )

        return attrs


class HolidaySerializer(serializers.ModelSerializer):
    """Serializer for Holiday model."""

    class Meta:
        model = Holiday
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


# =============================================================================
# Payroll Serializers
# =============================================================================


class SalaryStructureSerializer(serializers.ModelSerializer):
    """Serializer for SalaryStructure model."""

    employee_name = serializers.CharField(
        source="employee.full_name", read_only=True
    )
    total_earnings = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    total_deductions = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    net_salary = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    ctc = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = SalaryStructure
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class PayrollSerializer(serializers.ModelSerializer):
    """Serializer for Payroll model."""

    employee_name = serializers.CharField(
        source="employee.full_name", read_only=True
    )
    employee_id = serializers.CharField(
        source="employee.employee_id", read_only=True
    )
    month_name = serializers.SerializerMethodField()

    class Meta:
        model = Payroll
        fields = "__all__"
        read_only_fields = [
            "id", "total_earnings", "total_deductions", "net_pay",
            "processed_at", "created_at", "updated_at",
        ]

    def get_month_name(self, obj: Payroll) -> str:
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        return month_names[obj.month - 1]


# =============================================================================
# Performance Serializers
# =============================================================================


class PerformanceReviewSerializer(serializers.ModelSerializer):
    """Serializer for PerformanceReview model."""

    employee_name = serializers.CharField(
        source="employee.full_name", read_only=True
    )
    reviewer_name = serializers.CharField(
        source="reviewer.full_name", read_only=True
    )

    class Meta:
        model = PerformanceReview
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class GoalSerializer(serializers.ModelSerializer):
    """Serializer for Goal model."""

    employee_name = serializers.CharField(
        source="employee.full_name", read_only=True
    )

    class Meta:
        model = Goal
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


# =============================================================================
# Notification Serializers
# =============================================================================


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""

    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class AutomationRuleSerializer(serializers.ModelSerializer):
    """Serializer for AutomationRule model."""

    trigger_event_display = serializers.CharField(
        source="get_trigger_event_display", read_only=True
    )
    action_type_display = serializers.CharField(
        source="get_action_type_display", read_only=True
    )

    class Meta:
        model = AutomationRule
        fields = [
            "id",
            "name",
            "description",
            "trigger_event",
            "trigger_event_display",
            "condition_expression",
            "action_type",
            "action_type_display",
            "action_config",
            "is_active",
            "priority",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SystemSettingsSerializer(serializers.ModelSerializer):
    """Serializer for SystemSettings model."""

    class Meta:
        model = SystemSettings
        fields = [
            "ai_provider",
            "deepseek_api_key",
            "deepseek_base_url",
            "deepseek_model",
            "openai_api_key",
            "openai_base_url",
            "openai_model",
            "embedding_model",
            "max_tokens",
            "temperature",
            "notify_leave_requests",
            "notify_payroll_updates",
            "notify_attendance_anomalies",
            "notify_performance_reviews",
            "notify_new_employees",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]
