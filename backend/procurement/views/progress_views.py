from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from ..models import ProcurementPlan, ActivityLog, PerformanceMetric, Timeline
from ..serializers import (
    ProcurementPlanSerializer, 
    ActivityLogSerializer, 
    PerformanceMetricSerializer
)
from ..utils import normalize_stage_id, validate_stage_transition
from users.utils import is_superadmin, get_queryset_for_user
from users.permissions import HasPermission


class ProgressOverviewView(generics.RetrieveAPIView):
    """
    Get comprehensive progress overview for a procurement plan
    """
    queryset = ProcurementPlan.objects.all()
    serializer_class = ProcurementPlanSerializer
    permission_classes = [IsAuthenticated, HasPermission('planning.view')]

    def get_queryset(self):
        return get_queryset_for_user(self.request.user, ProcurementPlan.objects.all(), action='view')

    def retrieve(self, request, *args, **kwargs):
        if not getattr(request.user, 'user_role', None):
            return Response(
                {'error': 'User must have a role to view progress.'},
                status=status.HTTP_403_FORBIDDEN
            )

        procurement_plan = self.get_object()
        
        # Calculate comprehensive progress data
        progress_data = self.calculate_comprehensive_progress(procurement_plan)
        
        return Response(progress_data, status=status.HTTP_200_OK)

    def calculate_comprehensive_progress(self, plan):
        """Calculate comprehensive progress metrics"""
        # Basic progress calculation
        current_progress = plan.calculate_progress_percentage()
        
        # Timeline progress
        timeline_progress = self.calculate_timeline_progress(plan)
        
        # Activity progress
        activity_progress = self.calculate_activity_progress(plan)
        
        # Performance metrics summary
        performance_summary = self.get_performance_summary(plan)
        
        # Calculate overall health score
        health_score = self.calculate_health_score(plan)
        
        return {
            'procurement_plan_id': plan.id,
            'policy_number': plan.policy_number,
            'project_name': plan.project_name,
            'current_stage': plan.stage,
            'current_stage_display': plan.get_stage_display(),
            'status': plan.status,
            'priority': plan.priority,
            'progress': {
                'overall_percentage': current_progress,
                'stage_percentage': current_progress,
                'timeline_percentage': timeline_progress,
                'activity_percentage': activity_progress,
                'weighted_average': round((current_progress + timeline_progress + activity_progress) / 3, 2)
            },
            'timeline': {
                'planned_start': plan.planned_start_date,
                'planned_end': plan.planned_end_date,
                'actual_start': plan.actual_start_date,
                'actual_end': plan.actual_end_date,
                'days_elapsed': self.calculate_days_elapsed(plan),
                'days_remaining': plan.days_until_deadline(),
                'is_overdue': plan.is_overdue(),
                'next_milestone': {
                    'date': plan.next_milestone_date,
                    'description': plan.next_milestone_description
                }
            },
            'performance': performance_summary,
            'health_score': health_score,
            'recent_activities': self.get_recent_activities(plan, 10),
            'upcoming_milestones': self.get_upcoming_milestones(plan),
            'risk_indicators': self.get_risk_indicators(plan),
            'recommendations': self.generate_recommendations(plan)
        }

    def calculate_timeline_progress(self, plan):
        """Calculate progress based on timeline completion"""
        if not plan.planned_start_date or not plan.planned_end_date:
            return 0
        
        total_days = (plan.planned_end_date - plan.planned_start_date).days
        if total_days <= 0:
            return 100
        
        if plan.actual_start_date:
            elapsed_days = (timezone.now().date() - plan.actual_start_date).days
        else:
            elapsed_days = (timezone.now().date() - plan.planned_start_date).days
        
        progress = min(100, max(0, (elapsed_days / total_days) * 100))
        return round(progress, 2)

    def calculate_activity_progress(self, plan):
        """Calculate progress based on activity completion"""
        activities = ActivityLog.objects.filter(procurement_plan=plan)
        if not activities.exists():
            return 0
        
        # Define stage completion activities
        completion_activities = [
            'stage_advanced', 'milestone_completed', 'approved',
            'evaluation_completed', 'contract_awarded'
        ]
        
        completed_activities = activities.filter(action__in=completion_activities).count()
        total_activities = activities.count()
        
        if total_activities == 0:
            return 0
        
        progress = (completed_activities / total_activities) * 100
        return round(progress, 2)

    def get_performance_summary(self, plan):
        """Get summary of performance metrics"""
        metrics = PerformanceMetric.objects.filter(procurement_plan=plan)
        
        if not metrics.exists():
            return {
                'total_metrics': 0,
                'on_target': 0,
                'at_risk': 0,
                'critical': 0,
                'overall_score': 0
            }
        
        status_counts = metrics.values('status').annotate(count=models.Count('id'))
        status_dict = {item['status']: item['count'] for item in status_counts}
        
        total = metrics.count()
        on_target = status_dict.get('on_target', 0) + status_dict.get('above_target', 0)
        at_risk = status_dict.get('at_risk', 0) + status_dict.get('below_target', 0)
        critical = status_dict.get('critical', 0)
        
        # Calculate overall performance score
        score = (on_target * 100 + at_risk * 60 + critical * 20) / total if total > 0 else 0
        
        return {
            'total_metrics': total,
            'on_target': on_target,
            'at_risk': at_risk,
            'critical': critical,
            'overall_score': round(score, 2)
        }

    def calculate_health_score(self, plan):
        """Calculate overall project health score"""
        factors = []
        
        # Progress factor (30%)
        progress_score = plan.calculate_progress_percentage()
        factors.append(('progress', progress_score * 0.3))
        
        # Timeline factor (25%)
        if plan.is_overdue():
            timeline_score = max(0, 100 - abs(plan.days_until_deadline() or 0) * 2)
        else:
            timeline_score = 100
        factors.append(('timeline', timeline_score * 0.25))
        
        # Performance factor (25%)
        perf_summary = self.get_performance_summary(plan)
        factors.append(('performance', perf_summary['overall_score'] * 0.25))
        
        # Activity factor (20%)
        recent_activity_count = ActivityLog.objects.filter(
            procurement_plan=plan,
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).count()
        activity_score = min(100, recent_activity_count * 20)
        factors.append(('activity', activity_score * 0.2))
        
        # Calculate weighted average
        total_score = sum(score for _, score in factors)
        
        return {
            'score': round(total_score, 2),
            'rating': self.get_health_rating(total_score),
            'factors': {name: round(score / weight, 2) for name, score in factors for weight in [0.3, 0.25, 0.25, 0.2]}
        }

    def get_health_rating(self, score):
        """Get health rating based on score"""
        if score >= 90:
            return 'Excellent'
        elif score >= 75:
            return 'Good'
        elif score >= 60:
            return 'Fair'
        elif score >= 40:
            return 'Poor'
        else:
            return 'Critical'

    def calculate_days_elapsed(self, plan):
        """Calculate days elapsed since start"""
        if plan.actual_start_date:
            return (timezone.now().date() - plan.actual_start_date).days
        elif plan.planned_start_date:
            return max(0, (timezone.now().date() - plan.planned_start_date).days)
        return 0

    def get_recent_activities(self, plan, limit=10):
        """Get recent activities for the plan"""
        activities = ActivityLog.objects.filter(
            procurement_plan=plan
        ).select_related('user')[:limit]
        
        return [activity.format_for_display() for activity in activities]

    def get_upcoming_milestones(self, plan):
        """Get upcoming milestones from timeline"""
        upcoming = Timeline.objects.filter(
            procurement_plan=plan,
            planned_end_date__gte=timezone.now().date(),
            is_milestone=True
        ).order_by('planned_end_date')[:5]
        
        return [{
            'id': milestone.id,
            'description': milestone.milestone_description,
            'date': milestone.planned_end_date,
            'stage': milestone.get_stage_display(),
            'is_overdue': milestone.is_overdue(),
            'days_until': (milestone.planned_end_date - timezone.now().date()).days if milestone.planned_end_date else None
        } for milestone in upcoming]

    def get_risk_indicators(self, plan):
        """Identify risk indicators"""
        risks = []
        
        # Overdue risk
        if plan.is_overdue():
            risks.append({
                'type': 'timeline',
                'severity': 'high',
                'message': f'Project is {abs(plan.days_until_deadline())} days overdue'
            })
        
        # Budget variance risk
        if hasattr(plan, 'performance_metrics'):
            cost_metrics = plan.performance_metrics.filter(metric_type='cost_variance')
            for metric in cost_metrics:
                if metric.status in ['critical', 'at_risk']:
                    risks.append({
                        'type': 'budget',
                        'severity': metric.status,
                        'message': f'Cost variance is {metric.current_value}%'
                    })
        
        # Inactive project risk
        last_activity = ActivityLog.objects.filter(procurement_plan=plan).first()
        if last_activity and (timezone.now() - last_activity.timestamp).days > 7:
            risks.append({
                'type': 'activity',
                'severity': 'medium',
                'message': f'No activity for {(timezone.now() - last_activity.timestamp).days} days'
            })
        
        return risks

    def generate_recommendations(self, plan):
        """Generate actionable recommendations"""
        recommendations = []
        
        # Progress-based recommendations
        progress = plan.calculate_progress_percentage()
        if progress < 25 and plan.stage in ['planning', 'specification']:
            recommendations.append({
                'type': 'progress',
                'priority': 'medium',
                'action': 'Consider accelerating planning phase to avoid delays'
            })
        
        # Timeline recommendations
        if plan.is_overdue():
            recommendations.append({
                'type': 'timeline',
                'priority': 'high',
                'action': 'Review project timeline and consider resource reallocation'
            })
        
        # Activity recommendations
        recent_activities = ActivityLog.objects.filter(
            procurement_plan=plan,
            timestamp__gte=timezone.now() - timedelta(days=3)
        ).count()
        
        if recent_activities == 0:
            recommendations.append({
                'type': 'activity',
                'priority': 'medium',
                'action': 'Project appears inactive - check with stakeholders'
            })
        
        return recommendations


