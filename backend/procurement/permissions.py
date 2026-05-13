from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Q
from datetime import datetime, timedelta
from users.models import CustomUser
from .models import (
    ProcurementPlan, 
    ProcurementDocument, 
    ProcurementStakeholder,
    ProcurementRisk,
    ActivityLog,
    Timeline
)
import logging

logger = logging.getLogger(__name__)


class BaseProcurementPermission(permissions.BasePermission):
    """
    Base permission class for procurement module with role hierarchy support
    """
    
    def has_permission(self, request, view):
        """Check if user has basic access to procurement module"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check for user account status
        if not self.is_user_active_and_valid(request.user):
            return False
        
        # Superusers have full access
        if request.user.is_superuser:
            return True
            
        # Must have a role assigned
        if not getattr(request.user, 'user_role', None):
            return False
        
        # Check for emergency maintenance mode
        if self.is_emergency_maintenance_mode() and not self.has_emergency_override(request.user):
            return False
            
        return True
    
    def is_user_active_and_valid(self, user):
        """Check if user account is active and valid"""
        if not user or not user.is_authenticated:
            return False
            
        # Check if user is active
        if not user.is_active:
            logger.warning(f"Inactive user attempted access: {user.username}")
            return False
            
        # Check if user has been deactivated recently
        cache_key = f"user_deactivated_{user.pk}"
        if cache.get(cache_key):
            return False
            
        # Check for temporary suspension
        suspension_key = f"user_suspended_{user.pk}"
        suspension_data = cache.get(suspension_key)
        if suspension_data:
            suspension_until = datetime.fromisoformat(suspension_data['until'])
            if timezone.now() < suspension_until:
                return False
                
        return True
    
    def is_emergency_maintenance_mode(self):
        """Check if system is in emergency maintenance mode"""
        return cache.get('emergency_maintenance_mode', False)
    
    def has_emergency_override(self, user):
        """Check if user has emergency override permissions"""
        if not user or not getattr(user, 'user_role', None):
            return False
            
        # Only specific roles can override emergency maintenance
        emergency_roles = ['admin', 'system_admin', 'emergency_coordinator']
        user_role_hierarchy = user.user_role.get_hierarchy() if getattr(user, 'user_role', None) else []
        return any(role in user_role_hierarchy for role in emergency_roles)
    
    def check_time_based_access(self, user, procurement_plan):
        """Check if user has time-based access restrictions"""
        if not user or not procurement_plan:
            return True
            
        # Check business hours restrictions
        if self.has_business_hours_restriction(user):
            current_time = timezone.now().time()
            if not (timezone.time(8, 0) <= current_time <= timezone.time(18, 0)):
                return False
        
        # Check stage-specific time restrictions
        stage_restrictions = self.get_stage_time_restrictions(procurement_plan.stage)
        if stage_restrictions:
            return self.check_stage_time_access(user, stage_restrictions)
            
        return True
    
    def has_business_hours_restriction(self, user):
        """Check if user has business hours restrictions"""
        if not user or not getattr(user, 'user_role', None):
            return False
            
        # Some roles are restricted to business hours only
        restricted_roles = ['committee_member', 'evaluator', 'reviewer']
        user_role_hierarchy = user.user_role.get_hierarchy() if getattr(user, 'user_role', None) else []
        return any(role in user_role_hierarchy for role in restricted_roles)
    
    def get_stage_time_restrictions(self, stage):
        """Get time restrictions for specific procurement stages"""
        # Define stages that have time restrictions
        stage_restrictions = {
            'bidding': {
                'freeze_period_hours': 24,  # No changes 24 hours before deadline
                'business_hours_only': True
            },
            'evaluation': {
                'secure_hours_only': True,  # Only during secure hours
                'minimum_evaluators': 2     # Minimum evaluators required
            },
            'contract': {
                'approval_hours': (9, 17),  # Only during approval hours
                'weekend_restriction': True
            }
        }
        return stage_restrictions.get(stage, {})
    
    def check_stage_time_access(self, user, restrictions):
        """Check access based on stage-specific time restrictions"""
        current_time = timezone.now()
        
        # Check business hours restriction
        if restrictions.get('business_hours_only'):
            if not (8 <= current_time.hour <= 18):
                return False
        
        # Check approval hours
        if 'approval_hours' in restrictions:
            start_hour, end_hour = restrictions['approval_hours']
            if not (start_hour <= current_time.hour <= end_hour):
                return False
        
        # Check weekend restriction
        if restrictions.get('weekend_restriction'):
            if current_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
                return False
                
        return True
    
    def check_delegation_permissions(self, user, procurement_plan, delegated_by=None):
        """Check if user has delegated permissions"""
        if not delegated_by:
            return False
            
        # Check if delegation is valid
        delegation_key = f"delegation_{delegated_by.pk}_{user.pk}"
        delegation_data = cache.get(delegation_key)
        
        if not delegation_data:
            return False
            
        # Check delegation validity period
        valid_until = datetime.fromisoformat(delegation_data['valid_until'])
        if timezone.now() > valid_until:
            cache.delete(delegation_key)
            return False
            
        # Check if delegation covers this procurement
        if procurement_plan.pk not in delegation_data.get('procurement_plans', []):
            return False
            
        # Check delegated permissions
        delegated_permissions = delegation_data.get('permissions', [])
        return len(delegated_permissions) > 0
    
    def check_cross_department_access(self, user, procurement_plan):
        """Check cross-department access permissions"""
        if not user or not procurement_plan:
            return False
            
        # Same department - allow access
        if user.department == procurement_plan.department:
            return True
            
        # Check if user has cross-department permissions
        cross_dept_roles = ['admin', 'director', 'manager', 'audit_officer']
        user_role_hierarchy = user.user_role.get_hierarchy() if getattr(user, 'user_role', None) else []
        if any(role in user_role_hierarchy for role in cross_dept_roles):
            return True
            
        # Check specific cross-department assignments
        cross_dept_key = f"cross_dept_access_{user.pk}"
        cross_dept_data = cache.get(cross_dept_key, {})
        allowed_departments = cross_dept_data.get('departments', [])
        
        return procurement_plan.department in allowed_departments
    
    def check_geographical_restrictions(self, user, procurement_plan):
        """Check geographical access restrictions"""
        if not hasattr(user, 'location') or not hasattr(procurement_plan, 'location'):
            return True  # No restriction if location not defined
            
        # Check if user location matches procurement location
        if user.location == procurement_plan.location:
            return True
            
        # Check if user has multi-location access
        multi_location_roles = ['admin', 'regional_manager', 'director']
        user_role_hierarchy = user.user_role.get_hierarchy() if getattr(user, 'user_role', None) else []
        return any(role in user_role_hierarchy for role in multi_location_roles)
    
    def check_data_sensitivity_access(self, user, sensitivity_level):
        """Check access based on data sensitivity levels"""
        if not user or not sensitivity_level:
            return True
            
        user_clearance_level = getattr(user, 'security_clearance', 'basic')
        
        # Define sensitivity hierarchy
        sensitivity_hierarchy = {
            'public': 0,
            'internal': 1,
            'confidential': 2,
            'restricted': 3,
            'classified': 4,
            'top_secret': 5
        }
        
        clearance_hierarchy = {
            'basic': 1,
            'standard': 2,
            'elevated': 3,
            'high': 4,
            'maximum': 5
        }
        
        required_level = sensitivity_hierarchy.get(sensitivity_level, 0)
        user_level = clearance_hierarchy.get(user_clearance_level, 0)
        
        return user_level >= required_level
    
    def check_compliance_requirements(self, user, procurement_plan, action):
        """Check compliance requirements for specific actions"""
        if not user or not procurement_plan:
            return True
            
        # Get compliance rules for the procurement type
        compliance_rules = self.get_compliance_rules(procurement_plan)
        
        # Check if action requires compliance validation
        if action in compliance_rules.get('restricted_actions', []):
            return self.validate_compliance_requirements(user, compliance_rules)
            
        return True
    
    def get_compliance_rules(self, procurement_plan):
        """Get compliance rules based on procurement characteristics"""
        rules = {
            'restricted_actions': [],
            'required_approvals': [],
            'audit_requirements': []
        }
        
        # High-value procurements have stricter rules
        if procurement_plan.estimated_cost > 1000000:  # $1M threshold
            rules['restricted_actions'].extend(['delete', 'stage_revert'])
            rules['required_approvals'].append('financial_controller')
        
        # Critical procurements require additional oversight
        if procurement_plan.priority == 'urgent':
            rules['audit_requirements'].append('real_time_monitoring')
            
        return rules
    
    def validate_compliance_requirements(self, user, compliance_rules):
        """Validate that user meets compliance requirements"""
        # Check required approvals
        for required_role in compliance_rules.get('required_approvals', []):
            if not self.user_has_role_access(user, required_role):
                return False
                
        # Check audit requirements
        audit_requirements = compliance_rules.get('audit_requirements', [])
        if 'real_time_monitoring' in audit_requirements:
            # Log the action for real-time monitoring
            self.log_compliance_action(user, 'high_priority_access')
            
        return True
    
    def user_has_role_access(self, user, required_role):
        """Check if user has access to required role functionality"""
        if not user or not getattr(user, 'user_role', None):
            return False
            
        user_role_hierarchy = user.user_role.get_hierarchy()
        return required_role in user_role_hierarchy
    
    def log_compliance_action(self, user, action_type):
        """Log compliance-related actions"""
        logger.info(f"Compliance action: {action_type} by user {user.username}")
        
        # Store in cache for real-time monitoring
        monitoring_key = f"compliance_monitoring_{timezone.now().strftime('%Y%m%d')}"
        monitoring_data = cache.get(monitoring_key, [])
        monitoring_data.append({
            'user': user.username,
            'action': action_type,
            'timestamp': timezone.now().isoformat(),
            'ip_address': getattr(user, 'last_ip', 'unknown')
        })
        cache.set(monitoring_key, monitoring_data, 86400)  # 24 hours
    
    def check_integration_permissions(self, user, integration_type):
        """Check permissions for external system integrations"""
        if not user or not integration_type:
            return False
            
        # Define integration access roles
        integration_roles = {
            'financial_system': ['financial_officer', 'admin', 'manager'],
            'vendor_portal': ['procurement_officer', 'vendor_liaison', 'admin'],
            'audit_system': ['audit_officer', 'compliance_officer', 'admin'],
            'reporting_system': ['manager', 'director', 'admin', 'analyst']
        }
        
        allowed_roles = integration_roles.get(integration_type, [])
        if not allowed_roles:
            return False
            
        user_role_hierarchy = user.user_role.get_hierarchy() if getattr(user, 'user_role', None) else []
        return any(role in user_role_hierarchy for role in allowed_roles)
    
    def get_user_allowed_roles(self, user):
        """Get all roles within user's hierarchy tree"""
        if not user or not getattr(user, 'user_role', None):
            return []
        return [user.user_role] + user.user_role.get_all_descendants()
    
    def is_procurement_owner_or_superior(self, user, procurement_plan):
        """Check if user is owner or in superior role in hierarchy"""
        if not user or not procurement_plan:
            return False
            
        # Direct owner
        if procurement_plan.owner == user:
            return True
            
        # Check hierarchy - user can access if procurement owner is in their subtree
        user_allowed_roles = self.get_user_allowed_roles(user)
        return procurement_plan.owner.user_role in user_allowed_roles


