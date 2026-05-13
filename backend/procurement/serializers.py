
import logging
from rest_framework import serializers
from .models import (
    ProcurementPlan,
    PlanTermination,
    QuarterlyTarget,
    StageHistory,
    ProcurementStakeholder,
    Timeline,
    ProcurementRisk,
    ApprovalWorkflow,
    ApprovalWorkflowDependency,
    ActivityLog,
    PerformanceMetric,
    ProcurementDocument,
    DocumentAccessLog,
    DocumentCategory,
    ProcurementNotification,
    ExternalIntegration,
)
from django.db import transaction
from django.utils import timezone
from users.models import CustomUser
from .utils import normalize_stage_id, validate_stage_transition


class DocumentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentCategory
        fields = ['id', 'key', 'label', 'is_active', 'max_file_size']


class QuarterlyTargetSerializer(serializers.ModelSerializer):
    """Serializer for QuarterlyTarget model"""
    class Meta:
        model = QuarterlyTarget
        fields = [
            'id', 'quarter', 'target_details', 'status', 'priority', 
            'progress_percentage', 'created_at', 'updated_at'
        ]


class ProcurementPlanSerializer(serializers.ModelSerializer):
    """Serializer for ProcurementPlan model with read-only owner and quarterly targets"""
    owner_name = serializers.CharField(source='owner.first_name', read_only=True)
    owner_email = serializers.CharField(source='owner.email', read_only=True)
    office_name = serializers.CharField(source='office.name', read_only=True)
    office_code = serializers.CharField(source='office.code', read_only=True)
    quarterly_targets = QuarterlyTargetSerializer(many=True, required=False)
    committee_count = serializers.SerializerMethodField()
    # Per-plan permission flags — used by the frontend to show/hide Edit and Delete buttons
    can_manage = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = ProcurementPlan
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'stage_updated_at', 'dept_index']

    def _get_manage_filter(self, user):
        """Cache the manage-action Q filter so it's only built once per serializer context."""
        ctx = self.context
        if '_manage_filter' not in ctx:
            from .mixins import get_procurement_plan_filter
            ctx['_manage_filter'] = get_procurement_plan_filter(user, action='manage')
        return ctx['_manage_filter']

    def _get_delete_filter(self, user):
        """Cache the delete-action Q filter (same as manage for now)."""
        ctx = self.context
        if '_delete_filter' not in ctx:
            from .mixins import get_procurement_plan_filter
            ctx['_delete_filter'] = get_procurement_plan_filter(user, action='manage')
        return ctx['_delete_filter']

    def get_can_manage(self, obj):
        """Return True if the requesting user is allowed to edit this specific plan."""
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        user = request.user
        # Super Admin / superuser always can
        from users.utils import is_superadmin
        if getattr(user, 'is_superuser', False) or is_superadmin(user):
            return True
        # Must have route-level planning.manage permission first
        if not user.has_rbac_permission('planning.manage'):
            return False
        # Then check record-level scope
        q_filter = self._get_manage_filter(user)
        return ProcurementPlan.objects.filter(q_filter, pk=obj.pk).exists()

    def get_can_delete(self, obj):
        """Return True if the requesting user is allowed to delete this specific plan."""
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        user = request.user
        from users.utils import is_superadmin
        if getattr(user, 'is_superuser', False) or is_superadmin(user):
            return True
        # Must have route-level planning.delete permission first
        if not user.has_rbac_permission('planning.delete'):
            return False
        q_filter = self._get_delete_filter(user)
        return ProcurementPlan.objects.filter(q_filter, pk=obj.pk).exists()

    def get_committee_count(self, obj):
        """Return the count of committees associated with this procurement plan"""
        # Favor annotated count if available
        return getattr(obj, 'committee_count', obj.committees.count())

    def to_representation(self, instance):
        """Ensure all 4 quarters are present in the response"""
        data = super().to_representation(instance)
        
        # Ensure quarterly_targets has all 4 quarters
        existing_targets = data.get('quarterly_targets', [])
        existing_quarters = {t.get('quarter') for t in existing_targets}
        
        all_quarters = ['Q1', 'Q2', 'Q3', 'Q4']
        for q in all_quarters:
            if q not in existing_quarters:
                existing_targets.append({
                    'id': None,
                    'quarter': q,
                    'target_details': '',
                    'status': 'Planned',
                    'priority': 'medium',
                    'progress_percentage': 0.00,
                    'created_at': None,
                    'updated_at': None
                })
        
        # Sort targets by quarter
        data['quarterly_targets'] = sorted(existing_targets, key=lambda x: x.get('quarter', ''))
        return data

    def validate(self, data):
        """Custom validation for the serializer"""
        # dept_index is auto-generated from policy_number, so we don't validate it here
        if 'dept_index' in data:
            del data['dept_index']

        if self.instance is not None and "stage" in data:
            target_stage = normalize_stage_id(data.get("stage"))
            current_stage = normalize_stage_id(self.instance.stage)
            data["stage"] = target_stage

            if target_stage != current_stage:
                can_transition, errors = validate_stage_transition(
                    self.instance, target_stage
                )
                if not can_transition:
                    raise serializers.ValidationError({"stage": errors})

        return data

    def get_fields(self):
        """Make owner field optional during creation"""
        fields = super().get_fields()
        if self.instance is None:  # Creating a new instance
            if 'owner' in fields:
                fields['owner'].required = False
        return fields

    def create(self, validated_data):
        quarterly_targets_data = validated_data.pop('quarterly_targets', [])
        plan = super().create(validated_data)
        
        for target_data in quarterly_targets_data:
            QuarterlyTarget.objects.create(procurement_plan=plan, **target_data)
        
        return plan

    def update(self, instance, validated_data):
        # Remove quarterly_targets from validated_data to prevent super().update from failing
        # We rely on ProcurementPlanViewSet.update to handle quarterly target synchronization
        validated_data.pop('quarterly_targets', None)
        return super().update(instance, validated_data)


class ProcurementPlanCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating ProcurementPlan with quarterly targets"""
    quarterly_targets = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        default=list
    )

    class Meta:
        model = ProcurementPlan
        fields = [
            'policy_number', 'department', 'office', 'fiscal_year', 'program_number',
            'project_name', 'project_description', 'estimated_cost', 'budget', 'stage',
            'status', 'priority', 'progress_percentage', 'planned_start_date',
            'planned_end_date', 'actual_start_date', 'actual_end_date',
            'next_milestone_date', 'next_milestone_description',
            'quarterly_targets'  # Added to handle nested creation
        ]

    def validate_quarterly_targets(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Quarterly targets must be a list.")

        seen_quarters = set()
        for target in value:
            if not isinstance(target, dict):
                raise serializers.ValidationError("Each quarterly target must be an object.")

            quarter = target.get('quarter')
            if not quarter:
                raise serializers.ValidationError("Each quarterly target must include a quarter.")

            if quarter in seen_quarters:
                raise serializers.ValidationError(f"Duplicate quarter detected: {quarter}")
            seen_quarters.add(quarter)

        return value

    def validate_policy_number(self, value):
        if not value:
            return value
        dept_index = value.split('-')[-1]
        if len(dept_index) > 10:
            raise serializers.ValidationError(
                "Policy number suffix after '-' must be 10 characters or fewer."
            )
        return value

    def create(self, validated_data):
        logger = logging.getLogger(__name__)

        # Extract quarterly targets before creating plan
        quarterly_targets_data = validated_data.pop('quarterly_targets', [])

        logger.info("Creating procurement plan with %s quarterly targets", len(quarterly_targets_data))

        try:
            with transaction.atomic():
                # Create the procurement plan
                plan = super().create(validated_data)

                created_targets = []
                # Create quarterly targets
                for target_data in quarterly_targets_data:
                    try:
                        target = QuarterlyTarget.objects.create(
                            procurement_plan=plan,
                            quarter=target_data.get('quarter'),
                            target_details=target_data.get('target_details', ''),
                            status=target_data.get('status', 'Planned'),
                        )
                        created_targets.append(target)
                        logger.info("Created quarterly target %s for plan %s", target.quarter, plan.id)
                    except Exception as exc:
                        logger.exception("Failed to create quarterly target for plan %s", plan.id)
                        raise serializers.ValidationError(
                            {"quarterly_targets": "Failed to create quarterly targets."}
                        ) from exc

                logger.info(
                    "Created %s quarterly targets for plan %s",
                    len(created_targets),
                    plan.id
                )

                return plan
        except serializers.ValidationError:
            raise




# ... keep existing code (all other serializers remain the same)
class StageHistorySerializer(serializers.ModelSerializer):
    """Serializer for StageHistory model"""
    class Meta:
        model = StageHistory
        fields = '__all__'


class ProcurementStakeholderSerializer(serializers.ModelSerializer):
    """Serializer for ProcurementStakeholder model"""
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    procurement_plan_title = serializers.CharField(source='procurement_plan.project_name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.name', read_only=True)
    escalation_contact_name = serializers.CharField(source='escalation_contact.name', read_only=True)

    class Meta:
        model = ProcurementStakeholder
        fields = '__all__'


class StakeholderCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating stakeholders"""

    class Meta:
        model = ProcurementStakeholder
        fields = [
            'procurement_plan', 'user', 'role', 'involvement_level', 'authority_level',
            'responsibilities', 'primary_contact', 'contact_priority', 'escalation_contact',
            'assignment_start_date', 'assignment_end_date', 'notification_preferences',
            'notes', 'status'
        ]

    def validate(self, data):
        """Validate stakeholder data"""
        # Check that assignment start date is before end date
        start_date = data.get('assignment_start_date')
        end_date = data.get('assignment_end_date')

        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError("Assignment start date must be before end date")

        # Validate that only one primary contact per role per procurement plan
        if data.get('primary_contact', False):
            procurement_plan = data.get('procurement_plan')
            role = data.get('role')
            user = data.get('user')

            if procurement_plan and role:
                existing_primary = ProcurementStakeholder.objects.filter(
                    procurement_plan=procurement_plan,
                    role=role,
                    primary_contact=True
                ).exclude(user=user if self.instance else None)

                if existing_primary.exists():
                    raise serializers.ValidationError(
                        f"A primary contact for role '{role}' already exists for this procurement plan"
                    )

        return data


