from rest_framework import generics, status, filters, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction

from ..models import ProcurementStakeholder, ProcurementPlan
from ..serializers import (
    ProcurementStakeholderSerializer, 
    StakeholderCreateUpdateSerializer,
    StakeholderBulkActionSerializer
)
from users.models import CustomUser
from users.permissions import HasPermission
from users.utils import get_queryset_for_user


class StakeholderPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class StakeholderListCreateView(generics.ListCreateAPIView):
    """
    List all stakeholders or create a new stakeholder
    """
    queryset = ProcurementStakeholder.objects.select_related(
        'user', 'procurement_plan', 'assigned_by', 'escalation_contact'
    ).all()
    pagination_class = StakeholderPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'role': ['exact', 'in'],
        'involvement_level': ['exact', 'in'],
        'authority_level': ['exact', 'in'],
        'status': ['exact', 'in'],
        'primary_contact': ['exact'],
        'procurement_plan': ['exact'],
        'assigned_at': ['gte', 'lte'],
        'assignment_start_date': ['gte', 'lte'],
        'assignment_end_date': ['gte', 'lte'],
    }
    search_fields = [
        'user__employee_profile__name', 'user__username', 'user__email',
        'procurement_plan__project_name', 'procurement_plan__policy_number',
        'responsibilities', 'notes'
    ]
    ordering_fields = [
        'contact_priority', 'assigned_at', 'role', 'involvement_level',
        'authority_level', 'status', 'last_activity_date'
    ]
    ordering = ['contact_priority', 'role']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return StakeholderCreateUpdateSerializer
        return ProcurementStakeholderSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [HasPermission('planning.manage')()]
        return [HasPermission('planning.view')()]
    
    def get_queryset(self):
        action = 'manage' if self.request.method == 'POST' else 'view'
        queryset = get_queryset_for_user(self.request.user, self.queryset, action=action)
        
        # Filter by procurement plan if specified
        procurement_plan_id = self.request.query_params.get('procurement_plan_id')
        if procurement_plan_id:
            queryset = queryset.filter(procurement_plan_id=procurement_plan_id)
        
        # Filter by user if specified
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter active stakeholders only
        active_only = self.request.query_params.get('active_only')
        if active_only and active_only.lower() == 'true':
            current_date = timezone.now().date()
            queryset = queryset.filter(
                status='active',
                assignment_start_date__lte=current_date,
                assignment_end_date__gte=current_date
            )
        
        # Filter by roles that can approve documents
        approvers_only = self.request.query_params.get('approvers_only')
        if approvers_only and approvers_only.lower() == 'true':
            queryset = queryset.filter(
                authority_level__in=['approve', 'manage', 'full_control'],
                status='active'
            )
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)


class StakeholderDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a stakeholder
    """
    queryset = ProcurementStakeholder.objects.select_related(
        'user', 'procurement_plan', 'assigned_by', 'escalation_contact'
    ).all()

    def get_queryset(self):
        action = 'manage' if self.request.method in ['PUT', 'PATCH', 'DELETE'] else 'view'
        return get_queryset_for_user(self.request.user, self.queryset, action=action)
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return StakeholderCreateUpdateSerializer
        return ProcurementStakeholderSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [HasPermission('planning.manage')()]
        return [HasPermission('planning.view')()]


@api_view(['POST'])
@permission_classes([HasPermission('planning.manage')])
def record_stakeholder_activity(request, pk):
    """
    Record activity for a stakeholder and update metrics
    """
    # Secure stakeholder access
    queryset = get_queryset_for_user(request.user, ProcurementStakeholder.objects.all(), action='manage')
    stakeholder = get_object_or_404(queryset, pk=pk)
    
    activity_type = request.data.get('activity_type')
    increment_counter = request.data.get('increment_counter')
    
    # Validate increment_counter
    valid_counters = ['documents_reviewed', 'meetings_attended', 'approvals_given']
    if increment_counter and increment_counter not in valid_counters:
        return Response(
            {'error': f'Invalid increment_counter. Must be one of: {valid_counters}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    stakeholder.record_activity(activity_type, increment_counter)
    
    serializer = ProcurementStakeholderSerializer(stakeholder)
    return Response({
        'message': 'Activity recorded successfully',
        'stakeholder': serializer.data
    })


@api_view(['POST'])
@permission_classes([HasPermission('planning.manage')])
def update_notification_preferences(request, pk):
    """
    Update notification preferences for a stakeholder
    """
    stakeholder = get_object_or_404(ProcurementStakeholder, pk=pk)
    
    preference_type = request.data.get('preference_type')
    enabled = request.data.get('enabled')
    
    if not preference_type or enabled is None:
        return Response(
            {'error': 'preference_type and enabled are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    stakeholder.set_notification_preference(preference_type, enabled)
    
    serializer = ProcurementStakeholderSerializer(stakeholder)
    return Response({
        'message': 'Notification preferences updated successfully',
        'stakeholder': serializer.data
    })


@api_view(['POST'])
@permission_classes([HasPermission('planning.manage')])
def bulk_stakeholder_actions(request):
    """
    Perform bulk actions on multiple stakeholders
    """
    serializer = StakeholderBulkActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    action = serializer.validated_data['action']
    stakeholder_ids = serializer.validated_data['stakeholder_ids']
    
    # Get stakeholders with security scoping
    stakeholders = get_queryset_for_user(request.user, ProcurementStakeholder.objects.filter(id__in=stakeholder_ids), action='manage')
    if not stakeholders.exists():
        return Response(
            {'error': 'No stakeholders found with the provided IDs'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    results = {'success_count': 0, 'error_count': 0, 'errors': []}
    
    with transaction.atomic():
        for stakeholder in stakeholders:
            try:
                if action == 'activate':
                    stakeholder.status = 'active'
                    stakeholder.save()
                elif action == 'deactivate':
                    stakeholder.status = 'inactive'
                    stakeholder.save()
                elif action == 'update_status':
                    new_status = serializer.validated_data.get('new_status')
                    if new_status:
                        stakeholder.status = new_status
                        stakeholder.save()
                elif action == 'update_authority':
                    new_authority = serializer.validated_data.get('new_authority_level')
                    if new_authority:
                        stakeholder.authority_level = new_authority
                        stakeholder.save()
                elif action == 'delete':
                    stakeholder.delete()
                
                results['success_count'] += 1
            except Exception as e:
                results['error_count'] += 1
                results['errors'].append({
                    'stakeholder_id': stakeholder.id,
                    'error': str(e)
                })
    
    return Response({
        'message': f'Bulk action "{action}" completed',
        'results': results
    })


@api_view(['GET'])
@permission_classes([HasPermission('planning.view')])
def stakeholder_statistics(request):
    """
    Get stakeholder statistics and analytics
    """
    procurement_plan_id = request.query_params.get('procurement_plan_id')
    
    # Base queryset with security scoping
    queryset = get_queryset_for_user(request.user, ProcurementStakeholder.objects.all(), action='view')
    if procurement_plan_id:
        queryset = queryset.filter(procurement_plan_id=procurement_plan_id)
    
    # Basic counts
    total_stakeholders = queryset.count()
    active_stakeholders = queryset.filter(status='active').count()
    primary_contacts = queryset.filter(primary_contact=True, status='active').count()
    
    # Role distribution
    role_distribution = list(queryset.values('role').annotate(count=Count('id')))
    
    # Authority level distribution
    authority_distribution = list(queryset.values('authority_level').annotate(count=Count('id')))
    
    # Involvement level distribution
    involvement_distribution = list(queryset.values('involvement_level').annotate(count=Count('id')))
    
    # Activity metrics
    activity_metrics = queryset.aggregate(
        avg_documents_reviewed=Avg('documents_reviewed'),
        avg_meetings_attended=Avg('meetings_attended'),
        avg_approvals_given=Avg('approvals_given')
    )
    
    # Status distribution
    status_distribution = list(queryset.values('status').annotate(count=Count('id')))
    
    # Recent activities (stakeholders with recent activity)
    recent_threshold = timezone.now() - timezone.timedelta(days=7)
    recent_active = queryset.filter(
        last_activity_date__gte=recent_threshold
    ).count()
    
    return Response({
        'total_stakeholders': total_stakeholders,
        'active_stakeholders': active_stakeholders,
        'primary_contacts': primary_contacts,
        'recent_active_stakeholders': recent_active,
        'role_distribution': role_distribution,
        'authority_distribution': authority_distribution,
        'involvement_distribution': involvement_distribution,
        'status_distribution': status_distribution,
        'activity_metrics': {
            'avg_documents_reviewed': round(activity_metrics['avg_documents_reviewed'] or 0, 2),
            'avg_meetings_attended': round(activity_metrics['avg_meetings_attended'] or 0, 2),
            'avg_approvals_given': round(activity_metrics['avg_approvals_given'] or 0, 2),
        }
    })


@api_view(['GET'])
@permission_classes([HasPermission('planning.view')])
def get_stakeholders_by_role(request):
    """
    Get stakeholders filtered by role for a specific procurement plan
    """
    procurement_plan_id = request.query_params.get('procurement_plan_id')
    role = request.query_params.get('role')
    
    if not procurement_plan_id or not role:
        return Response(
            {'error': 'procurement_plan_id and role are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Secure procurement plan access
        plans = get_queryset_for_user(request.user, ProcurementPlan.objects.all(), action='view')
        procurement_plan = get_object_or_404(plans, id=procurement_plan_id)
    except (ProcurementPlan.DoesNotExist, Exception):
        return Response(
            {'error': 'Procurement plan not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    stakeholders = ProcurementStakeholder.get_stakeholders_by_role(procurement_plan, role)
    serializer = ProcurementStakeholderSerializer(stakeholders, many=True)
    
    return Response({
        'procurement_plan': procurement_plan.policy_number,
        'role': role,
        'stakeholders': serializer.data
    })


@api_view(['GET'])
@permission_classes([HasPermission('planning.view')])
def get_primary_contacts(request):
    """
    Get primary contacts for a specific procurement plan
    """
    procurement_plan_id = request.query_params.get('procurement_plan_id')
    
    if not procurement_plan_id:
        return Response(
            {'error': 'procurement_plan_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Secure procurement plan access
        plans = get_queryset_for_user(request.user, ProcurementPlan.objects.all(), action='view')
        procurement_plan = get_object_or_404(plans, id=procurement_plan_id)
    except (ProcurementPlan.DoesNotExist, Exception):
        return Response(
            {'error': 'Procurement plan not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    primary_contacts = ProcurementStakeholder.get_primary_contacts(procurement_plan)
    serializer = ProcurementStakeholderSerializer(primary_contacts, many=True)
    
    return Response({
        'procurement_plan': procurement_plan.policy_number,
        'primary_contacts': serializer.data
    })


@api_view(['GET'])
@permission_classes([HasPermission('planning.view')])
def get_approvers(request):
    """
    Get all stakeholders who can approve documents for a specific procurement plan
    """
    procurement_plan_id = request.query_params.get('procurement_plan_id')
    
    if not procurement_plan_id:
        return Response(
            {'error': 'procurement_plan_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        procurement_plan = ProcurementPlan.objects.get(id=procurement_plan_id)
    except ProcurementPlan.DoesNotExist:
        return Response(
            {'error': 'Procurement plan not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    approvers = ProcurementStakeholder.get_approvers(procurement_plan)
    serializer = ProcurementStakeholderSerializer(approvers, many=True)
    
    return Response({
        'procurement_plan': procurement_plan.policy_number,
        'approvers': serializer.data
    })