@api_view(['POST'])
@permission_classes([HasPermission('planning.manage')])
def update_progress(request, pk):
    """
    Manually update progress for a procurement plan
    """
    if not getattr(request.user, 'user_role', None):
        return Response(
            {'error': 'User must have a role to update progress.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user = request.user
    
    # Get procurement plan with access control
    plan = get_object_or_404(
        get_queryset_for_user(user, ProcurementPlan.objects.all(), action='manage'),
        pk=pk
    )
    
    # Get update data
    progress_percentage = request.data.get('progress_percentage')
    stage = request.data.get('stage')
    notes = request.data.get('notes', '')
    
    old_values = {
        'progress_percentage': float(plan.progress_percentage),
        'stage': plan.stage
    }
    
    # Update progress
    if progress_percentage is not None:
        try:
            progress_percentage = Decimal(str(progress_percentage))
            if 0 <= progress_percentage <= 100:
                plan.progress_percentage = progress_percentage
            else:
                return Response(
                    {'error': 'Progress percentage must be between 0 and 100.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid progress percentage format.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Update stage if provided
    if stage:
        normalized_stage = normalize_stage_id(stage)
        valid_stage_values = {choice[0] for choice in ProcurementPlan.STAGE_CHOICES}
        if normalized_stage not in valid_stage_values:
            return Response(
                {'error': f"Invalid stage '{stage}'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        can_transition, transition_errors = validate_stage_transition(
            plan, normalized_stage
        )
        if not can_transition:
            return Response(
                {
                    'error': 'Stage transition is not allowed.',
                    'details': transition_errors,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        old_stage = plan.stage
        plan.stage = normalized_stage
        plan.stage_updated_at = timezone.now()
        
        # Log stage advancement
        if old_stage != normalized_stage:
            ActivityLog.log_activity(
                procurement_plan=plan,
                action='stage_advanced',
                user=user,
                description=f'Stage advanced from {old_stage} to {normalized_stage}',
                details={'old_stage': old_stage, 'new_stage': normalized_stage, 'notes': notes},
                old_values={'stage': old_stage},
                new_values={'stage': normalized_stage}
            )
    
    plan.save()
    
    new_values = {
        'progress_percentage': float(plan.progress_percentage),
        'stage': plan.stage
    }
    
    # Log progress update
    ActivityLog.log_activity(
        procurement_plan=plan,
        action='updated',
        user=user,
        description=f'Progress updated to {plan.progress_percentage}%',
        details={'progress_update': True, 'notes': notes},
        old_values=old_values,
        new_values=new_values
    )
    
    # Recalculate comprehensive progress
    progress_view = ProgressOverviewView()
    progress_data = progress_view.calculate_comprehensive_progress(plan)
    
    return Response({
        'message': 'Progress updated successfully.',
        'progress_data': progress_data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([HasPermission('planning.manage')])
def calculate_auto_progress(request, pk):
    """
    Auto-calculate progress based on stage, timeline, and activities
    """
    if not getattr(request.user, 'user_role', None):
        return Response(
            {'error': 'User must have a role to calculate progress.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user = request.user
    
    # Get procurement plan with access control
    plan = get_object_or_404(
        get_queryset_for_user(user, ProcurementPlan.objects.all(), action='manage'),
        pk=pk
    )
    
    old_progress = float(plan.progress_percentage)
    
    # Calculate new progress
    stage_progress = plan.calculate_progress_percentage()
    
    # Calculate timeline-based progress
    progress_view = ProgressOverviewView()
    timeline_progress = progress_view.calculate_timeline_progress(plan)
    activity_progress = progress_view.calculate_activity_progress(plan)
    
    # Weighted calculation (stage: 50%, timeline: 30%, activity: 20%)
    calculated_progress = (
        stage_progress * 0.5 +
        timeline_progress * 0.3 +
        activity_progress * 0.2
    )
    
    # Update progress
    plan.progress_percentage = Decimal(str(round(calculated_progress, 2)))
    plan.save()
    
    # Log the auto-calculation
    ActivityLog.log_activity(
        procurement_plan=plan,
        action='updated',
        user=user,
        description=f'Progress auto-calculated to {plan.progress_percentage}%',
        details={
            'auto_calculation': True,
            'components': {
                'stage_progress': stage_progress,
                'timeline_progress': timeline_progress,
                'activity_progress': activity_progress
            }
        },
        old_values={'progress_percentage': old_progress},
        new_values={'progress_percentage': float(plan.progress_percentage)}
    )
    
    return Response({
        'message': 'Progress calculated automatically.',
        'old_progress': old_progress,
        'new_progress': float(plan.progress_percentage),
        'calculation_components': {
            'stage_progress': stage_progress,
            'timeline_progress': timeline_progress,
            'activity_progress': activity_progress
        }
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([HasPermission('planning.view')])
def progress_analytics(request):
    """
    Get progress analytics across all accessible procurement plans
    """
    if not getattr(request.user, 'user_role', None):
        return Response(
            {'error': 'User must have a role to view analytics.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user = request.user
    
    # Get accessible plans
    plans = get_queryset_for_user(user, ProcurementPlan.objects.all(), action='view')
    
    # Calculate analytics
    analytics = {
        'summary': {
            'total_plans': plans.count(),
            'active_plans': plans.filter(status='active').count(),
            'completed_plans': plans.filter(status='completed').count(),
            'overdue_plans': len([p for p in plans if p.is_overdue()]),
            'average_progress': round(plans.aggregate(
                avg=models.Avg('progress_percentage')
            )['avg'] or 0, 2)
        },
        'by_stage': {},
        'by_status': {},
        'by_priority': {},
        'progress_distribution': {
            '0-25%': 0, '26-50%': 0, '51-75%': 0, '76-100%': 0
        },
        'timeline_performance': {
            'on_time': 0,
            'at_risk': 0,
            'overdue': 0
        },
        'trends': {
            'this_month': 0,
            'last_month': 0,
            'improvement': 0
        }
    }
    
    # Group by stage
    stage_counts = plans.values('stage').annotate(count=models.Count('id'))
    for item in stage_counts:
        analytics['by_stage'][item['stage']] = item['count']
    
    # Group by status
    status_counts = plans.values('status').annotate(count=models.Count('id'))
    for item in status_counts:
        analytics['by_status'][item['status']] = item['count']
    
    # Group by priority
    priority_counts = plans.values('priority').annotate(count=models.Count('id'))
    for item in priority_counts:
        analytics['by_priority'][item['priority']] = item['count']
    
    # Progress distribution
    for plan in plans:
        progress = float(plan.progress_percentage)
        if progress <= 25:
            analytics['progress_distribution']['0-25%'] += 1
        elif progress <= 50:
            analytics['progress_distribution']['26-50%'] += 1
        elif progress <= 75:
            analytics['progress_distribution']['51-75%'] += 1
        else:
            analytics['progress_distribution']['76-100%'] += 1
    
    # Timeline performance
    for plan in plans:
        if plan.is_overdue():
            analytics['timeline_performance']['overdue'] += 1
        elif plan.days_until_deadline() and plan.days_until_deadline() <= 7:
            analytics['timeline_performance']['at_risk'] += 1
        else:
            analytics['timeline_performance']['on_time'] += 1
    
    # Monthly trends (simplified)
    this_month = timezone.now().replace(day=1)
    last_month = (this_month - timedelta(days=1)).replace(day=1)
    
    this_month_activities = ActivityLog.objects.filter(
        procurement_plan__in=plans,
        timestamp__gte=this_month
    ).count()
    
    last_month_activities = ActivityLog.objects.filter(
        procurement_plan__in=plans,
        timestamp__gte=last_month,
        timestamp__lt=this_month
    ).count()
    
    analytics['trends']['this_month'] = this_month_activities
    analytics['trends']['last_month'] = last_month_activities
    
    if last_month_activities > 0:
        improvement = ((this_month_activities - last_month_activities) / last_month_activities) * 100
        analytics['trends']['improvement'] = round(improvement, 2)
    
    return Response(analytics, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([HasPermission('planning.manage')])
def bulk_progress_update(request):
    """
    Update progress for multiple procurement plans in bulk
    """
    if not getattr(request.user, 'user_role', None):
        return Response(
            {'error': 'User must have a role to update progress.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user = request.user
    accessible_plans_qs = get_queryset_for_user(user, ProcurementPlan.objects.all(), action='manage')
    
    updates = request.data.get('updates', [])
    if not updates:
        return Response(
            {'error': 'No updates provided.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    results = {
        'successful': [],
        'failed': [],
        'total': len(updates)
    }
    
    for update in updates:
        plan_id = update.get('plan_id')
        progress = update.get('progress_percentage')
        stage = update.get('stage')
        
        try:
            plan = accessible_plans_qs.get(id=plan_id)
            
            old_values = {
                'progress_percentage': float(plan.progress_percentage),
                'stage': plan.stage
            }
            
            # Update progress
            if progress is not None:
                plan.progress_percentage = Decimal(str(progress))
            
            # Update stage
            if stage:
                normalized_stage = normalize_stage_id(stage)
                valid_stage_values = {choice[0] for choice in ProcurementPlan.STAGE_CHOICES}
                if normalized_stage not in valid_stage_values:
                    raise ValueError(f"Invalid stage '{stage}'.")

                can_transition, transition_errors = validate_stage_transition(
                    plan, normalized_stage
                )
                if not can_transition:
                    raise ValueError("; ".join(transition_errors))

                plan.stage = normalized_stage
                plan.stage_updated_at = timezone.now()
            
            plan.save()
            
            # Log the update
            ActivityLog.log_activity(
                procurement_plan=plan,
                action='updated',
                user=user,
                description=f'Bulk progress update: {plan.progress_percentage}%',
                details={'bulk_update': True},
                old_values=old_values,
                new_values={
                    'progress_percentage': float(plan.progress_percentage),
                    'stage': plan.stage
                }
            )
            
            results['successful'].append({
                'plan_id': plan_id,
                'policy_number': plan.policy_number,
                'new_progress': float(plan.progress_percentage)
            })
            
        except ProcurementPlan.DoesNotExist:
            results['failed'].append({
                'plan_id': plan_id,
                'error': 'Plan not found or access denied'
            })
        except Exception as e:
            results['failed'].append({
                'plan_id': plan_id,
                'error': str(e)
            })
    
    return Response(results, status=status.HTTP_200_OK)
