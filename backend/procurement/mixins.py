"""
Shared AccessControlMixin for consistent role-hierarchy-based filtering
across all procurement-related ViewSets.
"""
from django.db.models import Q



def get_procurement_plan_filter(user, action='view'):
    """
    Build the unified Q filter for procurement plan visibility and management.

    action: 'view' or 'manage'

    Two-layer permission model
    --------------------------
    Layer 1 — Route-level (checked by HasPermission in get_permissions):
        planning.view    → user may attempt to VIEW plans
        planning.manage  → user may attempt to MANAGE (edit/delete) plans

    Layer 2 — Record-level (this function): which specific plans they can act on.

    Record-level access rules (in order of precedence):
    1. Super Admin / Superuser  →  unrestricted access to all plans.

    2. action='view':
       - Has 'planning.view_cross_office'  →  can see ALL plans across all offices.
       - Otherwise                         →  restricted to own office (exact match),
                                              own plans (owner), or plans where an
                                              active stakeholder.

    3. action='manage':
       - Has 'planning.edit_cross_office_plan'  →  can manage ALL plans across all
                                                    offices (explicit cross-office grant).
       - Has 'planning.manage' only (implicit)  →  restricted to plans in their own
                                                    office (exact match), plans they
                                                    own, or plans where they are an
                                                    active stakeholder with manage/
                                                    full_control authority.

    NOTE: 'planning.view_cross_office' alone does NOT grant management access.
    """
    if not user or not user.is_authenticated:
        return Q(pk__isnull=True)
    
    # 1. Superuser or Super Admin bypass
    from users.utils import is_superadmin
    if getattr(user, 'is_superuser', False) or is_superadmin(user):
        return Q()

    # 2. HRBAC Cross-office permissions
    if action == 'manage':
        # edit_cross_office_plan is required on its own for system-wide management.
        # Having only view_cross_office does NOT grant management access.
        if user.has_rbac_permission('planning.edit_cross_office_plan'):
            return Q()
    else:
        # view_cross_office grants read-only visibility across all offices.
        if user.has_rbac_permission('planning.view_cross_office'):
            return Q()
    
    # Build combined filter for normal scoping
    filters = Q(owner=user)
    
    # 3. Stakeholder access
    if action == 'manage':
        # For managing, stakeholder must have management authority level
        filters |= Q(
            stakeholders__user=user, 
            stakeholders__status='active',
            stakeholders__authority_level__in=['manage', 'full_control']
        )
    else:
        # For viewing, any active stakeholder can see the plan
        filters |= Q(stakeholders__user=user, stakeholders__status='active')
    
    # 4. Office Hierarchy access (Subtree NOT required - exact office only)
    if getattr(user, 'office', None):
        filters |= Q(office=user.office)
    
    return filters


class AccessControlMixin:
    """
    Mixin that provides unified role-hierarchy-based queryset filtering.
    """
    
    procurement_plan_field = 'procurement_plan'
    
    def get_access_filter(self):
        """Get the Q filter for the current user's access level."""
        request = getattr(self, 'request', None)
        if not request or not request.user:
            return Q(pk__isnull=True)
            
        user = request.user
        action = 'manage' if getattr(self, 'action', None) in ['update', 'partial_update', 'destroy'] else 'view'
        plan_filter = get_procurement_plan_filter(user, action=action)
        
        if not self.procurement_plan_field:
            return plan_filter
        
        # Related model - prefix the filter with the FK field name
        prefixed_filter = Q()
        for child in plan_filter.children:
            if isinstance(child, Q):
                prefixed_child = Q()
                for grandchild in child.children:
                    if isinstance(grandchild, tuple):
                        key, value = grandchild
                        prefixed_child.children.append(
                            (f"{self.procurement_plan_field}__{key}", value)
                        )
                    elif isinstance(grandchild, Q):
                        prefixed_child.children.append(grandchild)
                prefixed_child.connector = child.connector
                prefixed_filter.children.append(prefixed_child)
            elif isinstance(child, tuple):
                key, value = child
                if key == 'pk__isnull':
                    prefixed_filter.children.append((key, value))
                else:
                    prefixed_filter.children.append(
                        (f"{self.procurement_plan_field}__{key}", value)
                    )
        prefixed_filter.connector = plan_filter.connector
        return prefixed_filter
    
    def get_filtered_queryset(self, base_queryset):
        """Apply access control filter to a base queryset."""
        request = getattr(self, 'request', None)
        if not request or not request.user or not request.user.is_authenticated:
            return base_queryset.none()
        
        user = request.user
        if getattr(user, 'is_superuser', False):
            return base_queryset
        
        action = 'manage' if getattr(self, 'action', None) in ['update', 'partial_update', 'destroy'] else 'view'
        plan_filter = get_procurement_plan_filter(user, action=action)
        
        if not self.procurement_plan_field:
            # If Q() is empty, filter() is no-op
            return base_queryset.filter(plan_filter).distinct()
        
        # For related models, prefix the filter keys
        return self._apply_prefixed_filter(base_queryset, plan_filter).distinct()
    
    def _apply_prefixed_filter(self, queryset, plan_filter):
        """Apply a plan filter with field prefix for related models."""
        prefix = self.procurement_plan_field
        user = self.request.user

        if not user or not user.is_authenticated:
            return queryset.none()

        if getattr(user, 'is_superuser', False):
            return queryset

        # If plan_filter is empty Q(), it means full system access was granted by get_procurement_plan_filter
        if not plan_filter:
            return queryset

        return queryset.filter(plan_filter)
