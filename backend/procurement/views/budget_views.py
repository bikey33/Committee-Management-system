from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.permissions import HasPermission
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db.models import Sum, F, Q
from decimal import Decimal
import json

from ..models import ProcurementPlan
from ..serializers import ProcurementPlanSerializer
from ..mixins import get_procurement_plan_filter


class BudgetViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasPermission('planning.view')]
    # Provide a default serializer_class so schema generation (drf_yasg)
    # can call get_serializer() without raising an assertion.
    serializer_class = ProcurementPlanSerializer

    def get_permissions(self):
        """Map budget actions to granular permissions"""
        if self.action in ['revisions', 'approve_revision', 'reject_revision'] and self.request.method == 'POST':
            return [IsAuthenticated(), HasPermission('planning.manage')()]
        return [IsAuthenticated(), HasPermission('planning.view')()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return ProcurementPlan.objects.none()
        
        # Revisions and updates require 'manage' permission for cross-office
        action = 'manage' if self.action in ['revisions', 'approve_revision', 'reject_revision'] or self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] else 'view'
        
        access_filter = get_procurement_plan_filter(user, action=action)
        if not access_filter:
            return ProcurementPlan.objects.all()
        
        return ProcurementPlan.objects.filter(access_filter).distinct()

    @action(detail=True, methods=['get'])
    def budget(self, request, pk=None):
        """Get budget overview for a procurement plan"""
        plan = self.get_object()

        # Calculate budget metrics
        budget_data = {
            'total_budget': plan.budget,
            'estimated_cost': plan.estimated_cost,
            'variance': ((plan.budget - plan.estimated_cost) / plan.estimated_cost * 100) if plan.estimated_cost > 0 else 0,
            'utilization_rate': 47.5,  # This would come from actual spending data
            'burn_rate': plan.budget * 0.08,  # Monthly burn rate calculation
        }

        return Response(budget_data)

    @action(detail=True, methods=['get'])
    def breakdown(self, request, pk=None):
        """Get budget breakdown by category"""
        plan = self.get_object()

        # Mock budget breakdown - in production, this would come from a budget categories model
        breakdown = [
            {
                'category': 'Equipment & Materials',
                'allocated': plan.budget * 0.6,
                'spent': plan.budget * 0.35,
                'remaining': plan.budget * 0.25,
                'percentage_used': 58.3
            },
            {
                'category': 'Services & Labor',
                'allocated': plan.budget * 0.25,
                'spent': plan.budget * 0.12,
                'remaining': plan.budget * 0.13,
                'percentage_used': 48.0
            },
            {
                'category': 'Administrative Costs',
                'allocated': plan.budget * 0.1,
                'spent': plan.budget * 0.04,
                'remaining': plan.budget * 0.06,
                'percentage_used': 40.0
            },
            {
                'category': 'Contingency',
                'allocated': plan.budget * 0.05,
                'spent': 0,
                'remaining': plan.budget * 0.05,
                'percentage_used': 0
            }
        ]

        return Response(breakdown)

    @action(detail=True, methods=['get', 'post'])
    def revisions(self, request, pk=None):
        """Get or create budget revisions"""
        plan = self.get_object()

        if request.method == 'GET':
            # Mock revision history - in production, this would come from a budget revisions model
            revisions = [
                {
                    'id': '1',
                    'version': 2,
                    'original_budget': plan.budget,
                    'revised_budget': plan.budget * 1.15,
                    'reason': 'Additional technical requirements identified',
                    'approved_by': 'John Doe',
                    'approved_date': '2024-01-15',
                    'status': 'approved',
                    'variance_percentage': 15,
                    'impact_assessment': 'Medium impact on project timeline'
                },
                {
                    'id': '2',
                    'version': 1,
                    'original_budget': plan.estimated_cost,
                    'revised_budget': plan.budget,
                    'reason': 'Initial budget allocation',
                    'approved_by': 'System',
                    'approved_date': plan.created_at.isoformat(),
                    'status': 'approved',
                    'variance_percentage': 0,
                    'impact_assessment': 'Initial budget setup'
                }
            ]
            return Response(revisions)

        elif request.method == 'POST':
            # Create new budget revision
            revision_data = request.data

            # In production, save to budget revisions model
            new_revision = {
                'id': '3',
                'version': 3,
                'original_budget': plan.budget,
                'revised_budget': revision_data.get('revised_budget'),
                'reason': revision_data.get('reason'),
                'approved_by': None,
                'approved_date': None,
                'status': 'pending',
                'variance_percentage': ((revision_data.get('revised_budget', 0) - plan.budget) / plan.budget * 100) if plan.budget > 0 else 0,
                'impact_assessment': revision_data.get('impact_assessment', '')
            }

            return Response(new_revision, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def approve_revision(self, request, pk=None):
        """Approve a budget revision"""
        plan = self.get_object()
        revision_id = request.data.get('revision_id')

        # In production, update the revision status in database
        return Response({'message': 'Budget revision approved successfully'})

    @action(detail=True, methods=['post'])
    def reject_revision(self, request, pk=None):
        """Reject a budget revision"""
        plan = self.get_object()
        revision_id = request.data.get('revision_id')
        reason = request.data.get('reason')

        # In production, update the revision status in database
        return Response({'message': 'Budget revision rejected'})

    @action(detail=True, methods=['get'])
    def variance_analysis(self, request, pk=None):
        """Get budget variance analysis"""
        plan = self.get_object()

        variance_data = [
            {
                'category': 'Equipment & Materials',
                'planned': plan.budget * 0.6,
                'actual': plan.budget * 0.35,
                'variance': plan.budget * 0.25,
                'variance_percentage': -41.7,
                'status': 'under'
            },
            {
                'category': 'Services & Labor',
                'planned': plan.budget * 0.25,
                'actual': plan.budget * 0.12,
                'variance': plan.budget * 0.13,
                'variance_percentage': -52.0,
                'status': 'under'
            }
        ]

        return Response(variance_data)

    @action(detail=True, methods=['get'])
    def spending(self, request, pk=None):
        """Get budget spending records"""
        plan = self.get_object()

        # Mock spending data
        spending = [
            {
                'id': '1',
                'category': 'Equipment & Materials',
                'amount': plan.budget * 0.15,
                'description': 'Office equipment purchase',
                'date': '2024-01-10',
                'status': 'approved'
            },
            {
                'id': '2',
                'category': 'Services & Labor',
                'amount': plan.budget * 0.08,
                'description': 'Consulting services',
                'date': '2024-01-15',
                'status': 'approved'
            }
        ]

        return Response(spending)

    @action(detail=True, methods=['get'])
    def alerts(self, request, pk=None):
        """Get budget alerts"""
        plan = self.get_object()

        alerts = [
            {
                'id': '1',
                'type': 'milestone',
                'message': 'Budget utilization has reached 75% threshold',
                'severity': 'medium',
                'created_at': '2024-01-20T10:00:00Z',
                'acknowledged': False
            }
        ]

        return Response(alerts)

    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """Get budget performance metrics"""
        plan = self.get_object()

        metrics = {
            'total_allocated': plan.budget,
            'total_spent': plan.budget * 0.47,
            'total_remaining': plan.budget * 0.53,
            'utilization_rate': 47.0,
            'burn_rate': plan.budget * 0.08,
            'variance': ((plan.budget - plan.estimated_cost) / plan.estimated_cost * 100) if plan.estimated_cost > 0 else 0,
            'categories_over_budget': 0,
            'categories_under_budget': 4,
            'approval_pending': 1
        }

        return Response(metrics)

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """Export budget report"""
        plan = self.get_object()
        format_type = request.query_params.get('format', 'pdf')

        # Mock export functionality
        if format_type == 'pdf':
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="budget_report_{plan.id}.pdf"'
            response.write(b'Mock PDF content')
        elif format_type == 'excel':
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="budget_report_{plan.id}.xlsx"'
            response.write(b'Mock Excel content')
        else:  # csv
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="budget_report_{plan.id}.csv"'
            response.write(b'Mock CSV content')

        return response