class StakeholderBulkActionSerializer(serializers.Serializer):
    """Serializer for bulk stakeholder actions"""
    ACTION_CHOICES = [
        ('activate', 'Activate'),
        ('deactivate', 'Deactivate'),
        ('update_status', 'Update Status'),
        ('update_authority', 'Update Authority Level'),
        ('delete', 'Delete'),
    ]

    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    stakeholder_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100
    )
    new_status = serializers.CharField(required=False, allow_blank=True)
    new_authority_level = serializers.CharField(required=False, allow_blank=True)

    def validate_stakeholder_ids(self, value):
        """Validate that all stakeholder IDs exist"""
        existing_count = ProcurementStakeholder.objects.filter(id__in=value).count()
        if existing_count != len(value):
            raise serializers.ValidationError("Some stakeholder IDs do not exist")
        return value

    def validate(self, data):
        """Validate action-specific requirements"""
        action = data.get('action')

        if action == 'update_status' and not data.get('new_status'):
            raise serializers.ValidationError("new_status is required for update_status action")

        if action == 'update_authority' and not data.get('new_authority_level'):
            raise serializers.ValidationError("new_authority_level is required for update_authority action")

        return data


class TimelineSerializer(serializers.ModelSerializer):
    """Serializer for Timeline model"""
    class Meta:
        model = Timeline
        fields = '__all__'


class ProcurementRiskSerializer(serializers.ModelSerializer):
    """Serializer for ProcurementRisk model"""
    class Meta:
        model = ProcurementRisk
        fields = '__all__'


class ApprovalWorkflowSerializer(serializers.ModelSerializer):
    """Serializer for ApprovalWorkflow model"""
    class Meta:
        model = ApprovalWorkflow
        fields = '__all__'


