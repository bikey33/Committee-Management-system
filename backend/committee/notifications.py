"""
Committee membership notifications.

A user is notified (SMS + email) when they are appointed to a committee — on
initial committee creation, when added via the Add-Member action, and when their
role changes during an edit. Dispatch is explicit (called from the create/update/
add-member code paths) rather than signal-based, because notifications must fire
for genuine additions and role changes but NOT for members silently re-added while
a committee is being edited.

Reuses the existing delivery stack: committee.tasks.send_committee_notification_task
(SMS via utils.sms_sender + email via utils.email_sender).
"""
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError

from .models import CommitteeRole
from .tasks import send_committee_notification_task

logger = logging.getLogger(__name__)


def _resolve_profile(user):
    """Return the user's EmployeeDetail, or None.

    The reverse OneToOne raises ObjectDoesNotExist (not AttributeError) when no
    profile exists, so getattr(..., None) would not catch it.
    """
    try:
        return user.employee_profile
    except ObjectDoesNotExist:
        return None


def _resolve_phone(profile):
    if not profile:
        return None
    return (profile.phone or profile.mno or '').strip() or None


def _resolve_name(user, profile):
    if profile and profile.name:
        return profile.name
    full = f"{user.first_name} {user.last_name}".strip()
    return full or user.username


def _resolve_role_label(role_value):
    if not role_value:
        return 'Member'
    try:
        role = CommitteeRole.objects.filter(value__iexact=role_value).first()
        if role:
            return role.label
    except (ProgrammingError, OperationalError):
        pass
    return role_value.replace('_', ' ').title()


def notify_committee_membership(membership):
    """Send the appointment notification (SMS + email) for one membership.

    Resolves all data defensively and dispatches the Celery task only after the
    surrounding transaction commits, so a rolled-back create/edit never sends.
    No-ops (with a log line) when the member has no phone on file.
    """
    user = membership.user
    profile = _resolve_profile(user)

    phone = _resolve_phone(profile)
    if not phone:
        logger.warning(
            f"No phone for user {user} (membership {membership.pk}); "
            f"skipping committee notification"
        )
        return

    committee = membership.committee
    plan = committee.procurement_plan

    name = _resolve_name(user, profile)
    role = _resolve_role_label(membership.committee_role)
    committee_type = committee.get_committee_type_display()
    committee_name = committee.name
    policy_number = plan.policy_number if plan else "N/A"
    project_name = plan.project_name if plan else committee_name
    email = user.email or None

    transaction.on_commit(lambda: send_committee_notification_task.delay(
        phone_number=phone,
        name=name,
        role=role,
        policy_number=policy_number,
        project_name=project_name,
        committee_type=committee_type,
        email=email,
        committee_name=committee_name,
        file_path=None,
    ))
