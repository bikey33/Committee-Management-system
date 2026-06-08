"""
Signals to auto-create ProcurementStakeholder entries when
users are added to committees (CommitteeMembership).
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CommitteeMembership
from procurement.models import ProcurementStakeholder

logger = logging.getLogger(__name__)

# Member appointment notifications (SMS + email) are dispatched explicitly from the
# create / add-member / role-change code paths via committee.notifications, not from a
# signal — see committee/notifications.py for the rationale.


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


@receiver(post_save, sender='committee.Committee')
def auto_create_phase_checkpoints(sender, instance, created, **kwargs):
    """
    Automatically create phase checkpoints when a committee is created.
    """
    if not created:
        return
    
    from .models import CommitteePhaseCheckpoint
    
    committee = instance
    
    # Default checkpoints for initialization phase
    init_checkpoints = [
        {
            'phase': 'initialization',
            'name': 'Committee Formation',
            'description': 'Committee has been properly formed with all members assigned',
            'order': 1
        },
        {
            'phase': 'initialization',
            'name': 'First Meeting',
            'description': 'Committee conducted its first official meeting',
            'order': 2
        },
        {
            'phase': 'initialization',
            'name': 'Specification Review',
            'description': 'Tender specifications have been reviewed and finalized',
            'order': 3
        }
    ]
    
    # Default checkpoints for finalization phase
    final_checkpoints = [
        {
            'phase': 'finalization',
            'name': 'Evaluation Complete',
            'description': 'Evaluation process has been completed',
            'order': 1
        },
        {
            'phase': 'finalization',
            'name': 'Report Generation',
            'description': 'Committee report has been generated',
            'order': 2
        },
        {
            'phase': 'finalization',
            'name': 'Final Approval',
            'description': 'Final recommendations have been approved',
            'order': 3
        }
    ]
    
    all_checkpoints = init_checkpoints + final_checkpoints
    
    for cp_data in all_checkpoints:
        CommitteePhaseCheckpoint.objects.get_or_create(
            committee=committee,
            phase=cp_data['phase'],
            order=cp_data['order'],
            defaults={
                'name': cp_data['name'],
                'description': cp_data['description'],
            }
        )
    
    logger.info(
        f"Auto-created {len(all_checkpoints)} checkpoints for committee '{committee.name}'"
    )
