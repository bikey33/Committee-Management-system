"""
DEPRECATED: These class-based views are superseded by the unified
ProcurementPlanViewSet in base_views.py which now includes full
role-hierarchy-based access control.

These views are kept for backward compatibility but should NOT be
registered in new URL patterns. Use ProcurementPlanViewSet instead.
"""

import logging
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from ..models import ProcurementPlan, Timeline
from ..serializers import ProcurementPlanSerializer, ProcurementPlanCreateSerializer
from users.models import CustomUser
from users.utils import is_superadmin, get_queryset_for_user
from datetime import date, timedelta
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError


class ProcurementPlanListCreateView(generics.ListCreateAPIView):
    queryset = ProcurementPlan.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProcurementPlanCreateSerializer
        return ProcurementPlanSerializer

    def get_queryset(self):
        action = 'manage' if self.request.method == 'POST' else 'view'
        return get_queryset_for_user(self.request.user, ProcurementPlan.objects.all(), action=action).order_by('-created_at')

    def perform_create(self, serializer):
        logger = logging.getLogger(__name__)
        logger.info("Setting owner to: %s", self.request.user)
        logger.info(
            "Request data quarterly_targets: %s",
            self.request.data.get('quarterly_targets', [])
        )
        plan = serializer.save(owner=self.request.user)
        logger.info("Created plan with owner: %s", plan.owner)

        targets = plan.quarterly_targets.all()
        logger.info("Quarterly targets created: %s", targets.count())
        for target in targets:
            details = target.target_details or 'N/A'
            logger.info("  - %s: %s", target.quarter, details[:50])
        # Auto-generate timeline for new plan
        self.generate_timeline_for_plan(plan)

    def generate_timeline_for_plan(self, plan):
        """Generate default timeline entries for a procurement plan"""
        generate_timeline_for_plan(plan)

    def create(self, request, *args, **kwargs):
        print(f"CREATE request data: {request.data}")
        print(f"User: {request.user}")
        serializer = self.get_serializer(data=request.data)
        
        # Debug validation errors
        if not serializer.is_valid():
            print(f"Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_create(serializer)
        except ValidationError as exc:
            detail = getattr(exc, 'detail', str(exc))
            return Response({'error': detail}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as exc:
            return Response({'error': 'Integrity error creating procurement plan.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logging.getLogger(__name__).exception("Error creating procurement plan")
            return Response({'error': 'Server error creating procurement plan.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Return the created object using the read serializer
        created_plan = serializer.instance
        response_serializer = ProcurementPlanSerializer(created_plan)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().get(request, *args, **kwargs)


class ProcurementPlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProcurementPlan.objects.all()
    serializer_class = ProcurementPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        action = 'manage' if self.request.method in ['PUT', 'PATCH', 'DELETE'] else 'view'
        return get_queryset_for_user(self.request.user, ProcurementPlan.objects.all(), action=action)

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().get(request, *args, **kwargs)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_timeline(request, pk):
    """Generate timeline for an existing procurement plan"""
    try:
        plan = ProcurementPlan.objects.get(pk=pk)
        
        # Check if user has permission to modify this plan
        if not get_queryset_for_user(request.user, ProcurementPlan.objects.filter(pk=pk), action='manage').exists():
            return Response(
                {'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Clear existing timelines if regenerating
        plan.timelines.all().delete()
        
        # Generate new timeline
        generate_timeline_for_plan(plan)
        
        # Return updated plan data
        serializer = ProcurementPlanSerializer(plan)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except ProcurementPlan.DoesNotExist:
        return Response(
            {'error': 'Procurement plan not found.'},
            status=status.HTTP_404_NOT_FOUND
        )


def generate_timeline_for_plan(plan):
    """Generate default timeline entries for a procurement plan"""
    stage_configs = [
        {'stage': 'planning', 'duration_days': 14, 'is_milestone': False, 'description': 'Planning phase'},
        {'stage': 'specification', 'duration_days': 21, 'is_milestone': True, 'description': 'Specification development'},
        {'stage': 'tender', 'duration_days': 30, 'is_milestone': True, 'description': 'Tender preparation and publication'},
        {'stage': 'committee', 'duration_days': 7, 'is_milestone': False, 'description': 'Committee formation'},
        {'stage': 'bidding', 'duration_days': 28, 'is_milestone': True, 'description': 'Bid submission period'},
        {'stage': 'evaluation', 'duration_days': 21, 'is_milestone': True, 'description': 'Bid evaluation'},
        {'stage': 'contract', 'duration_days': 14, 'is_milestone': True, 'description': 'Contract award'},
        {'stage': 'complaint', 'duration_days': 7, 'is_milestone': False, 'description': 'Complaint period'},
        {'stage': 'management', 'duration_days': 90, 'is_milestone': False, 'description': 'Contract management'},
    ]
    
    current_date = date.today()
    
    for i, config in enumerate(stage_configs):
        start_date = current_date + timedelta(days=sum(s['duration_days'] for s in stage_configs[:i]))
        end_date = start_date + timedelta(days=config['duration_days'])
        
        Timeline.objects.create(
            procurement_plan=plan,
            stage=config['stage'],
            planned_start_date=start_date,
            planned_end_date=end_date,
            is_milestone=config['is_milestone'],
            milestone_description=config['description'],
            is_critical_path=config['stage'] in ['specification', 'tender', 'bidding', 'evaluation', 'contract'],
            buffer_days=2 if config['is_milestone'] else 0,
            status='scheduled' if i > 0 else 'active',
            auto_calculated=True
        )
