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


def _stakeholder_role_for(membership):
    role = (membership.committee_role or 'member').lower()
    return 'committee_chair' if role in ('chairperson', 'chair') else 'committee_member'


def ensure_stakeholder_for_membership(membership):
    """Ensure an active ProcurementStakeholder exists for this membership's user
    on the committee's procurement plan. Idempotent; reactivates if deactivated.
    Safe to call on a genuine join or a re-add."""
    committee = membership.committee
    procurement_plan = committee.procurement_plan
    if not procurement_plan:
        logger.debug(
            f"Committee '{committee.name}' has no procurement plan; "
            f"skipping stakeholder creation for user {membership.user}"
        )
        return

    user = membership.user
    stakeholder_role = _stakeholder_role_for(membership)

    existing = ProcurementStakeholder.objects.filter(
        procurement_plan=procurement_plan, user=user, role=stakeholder_role,
    ).first()

    if existing:
        if existing.status != 'active':
            existing.status = 'active'
            existing.save(update_fields=['status'])
            logger.info(
                f"Reactivated stakeholder for {user} on plan "
                f"{procurement_plan.policy_number} (role: {stakeholder_role})"
            )
        return

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
        f"{procurement_plan.policy_number} (role: {stakeholder_role}, committee: {committee.name})"
    )


def deactivate_stakeholder_for_membership(membership):
    """Deactivate the auto-created stakeholder when a member is removed, so a
    removed member loses procurement-plan visibility."""
    committee = membership.committee
    procurement_plan = committee.procurement_plan
    if not procurement_plan:
        return
    ProcurementStakeholder.objects.filter(
        procurement_plan=procurement_plan,
        user=membership.user,
        role=_stakeholder_role_for(membership),
    ).exclude(status='inactive').update(status='inactive')


@receiver(post_save, sender=CommitteeMembership)
def auto_create_stakeholder_on_committee_join(sender, instance, created, **kwargs):
    """On a genuine new membership, ensure the user has a stakeholder entry."""
    if not created:
        return
    ensure_stakeholder_for_membership(instance)


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
