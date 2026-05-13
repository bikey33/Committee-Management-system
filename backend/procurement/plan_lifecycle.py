from django.db import transaction
from django.utils import timezone

from .models import (
    ActivityLog,
    ApprovalWorkflow,
    PlanTermination,
    ProcurementDocument,
)


def _count_and_update(queryset, **update_fields):
    """Count matching records and update them. Returns the count."""
    count = queryset.count()
    if count:
        queryset.update(**update_fields)
    return count


def _apply_cascading_effects(plan):
    """Apply cascading effects when a plan is terminated.

    Does NOT delete data — marks related records as dissolved/closed/withdrawn/etc.
    All data is preserved as read-only historical records.
    """
    effects = {}

    # 1. Committees: dissolve active ones
    try:
        from committee.models import Committee
        effects['committees_dissolved'] = _count_and_update(
            Committee.objects.filter(
                procurement_plan=plan
            ).exclude(status__in=['completed', 'dissolved']),
            status='dissolved',
        )
    except (ImportError, Exception):
        effects['committees_dissolved'] = 0

    # 2. Tenders: close published/open ones
    try:
        from tender.models import Tender
        effects['tenders_closed'] = _count_and_update(
            Tender.objects.filter(
                procurement_plan=plan,
                status__in=['published', 'open', 'draft'],
            ),
            status='closed',
        )
    except (ImportError, Exception):
        effects['tenders_closed'] = 0

    # 3. Active bids: withdraw
    try:
        from bidder.models import BidderDocument
        effects['bids_withdrawn'] = _count_and_update(
            BidderDocument.objects.filter(
                procurement_plan=plan,
            ).exclude(status__in=['withdrawn', 'rejected']),
            status='withdrawn',
        )
    except (ImportError, Exception):
        effects['bids_withdrawn'] = 0

    # 4. Pending approval workflows: withdraw
    effects['approvals_withdrawn'] = _count_and_update(
        ApprovalWorkflow.objects.filter(
            procurement_plan=plan,
            status__in=['pending', 'in_review', 'on_hold'],
        ),
        status='withdrawn',
    )

    return effects


def perform_plan_termination(plan, user, reason_category, reason, remarks='',
                              documents=None, ip_address=None, user_agent=None):
    """Terminate a procurement plan with cascading effects.

    Args:
        plan: ProcurementPlan instance
        user: User performing the termination
        reason_category: One of PlanTermination.REASON_CATEGORIES
        reason: Detailed reason text
        remarks: Optional additional remarks
        documents: List of uploaded file objects (at least 1 required)
        ip_address: Request IP address for audit
        user_agent: Request user agent for audit

    Returns:
        dict with termination details and cascading effects summary

    Raises:
        ValueError: If plan cannot be terminated or validation fails
    """
    if plan.status == 'cancelled':
        raise ValueError("This plan has already been terminated.")
    if plan.status == 'completed':
        raise ValueError("Completed plans cannot be terminated.")
    if not reason or not reason.strip():
        raise ValueError("A termination reason is required.")
    if not reason_category:
        raise ValueError("A reason category is required.")
    if not documents:
        raise ValueError("At least one supporting document is required.")

    valid_categories = [c[0] for c in PlanTermination.REASON_CATEGORIES]
    if reason_category not in valid_categories:
        raise ValueError(f"Invalid reason category: {reason_category}")

    with transaction.atomic():
        old_status = plan.status
        old_stage = plan.stage

        # Apply cascading effects
        cascading_effects = _apply_cascading_effects(plan)

        # Update plan status
        plan.status = 'cancelled'
        plan.save(update_fields=['status'])

        # Create termination record
        termination = PlanTermination.objects.create(
            procurement_plan=plan,
            reason_category=reason_category,
            reason=reason.strip(),
            remarks=remarks.strip() if remarks else '',
            stage_at_termination=old_stage,
            terminated_by=user,
            cascading_effects=cascading_effects,
        )

        # Save termination documents
        saved_docs = []
        for doc_file in documents:
            doc = ProcurementDocument.objects.create(
                procurement_plan=plan,
                title=f"Termination Document - {doc_file.name}",
                document_type='termination_document',
                file=doc_file,
                file_name=doc_file.name,
                file_size=doc_file.size,
                uploaded_by=user,
                status='approved',
                access_level='internal',
                custom_metadata={'termination_id': termination.id},
            )
            saved_docs.append(doc.id)

        # Log activity
        ActivityLog.log_activity(
            procurement_plan=plan,
            action='plan_terminated',
            user=user,
            description=f"Procurement plan {plan.policy_number} terminated: {termination.get_reason_category_display()}",
            details={
                'reason_category': reason_category,
                'reason': reason.strip(),
                'remarks': remarks.strip() if remarks else '',
                'stage_at_termination': old_stage,
                'cascading_effects': cascading_effects,
                'document_ids': saved_docs,
            },
            related_object=termination,
            severity='critical',
            old_values={'status': old_status, 'stage': old_stage},
            new_values={'status': 'cancelled'},
            ip_address=ip_address,
            user_agent=user_agent or '',
        )

    return {
        'termination_id': termination.id,
        'old_status': old_status,
        'stage_at_termination': old_stage,
        'cascading_effects': cascading_effects,
        'documents_saved': len(saved_docs),
    }