class ProcurementPlanPermission(BaseProcurementPermission):
    """
    Permission class for ProcurementPlan operations
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
            
        # Allow list/create for authenticated users with procurement role
        if view.action in ['list', 'create']:
            return self.has_procurement_access(request.user)
            
        return True
    
    def has_object_permission(self, request, view, obj):
        """Object-level permissions for procurement plans"""
        user = request.user
        
        # Superusers have full access
        if user.is_superuser:
            return True
        
        # Check basic access
        if not self.has_procurement_access(user):
            return False
        
        # Read permissions
        if view.action in ['retrieve', 'list']:
            return self.can_view_procurement_plan(user, obj)
        
        # Write permissions  
        if view.action in ['update', 'partial_update']:
            return self.can_edit_procurement_plan(user, obj)
        
        # Delete permissions
        if view.action == 'destroy':
            return self.can_delete_procurement_plan(user, obj)
        
        # Custom actions
        if view.action in ['advance_stage', 'revert_stage']:
            return self.can_manage_procurement_stage(user, obj)
            
        return False
    
    def has_procurement_access(self, user):
        """Check if user has basic procurement access"""
        if not user or not getattr(user, 'user_role', None):
            return False
            
        # Define roles that can access procurement
        procurement_roles = [
            'procurement_officer', 'project_manager', 'admin', 
            'committee_member', 'evaluator', 'manager', 'director'
        ]
        
        # Check user's role and hierarchy
        user_role_hierarchy = user.user_role.get_hierarchy()
        return any(role in user_role_hierarchy for role in procurement_roles)
    
    def can_view_procurement_plan(self, user, procurement_plan):
        """Check if user can view procurement plan"""
        # Owner or superior in hierarchy
        if self.is_procurement_owner_or_superior(user, procurement_plan):
            return True
            
        # Stakeholder with any authority level
        if self.is_procurement_stakeholder(user, procurement_plan):
            return True
            
        # Department members can view plans in their department
        if user.department == procurement_plan.department:
            return True
            
        return False
    
    def can_edit_procurement_plan(self, user, procurement_plan):
        """Check if user can edit procurement plan"""
        # Owner or superior in hierarchy
        if self.is_procurement_owner_or_superior(user, procurement_plan):
            return True
            
        # Stakeholder with management authority
        stakeholder = self.get_user_stakeholder_role(user, procurement_plan)
        if stakeholder and stakeholder.authority_level in ['manage', 'full_control']:
            return True
            
        return False
    
    def can_delete_procurement_plan(self, user, procurement_plan):
        """Check if user can delete procurement plan"""
        # Only owner or full control stakeholders
        if procurement_plan.owner == user:
            return True
            
        stakeholder = self.get_user_stakeholder_role(user, procurement_plan)
        return stakeholder and stakeholder.authority_level == 'full_control'
    
    def can_manage_procurement_stage(self, user, procurement_plan):
        """Check if user can advance/revert procurement stages"""
        # Owner or superior in hierarchy
        if self.is_procurement_owner_or_superior(user, procurement_plan):
            return True
            
        # Stakeholder with management authority
        stakeholder = self.get_user_stakeholder_role(user, procurement_plan)
        return stakeholder and stakeholder.authority_level in ['manage', 'full_control']
    
    def is_procurement_stakeholder(self, user, procurement_plan):
        """Check if user is a stakeholder in the procurement"""
        return ProcurementStakeholder.objects.filter(
            procurement_plan=procurement_plan,
            user=user,
            status='active'
        ).exists()
    
    def get_user_stakeholder_role(self, user, procurement_plan):
        """Get user's stakeholder role in procurement"""
        try:
            return ProcurementStakeholder.objects.get(
                procurement_plan=procurement_plan,
                user=user,
                status='active'
            )
        except ProcurementStakeholder.DoesNotExist:
            return None


