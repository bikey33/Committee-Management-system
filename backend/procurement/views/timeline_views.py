from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ..models import Timeline
from ..serializers import TimelineSerializer


from users.utils import is_superadmin, get_queryset_for_user

from users.permissions import HasPermission

class TimelineListCreateView(generics.ListCreateAPIView):
    """
    List all timelines or create a new timeline.
    Users can only see timelines for procurement plans they have access to.
    """
    serializer_class = TimelineSerializer
    permission_classes = [IsAuthenticated, HasPermission('planning.view')]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), HasPermission('planning.manage')()]
        return [IsAuthenticated(), HasPermission('planning.view')()]

    def get_queryset(self):
        action = 'manage' if self.request.method == 'POST' else 'view'
        return get_queryset_for_user(self.request.user, Timeline.objects.all(), action=action).select_related('procurement_plan').order_by('-created_at')

    def perform_create(self, serializer):
        # Ensure the procurement plan exists and user has access to it
        procurement_plan = serializer.validated_data.get('procurement_plan')
        if procurement_plan:
            user = self.request.user
            if not is_superadmin(user):
                # Check if procurement plan's office is in user's office subtree
                if not (user.office and procurement_plan.office and procurement_plan.office in user.office.get_descendants(include_self=True)):
                    raise PermissionError("You don't have permission to create timelines for this procurement plan.")
        
        serializer.save()

    def get(self, request, *args, **kwargs):
        if not getattr(request.user, 'user_role', None):
            return Response(
                {'error': 'User must have a role to view timelines.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().get(request, *args, **kwargs)


class TimelineDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a timeline instance.
    Users can only access timelines for procurement plans they have permission to view.
    """
    serializer_class = TimelineSerializer
    permission_classes = [IsAuthenticated, HasPermission('planning.view')]

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), HasPermission('planning.manage')()]
        return [IsAuthenticated(), HasPermission('planning.view')()]

    def get_queryset(self):
        action = 'manage' if self.request.method in ['PUT', 'PATCH', 'DELETE'] else 'view'
        return get_queryset_for_user(self.request.user, Timeline.objects.all(), action=action).select_related('procurement_plan')

    def get(self, request, *args, **kwargs):
        if not getattr(request.user, 'user_role', None):
            return Response(
                {'error': 'User must have a role to view timeline details.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().get(request, *args, **kwargs)

    def perform_update(self, serializer):
        # Additional validation can be added here if needed
        serializer.save()

    def perform_destroy(self, instance):
        # Check if timeline can be safely deleted
        # Add any business logic validation here
        instance.delete()