class ApprovalWorkflowDependencySerializer(serializers.ModelSerializer):
    """Serializer for ApprovalWorkflowDependency model"""
    class Meta:
        model = ApprovalWorkflowDependency
        fields = '__all__'


class ActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for ActivityLog model"""
    class Meta:
        model = ActivityLog
        fields = '__all__'


class PerformanceMetricSerializer(serializers.ModelSerializer):
    """Serializer for PerformanceMetric model"""
    class Meta:
        model = PerformanceMetric
        fields = '__all__'


class ProcurementDocumentSerializer(serializers.ModelSerializer):
    """Serializer for ProcurementDocument model with detailed information"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.name', read_only=True)
    file_extension = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    can_download = serializers.SerializerMethodField()
    access_level_color = serializers.SerializerMethodField()

    class Meta:
        model = ProcurementDocument
        fields = [
            'id', 'procurement_plan', 'title', 'description', 'document_type',
            'file', 'file_name', 'file_size', 'file_hash', 'mime_type',
            'version_number', 'parent_document', 'is_current_version', 'version_notes',
            'status', 'approved_by', 'approved_by_name', 'approved_at', 'approval_notes',
            'access_level', 'access_level_color', 'allowed_roles', 'allowed_users',
            'uploaded_by', 'uploaded_by_name', 'uploaded_at',
            'last_accessed_by', 'last_accessed_at', 'download_count',
            'tags', 'custom_metadata', 'created_at', 'updated_at', 'expires_at',
            'file_extension', 'is_expired', 'can_download'
        ]
        read_only_fields = [
            'id', 'file_hash', 'uploaded_by', 'uploaded_at', 'last_accessed_by',
            'last_accessed_at', 'download_count', 'created_at', 'updated_at'
        ]

    def get_file_extension(self, obj):
        return obj.get_file_extension()

    def get_is_expired(self, obj):
        return obj.is_expired()

    def get_can_download(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return obj.can_access(request.user)
        return False

    def get_access_level_color(self, obj):
        return obj.get_access_level_display_color()


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading new documents"""
    file = serializers.FileField(required=True)

    class Meta:
        model = ProcurementDocument
        fields = [
            'procurement_plan', 'title', 'description', 'document_type',
            'file', 'access_level', 'allowed_roles', 'tags',
            'custom_metadata', 'expires_at'
        ]

    def validate_file(self, value):
        """Validate uploaded file"""
        # Check file size (10MB limit)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size cannot exceed 10MB")

        # Check file type
        allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.jpg', '.jpeg', '.png']
        file_extension = '.' + value.name.split('.')[-1].lower()
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(f"File type {file_extension} is not allowed")

        return value

    def create(self, validated_data):
        # Set the uploaded_by field to the current user
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['uploaded_by'] = request.user

        return super().create(validated_data)


class DocumentAccessLogSerializer(serializers.ModelSerializer):
    """Serializer for document access logs"""
    user_name = serializers.CharField(source='user.name', read_only=True)
    document_title = serializers.CharField(source='document.title', read_only=True)

    class Meta:
        model = DocumentAccessLog
        fields = [
            'id', 'document', 'document_title', 'user', 'user_name',
            'action', 'ip_address', 'user_agent', 'additional_data', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class DocumentVersionSerializer(serializers.ModelSerializer):
    """Serializer for document version information"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.name', read_only=True)

    class Meta:
        model = ProcurementDocument
        fields = [
            'id', 'version_number', 'version_notes', 'uploaded_by', 'uploaded_by_name',
            'uploaded_at', 'file_size', 'is_current_version', 'status'
        ]
        read_only_fields = ['id', 'uploaded_by', 'uploaded_at']


class DocumentBulkActionSerializer(serializers.Serializer):
    """Serializer for bulk document actions"""
    ACTION_CHOICES = [
        ('delete', 'Delete'),
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('change_access_level', 'Change Access Level'),
        ('add_tags', 'Add Tags'),
        ('remove_tags', 'Remove Tags'),
    ]

    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100
    )
    parameters = serializers.JSONField(required=False, default=dict)

    def validate_document_ids(self, value):
        """Validate that all document IDs exist and user has access"""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            raise serializers.ValidationError("Authentication required")

        user = request.user
        allowed_roles = user.get_allowed_roles()
        allowed_role_ids = [role.id for role in allowed_roles]

        # Check if all documents exist and user has access
        accessible_docs = ProcurementDocument.objects.filter(
            id__in=value,
            procurement_plan__owner__role__id__in=allowed_role_ids
        )

        if accessible_docs.count() != len(value):
            raise serializers.ValidationError("Some documents are not accessible or do not exist")

        return value