class ProcurementDocumentPermission(BaseProcurementPermission):
    """
    Permission class for ProcurementDocument operations with access level support
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        # Allow list for authenticated users
        if view.action == 'list':
            return True
            
        # Create requires procurement access
        if view.action == 'create':
            return self.has_document_upload_access(request.user)
            
        return True
    
    def has_object_permission(self, request, view, obj):
        """Object-level permissions for documents"""
        user = request.user
        
        # Use document's built-in access control
        if view.action in ['retrieve', 'download']:
            return self.can_access_document(user, obj)
        
        # Edit permissions
        if view.action in ['update', 'partial_update']:
            return self.can_edit_document(user, obj)
        
        # Delete permissions
        if view.action == 'destroy':
            return self.can_delete_document(user, obj)
        
        # Approval actions
        if view.action in ['approve', 'reject']:
            return self.can_approve_document(user, obj)
            
        return False
    
    def can_access_document(self, user, document):
        """Check if user can access document based on access levels"""
        # Use document's built-in access control method
        if document.can_access(user):
            return True
        
        # Additional checks for procurement context
        # Procurement owner and stakeholders with appropriate authority
        if self.is_procurement_owner_or_superior(user, document.procurement_plan):
            return True
            
        stakeholder = self.get_user_stakeholder_role(user, document.procurement_plan)
        if stakeholder and stakeholder.authority_level in ['view_only', 'comment', 'approve', 'manage', 'full_control']:
            # Check if document access level allows stakeholder access
            if document.access_level in ['public', 'internal']:
                return True
            elif document.access_level == 'restricted' and stakeholder.authority_level in ['approve', 'manage', 'full_control']:
                return True
        
        return False
    
    def can_edit_document(self, user, document):
        """Check if user can edit document"""
        # Document uploader
        if document.uploaded_by == user:
            return True
            
        # Procurement owner or superior
        if self.is_procurement_owner_or_superior(user, document.procurement_plan):
            return True
            
        # Stakeholder with management authority
        stakeholder = self.get_user_stakeholder_role(user, document.procurement_plan)
        return stakeholder and stakeholder.authority_level in ['manage', 'full_control']
    
    def can_delete_document(self, user, document):
        """Check if user can delete document"""
        # Document uploader (if document is in draft status)
        if document.uploaded_by == user and document.status == 'draft':
            return True
            
        # Procurement owner
        if document.procurement_plan.owner == user:
            return True
            
        # Stakeholder with full control
        stakeholder = self.get_user_stakeholder_role(user, document.procurement_plan)
        return stakeholder and stakeholder.authority_level == 'full_control'
    
    def can_approve_document(self, user, document):
        """Check if user can approve/reject document"""
        # Check if user is in allowed approvers
        if document.allowed_users.filter(pk=user.pk).exists():
            return True
            
        # Stakeholder with approval authority
        stakeholder = self.get_user_stakeholder_role(user, document.procurement_plan)
        return stakeholder and stakeholder.can_approve_documents()
    
    def has_document_upload_access(self, user):
        """Check if user can upload documents"""
        if not user or not getattr(user, 'user_role', None):
            return False
            
        # Define roles that can upload documents
        upload_roles = [
            'procurement_officer', 'project_manager', 'admin',
            'committee_member', 'technical_lead', 'manager'
        ]
        
        user_role_hierarchy = user.user_role.get_hierarchy()
        return any(role in user_role_hierarchy for role in upload_roles)
    
    def get_user_stakeholder_role(self, user, procurement_plan):
        """Get user's stakeholder role in procurement"""
        try:
            return ProcurementStakeholder.objects.get(
                procurement_plan=procurement_plan,
                user=user,
                status='active'
            )
        except ProcurementStakeholder.DoesNotExist:
            return None


