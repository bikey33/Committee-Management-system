# committee/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .permissions import CommitteePermission
from .models import Committee, CommitteeMembership, CommitteeRole, ReviewCommitteeDefaultMember, CommitteePhaseCheckpoint, CommitteeDocument
from .notifications import notify_committee_membership
from .signals import ensure_stakeholder_for_membership, deactivate_stakeholder_for_membership
from .models import is_committee_closed, is_committee_overdue
from procurement.models import ProcurementDocument
from django.db.utils import OperationalError, ProgrammingError
from .serializers import CommitteeSerializer
from users.models import CustomUser, Office
from procurement.models import ProcurementPlan
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.dateparse import parse_date
from django.http import HttpResponse
from django.conf import settings
import os
import json
import logging

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.http import FileResponse, HttpResponse
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from procurement.models import ProcurementPlan
from users.models import CustomUser

from .models import Committee, CommitteeMembership, ReviewCommitteeDefaultMember
from .permissions import CommitteePermission
from .serializers import CommitteeSerializer


from users.utils import is_superadmin, get_queryset_for_user
from users.permissions import HasPermission

logger = logging.getLogger(__name__)


class CommitteeRolesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            roles = CommitteeRole.objects.filter(is_active=True).order_by('sort_order', 'label')
            if roles.exists():
                data = [{"id": role.id, "value": role.value, "label": role.label} for role in roles]
            else:
                data = []
        except (ProgrammingError, OperationalError):
            data = []
        if not data:
            data = [
                {"id": 1, "value": "chairperson", "label": "Chairperson"},
                {"id": 2, "value": "coordinator", "label": "Coordinator"},
                {"id": 3, "value": "sub_coordinator", "label": "Sub Coordinator"},
                {"id": 4, "value": "secretary", "label": "Secretary"},
                {"id": 5, "value": "member", "label": "Member"},
                {"id": 6, "value": "invitee", "label": "Invitee"},
                {"id": 7, "value": "subject_expert", "label": "Subject Expert"},
                {"id": 8, "value": "others", "label": "Others"},
            ]
        return Response(
            {"status": "success", "data": data},
            status=status.HTTP_200_OK
        )