class ProcurementNotificationSerializer(serializers.ModelSerializer):
    """Serializer for ProcurementNotification model with detailed information"""
    sender_name = serializers.CharField(source='sender.name', read_only=True)
    recipient_name = serializers.CharField(source='recipient.name', read_only=True)
    procurement_plan_title = serializers.CharField(source='procurement_plan.title', read_only=True)
    procurement_plan_policy_number = serializers.CharField(source='procurement_plan.policy_number', read_only=True)
    priority_color = serializers.SerializerMethodField()
    context_display = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    time_since_created = serializers.SerializerMethodField()

    class Meta:
        model = ProcurementNotification
        fields = [
            'id', 'procurement_plan', 'procurement_plan_title', 'procurement_plan_policy_number',
            'recipient', 'recipient_name', 'sender', 'sender_name',
            'notification_type', 'title', 'message', 'priority', 'priority_color',
            'is_read', 'read_at', 'is_dismissed', 'dismissed_at',
            'action_url', 'action_label', 'context_data', 'context_display',
            'related_object_type', 'related_object_id',
            'scheduled_for', 'delivered_at', 'delivery_method',
            'created_at', 'updated_at', 'expires_at', 'is_expired', 'time_since_created'
        ]
        read_only_fields = [
            'id', 'sender', 'read_at', 'dismissed_at', 'delivered_at',
            'created_at', 'updated_at'
        ]

    def get_priority_color(self, obj):
        return obj.get_priority_color()

    def get_context_display(self, obj):
        return obj.get_context_display()

    def get_is_expired(self, obj):
        return obj.is_expired()

    def get_time_since_created(self, obj):
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        diff = now - obj.created_at

        if diff < timedelta(minutes=1):
            return "just now"
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff < timedelta(days=30):
            days = diff.days
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            return obj.created_at.strftime('%b %d, %Y')


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new notifications"""

    class Meta:
        model = ProcurementNotification
        fields = [
            'procurement_plan', 'recipient', 'notification_type',
            'title', 'message', 'priority', 'action_url', 'action_label',
            'context_data', 'related_object_type', 'related_object_id',
            'scheduled_for', 'delivery_method', 'expires_at'
        ]

    def validate_procurement_plan(self, value):
        """Validate that the user has access to the procurement plan"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user
            from users.utils import is_superadmin
            if is_superadmin(user):
                return value
            
            # Simple check: user must be in the same office subtree as the plan owner
            # Or just use get_queryset_for_user logic implicitly
            from users.utils import get_queryset_for_user
            if not get_queryset_for_user(user, ProcurementPlan.objects.filter(id=value.id)).exists():
                raise serializers.ValidationError(
                    "You don't have permission to create notifications for this procurement plan.")

        return value

    def validate_recipient(self, value):
        """Validate that the recipient exists and is active"""
        if not value.is_active:
            raise serializers.ValidationError("Cannot send notifications to inactive users.")
        return value

    def create(self, validated_data):
        # Set the sender field to the current user
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['sender'] = request.user

        return super().create(validated_data)


class ActivityLogCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating activity logs"""

    class Meta:
        model = ActivityLog
        fields = [
            'procurement_plan', 'user', 'action', 'description',
            'object_type', 'object_id', 'ip_address', 'user_agent',
            'additional_data'
        ]

    def create(self, validated_data):
        # Set the user field to the current user if not provided
        request = self.context.get('request')
        if request and hasattr(request, 'user') and not validated_data.get('user'):
            validated_data['user'] = request.user

        return super().create(validated_data)


class ExternalIntegrationSerializer(serializers.ModelSerializer):
    """Serializer for ExternalIntegration model"""
    sync_age_days = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = ExternalIntegration
        fields = [
            'id', 'system_name', 'sync_status', 'last_sync',
            'api_endpoint', 'configuration', 'error_message',
            'created_at', 'updated_at', 'sync_age_days', 'is_active'
        ]
        read_only_fields = ['id', 'last_sync', 'created_at', 'updated_at']

    def validate_configuration(self, value):
        """Validate that configuration is a valid JSON object"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Configuration must be a valid JSON object")
        return value


class RiskCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating risks"""

    class Meta:
        model = ProcurementRisk
        fields = [
            'procurement_plan', 'risk_title', 'risk_description', 'risk_type',
            'probability', 'impact', 'status', 'owner', 'identified_date',
            'target_resolution_date', 'actual_resolution_date',
            'mitigation_strategy', 'mitigation_actions', 'contingency_plan',
            'cost_impact', 'schedule_impact_days', 'notes'
        ]

    def validate(self, data):
        """Validate risk data"""
        # Check that target resolution date is in the future
        target_date = data.get('target_resolution_date')
        if target_date and target_date <= timezone.now().date():
            raise serializers.ValidationError("Target resolution date must be in the future")

        return data


class RiskBulkActionSerializer(serializers.Serializer):
    """Serializer for bulk risk actions"""
    ACTION_CHOICES = [
        ('update_status', 'Update Status'),
        ('assign_owner', 'Assign Owner'),
        ('update_priority', 'Update Priority'),
        ('delete', 'Delete'),
    ]

    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    risk_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100
    )
    new_status = serializers.CharField(required=False, allow_blank=True)
    new_owner_id = serializers.IntegerField(required=False)
    new_probability = serializers.CharField(required=False, allow_blank=True)
    new_impact = serializers.CharField(required=False, allow_blank=True)

    def validate_risk_ids(self, value):
        """Validate that all risk IDs exist"""
        existing_count = ProcurementRisk.objects.filter(id__in=value).count()
        if existing_count != len(value):
            raise serializers.ValidationError("Some risk IDs do not exist")
        return value

    def validate(self, data):
        """Validate action-specific requirements"""
        action = data.get('action')

        if action == 'update_status' and not data.get('new_status'):
            raise serializers.ValidationError("new_status is required for update_status action")

        if action == 'assign_owner' and not data.get('new_owner_id'):
            raise serializers.ValidationError("new_owner_id is required for assign_owner action")

        return data


class PlanTerminationSerializer(serializers.ModelSerializer):
    """Read serializer for PlanTermination — includes user info and documents"""
    reason_category_display = serializers.CharField(
        source='get_reason_category_display', read_only=True
    )
    terminated_by_name = serializers.SerializerMethodField()
    terminated_by_employee_id = serializers.CharField(
        source='terminated_by.employee_id', read_only=True, default=''
    )
    documents = serializers.SerializerMethodField()

    class Meta:
        model = PlanTermination
        fields = [
            'id', 'reason_category', 'reason_category_display',
            'reason', 'remarks', 'stage_at_termination',
            'terminated_by', 'terminated_by_name', 'terminated_by_employee_id',
            'terminated_at', 'cascading_effects', 'documents',
        ]

    def get_terminated_by_name(self, obj):
        if obj.terminated_by:
            return obj.terminated_by.get_full_name() or obj.terminated_by.employee_id
        return 'Unknown'

    def get_documents(self, obj):
        docs = ProcurementDocument.objects.filter(
            procurement_plan=obj.procurement_plan,
            document_type='termination_document',
        )
        return ProcurementDocumentSerializer(
            docs, many=True, context=self.context
        ).data


class TerminatePlanSerializer(serializers.Serializer):
    """Write serializer for terminating a plan — validates input"""
    reason_category = serializers.ChoiceField(
        choices=PlanTermination.REASON_CATEGORIES
    )
    reason = serializers.CharField(min_length=1)
    remarks = serializers.CharField(required=False, allow_blank=True, default='')