class ProcurementStakeholderPermission(BaseProcurementPermission):
    """
    Permission class for ProcurementStakeholder operations
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
            
        # List/create requires stakeholder management access
        if view.action in ['list', 'create']:
            return self.has_stakeholder_management_access(request.user)
            
        return True
    
    def has_object_permission(self, request, view, obj):
        """Object-level permissions for stakeholders"""
        user = request.user
        
        # View permissions
        if view.action in ['retrieve', 'list']:
            return self.can_view_stakeholder(user, obj)
        
        # Edit permissions
        if view.action in ['update', 'partial_update']:
            return self.can_edit_stakeholder(user, obj)
        
        # Delete permissions
        if view.action == 'destroy':
            return self.can_remove_stakeholder(user, obj)
            
        return False
    
    def can_view_stakeholder(self, user, stakeholder):
        """Check if user can view stakeholder information"""
        # Procurement owner or superior
        if self.is_procurement_owner_or_superior(user, stakeholder.procurement_plan):
            return True
            
        # User viewing their own stakeholder record
        if stakeholder.user == user:
            return True
            
        # Other stakeholders with appropriate authority
        user_stakeholder = self.get_user_stakeholder_role(user, stakeholder.procurement_plan)
        return user_stakeholder and user_stakeholder.authority_level in ['manage', 'full_control']
    
    def can_edit_stakeholder(self, user, stakeholder):
        """Check if user can edit stakeholder"""
        # Procurement owner or superior
        if self.is_procurement_owner_or_superior(user, stakeholder.procurement_plan):
            return True
            
        # Stakeholder with full control
        user_stakeholder = self.get_user_stakeholder_role(user, stakeholder.procurement_plan)
        return user_stakeholder and user_stakeholder.authority_level == 'full_control'
    
    def can_remove_stakeholder(self, user, stakeholder):
        """Check if user can remove stakeholder"""
        # Cannot remove procurement owner
        if stakeholder.user == stakeholder.procurement_plan.owner:
            return False
            
        # Procurement owner or superior
        if self.is_procurement_owner_or_superior(user, stakeholder.procurement_plan):
            return True
            
        # Stakeholder with full control (but not themselves)
        user_stakeholder = self.get_user_stakeholder_role(user, stakeholder.procurement_plan)
        return (user_stakeholder and 
                user_stakeholder.authority_level == 'full_control' and 
                stakeholder.user != user)
    
    def has_stakeholder_management_access(self, user):
        """Check if user can manage stakeholders"""
        if not user or not getattr(user, 'user_role', None):
            return False
            
        management_roles = [
            'procurement_officer', 'project_manager', 'admin', 'manager', 'director'
        ]
        
        user_role_hierarchy = user.user_role.get_hierarchy()
        return any(role in user_role_hierarchy for role in management_roles)
    
    def get_user_stakeholder_role(self, user, procurement_plan):
        """Get user's stakeholder role in procurement"""
        try:
            return ProcurementStakeholder.objects.get(
                procurement_plan=procurement_plan,
                user=user,
                status='active'
            )
        except ProcurementStakeholder.DoesNotExist:
            return None


class ProcurementRiskPermission(BaseProcurementPermission):
    """
    Permission class for ProcurementRisk operations
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
            
        # Allow list/create for stakeholders
        if view.action in ['list', 'create']:
            return True
            
        return True
    
    def has_object_permission(self, request, view, obj):
        """Object-level permissions for risks"""
        user = request.user
        
        # View permissions
        if view.action in ['retrieve', 'list']:
            return self.can_view_risk(user, obj)
        
        # Edit permissions
        if view.action in ['update', 'partial_update']:
            return self.can_edit_risk(user, obj)
        
        # Delete permissions
        if view.action == 'destroy':
            return self.can_delete_risk(user, obj)
            
        return False
    
    def can_view_risk(self, user, risk):
        """Check if user can view risk"""
        # Procurement owner or superior
        if self.is_procurement_owner_or_superior(user, risk.procurement_plan):
            return True
            
        # Risk owner
        if risk.owner == user:
            return True
            
        # Stakeholder
        return self.is_procurement_stakeholder(user, risk.procurement_plan)
    
    def can_edit_risk(self, user, risk):
        """Check if user can edit risk"""
        # Risk owner
        if risk.owner == user:
            return True
            
        # Procurement owner or superior
        if self.is_procurement_owner_or_superior(user, risk.procurement_plan):
            return True
            
        # Stakeholder with management authority
        stakeholder = self.get_user_stakeholder_role(user, risk.procurement_plan)
        return stakeholder and stakeholder.authority_level in ['manage', 'full_control']
    
    def can_delete_risk(self, user, risk):
        """Check if user can delete risk"""
        # Risk owner (if risk is not yet mitigated)
        if risk.owner == user and risk.status in ['identified', 'active']:
            return True
            
        # Procurement owner
        if risk.procurement_plan.owner == user:
            return True
            
        # Stakeholder with full control
        stakeholder = self.get_user_stakeholder_role(user, risk.procurement_plan)
        return stakeholder and stakeholder.authority_level == 'full_control'
    
    def is_procurement_stakeholder(self, user, procurement_plan):
        """Check if user is a stakeholder in the procurement"""
        return ProcurementStakeholder.objects.filter(
            procurement_plan=procurement_plan,
            user=user,
            status='active'
        ).exists()
    
    def get_user_stakeholder_role(self, user, procurement_plan):
        """Get user's stakeholder role in procurement"""
        try:
            return ProcurementStakeholder.objects.get(
                procurement_plan=procurement_plan,
                user=user,
                status='active'
            )
        except ProcurementStakeholder.DoesNotExist:
            return None