class CommitteeRolesCRUDView(APIView):
    """Full CRUD for committee role types (admin only)."""
    permission_classes = [IsAuthenticated, HasPermission('settings.committee_roles')]

    def get(self, request):
        """List ALL roles (including inactive) for admin management."""
        roles = CommitteeRole.objects.all().order_by('sort_order', 'label')
        data = [
            {
                'id': r.id,
                'value': r.value,
                'label': r.label,
                'is_active': r.is_active,
                'sort_order': r.sort_order,
                'created_at': r.created_at,
                'updated_at': r.updated_at,
            }
            for r in roles
        ]
        return Response({'results': data}, status=status.HTTP_200_OK)

    def post(self, request):
        """Create a new committee role type."""

        value = (request.data.get('value') or '').strip().lower().replace(' ', '_')
        label = (request.data.get('label') or '').strip()
        sort_order = request.data.get('sort_order', 0)
        is_active = request.data.get('is_active', True)

        if not value:
            return Response({'error': 'Value is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not label:
            return Response({'error': 'Label is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if CommitteeRole.objects.filter(value=value).exists():
            return Response(
                {'error': f'Role with value "{value}" already exists.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        role = CommitteeRole.objects.create(
            value=value,
            label=label,
            sort_order=int(sort_order),
            is_active=bool(is_active),
        )
        return Response(
            {
                'id': role.id,
                'value': role.value,
                'label': role.label,
                'is_active': role.is_active,
                'sort_order': role.sort_order,
                'created_at': role.created_at,
                'updated_at': role.updated_at,
            },
            status=status.HTTP_201_CREATED,
        )


class CommitteeRoleDetailView(APIView):
    """GET / PUT / DELETE for a single CommitteeRole by id."""
    permission_classes = [IsAuthenticated, HasPermission('settings.committee_roles')]

    def _get_role(self, role_id):
        try:
            return CommitteeRole.objects.get(id=role_id)
        except CommitteeRole.DoesNotExist:
            return None

    def get(self, request, role_id: int):
        role = self._get_role(role_id)
        if not role:
            return Response({'error': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'id': role.id,
            'value': role.value,
            'label': role.label,
            'is_active': role.is_active,
            'sort_order': role.sort_order,
            'created_at': role.created_at,
            'updated_at': role.updated_at,
        })

    def put(self, request, role_id: int):
        role = self._get_role(role_id)
        if not role:
            return Response({'error': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

        label = request.data.get('label')
        if label is not None:
            role.label = str(label).strip()
        sort_order = request.data.get('sort_order')
        if sort_order is not None:
            role.sort_order = int(sort_order)
        is_active = request.data.get('is_active')
        if is_active is not None:
            role.is_active = bool(is_active)
        role.save()

        return Response({
            'id': role.id,
            'value': role.value,
            'label': role.label,
            'is_active': role.is_active,
            'sort_order': role.sort_order,
            'created_at': role.created_at,
            'updated_at': role.updated_at,
        })

    def patch(self, request, role_id: int):
        return self.put(request, role_id)

    def delete(self, request, role_id: int):
        role = self._get_role(role_id)
        if not role:
            return Response({'error': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Check if role is in use by any committee membership
        in_use = CommitteeMembership.objects.filter(committee_role=role.value).exists()
        if in_use:
            return Response(
                {'error': f'Role "{role.label}" is currently assigned to committee members and cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        role.delete()
        return Response({'message': 'Role deleted.'}, status=status.HTTP_200_OK)


class CreateCommitteeView(APIView):
    permission_classes = [CommitteePermission]

    def post(self, request):
        logger.debug(f"CreateCommitteeView called with data: {dict(request.data)}")
        logger.debug(f"Authenticated user: {request.user}")

        members_data = request.data.get('members', [])
        if isinstance(members_data, str):
            try:
                members_data = json.loads(members_data)
            except json.JSONDecodeError:
                members_data = []

        serializer_data = {
            'name': request.data.get('name'),
            'purpose': request.data.get('purpose'),
            'committee_type': request.data.get('committee_type'),
            'office': request.data.get('office') or None,
            'deadline': request.data.get('deadline') or None,
            'formation_date': request.data.get('formation_date') or None,
            'formation_letter': request.FILES.get('formation_letter'),
            'members': members_data,
        }

        logger.debug(f"Serializer data: {serializer_data}")
        committee_type = serializer_data.get('committee_type')

        serializer = CommitteeSerializer(data=serializer_data, context={'request': request})

        if serializer.is_valid():
            committee = serializer.save()
            logger.debug(f"Committee created: {committee.id}")
            logger.debug(f"Committee created_by: {committee.created_by}")
            logger.debug(
                f"Committee created_by employee_id: {committee.created_by.employee_id if committee.created_by else 'None'}")

            return Response(
                {
                    "status": "success",
                    "message": "Committee created successfully",
                    "data": {"committee": serializer.data}
                },
                status=status.HTTP_201_CREATED
            )
        else:
            logger.error(f"Serializer errors: {serializer.errors}")
            return Response(
                {
                    "status": "error",
                    "message": "Invalid data provided",
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class UpdateCommitteeView(APIView):
    permission_classes = [CommitteePermission]

    def patch(self, request, committee_id):
        logger.debug(f"UpdateCommitteeView called with committee_id: {committee_id}, data: {dict(request.data)}")
        logger.debug(f"Authenticated user: {request.user}")

        try:
            committee = Committee.objects.get(id=committee_id)
        except Committee.DoesNotExist:
            logger.error(f"Committee not found: {committee_id}")
            return Response(
                {"status": "error", "message": "Committee not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        self.check_object_permissions(request, committee)

        members_data = request.data.get('members', [])
        if isinstance(members_data, str):
            try:
                members_data = json.loads(members_data)
            except json.JSONDecodeError:
                members_data = []

        serializer_data = {
            'name': request.data.get('name'),
            'purpose': request.data.get('purpose'),
            'committee_type': request.data.get('committee_type'),
            'office': request.data.get('office') or None,
            'deadline': request.data.get('deadline') or None,
            'formation_date': request.data.get('formation_date') or None,
            'formation_letter': request.FILES.get('formation_letter'),
            'members': members_data,
        }

        logger.debug(f"Serializer data: {serializer_data}")
        serializer = CommitteeSerializer(
            instance=committee,
            data=serializer_data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            try:
                committee = serializer.save()
                logger.debug(f"Committee updated: {committee.id}")
                return Response(
                    {"status": "success", "data": {"committee": CommitteeSerializer(committee).data}},
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                logger.error(f"Failed to update committee: {str(e)}")
                return Response(
                    {"status": "error", "message": f"Failed to update committee: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        logger.error(f"Serializer errors: {serializer.errors}")
        return Response(
            {"status": "error", "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class GetAllCommitteesView(APIView):
    permission_classes = [CommitteePermission]

    def get(self, request):
        try:
            if is_superadmin(request.user) or request.user.has_rbac_permission('committee.view_cross_office'):
                committees = Committee.objects.select_related(
                    'created_by', 'created_by__user_role'
                ).prefetch_related(
                    'memberships', 'memberships__user'
                ).all()
            else:
                # Custom scoping: creators see their own, members see their own,
                # and users see committees tied to their own office. (Office has no
                # hierarchy, so scope to the user's single office — not descendants.)
                office_q = models.Q()
                if request.user.office:
                    office_q = (
                        models.Q(office=request.user.office)
                        | models.Q(procurement_plan__office=request.user.office)
                        | models.Q(created_by__office=request.user.office)
                    )

                committees = Committee.objects.select_related(
                    'created_by', 'created_by__user_role'
                ).prefetch_related(
                    'memberships', 'memberships__user'
                ).filter(
                    models.Q(created_by=request.user) |
                    models.Q(memberships__user=request.user, memberships__is_active=True) |
                    office_q
                ).distinct()

            serializer = CommitteeSerializer(committees, many=True, context={'request': request})
            logger.debug(f"Fetched committees: {len(serializer.data)}")
            return Response(
                {
                    "status": "success",
                    "results": len(serializer.data),
                    "data": {"committees": serializer.data}
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Failed to fetch committees: {str(e)}")
            return Response(
                {
                    "status": "error",
                    "message": f"Failed to fetch committees: {str(e)}"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetCommitteeByIdView(APIView):
    permission_classes = [CommitteePermission]

    def get(self, request, committee_id):
        try:
            committee = Committee.objects.get(id=committee_id)
            self.check_object_permissions(request, committee)
            serializer = CommitteeSerializer(committee, context={'request': request})
            logger.debug(f"Fetched committee with ID: {committee.id}")
            return Response(
                {"status": "success", "data": {"committee": serializer.data}},
                status=status.HTTP_200_OK
            )
        except ObjectDoesNotExist:
            logger.error(f"Committee with ID {committee_id} not found")
            return Response(
                {"status": "error", "message": "Committee not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.exception(f"An unexpected error occurred while fetching committee with ID {committee_id}: {str(e)}")
            return Response(
                {"status": "error", "message": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeleteCommitteeView(APIView):
    permission_classes = [CommitteePermission]

    def delete(self, request, committee_id):
        try:
            committee = Committee.objects.get(id=committee_id)
            self.check_object_permissions(request, committee)
            committee.delete()
            logger.debug(f"Committee deleted: {committee_id}")
            return Response(
                {"status": "success", "message": "Committee deleted successfully"},
                status=status.HTTP_200_OK
            )
        except ObjectDoesNotExist:
            logger.error(f"Committee {committee_id} not found")
            return Response(
                {"status": "error", "message": "Committee not found"},
                status=status.HTTP_404_NOT_FOUND
            )


class AddMemberView(APIView):
    permission_classes = [CommitteePermission]

    def post(self, request, committee_id):
        try:
            committee = Committee.objects.get(id=committee_id)
            self.check_object_permissions(request, committee)

            employee_id = request.data.get('employeeId')
            committee_role = request.data.get('committeeRole', 'member')
            try:
                valid_roles = list(CommitteeRole.objects.filter(is_active=True).values_list('value', flat=True))
            except (ProgrammingError, OperationalError):
                valid_roles = []
            if not valid_roles:
                valid_roles = ['member', 'chairperson', 'secretary']
            if valid_roles and committee_role not in valid_roles:
                logger.error(f"Invalid role: {committee_role}")
                return Response(
                    {"status": "error", "message": f"Invalid role: {committee_role}. Must be one of {valid_roles}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                user = CustomUser.objects.get(employee_id=employee_id)
            except CustomUser.DoesNotExist:
                logger.error(f"User {employee_id} not found")
                return Response(
                    {"status": "error", "message": "User not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            existing = CommitteeMembership.objects.filter(committee=committee, user=user).first()
            if existing and existing.is_active:
                logger.error(f"User {employee_id} is already a member of committee {committee_id}")
                return Response(
                    {"status": "error", "message": "User is already a member of this committee"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if existing:
                # Previously removed — reactivate the existing row (genuine re-join).
                existing.reactivate(role=committee_role)
                membership = existing
                ensure_stakeholder_for_membership(membership)
            else:
                membership = CommitteeMembership.objects.create(
                    committee=committee, user=user, committee_role=committee_role
                )
            notify_committee_membership(membership)
            serializer = CommitteeSerializer(committee, context={'request': request})
            logger.debug(f"Member {employee_id} added to committee {committee_id}")
            return Response(
                {"status": "success", "data": {"committee": serializer.data}},
                status=status.HTTP_200_OK
            )
        except ObjectDoesNotExist:
            logger.error(f"Committee {committee_id} not found")
            return Response(
                {"status": "error", "message": "Committee not found"},
                status=status.HTTP_404_NOT_FOUND
            )


class RemoveMemberView(APIView):
    permission_classes = [CommitteePermission]

    def delete(self, request, committee_id, employee_id):
        logger.debug(f"RemoveMemberView called with committee_id: {committee_id}, employee_id: {employee_id}")
        try:
            committee = Committee.objects.get(id=committee_id)
            self.check_object_permissions(request, committee)
            try:
                user = CustomUser.objects.get(employee_id=employee_id)
            except CustomUser.DoesNotExist:
                logger.error(f"User {employee_id} not found")
                return Response(
                    {"status": "error", "message": "User not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            membership = CommitteeMembership.objects.filter(
                committee=committee, user=user, is_active=True
            ).first()
            if not membership:
                logger.error(f"User {employee_id} is not a member of committee {committee_id}")
                return Response(
                    {"status": "error", "message": "User is not a member of this committee"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Soft-delete to retain history; remove plan visibility.
            membership.soft_delete()
            deactivate_stakeholder_for_membership(membership)
            serializer = CommitteeSerializer(committee, context={'request': request})
            logger.debug(f"Member {employee_id} removed from committee {committee_id}")
            return Response(
                {"status": "success", "data": {"committee": serializer.data}},
                status=status.HTTP_200_OK
            )
        except Committee.DoesNotExist:
            logger.error(f"Committee {committee_id} not found")
            return Response(
                {"status": "error", "message": "Committee not found"},
                status=status.HTTP_404_NOT_FOUND
            )


class GetCommitteesByMemberView(APIView):
    permission_classes = [CommitteePermission]

    def get(self, request, employee_id):
        try:
            user = CustomUser.objects.get(employee_id=employee_id)
            memberships = CommitteeMembership.objects.filter(user=user, is_active=True)
            committees = [membership.committee for membership in memberships]
            # Since this is a list of objects, we can't cleanly prefetch here easily without reconstructing the queryset,
            # but usually this list is small. Rebuilding as a queryset:
            committee_ids = [c.id for c in committees]
            qs = Committee.objects.filter(id__in=committee_ids).select_related(
                'created_by', 'created_by__user_role', 'procurement_plan'
            ).prefetch_related(
                'memberships', 'memberships__user'
            )
            serializer = CommitteeSerializer(qs, many=True, context={'request': request})
            logger.debug(f"Fetched {len(committees)} committees for user {employee_id}")
            return Response(
                {
                    "status": "success",
                    "results": len(serializer.data),
                    "data": {"committees": serializer.data}
                },
                status=status.HTTP_200_OK
            )
        except CustomUser.DoesNotExist:
            logger.error(f"User {employee_id} not found")
            return Response(
                {"status": "error", "message": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )


class GetCommitteesByTypeView(APIView):
    permission_classes = [CommitteePermission]

    def get(self, request, committee_type):
        try:
            qs = Committee.objects.filter(committee_type=committee_type).select_related(
                'created_by', 'created_by__user_role', 'procurement_plan'
            ).prefetch_related(
                'memberships', 'memberships__user'
            )
            if is_superadmin(request.user) or request.user.has_rbac_permission('committee.view_cross_office'):
                pass # Already filtered by type, no further restriction
            else:
                descendant_offices = []
                if request.user.office:
                    descendant_offices = request.user.office.get_descendants(include_self=True)
                
                qs = qs.filter(
                    models.Q(created_by=request.user) |
                    models.Q(memberships__user=request.user, memberships__is_active=True) |
                    models.Q(created_by__office__in=descendant_offices) |
                    models.Q(procurement_plan__office__in=descendant_offices)
                ).distinct()

            serializer = CommitteeSerializer(qs, many=True, context={'request': request})
            return Response(
                {
                    "status": "success",
                    "results": len(serializer.data),
                    "data": {"committees": serializer.data}
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Failed to fetch committees by type {committee_type}: {str(e)}")
            return Response(
                {"status": "error", "message": f"Failed to fetch committees: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetCommitteesByDateRangeView(APIView):
    permission_classes = [CommitteePermission]

    def get(self, request):
        start_date = request.query_params.get('startDate')
        end_date = request.query_params.get('endDate')

        if not start_date or not end_date:
            logger.error("Missing startDate or endDate")
            return Response(
                {"status": "error", "message": "startDate and endDate are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        start_date = parse_date(start_date)
        end_date = parse_date(end_date)

        if not start_date or not end_date:
            logger.error("Invalid date format")
            return Response(
                {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )

        committees = Committee.objects.filter(formation_date__range=[start_date, end_date]).select_related(
            'created_by', 'created_by__user_role', 'procurement_plan'
        ).prefetch_related(
            'memberships', 'memberships__user'
        )
        if is_superadmin(request.user) or request.user.has_rbac_permission('committee.view_cross_office'):
            pass  # Superadmin/Cross-office views all within range
        else:
            descendant_offices = []
            if request.user.office:
                descendant_offices = request.user.office.get_descendants(include_self=True)
            
            committees = committees.filter(
                models.Q(created_by=request.user) |
                models.Q(memberships__user=request.user, memberships__is_active=True) |
                models.Q(created_by__office__in=descendant_offices) |
                models.Q(procurement_plan__office__in=descendant_offices)
            ).distinct()

        serializer = CommitteeSerializer(committees, many=True, context={'request': request})
        logger.debug(f"Fetched {len(committees)} committees in date range")
        return Response(
            {
                "status": "success",
                "results": len(serializer.data),
                "data": {"committees": serializer.data}
            },
            status=status.HTTP_200_OK
        )


class DownloadFormationLetterView(APIView):
    permission_classes = [CommitteePermission]

    def get(self, request, committee_id):
        try:
            committee = Committee.objects.get(id=committee_id)
            self.check_object_permissions(request, committee)

            if not committee.formation_letter:
                logger.error(f"No formation letter for committee {committee_id}")
                return Response(
                    {"status": "error", "message": "No formation letter available"},
                    status=status.HTTP_404_NOT_FOUND
                )

            storage = committee.formation_letter.storage
            file_name = committee.formation_letter.name
            if not storage.exists(file_name):
                logger.error(f"Formation letter file not found for committee {committee_id}: {file_name}")
                return Response(
                    {"status": "error", "message": "Formation letter file not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            import mimetypes
            content_type, _ = mimetypes.guess_type(file_name)
            if not content_type:
                content_type = 'application/octet-stream'

            response = FileResponse(storage.open(file_name, 'rb'), content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{file_name.split("/")[-1]}"'
            logger.debug(f"Formation letter downloaded for committee {committee_id}")
            return response
        except ObjectDoesNotExist:
            logger.error(f"Committee {committee_id} not found")
            return Response(
                {"status": "error", "message": "Committee not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except FileNotFoundError:
            logger.error(f"Formation letter file not found for committee {committee_id}")
            return Response(
                {"status": "error", "message": "Formation letter file not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class PreviewFormationLetterView(APIView):
    permission_classes = [CommitteePermission]

    def get(self, request, committee_id):
        try:
            committee = Committee.objects.get(id=committee_id)
            self.check_object_permissions(request, committee)

            if not committee.formation_letter:
                logger.error(f"No formation letter for committee {committee_id}")
                return Response(
                    {"status": "error", "message": "No formation letter available"},
                    status=status.HTTP_404_NOT_FOUND
                )

            storage = committee.formation_letter.storage
            file_name = committee.formation_letter.name
            if not storage.exists(file_name):
                logger.error(f"Formation letter file not found for committee {committee_id}: {file_name}")
                return Response(
                    {"status": "error", "message": "Formation letter file not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            import mimetypes
            content_type, _ = mimetypes.guess_type(file_name)
            if not content_type:
                content_type = 'application/octet-stream'

            response = FileResponse(storage.open(file_name, 'rb'), content_type=content_type)
            # Content-Disposition 'inline' allows previewing in browsers
            response['Content-Disposition'] = f'inline; filename="{file_name.split("/")[-1]}"'
            logger.debug(f"Formation letter previewed for committee {committee_id}")
            return response
        except ObjectDoesNotExist:
            logger.error(f"Committee {committee_id} not found")
            return Response(
                {"status": "error", "message": "Committee not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except FileNotFoundError:
            logger.error(f"Formation letter file not found for committee {committee_id}")
            return Response(
                {"status": "error", "message": "Formation letter file not found"},
                status=status.HTTP_404_NOT_FOUND
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def committee_details_with_type(request, committee_id):
    """Get committee details with associated data based on committee type"""
    try:
        committee = Committee.objects.get(id=committee_id)

        # Get committee data
        committee_data = CommitteeSerializer(committee).data

        # Get associated data based on committee type
        associated_data = {}
        # specification, review, evaluation features are handled by their dedicated modules
        associated_data['info'] = 'Associated data not available in standalone CMS'

        return Response({
            'success': True,
            'data': {
                'committee': committee_data,
                'associated_data': associated_data
            }
        })

    except Committee.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Committee not found'
        }, status=status.HTTP_404_NOT_FOUND)


class GetCommitteesByProcurementPlanView(APIView):
    permission_classes = [CommitteePermission]

    def get(self, request, procurement_plan_id):
        """Get committees associated with a specific procurement plan"""
        logger.debug(f"GetCommitteesByProcurementPlanView called for procurement plan: {procurement_plan_id}")

        try:
            # Verify procurement plan exists
            try:
                procurement_plan = ProcurementPlan.objects.get(id=procurement_plan_id)
            except ObjectDoesNotExist:
                logger.error(f"ProcurementPlan {procurement_plan_id} not found")
                return Response(
                    {"status": "error", "message": "Procurement plan not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get committees for this procurement plan
            committees = Committee.objects.filter(procurement_plan_id=procurement_plan_id).select_related(
                'created_by', 'created_by__user_role', 'procurement_plan'
            ).prefetch_related(
                'memberships', 'memberships__user'
            )

            logger.debug(f"Found {committees.count()} committees for procurement plan {procurement_plan_id}")

            serializer = CommitteeSerializer(committees, many=True, context={'request': request})

            return Response({
                "status": "success",
                "message": f"Committees retrieved successfully for procurement plan {procurement_plan_id}",
                "data": serializer.data,
                "count": committees.count()
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving committees for procurement plan {procurement_plan_id}: {str(e)}")
            return Response(
                {"status": "error", "message": f"Error retrieving committees: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReviewCommitteeDefaultMembersView(APIView):
    """CRUD for default review committee members, optionally filtered by hierarchy level."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List active default members, optionally filtered by office_id or department."""
        defaults = ReviewCommitteeDefaultMember.objects.filter(is_active=True).select_related('user', 'office')

        office_id = request.query_params.get('office_id') or request.query_params.get('role_hierarchy_id')
        department = request.query_params.get('department')
        for_plan = request.query_params.get('for_plan')

        if for_plan:
            # Resolve: find office-specific defaults for the plan's office, fall back to global
            try:
                plan = ProcurementPlan.objects.get(id=for_plan)
                office = plan.office
                if office:
                    specific = defaults.filter(office=office)
                    if specific.exists():
                        defaults = specific
                    else:
                        # Search by ancestors or fallback to global
                        ancestors = office.get_ancestors()
                        found = False
                        for ancestor in reversed(ancestors):
                            specific = defaults.filter(office=ancestor)
                            if specific.exists():
                                defaults = specific
                                found = True
                                break
                        if not found:
                            defaults = defaults.filter(office__isnull=True)
                else:
                    defaults = defaults.filter(office__isnull=True)
            except ProcurementPlan.DoesNotExist:
                defaults = defaults.filter(office__isnull=True)
        elif office_id:
            if office_id == 'global':
                defaults = defaults.filter(office__isnull=True)
            else:
                defaults = defaults.filter(office_id=office_id)
        elif department:
            # If department provided, find linked office
            office = Office.objects.filter(name__iexact=department).first()
            if office:
                defaults = defaults.filter(office=office)
            else:
                defaults = defaults.filter(office__isnull=True)

        data = [
            {
                'id': d.id,
                'employeeId': d.user.employee_id,
                'name': d.user.name or d.user.username,
                'email': d.user.email,
                'department': getattr(d.user, 'department', None),
                'user_office_name': d.user.office.name if getattr(d.user, 'office', None) else None,
                'designation': getattr(d.user, 'designation', None),
                'committee_role': d.committee_role,
                'is_active': d.is_active,
                'office_id': d.office_id,
                'office_name': d.office.name if d.office else None,
            }
            for d in defaults
        ]
        return Response({'status': 'success', 'data': data}, status=status.HTTP_200_OK)

    def post(self, request):
        """Add a default member, optionally tied to an office."""
        if not request.user.has_rbac_permission('settings.review_defaults'):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        employee_id = request.data.get('employeeId')
        committee_role = request.data.get('committeeRole', 'member')
        office_id = request.data.get('officeId') or request.data.get('roleHierarchyId')

        if not employee_id:
            return Response({'error': 'employeeId is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(employee_id=employee_id)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        office = None
        if office_id:
            try:
                office = Office.objects.get(id=office_id)
            except Office.DoesNotExist:
                return Response({'error': 'Office not found.'}, status=status.HTTP_404_NOT_FOUND)

        if ReviewCommitteeDefaultMember.objects.filter(
            user=user, committee_role=committee_role, office=office
        ).exists():
            return Response(
                {'error': 'This user is already a default member with this role at this office level.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        default_member = ReviewCommitteeDefaultMember.objects.create(
            user=user, committee_role=committee_role, office=office, is_active=True
        )
        return Response({
            'status': 'success',
            'data': {
                'id': default_member.id,
                'employeeId': user.employee_id,
                'name': user.name or user.username,
                'email': user.email,
                'committee_role': default_member.committee_role,
                'office_id': default_member.office_id,
                'office_name': default_member.office.name if default_member.office else None,
            }
        }, status=status.HTTP_201_CREATED)


class ReviewCommitteeDefaultMembersDeleteView(APIView):
    """Delete a default review committee member."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Remove a default member by id."""
        if not request.user.has_rbac_permission('settings.review_defaults'):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        default_id = request.data.get('id')
        if not default_id:
            return Response({'error': 'id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            default_member = ReviewCommitteeDefaultMember.objects.get(id=default_id)
            default_member.delete()
            return Response({'status': 'success', 'message': 'Default member removed.'}, status=status.HTTP_200_OK)
        except ReviewCommitteeDefaultMember.DoesNotExist:
            return Response({'error': 'Default member not found.'}, status=status.HTTP_404_NOT_FOUND)


class CommitteePhaseCheckpointView(APIView):
    """Manage committee phase checkpoints"""
    permission_classes = [IsAuthenticated]

    def get(self, request, committee_id):
        """Get all checkpoints for a committee"""
        try:
            committee = Committee.objects.get(id=committee_id)
            checkpoints = CommitteePhaseCheckpoint.objects.filter(committee=committee).order_by('phase', 'order')
            
            from .serializers import CommitteePhaseCheckpointSerializer
            serializer = CommitteePhaseCheckpointSerializer(checkpoints, many=True)
            
            return Response({
                'status': 'success',
                'data': {
                    'committee_id': committee.id,
                    'checkpoints': serializer.data
                }
            }, status=status.HTTP_200_OK)
        except Committee.DoesNotExist:
            return Response(
                {'status': 'error', 'message': 'Committee not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.exception(f"Error fetching checkpoints: {str(e)}")
            return Response(
                {'status': 'error', 'message': 'An error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request, committee_id):
        """Create checkpoints for a committee (initialization of phases)"""
        try:
            committee = Committee.objects.get(id=committee_id)
            
            # Create default checkpoints for initialization phase
            init_checkpoints = [
                {
                    'phase': 'initialization',
                    'name': 'Committee Formation',
                    'description': 'Committee has been properly formed with all members assigned',
                    'order': 1
                },
                {
                    'phase': 'initialization',
                    'name': 'First Meeting',
                    'description': 'Committee conducted its first official meeting',
                    'order': 2
                },
                {
                    'phase': 'initialization',
                    'name': 'Specification Review',
                    'description': 'Tender specifications have been reviewed and finalized',
                    'order': 3
                }
            ]
            
            # Create default checkpoints for finalization phase
            final_checkpoints = [
                {
                    'phase': 'finalization',
                    'name': 'Evaluation Complete',
                    'description': 'Evaluation process has been completed',
                    'order': 1
                },
                {
                    'phase': 'finalization',
                    'name': 'Report Generation',
                    'description': 'Committee report has been generated',
                    'order': 2
                },
                {
                    'phase': 'finalization',
                    'name': 'Final Approval',
                    'description': 'Final recommendations have been approved',
                    'order': 3
                }
            ]
            
            all_checkpoints = init_checkpoints + final_checkpoints
            created_checkpoints = []
            
            for cp_data in all_checkpoints:
                checkpoint, created = CommitteePhaseCheckpoint.objects.get_or_create(
                    committee=committee,
                    phase=cp_data['phase'],
                    order=cp_data['order'],
                    defaults={
                        'name': cp_data['name'],
                        'description': cp_data['description'],
                    }
                )
                if created:
                    created_checkpoints.append(checkpoint)
            
            from .serializers import CommitteePhaseCheckpointSerializer
            serializer = CommitteePhaseCheckpointSerializer(created_checkpoints, many=True)
            
            return Response({
                'status': 'success',
                'message': f'{len(created_checkpoints)} checkpoints created',
                'data': {
                    'checkpoints': serializer.data
                }
            }, status=status.HTTP_201_CREATED)
        except Committee.DoesNotExist:
            return Response(
                {'status': 'error', 'message': 'Committee not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.exception(f"Error creating checkpoints: {str(e)}")
            return Response(
                {'status': 'error', 'message': 'An error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CommitteePhaseCheckpointDetailView(APIView):
    """Mark checkpoints as complete"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, checkpoint_id):
        """Mark a checkpoint as complete"""
        try:
            checkpoint = CommitteePhaseCheckpoint.objects.get(id=checkpoint_id)
            
            # Mark checkpoint as complete
            checkpoint.mark_completed(user=request.user)
            
            from .serializers import CommitteePhaseCheckpointSerializer
            serializer = CommitteePhaseCheckpointSerializer(checkpoint)
            
            return Response({
                'status': 'success',
                'message': 'Checkpoint marked as complete',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except CommitteePhaseCheckpoint.DoesNotExist:
            return Response(
                {'status': 'error', 'message': 'Checkpoint not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.exception(f"Error updating checkpoint: {str(e)}")
            return Response(
                {'status': 'error', 'message': 'An error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CommitteePhaseTransitionView(APIView):
    """Handle phase transitions"""
    permission_classes = [IsAuthenticated]

    def post(self, request, committee_id):
        """Move committee to next phase"""
        try:
            committee = Committee.objects.get(id=committee_id)
            
            # Check if initialization is complete before allowing finalization
            if committee.current_phase == 'initialization' and not committee.initialization_phase_completed:
                return Response({
                    'status': 'error',
                    'message': 'Cannot move to finalization phase until all initialization checkpoints are complete'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Transition to next phase
            if committee.current_phase == 'initialization':
                committee.current_phase = 'finalization'
                committee.save()
                return Response({
                    'status': 'success',
                    'message': 'Committee moved to finalization phase',
                    'data': {'current_phase': committee.current_phase}
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Committee has already reached the final phase'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Committee.DoesNotExist:
            return Response(
                {'status': 'error', 'message': 'Committee not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.exception(f"Error transitioning phase: {str(e)}")
            return Response(
                {'status': 'error', 'message': 'An error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ---------------------------------------------------------------------------
# Committee status transition
# ---------------------------------------------------------------------------

class CommitteeStatusView(APIView):
    """Update only the committee_status field without going through full serializer validation."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, committee_id):
        try:
            committee = Committee.objects.get(id=committee_id)
        except Committee.DoesNotExist:
            return Response({'status': 'error', 'message': 'Committee not found'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('committee_status')
        valid_statuses = [s[0] for s in Committee.COMMITTEE_STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {'status': 'error', 'message': f'Invalid status. Valid choices: {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        committee.committee_status = new_status
        update_fields = ['committee_status', 'updated_at']
        notes = request.data.get('completion_notes')
        if notes is not None:
            committee.completion_notes = notes
            update_fields.append('completion_notes')
        committee.save(update_fields=update_fields)
        return Response({'status': 'success', 'data': {'committee_status': committee.committee_status}})


# ---------------------------------------------------------------------------
# Committee document endpoints
# ---------------------------------------------------------------------------

class CommitteeDocumentView(APIView):
    """List and upload documents for the In Progress phase."""
    permission_classes = [IsAuthenticated]

    def get(self, request, committee_id):
        try:
            committee = Committee.objects.get(id=committee_id)
        except Committee.DoesNotExist:
            return Response({'status': 'error', 'message': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        docs = committee.documents.order_by('-uploaded_at')
        data = [
            {
                'id': d.id,
                'name': d.name or d.file.name.split('/')[-1],
                'url': request.build_absolute_uri(d.file.url) if d.file else None,
                'uploaded_at': d.uploaded_at,
                'uploaded_by': d.uploaded_by.get_full_name() if d.uploaded_by else None,
            }
            for d in docs
        ]
        return Response({'status': 'success', 'data': data})

    def post(self, request, committee_id):
        try:
            committee = Committee.objects.get(id=committee_id)
        except Committee.DoesNotExist:
            return Response({'status': 'error', 'message': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        file = request.FILES.get('file')
        if not file:
            return Response({'status': 'error', 'message': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        name = request.data.get('name', '') or file.name
        doc = CommitteeDocument.objects.create(
            committee=committee,
            file=file,
            name=name,
            uploaded_by=request.user,
        )
        return Response({
            'status': 'success',
            'data': {
                'id': doc.id,
                'name': doc.name,
                'url': request.build_absolute_uri(doc.file.url),
                'uploaded_at': doc.uploaded_at,
            }
        }, status=status.HTTP_201_CREATED)


class CommitteeDocumentDetailView(APIView):
    """Delete a single document."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, committee_id, doc_id):
        try:
            doc = CommitteeDocument.objects.get(id=doc_id, committee_id=committee_id)
        except CommitteeDocument.DoesNotExist:
            return Response({'status': 'error', 'message': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        doc.file.delete(save=False)
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CommitteeDocumentServeView(APIView):
    """Stream a committee document through Django so storage credentials stay server-side."""
    permission_classes = [IsAuthenticated]

    def get(self, request, committee_id, doc_id):
        import mimetypes
        try:
            doc = CommitteeDocument.objects.get(id=doc_id, committee_id=committee_id)
        except CommitteeDocument.DoesNotExist:
            return Response({'status': 'error', 'message': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        storage = doc.file.storage
        file_name = doc.file.name
        try:
            content_type, _ = mimetypes.guess_type(file_name)
            content_type = content_type or 'application/octet-stream'
            response = FileResponse(storage.open(file_name, 'rb'), content_type=content_type)
            display_name = file_name.split('/')[-1]
            response['Content-Disposition'] = f'inline; filename="{display_name}"'
            return response
        except FileNotFoundError:
            return Response({'status': 'error', 'message': 'File not found in storage'}, status=status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Reporting endpoints
# ---------------------------------------------------------------------------

def _is_committee_admin(user):
    return is_superadmin(user) or user.has_rbac_permission('committee.view_cross_office')


def _committee_report_item(committee, *, my_role=None, membership_active=None,
                           joined_at=None, left_at=None):
    """Compact committee dict for report lists (avoids full serializer cost)."""
    closed = is_committee_closed(committee)
    item = {
        "committee_id": committee.id,
        "name": committee.name,
        "committee_type": committee.committee_type,
        "committee_status": committee.committee_status,
        "office_name": (
            committee.office.name if committee.office
            else (committee.procurement_plan.office.name
                  if committee.procurement_plan and committee.procurement_plan.office else None)
        ),
        "deadline": committee.deadline,
        "members_count": committee.memberships.filter(is_active=True).count(),
        "is_closed": closed,
        "is_overdue": is_committee_overdue(committee),
    }
    if my_role is not None:
        item["my_role"] = my_role
    if membership_active is not None:
        item["membership_active"] = membership_active
        item["joined_at"] = joined_at
        item["left_at"] = left_at
        item["left_reason"] = (
            "removed" if not membership_active else ("closed" if closed else None)
        )
    return item


class MyCommitteesReportView(APIView):
    """GET /committees/reports/my-committees/ — the user's active vs past committees."""
    permission_classes = [CommitteePermission]

    def get(self, request):
        memberships = (
            CommitteeMembership.objects
            .filter(user=request.user)
            .select_related('committee', 'committee__office', 'committee__procurement_plan',
                            'committee__procurement_plan__office')
            .prefetch_related('committee__checkpoints')
        )
        active, past = [], []
        for m in memberships:
            committee = m.committee
            item = _committee_report_item(
                committee, my_role=m.committee_role, membership_active=m.is_active,
                joined_at=m.created_at, left_at=m.left_at,
            )
            # Active: still a member AND committee not closed. Otherwise it's past
            # (removed, or closed-but-still-member).
            if m.is_active and not item["is_closed"]:
                active.append(item)
            else:
                past.append(item)

        return Response({
            "status": "success",
            "data": {
                "active": active,
                "past": past,
                "counts": {"active": len(active), "past": len(past)},
            },
        }, status=status.HTTP_200_OK)


class OfficeCommitteesView(APIView):
    """GET /committees/reports/office/ — committees tied to the user's office.

    Admins/cross-office users may pass ?office_id= to view another office.
    """
    permission_classes = [CommitteePermission]

    def get(self, request):
        office_id = request.query_params.get('office_id')
        if office_id and _is_committee_admin(request.user):
            office = Office.objects.filter(id=office_id).first()
        else:
            office = request.user.office

        if not office:
            return Response(
                {"status": "success", "results": 0, "data": {"committees": []},
                 "office": None},
                status=status.HTTP_200_OK,
            )

        committees = Committee.objects.filter(
            models.Q(office=office) | models.Q(procurement_plan__office=office)
        ).select_related(
            'created_by', 'created_by__user_role', 'office', 'procurement_plan'
        ).prefetch_related('memberships', 'memberships__user', 'checkpoints').distinct()

        serializer = CommitteeSerializer(committees, many=True, context={'request': request})
        return Response({
            "status": "success",
            "results": len(serializer.data),
            "office": {"id": office.id, "name": office.name},
            "data": {"committees": serializer.data},
        }, status=status.HTTP_200_OK)


class CommitteeStatsView(APIView):
    """GET /committees/reports/stats/ — aggregate counts for cards & charts.

    Admins (or ?office_id=) see org-wide / a chosen office; regular users see
    their personal + own-office committees.
    """
    permission_classes = [CommitteePermission]

    def get(self, request):
        admin = _is_committee_admin(request.user)
        office_id = request.query_params.get('office_id')

        if admin and office_id:
            qs = Committee.objects.filter(
                models.Q(office_id=office_id) | models.Q(procurement_plan__office_id=office_id)
            )
            scope = "office"
        elif admin:
            qs = Committee.objects.all()
            scope = "org"
        else:
            office = request.user.office
            office_q = models.Q()
            if office:
                office_q = models.Q(office=office) | models.Q(procurement_plan__office=office)
            qs = Committee.objects.filter(
                models.Q(created_by=request.user)
                | models.Q(memberships__user=request.user, memberships__is_active=True)
                | office_q
            )
            scope = "personal"

        qs = qs.distinct()

        by_status = list(qs.values('committee_status').annotate(count=models.Count('id')).order_by())
        by_type = list(qs.values('committee_type').annotate(count=models.Count('id')).order_by())
        by_office = list(
            qs.values('office_id', 'office__name').annotate(count=models.Count('id')).order_by()
        )
        by_office = [
            {"office_id": r["office_id"], "office_name": r["office__name"], "count": r["count"]}
            for r in by_office
        ]

        # closed/overdue depend on the checkpoint-derived property → compute in Python.
        total = closed = overdue = 0
        for c in qs.prefetch_related('checkpoints'):
            total += 1
            if is_committee_closed(c):
                closed += 1
            elif is_committee_overdue(c):
                overdue += 1

        return Response({
            "status": "success",
            "scope": scope,
            "data": {
                "totals": {"total": total, "closed": closed, "open": total - closed, "overdue": overdue},
                "by_status": by_status,
                "by_type": by_type,
                "by_office": by_office,
            },
        }, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# Report: Role Distribution
# ─────────────────────────────────────────────────────────────────────────────

class RoleDistributionReportView(APIView):
    """GET /committees/reports/role-distribution/

    Returns how many active members hold each committee role across all
    committees, plus a per-role member breakdown (name, employee_id,
    committee_count).  Requires committee.view_cross_office permission.
    """
    permission_classes = [IsAuthenticated, HasPermission('committee.view_cross_office')]

    def get(self, request):
        from django.db.models import Count, Q

        # All active memberships
        memberships = (
            CommitteeMembership.objects
            .filter(is_active=True)
            .select_related('user', 'committee', 'committee__office')
        )

        # Build role → {member_id → {name, employee_id, committees[]}}
        role_map: dict = {}
        for m in memberships:
            role = (m.committee_role or 'member').strip()
            if role not in role_map:
                role_map[role] = {}
            uid = m.user.employee_id
            if uid not in role_map[role]:
                role_map[role][uid] = {
                    'employee_id': uid,
                    'name': (
                        f"{m.user.first_name} {m.user.last_name}".strip()
                        or m.user.username
                    ),
                    'office': m.user.office.name if m.user.office else None,
                    'committees': [],
                }
            role_map[role][uid]['committees'].append({
                'id': m.committee.id,
                'name': m.committee.name,
                'office': m.committee.office.name if m.committee.office else None,
                'status': m.committee.committee_status,
            })

        result = []
        for role, members in sorted(role_map.items()):
            member_list = sorted(
                [
                    {**info, 'committee_count': len(info['committees'])}
                    for info in members.values()
                ],
                key=lambda x: -x['committee_count'],
            )
            result.append({
                'role': role,
                'member_count': len(member_list),
                'total_memberships': sum(m['committee_count'] for m in member_list),
                'members': member_list,
            })

        # Sort by member_count descending
        result.sort(key=lambda r: -r['member_count'])

        return Response({'roles': result}, status=200)


# ─────────────────────────────────────────────────────────────────────────────
# Report: Stalled / Inactive Committees
# ─────────────────────────────────────────────────────────────────────────────

class StalledCommitteesReportView(APIView):
    """GET /committees/reports/stalled/?days=30

    Returns non-closed committees whose last activity (updated_at or latest
    document upload) is older than `days` days.  Requires
    committee.view_cross_office permission.
    """
    permission_classes = [IsAuthenticated, HasPermission('committee.view_cross_office')]

    def get(self, request):
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Max, Subquery, OuterRef

        try:
            days = max(1, int(request.query_params.get('days', 30)))
        except (ValueError, TypeError):
            days = 30

        cutoff = timezone.now() - timedelta(days=days)

        # Latest document upload per committee (subquery)
        latest_doc = (
            CommitteeDocument.objects
            .filter(committee=OuterRef('pk'))
            .order_by('-uploaded_at')
            .values('uploaded_at')[:1]
        )

        qs = (
            Committee.objects
            .exclude(committee_status__in=['completed', 'dissolved'])
            .annotate(latest_doc_at=Subquery(latest_doc))
            .select_related('office', 'created_by')
            .prefetch_related('checkpoints', 'memberships__user')
        )

        stalled = []
        for c in qs:
            # Skip if already closed via checkpoint logic
            if is_committee_closed(c):
                continue

            # Determine last activity: max of updated_at and latest doc upload
            last_activity = c.updated_at
            if c.latest_doc_at and c.latest_doc_at > last_activity:
                last_activity = c.latest_doc_at

            if last_activity >= cutoff:
                continue  # Active recently — not stalled

            days_stalled = (timezone.now() - last_activity).days

            active_members = [
                {
                    'employee_id': m.user.employee_id,
                    'name': (
                        f"{m.user.first_name} {m.user.last_name}".strip()
                        or m.user.username
                    ),
                    'role': m.committee_role,
                }
                for m in c.memberships.filter(is_active=True)
            ]

            stalled.append({
                'id': c.id,
                'name': c.name,
                'committee_type': c.committee_type,
                'committee_status': c.committee_status,
                'office': c.office.name if c.office else None,
                'created_at': c.created_at.isoformat(),
                'last_activity': last_activity.isoformat(),
                'days_stalled': days_stalled,
                'is_overdue': is_committee_overdue(c),
                'deadline': c.deadline.isoformat() if c.deadline else None,
                'member_count': len(active_members),
                'members': active_members,
            })

        # Sort: most stalled first
        stalled.sort(key=lambda x: -x['days_stalled'])

        return Response({
            'days_threshold': days,
            'cutoff': cutoff.isoformat(),
            'count': len(stalled),
            'committees': stalled,
        }, status=200)
