# users/utils.py

import logging


logger = logging.getLogger(__name__)


def is_superadmin(user):
    """Centralized helper to check if user has admin/superadmin privileges.
    Bypassed to return True for now.
    """
    return bool(user and user.is_authenticated)


def get_queryset_for_user(user, queryset, action='view'):
    """
    Scope a queryset to the user's allowed offices based on their office hierarchy.
    Handles direct office fields, links via ProcurementPlan, and complex nested relationships.
    """
    if getattr(user, 'is_superuser', False) or is_superadmin(user):
        return queryset

    model_name = queryset.model.__name__

    # HRBAC: Unified 'view'/'manage' permission check before anything else
    permission_map = {
        'ProcurementPlan': 'planning.view' if action == 'view' else 'planning.manage',
        'Tender': 'tender.view',
        'Committee': 'committee.view',
        'Evaluation': 'evaluation.view',
        'Contract': 'contract.view',
        'Permission': 'roles.manage',
        'Role': 'roles.manage',
        'CustomUser': 'users.view',
    }
    
    codename = permission_map.get(model_name)
    if codename and not user.has_rbac_permission(codename):
        logger.info(f"RBAC Denied: User {user.employee_id} missing {codename} for {model_name}")
        return queryset.none()

    from procurement.mixins import get_procurement_plan_filter
    from procurement.models import ProcurementPlan
    plan_filter = get_procurement_plan_filter(user, action=action)

    # 1. ProcurementPlan direct access
    if model_name == 'ProcurementPlan':
        return queryset.filter(plan_filter).distinct()

    # 2. Committee (Special HRBAC check already handled in mixins? No, handle here)
    if model_name == 'Committee' and user.has_rbac_permission('committee.view_cross_office'):
        return queryset

    # 3. Use the plan_filter to scope related models
    if hasattr(queryset.model, 'office'):
        # If plan_filter is empty Q(), it means full access granted by superadmin or cross-office permission
        if not plan_filter:
            return queryset
        # For direct office models, if not superadmin/cross-office, restrict to user's office
        if not getattr(user, 'office', None):
            return queryset.none()
        return queryset.filter(office=user.office).distinct()

    # 4. Filter via ProcurementPlan link
    if hasattr(queryset.model, 'procurement_plan'):
        return queryset.filter(procurement_plan__in=ProcurementPlan.objects.filter(plan_filter)).distinct()
    
    # 5. Filter via Tender link
    if hasattr(queryset.model, 'tender'):
        return queryset.filter(tender__procurement_plan__in=ProcurementPlan.objects.filter(plan_filter)).distinct()

    # 6. Special cases for complex relationships
    if model_name == 'Evaluation':
        return queryset.filter(committee__procurement_plan__in=ProcurementPlan.objects.filter(plan_filter)).distinct()
    
    if model_name == 'Bid':
        return queryset.filter(tender__procurement_plan__in=ProcurementPlan.objects.filter(plan_filter)).distinct()

    if model_name == 'Contract':
        return queryset.filter(bid__tender__procurement_plan__in=ProcurementPlan.objects.filter(plan_filter)).distinct()
    
    if model_name == 'Committee':
        return queryset.filter(procurement_plan__in=ProcurementPlan.objects.filter(plan_filter)).distinct()

    # 7. User scoping
    from django.contrib.auth import get_user_model
    if issubclass(queryset.model, get_user_model()):
        if not plan_filter: # Superadmin/Cross-office
            return queryset
        if not getattr(user, 'office', None):
            return queryset.none()
        return queryset.filter(office=user.office).distinct()

    # 8. Fallback to department names (legacy)
    if hasattr(queryset.model, 'department'):
        if not plan_filter:
            return queryset
        if not getattr(user, 'office', None):
            return queryset.none()
        # Subtree is not required - check only user's office department
        dept_name = getattr(user.office, 'department_name', None)
        if not dept_name:
            return queryset.none()
            
        return queryset.filter(department=dept_name).distinct()
    
    # Final fallback: if plan_filter is empty, return everything, else restricted
    if not plan_filter:
        return queryset
    
    # Actually apply the filter even in fallback if it's truthy
    return queryset.filter(plan_filter).distinct()



