from rest_framework import viewsets, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import Q
from django.db.models import Count, Prefetch
from django.db import transaction
import json
import logging

logger = logging.getLogger(__name__)

from ..models import (
    ProcurementPlan,
    QuarterlyTarget,
    StageHistory,
    Timeline,
    ProcurementRisk,
    ApprovalWorkflow,
    ApprovalWorkflowDependency,
    ActivityLog,
    PerformanceMetric,
)
from ..serializers import (
    ProcurementPlanSerializer,
    ProcurementPlanCreateSerializer,
    QuarterlyTargetSerializer,
    StageHistorySerializer,
    TimelineSerializer,
    ProcurementRiskSerializer,
    ApprovalWorkflowSerializer,
    ApprovalWorkflowDependencySerializer,
    ActivityLogSerializer,
    ActivityLogCreateSerializer,
    PerformanceMetricSerializer,
)
from ..utils import apply_procurement_filters, create_standard_paginated_response
from ..mixins import get_procurement_plan_filter
from ..stage_reset import perform_stage_reset
from ..plan_lifecycle import perform_plan_termination
from ..serializers import PlanTerminationSerializer, TerminatePlanSerializer

from users.permissions import HasPermission

class ProcurementPlanViewSet(viewsets.ModelViewSet):
    """ViewSet for managing procurement plans"""
    queryset = ProcurementPlan.objects.all()
    serializer_class = ProcurementPlanSerializer
    permission_classes = [permissions.IsAuthenticated, HasPermission('planning.view')]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['project_name', 'policy_number', 'project_description']
    ordering_fields = ['created_at', 'updated_at', 'project_name']
    ordering = ['-created_at']

    def get_permissions(self):
        """Granular permission mapping for actions"""
        if self.action == 'create':
            return [permissions.IsAuthenticated(), HasPermission('planning.create')()]
        if self.action in ['destroy', 'bulk_delete']:
            return [permissions.IsAuthenticated(), HasPermission('planning.delete')()]
        if self.action in ['update', 'partial_update', 'reset_stage']:
            return [permissions.IsAuthenticated(), HasPermission('planning.manage')()]
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated(), HasPermission('planning.view')()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return ProcurementPlanCreateSerializer
        return ProcurementPlanSerializer

    @staticmethod
    def _is_superadmin_user(user):
        from users.utils import is_superadmin
        return is_superadmin(user)

    def get_queryset(self):
        """Unified queryset with role hierarchy, ownership, stakeholder, and department filtering"""
        user = self.request.user
        if not user.is_authenticated:
            return ProcurementPlan.objects.none()

        # Get the unified access filter
        # Include custom actions in the 'manage' group for correct scoping
        manage_actions = ['update', 'partial_update', 'destroy', 'reset_stage', 'bulk_delete', 'terminate_plan']
        action = 'manage' if self.action in manage_actions else 'view'
        access_filter = get_procurement_plan_filter(user, action=action)

        # Optimized queryset with all necessary joins
        queryset = ProcurementPlan.objects.select_related(
            'owner', 'owner__user_role', 'office'
        ).prefetch_related(
            'stakeholders__user',
            'committees',
            'quarterly_targets'
        ).annotate(
            committee_count=Count('committees', distinct=True)
        )

        # Apply the unified filter.
        # NOTE: access_filter may be an empty Q() meaning full access (superuser/cross-office bypass).
        # We must ALWAYS call .filter(access_filter) — never skip it with `if access_filter:`
        # because an empty Q() is falsy but means 'no restriction', not 'deny all'.
        queryset = queryset.filter(access_filter)

        return queryset.distinct()

    def list(self, request, *args, **kwargs):
        """Optimized list method with single database query"""
        # Start with optimized base queryset
        queryset = self.get_queryset()

        # Apply search filter (handled by DRF SearchFilter)
        search_filter = filters.SearchFilter()
        queryset = search_filter.filter_queryset(request, queryset, self)

        # Apply custom filters if any
        queryset = apply_procurement_filters(queryset, request)

        # Apply ordering (use database-level ordering)
        ordering = request.query_params.get('ordering', '-created_at')
        if ordering:
            # Validate ordering field to prevent SQL injection
            valid_fields = ['created_at', '-created_at', 'updated_at', '-updated_at', 'project_name', '-project_name']
            if ordering in valid_fields:
                queryset = queryset.order_by(ordering)

        # Return paginated response (single query for count + results)
        return create_standard_paginated_response(
            queryset, request, self.get_serializer_class(), 'data'
        )

    def perform_create(self, serializer):
        """Set the owner and office to the current user when creating a procurement plan"""
        user = self.request.user
        office = getattr(user, 'office', None)
        serializer.save(owner=user, office=office)

    def _sync_quarterly_targets(self, procurement_plan, targets_data):
        if isinstance(targets_data, str):
            try:
                targets_data = json.loads(targets_data)
            except json.JSONDecodeError as exc:
                raise ValidationError({"quarterly_targets": "Invalid JSON format."}) from exc

        if not isinstance(targets_data, list):
            raise ValidationError({"quarterly_targets": "Quarterly targets must be a list."})

        allowed_quarters = {choice[0] for choice in QuarterlyTarget._meta.get_field('quarter').choices}
        allowed_statuses = {choice[0] for choice in QuarterlyTarget._meta.get_field('status').choices}
        allowed_priorities = {choice[0] for choice in QuarterlyTarget._meta.get_field('priority').choices}

        existing_by_quarter = {
            target.quarter: target for target in procurement_plan.quarterly_targets.all()
        }

        seen_quarters = set()
        keep_quarters = set()

        for target_data in targets_data:
            if not isinstance(target_data, dict):
                raise ValidationError({"quarterly_targets": "Each quarterly target must be an object."})

            quarter = target_data.get("quarter")
            if not quarter:
                raise ValidationError({"quarterly_targets": "Each quarterly target must include a quarter."})
            if quarter not in allowed_quarters:
                raise ValidationError({"quarterly_targets": f"Invalid quarter: {quarter}."})
            if quarter in seen_quarters:
                raise ValidationError({"quarterly_targets": f"Duplicate quarter detected: {quarter}."})

            seen_quarters.add(quarter)
            keep_quarters.add(quarter)

            target = existing_by_quarter.get(quarter)
            if target is None:
                target = QuarterlyTarget(procurement_plan=procurement_plan, quarter=quarter)

            if "status" in target_data:
                status_value = target_data.get("status")
                if status_value not in allowed_statuses:
                    raise ValidationError({"quarterly_targets": f"Invalid status: {status_value}."})
                target.status = status_value

            if "priority" in target_data:
                priority_value = target_data.get("priority")
                if priority_value not in allowed_priorities:
                    raise ValidationError({"quarterly_targets": f"Invalid priority: {priority_value}."})
                target.priority = priority_value

            if "target_details" in target_data:
                target.target_details = target_data.get("target_details") or ""

            if "target_start_date" in target_data:
                target.target_start_date = target_data.get("target_start_date")
            if "target_end_date" in target_data:
                target.target_end_date = target_data.get("target_end_date")
            if "actual_completion_date" in target_data:
                target.actual_completion_date = target_data.get("actual_completion_date")

            if "milestones" in target_data:
                target.milestones = target_data.get("milestones") or []
            if "dependencies" in target_data:
                target.dependencies = target_data.get("dependencies") or []
            if "progress_percentage" in target_data:
                target.progress_percentage = target_data.get("progress_percentage") or 0
            if "notes" in target_data:
                target.notes = target_data.get("notes") or ""
            if "risk_assessment" in target_data:
                target.risk_assessment = target_data.get("risk_assessment") or ""

            if "completed_by" in target_data:
                target.completed_by_id = target_data.get("completed_by") or None

            target.save()

        procurement_plan.quarterly_targets.exclude(quarter__in=keep_quarters).delete()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        raw_targets = request.data.get("quarterly_targets", None)

        with transaction.atomic():
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            if raw_targets is not None:
                self._sync_quarterly_targets(instance, raw_targets)

        # Clear prefetch cache and re-fetch with optimized queryset for fresh response
        if hasattr(instance, '_prefetch_related_cache'):
            instance._prefetch_related_cache.clear()
        
        # Re-fetch the object with prefetch_related to ensure all targets are fresh
        instance = self.get_queryset().get(pk=instance.pk)
        return Response(self.get_serializer(instance).data)

    @action(detail=False, methods=['post'], url_path='bulk-delete')
    def bulk_delete(self, request):
        """Bulk delete procurement plans - Scoped to user's management authority"""
        plan_ids = request.data.get('plan_ids', [])

        if not plan_ids:
            return Response(
                {'error': 'No plan IDs provided for deletion.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(plan_ids, list):
            return Response(
                {'error': 'plan_ids must be a list.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Use the scoped queryset (action='manage') to find deletable plans
        # This automatically respects office and cross-office permissions
        queryset = self.get_queryset().filter(id__in=plan_ids)
        existing_ids = list(queryset.values_list('id', flat=True))

        if len(existing_ids) == 0:
            return Response(
                {'error': 'No accessible plans found with the provided IDs.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Performance check: did we miss any requested IDs due to lack of permission?
        if len(existing_ids) != len(plan_ids):
            missing_ids = set(plan_ids) - set(existing_ids)
            # Log this as a potentially unauthorized attempt or missing data
            logger.warning(f"User {request.user} tried to bulk-delete {len(plan_ids)} plans but only has access to {len(existing_ids)}. Missing: {list(missing_ids)}")

        # Perform the bulk deletion on the scoped queryset
        deleted_count = queryset.count()
        queryset.delete()

        return Response({
            'message': f'Successfully deleted {deleted_count} procurement plans.',
            'deleted_count': deleted_count,
            'deleted_ids': existing_ids
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reset-stage')
    def reset_stage(self, request, pk=None):
        """Reset current stage to the immediate previous stage and clear stage-specific data."""
        if not self._is_superadmin_user(request.user):
            return Response(
                {'error': 'Only SUPERADMIN can reset procurement stages.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        plan = self.get_object()
        target_stage = request.data.get('target_stage')
        reason = request.data.get('reason', '')

        try:
            with transaction.atomic():
                result = perform_stage_reset(
                    plan=plan,
                    user=request.user,
                    target_stage=target_stage,
                    reason=reason,
                )
        except ValueError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {'error': f'Failed to reset stage: {str(exc)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        plan.refresh_from_db()
        return Response(
            {
                'message': f"Stage reset from {result['old_stage']} to {result['new_stage']} completed.",
                'result': result,
                'data': self.get_serializer(plan).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='terminate')
    def terminate_plan(self, request, pk=None):
        """Terminate a procurement plan with mandatory documents and cascading effects."""
        if not request.user.has_rbac_permission('planning.terminate'):
            return Response(
                {'error': 'You do not have permission to terminate plans.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        plan = self.get_object()

        serializer = TerminatePlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        documents = request.FILES.getlist('documents')
        if not documents:
            return Response(
                {'error': 'At least one supporting document is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = perform_plan_termination(
                plan=plan,
                user=request.user,
                reason_category=serializer.validated_data['reason_category'],
                reason=serializer.validated_data['reason'],
                remarks=serializer.validated_data.get('remarks', ''),
                documents=documents,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
        except ValueError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan.refresh_from_db()
        return Response(
            {
                'message': f"Procurement plan {plan.policy_number} has been terminated.",
                'result': result,
                'data': self.get_serializer(plan).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['get'], url_path='termination')
    def get_termination(self, request, pk=None):
        """Get termination details for a plan."""
        plan = self.get_object()

        try:
            termination = plan.termination
        except plan._meta.model.termination.RelatedObjectDoesNotExist:
            return Response(
                {'error': 'This plan has not been terminated.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PlanTerminationSerializer(termination, context={'request': request})
        return Response(serializer.data)


class QuarterlyTargetViewSet(viewsets.ModelViewSet):
    """ViewSet for managing quarterly targets"""
    queryset = QuarterlyTarget.objects.all()
    serializer_class = QuarterlyTargetSerializer
    permission_classes = [permissions.IsAuthenticated, HasPermission('planning.view')]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['procurement_plan', 'quarter', 'status']
    ordering_fields = ['quarter', 'priority', 'progress_percentage', 'created_at']
    ordering = ['quarter']

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), HasPermission('planning.create')()]
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(), HasPermission('planning.manage')()]
        if self.action == 'destroy':
            return [permissions.IsAuthenticated(), HasPermission('planning.delete')()]
        return [permissions.IsAuthenticated(), HasPermission('planning.view')()]

    def get_queryset(self):
        """Filter targets based on user access to procurement plans (hierarchy-aware)"""
        user = self.request.user
        if not user.is_authenticated:
            return QuarterlyTarget.objects.none()

        action = 'manage' if self.action in ['create', 'update', 'partial_update', 'destroy'] else 'view'
        access_filter = get_procurement_plan_filter(user, action=action)
        if not access_filter:
            return QuarterlyTarget.objects.all()

        # Prefix filter for related model
        return QuarterlyTarget.objects.filter(
            Q(procurement_plan__in=ProcurementPlan.objects.filter(access_filter))
        ).distinct()


class StageHistoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing stage history"""
    queryset = StageHistory.objects.all()
    serializer_class = StageHistorySerializer
    permission_classes = [permissions.IsAuthenticated, HasPermission('planning.view')]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['procurement_plan', 'stage', 'status']
    ordering_fields = ['start_date', 'end_date', 'stage']
    ordering = ['-start_date']

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), HasPermission('planning.create')()]
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(), HasPermission('planning.manage')()]
        if self.action == 'destroy':
            return [permissions.IsAuthenticated(), HasPermission('planning.delete')()]
        return [permissions.IsAuthenticated(), HasPermission('planning.view')()]

    def get_queryset(self):
        """Filter stage history based on user access to procurement plans (hierarchy-aware)"""
        user = self.request.user
        if not user.is_authenticated:
            return StageHistory.objects.none()

        action = 'manage' if self.action in ['create', 'update', 'partial_update', 'destroy'] else 'view'
        access_filter = get_procurement_plan_filter(user, action=action)
        if not access_filter:
            return StageHistory.objects.all()

        return StageHistory.objects.filter(
            Q(procurement_plan__in=ProcurementPlan.objects.filter(access_filter))
        ).distinct()


class TimelineViewSet(viewsets.ModelViewSet):
    """ViewSet for managing timelines"""
    queryset = Timeline.objects.all()
    serializer_class = TimelineSerializer
    permission_classes = [permissions.IsAuthenticated, HasPermission('planning.view')]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    filterset_fields = ['procurement_plan', 'status', 'priority']
    ordering_fields = ['start_date', 'end_date', 'created_at']
    ordering = ['start_date']

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), HasPermission('planning.create')()]
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(), HasPermission('planning.manage')()]
        if self.action == 'destroy':
            return [permissions.IsAuthenticated(), HasPermission('planning.delete')()]
        return [permissions.IsAuthenticated(), HasPermission('planning.view')()]

    def get_queryset(self):
        """Filter timelines based on user access to procurement plans (hierarchy-aware)"""
        user = self.request.user
        if not user.is_authenticated:
            return Timeline.objects.none()

        action = 'manage' if self.action in ['create', 'update', 'partial_update', 'destroy'] else 'view'
        access_filter = get_procurement_plan_filter(user, action=action)
        if not access_filter:
            return Timeline.objects.all()

        return Timeline.objects.filter(
            Q(procurement_plan__in=ProcurementPlan.objects.filter(access_filter))
        ).distinct()


class ProcurementRiskViewSet(viewsets.ModelViewSet):
    """ViewSet for managing procurement risks"""
    queryset = ProcurementRisk.objects.all()
    serializer_class = ProcurementRiskSerializer
    permission_classes = [permissions.IsAuthenticated, HasPermission('planning.view')]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    filterset_fields = ['procurement_plan', 'category', 'severity', 'status']
    ordering_fields = ['severity', 'impact', 'created_at']
    ordering = ['-severity', '-impact']

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), HasPermission('planning.create')()]
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(), HasPermission('planning.manage')()]
        if self.action == 'destroy':
            return [permissions.IsAuthenticated(), HasPermission('planning.delete')()]
        return [permissions.IsAuthenticated(), HasPermission('planning.view')()]

    def get_queryset(self):
        """Filter risks based on user access to procurement plans (hierarchy-aware)"""
        user = self.request.user
        if not user.is_authenticated:
            return ProcurementRisk.objects.none()

        action = 'manage' if self.action in ['create', 'update', 'partial_update', 'destroy'] else 'view'
        access_filter = get_procurement_plan_filter(user, action=action)
        if not access_filter:
            return ProcurementRisk.objects.all()

        return ProcurementRisk.objects.filter(
            Q(procurement_plan__in=ProcurementPlan.objects.filter(access_filter))
        ).distinct()


class ApprovalWorkflowViewSet(viewsets.ModelViewSet):
    """ViewSet for managing approval workflows"""
    queryset = ApprovalWorkflow.objects.all()
    serializer_class = ApprovalWorkflowSerializer
    permission_classes = [permissions.IsAuthenticated, HasPermission('planning.view')]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    filterset_fields = ['procurement_plan', 'status', 'current_step']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), HasPermission('planning.create')()]
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(), HasPermission('planning.manage')()]
        if self.action == 'destroy':
            return [permissions.IsAuthenticated(), HasPermission('planning.delete')()]
        return [permissions.IsAuthenticated(), HasPermission('planning.view')()]

    def get_queryset(self):
        """Filter workflows based on user access to procurement plans (hierarchy-aware)"""
        user = self.request.user
        if not user.is_authenticated:
            return ApprovalWorkflow.objects.none()

        action = 'manage' if self.action in ['create', 'update', 'partial_update', 'destroy'] else 'view'
        access_filter = get_procurement_plan_filter(user, action=action)
        if not access_filter:
            return ApprovalWorkflow.objects.all()

        return ApprovalWorkflow.objects.filter(
            Q(procurement_plan__in=ProcurementPlan.objects.filter(access_filter))
        ).distinct()


class ApprovalWorkflowDependencyViewSet(viewsets.ModelViewSet):
    """ViewSet for managing approval workflow dependencies"""
    queryset = ApprovalWorkflowDependency.objects.all()
    serializer_class = ApprovalWorkflowDependencySerializer
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), HasPermission('planning.manage')()]
        return [permissions.IsAuthenticated(), HasPermission('planning.view')()]

    def get_queryset(self):
        """Filter dependencies based on user access to workflows (hierarchy-aware)"""
        user = self.request.user
        if not user.is_authenticated:
            return ApprovalWorkflowDependency.objects.none()

        action = 'manage' if self.action in ['create', 'update', 'partial_update', 'destroy'] else 'view'
        access_filter = get_procurement_plan_filter(user, action=action)
        if not access_filter:
            return ApprovalWorkflowDependency.objects.all()

        return ApprovalWorkflowDependency.objects.filter(
            Q(workflow__procurement_plan__in=ProcurementPlan.objects.filter(access_filter))
        ).distinct()


class ActivityLogViewSet(viewsets.ModelViewSet):
    """ViewSet for managing activity logs"""
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['action', 'action_description']
    filterset_fields = ['procurement_plan', 'user', 'action', 'content_type']
    ordering_fields = ['timestamp', 'action']
    ordering = ['-timestamp']
    
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), HasPermission('planning.manage')()]
        return [permissions.IsAuthenticated(), HasPermission('planning.view')()]

    def get_serializer_class(self):
        if self.action == 'create':
            return ActivityLogCreateSerializer
        return ActivityLogSerializer

    def get_queryset(self):
        """Filter activity logs based on user access to procurement plans (hierarchy-aware)"""
        user = self.request.user
        if not user.is_authenticated:
            return ActivityLog.objects.none()

        action = 'manage' if self.action in ['create', 'update', 'partial_update', 'destroy'] else 'view'
        access_filter = get_procurement_plan_filter(user, action=action)
        if not access_filter:
            return ActivityLog.objects.all()

        return ActivityLog.objects.filter(
            Q(procurement_plan__in=ProcurementPlan.objects.filter(access_filter)) |
            Q(user=user)
        ).distinct()


class PerformanceMetricViewSet(viewsets.ModelViewSet):
    """ViewSet for managing performance metrics"""
    queryset = PerformanceMetric.objects.all()
    serializer_class = PerformanceMetricSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['metric_name', 'description']
    filterset_fields = ['procurement_plan', 'metric_type', 'status']
    ordering_fields = ['metric_value', 'target_value', 'created_at']
    ordering = ['-created_at']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), HasPermission('planning.manage')()]
        return [permissions.IsAuthenticated(), HasPermission('planning.view')()]

    def get_queryset(self):
        """Filter metrics based on user access to procurement plans (hierarchy-aware)"""
        user = self.request.user
        if not user.is_authenticated:
            return PerformanceMetric.objects.none()

        action = 'manage' if self.action in ['create', 'update', 'partial_update', 'destroy'] else 'view'
        access_filter = get_procurement_plan_filter(user, action=action)
        if not access_filter:
            return PerformanceMetric.objects.all()

        return PerformanceMetric.objects.filter(
            Q(procurement_plan__in=ProcurementPlan.objects.filter(access_filter))
        ).distinct()
