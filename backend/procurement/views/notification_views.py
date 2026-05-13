from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from django.db import models
from django.utils import timezone
from ..models import ProcurementNotification
from ..serializers import ProcurementNotificationSerializer, NotificationCreateSerializer


from users.utils import is_superadmin, get_queryset_for_user

class NotificationListCreateView(generics.ListCreateAPIView):
    """
    List all notifications or create a new notification.
    Users can only see notifications for procurement plans they have access to.
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return NotificationCreateSerializer
        return ProcurementNotificationSerializer

    def get_queryset(self):
        user = self.request.user
        if not getattr(user, 'user_role', None):
            return ProcurementNotification.objects.none()

        # Use scoping helper and add directly addressed notifications
        base_qs = get_queryset_for_user(user, ProcurementNotification.objects.all(), action='view')
        queryset = (base_qs | ProcurementNotification.objects.filter(recipient=user)).distinct()
        
        queryset = queryset.select_related('procurement_plan', 'sender', 'recipient').order_by('-created_at')
        
        # Optional filtering by read status
        is_read = self.request.query_params.get('is_read', None)
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')
            
        # Optional filtering by notification type
        notification_type = self.request.query_params.get('notification_type', None)
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
            
        # Optional filtering by priority
        priority = self.request.query_params.get('priority', None)
        if priority:
            queryset = queryset.filter(priority=priority)
            
        # Optional filtering by procurement plan
        procurement_plan_id = self.request.query_params.get('procurement_plan', None)
        if procurement_plan_id:
            queryset = queryset.filter(procurement_plan_id=procurement_plan_id)
            
        # Optional filtering by recipient
        recipient_id = self.request.query_params.get('recipient', None)
        if recipient_id:
            queryset = queryset.filter(recipient_id=recipient_id)
            
        # Optional filtering by date range
        date_from = self.request.query_params.get('date_from', None)
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
            
        date_to = self.request.query_params.get('date_to', None)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
            
        # Hide expired notifications by default
        show_expired = self.request.query_params.get('show_expired', 'false')
        if show_expired.lower() != 'true':
            queryset = queryset.filter(
                models.Q(dismissed_at__isnull=True)
            )

        return queryset

    def perform_create(self, serializer):
        # Ensure the procurement plan exists and user has access to it
        procurement_plan = serializer.validated_data.get('procurement_plan')
        if procurement_plan:
            user = self.request.user
            # Use get_queryset_for_user to verify management access to the plan
            if not get_queryset_for_user(user, ProcurementPlan.objects.filter(pk=procurement_plan.pk), action='manage').exists():
                raise PermissionError("You don't have permission to create notifications for this procurement plan.")
        
        serializer.save(sender=self.request.user)

    def get(self, request, *args, **kwargs):
        if not getattr(request.user, 'user_role', None):
            return Response(
                {'error': 'User must have a role to view notifications.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().get(request, *args, **kwargs)


class NotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a notification instance.
    Users can only access notifications for procurement plans they have permission to view.
    """
    serializer_class = ProcurementNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not getattr(user, 'user_role', None):
            return ProcurementNotification.objects.none()

        base_qs = get_queryset_for_user(user, ProcurementNotification.objects.all())
        return (base_qs | ProcurementNotification.objects.filter(recipient=user)).distinct().select_related('procurement_plan', 'sender', 'recipient')

    def get(self, request, *args, **kwargs):
        if not getattr(request.user, 'user_role', None):
            return Response(
                {'error': 'User must have a role to view notification details.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().get(request, *args, **kwargs)

    def perform_update(self, serializer):
        # Additional validation can be added here if needed
        serializer.save()

    def perform_destroy(self, instance):
        # Check if notification can be safely deleted
        # Only allow deletion by the recipient or sender
        user = self.request.user
        if instance.recipient != user and instance.sender != user and not user.is_superuser:
            raise PermissionError("You can only delete your own notifications.")
        instance.delete()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_as_read(request, pk):
    """
    Mark a notification as read.
    """
    if not getattr(request.user, 'user_role', None):
        return Response(
            {'error': 'User must have a role to mark notifications as read.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user = request.user
    
    # Get notification with access control
    base_qs = get_queryset_for_user(user, ProcurementNotification.objects.all())
    notification = get_object_or_404(
        (base_qs | ProcurementNotification.objects.filter(recipient=user)).distinct(),
        pk=pk
    )
    
    # Only allow the recipient to mark as read
    if notification.recipient != user and not user.is_superuser:
        return Response(
            {'error': 'You can only mark your own notifications as read.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    notification.mark_as_read()
    
    serializer = ProcurementNotificationSerializer(notification, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dismiss_notification(request, pk):
    """
    Dismiss a notification.
    """
    if not getattr(request.user, 'user_role', None):
        return Response(
            {'error': 'User must have a role to dismiss notifications.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user = request.user
    
    # Get notification with access control
    base_qs = get_queryset_for_user(user, ProcurementNotification.objects.all())
    notification = get_object_or_404(
        (base_qs | ProcurementNotification.objects.filter(recipient=user)).distinct(),
        pk=pk
    )
    
    # Only allow the recipient to dismiss
    if notification.recipient != user and not user.is_superuser:
        return Response(
            {'error': 'You can only dismiss your own notifications.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    notification.dismiss()
    
    serializer = ProcurementNotificationSerializer(notification, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_as_read(request):
    """
    Mark all unread notifications for the current user as read.
    """
    if not getattr(request.user, 'user_role', None):
        return Response(
            {'error': 'User must have a role to mark notifications as read.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user = request.user
    
    # Get all unread notifications for the user
    notifications = ProcurementNotification.objects.filter(
        recipient=user,
        is_read=False
    )
    
    # Mark all as read
    updated_count = notifications.update(
        is_read=True,
        # read_at=timezone.now() # Model doesn't have read_at, it has updated_at via save() but update() bypasses it
    )
    
    return Response({
        'message': f'{updated_count} notifications marked as read.',
        'updated_count': updated_count
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notification_stats(request):
    """
    Get notification statistics for the current user.
    """
    if not getattr(request.user, 'user_role', None):
        return Response(
            {'error': 'User must have a role to view notification stats.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user = request.user
    
    # Get notifications for the user
    user_notifications = ProcurementNotification.objects.filter(
        recipient=user
    ).exclude(dismissed_at__isnull=False)
    
    # Calculate stats
    stats = {
        'total_notifications': user_notifications.count(),
        'unread_notifications': user_notifications.filter(is_read=False).count(),
        'high_priority_unread': user_notifications.filter(
            is_read=False, 
            notification_type__in=['error', 'warning', 'deadline_alert']
        ).count(),
        'notifications_by_type': {},
        'recent_notifications': user_notifications.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).count()
    }
    
    # Group by notification type
    type_counts = user_notifications.values('notification_type').annotate(
        count=models.Count('id')
    ).order_by('-count')
    
    for item in type_counts:
        stats['notifications_by_type'][item['notification_type']] = item['count']
    
    return Response(stats, status=status.HTTP_200_OK)