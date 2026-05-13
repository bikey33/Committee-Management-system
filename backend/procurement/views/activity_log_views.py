from rest_framework import generics, status, filters, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
from django.contrib.contenttypes.models import ContentType

from ..models import ActivityLog, ProcurementPlan
from ..serializers import ActivityLogSerializer, ActivityLogCreateSerializer
from django.http import HttpResponse
import csv
from users.models import CustomUser
from users.permissions import HasPermission
from users.utils import get_queryset_for_user


class ActivityLogPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class ActivityLogListCreateView(generics.ListCreateAPIView):
    """
    List all activity logs or create a new activity log
    """
    queryset = ActivityLog.objects.select_related(
        'user', 'procurement_plan', 'content_type'
    ).all()
    pagination_class = ActivityLogPagination
    permission_classes = [permissions.IsAuthenticated, HasPermission('planning.view')]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'action': ['exact', 'in'],
        'severity': ['exact', 'in'],
        'procurement_plan': ['exact'],
        'user': ['exact'],
        'is_system_action': ['exact'],
        'timestamp': ['gte', 'lte', 'date'],
        'content_type': ['exact'],
    }
    search_fields = [
        'action_description', 'user_display_name', 'details',
        'procurement_plan__project_name', 'procurement_plan__policy_number'
    ]
    ordering_fields = [
        'timestamp', 'action', 'severity', 'user_display_name'
    ]
    ordering = ['-timestamp']
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), HasPermission('planning.manage')()]
        return [permissions.IsAuthenticated(), HasPermission('planning.view')()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ActivityLogCreateSerializer
        return ActivityLogSerializer
    
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
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                queryset = queryset.filter(timestamp__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                queryset = queryset.filter(timestamp__lte=end_date)
            except ValueError:
                pass
        
        # Filter by action types
        action_types = self.request.query_params.get('action_types')
        if action_types:
            action_list = action_types.split(',')
            queryset = queryset.filter(action__in=action_list)
        
        # Filter by severity levels
        severity_levels = self.request.query_params.get('severity_levels')
        if severity_levels:
            severity_list = severity_levels.split(',')
            queryset = queryset.filter(severity__in=severity_list)
        
        # Filter for recent activities (last N days)
        recent_days = self.request.query_params.get('recent_days')
        if recent_days:
            try:
                days = int(recent_days)
                since_date = timezone.now() - timedelta(days=days)
                queryset = queryset.filter(timestamp__gte=since_date)
            except ValueError:
                pass
        
        # Filter for critical activities only
        critical_only = self.request.query_params.get('critical_only')
        if critical_only and critical_only.lower() == 'true':
            queryset = queryset.filter(severity__in=['critical', 'error'])
        
        # Filter for user activities only (exclude system actions)
        user_actions_only = self.request.query_params.get('user_actions_only')
        if user_actions_only and user_actions_only.lower() == 'true':
            queryset = queryset.filter(is_system_action=False)
        
        # Filter for system activities only
        system_actions_only = self.request.query_params.get('system_actions_only')
        if system_actions_only and system_actions_only.lower() == 'true':
            queryset = queryset.filter(is_system_action=True)
        
        return queryset
    
    def perform_create(self, serializer):
        # Capture request metadata
        request_meta = {
            'ip_address': self.get_client_ip(),
            'user_agent': self.request.META.get('HTTP_USER_AGENT', ''),
            'user': self.request.user if self.request.user.is_authenticated else None
        }
        serializer.save(**request_meta)
    
    def get_client_ip(self):
        """Get client IP address from request"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class ActivityLogDetailView(generics.RetrieveAPIView):
    """
    Retrieve a specific activity log entry
    """
    queryset = ActivityLog.objects.select_related(
        'user', 'procurement_plan', 'content_type'
    ).all()
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated, HasPermission('planning.view')]

    def get_queryset(self):
        return get_queryset_for_user(self.request.user, self.queryset, action='view')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, HasPermission('planning.manage')])
def create_activity_log(request):
    """
    Create a new activity log entry with full context
    """
    # Required fields
    procurement_plan_id = request.data.get('procurement_plan_id')
    action = request.data.get('action')
    description = request.data.get('description')
    
    if not all([procurement_plan_id, action]):
        return Response(
            {'error': 'procurement_plan_id and action are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Secure procurement plan access
        plans = get_queryset_for_user(request.user, ProcurementPlan.objects.all(), action='manage')
        procurement_plan = get_object_or_404(plans, id=procurement_plan_id)
    except (ProcurementPlan.DoesNotExist, Exception):
        return Response(
            {'error': 'Procurement plan not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Optional fields
    details = request.data.get('details', {})
    severity = request.data.get('severity', 'info')
    related_object_type = request.data.get('related_object_type')
    related_object_id = request.data.get('related_object_id')
    old_values = request.data.get('old_values', {})
    new_values = request.data.get('new_values', {})
    
    # Get related object if specified
    related_object = None
    if related_object_type and related_object_id:
        try:
            content_type = ContentType.objects.get(model=related_object_type.lower())
            model_class = content_type.model_class()
            related_object = model_class.objects.get(id=related_object_id)
        except (ContentType.DoesNotExist, AttributeError, Exception):
            pass  # Ignore if related object can't be found
    
    # Get client IP and user agent
    def get_client_ip():
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
    
    # Create the activity log
    log_entry = ActivityLog.log_activity(
        procurement_plan=procurement_plan,
        action=action,
        user=request.user,
        description=description,
        details=details,
        related_object=related_object,
        severity=severity,
        old_values=old_values,
        new_values=new_values,
        ip_address=get_client_ip(),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    serializer = ActivityLogSerializer(log_entry)
    return Response({
        'message': 'Activity log created successfully',
        'activity_log': serializer.data
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, HasPermission('planning.view')])
def activity_analytics(request):
    """
    Get activity analytics and statistics
    """
    procurement_plan_id = request.query_params.get('procurement_plan_id')
    days = int(request.query_params.get('days', 30))  # Default to last 30 days
    
    # Base queryset with security scoping
    queryset = get_queryset_for_user(request.user, ActivityLog.objects.all(), action='view')
    if procurement_plan_id:
        queryset = queryset.filter(procurement_plan_id=procurement_plan_id)
    
    # Filter by date range
    since_date = timezone.now() - timedelta(days=days)
    queryset = queryset.filter(timestamp__gte=since_date)
    
    # Basic counts
    total_activities = queryset.count()
    user_activities = queryset.filter(is_system_action=False).count()
    system_activities = queryset.filter(is_system_action=True).count()
    
    # Severity distribution
    severity_distribution = list(queryset.values('severity').annotate(count=Count('id')))
    
    # Action type distribution
    action_distribution = list(queryset.values('action').annotate(count=Count('id')).order_by('-count')[:10])
    
    # User activity distribution (top 10 most active users)
    user_distribution = list(queryset.exclude(user__isnull=True).values(
        'user__username', 'user_display_name'
    ).annotate(count=Count('id')).order_by('-count')[:10])
    
    # Daily activity trend
    daily_activities = []
    for i in range(days):
        day_start = since_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        day_count = queryset.filter(
            timestamp__gte=day_start,
            timestamp__lt=day_end
        ).count()
        daily_activities.append({
            'date': day_start.date().isoformat(),
            'count': day_count
        })
    
    # Hourly activity pattern (average activities per hour)
    hourly_pattern = []
    for hour in range(24):
        hour_count = queryset.filter(timestamp__hour=hour).count()
        hourly_pattern.append({
            'hour': hour,
            'avg_count': round(hour_count / days, 2) if days > 0 else 0
        })
    
    # Critical activities
    critical_activities = queryset.filter(severity__in=['critical', 'error']).count()
    
    # Most active procurement plans
    if not procurement_plan_id:
        top_plans = list(queryset.values(
            'procurement_plan__policy_number', 'procurement_plan__project_name'
        ).annotate(count=Count('id')).order_by('-count')[:5])
    else:
        top_plans = []
    
    return Response({
        'period_days': days,
        'summary': {
            'total_activities': total_activities,
            'user_activities': user_activities,
            'system_activities': system_activities,
            'critical_activities': critical_activities,
            'avg_daily_activities': round(total_activities / days, 2) if days > 0 else 0
        },
        'distributions': {
            'severity': severity_distribution,
            'actions': action_distribution,
            'users': user_distribution,
            'top_plans': top_plans
        },
        'trends': {
            'daily_activities': daily_activities,
            'hourly_pattern': hourly_pattern
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, HasPermission('planning.view')])
def get_recent_activities(request):
    """
    Get recent activities for a procurement plan
    """
    procurement_plan_id = request.query_params.get('procurement_plan_id')
    limit = int(request.query_params.get('limit', 50))
    
    if not procurement_plan_id:
        return Response(
            {'error': 'procurement_plan_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Secure procurement plan access
        plans = get_queryset_for_user(request.user, ProcurementPlan.objects.all(), action='view')
        procurement_plan = get_object_or_404(plans, id=procurement_plan_id)
    except ProcurementPlan.DoesNotExist:
        return Response(
            {'error': 'Procurement plan not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    activities = ActivityLog.get_recent_activities(procurement_plan, limit)
    serializer = ActivityLogSerializer(activities, many=True)
    
    return Response({
        'procurement_plan': procurement_plan.policy_number,
        'activities': serializer.data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, HasPermission('planning.view')])
def get_user_activities(request):
    """
    Get activities performed by a specific user
    """
    user_id = request.query_params.get('user_id')
    limit = int(request.query_params.get('limit', 100))
    
    if not user_id:
        user_id = request.user.id  # Default to current user
    
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Secure activity log access
    activities = get_queryset_for_user(request.user, ActivityLog.objects.filter(user=user), action='view').order_by('-timestamp')[:limit]
    serializer = ActivityLogSerializer(activities, many=True)
    
    return Response({
        'user': user.username,
        'activities': serializer.data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, HasPermission('planning.view')])
def get_activities_by_action(request):
    """
    Get all activities of a specific type
    """
    procurement_plan_id = request.query_params.get('procurement_plan_id')
    action_type = request.query_params.get('action_type')
    
    if not all([procurement_plan_id, action_type]):
        return Response(
            {'error': 'procurement_plan_id and action_type are required'},
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
    
    activities = ActivityLog.get_activities_by_action(procurement_plan, action_type)
    serializer = ActivityLogSerializer(activities, many=True)
    
    return Response({
        'procurement_plan': procurement_plan.policy_number,
        'action_type': action_type,
        'activities': serializer.data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, HasPermission('planning.view')])
def get_critical_activities(request):
    """
    Get critical and error activities
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
    except ProcurementPlan.DoesNotExist:
        return Response(
            {'error': 'Procurement plan not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    activities = ActivityLog.get_critical_activities(procurement_plan)
    serializer = ActivityLogSerializer(activities, many=True)
    
    return Response({
        'procurement_plan': procurement_plan.policy_number,
        'critical_activities': serializer.data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, HasPermission('planning.view')])
def export_activity_logs(request):
    """
    Export activity logs in various formats
    """
    procurement_plan_id = request.query_params.get('procurement_plan_id')
    format_type = request.query_params.get('format', 'json')  # json, csv
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    # Base queryset with security scoping
    queryset = get_queryset_for_user(request.user, ActivityLog.objects.select_related('user', 'procurement_plan'), action='view')
    
    if procurement_plan_id:
        queryset = queryset.filter(procurement_plan_id=procurement_plan_id)
    
    # Apply date filters
    if start_date:
        try:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            queryset = queryset.filter(timestamp__gte=start_date)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            queryset = queryset.filter(timestamp__lte=end_date)
        except ValueError:
            pass
    
    activities = queryset[:1000]  # Limit to 1000 records for export
    
    if format_type == 'csv':
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="activity_logs.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Timestamp', 'Procurement Plan', 'Action', 'Description', 
            'User', 'Severity', 'IP Address'
        ])
        
        for activity in activities:
            writer.writerow([
                activity.timestamp.isoformat(),
                activity.procurement_plan.policy_number,
                activity.get_action_display(),
                activity.action_description,
                activity.user_display_name,
                activity.get_severity_display(),
                activity.ip_address or ''
            ])
        
        return response
    
    else:  # JSON format
        serializer = ActivityLogSerializer(activities, many=True)
        return Response({
            'total_count': queryset.count(),
            'exported_count': len(activities),
            'activities': serializer.data
        })