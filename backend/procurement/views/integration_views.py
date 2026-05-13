from django.db.models import Count, Q, Avg
from django.utils import timezone
from django.http import JsonResponse
from rest_framework import viewsets, status, permissions
from users.permissions import HasPermission
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import timedelta
import requests

from ..models.integration import ExternalIntegration
from ..serializers import ExternalIntegrationSerializer


class ExternalIntegrationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing external integrations"""
    queryset = ExternalIntegration.objects.all()
    serializer_class = ExternalIntegrationSerializer
    permission_classes = [permissions.IsAuthenticated, HasPermission('planning.view')]

    def get_permissions(self):
        """Map integration actions to granular permissions"""
        if self.action in ['list', 'retrieve', 'analytics']:
            return [permissions.IsAuthenticated(), HasPermission('planning.view')()]
        return [permissions.IsAuthenticated(), HasPermission('settings.system_config')()]
    
    def get_queryset(self):
        """Filter integrations based on query parameters"""
        queryset = super().get_queryset()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(sync_status=status_filter)
        
        # Filter by sync age
        sync_age = self.request.query_params.get('sync_age')
        if sync_age:
            cutoff_date = timezone.now() - timedelta(days=int(sync_age))
            queryset = queryset.filter(last_sync__gte=cutoff_date)
        
        # Filter by errors
        has_errors = self.request.query_params.get('has_errors')
        if has_errors and has_errors.lower() == 'true':
            queryset = queryset.exclude(error_message='')
        
        return queryset.order_by('system_name')

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get integration analytics and statistics"""
        integrations = ExternalIntegration.objects.all()
        
        # Calculate 24h sync count
        last_24h = timezone.now() - timedelta(hours=24)
        last_24h_syncs = integrations.filter(last_sync__gte=last_24h).count()
        
        # Calculate average sync age
        active_integrations = integrations.filter(
            sync_status='active',
            last_sync__isnull=False
        )
        
        avg_sync_age = 0
        if active_integrations.exists():
            total_age = sum(
                (timezone.now() - integration.last_sync).days 
                for integration in active_integrations 
                if integration.last_sync
            )
            avg_sync_age = round(total_age / active_integrations.count(), 1)
        
        # Status counts
        status_counts = integrations.values('sync_status').annotate(
            count=Count('id')
        )
        
        analytics_data = {
            'total_integrations': integrations.count(),
            'active_integrations': integrations.filter(sync_status='active').count(),
            'failed_integrations': integrations.filter(sync_status='failed').count(),
            'pending_integrations': integrations.filter(sync_status='pending').count(),
            'average_sync_age': avg_sync_age,
            'last_24h_syncs': last_24h_syncs,
            'status_breakdown': {item['sync_status']: item['count'] for item in status_counts}
        }
        
        return Response(analytics_data)

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test integration connection"""
        integration = self.get_object()
        
        if not integration.api_endpoint:
            return Response(
                {'error': 'No API endpoint configured for this integration'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Attempt to connect to the endpoint
            response = requests.get(
                integration.api_endpoint,
                timeout=10,
                headers={'User-Agent': 'ProcurementSystem/1.0'}
            )
            
            if response.status_code == 200:
                integration.sync_status = 'active'
                integration.error_message = ''
                integration.save()
                
                return Response({
                    'status': 'success',
                    'message': 'Connection test successful',
                    'response_time': response.elapsed.total_seconds()
                })
            else:
                error_msg = f'HTTP {response.status_code}: Connection failed'
                integration.mark_sync_failed(error_msg)
                
                return Response({
                    'status': 'failed',
                    'message': error_msg
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except requests.exceptions.RequestException as e:
            error_msg = f'Connection error: {str(e)}'
            integration.mark_sync_failed(error_msg)
            
            return Response({
                'status': 'failed',
                'message': error_msg
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Trigger manual sync for integration"""
        integration = self.get_object()
        
        # In a real implementation, this would trigger the actual sync process
        # For now, we'll simulate a sync operation
        try:
            # Simulate sync logic here
            # This would typically involve calling external APIs and updating local data
            
            integration.mark_sync_success()
            
            return Response({
                'status': 'success',
                'message': f'Sync triggered successfully for {integration.system_name}',
                'last_sync': integration.last_sync
            })
            
        except Exception as e:
            error_msg = f'Sync failed: {str(e)}'
            integration.mark_sync_failed(error_msg)
            
            return Response({
                'status': 'failed',
                'message': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def sync_success(self, request, pk=None):
        """Mark sync as successful"""
        integration = self.get_object()
        integration.mark_sync_success()
        
        return Response({
            'status': 'success',
            'message': f'Integration {integration.system_name} marked as successfully synced'
        })

    @action(detail=True, methods=['post'])
    def sync_failed(self, request, pk=None):
        """Mark sync as failed with error message"""
        integration = self.get_object()
        error_message = request.data.get('error_message', 'Sync failed')
        
        integration.mark_sync_failed(error_message)
        
        return Response({
            'status': 'failed',
            'message': f'Integration {integration.system_name} marked as failed',
            'error_message': error_message
        })

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Update integration status"""
        integration = self.get_object()
        new_status = request.data.get('sync_status')
        error_message = request.data.get('error_message', '')
        
        if new_status not in dict(ExternalIntegration.SYNC_STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        integration.sync_status = new_status
        if error_message:
            integration.error_message = error_message
        integration.save()
        
        serializer = self.get_serializer(integration)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def update_configuration(self, request, pk=None):
        """Update integration configuration"""
        integration = self.get_object()
        configuration = request.data.get('configuration', {})
        
        if not isinstance(configuration, dict):
            return Response(
                {'error': 'Configuration must be a valid JSON object'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        integration.configuration = configuration
        integration.save()
        
        serializer = self.get_serializer(integration)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """Perform bulk actions on multiple integrations"""
        integration_ids = request.data.get('integration_ids', [])
        action_type = request.data.get('action')
        
        if not integration_ids:
            return Response(
                {'error': 'No integration IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        integrations = ExternalIntegration.objects.filter(id__in=integration_ids)
        
        if action_type == 'activate':
            integrations.update(sync_status='active')
        elif action_type == 'deactivate':
            integrations.update(sync_status='inactive')
        elif action_type == 'test_all':
            # Test all selected integrations
            results = []
            for integration in integrations:
                # Simulate test logic
                results.append({
                    'id': integration.id,
                    'name': integration.system_name,
                    'status': 'tested'
                })
            return Response({'results': results})
        else:
            return Response(
                {'error': 'Invalid action type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'message': f'Bulk {action_type} completed for {integrations.count()} integrations'
        })