class TimelinePermission(BaseProcurementPermission):
    """
    Permission class for Timeline operations
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
            
        # Allow list for stakeholders
        if view.action == 'list':
            return True
            
        # Create/edit requires management access
        if view.action in ['create', 'update', 'partial_update']:
            return self.has_timeline_management_access(request.user)
            
        return True
    
    def has_object_permission(self, request, view, obj):
        """Object-level permissions for timelines"""
        user = request.user
        
        # View permissions
        if view.action in ['retrieve', 'list']:
            return self.can_view_timeline(user, obj)
        
        # Edit permissions
        if view.action in ['update', 'partial_update']:
            return self.can_edit_timeline(user, obj)
        
        # Delete permissions
        if view.action == 'destroy':
            return self.can_delete_timeline(user, obj)
            
        return False
    
    def can_view_timeline(self, user, timeline):
        """Check if user can view timeline"""
        # Procurement owner or superior
        if self.is_procurement_owner_or_superior(user, timeline.procurement_plan):
            return True
            
        # Stakeholder
        return self.is_procurement_stakeholder(user, timeline.procurement_plan)
    
    def can_edit_timeline(self, user, timeline):
        """Check if user can edit timeline"""
        # Procurement owner or superior
        if self.is_procurement_owner_or_superior(user, timeline.procurement_plan):
            return True
            
        # Stakeholder with management authority
        stakeholder = self.get_user_stakeholder_role(user, timeline.procurement_plan)
        return stakeholder and stakeholder.authority_level in ['manage', 'full_control']
    
    def can_delete_timeline(self, user, timeline):
        """Check if user can delete timeline"""
        # Only allow deletion of non-auto-calculated timelines
        if timeline.auto_calculated:
            return False
            
        # Procurement owner
        if timeline.procurement_plan.owner == user:
            return True
            
        # Stakeholder with full control
        stakeholder = self.get_user_stakeholder_role(user, timeline.procurement_plan)
        return stakeholder and stakeholder.authority_level == 'full_control'
    
    def has_timeline_management_access(self, user):
        """Check if user can manage timelines"""
        if not user or not getattr(user, 'user_role', None):
            return False
            
        management_roles = [
            'procurement_officer', 'project_manager', 'admin', 'manager'
        ]
        
        user_role_hierarchy = user.user_role.get_hierarchy() if getattr(user, 'user_role', None) else []
        return any(role in user_role_hierarchy for role in management_roles)
    
    def is_procurement_stakeholder(self, user, procurement_plan):
        """Check if user is a stakeholder in the procurement"""
        return ProcurementStakeholder.objects.filter(
            procurement_plan=procurement_plan,
            user=user,
            status='active'
        ).exists()
    
    def get_user_stakeholder_role(self, user, procurement_plan):
        """Get user's stakeholder role in procurement"""
        try:
            return ProcurementStakeholder.objects.get(
                procurement_plan=procurement_plan,
                user=user,
                status='active'
            )
        except ProcurementStakeholder.DoesNotExist:
            return None


class ActivityLogPermission(BaseProcurementPermission):
    """
    Permission class for ActivityLog - mostly read-only
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
            
        # Only allow list and retrieve (activity logs are created by system)
        if view.action in ['list', 'retrieve']:
            return True
            
        # No manual creation/editing of activity logs
        return False
    
    def has_object_permission(self, request, view, obj):
        """Object-level permissions for activity logs"""
        user = request.user
        
        # View permissions only
        if view.action in ['retrieve', 'list']:
            return self.can_view_activity_log(user, obj)
            
        return False
    
    def can_view_activity_log(self, user, activity_log):
        """Check if user can view activity log"""
        # Procurement owner or superior
        if self.is_procurement_owner_or_superior(user, activity_log.procurement_plan):
            return True
            
        # User viewing their own activities
        if activity_log.user == user:
            return True
            
        # Stakeholder with appropriate authority
        stakeholder = self.get_user_stakeholder_role(user, activity_log.procurement_plan)
        return stakeholder and stakeholder.authority_level in ['manage', 'full_control']
    
    def get_user_stakeholder_role(self, user, procurement_plan):
        """Get user's stakeholder role in procurement"""
        try:
            return ProcurementStakeholder.objects.get(
                procurement_plan=procurement_plan,
                user=user,
                status='active'
            )
        except ProcurementStakeholder.DoesNotExist:
            return None


# Convenience permission classes for common use cases
class IsProcurementOwnerOrSuperior(BaseProcurementPermission):
    """
    Permission that allows access only to procurement owners or their superiors in hierarchy
    """
    
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'procurement_plan'):
            procurement_plan = obj.procurement_plan
        elif hasattr(obj, 'owner'):
            procurement_plan = obj
        else:
            return False
            
        return self.is_procurement_owner_or_superior(request.user, procurement_plan)


class IsProcurementStakeholder(BaseProcurementPermission):
    """
    Permission that allows access only to procurement stakeholders
    """
    
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'procurement_plan'):
            procurement_plan = obj.procurement_plan
        elif hasattr(obj, 'owner'):
            procurement_plan = obj
        else:
            return False
            
        return ProcurementStakeholder.objects.filter(
            procurement_plan=procurement_plan,
            user=request.user,
            status='active'
        ).exists()


