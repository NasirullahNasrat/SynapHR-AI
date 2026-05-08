"""
Signal handlers for the HRMS app.

Handles automatic notifications and updates when HRMS models change.
Integrates with the RuleEngine for automated workflow actions.
"""

from __future__ import annotations

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from config.apps.hrms.automation import RuleEngine
from config.apps.hrms.models import (
    Attendance,
    Employee,
    LeaveRequest,
    Notification,
    Payroll,
    PerformanceReview,
)

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=LeaveRequest)
def handle_leave_request_status_change(
    sender, instance: LeaveRequest, **kwargs
) -> None:
    """
    Track leave request status changes for notification.

    When a leave request status changes, this signal captures the old status
    so the post_save handler can send appropriate notifications.
    """
    if instance.pk:
        try:
            old_instance = LeaveRequest.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except LeaveRequest.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=LeaveRequest)
def notify_leave_request_update(sender, instance: LeaveRequest, created: bool, **kwargs) -> None:
    """
    Send notifications when leave requests are created or updated.

    Creates notifications for:
    - New leave requests (notify the manager/reporting_to)
    - Approved leave requests (notify the employee)
    - Rejected leave requests (notify the employee)
    """
    try:
        if created:
            # Notify the reporting manager about new leave request
            if instance.employee.reporting_to:
                Notification.objects.create(
                    recipient=instance.employee.reporting_to.user,
                    notification_type=Notification.NotificationType.LEAVE_REQUEST,
                    title=f"Leave Request from {instance.employee.full_name}",
                    message=(
                        f"{instance.employee.full_name} has requested "
                        f"{instance.total_days} day(s) of {instance.leave_type.name} "
                        f"from {instance.start_date} to {instance.end_date}."
                    ),
                    link=f"/hr/leave-requests/{instance.id}",
                    metadata={
                        "leave_request_id": str(instance.id),
                        "employee_id": str(instance.employee.id),
                        "status": instance.status,
                    },
                )
        else:
            old_status = getattr(instance, "_old_status", None)
            if old_status and old_status != instance.status:
                if instance.status == LeaveRequest.LeaveStatus.APPROVED:
                    Notification.objects.create(
                        recipient=instance.employee.user,
                        notification_type=Notification.NotificationType.LEAVE_APPROVED,
                        title="Leave Request Approved",
                        message=(
                            f"Your {instance.leave_type.name} request "
                            f"({instance.start_date} to {instance.end_date}) "
                            f"has been approved."
                        ),
                        link=f"/hr/leave-requests/{instance.id}",
                        metadata={
                            "leave_request_id": str(instance.id),
                            "status": instance.status,
                        },
                    )
                elif instance.status == LeaveRequest.LeaveStatus.REJECTED:
                    reason = instance.rejection_reason or "No reason provided"
                    Notification.objects.create(
                        recipient=instance.employee.user,
                        notification_type=Notification.NotificationType.LEAVE_REJECTED,
                        title="Leave Request Rejected",
                        message=(
                            f"Your {instance.leave_type.name} request "
                            f"({instance.start_date} to {instance.end_date}) "
                            f"has been rejected. Reason: {reason}"
                        ),
                        link=f"/hr/leave-requests/{instance.id}",
                        metadata={
                            "leave_request_id": str(instance.id),
                            "status": instance.status,
                            "reason": reason,
                        },
                    )
    except Exception as e:
        logger.error("Failed to send leave request notification: %s", str(e))

    # Evaluate automation rules for LEAVE_REQUESTED / LEAVE_APPROVED / LEAVE_REJECTED
    try:
        if created:
            RuleEngine.evaluate("LEAVE_REQUESTED", {"instance": instance})
        else:
            old_status = getattr(instance, "_old_status", None)
            if old_status and old_status != instance.status:
                if instance.status == LeaveRequest.LeaveStatus.APPROVED:
                    RuleEngine.evaluate("LEAVE_APPROVED", {"instance": instance})
                elif instance.status == LeaveRequest.LeaveStatus.REJECTED:
                    RuleEngine.evaluate("LEAVE_REJECTED", {"instance": instance})
    except Exception as e:
        logger.error("Failed to evaluate leave automation rules: %s", str(e))


@receiver(post_save, sender=Payroll)
def notify_payroll_update(sender, instance: Payroll, created: bool, **kwargs) -> None:
    """
    Send notification when payroll is processed.
    """
    try:
        if instance.status == Payroll.PayrollStatus.PAID and not created:
            Notification.objects.create(
                recipient=instance.employee.user,
                notification_type=Notification.NotificationType.PAYROLL,
                title="Salary Credited",
                message=(
                    f"Your salary for {instance.get_month_display()} {instance.year} "
                    f"has been credited. Net pay: ${instance.net_pay}"
                ),
                link=f"/hr/payroll/{instance.id}",
                metadata={
                    "payroll_id": str(instance.id),
                    "month": instance.month,
                    "year": instance.year,
                    "net_pay": str(instance.net_pay),
                },
            )
    except Exception as e:
        logger.error("Failed to send payroll notification: %s", str(e))

    # Evaluate automation rules for PAYROLL_PROCESSED
    try:
        if instance.status == Payroll.PayrollStatus.PAID:
            RuleEngine.evaluate("PAYROLL_PROCESSED", {"instance": instance})
    except Exception as e:
        logger.error("Failed to evaluate payroll automation rules: %s", str(e))


@receiver(post_save, sender=Employee)
def handle_employee_created(sender, instance: Employee, created: bool, **kwargs) -> None:
    """Evaluate automation rules when an employee is created."""
    if created:
        try:
            RuleEngine.evaluate("EMPLOYEE_CREATED", {"instance": instance})
        except Exception as e:
            logger.error("Failed to evaluate employee automation rules: %s", str(e))


@receiver(post_save, sender=Attendance)
def handle_attendance_marked(sender, instance: Attendance, created: bool, **kwargs) -> None:
    """Evaluate automation rules when attendance is marked."""
    if created:
        try:
            RuleEngine.evaluate("ATTENDANCE_MARKED", {"instance": instance})
        except Exception as e:
            logger.error("Failed to evaluate attendance automation rules: %s", str(e))


@receiver(post_save, sender=PerformanceReview)
def handle_review_submitted(sender, instance: PerformanceReview, created: bool, **kwargs) -> None:
    """Evaluate automation rules when a performance review is submitted."""
    if created:
        try:
            RuleEngine.evaluate("REVIEW_SUBMITTED", {"instance": instance})
        except Exception as e:
            logger.error("Failed to evaluate review automation rules: %s", str(e))
