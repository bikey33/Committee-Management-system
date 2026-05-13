from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from procurement.models import ProcurementPlan
from tender.models import Tender
from tender.serializers import TenderSerializer
from users.permissions import HasPermission
from users.utils import get_queryset_for_user


class ProcurementPlanTendersView(generics.ListAPIView):
    """
    Get all tenders for a specific procurement plan
    """
    serializer_class = TenderSerializer
    permission_classes = [IsAuthenticated, HasPermission('planning.view')]

    @swagger_auto_schema(
        tags=["Procurement Plans"],
        operation_summary="Get tenders for a procurement plan",
        operation_description="Retrieve all tenders associated with a specific procurement plan",
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_PATH,
                description="Procurement Plan ID",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    ),
                    'meta': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'count': openapi.Schema(type=openapi.TYPE_INTEGER)
                        }
                    )
                }
            ),
            404: "Procurement plan not found"
        }
    )
    def get(self, request, *args, **kwargs):
        procurement_plan_id = self.kwargs.get('id')

        # Verify procurement plan exists and user has access
        procurement_plan = get_object_or_404(
            get_queryset_for_user(request.user, ProcurementPlan.objects.all(), action='view'),
            id=procurement_plan_id
        )

        # Get all tenders for this procurement plan
        tenders = Tender.objects.filter(procurement_plan=procurement_plan)

        serializer = self.get_serializer(tenders, many=True)

        return Response({
            'success': True,
            'message': 'Tenders retrieved successfully',
            'data': serializer.data,
            'meta': {
                'count': tenders.count()
            }
        }, status=status.HTTP_200_OK)