class HasStakeholderAuthority(BaseProcurementPermission):
    """
    Permission that checks stakeholder authority level
    """
    
    def __init__(self, required_authority_levels=None):
        self.required_authority_levels = required_authority_levels or ['manage', 'full_control']
    
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'procurement_plan'):
            procurement_plan = obj.procurement_plan
        elif hasattr(obj, 'owner'):
            procurement_plan = obj
        else:
            return False
        
        try:
            stakeholder = ProcurementStakeholder.objects.get(
                procurement_plan=procurement_plan,
                user=request.user,
                status='active'
            )
            return stakeholder.authority_level in self.required_authority_levels
        except ProcurementStakeholder.DoesNotExist:
            return False


# Permission helper functions
def check_procurement_access(user, procurement_plan, action='view'):
    """
    Helper function to check procurement access for different actions
    
    Args:
        user: User object
        procurement_plan: ProcurementPlan object
        action: 'view', 'edit', 'delete', 'manage'
    
    Returns:
        bool: True if user has permission
    """
    if not user or not user.is_authenticated or not procurement_plan:
        return False
    
    # Superuser has all access
    if user.is_superuser:
        return True
    
    permission = ProcurementPlanPermission()
    
    if action == 'view':
        return permission.can_view_procurement_plan(user, procurement_plan)
    elif action == 'edit':
        return permission.can_edit_procurement_plan(user, procurement_plan)
    elif action == 'delete':
        return permission.can_delete_procurement_plan(user, procurement_plan)
    elif action == 'manage':
        return permission.can_manage_procurement_stage(user, procurement_plan)
    
    return False


def check_document_access(user, document, action='view'):
    """
    Helper function to check document access for different actions
    
    Args:
        user: User object
        document: ProcurementDocument object
        action: 'view', 'edit', 'delete', 'approve'
    
    Returns:
        bool: True if user has permission
    """
    if not user or not user.is_authenticated or not document:
        return False
    
    # Superuser has all access
    if user.is_superuser:
        return True
    
    permission = ProcurementDocumentPermission()
    
    if action == 'view':
        return permission.can_access_document(user, document)
    elif action == 'edit':
        return permission.can_edit_document(user, document)
    elif action == 'delete':
        return permission.can_delete_document(user, document)
    elif action == 'approve':
        return permission.can_approve_document(user, document)
    
    return False


# Advanced permission classes for edge cases

class TemporaryAccessPermission(BaseProcurementPermission):
    """
    Permission class for temporary access scenarios
    """
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        if hasattr(obj, 'procurement_plan'):
            procurement_plan = obj.procurement_plan
        elif hasattr(obj, 'owner'):
            procurement_plan = obj
        else:
            return False
        
        # Check for temporary access grants
        temp_access_key = f"temp_access_{user.pk}_{procurement_plan.pk}"
        temp_access_data = cache.get(temp_access_key)
        
        if not temp_access_data:
            return False
        
        # Check if temporary access is still valid
        valid_until = datetime.fromisoformat(temp_access_data['valid_until'])
        if timezone.now() > valid_until:
            cache.delete(temp_access_key)
            return False
        
        # Check if action is allowed
        allowed_actions = temp_access_data.get('allowed_actions', [])
        return view.action in allowed_actions


class ReadOnlyModePermission(BaseProcurementPermission):
    """
    Permission class for read-only mode during critical operations
    """
    
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'procurement_plan'):
            procurement_plan = obj.procurement_plan
        elif hasattr(obj, 'owner'):
            procurement_plan = obj
        else:
            return False
        
        # Check if procurement is in read-only mode
        readonly_key = f"readonly_mode_{procurement_plan.pk}"
        readonly_data = cache.get(readonly_key)
        
        if readonly_data:
            # Only allow read operations
            if view.action in ['list', 'retrieve']:
                return True
            
            # Check for emergency override
            if self.has_emergency_override(request.user):
                return True
                
            return False
        
        return True


class MultiRolePermission(BaseProcurementPermission):
    """
    Permission class for users with multiple roles in same procurement
    """
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        if hasattr(obj, 'procurement_plan'):
            procurement_plan = obj.procurement_plan
        elif hasattr(obj, 'owner'):
            procurement_plan = obj
        else:
            return False
        
        # Get all stakeholder roles for this user in this procurement
        user_stakeholder_roles = ProcurementStakeholder.objects.filter(
            procurement_plan=procurement_plan,
            user=user,
            status='active'
        )
        
        if not user_stakeholder_roles.exists():
            return False
        
        # Check permissions based on highest authority level
        max_authority = max(
            stakeholder.authority_level for stakeholder in user_stakeholder_roles
        )
        
        authority_hierarchy = {
            'view_only': 1,
            'comment': 2,
            'approve': 3,
            'manage': 4,
            'full_control': 5
        }
        
        required_level = self.get_required_authority_level(view.action)
        user_level = authority_hierarchy.get(max_authority, 0)
        
        return user_level >= required_level
    
    def get_required_authority_level(self, action):
        """Get required authority level for action"""
        action_requirements = {
            'retrieve': 1,      # view_only
            'list': 1,          # view_only
            'update': 4,        # manage
            'partial_update': 4, # manage
            'destroy': 5,       # full_control
            'approve': 3,       # approve
            'reject': 3,        # approve
        }
        return action_requirements.get(action, 1)


class EscalationPermission(BaseProcurementPermission):
    """
    Permission class for escalation scenarios
    """
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        if hasattr(obj, 'procurement_plan'):
            procurement_plan = obj.procurement_plan
        elif hasattr(obj, 'owner'):
            procurement_plan = obj
        else:
            return False
        
        # Check if this is an escalation scenario
        escalation_key = f"escalation_{procurement_plan.pk}"
        escalation_data = cache.get(escalation_key)
        
        if not escalation_data:
            return False
        
        # Check if user is authorized for escalation
        authorized_escalation_roles = [
            'director', 'manager', 'admin', 'compliance_officer'
        ]
        
        user_role_hierarchy = user.user_role.get_hierarchy() if getattr(user, 'user_role', None) else []
        if not any(role in user_role_hierarchy for role in authorized_escalation_roles):
            return False
        
        # Log escalation access
        logger.warning(f"Escalation access granted to {user.username} for procurement {procurement_plan.policy_number}")
        
        return True


