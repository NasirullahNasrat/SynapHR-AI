"""
AI Services for the Chatbot app.

Provides DeepSeek API integration, function/tool calling for HRMS operations,
RAG (Retrieval-Augmented Generation), embedding generation, and semantic search.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import numpy as np
from django.conf import settings
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from openai import OpenAI

logger = logging.getLogger(__name__)


# =============================================================================
# HRMS Tool Functions - These are the functions the AI can call to interact
# with the HRMS system data. Each function is registered with a name,
# description, and parameter schema for the AI to understand.
# =============================================================================

class HRMSTools:
    """
    Collection of tools/functions that the AI can call to interact with
    the HRMS system. Each method represents a capability.
    """

    def __init__(self, user):
        self.user = user
        # Lazy imports to avoid circular dependencies
        from config.apps.hrms.models import (
            Employee, Department, Designation, Attendance, LeaveRequest,
            LeaveType, LeaveAllocation, Holiday, Payroll, SalaryStructure,
            PerformanceReview, Goal, Notification,
        )
        from config.apps.accounts.models import User
        self.Employee = Employee
        self.Department = Department
        self.Designation = Designation
        self.Attendance = Attendance
        self.LeaveRequest = LeaveRequest
        self.LeaveType = LeaveType
        self.LeaveAllocation = LeaveAllocation
        self.Holiday = Holiday
        self.Payroll = Payroll
        self.SalaryStructure = SalaryStructure
        self.PerformanceReview = PerformanceReview
        self.Goal = Goal
        self.Notification = Notification
        self.User = User

    def _is_hr_or_admin(self) -> bool:
        return self.user.user_type in ('HR', 'ADMIN')

    # ---- Employee Tools ----

    def get_employee_count(self) -> str:
        """Get total number of employees."""
        count = self.Employee.objects.count()
        return json.dumps({"total_employees": count})

    def get_active_employee_count(self) -> str:
        """Get number of active employees."""
        count = self.Employee.objects.filter(employment_status='ACTIVE').count()
        return json.dumps({"active_employees": count})

    def list_employees(self, department_id: str = "", status: str = "", search: str = "") -> str:
        """List employees with optional filters.
        
        Args:
            department_id: Filter by department UUID (optional)
            status: Filter by employment status (ACTIVE, INACTIVE, ON_LEAVE, TERMINATED, RESIGNED) (optional)
            search: Search by name or employee ID (optional)
        """
        qs = self.Employee.objects.select_related('user', 'department', 'designation').all()
        if department_id:
            qs = qs.filter(department_id=department_id)
        if status:
            qs = qs.filter(employment_status=status)
        if search:
            qs = qs.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(employee_id__icontains=search)
            )
        employees = []
        for emp in qs[:20]:
            employees.append({
                "id": str(emp.id),
                "employee_id": emp.employee_id,
                "name": f"{emp.user.first_name} {emp.user.last_name}",
                "email": emp.user.email,
                "department": emp.department.name if emp.department else "",
                "designation": emp.designation.title if emp.designation else "",
                "status": emp.employment_status,
                "joining_date": str(emp.joining_date) if emp.joining_date else "",
            })
        return json.dumps({"employees": employees, "total": len(employees)})

    def get_employee_details(self, employee_id: str) -> str:
        """Get detailed information about a specific employee.
        
        Args:
            employee_id: The employee UUID or employee_id string (e.g., EMP-001)
        """
        emp = (
            self.Employee.objects.select_related('user', 'department', 'designation', 'reporting_to')
            .filter(Q(id=employee_id) | Q(employee_id=employee_id))
            .first()
        )
        if not emp:
            return json.dumps({"error": "Employee not found"})
        return json.dumps({
            "id": str(emp.id),
            "employee_id": emp.employee_id,
            "name": f"{emp.user.first_name} {emp.user.last_name}",
            "email": emp.user.email,
            "phone": emp.user.phone_number or "",
            "department": emp.department.name if emp.department else "",
            "designation": emp.designation.title if emp.designation else "",
            "status": emp.employment_status,
            "type": emp.employment_type,
            "joining_date": str(emp.joining_date) if emp.joining_date else "",
            "reporting_to": f"{emp.reporting_to.user.first_name} {emp.reporting_to.user.last_name}" if emp.reporting_to else "",
            "emergency_contact": emp.emergency_contact or "",
            "address": emp.address or "",
        })

    def create_employee(self, first_name: str, last_name: str, email: str,
                        department_id: str, designation_id: str,
                        employee_id: str = "", password: str = "changeme123",
                        employment_status: str = "ACTIVE",
                        employment_type: str = "FULL_TIME",
                        joining_date: str = "") -> str:
        """Create a new employee with a user account.
        
        Args:
            first_name: Employee's first name
            last_name: Employee's last name
            email: Employee's email address
            department_id: Department UUID
            designation_id: Designation UUID
            employee_id: Custom employee ID (auto-generated if empty)
            password: Initial password (default: changeme123)
            employment_status: Employment status (ACTIVE, INACTIVE, ON_LEAVE, TERMINATED, RESIGNED)
            employment_type: Employment type (FULL_TIME, PART_TIME, CONTRACT, INTERN, PROBATION)
            joining_date: Joining date (YYYY-MM-DD, defaults to today)
        """
        if not self._is_hr_or_admin():
            return json.dumps({"error": "Permission denied. Only HR and Admin can create employees."})
        
        from config.apps.accounts.serializers import UserSerializer
        from config.apps.hrms.serializers import EmployeeSerializer
        
        username = employee_id.lower() if employee_id else email.split('@')[0]
        if not joining_date:
            joining_date = str(timezone.localdate())
        
        user_data = {
            'username': username,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'password': password,
            # UserSerializer expects confirm_password, not password2
            'confirm_password': password,
            'user_type': 'EMPLOYEE',
        }
        
        user_serializer = UserSerializer(data=user_data)
        if not user_serializer.is_valid():
            return json.dumps({"error": f"User validation failed: {user_serializer.errors}"})
        
        user = user_serializer.save()
        
        emp_data = {
            'user': str(user.id),
            'employee_id': employee_id or f"EMP-{str(user.id)[:8].upper()}",
            'department': department_id,
            'designation': designation_id,
            'employment_status': employment_status,
            'employment_type': employment_type,
            'joining_date': joining_date,
        }
        
        emp_serializer = EmployeeSerializer(data=emp_data)
        if not emp_serializer.is_valid():
            user.delete()  # Rollback user creation
            return json.dumps({"error": f"Employee validation failed: {emp_serializer.errors}"})
        
        emp = emp_serializer.save()
        return json.dumps({
            "success": True,
            "employee_id": emp.employee_id,
            "name": f"{first_name} {last_name}",
            "id": str(emp.id),
        })

    # ---- Designation Tools ----

    def list_designations(self, department_id: str = "") -> str:
        """List all designations, optionally filtered by department.

        Args:
            department_id: Filter by department UUID (optional)
        """
        qs = self.Designation.objects.select_related('department').all()
        if department_id:
            qs = qs.filter(department_id=department_id)
        result = []
        for d in qs:
            result.append({
                "id": str(d.id),
                "title": d.title,
                "department": d.department.name if d.department else "",
                "description": d.description or "",
                "is_active": d.is_active,
            })
        return json.dumps({"designations": result, "total": len(result)})

    # ---- Department Tools ----

    def list_departments(self) -> str:
        """List all departments with employee counts."""
        depts = self.Department.objects.annotate(
            emp_count=Count('employees')
        ).all()
        result = []
        for d in depts:
            result.append({
                "id": str(d.id),
                "name": d.name,
                "code": d.code,
                "description": d.description or "",
                "employee_count": d.emp_count,
                "is_active": d.is_active,
            })
        return json.dumps({"departments": result, "total": len(result)})

    def create_department(self, name: str, code: str, description: str = "") -> str:
        """Create a new department.
        
        Args:
            name: Department name
            code: Department code (e.g., ENG)
            description: Department description (optional)
        """
        if not self._is_hr_or_admin():
            return json.dumps({"error": "Permission denied. Only HR and Admin can create departments."})
        
        dept = self.Department.objects.create(name=name, code=code.upper(), description=description)
        return json.dumps({"success": True, "id": str(dept.id), "name": dept.name, "code": dept.code})

    def update_department(self, department_id: str, name: str = "", code: str = "", description: str = "") -> str:
        """Update an existing department.
        
        Args:
            department_id: Department UUID
            name: New department name (optional)
            code: New department code (optional)
            description: New description (optional)
        """
        if not self._is_hr_or_admin():
            return json.dumps({"error": "Permission denied."})
        
        try:
            dept = self.Department.objects.get(id=department_id)
        except self.Department.DoesNotExist:
            return json.dumps({"error": "Department not found"})
        
        if name:
            dept.name = name
        if code:
            dept.code = code.upper()
        if description:
            dept.description = description
        dept.save()
        return json.dumps({"success": True, "id": str(dept.id), "name": dept.name})

    def delete_department(self, department_id: str) -> str:
        """Delete a department.
        
        Args:
            department_id: Department UUID
        """
        if not self._is_hr_or_admin():
            return json.dumps({"error": "Permission denied."})
        try:
            dept = self.Department.objects.get(id=department_id)
            dept.delete()
            return json.dumps({"success": True, "message": "Department deleted"})
        except self.Department.DoesNotExist:
            return json.dumps({"error": "Department not found"})

    # ---- Attendance Tools ----

    def get_attendance_summary(self, date_str: str = "") -> str:
        """Get attendance summary for a specific date or today.
        
        Args:
            date_str: Date in YYYY-MM-DD format (defaults to today)
        """
        if not date_str:
            date_str = str(date.today())
        
        records = self.Attendance.objects.filter(date=date_str)
        total = records.count()
        summary = {
            "date": date_str,
            "total_records": total,
            "present": records.filter(status='PRESENT').count(),
            "absent": records.filter(status='ABSENT').count(),
            "late": records.filter(status='LATE').count(),
            "half_day": records.filter(status='HALF_DAY').count(),
            "on_leave": records.filter(status='ON_LEAVE').count(),
        }
        return json.dumps(summary)

    def mark_attendance(self, employee_id: str, date_str: str, status: str,
                        check_in: str = "09:00", check_out: str = "18:00",
                        notes: str = "") -> str:
        """Mark attendance for an employee on a specific date.
        
        Args:
            employee_id: Employee UUID or employee_id string
            date_str: Date in YYYY-MM-DD format
            status: Attendance status (PRESENT, ABSENT, LATE, HALF_DAY, ON_LEAVE)
            check_in: Check-in time (HH:MM, optional)
            check_out: Check-out time (HH:MM, optional)
            notes: Optional notes
        """
        if not self._is_hr_or_admin():
            return json.dumps({"error": "Permission denied. Only HR and Admin can mark attendance."})
        
        emp = self.Employee.objects.filter(
            Q(id=employee_id) | Q(employee_id=employee_id)
        ).first()
        if not emp:
            return json.dumps({"error": "Employee not found"})
        
        att, created = self.Attendance.objects.update_or_create(
            employee=emp,
            date=date_str,
            defaults={
                'status': status,
                'check_in': check_in,
                'check_out': check_out,
                'notes': notes,
            }
        )
        return json.dumps({
            "success": True,
            "action": "created" if created else "updated",
            "employee": f"{emp.user.first_name} {emp.user.last_name}",
            "date": date_str,
            "status": status,
        })

    def mark_attendance_bulk(self, employee_ids: list, date_str: str, status: str,
                              check_in: str = "09:00", check_out: str = "18:00") -> str:
        """Mark attendance for multiple employees on a specific date.
        
        Args:
            employee_ids: List of employee UUIDs or employee_id strings
            date_str: Date in YYYY-MM-DD format
            status: Attendance status (PRESENT, ABSENT, LATE, HALF_DAY, ON_LEAVE)
            check_in: Check-in time (HH:MM, optional)
            check_out: Check-out time (HH:MM, optional)
        """
        if not self._is_hr_or_admin():
            return json.dumps({"error": "Permission denied."})
        
        results = []
        for eid in employee_ids:
            emp = self.Employee.objects.filter(Q(id=eid) | Q(employee_id=eid)).first()
            if emp:
                self.Attendance.objects.update_or_create(
                    employee=emp,
                    date=date_str,
                    defaults={'status': status, 'check_in': check_in, 'check_out': check_out}
                )
                results.append(f"{emp.employee_id} ({emp.user.first_name} {emp.user.last_name})")
        
        return json.dumps({
            "success": True,
            "message": f"Marked {len(results)} employees as {status} on {date_str}",
            "employees": results,
        })

    def mark_attendance_date_range(self, employee_ids: list, start_date: str, end_date: str, status: str) -> str:
        """Mark attendance for employees across a date range.
        
        Args:
            employee_ids: List of employee UUIDs or employee_id strings
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            status: Attendance status (PRESENT, ABSENT, LATE, HALF_DAY, ON_LEAVE)
        """
        if not self._is_hr_or_admin():
            return json.dumps({"error": "Permission denied."})
        
        from datetime import date as date_type
        start = date_type.fromisoformat(start_date)
        end = date_type.fromisoformat(end_date)
        
        total_marked = 0
        for eid in employee_ids:
            emp = self.Employee.objects.filter(Q(id=eid) | Q(employee_id=eid)).first()
            if not emp:
                continue
            current = start
            while current <= end:
                # Skip weekends
                if current.weekday() < 5:
                    self.Attendance.objects.update_or_create(
                        employee=emp,
                        date=str(current),
                        defaults={'status': status}
                    )
                    total_marked += 1
                current += timedelta(days=1)
        
        return json.dumps({
            "success": True,
            "message": f"Marked {total_marked} attendance records as {status} from {start_date} to {end_date}",
        })

    # ---- Leave Tools ----

    def list_leave_types(self) -> str:
        """List all available leave types."""
        types = self.LeaveType.objects.all()
        result = [{
            "id": str(lt.id),
            "name": lt.name,
            "code": lt.code,
            "days_per_year": lt.days_per_year,
            "is_active": lt.is_active,
            "is_paid": lt.is_paid,
            # Older code referenced `requires_documentation`; keep the flag for compatibility.
            "requires_documentation": getattr(lt, "requires_documentation", False),
        } for lt in types]
        return json.dumps({"leave_types": result, "total": len(result)})

    def get_leave_balance(self, employee_id: str = "") -> str:
        """Get leave balance for an employee or all employees.
        
        Args:
            employee_id: Employee UUID or employee_id (optional, returns all if empty)
        """
        allocations = self.LeaveAllocation.objects.select_related('employee__user', 'leave_type').all()
        if employee_id:
            allocations = allocations.filter(
                Q(employee__id=employee_id) | Q(employee__employee_id=employee_id)
            )
        
        result = {}
        for alloc in allocations:
            key = f"{alloc.employee.employee_id} ({alloc.employee.user.first_name} {alloc.employee.user.last_name})"
            if key not in result:
                result[key] = []
            result[key].append({
                "leave_type": alloc.leave_type.name,
                "total_days": float(alloc.total_days),
                "used_days": float(alloc.used_days),
                "remaining": float(alloc.remaining_days),
            })
        return json.dumps({"leave_balances": result})

    def list_leave_requests(self, status: str = "", employee_id: str = "") -> str:
        """List leave requests with optional filters.
        
        Args:
            status: Filter by status (PENDING, APPROVED, REJECTED, CANCELLED) (optional)
            employee_id: Filter by employee (optional)
        """
        qs = self.LeaveRequest.objects.select_related('employee__user', 'leave_type', 'approved_by').all()
        if status:
            qs = qs.filter(status=status)
        if employee_id:
            qs = qs.filter(Q(employee__id=employee_id) | Q(employee__employee_id=employee_id))
        
        result = []
        for lr in qs[:30]:
            result.append({
                "id": str(lr.id),
                "employee": f"{lr.employee.user.first_name} {lr.employee.user.last_name}",
                "employee_id": lr.employee.employee_id,
                "leave_type": lr.leave_type.name,
                "start_date": str(lr.start_date),
                "end_date": str(lr.end_date),
                "total_days": float(lr.total_days),
                "status": lr.status,
                "reason": lr.reason or "",
                "half_day": lr.half_day,
                "is_emergency": lr.is_emergency,
            })
        return json.dumps({"leave_requests": result, "total": len(result)})

    def create_leave_request(self, employee_id: str, leave_type_id: str,
                              start_date: str, end_date: str, reason: str = "",
                              half_day: bool | str = False, is_emergency: bool = False) -> str:
        """Create a leave request.

        Args:
            employee_id: Employee UUID or employee_id string
            leave_type_id: Leave type UUID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            reason: Reason for leave (optional)
            half_day: Whether it's a half day leave (bool) or explicit choice (FULL, FIRST_HALF, SECOND_HALF)
            is_emergency: Whether it's an emergency leave (default: false)
        """
        emp = self.Employee.objects.filter(
            Q(id=employee_id) | Q(employee_id=employee_id)
        ).first()
        if not emp:
            return json.dumps({"error": "Employee not found"})
        
        lt = self.LeaveType.objects.filter(id=leave_type_id).first()
        if not lt:
            return json.dumps({"error": "Leave type not found"})

        # Normalize half_day to the model's choices
        half_day_normalized = "FULL"
        if isinstance(half_day, str):
            hd_upper = half_day.upper()
            if hd_upper in {"FULL", "FIRST_HALF", "SECOND_HALF"}:
                half_day_normalized = hd_upper
            elif half_day.lower() in {"true", "1", "yes", "half", "half_day", "half-day"}:
                half_day_normalized = "FIRST_HALF"
        elif half_day:
            half_day_normalized = "FIRST_HALF"
        
        lr = self.LeaveRequest.objects.create(
            employee=emp,
            leave_type=lt,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            half_day=half_day_normalized,
            is_emergency=is_emergency,
            status='PENDING',
        )
        return json.dumps({
            "success": True,
            "message": f"Leave request created for {emp.user.first_name} {emp.user.last_name}",
            "id": str(lr.id),
            "status": "PENDING",
        })

    def approve_leave_request(self, leave_request_id: str) -> str:
        """Approve a pending leave request.
        
        Args:
            leave_request_id: Leave request UUID
        """
        if not self._is_hr_or_admin():
            return json.dumps({"error": "Permission denied."})
        try:
            lr = self.LeaveRequest.objects.get(id=leave_request_id, status='PENDING')
            lr.status = 'APPROVED'
            lr.approved_by = self.user
            lr.approved_at = timezone.now()
            lr.save()
            return json.dumps({
                "success": True,
                "message": f"Leave request approved for {lr.employee.user.first_name} {lr.employee.user.last_name}"
            })
        except self.LeaveRequest.DoesNotExist:
            return json.dumps({"error": "Leave request not found or already processed"})

    def approve_leave_by_employee_name(self, first_name: str = "", last_name: str = "") -> str:
        """Approve a pending leave request by finding the employee by name.
        
        Looks up the employee by first and/or last name, finds their most recent
        pending leave request, approves it, and sends a notification to both
        the employee and their reporting manager.
        
        Args:
            first_name: Employee's first name (e.g., "John")
            last_name: Employee's last name (e.g., "Doe")
        """
        if not self._is_hr_or_admin():
            return json.dumps({"error": "Permission denied. Only HR and Admin can approve leave requests."})
        
        if not first_name and not last_name:
            return json.dumps({"error": "Please provide the employee's name. Example: 'Approve John Doe's leave request'"})
        
        try:
            # Build query to find employee by name
            emp_query = Q()
            if first_name:
                emp_query &= Q(user__first_name__iexact=first_name)
            if last_name:
                emp_query &= Q(user__last_name__iexact=last_name)
            
            # If only one name provided, search both first and last name
            if first_name and not last_name:
                emp_query = Q(user__first_name__iexact=first_name) | Q(user__last_name__iexact=first_name)
            
            employee = self.Employee.objects.filter(emp_query).first()
            if not employee:
                # Try partial match
                if first_name:
                    emp_query = Q(user__first_name__icontains=first_name)
                    if last_name:
                        emp_query &= Q(user__last_name__icontains=last_name)
                    employee = self.Employee.objects.filter(emp_query).first()
            
            if not employee:
                return json.dumps({"error": f"Employee not found with name '{first_name} {last_name}'. Please check the name and try again."})
            
            # Find the most recent pending leave request for this employee
            leave_request = self.LeaveRequest.objects.filter(
                employee=employee,
                status='PENDING'
            ).order_by('-created_at').first()
            
            if not leave_request:
                return json.dumps({"error": f"No pending leave request found for {employee.user.first_name} {employee.user.last_name}."})
            
            # Approve the leave
            leave_request.status = 'APPROVED'
            leave_request.approved_by = self.user
            leave_request.approved_at = timezone.now()
            leave_request.save()
            
            emp_name = f"{employee.user.first_name} {employee.user.last_name}"
            
            # Send notification to the employee
            try:
                self.Notification.objects.create(
                    recipient=employee.user,
                    notification_type=self.Notification.NotificationType.LEAVE_APPROVED,
                    title="Leave Request Approved",
                    message=(
                        f"Your {leave_request.leave_type.name} request "
                        f"({leave_request.start_date} to {leave_request.end_date}) "
                        f"has been approved by {self.user.get_full_name() or self.user.username}."
                    ),
                    link=f"/hr/leave-requests/{leave_request.id}",
                    metadata={
                        "leave_request_id": str(leave_request.id),
                        "status": "APPROVED",
                        "approved_by": str(self.user.id),
                    },
                )
            except Exception:
                pass  # Notification failure shouldn't block the approval
            
            # Send notification to the reporting manager
            try:
                if employee.reporting_to:
                    self.Notification.objects.create(
                        recipient=employee.reporting_to.user,
                        notification_type=self.Notification.NotificationType.LEAVE_APPROVED,
                        title=f"Leave Approved for {emp_name}",
                        message=(
                            f"The {leave_request.leave_type.name} request for {emp_name} "
                            f"({leave_request.start_date} to {leave_request.end_date}) "
                            f"has been approved by {self.user.get_full_name() or self.user.username}."
                        ),
                        link=f"/hr/leave-requests/{leave_request.id}",
                        metadata={
                            "leave_request_id": str(leave_request.id),
                            "status": "APPROVED",
                            "approved_by": str(self.user.id),
                        },
                    )
            except Exception:
                pass
            
            return json.dumps({
                "success": True,
                "message": f"Leave request approved for {emp_name}",
                "leave_type": leave_request.leave_type.name,
                "start_date": str(leave_request.start_date),
                "end_date": str(leave_request.end_date),
                "total_days": float(leave_request.total_days),
                "employee": emp_name,
                "notified_employee": True,
                "notified_manager": bool(employee.reporting_to),
            })
        except Exception as e:
            return json.dumps({"error": f"Error approving leave: {str(e)}"})

    def reject_leave_request(self, leave_request_id: str, reason: str = "") -> str:
        """Reject a pending leave request.
        
        Args:
            leave_request_id: Leave request UUID
            reason: Rejection reason (optional)
        """
        if not self._is_hr_or_admin():
            return json.dumps({"error": "Permission denied."})
        try:
            lr = self.LeaveRequest.objects.get(id=leave_request_id, status='PENDING')
            lr.status = 'REJECTED'
            lr.rejection_reason = reason
            lr.approved_by = self.user
            lr.approved_at = timezone.now()
            lr.save()
            return json.dumps({
                "success": True,
                "message": f"Leave request rejected for {lr.employee.user.first_name} {lr.employee.user.last_name}"
            })
        except self.LeaveRequest.DoesNotExist:
            return json.dumps({"error": "Leave request not found or already processed"})

    # ---- Payroll Tools ----

    def get_payroll_summary(self, month: int = 0, year: int = 0) -> str:
        """Get payroll summary for a specific month/year.
        
        Args:
            month: Month number (1-12, defaults to current month)
            year: Year (defaults to current year)
        """
        today = date.today()
        month = month or today.month
        year = year or today.year
        
        payrolls = self.Payroll.objects.filter(month=month, year=year)
        total_net = payrolls.aggregate(total=Sum('net_pay'))['total'] or 0
        total_basic = payrolls.aggregate(total=Sum('basic_salary'))['total'] or 0
        total_earnings = payrolls.aggregate(total=Sum('total_earnings'))['total'] or 0
        total_deductions = payrolls.aggregate(total=Sum('total_deductions'))['total'] or 0
        count = payrolls.count()
        
        return json.dumps({
            "month": month,
            "year": year,
            "total_employees": count,
            "total_basic_salary": float(total_basic),
            "total_earnings": float(total_earnings),
            "total_deductions": float(total_deductions),
            "total_net_pay": float(total_net),
            "average_net_pay": float(total_net / count) if count > 0 else 0,
        })

    def list_payroll(self, month: int = 0, year: int = 0) -> str:
        """List payroll records.
        
        Args:
            month: Month number (1-12, defaults to current)
            year: Year (defaults to current)
        """
        today = date.today()
        month = month or today.month
        year = year or today.year
        
        payrolls = self.Payroll.objects.filter(month=month, year=year).select_related('employee__user')
        result = []
        for p in payrolls[:30]:
            result.append({
                "id": str(p.id),
                "employee": f"{p.employee.user.first_name} {p.employee.user.last_name}",
                "employee_id": p.employee.employee_id,
                "basic_salary": float(p.basic_salary),
                "total_earnings": float(p.total_earnings),
                "total_deductions": float(p.total_deductions),
                "net_pay": float(p.net_pay),
                "status": p.status,
            })
        return json.dumps({"payrolls": result, "total": len(result)})

    # ---- Performance Tools ----

    def list_performance_reviews(self, employee_id: str = "") -> str:
        """List performance reviews.
        
        Args:
            employee_id: Filter by employee (optional)
        """
        qs = self.PerformanceReview.objects.select_related('employee__user', 'reviewer').all()
        if employee_id:
            qs = qs.filter(Q(employee__id=employee_id) | Q(employee__employee_id=employee_id))
        
        result = []
        for r in qs[:20]:
            result.append({
                "id": str(r.id),
                "employee": f"{r.employee.user.first_name} {r.employee.user.last_name}",
                "reviewer": f"{r.reviewer.first_name} {r.reviewer.last_name}" if r.reviewer else "",
                "status": r.status,
                "overall_rating": float(r.overall_rating) if r.overall_rating else None,
                "review_date": str(r.review_date) if r.review_date else "",
            })
        return json.dumps({"reviews": result, "total": len(result)})

    def list_goals(self, employee_id: str = "", status: str = "") -> str:
        """List goals.
        
        Args:
            employee_id: Filter by employee (optional)
            status: Filter by status (NOT_STARTED, IN_PROGRESS, COMPLETED, ON_HOLD, CANCELLED) (optional)
        """
        qs = self.Goal.objects.select_related('employee__user').all()
        if employee_id:
            qs = qs.filter(Q(employee__id=employee_id) | Q(employee__employee_id=employee_id))
        if status:
            qs = qs.filter(status=status)
        
        result = []
        for g in qs[:20]:
            result.append({
                "id": str(g.id),
                "title": g.title,
                "employee": f"{g.employee.user.first_name} {g.employee.user.last_name}",
                "status": g.status,
                "progress": g.progress_percentage,
                "goal_type": g.goal_type,
                "start_date": str(g.start_date) if g.start_date else "",
                "end_date": str(g.end_date) if g.end_date else "",
            })
        return json.dumps({"goals": result, "total": len(result)})

    # ---- Dashboard / Report Tools ----

    def get_dashboard_summary(self) -> str:
        """Get a comprehensive dashboard summary of the organization."""
        total_emp = self.Employee.objects.count()
        active_emp = self.Employee.objects.filter(employment_status='ACTIVE').count()
        dept_count = self.Department.objects.count()
        
        today_str = str(date.today())
        today_att = self.Attendance.objects.filter(date=today_str)
        
        pending_leaves = self.LeaveRequest.objects.filter(status='PENDING').count()
        
        # Current month payroll
        today = date.today()
        payroll = self.Payroll.objects.filter(month=today.month, year=today.year)
        total_payroll = payroll.aggregate(total=Sum('net_pay'))['total'] or 0
        
        return json.dumps({
            "total_employees": total_emp,
            "active_employees": active_emp,
            "departments": dept_count,
            "today_attendance": {
                "present": today_att.filter(status='PRESENT').count(),
                "absent": today_att.filter(status='ABSENT').count(),
                "late": today_att.filter(status='LATE').count(),
                "half_day": today_att.filter(status='HALF_DAY').count(),
                "on_leave": today_att.filter(status='ON_LEAVE').count(),
            },
            "pending_leaves": pending_leaves,
            "current_month_payroll": float(total_payroll),
            "on_leave_today": today_att.filter(status='ON_LEAVE').count(),
        })

    def get_upcoming_holidays(self) -> str:
        """Get upcoming holidays."""
        today = date.today()
        holidays = self.Holiday.objects.filter(date__gte=today).order_by('date')[:10]
        result = [{"name": h.name, "date": str(h.date), "type": h.get_holiday_type_display() if hasattr(h, 'get_holiday_type_display') else ""} for h in holidays]
        return json.dumps({"upcoming_holidays": result})

    def get_department_report(self) -> str:
        """Get a report of all departments with employee counts."""
        depts = self.Department.objects.annotate(
            emp_count=Count('employees'),
            active_count=Count('employees', filter=Q(employees__employment_status='ACTIVE'))
        ).all()
        result = []
        for d in depts:
            result.append({
                "name": d.name,
                "code": d.code,
                "total_employees": d.emp_count,
                "active_employees": d.active_count,
            })
        return json.dumps({"departments": result, "total": len(result)})

    def get_attendance_report(self, start_date: str = "", end_date: str = "") -> str:
        """Get attendance report for a date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD (defaults to 30 days ago)
            end_date: End date in YYYY-MM-DD (defaults to today)
        """
        if not end_date:
            end_date = str(date.today())
        if not start_date:
            start_date = str(date.today() - timedelta(days=30))
        
        records = self.Attendance.objects.filter(date__gte=start_date, date__lte=end_date)
        summary = records.values('status').annotate(count=Count('id'))
        total = records.count()
        
        return json.dumps({
            "period": f"{start_date} to {end_date}",
            "total_records": total,
            "breakdown": {s['status']: s['count'] for s in summary},
        })

    # ---- Natural Language Attendance Query ----

    def query_attendance(self, metric: str = "", period: str = "",
                         condition: str = "", threshold: int = 0,
                         group_by: str = "employee",
                         department_id: str = "") -> str:
        """Answer natural language questions about attendance data.
        
        Analyzes attendance records based on structured parameters extracted
        from natural language queries by the AI. Supports questions like:
        - "Who arrived late more than 3 times this week?"
        - "How many employees were absent last month?"
        - "Show me attendance trends for the Engineering department"
        
        Args:
            metric: What to measure - "late_count", "absent_count", "present_count",
                    "half_day_count", "wfh_count", "overtime_hours", "attendance_rate",
                    "trend", "all"
            period: Time period - "today", "this_week", "this_month", "last_week",
                    "last_month", "this_quarter", "last_quarter", "this_year",
                    or a custom range "YYYY-MM-DD:YYYY-MM-DD"
            condition: Filter condition - "greater_than", "less_than", "equal_to",
                      "top", "bottom", "all"
            threshold: Numeric threshold for conditions (e.g., 3 for "more than 3 times")
            group_by: How to group results - "employee" (default), "department", "date", "status"
            department_id: Optional department UUID to filter by
        """
        from django.db.models import Count, Q, Sum, Avg, F, Value, CharField
        from django.db.models.functions import TruncMonth, TruncWeek
        
        # Parse period into date range
        today = date.today()
        start_date = None
        end_date = None
        
        if not period or period == "today":
            start_date = today
            end_date = today
        elif period == "this_week":
            start_date = today - timedelta(days=today.weekday())
            end_date = today
        elif period == "last_week":
            end_date = today - timedelta(days=today.weekday() + 1)
            start_date = end_date - timedelta(days=6)
        elif period == "this_month":
            start_date = today.replace(day=1)
            end_date = today
        elif period == "last_month":
            end_date = today.replace(day=1) - timedelta(days=1)
            start_date = end_date.replace(day=1)
        elif period == "this_quarter":
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            start_date = today.replace(month=quarter_month, day=1)
            end_date = today
        elif period == "last_quarter":
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            start_date = today.replace(month=quarter_month, day=1) - timedelta(days=1)
            start_date = start_date.replace(day=1)
            # Go back 3 months from start of current quarter
            prev_quarter_month = start_date.month - 3
            prev_quarter_year = start_date.year
            if prev_quarter_month < 1:
                prev_quarter_month += 12
                prev_quarter_year -= 1
            start_date = start_date.replace(year=prev_quarter_year, month=prev_quarter_month, day=1)
            end_date = today.replace(month=quarter_month, day=1) - timedelta(days=1)
        elif period == "this_year":
            start_date = today.replace(month=1, day=1)
            end_date = today
        elif ":" in period:
            parts = period.split(":")
            if len(parts) == 2:
                try:
                    start_date = date.fromisoformat(parts[0])
                    end_date = date.fromisoformat(parts[1])
                except ValueError:
                    pass
        
        if not start_date or not end_date:
            return json.dumps({
                "error": f"Could not parse period: '{period}'. Use 'today', 'this_week', 'last_week', 'this_month', 'last_month', 'this_quarter', 'last_quarter', 'this_year', or 'YYYY-MM-DD:YYYY-MM-DD'."
            })
        
        # Build base query
        filters = Q(date__gte=start_date, date__lte=end_date)
        if department_id:
            filters &= Q(employee__department_id=department_id)
        
        records = self.Attendance.objects.filter(filters).select_related(
            "employee__user", "employee__department"
        )
        
        total_employees = self.Employee.objects.filter(
            employment_status=self.Employee.EmploymentStatus.ACTIVE
        ).count()
        
        # Determine metric and build response
        if metric == "trend" or metric == "all":
            # Daily breakdown
            daily = records.values("date").annotate(
                present=Count("id", filter=Q(status="PRESENT")),
                absent=Count("id", filter=Q(status="ABSENT")),
                late=Count("id", filter=Q(status="LATE")),
                half_day=Count("id", filter=Q(status="HALF_DAY")),
                wfh=Count("id", filter=Q(status="WFH")),
                on_leave=Count("id", filter=Q(status="ON_LEAVE")),
            ).order_by("date")
            
            return json.dumps({
                "query": f"Attendance trend from {start_date} to {end_date}",
                "period": {"start": str(start_date), "end": str(end_date)},
                "total_days": (end_date - start_date).days + 1,
                "daily_breakdown": [
                    {
                        "date": str(d["date"]),
                        "present": d["present"],
                        "absent": d["absent"],
                        "late": d["late"],
                        "half_day": d["half_day"],
                        "wfh": d["wfh"],
                        "on_leave": d["on_leave"],
                    }
                    for d in daily
                ],
                "total_employees": total_employees,
            })
        
        # Group by employee and count occurrences of the metric status
        status_map = {
            "late_count": "LATE",
            "absent_count": "ABSENT",
            "present_count": "PRESENT",
            "half_day_count": "HALF_DAY",
            "wfh_count": "WFH",
            "on_leave_count": "ON_LEAVE",
        }
        
        target_status = status_map.get(metric, "LATE")
        
        # Employee-level aggregation
        employee_stats = records.values(
            "employee__id", "employee__user__first_name",
            "employee__user__last_name", "employee__user__employee_id",
            "employee__department__name"
        ).annotate(
            status_count=Count("id", filter=Q(status=target_status)),
            total_days=Count("id"),
            total_late_minutes=Sum("late_minutes"),
            total_overtime=Sum("overtime_hours"),
            avg_work_hours=Avg("work_hours"),
        ).order_by("-status_count")
        
        # Apply condition/threshold filter
        if condition == "greater_than" and threshold > 0:
            employee_stats = [e for e in employee_stats if e["status_count"] > threshold]
        elif condition == "less_than" and threshold > 0:
            employee_stats = [e for e in employee_stats if e["status_count"] < threshold]
        elif condition == "equal_to" and threshold > 0:
            employee_stats = [e for e in employee_stats if e["status_count"] == threshold]
        elif condition == "top" and threshold > 0:
            employee_stats = list(employee_stats[:threshold])
        elif condition == "bottom" and threshold > 0:
            employee_stats = list(reversed(employee_stats))[:threshold]
        
        # Build result
        result_list = []
        for e in employee_stats:
            full_name = f"{e['employee__user__first_name']} {e['employee__user__last_name']}".strip()
            result_list.append({
                "employee_id": e["employee__user__employee_id"],
                "name": full_name or "Unknown",
                "department": e["employee__department__name"] or "N/A",
                f"{metric or 'late_count'}": e["status_count"],
                "total_attendance_days": e["total_days"],
                "total_late_minutes": float(e["total_late_minutes"] or 0),
                "avg_work_hours": float(e["avg_work_hours"] or 0),
                "total_overtime_hours": float(e["total_overtime"] or 0),
            })
        
        # Summary stats
        total_with_condition = records.filter(status=target_status).count()
        unique_employees = records.filter(status=target_status).values("employee").distinct().count()
        
        return json.dumps({
            "query": f"Employees with {metric.replace('_', ' ')} from {start_date} to {end_date}",
            "period": {"start": str(start_date), "end": str(end_date)},
            "metric": metric,
            "condition": condition,
            "threshold": threshold,
            "total_employees_in_period": records.values("employee").distinct().count(),
            "unique_employees_with_condition": unique_employees,
            "total_occurrences": total_with_condition,
            "results": result_list[:50],  # Limit to 50 results
            "result_count": len(result_list),
            "total_employees_org": total_employees,
        })

    def execute(self, function_name: str, **kwargs: Any) -> str:
        """Execute a function by name with the given arguments.
        
        This is the dispatch method called by the chat view when the AI
        requests a function call. It maps function names to the corresponding
        method on this class.
        
        Args:
            function_name: The name of the function to execute (e.g., "list_employees")
            **kwargs: Arguments to pass to the function
        
        Returns:
            JSON string result from the function
        """
        method = getattr(self, function_name, None)
        if method is None:
            return json.dumps({
                "error": f"Unknown function: '{function_name}'. "
                         f"Available functions: {', '.join(self._get_available_functions())}"
            })
        try:
            result = method(**kwargs)
            return result
        except TypeError as e:
            return json.dumps({
                "error": f"Invalid arguments for '{function_name}': {str(e)}"
            })
        except Exception as e:
            return json.dumps({
                "error": f"Error executing '{function_name}': {str(e)}"
            })

    def _get_available_functions(self) -> list[str]:
        """Get list of all callable function names on this tool."""
        exclude = {"execute", "_get_available_functions", "__init__", "user"}
        return [
            name for name in dir(self)
            if callable(getattr(self, name))
            and not name.startswith("_")
            and name not in exclude
        ]


# =============================================================================
# Function Registry - Maps function names to their schemas and implementations
# =============================================================================

# Define all available tools/functions for the AI
HRMS_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_dashboard_summary",
            "description": "Get a comprehensive dashboard summary of the organization including employee counts, today's attendance, pending leaves, and payroll",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_employee_count",
            "description": "Get total number of employees in the organization",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_employee_count",
            "description": "Get number of active employees",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_employees",
            "description": "List employees with optional filters by department, status, or search term",
            "parameters": {
                "type": "object",
                "properties": {
                    "department_id": {"type": "string", "description": "Filter by department UUID"},
                    "status": {"type": "string", "description": "Filter by employment status (ACTIVE, INACTIVE, ON_LEAVE, TERMINATED, RESIGNED)"},
                    "search": {"type": "string", "description": "Search by name or employee ID"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_employee_details",
            "description": "Get detailed information about a specific employee by their UUID or employee ID (e.g., EMP-001)",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string", "description": "Employee UUID or employee_id string (e.g., EMP-001)"}
                },
                "required": ["employee_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_employee",
            "description": "Create a new employee with a user account. Requires HR or Admin permissions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {"type": "string", "description": "Employee's first name"},
                    "last_name": {"type": "string", "description": "Employee's last name"},
                    "email": {"type": "string", "description": "Employee's email address"},
                    "department_id": {"type": "string", "description": "Department UUID"},
                    "designation_id": {"type": "string", "description": "Designation UUID"},
                    "employee_id": {"type": "string", "description": "Custom employee ID (auto-generated if empty)"},
                    "password": {"type": "string", "description": "Initial password (default: changeme123)"},
                    "employment_status": {"type": "string", "description": "Employment status"},
                    "employment_type": {"type": "string", "description": "Employment type"},
                    "joining_date": {"type": "string", "description": "Joining date (YYYY-MM-DD)"}
                },
                "required": ["first_name", "last_name", "email", "department_id", "designation_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_designations",
            "description": "List all designations, optionally filtered by department. Use this BEFORE create_employee to get the designation UUID required for creating an employee.",
            "parameters": {
                "type": "object",
                "properties": {
                    "department_id": {"type": "string", "description": "Filter by department UUID (optional)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_departments",
            "description": "List all departments with employee counts",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_department",
            "description": "Create a new department. Requires HR or Admin permissions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Department name"},
                    "code": {"type": "string", "description": "Department code (e.g., ENG)"},
                    "description": {"type": "string", "description": "Department description"}
                },
                "required": ["name", "code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_department",
            "description": "Update an existing department's name, code, or description",
            "parameters": {
                "type": "object",
                "properties": {
                    "department_id": {"type": "string", "description": "Department UUID"},
                    "name": {"type": "string", "description": "New department name"},
                    "code": {"type": "string", "description": "New department code"},
                    "description": {"type": "string", "description": "New department description"}
                },
                "required": ["department_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_department",
            "description": "Delete a department. Requires HR or Admin permissions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "department_id": {"type": "string", "description": "Department UUID"}
                },
                "required": ["department_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_attendance_summary",
            "description": "Get attendance summary for a specific date or today",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {"type": "string", "description": "Date in YYYY-MM-DD format (defaults to today)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mark_attendance",
            "description": "Mark attendance for an employee on a specific date. Requires HR or Admin permissions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string", "description": "Employee UUID or employee_id string"},
                    "date_str": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    "status": {"type": "string", "description": "Attendance status (PRESENT, ABSENT, LATE, HALF_DAY, ON_LEAVE)"},
                    "check_in": {"type": "string", "description": "Check-in time (HH:MM)"},
                    "check_out": {"type": "string", "description": "Check-out time (HH:MM)"},
                    "notes": {"type": "string", "description": "Optional notes"}
                },
                "required": ["employee_id", "date_str", "status"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mark_attendance_bulk",
            "description": "Mark attendance for multiple employees on a specific date. Requires HR or Admin permissions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_ids": {"type": "array", "items": {"type": "string"}, "description": "List of employee UUIDs or employee_id strings"},
                    "date_str": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    "status": {"type": "string", "description": "Attendance status (PRESENT, ABSENT, LATE, HALF_DAY, ON_LEAVE)"},
                    "check_in": {"type": "string", "description": "Check-in time (HH:MM)"},
                    "check_out": {"type": "string", "description": "Check-out time (HH:MM)"}
                },
                "required": ["employee_ids", "date_str", "status"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mark_attendance_date_range",
            "description": "Mark attendance for employees across a date range (e.g., mark present or absent from date to date). Requires HR or Admin permissions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_ids": {"type": "array", "items": {"type": "string"}, "description": "List of employee UUIDs or employee_id strings"},
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"},
                    "status": {"type": "string", "description": "Attendance status (PRESENT, ABSENT, LATE, HALF_DAY, ON_LEAVE)"}
                },
                "required": ["employee_ids", "start_date", "end_date", "status"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_leave_types",
            "description": "List all available leave types",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_leave_balance",
            "description": "Get leave balance for an employee or all employees",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string", "description": "Employee UUID or employee_id (optional, returns all if empty)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_leave_requests",
            "description": "List leave requests with optional filters by status or employee",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by status (PENDING, APPROVED, REJECTED, CANCELLED)"},
                    "employee_id": {"type": "string", "description": "Filter by employee UUID or employee_id"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_leave_request",
            "description": "Create a leave request for an employee",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string", "description": "Employee UUID or employee_id string"},
                    "leave_type_id": {"type": "string", "description": "Leave type UUID"},
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"},
                    "reason": {"type": "string", "description": "Reason for leave"},
                    "half_day": {"type": "boolean", "description": "Whether it's a half day leave"},
                    "is_emergency": {"type": "boolean", "description": "Whether it's an emergency leave"}
                },
                "required": ["employee_id", "leave_type_id", "start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "approve_leave_request",
            "description": "Approve a pending leave request. Requires HR or Admin permissions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "leave_request_id": {"type": "string", "description": "Leave request UUID"}
                },
                "required": ["leave_request_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "approve_leave_by_employee_name",
            "description": "Approve a pending leave request by finding the employee by name. Looks up the employee by first and/or last name, finds their most recent pending leave request, approves it, and sends notifications to both the employee and their reporting manager. Requires HR or Admin permissions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {"type": "string", "description": "Employee's first name (e.g., 'John')"},
                    "last_name": {"type": "string", "description": "Employee's last name (e.g., 'Doe')"}
                },
                "required": ["first_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reject_leave_request",
            "description": "Reject a pending leave request. Requires HR or Admin permissions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "leave_request_id": {"type": "string", "description": "Leave request UUID"},
                    "reason": {"type": "string", "description": "Rejection reason"}
                },
                "required": ["leave_request_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_payroll_summary",
            "description": "Get payroll summary for a specific month/year",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {"type": "integer", "description": "Month number (1-12, defaults to current month)"},
                    "year": {"type": "integer", "description": "Year (defaults to current year)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_payroll",
            "description": "List payroll records for a specific month/year",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {"type": "integer", "description": "Month number (1-12, defaults to current)"},
                    "year": {"type": "integer", "description": "Year (defaults to current)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_performance_reviews",
            "description": "List performance reviews, optionally filtered by employee",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string", "description": "Filter by employee UUID or employee_id"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_goals",
            "description": "List goals, optionally filtered by employee or status",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string", "description": "Filter by employee UUID or employee_id"},
                    "status": {"type": "string", "description": "Filter by status (NOT_STARTED, IN_PROGRESS, COMPLETED, ON_HOLD, CANCELLED)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_upcoming_holidays",
            "description": "Get upcoming holidays",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_department_report",
            "description": "Get a report of all departments with employee counts",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_attendance_report",
            "description": "Get attendance report for a date range",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD (defaults to 30 days ago)"},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD (defaults to today)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_attendance",
            "description": "Answer natural language questions about attendance data. Use this when the user asks questions like 'Who arrived late more than 3 times this week?', 'How many were absent last month?', 'Show attendance trends', 'Who has the most overtime?', 'List employees with perfect attendance'. The AI should parse the user's question and fill in the appropriate parameters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "enum": ["late_count", "absent_count", "present_count", "half_day_count", "wfh_count", "on_leave_count", "overtime_hours", "attendance_rate", "trend", "all"],
                        "description": "What to measure. Use 'late_count' for late arrivals, 'absent_count' for absences, 'present_count' for present, 'half_day_count' for half days, 'wfh_count' for work from home, 'on_leave_count' for on leave, 'overtime_hours' for overtime, 'trend' for daily breakdown, 'all' for everything"
                    },
                    "period": {
                        "type": "string",
                        "description": "Time period: 'today', 'this_week', 'last_week', 'this_month', 'last_month', 'this_quarter', 'last_quarter', 'this_year', or custom range 'YYYY-MM-DD:YYYY-MM-DD'"
                    },
                    "condition": {
                        "type": "string",
                        "enum": ["greater_than", "less_than", "equal_to", "top", "bottom", "all"],
                        "description": "Filter condition. Use 'greater_than' for 'more than', 'less_than' for 'less than', 'equal_to' for 'exactly', 'top' for 'top N', 'bottom' for 'bottom N', 'all' for no filter"
                    },
                    "threshold": {
                        "type": "integer",
                        "description": "Numeric threshold for conditions. E.g., 3 for 'more than 3 times', 5 for 'top 5'"
                    },
                    "group_by": {
                        "type": "string",
                        "enum": ["employee", "department", "date", "status"],
                        "description": "How to group results: 'employee' (default), 'department', 'date', 'status'"
                    },
                    "department_id": {
                        "type": "string",
                        "description": "Optional department UUID to filter by a specific department"
                    }
                },
                "required": ["metric", "period"]
            }
        }
    },
]


# =============================================================================
# DeepSeek Client - Handles communication with the DeepSeek API
# =============================================================================

class DeepSeekClient:
    """
    Client for interacting with AI APIs (OpenAI-compatible).
    Supports both DeepSeek and OpenAI providers, dynamically switching
    based on SystemSettings configuration.

    Handles chat completions, function/tool calling, and embedding generation.
    """

    def __init__(self):
        # Try to load from SystemSettings first, fall back to settings.py
        self._load_from_db()

    def _load_from_db(self) -> None:
        """Load configuration from SystemSettings or settings.py defaults."""
        try:
            from config.apps.hrms.models import SystemSettings
            sys_settings = SystemSettings.get_settings()
            db_api_key = sys_settings.get_active_api_key()
            db_base_url = sys_settings.get_active_base_url()
            db_model = sys_settings.get_active_model()

            # Use DB values if they are non-empty, otherwise fall back to .env defaults
            self.api_key = db_api_key or settings.DEEPSEEK_API_KEY
            self.base_url = db_base_url or settings.DEEPSEEK_BASE_URL
            self.model = db_model or settings.DEEPSEEK_MODEL
            self.embedding_model = sys_settings.embedding_model or settings.DEEPSEEK_EMBEDDING_MODEL
            self.provider = sys_settings.ai_provider
        except Exception:
            # Fall back to settings.py defaults
            self.api_key = settings.DEEPSEEK_API_KEY
            self.base_url = settings.DEEPSEEK_BASE_URL
            self.model = settings.DEEPSEEK_MODEL
            self.embedding_model = settings.DEEPSEEK_EMBEDDING_MODEL
            self.provider = "DEEPSEEK"

        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            logger.info(
                "AI client initialized with provider=%s model=%s at %s",
                self.provider,
                self.model,
                self.base_url,
            )
        else:
            self.client = None
            logger.warning(
                "AI API key not configured. AI features will be unavailable."
            )

    def reload(self) -> None:
        """Reload configuration from SystemSettings (called after settings update)."""
        self._load_from_db()

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        functions: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> dict[str, Any] | None:
        """
        Send a chat completion request to the DeepSeek API with optional function calling.

        Args:
            messages: List of message dicts with 'role' and 'content'
            functions: Optional list of function definitions for tool calling
            temperature: Response creativity (0.0 - 1.0)
            max_tokens: Maximum tokens in the response

        Returns:
            Dict with 'content', 'tokens_used', 'model', and optionally 'function_call'
        """
        if not self.client:
            logger.error("DeepSeek client not initialized (missing API key)")
            return None

        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if functions:
                kwargs["tools"] = functions
                kwargs["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]

            result: dict[str, Any] = {
                "content": choice.message.content or "",
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "model": response.model,
            }

            # Handle tool/function calls
            if choice.message.tool_calls:
                result["function_call"] = {
                    "name": choice.message.tool_calls[0].function.name,
                    "arguments": choice.message.tool_calls[0].function.arguments,
                }
                # If the model only made a function call with no text content
                if not result["content"]:
                    result["content"] = json.dumps({
                        "function_call": result["function_call"]["name"],
                        "awaiting_execution": True,
                    })

            return result

        except Exception as e:
            logger.error("DeepSeek API call failed: %s", str(e), exc_info=True)
            return None

    def generate_embedding(self, text: str) -> list[float] | None:
        """
        Generate an embedding vector for the given text.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the embedding vector, or None on failure
        """
        if not self.client:
            logger.error("DeepSeek client not initialized (missing API key)")
            return None

        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(
                "Embedding generation failed: %s", str(e), exc_info=True
            )
            return None

    def is_available(self) -> bool:
        """Check if the AI client is properly configured (has API key and client)."""
        return self.client is not None

    def test_connection(self) -> dict:
        """
        Actually test the API connection by making a minimal API call.
        Returns a dict with 'success' (bool) and 'message' (str).
        This is used by the health check and Settings page to verify the API key works.
        """
        if not self.client:
            return {
                "success": False,
                "message": "AI client not initialized. No API key configured.",
            }

        try:
            # Make a minimal chat completion request to test connectivity
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Say 'ok'"}],
                max_tokens=10,
            )
            if response and response.choices:
                return {
                    "success": True,
                    "message": f"Connected to {self.provider} ({self.model})",
                    "model": response.model,
                }
            return {
                "success": False,
                "message": "API returned an empty response.",
            }
        except Exception as e:
            error_str = str(e)
            logger.warning("AI connection test failed: %s", error_str)
            return {
                "success": False,
                "message": f"Connection failed: {error_str}",
            }


# =============================================================================
# RAG Engine - Retrieval-Augmented Generation for company documents
# =============================================================================

class RAGEngine:
    """
    Retrieval-Augmented Generation engine that searches company documents
    and policies to provide context-aware responses.

    Uses cosine similarity search over document embeddings stored in the database.
    """

    def __init__(self):
        from config.apps.chatbot.models import DocumentEmbedding

        self.DocumentEmbedding = DocumentEmbedding

    def build_context(
        self,
        query: str,
        document_type: str | None = None,
        top_k: int = 3,
    ) -> str:
        """
        Build a context string from relevant documents for the given query.

        Args:
            query: The user's query text
            document_type: Optional filter by document type
            top_k: Number of top documents to include

        Returns:
            A string containing the relevant document context, or empty string
        """
        similar_docs = self.search_similar(query, document_type, top_k)
        if not similar_docs:
            return ""

        context_parts = []
        for doc in similar_docs:
            content = doc.get("content", "")
            title = doc.get("title", "Untitled")
            context_parts.append(f"[From: {title}]\n{content}")

        return "\n\n---\n\n".join(context_parts)

    def search_similar(
        self,
        query: str,
        document_type: str | None = None,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Search for documents similar to the query using cosine similarity.

        Args:
            query: The search query
            document_type: Optional filter by document type
            top_k: Number of results to return

        Returns:
            List of dicts with 'content', 'title', 'similarity' keys
        """
        # Get the DeepSeek client for embedding generation
        client = get_deepseek_client()
        if not client or not client.is_available():
            logger.warning(
                "DeepSeek client unavailable for RAG search. "
                "Falling back to keyword search."
            )
            return self._keyword_search(query, document_type, top_k)

        query_embedding = client.generate_embedding(query)
        if not query_embedding:
            logger.warning(
                "Failed to generate query embedding. Falling back to keyword search."
            )
            return self._keyword_search(query, document_type, top_k)

        # Get all document embeddings from the database
        docs_qs = self.DocumentEmbedding.objects.all()
        if document_type:
            docs_qs = docs_qs.filter(document_type=document_type)

        if not docs_qs.exists():
            return []

        # Compute cosine similarity
        query_vec = np.array(query_embedding, dtype=np.float32)
        results: list[dict[str, Any]] = []

        for doc in docs_qs:
            doc_vec = np.array(doc.embedding, dtype=np.float32)
            similarity = self._cosine_similarity(query_vec, doc_vec)

            results.append({
                "id": str(doc.id),
                "content": doc.content[:2000],  # Limit content length
                "title": doc.title or "Untitled",
                "document_type": doc.document_type,
                "similarity": float(similarity),
            })

        # Sort by similarity (highest first) and return top_k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def _keyword_search(
        self,
        query: str,
        document_type: str | None = None,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Fallback keyword-based search when embeddings are unavailable.
        """
        docs_qs = self.DocumentEmbedding.objects.all()
        if document_type:
            docs_qs = docs_qs.filter(document_type=document_type)

        # Simple keyword matching
        query_lower = query.lower()
        query_words = query_lower.split()

        results: list[dict[str, Any]] = []
        for doc in docs_qs:
            content_lower = doc.content.lower()
            title_lower = doc.title.lower() if doc.title else ""

            # Count keyword matches
            score = sum(
                1 for word in query_words
                if word in content_lower or word in title_lower
            )

            if score > 0:
                results.append({
                    "id": str(doc.id),
                    "content": doc.content[:2000],
                    "title": doc.title or "Untitled",
                    "document_type": doc.document_type,
                    "similarity": score / len(query_words) if query_words else 0,
                })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    @staticmethod
    def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot_product / (norm_a * norm_b))

    def get_system_prompt(self) -> str:
        """Get the system prompt for the AI assistant."""
        now = timezone.localtime(timezone.now())
        today = now.date()
        current_date_str = today.isoformat()
        current_time_str = now.strftime("%H:%M")
        day_of_week = today.strftime("%A")

        return (
            "You are an intelligent HRMS (Human Resource Management System) AI assistant. "
            "Your role is to help users manage and query all aspects of the HR system.\n\n"
            f"CURRENT DATE AND TIME: Today is {day_of_week}, {current_date_str}. "
            f"The current time is {current_time_str} (Asia/Kabul timezone).\n"
            "IMPORTANT: Always use this current date when referring to 'today', 'tomorrow', "
            "or any relative dates. Do not guess or hallucinate dates.\n\n"
            "CAPABILITIES:\n"
            "1. You can QUERY any data in the system - employees, departments, attendance, "
            "leaves, payroll, performance reviews, goals, and more.\n"
            "2. You can MODIFY data - create employees, mark attendance, manage leaves, "
            "update departments, and more (with proper permissions).\n"
            "3. You can GENERATE REPORTS - department reports, attendance reports, "
            "payroll summaries, and comprehensive organizational overviews.\n"
            "4. You can answer questions about company policies based on uploaded documents.\n\n"
            "EMPLOYEE MANAGEMENT:\n"
            "- To CREATE an employee, you MUST first call list_departments() and "
            "list_designations() to get the required UUIDs for department_id and "
            "designation_id. Then use create_employee function with: "
            "first_name, last_name, email, department_id, and designation_id.\n"
            "- To look up employees, first use list_employees() to find the employee, "
            "then use get_employee_details(employee_id) for full details.\n"
            "- You can search employees by name, department, or status.\n"
            "- Only HR and Admin users can create employees.\n\n"
            "RULES:\n"
            "- Always be helpful, professional, and concise.\n"
            "- When asked to perform actions that modify data, confirm with the user first.\n"
            "- If you don't have permission to perform an action, explain why.\n"
            "- Use the available tools/functions to get real data from the system.\n"
            "- When presenting data, format it nicely using tables or bullet points.\n"
            "- For date ranges, always clarify the exact dates with the user.\n"
            "- You can mark attendance for employees across date ranges (e.g., 'mark John "
            "as present from 2024-01-01 to 2024-01-05').\n"
            "- You can create, update, and delete departments.\n"
            "- You can view and manage leave requests.\n"
            "- You can provide payroll summaries and performance review information.\n\n"
            "Always strive to provide accurate, data-driven responses using the "
            "HRMS system's real data."
        )


# =============================================================================
# Local Intent Parser - Fallback when DeepSeek API is unavailable
# =============================================================================

class LocalIntentParser:
    """
    Parses natural language commands and executes them using HRMSTools
    when the DeepSeek AI API is unavailable.

    This provides basic conversational AI capabilities by matching user
    messages against known intent patterns and extracting parameters
    to call the appropriate HRMS tool functions.
    """

    def __init__(self, hrms_tools: HRMSTools):
        self.tools = hrms_tools

    def _get_today_str(self) -> str:
        """Get today's date as string using the configured timezone."""
        return timezone.localdate().isoformat()

    def _get_tomorrow_str(self) -> str:
        """Get tomorrow's date as string using the configured timezone."""
        return (timezone.localdate() + timedelta(days=1)).isoformat()

    def process_message(self, message: str) -> str:
        """
        Process a user message and return a response string.
        Tries to match the message against known intents and execute
        the corresponding HRMS tool function.
        """
        msg_lower = message.lower().strip()

        # ---- Greetings ----
        if self._matches_any(msg_lower, [
            "hello", "hi", "hey", "good morning", "good afternoon",
            "good evening", "greetings", "howdy", "what's up", "sup"
        ]):
            return "Hello! I'm your HRMS AI Assistant. I can help you manage employees, attendance, leaves, payroll, and more. How can I assist you today?"

        # ---- Help / Capabilities ----
        if self._matches_any(msg_lower, [
            "help", "what can you do", "capabilities", "commands",
            "what can i ask", "how can you help", "features"
        ]):
            return (
                "I can help you with the following:\n\n"
                "📋 **Employees** - List employees, get details, create new employees\n"
                "🏢 **Departments** - List, create, update, or delete departments\n"
                "✅ **Attendance** - View attendance summary, mark attendance, ask natural language questions\n"
                "🏖️ **Leaves** - List leave types, check balances, create/approve/reject leave requests\n"
                "💰 **Payroll** - View payroll summaries and details\n"
                "📊 **Performance** - List performance reviews and goals\n"
                "📈 **Reports** - Dashboard summary, department reports, attendance reports\n"
                "🎉 **Holidays** - View upcoming holidays\n\n"
                "Try saying something like:\n"
                '- "Show me all employees"\n'
                '- "Create employee John Doe, john@example.com, Engineering, Developer"\n'
                '- "Tell me about John"\n'
                '- "Create a leave for John"\n'
                '- "Mark EMP-001 as present today"\n'
                '- "Show pending leave requests"\n'
                '- "What is the payroll summary?"\n'
                '- "Who arrived late more than 3 times this week?"\n'
                '- "How many employees were absent last month?"\n'
                '- "Show attendance trends this month"\n'
                '- "Top 5 employees with most overtime"'
            )

        # ---- Dashboard Summary ----
        if self._matches_any(msg_lower, [
            "dashboard", "summary", "overview", "show me the dashboard",
            "organization overview", "company overview", "org summary"
        ]):
            return self._safe_execute("get_dashboard_summary")

        # ---- Employee Operations ----
        # List all employees
        if self._matches_any(msg_lower, [
            "list employees", "show employees", "all employees",
            "employee list", "show me employees", "list all employees",
            "get employees", "view employees"
        ]):
            return self._safe_execute("list_employees")

        # Employee count
        if self._matches_any(msg_lower, [
            "how many employees", "employee count", "total employees",
            "number of employees", "count employees"
        ]):
            # Check if they want active count
            if self._matches_any(msg_lower, ["active"]):
                return self._safe_execute("get_active_employee_count")
            return self._safe_execute("get_employee_count")

        # Get employee details - by ID or name
        emp_id_match = self._extract_employee_id(message)
        if emp_id_match and self._matches_any(msg_lower, ["details of", "get employee", "show employee",
                                                           "employee info", "employee information",
                                                           "find employee", "search employee",
                                                           "tell me about", "information about",
                                                           "who is", "details about"]):
            return self._safe_execute("get_employee_details", employee_id=emp_id_match)

        # Also try name-based employee lookup for queries like "tell me about John"
        name_based_emp_id = self._extract_employee_id_from_text(message)
        if name_based_emp_id and self._matches_any(msg_lower, ["details of", "get employee", "show employee",
                                                                "employee info", "employee information",
                                                                "find employee", "search employee",
                                                                "tell me about", "information about",
                                                                "who is", "details about"]):
            return self._safe_execute("get_employee_details", employee_id=name_based_emp_id)

        if not emp_id_match and not name_based_emp_id and self._matches_any(msg_lower, ["details of", "get employee", "show employee",
                                                                                         "employee info", "employee information",
                                                                                         "find employee", "search employee",
                                                                                         "tell me about", "information about",
                                                                                         "who is", "details about"]):
            return "Please provide an employee ID or name. For example: 'Show details of EMP-001' or 'Tell me about John'"

        # ---- Create Employee ----
        if self._matches_any(msg_lower, ["create employee", "add employee", "new employee",
                                          "hire employee", "register employee",
                                          "create a new employee", "add a new employee"]):
            return self._handle_create_employee(message, msg_lower)

        # ---- Designation Operations ----
        if self._matches_any(msg_lower, [
            "list designations", "show designations", "all designations",
            "designation list", "show me designations", "designations",
            "what designations", "list designation"
        ]):
            return self._safe_execute("list_designations")

        # ---- Department Operations ----
        if self._matches_any(msg_lower, [
            "list departments", "show departments", "all departments",
            "department list", "show me departments", "departments"
        ]):
            return self._safe_execute("list_departments")

        if self._matches_any(msg_lower, ["department report", "department wise",
                                          "department-wise", "employees by department"]):
            return self._safe_execute("get_department_report")

        # ---- Attendance Operations ----
        if self._matches_any(msg_lower, [
            "attendance summary", "attendance report", "show attendance",
            "today attendance", "attendance today", "attendance for today"
        ]):
            today = self._get_today_str()
            return self._safe_execute("get_attendance_summary", date_str=today)

        # Mark attendance
        if self._matches_any(msg_lower, ["mark attendance", "mark present", "mark absent",
                                          "mark late", "mark half day"]):
            emp_id = emp_id_match or self._extract_employee_id_from_text(message)
            status = self._extract_attendance_status(msg_lower)
            if emp_id and status:
                today = self._get_today_str()
                return self._safe_execute("mark_attendance", employee_id=emp_id,
                                           date_str=today, status=status)
            elif not emp_id:
                return "Please specify which employee. For example: 'Mark EMP-001 as present today'"
            else:
                return "Please specify a status: PRESENT, ABSENT, LATE, or HALF_DAY."

        # Mark attendance for date range
        if self._matches_any(msg_lower, ["mark present from", "mark absent from",
                                          "mark attendance from"]):
            emp_id = emp_id_match or self._extract_employee_id_from_text(message)
            dates = self._extract_date_range(message)
            status = self._extract_attendance_status(msg_lower)
            if emp_id and dates and status:
                return self._safe_execute("mark_attendance_date_range",
                                           employee_ids=[emp_id],
                                           start_date=dates["start"],
                                           end_date=dates["end"],
                                           status=status)
            return "Please specify employee, dates, and status. Example: 'Mark EMP-001 as present from 2024-01-01 to 2024-01-05'"

        # ---- Leave Operations ----
        if self._matches_any(msg_lower, ["leave types", "types of leave",
                                          "leave categories", "what leaves"]):
            return self._safe_execute("list_leave_types")

        if self._matches_any(msg_lower, ["leave balance", "leave remaining",
                                          "leaves left", "check leave balance",
                                          "my leave balance", "available leave"]):
            if emp_id_match:
                return self._safe_execute("get_leave_balance", employee_id=emp_id_match)
            return self._safe_execute("get_leave_balance")

        if self._matches_any(msg_lower, ["pending leaves", "pending leave requests",
                                          "pending leave", "leave requests pending",
                                          "show pending leaves"]):
            return self._safe_execute("list_leave_requests", status="PENDING")

        if self._matches_any(msg_lower, ["approved leaves", "approved leave requests",
                                          "show approved leaves"]):
            return self._safe_execute("list_leave_requests", status="APPROVED")

        if self._matches_any(msg_lower, ["rejected leaves", "rejected leave requests"]):
            return self._safe_execute("list_leave_requests", status="REJECTED")

        if self._matches_any(msg_lower, ["all leaves", "list leaves", "leave requests",
                                          "show leaves", "all leave requests"]):
            return self._safe_execute("list_leave_requests")

        # Create leave request
        if self._matches_any(msg_lower, ["create leave", "apply leave", "apply for leave",
                                          "create a leave", "request leave", "new leave",
                                          "book leave", "take leave"]):
            return self._handle_create_leave(message, msg_lower)

        # Approve leave - by ID or by employee name
        if self._matches_any(msg_lower, ["approve leave", "approve request", "approve"]):
            leave_id = self._extract_leave_id(message)
            if leave_id:
                return self._safe_execute("approve_leave_request", leave_request_id=leave_id)
            # Try name-based lookup: "Approve John's leave" or "Approve John Doe leave"
            name_based_emp_id = self._extract_employee_id_from_text(message)
            if name_based_emp_id:
                # Extract first_name and last_name from the message
                import re
                # Remove common words to isolate the name
                cleaned = message
                for word in ["approve", "leave", "request", "s", "the", "of", "for", "from"]:
                    cleaned = re.sub(r'\b' + word + r'\b', '', cleaned, flags=re.IGNORECASE)
                cleaned = cleaned.strip().strip("'").strip()
                # Split remaining words to get first/last name
                name_parts = cleaned.split()
                first_name = name_parts[0] if name_parts else ""
                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                if first_name:
                    return self._safe_execute("approve_leave_by_employee_name",
                                               first_name=first_name,
                                               last_name=last_name)
            return "Please provide the leave request ID or employee name. Examples: 'Approve leave request abc-123' or 'Approve John's leave'"

        # Reject leave
        if self._matches_any(msg_lower, ["reject leave", "reject request"]):
            leave_id = self._extract_leave_id(message)
            if leave_id:
                return self._safe_execute("reject_leave_request", leave_request_id=leave_id)
            return "Please provide the leave request ID. Example: 'Reject leave request abc-123'"

        # ---- Payroll Operations ----
        if self._matches_any(msg_lower, [
            "payroll summary", "payroll", "salary summary",
            "total payroll", "payroll this month", "monthly payroll"
        ]):
            return self._safe_execute("get_payroll_summary")

        if self._matches_any(msg_lower, [
            "list payroll", "payroll list", "show payroll",
            "payroll details", "salary list"
        ]):
            return self._safe_execute("list_payroll")

        # ---- Performance Operations ----
        if self._matches_any(msg_lower, [
            "performance reviews", "performance review", "reviews",
            "list performance", "show performance"
        ]):
            if emp_id_match:
                return self._safe_execute("list_performance_reviews", employee_id=emp_id_match)
            return self._safe_execute("list_performance_reviews")

        if self._matches_any(msg_lower, ["goals", "list goals", "show goals"]):
            if emp_id_match:
                return self._safe_execute("list_goals", employee_id=emp_id_match)
            return self._safe_execute("list_goals")

        # ---- Holidays ----
        if self._matches_any(msg_lower, [
            "holidays", "upcoming holidays", "holiday list",
            "show holidays", "list holidays", "vacation days"
        ]):
            return self._safe_execute("get_upcoming_holidays")

        # ---- Natural Language Attendance Queries ----
        if self._matches_any(msg_lower, [
            "who arrived late", "who was late", "who came late",
            "late arrivals", "employees late", "late more than",
            "late times this week", "late times this month",
            "who was absent", "who is absent", "absent employees",
            "absent this week", "absent this month",
            "attendance trend", "attendance trends",
            "most overtime", "highest overtime", "overtime hours",
            "perfect attendance", "attendance rate",
            "who worked from home", "wfh count", "work from home",
            "half day count", "half days",
            "on leave count", "employees on leave"
        ]):
            # Parse period from message
            period = "this_month"
            if self._matches_any(msg_lower, ["today", "this week"]):
                period = "this_week" if "week" in msg_lower else "today"
            elif self._matches_any(msg_lower, ["last week"]):
                period = "last_week"
            elif self._matches_any(msg_lower, ["last month"]):
                period = "last_month"
            elif self._matches_any(msg_lower, ["this quarter", "this quarter"]):
                period = "this_quarter"
            elif self._matches_any(msg_lower, ["this year"]):
                period = "this_year"

            # Parse metric
            metric = "late_count"
            if self._matches_any(msg_lower, ["absent", "absence"]):
                metric = "absent_count"
            elif self._matches_any(msg_lower, ["present"]):
                metric = "present_count"
            elif self._matches_any(msg_lower, ["overtime"]):
                metric = "overtime_hours"
            elif self._matches_any(msg_lower, ["trend"]):
                metric = "trend"
            elif self._matches_any(msg_lower, ["wfh", "work from home"]):
                metric = "wfh_count"
            elif self._matches_any(msg_lower, ["half day"]):
                metric = "half_day_count"
            elif self._matches_any(msg_lower, ["on leave"]):
                metric = "on_leave_count"
            elif self._matches_any(msg_lower, ["attendance rate", "attendance percentage"]):
                metric = "attendance_rate"

            # Parse condition/threshold
            condition = "all"
            threshold = 0
            if self._matches_any(msg_lower, ["more than", "greater than", "over"]):
                condition = "greater_than"
                # Try to extract number
                import re
                nums = re.findall(r'\d+', msg_lower)
                if nums:
                    threshold = int(nums[0])
            elif self._matches_any(msg_lower, ["less than", "fewer than", "under"]):
                condition = "less_than"
                nums = re.findall(r'\d+', msg_lower)
                if nums:
                    threshold = int(nums[0])
            elif self._matches_any(msg_lower, ["top"]):
                condition = "top"
                nums = re.findall(r'\d+', msg_lower)
                if nums:
                    threshold = int(nums[0])
                else:
                    threshold = 5  # Default top 5
            elif self._matches_any(msg_lower, ["bottom"]):
                condition = "bottom"
                nums = re.findall(r'\d+', msg_lower)
                if nums:
                    threshold = int(nums[0])
                else:
                    threshold = 5  # Default bottom 5

            return self._safe_execute("query_attendance",
                                       metric=metric,
                                       period=period,
                                       condition=condition,
                                       threshold=threshold)

        # ---- Attendance Report ----
        if self._matches_any(msg_lower, [
            "attendance report for", "attendance from", "attendance between"
        ]):
            dates = self._extract_date_range(message)
            if dates:
                return self._safe_execute("get_attendance_report",
                                           start_date=dates["start"],
                                           end_date=dates["end"])
            return self._safe_execute("get_attendance_report")

        # ---- Fallback ----
        return (
            "I'm not sure I understand. I can help you with employees, "
            "attendance, leaves, payroll, departments, performance reviews, "
            "and more. Try asking something like:\n"
            '- "Show me all employees"\n'
            '- "Create employee John Doe, john@example.com, Engineering, Developer"\n'
            '- "Tell me about John"\n'
            '- "Create a leave for EMP-001"\n'
            '- "Mark EMP-001 as present today"\n'
            '- "Show pending leave requests"\n'
            '- "Approve John\'s leave request"\n'
            '- "Who arrived late more than 3 times this week?"\n'
            '- "How many employees were absent last month?"\n'
            '- "What can you do?"'
        )

    def _matches_any(self, text: str, patterns: list[str]) -> bool:
        """Check if any of the patterns appear in the text."""
        return any(p in text for p in patterns)

    def _extract_employee_id(self, message: str) -> str | None:
        """Extract employee ID like EMP-001 or UUID from message."""
        import re
        # Match EMP-XXX pattern
        emp_match = re.search(r'EMP[-_][A-Z0-9]+', message, re.IGNORECASE)
        if emp_match:
            return emp_match.group(0).upper()
        # Match UUID pattern
        uuid_match = re.search(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            message, re.IGNORECASE
        )
        if uuid_match:
            return uuid_match.group(0)
        return None

    def _extract_employee_id_from_text(self, message: str) -> str | None:
        """Try to find an employee reference - ID or name-based lookup."""
        emp_id = self._extract_employee_id(message)
        if emp_id:
            return emp_id

        # Try to find a name in the message and look up the employee
        import re

        # Extract potential name tokens from the message
        # Look for capitalized words that could be names (2+ chars)
        name_words = re.findall(r'\b[A-Z][a-z]+\b', message)

        # Also try to extract names after common prefixes like "for", "of", "employee"
        # e.g., "create leave for John", "leave for John Doe"
        prefix_patterns = [
            r'(?:for|of|employee|to|by|with)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'(?:create|apply|book|take)\s+(?:leave|a\s+leave)\s+(?:for\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        ]
        for pattern in prefix_patterns:
            match = re.search(pattern, message)
            if match:
                extracted_name = match.group(1).strip()
                # Add extracted name words to our search set
                for w in extracted_name.split():
                    if w not in name_words:
                        name_words.append(w)

        if not name_words:
            return None

        # Try to find employee by name
        try:
            result = json.loads(self.tools.list_employees())
            employees = result.get("employees", [])
            # First pass: try to match full name (first + last)
            if len(name_words) >= 2:
                full_name_query = " ".join(name_words[:2]).lower()
                for emp in employees:
                    emp_name = emp.get("name", "").lower()
                    if full_name_query == emp_name or full_name_query in emp_name:
                        return emp.get("employee_id") or emp.get("id")

            # Second pass: match any single name word
            for emp in employees:
                emp_name = emp.get("name", "").lower()
                for word in name_words:
                    if word.lower() in emp_name:
                        return emp.get("employee_id") or emp.get("id")

            # Third pass: try matching first name only (case-insensitive)
            for emp in employees:
                emp_name = emp.get("name", "").lower()
                first_name = emp_name.split()[0] if emp_name else ""
                for word in name_words:
                    if word.lower() == first_name:
                        return emp.get("employee_id") or emp.get("id")

        except Exception:
            pass

        return None

    def _extract_attendance_status(self, msg_lower: str) -> str | None:
        """Extract attendance status from message."""
        if "present" in msg_lower:
            return "PRESENT"
        if "absent" in msg_lower:
            return "ABSENT"
        if "late" in msg_lower:
            return "LATE"
        if "half day" in msg_lower or "half-day" in msg_lower:
            return "HALF_DAY"
        if "on leave" in msg_lower:
            return "ON_LEAVE"
        return None

    def _extract_date_range(self, message: str) -> dict | None:
        """Extract start and end dates from a message."""
        import re
        dates = re.findall(r'\d{4}-\d{2}-\d{2}', message)
        if len(dates) >= 2:
            return {"start": dates[0], "end": dates[1]}
        if len(dates) == 1:
            # Single date - check for "from" context
            if "from" in message.lower() and "to" in message.lower():
                return {"start": dates[0], "end": dates[0]}
            return {"start": dates[0], "end": dates[0]}
        return None

    def _extract_leave_id(self, message: str) -> str | None:
        """Extract a leave request UUID from message."""
        import re
        uuid_match = re.search(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            message, re.IGNORECASE
        )
        if uuid_match:
            return uuid_match.group(0)
        return None

    def _handle_create_leave(self, message: str, msg_lower: str) -> str:
        """Handle 'create leave' intent by extracting parameters."""
        emp_id = self._extract_employee_id(message)
        if not emp_id:
            emp_id = self._extract_employee_id_from_text(message)

        if not emp_id:
            return (
                "I need to know which employee needs the leave. "
                "Please provide an employee ID or name. "
                "Example: 'Create a leave for John' or 'Create a leave for EMP-001'"
            )

        # Try to find leave type
        leave_type = self._extract_leave_type(msg_lower)

        # Try to extract dates
        dates = self._extract_date_range(message)
        today_str = self._get_today_str()

        if dates:
            start_date = dates.get("start", today_str)
            end_date = dates.get("end", today_str)
        else:
            # Check for "today" or "tomorrow"
            if "today" in msg_lower:
                start_date = today_str
                end_date = today_str
            elif "tomorrow" in msg_lower:
                start_date = self._get_tomorrow_str()
                end_date = self._get_tomorrow_str()
            else:
                return (
                    f"I found employee {emp_id}. Please specify the dates. "
                    "Example: 'Create a leave for EMP-001 from 2024-01-01 to 2024-01-03'"
                )

        # If we have a leave type, try to get its ID
        leave_type_id = None
        if leave_type:
            try:
                result = json.loads(self.tools.list_leave_types())
                for lt in result.get("leave_types", []):
                    if leave_type.lower() in lt.get("name", "").lower():
                        leave_type_id = lt["id"]
                        break
            except Exception:
                pass

        if not leave_type_id:
            # Try to get first available leave type
            try:
                result = json.loads(self.tools.list_leave_types())
                types = result.get("leave_types", [])
                if types:
                    leave_type_id = types[0]["id"]
                    leave_type = types[0]["name"]
                else:
                    return "No leave types are configured in the system. Please contact an administrator."
            except Exception as e:
                return f"Could not retrieve leave types: {str(e)}"

        reason = self._extract_reason(message)
        return self._safe_execute(
            "create_leave_request",
            employee_id=emp_id,
            leave_type_id=leave_type_id,
            start_date=start_date,
            end_date=end_date,
            reason=reason or f"Leave requested via AI assistant",
        )

    def _handle_create_employee(self, message: str, msg_lower: str) -> str:
        """Handle 'create employee' intent by extracting parameters."""
        # Extract name from message (case-insensitive, tolerant of punctuation)
        import re
        name_match = re.search(
            r"(?:name\s+(?:is\s+)?)?([A-Za-z][\w'-]+)\s+([A-Za-z][\w'-]+)",
            message,
            re.IGNORECASE,
        )

        first_name = ""
        last_name = ""
        if name_match:
            first_name = name_match.group(1).capitalize()
            last_name = name_match.group(2).capitalize()
        else:
            # Try to extract single name after keywords
            single_name = re.search(r"(?:for|called|named)\s+([A-Za-z][\w'-]+)", message, re.IGNORECASE)
            if single_name:
                first_name = single_name.group(1).capitalize()

        # Fallback: try to grab first two name-like tokens before the email segment
        if not first_name or not last_name:
            email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.+-]+', message)
            name_zone = message
            if email_match:
                name_zone = message[: email_match.start()]

            tokens = [t for t in re.split(r"[^A-Za-z]+", name_zone) if t]
            stop = {
                "create", "employee", "add", "new", "a", "an", "the", "for",
                "as", "with", "email", "named", "name", "is", "please", "hire",
                "kindly", "role", "and", "in", "to",
            }
            name_like = [t for t in tokens if t.lower() not in stop]
            if len(name_like) >= 2:
                first_name = first_name or name_like[0].capitalize()
                last_name = last_name or name_like[1].capitalize()
            elif len(name_like) == 1:
                first_name = first_name or name_like[0].capitalize()

        if not first_name:
            return (
                "I need the employee's name to create them. "
                "Please provide details like:\n"
                '- "Create employee named John Doe"\n'
                '- "Add a new employee with name Jane Smith"\n\n'
                "I also need their email, department, and designation. "
                "You can provide all details at once, e.g.:\n"
                '- "Create employee John Doe, john@example.com, Engineering, Developer"'
            )

        # Try to extract email
        email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.+-]+', message)
        email = email_match.group(0) if email_match else ""

        # Try to extract department name
        dept_name = ""
        dept_id = ""
        try:
            depts_result = json.loads(self.tools.list_departments())
            for dept in depts_result.get("departments", []):
                if dept.get("name", "").lower() in msg_lower:
                    dept_name = dept.get("name", "")
                    dept_id = dept.get("id", "")
                    break
        except Exception:
            pass

        # Try to extract designation
        desig_name = ""
        desig_id = ""
        try:
            desigs_result = json.loads(self.tools.list_designations())
            for desig in desigs_result.get("designations", []):
                if desig.get("title", "").lower() in msg_lower:
                    desig_name = desig.get("title", "")
                    desig_id = desig.get("id", "")
                    break
        except Exception:
            pass

        # If we have all required info, try to create
        if email and dept_id and desig_id:
            return self._safe_execute(
                "create_employee",
                first_name=first_name,
                last_name=last_name,
                email=email,
                department_id=dept_id,
                designation_id=desig_id,
            )

        # Build helpful response with what we have and what's missing
        missing = []
        if not email:
            missing.append("email address")
        if not dept_id:
            missing.append("department")
        if not desig_id:
            missing.append("designation")

        info_parts = [f"**Name:** {first_name} {last_name}"]
        if email:
            info_parts.append(f"**Email:** {email}")
        if dept_name:
            info_parts.append(f"**Department:** {dept_name}")
        if desig_name:
            info_parts.append(f"**Designation:** {desig_name}")

        return (
            f"I found the following details:\n"
            f"{' | '.join(info_parts)}\n\n"
            f"I'm still missing: {', '.join(missing)}.\n\n"
            f"Please provide the missing information. For example:\n"
            f'- "Create employee {first_name} {last_name}, email@example.com, Department, Designation"'
        )

    def _extract_leave_type(self, msg_lower: str) -> str | None:
        """Extract leave type from message."""
        leave_types = [
            "annual", "sick", "personal", "casual", "maternity",
            "paternity", "bereavement", "study", "unpaid", "emergency",
            "vacation", "medical", "family", "marriage", "compensatory",
            "comp off", "privilege", "earned"
        ]
        for lt in leave_types:
            if lt in msg_lower:
                return lt
        return None

    def _extract_reason(self, message: str) -> str:
        """Extract reason from message after 'for' or 'because'."""
        import re
        # Look for reason after "for", "because", "reason"
        patterns = [
            r'(?:because|reason is|reason:)\s*(.+?)(?:\.|$)',
            r'(?:for|due to)\s+(.+?)(?:\.|$)',
        ]
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _safe_execute(self, func_name: str, **kwargs) -> str:
        """Safely execute an HRMS tool function and format the result."""
        try:
            result_json = self.tools.execute(func_name, **kwargs)
            result = json.loads(result_json)

            # Check for errors
            if "error" in result:
                return f"❌ {result['error']}"

            # Format the result nicely
            return self._format_result(func_name, result)
        except Exception as e:
            logger.error("LocalIntentParser error executing %s: %s", func_name, str(e), exc_info=True)
            return f"❌ Sorry, I encountered an error while processing your request: {str(e)}"

    def _format_result(self, func_name: str, result: dict) -> str:
        """Format the result of a tool execution into a nice response."""
        # Dashboard summary
        if func_name == "get_dashboard_summary":
            att = result.get("today_attendance", {})
            return (
                f"📊 **Dashboard Summary**\n\n"
                f"👥 **Employees:** {result.get('total_employees', 0)} total, "
                f"{result.get('active_employees', 0)} active\n"
                f"🏢 **Departments:** {result.get('departments', 0)}\n"
                f"✅ **Today's Attendance:** "
                f"Present: {att.get('present', 0)}, "
                f"Absent: {att.get('absent', 0)}, "
                f"Late: {att.get('late', 0)}, "
                f"Half Day: {att.get('half_day', 0)}, "
                f"On Leave: {att.get('on_leave', 0)}\n"
                f"⏳ **Pending Leaves:** {result.get('pending_leaves', 0)}\n"
                f"💰 **Current Month Payroll:** ${result.get('current_month_payroll', 0):,.2f}"
            )

        # Employee count
        if func_name == "get_employee_count":
            return f"👥 Total employees: **{result.get('total_employees', 0)}**"

        if func_name == "get_active_employee_count":
            return f"👥 Active employees: **{result.get('active_employees', 0)}**"

        # Employee list
        if func_name == "list_employees":
            employees = result.get("employees", [])
            if not employees:
                return "No employees found matching your criteria."
            lines = [f"👥 **Employees ({result.get('total', 0)} found):**\n"]
            for emp in employees:
                lines.append(
                    f"• **{emp.get('name', 'N/A')}** ({emp.get('employee_id', 'N/A')}) - "
                    f"{emp.get('department', 'N/A')} - {emp.get('status', 'N/A')}"
                )
            return "\n".join(lines)

        # Employee details
        if func_name == "get_employee_details":
            return (
                f"👤 **Employee Details:**\n\n"
                f"**Name:** {result.get('name', 'N/A')}\n"
                f"**ID:** {result.get('employee_id', 'N/A')}\n"
                f"**Email:** {result.get('email', 'N/A')}\n"
                f"**Phone:** {result.get('phone', 'N/A')}\n"
                f"**Department:** {result.get('department', 'N/A')}\n"
                f"**Designation:** {result.get('designation', 'N/A')}\n"
                f"**Status:** {result.get('status', 'N/A')}\n"
                f"**Type:** {result.get('type', 'N/A')}\n"
                f"**Joining Date:** {result.get('joining_date', 'N/A')}\n"
                f"**Reporting To:** {result.get('reporting_to', 'N/A')}"
            )

        # Departments
        if func_name == "list_departments":
            depts = result.get("departments", [])
            if not depts:
                return "No departments found."
            lines = [f"🏢 **Departments ({result.get('total', 0)}):**\n"]
            for d in depts:
                lines.append(
                    f"• **{d.get('name', 'N/A')}** ({d.get('code', 'N/A')}) - "
                    f"{d.get('employee_count', 0)} employees"
                )
            return "\n".join(lines)

        if func_name == "get_department_report":
            depts = result.get("departments", [])
            if not depts:
                return "No departments found."
            lines = [f"📋 **Department Report:**\n"]
            for d in depts:
                lines.append(
                    f"• **{d.get('name', 'N/A')}**: "
                    f"{d.get('active_employees', 0)} active / "
                    f"{d.get('total_employees', 0)} total"
                )
            return "\n".join(lines)

        # Attendance
        if func_name == "get_attendance_summary":
            return (
                f"✅ **Attendance Summary for {result.get('date', 'N/A')}:**\n\n"
                f"📊 Total Records: {result.get('total_records', 0)}\n"
                f"🟢 Present: {result.get('present', 0)}\n"
                f"🔴 Absent: {result.get('absent', 0)}\n"
                f"🟡 Late: {result.get('late', 0)}\n"
                f"🟠 Half Day: {result.get('half_day', 0)}\n"
                f"🔵 On Leave: {result.get('on_leave', 0)}"
            )

        if func_name == "mark_attendance":
            return (
                f"✅ Attendance marked successfully!\n"
                f"**Employee:** {result.get('employee', 'N/A')}\n"
                f"**Date:** {result.get('date', 'N/A')}\n"
                f"**Status:** {result.get('status', 'N/A')}\n"
                f"**Action:** {result.get('action', 'updated')}"
            )

        if func_name == "mark_attendance_date_range":
            return f"✅ {result.get('message', 'Attendance marked successfully.')}"

        if func_name == "mark_attendance_bulk":
            return f"✅ {result.get('message', 'Attendance marked successfully.')}"

        # Leaves
        if func_name == "list_leave_types":
            types = result.get("leave_types", [])
            if not types:
                return "No leave types configured."
            lines = [f"🏖️ **Available Leave Types:**\n"]
            for lt in types:
                lines.append(
                    f"• **{lt.get('name', 'N/A')}** - "
                    f"{lt.get('days_per_year', 0)} days/year"
                )
            return "\n".join(lines)

        if func_name == "get_leave_balance":
            balances = result.get("leave_balances", {})
            if not balances:
                return "No leave balances found."
            lines = [f"🏖️ **Leave Balances:**\n"]
            for emp_name, allocs in balances.items():
                lines.append(f"**{emp_name}:**")
                for a in allocs:
                    lines.append(
                        f"  • {a.get('leave_type', 'N/A')}: "
                        f"{a.get('remaining', 0)}/{a.get('total_days', 0)} days remaining"
                    )
            return "\n".join(lines)

        if func_name == "list_leave_requests":
            requests = result.get("leave_requests", [])
            if not requests:
                return "No leave requests found."
            lines = [f"🏖️ **Leave Requests ({result.get('total', 0)}):**\n"]
            for lr in requests:
                lines.append(
                    f"• **{lr.get('employee', 'N/A')}** - {lr.get('leave_type', 'N/A')}\n"
                    f"  {lr.get('start_date', 'N/A')} to {lr.get('end_date', 'N/A')} "
                    f"({lr.get('total_days', 0)} days) - **{lr.get('status', 'N/A')}**"
                )
            return "\n".join(lines)

        if func_name == "create_leave_request":
            return (
                f"✅ Leave request created successfully!\n"
                f"**Employee:** {result.get('message', '').replace('Leave request created for ', '')}\n"
                f"**Status:** {result.get('status', 'PENDING')}"
            )

        if func_name == "approve_leave_request":
            return f"✅ {result.get('message', 'Leave request approved.')}"

        if func_name == "approve_leave_by_employee_name":
            if "error" in result:
                return f"❌ {result.get('error', 'Could not approve leave.')}"
            msg = (
                f"✅ **{result.get('message', 'Leave request approved.')}**\n\n"
                f"**Employee:** {result.get('employee', 'N/A')}\n"
                f"**Leave Type:** {result.get('leave_type', 'N/A')}\n"
                f"**From:** {result.get('start_date', 'N/A')}\n"
                f"**To:** {result.get('end_date', 'N/A')}\n"
                f"**Total Days:** {result.get('total_days', 0)}\n"
            )
            if result.get('notified_employee'):
                msg += "\n✅ Employee has been notified."
            if result.get('notified_manager'):
                msg += "\n✅ Manager has been notified."
            return msg

        if func_name == "reject_leave_request":
            return f"✅ {result.get('message', 'Leave request rejected.')}"

        # Payroll
        if func_name == "get_payroll_summary":
            return (
                f"💰 **Payroll Summary - {result.get('month', 'N/A')}/{result.get('year', 'N/A')}:**\n\n"
                f"👥 Employees: {result.get('total_employees', 0)}\n"
                f"💵 Total Basic Salary: ${result.get('total_basic_salary', 0):,.2f}\n"
                f"📈 Total Earnings: ${result.get('total_earnings', 0):,.2f}\n"
                f"📉 Total Deductions: ${result.get('total_deductions', 0):,.2f}\n"
                f"🏦 Total Net Pay: ${result.get('total_net_pay', 0):,.2f}\n"
                f"📊 Average Net Pay: ${result.get('average_net_pay', 0):,.2f}"
            )

        if func_name == "list_payroll":
            payrolls = result.get("payrolls", [])
            if not payrolls:
                return "No payroll records found."
            lines = [f"💰 **Payroll Records:**\n"]
            for p in payrolls:
                lines.append(
                    f"• **{p.get('employee', 'N/A')}** ({p.get('employee_id', 'N/A')}) - "
                    f"${p.get('net_pay', 0):,.2f} - {p.get('status', 'N/A')}"
                )
            return "\n".join(lines)

        # Performance
        if func_name == "list_performance_reviews":
            reviews = result.get("reviews", [])
            if not reviews:
                return "No performance reviews found."
            lines = [f"📊 **Performance Reviews:**\n"]
            for r in reviews:
                rating = r.get('overall_rating', 'N/A')
                lines.append(
                    f"• **{r.get('employee', 'N/A')}** - "
                    f"Rating: {rating}/5 - {r.get('status', 'N/A')}"
                )
            return "\n".join(lines)

        if func_name == "list_goals":
            goals = result.get("goals", [])
            if not goals:
                return "No goals found."
            lines = [f"🎯 **Goals:**\n"]
            for g in goals:
                lines.append(
                    f"• **{g.get('title', 'N/A')}** - "
                    f"{g.get('employee', 'N/A')} - "
                    f"{g.get('progress', 0)}% - {g.get('status', 'N/A')}"
                )
            return "\n".join(lines)

        # Holidays
        if func_name == "get_upcoming_holidays":
            holidays = result.get("upcoming_holidays", [])
            if not holidays:
                return "No upcoming holidays found."
            lines = [f"🎉 **Upcoming Holidays:**\n"]
            for h in holidays:
                lines.append(f"• **{h.get('name', 'N/A')}** - {h.get('date', 'N/A')}")
            return "\n".join(lines)

        # Attendance report
        if func_name == "get_attendance_report":
            breakdown = result.get("breakdown", {})
            lines = [
                f"📋 **Attendance Report**\n"
                f"📅 Period: {result.get('period', 'N/A')}\n"
                f"📊 Total Records: {result.get('total_records', 0)}\n"
            ]
            for status, count in breakdown.items():
                lines.append(f"  • {status}: {count}")
            return "\n".join(lines)

        # Generic fallback for any other function
        return json.dumps(result, indent=2)


# =============================================================================
# Singleton Getters
# =============================================================================

_deepseek_client_instance: DeepSeekClient | None = None
_rag_engine_instance: RAGEngine | None = None


def get_deepseek_client() -> DeepSeekClient:
    """Get or create the singleton DeepSeekClient instance."""
    global _deepseek_client_instance
    if _deepseek_client_instance is None:
        _deepseek_client_instance = DeepSeekClient()
    return _deepseek_client_instance


def get_rag_engine() -> RAGEngine:
    """Get or create the singleton RAGEngine instance."""
    global _rag_engine_instance
    if _rag_engine_instance is None:
        _rag_engine_instance = RAGEngine()
    return _rag_engine_instance


def get_hrms_tools(user) -> HRMSTools:
    """Create a new HRMSTools instance for the given user."""
    return HRMSTools(user)
