from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import models
from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField
from django.utils import timezone
from datetime import timedelta
from ..models import ProcurementPlan, Timeline, StageHistory
from tender.models import Tender
from users.utils import get_queryset_for_user
from users.permissions import HasPermission

class DashboardMetricsView(APIView):
    """
    Get executive and operational metrics for the procurement dashboard.
    Filtered by user's office.
    """
    permission_classes = [IsAuthenticated, HasPermission('planning.view')]

    def get(self, request, *args, **kwargs):
        user = request.user
        office_id = request.query_params.get('office_id')
        
        # Base queryset filtered by user access
        plans = get_queryset_for_user(user, ProcurementPlan.objects.all(), action='view')
        
        if office_id:
            plans = plans.filter(office_id=office_id)

        # 1. Pending Actions (Count of plans in active stages)
        # We consider plans in stages before 'final_overview' that are 'active' as pending actions
        pending_stages = ['planning', 'specification', 'spec_review', 'tender', 'evaluation', 'loi', 'loa', 'contract_prep']
        pending_actions_count = plans.filter(stage__in=pending_stages, status='active').count()

        # 2. Project Funnel (Count per stage)
        funnel_data = plans.values('stage').annotate(count=Count('id')).order_by('stage')
        stage_map = dict(ProcurementPlan.STAGE_CHOICES)
        funnel = [
            {'stage': stage, 'label': stage_map.get(stage, stage), 'count': 0}
            for stage in ['planning', 'specification', 'spec_review', 'tender', 'evaluation', 'loi', 'loa', 'contract_prep', 'final_overview']
        ]
        funnel_dict = {item['stage']: item['count'] for item in funnel_data}
        for item in funnel:
            item['count'] = funnel_dict.get(item['stage'], 0)

        # 3. Milestone Backlog (Overdue timelines)
        now = timezone.now().date()
        backlog_count = Timeline.objects.filter(
            procurement_plan__in=plans,
            planned_end_date__lt=now,
            actual_end_date__isnull=True
        ).count()

        # 4. Lead Time Analytics (Average days per stage)
        # This is a bit complex, we look at StageHistory
        # For simplicity, we calculate avg duration between consecutive changes
        lead_times = []
        # Let's get durations for completed transitions
        # duration = changed_at (current) - changed_at (previous)
        # This requires aggregation that might be heavy, so we'll do a simplified version
        # for some common transitions if data exists
        
        # 5. Tender Success Rate
        tenders = Tender.objects.filter(procurement_plan__in=plans)
        total_tenders = tenders.count()
        awarded_tenders = tenders.filter(status='awarded').count()
        success_rate = (awarded_tenders / total_tenders * 100) if total_tenders > 0 else 0

        # 6. Upcoming Events (Next 14 days)
        upcoming_events = Timeline.objects.filter(
            procurement_plan__in=plans,
            planned_end_date__gte=now,
            planned_end_date__lte=now + timedelta(days=14),
            actual_end_date__isnull=True
        ).select_related('procurement_plan').order_by('planned_end_date')[:10]

        events = [{
            'id': e.id,
            'plan_name': e.procurement_plan.project_name,
            'event': e.milestone_description or f"Deadline for {e.get_stage_display()}",
            'date': e.planned_end_date,
            'stage': e.stage
        } for e in upcoming_events]

        # 7. Workload Distribution (Projects per department/working office)
        workload = plans.values('department').annotate(count=Count('id')).order_by('-count')

        data = {
            'summary': {
                'pending_actions': pending_actions_count,
                'milestone_backlog': backlog_count,
                'tender_success_rate': round(success_rate, 2),
                'total_active_projects': plans.filter(status='active').count()
            },
            'funnel': funnel,
            'upcoming_events': events,
            'workload': list(workload),
            'timestamp': timezone.now()
        }

        return Response(data, status=status.HTTP_200_OK)
