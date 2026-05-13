from rest_framework import serializers
from ..models.integration import ExternalIntegration


class ExternalIntegrationSerializer(serializers.ModelSerializer):
    """Serializer for ExternalIntegration model"""
    
    sync_age_days = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    sync_status_display = serializers.CharField(source='get_sync_status_display', read_only=True)
    
    class Meta:
        model = ExternalIntegration
        fields = [
            'id',
            'system_name',
            'sync_status',
            'sync_status_display',
            'last_sync',
            'api_endpoint',
            'configuration',
            'error_message',
            'created_at',
            'updated_at',
            'sync_age_days',
            'is_active'
        ]
        read_only_fields = ['created_at', 'updated_at', 'sync_age_days', 'is_active']
    
    def validate_system_name(self, value):
        """Validate system name is unique"""
        if self.instance and self.instance.system_name == value:
            return value
            
        if ExternalIntegration.objects.filter(system_name=value).exists():
            raise serializers.ValidationError("A system with this name already exists.")
        return value
    
    def validate_configuration(self, value):
        """Validate configuration is a valid dict"""
        if value is not None and not isinstance(value, dict):
            raise serializers.ValidationError("Configuration must be a valid JSON object.")
        return value


class IntegrationAnalyticsSerializer(serializers.Serializer):
    """Serializer for integration analytics data"""
    
    total_integrations = serializers.IntegerField()
    active_integrations = serializers.IntegerField()
    failed_integrations = serializers.IntegerField()
    pending_integrations = serializers.IntegerField()
    average_sync_age = serializers.FloatField()
    last_24h_syncs = serializers.IntegerField()
    status_breakdown = serializers.DictField()


class IntegrationTestResultSerializer(serializers.Serializer):
    """Serializer for integration test results"""
    
    status = serializers.CharField()
    message = serializers.CharField()
    response_time = serializers.FloatField(required=False)


class BulkActionSerializer(serializers.Serializer):
    """Serializer for bulk integration actions"""
    
    integration_ids = serializers.ListField(child=serializers.IntegerField())
    action = serializers.ChoiceField(choices=['activate', 'deactivate', 'test_all'])