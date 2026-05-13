"""
Signals to auto-create ProcurementStakeholder entries when
users are added to committees (CommitteeMembership).
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CommitteeMembership
from procurement.models import ProcurementStakeholder
from .tasks import send_committee_notification_task # Added

logger = logging.getLogger(__name__)

@receiver(post_save, sender=CommitteeMembership)
def notify_member_on_committee_join(sender, instance, created, **kwargs):
    """
    Disabled per user request to simplify the system and avoid Celery connection errors.
    """
    return


@receiver(post_save, sender=CommitteeMembership)
def auto_create_stakeholder_on_committee_join(sender, instance, created, **kwargs):
    """
    When a user is added to a committee that is linked to a procurement plan,
    automatically ensure they have a ProcurementStakeholder entry so they can
    see and interact with that plan.
    """
    if not created:
        return
    
    committee = instance.committee
    procurement_plan = committee.procurement_plan
    
    if not procurement_plan:
        logger.debug(
            f"Committee '{committee.name}' has no procurement plan; "
            f"skipping stakeholder creation for user {instance.user}"
        )
        return
    
    user = instance.user
    
    # Determine the stakeholder role based on committee role
    committee_role = instance.committee_role.lower() if instance.committee_role else 'member'
    if committee_role in ('chairperson', 'chair'):
        stakeholder_role = 'committee_chair'
    else:
        stakeholder_role = 'committee_member'
    
    # Check if user already has an active stakeholder entry for this plan + role
    existing = ProcurementStakeholder.objects.filter(
        procurement_plan=procurement_plan,
        user=user,
        role=stakeholder_role,
    ).first()
    
    if existing:
        # Reactivate if previously deactivated
        if existing.status != 'active':
            existing.status = 'active'
            existing.save(update_fields=['status'])
            logger.info(
                f"Reactivated stakeholder for {user} on plan "
                f"{procurement_plan.policy_number} (role: {stakeholder_role})"
            )
        return
    
    # Create new stakeholder entry
    ProcurementStakeholder.objects.create(
        procurement_plan=procurement_plan,
        user=user,
        role=stakeholder_role,
        involvement_level='primary',
        authority_level='comment',
        responsibilities=(
            f"Auto-assigned as {stakeholder_role} via committee "
            f"'{committee.name}' ({committee.get_committee_type_display()})"
        ),
        status='active',
    )
    
    logger.info(
        f"Auto-created stakeholder for {user} on plan "
        f"{procurement_plan.policy_number} (role: {stakeholder_role}, "
        f"committee: {committee.name})"
    )