class VendorLimitedAccessPermission(BaseProcurementPermission):
    """
    Permission class for external vendor/partner access
    """
    
    def has_permission(self, request, view):
        user = request.user
        
        # Check if user has vendor role
        if not getattr(user, 'user_role', None):
            return False
        
        vendor_roles = ['vendor', 'external_partner', 'contractor']
        user_role_hierarchy = user.user_role.get_hierarchy()
        
        return any(role in user_role_hierarchy for role in vendor_roles)
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        if hasattr(obj, 'procurement_plan'):
            procurement_plan = obj.procurement_plan
        elif hasattr(obj, 'owner'):
            procurement_plan = obj
        else:
            return False
        
        # Vendors can only access procurements they're invited to
        vendor_access_key = f"vendor_access_{user.pk}_{procurement_plan.pk}"
        vendor_access_data = cache.get(vendor_access_key)
        
        if not vendor_access_data:
            return False
        
        # Check access validity
        valid_until = datetime.fromisoformat(vendor_access_data['valid_until'])
        if timezone.now() > valid_until:
            return False
        
        # Vendors have limited actions
        allowed_actions = ['retrieve', 'list']
        if view.action not in allowed_actions:
            return False
        
        # Check document access level for vendors
        if hasattr(obj, 'access_level'):
            if obj.access_level in ['restricted', 'confidential', 'classified']:
                return False
        
        return True


class AuditTrailProtectionPermission(BaseProcurementPermission):
    """
    Permission class to protect audit trail integrity
    """
    
    def has_object_permission(self, request, view, obj):
        # Activity logs cannot be modified or deleted
        if isinstance(obj, ActivityLog):
            if view.action in ['update', 'partial_update', 'destroy']:
                # Only system administrators can manage activity logs in emergency
                if not (request.user.is_superuser or self.has_emergency_override(request.user)):
                    logger.critical(f"Attempted audit log modification by {request.user.username}")
                    return False
        
        return True


class ComplianceAuditPermission(BaseProcurementPermission):
    """
    Permission class for compliance and audit operations
    """
    
    def has_permission(self, request, view):
        user = request.user
        
        # Check if user has audit/compliance roles
        audit_roles = ['audit_officer', 'compliance_officer', 'legal_advisor', 'admin']
        user_role_hierarchy = user.user_role.get_hierarchy() if getattr(user, 'user_role', None) else []
        
        return any(role in user_role_hierarchy for role in audit_roles)
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Audit officers have broad read access but limited write access
        if view.action in ['retrieve', 'list']:
            return True
        
        # Write operations require specific authorization
        if view.action in ['update', 'partial_update']:
            # Only for compliance corrections
            compliance_key = f"compliance_correction_{user.pk}"
            return cache.get(compliance_key, False)
        
        return False


class HistoricalDataPermission(BaseProcurementPermission):
    """
    Permission class for accessing historical/archived data
    """
    
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'procurement_plan'):
            procurement_plan = obj.procurement_plan
        elif hasattr(obj, 'status'):
            # For completed procurements
            if obj.status != 'completed':
                return True  # Use normal permissions for active procurements
            procurement_plan = obj
        else:
            return False
        
        # Check if procurement is completed/archived
        if procurement_plan.status == 'completed':
            # Limited access to historical data
            if view.action in ['retrieve', 'list']:
                # Check if user has historical data access
                return self.has_historical_access(request.user, procurement_plan)
            else:
                # No modifications to completed procurements
                return False
        
        return True
    
    def has_historical_access(self, user, procurement_plan):
        """Check if user has access to historical data"""
        # Original stakeholders maintain read access
        was_stakeholder = ProcurementStakeholder.objects.filter(
            procurement_plan=procurement_plan,
            user=user
        ).exists()
        
        if was_stakeholder:
            return True
        
        # Audit and management roles have historical access
        historical_access_roles = ['audit_officer', 'manager', 'director', 'admin']
        user_role_hierarchy = user.user_role.get_hierarchy() if getattr(user, 'user_role', None) else []
        
        return any(role in user_role_hierarchy for role in historical_access_roles)


class BulkOperationPermission(BaseProcurementPermission):
    """
    Permission class for bulk operations
    """
    
    def has_permission(self, request, view):
        user = request.user
        
        # Bulk operations require elevated permissions
        bulk_operation_roles = ['admin', 'manager', 'director', 'system_admin']
        user_role_hierarchy = user.user_role.get_hierarchy() if getattr(user, 'user_role', None) else []
        
        if not any(role in user_role_hierarchy for role in bulk_operation_roles):
            return False
        
        # Check for bulk operation authorization
        bulk_auth_key = f"bulk_operation_auth_{user.pk}"
        bulk_auth_data = cache.get(bulk_auth_key)
        
        if not bulk_auth_data:
            return False
        
        # Check authorization validity
        valid_until = datetime.fromisoformat(bulk_auth_data['valid_until'])
        if timezone.now() > valid_until:
            cache.delete(bulk_auth_key)
            return False
        
        # Log bulk operation
        logger.info(f"Bulk operation authorized for {user.username}")
        
        return True


class GeographicalRestrictionBypass(BaseProcurementPermission):
    """
    Permission class to bypass geographical restrictions in emergencies
    """
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Check for emergency geographical bypass
        emergency_bypass_key = f"geo_bypass_{user.pk}"
        bypass_data = cache.get(emergency_bypass_key)
        
        if bypass_data:
            # Check validity
            valid_until = datetime.fromisoformat(bypass_data['valid_until'])
            if timezone.now() < valid_until:
                logger.warning(f"Geographical restriction bypassed by {user.username}")
                return True
        
        return False


