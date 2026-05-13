from rest_framework import generics, status, filters, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, Sum, Max, Min
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta

from ..models import ProcurementRisk, ProcurementPlan
from ..serializers import ProcurementRiskSerializer, RiskCreateUpdateSerializer, RiskBulkActionSerializer
from users.models import CustomUser
from users.permissions import HasPermission
from users.utils import get_queryset_for_user


class RiskPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class RiskListCreateView(generics.ListCreateAPIView):
    """
    List all risks or create a new risk
    """
    queryset = ProcurementRisk.objects.select_related(
        'procurement_plan', 'owner'
    ).all()
    pagination_class = RiskPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'risk_type': ['exact', 'in'],
        'probability': ['exact', 'in'],
        'impact': ['exact', 'in'],
        'status': ['exact', 'in'],
        'procurement_plan': ['exact'],
        'owner': ['exact'],
        'identified_date': ['gte', 'lte'],
        'target_resolution_date': ['gte', 'lte'],
        'actual_resolution_date': ['gte', 'lte'],
        'risk_score': ['gte', 'lte'],
        'cost_impact': ['gte', 'lte'],
        'schedule_impact_days': ['gte', 'lte'],
    }
    search_fields = [
        'risk_title', 'risk_description', 'mitigation_strategy',
        'procurement_plan__project_name', 'procurement_plan__policy_number',
        'owner__name', 'owner__username'
    ]
    ordering_fields = [
        'risk_score', 'identified_date', 'target_resolution_date',
        'cost_impact', 'schedule_impact_days', 'status'
    ]
    ordering = ['-risk_score', '-identified_date']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RiskCreateUpdateSerializer
        return ProcurementRiskSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [HasPermission('planning.manage')()]
        return [HasPermission('planning.view')()]
    
    def get_queryset(self):
        action = 'manage' if self.request.method == 'POST' else 'view'
        queryset = get_queryset_for_user(self.request.user, super().get_queryset(), action=action)
        
        # Filter by procurement plan if specified
        procurement_plan_id = self.request.query_params.get('procurement_plan_id')
        if procurement_plan_id:
            queryset = queryset.filter(procurement_plan_id=procurement_plan_id)
        
        # Filter by risk level
        risk_level = self.request.query_params.get('risk_level')
        if risk_level:
            if risk_level == 'critical':
                queryset = queryset.filter(risk_score__gte=20)
            elif risk_level == 'high':
                queryset = queryset.filter(risk_score__gte=15, risk_score__lt=20)
            elif risk_level == 'medium':
                queryset = queryset.filter(risk_score__gte=9, risk_score__lt=15)
            elif risk_level == 'low':
                queryset = queryset.filter(risk_score__gte=4, risk_score__lt=9)
            elif risk_level == 'very_low':
                queryset = queryset.filter(risk_score__lt=4)
        
        # Filter active risks only
        active_only = self.request.query_params.get('active_only')
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(status__in=['identified', 'active'])
        
        # Filter overdue risks
        overdue_only = self.request.query_params.get('overdue_only')
        if overdue_only and overdue_only.lower() == 'true':
            today = timezone.now().date()
            queryset = queryset.filter(
                target_resolution_date__lt=today,
                status__in=['identified', 'active']
            )
        
        # Filter by owner
        owner_id = self.request.query_params.get('owner_id')
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)
        
        return queryset
    
    def perform_create(self, serializer):
        # Set the owner to current user if not specified
        if not serializer.validated_data.get('owner'):
            serializer.save(owner=self.request.user)
        else:
            serializer.save()


class RiskDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a risk
    """
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return RiskCreateUpdateSerializer
        return ProcurementRiskSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [HasPermission('planning.manage')()]
        return [HasPermission('planning.view')()]

    def get_queryset(self):
        action = 'manage' if self.request.method in ['PUT', 'PATCH', 'DELETE'] else 'view'
        return get_queryset_for_user(self.request.user, ProcurementRisk.objects.all(), action=action).select_related('procurement_plan', 'owner')


@api_view(['POST'])
@permission_classes([HasPermission('planning.manage')])
def bulk_risk_actions(request):
    """
    Perform bulk actions on multiple risks
    """
    serializer = RiskBulkActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    action = serializer.validated_data['action']
    risk_ids = serializer.validated_data['risk_ids']
    
    # Get risks with access control
    risks = get_queryset_for_user(request.user, ProcurementRisk.objects.filter(id__in=risk_ids), action='manage')
    if not risks.exists():
        return Response(
            {'error': 'No risks found with the provided IDs'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    results = {'success_count': 0, 'error_count': 0, 'errors': []}
    
    with transaction.atomic():
        for risk in risks:
            try:
                if action == 'update_status':
                    new_status = serializer.validated_data.get('new_status')
                    if new_status:
                        risk.status = new_status
                        if new_status == 'resolved' and not risk.actual_resolution_date:
                            risk.actual_resolution_date = timezone.now().date()
                        risk.save()
                elif action == 'assign_owner':
                    new_owner_id = serializer.validated_data.get('new_owner_id')
                    if new_owner_id:
                        risk.owner_id = new_owner_id
                        risk.save()
                elif action == 'update_priority':
                    new_probability = serializer.validated_data.get('new_probability')
                    new_impact = serializer.validated_data.get('new_impact')
                    if new_probability:
                        risk.probability = new_probability
                    if new_impact:
                        risk.impact = new_impact
                    risk.save()  # This will auto-recalculate risk_score
                elif action == 'delete':
                    risk.delete()
                
                results['success_count'] += 1
            except Exception as e:
                results['error_count'] += 1
                results['errors'].append({
                    'risk_id': risk.id,
                    'error': str(e)
                })
    
    return Response({
        'message': f'Bulk action "{action}" completed',
        'results': results
    })


@api_view(['GET'])
@permission_classes([HasPermission('planning.view')])
def risk_analytics(request):
    """
    Get comprehensive risk analytics and reporting
    """
    procurement_plan_id = request.query_params.get('procurement_plan_id')
    
    # Base queryset
    queryset = get_queryset_for_user(request.user, ProcurementRisk.objects.all(), action="view")
    if procurement_plan_id:
        queryset = queryset.filter(procurement_plan_id=procurement_plan_id)
    
    # Basic counts
    total_risks = queryset.count()
    active_risks = queryset.filter(status__in=['identified', 'active']).count()
    resolved_risks = queryset.filter(status='resolved').count()
    overdue_risks = queryset.filter(
        target_resolution_date__lt=timezone.now().date(),
        status__in=['identified', 'active']
    ).count()
    
    # Risk level distribution
    risk_levels = {
        'critical': queryset.filter(risk_score__gte=20).count(),
        'high': queryset.filter(risk_score__gte=15, risk_score__lt=20).count(),
        'medium': queryset.filter(risk_score__gte=9, risk_score__lt=15).count(),
        'low': queryset.filter(risk_score__gte=4, risk_score__lt=9).count(),
        'very_low': queryset.filter(risk_score__lt=4).count(),
    }
    
    # Risk type distribution
    risk_type_distribution = list(queryset.values('risk_type').annotate(count=Count('id')))
    
    # Status distribution
    status_distribution = list(queryset.values('status').annotate(count=Count('id')))
    
    # Impact analysis
    impact_metrics = queryset.aggregate(
        total_cost_impact=Sum('cost_impact'),
        avg_cost_impact=Avg('cost_impact'),
        max_cost_impact=Max('cost_impact'),
        total_schedule_impact=Sum('schedule_impact_days'),
        avg_schedule_impact=Avg('schedule_impact_days'),
        max_schedule_impact=Max('schedule_impact_days'),
        avg_risk_score=Avg('risk_score'),
        max_risk_score=Max('risk_score')
    )
    
    # Timeline analysis
    resolution_metrics = queryset.filter(actual_resolution_date__isnull=False).aggregate(
        avg_resolution_days=Avg('actual_resolution_date') - Avg('identified_date')
    )
    
    # Top risks (highest risk scores)
    top_risks = list(queryset.order_by('-risk_score')[:5].values(
        'id', 'risk_title', 'risk_score', 'status', 'risk_type'
    ))
    
    # Recent risks (last 30 days)
    recent_threshold = timezone.now() - timedelta(days=30)
    recent_risks = queryset.filter(identified_date__gte=recent_threshold).count()
    
    # Mitigation progress
    risks_with_strategy = queryset.exclude(mitigation_strategy='').count()
    risks_with_actions = queryset.exclude(mitigation_actions=[]).count()
    
    return Response({
        'summary': {
            'total_risks': total_risks,
            'active_risks': active_risks,
            'resolved_risks': resolved_risks,
            'overdue_risks': overdue_risks,
            'recent_risks': recent_risks,
            'resolution_rate': round((resolved_risks / total_risks * 100) if total_risks > 0 else 0, 2)
        },
        'risk_levels': risk_levels,
        'distributions': {
            'risk_types': risk_type_distribution,
            'status': status_distribution
        },
        'impact_analysis': {
            'total_cost_impact': float(impact_metrics['total_cost_impact'] or 0),
            'avg_cost_impact': round(float(impact_metrics['avg_cost_impact'] or 0), 2),
            'max_cost_impact': float(impact_metrics['max_cost_impact'] or 0),
            'total_schedule_impact_days': impact_metrics['total_schedule_impact'] or 0,
            'avg_schedule_impact_days': round(float(impact_metrics['avg_schedule_impact'] or 0), 1),
            'max_schedule_impact_days': impact_metrics['max_schedule_impact'] or 0,
            'avg_risk_score': round(float(impact_metrics['avg_risk_score'] or 0), 2),
            'max_risk_score': float(impact_metrics['max_risk_score'] or 0)
        },
        'mitigation_progress': {
            'risks_with_strategy': risks_with_strategy,
            'risks_with_actions': risks_with_actions,
            'strategy_coverage': round((risks_with_strategy / total_risks * 100) if total_risks > 0 else 0, 2),
            'action_coverage': round((risks_with_actions / total_risks * 100) if total_risks > 0 else 0, 2)
        },
        'top_risks': top_risks
    })


@api_view(['GET'])
@permission_classes([HasPermission('planning.view')])
def risk_dashboard(request):
    """
    Get risk dashboard data for visualization
    """
    procurement_plan_id = request.query_params.get('procurement_plan_id')
    
    # Base queryset
    queryset = get_queryset_for_user(request.user, ProcurementRisk.objects.all(), action="view")
    if procurement_plan_id:
        queryset = queryset.filter(procurement_plan_id=procurement_plan_id)
    
    # Risk trend over time (last 6 months)
    six_months_ago = timezone.now() - timedelta(days=180)
    risk_trend = []
    for i in range(6):
        month_start = six_months_ago + timedelta(days=30 * i)
        month_end = month_start + timedelta(days=30)
        monthly_count = queryset.filter(
            identified_date__gte=month_start,
            identified_date__lt=month_end
        ).count()
        risk_trend.append({
            'month': month_start.strftime('%Y-%m'),
            'count': monthly_count
        })
    
    # Risk heat map (probability vs impact)
    heat_map_data = []
    for prob in ['very_low', 'low', 'medium', 'high', 'very_high']:
        for impact in ['negligible', 'minor', 'moderate', 'major', 'critical']:
            count = queryset.filter(probability=prob, impact=impact).count()
            if count > 0:
                heat_map_data.append({
                    'probability': prob,
                    'impact': impact,
                    'count': count
                })
    
    # Risk ownership distribution
    ownership_data = list(queryset.exclude(owner__isnull=True).values(
        'owner__name'
    ).annotate(count=Count('id')).order_by('-count')[:10])
    
    # Resolution timeline analysis
    resolved_risks = queryset.filter(
        actual_resolution_date__isnull=False,
        identified_date__isnull=False
    )
    
    resolution_timeline = []
    for risk in resolved_risks:
        days_to_resolve = (risk.actual_resolution_date - risk.identified_date.date()).days
        resolution_timeline.append({
            'risk_id': risk.id,
            'risk_title': risk.risk_title,
            'days_to_resolve': days_to_resolve,
            'risk_type': risk.risk_type
        })
    
    return Response({
        'risk_trend': risk_trend,
        'heat_map': heat_map_data,
        'ownership_distribution': ownership_data,
        'resolution_timeline': resolution_timeline[:20]  # Limit to 20 most recent
    })


@api_view(['POST'])
@permission_classes([HasPermission('planning.manage')])
def update_risk_status(request, pk):
    """
    Update risk status with automatic date handling
    """
    # Get risk with access control
    risk = get_object_or_404(
        get_queryset_for_user(request.user, ProcurementRisk.objects.all(), action='manage'),
        pk=pk
    )
    
    new_status = request.data.get('status')
    notes = request.data.get('notes', '')
    
    if not new_status:
        return Response(
            {'error': 'Status is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate status
    valid_statuses = [choice[0] for choice in ProcurementRisk.STATUS_CHOICES]
    if new_status not in valid_statuses:
        return Response(
            {'error': f'Invalid status. Must be one of: {valid_statuses}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Update status
    old_status = risk.status
    risk.status = new_status
    
    # Set resolution date if resolved
    if new_status == 'resolved' and not risk.actual_resolution_date:
        risk.actual_resolution_date = timezone.now().date()
    
    risk.save()
    
    # Log the status change if needed
    # This could be extended to create activity logs
    
    serializer = ProcurementRiskSerializer(risk)
    return Response({
        'message': f'Risk status updated from {old_status} to {new_status}',
        'risk': serializer.data
    })


@api_view(['GET'])
@permission_classes([HasPermission('planning.view')])
def get_risk_matrix(request):
    """
    Get risk matrix data for visualization
    """
    procurement_plan_id = request.query_params.get('procurement_plan_id')
    
    # Base queryset
    queryset = get_queryset_for_user(request.user, ProcurementRisk.objects.all(), action="view")
    if procurement_plan_id:
        queryset = queryset.filter(procurement_plan_id=procurement_plan_id)
    
    # Only include active risks
    queryset = queryset.filter(status__in=['identified', 'active'])
    
    matrix_data = []
    
    for risk in queryset:
        matrix_data.append({
            'id': risk.id,
            'title': risk.risk_title,
            'type': risk.risk_type,
            'probability': risk.probability,
            'impact': risk.impact,
            'risk_score': float(risk.risk_score),
            'risk_level': risk.get_risk_level(),
            'owner': risk.owner.name if risk.owner else None,
            'target_date': risk.target_resolution_date.isoformat() if risk.target_resolution_date else None
        })
    
    return Response({
        'matrix_data': matrix_data,
        'probability_levels': ProcurementRisk.PROBABILITY_LEVELS,
        'impact_levels': ProcurementRisk.IMPACT_LEVELS
    })