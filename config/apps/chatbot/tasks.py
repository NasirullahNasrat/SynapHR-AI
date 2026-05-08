"""
Celery tasks for the Chatbot app.

Handles background operations like embedding synchronization.
"""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="sync_employee_embeddings")
def sync_employee_embeddings() -> dict:
    """
    Synchronize employee data embeddings for RAG.

    This task runs periodically to update embeddings for employee data
    so the chatbot can answer questions about employees.

    Returns:
        dict: Summary of the operation
    """
    from .models import DocumentEmbedding
    from .services import get_deepseek_client, get_rag_engine
    from config.apps.hrms.models import Employee

    ai_client = get_deepseek_client()
    rag_engine = get_rag_engine()

    if not ai_client.is_available:
        return {"status": "skipped", "reason": "AI service not available"}

    # Remove old employee embeddings
    DocumentEmbedding.objects.filter(document_type="EMPLOYEE").delete()

    employees = Employee.objects.select_related("user", "department", "designation").filter(
        employment_status__in=["ACTIVE", "PROBATION"]
    )

    created_count = 0
    for employee in employees:
        try:
            # Create employee profile text
            profile_text = (
                f"Employee: {employee.full_name}\n"
                f"Employee ID: {employee.employee_id}\n"
                f"Email: {employee.email}\n"
                f"Department: {employee.department.name if employee.department else 'N/A'}\n"
                f"Designation: {employee.designation.title if employee.designation else 'N/A'}\n"
                f"Employment Status: {employee.employment_status}\n"
                f"Employment Type: {employee.employment_type}\n"
                f"Joining Date: {employee.joining_date}\n"
                f"Skills: {', '.join(employee.skills) if employee.skills else 'N/A'}\n"
                f"Highest Education: {employee.highest_education or 'N/A'}\n"
            )

            # Chunk and embed
            chunks = rag_engine.chunk_text(profile_text, chunk_size=1000)
            for i, chunk in enumerate(chunks):
                embedding = ai_client.generate_embedding(chunk)
                DocumentEmbedding.objects.create(
                    document_type="EMPLOYEE",
                    content=chunk,
                    embedding=embedding,
                    metadata={
                        "employee_id": str(employee.id),
                        "employee_user_id": str(employee.user.id),
                        "department": employee.department.name if employee.department else None,
                    },
                    chunk_index=i,
                )
                created_count += 1

        except Exception as e:
            logger.error(
                "Failed to sync embedding for employee %s: %s",
                employee.full_name,
                str(e),
            )

    logger.info("Synced %d employee embeddings", created_count)
    return {
        "status": "success",
        "embeddings_created": created_count,
    }