class DataRetentionPermission(BaseProcurementPermission):
    """
    Permission class for data retention and archival operations
    """
    
    def has_permission(self, request, view):
        user = request.user
        
        # Only specific roles can manage data retention
        retention_roles = ['admin', 'data_manager', 'compliance_officer']
        user_role_hierarchy = user.user_role.get_hierarchy() if getattr(user, 'user_role', None) else []
        
        return any(role in user_role_hierarchy for role in retention_roles)
    
    def has_object_permission(self, request, view, obj):
        # Check data retention policies
        if hasattr(obj, 'created_at'):
            # Apply retention rules based on object age and type
            age_days = (timezone.now() - obj.created_at).days
            
            # Different retention periods for different object types
            retention_periods = {
                'ActivityLog': 2555,  # 7 years
                'ProcurementDocument': 1825,  # 5 years
                'ProcurementPlan': 3650,  # 10 years
            }
            
            object_type = obj.__class__.__name__
            retention_period = retention_periods.get(object_type, 365)  # Default 1 year
            
            if age_days > retention_period:
                # Only archival operations allowed
                return view.action in ['archive', 'retrieve']
        
        return True


# Advanced helper functions for edge cases

def check_emergency_access(user, procurement_plan):
    """Check if user has emergency access to procurement"""
    if not user or not procurement_plan:
        return False
    
    emergency_key = f"emergency_access_{user.pk}_{procurement_plan.pk}"
    emergency_data = cache.get(emergency_key)
    
    if not emergency_data:
        return False
    
    # Check validity
    valid_until = datetime.fromisoformat(emergency_data['valid_until'])
    if timezone.now() > valid_until:
        cache.delete(emergency_key)
        return False
    
    # Log emergency access
    logger.critical(f"Emergency access used by {user.username} for procurement {procurement_plan.policy_number}")
    
    return True


def grant_temporary_access(user, procurement_plan, duration_hours=24, allowed_actions=None):
    """Grant temporary access to a user for specific procurement"""
    if not user or not procurement_plan:
        return False
    
    if allowed_actions is None:
        allowed_actions = ['retrieve', 'list']
    
    temp_access_key = f"temp_access_{user.pk}_{procurement_plan.pk}"
    valid_until = timezone.now() + timedelta(hours=duration_hours)
    
    cache.set(temp_access_key, {
        'valid_until': valid_until.isoformat(),
        'allowed_actions': allowed_actions,
        'granted_by': 'system',  # Could be modified to track who granted it
        'reason': 'temporary_assignment'
    }, duration_hours * 3600)
    
    logger.info(f"Temporary access granted to {user.username} for procurement {procurement_plan.policy_number}")
    
    return True


def revoke_access(user, procurement_plan):
    """Revoke all forms of access for a user to specific procurement"""
    if not user or not procurement_plan:
        return False
    
    # Remove temporary access
    temp_access_key = f"temp_access_{user.pk}_{procurement_plan.pk}"
    cache.delete(temp_access_key)
    
    # Remove vendor access
    vendor_access_key = f"vendor_access_{user.pk}_{procurement_plan.pk}"
    cache.delete(vendor_access_key)
    
    # Remove delegation
    delegation_keys = cache.keys(f"delegation_*_{user.pk}")
    for key in delegation_keys:
        cache.delete(key)
    
    # Deactivate stakeholder roles
    ProcurementStakeholder.objects.filter(
        procurement_plan=procurement_plan,
        user=user
    ).update(status='inactive')
    
    logger.info(f"Access revoked for {user.username} from procurement {procurement_plan.policy_number}")
    
    return True


def enable_read_only_mode(procurement_plan, duration_hours=1, reason="system_maintenance"):
    """Enable read-only mode for a procurement"""
    if not procurement_plan:
        return False
    
    readonly_key = f"readonly_mode_{procurement_plan.pk}"
    valid_until = timezone.now() + timedelta(hours=duration_hours)
    
    cache.set(readonly_key, {
        'valid_until': valid_until.isoformat(),
        'reason': reason,
        'enabled_at': timezone.now().isoformat()
    }, duration_hours * 3600)
    
    logger.warning(f"Read-only mode enabled for procurement {procurement_plan.policy_number}: {reason}")
    
    return True


def disable_read_only_mode(procurement_plan):
    """Disable read-only mode for a procurement"""
    if not procurement_plan:
        return False
    
    readonly_key = f"readonly_mode_{procurement_plan.pk}"
    cache.delete(readonly_key)
    
    logger.info(f"Read-only mode disabled for procurement {procurement_plan.policy_number}")
    
    return True


def check_bulk_operation_limit(user, operation_type, limit=100):
    """Check if user hasn't exceeded bulk operation limits"""
    daily_key = f"bulk_ops_{user.pk}_{timezone.now().strftime('%Y%m%d')}"
    current_count = cache.get(daily_key, 0)
    
    if current_count >= limit:
        logger.warning(f"Bulk operation limit exceeded by {user.username}")
        return False
    
    # Increment counter
    cache.set(daily_key, current_count + 1, 86400)  # 24 hours
    
    return True


def validate_permission_chain(user, procurement_plan, action):
    """Validate complete permission chain for complex scenarios"""
    # Check all permission layers
    checks = [
        ('user_active', lambda: user.is_active),
        ('basic_access', lambda: BaseProcurementPermission().has_permission(MockRequest(user), None)),
        ('procurement_access', lambda: check_procurement_access(user, procurement_plan, action)),
        ('time_restrictions', lambda: BaseProcurementPermission().check_time_based_access(user, procurement_plan)),
        ('compliance', lambda: BaseProcurementPermission().check_compliance_requirements(user, procurement_plan, action)),
    ]
    
    for check_name, check_func in checks:
        try:
            if not check_func():
                logger.debug(f"Permission check failed: {check_name} for user {user.username}")
                return False
        except Exception as e:
            logger.error(f"Permission check error ({check_name}): {str(e)}")
            return False
    
    return True


class MockRequest:
    """Mock request object for permission testing"""
    def __init__(self, user):
        self.user = user