import logging
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone
from ..models import ProcurementDocument, DocumentAccessLog
from ..serializers import (
    ProcurementDocumentSerializer,
    DocumentUploadSerializer,
    DocumentAccessLogSerializer,
    DocumentVersionSerializer,
    DocumentBulkActionSerializer
)
from users.utils import is_superadmin, get_queryset_for_user
from users.permissions import HasPermission

logger = logging.getLogger(__name__)

class DocumentListCreateView(generics.ListCreateAPIView):
    """
    List all documents or upload a new document.
    Users can only see documents for procurement plans they have access to.
    """
    queryset = ProcurementDocument.objects.all()
    permission_classes = [IsAuthenticated, HasPermission('planning.view')]
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), HasPermission('planning.manage')()]
        return [IsAuthenticated(), HasPermission('planning.view')()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DocumentUploadSerializer
        return ProcurementDocumentSerializer

    def get_queryset(self):
        user = self.request.user
        if not getattr(user, 'user_role', None):
            return ProcurementDocument.objects.none()

        action = 'manage' if self.request.method == 'POST' else 'view'
        # Get scoped documents
        queryset = get_queryset_for_user(user, ProcurementDocument.objects.all(), action=action)
        queryset = queryset.select_related('procurement_plan', 'uploaded_by').order_by('-created_at')

        # Filter by can_access (document-level logic)
        accessible_docs = [doc.pk for doc in queryset if doc.can_access(user)]
        queryset = queryset.filter(pk__in=accessible_docs)

        # Optional filtering by procurement plan
        procurement_plan_id = self.request.query_params.get('procurement_plan', None)
        if procurement_plan_id:
            queryset = queryset.filter(procurement_plan_id=procurement_plan_id)

        # Optional filtering by document type
        document_type = self.request.query_params.get('document_type', None)
        if document_type:
            queryset = queryset.filter(document_type=document_type)

        # Optional filtering by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Optional filtering by access level
        access_level = self.request.query_params.get('access_level', None)
        if access_level:
            queryset = queryset.filter(access_level=access_level)

        # Only show current versions by default
        show_all_versions = self.request.query_params.get('show_all_versions', 'false')
        if show_all_versions.lower() != 'true':
            queryset = queryset.filter(is_current_version=True)

        return queryset

    def perform_create(self, serializer):
        # Ensure the procurement plan exists and user has access to it
        procurement_plan = serializer.validated_data.get('procurement_plan')
        if procurement_plan:
            user = self.request.user
            if not is_superadmin(user):
                # Check if procurement plan's office is in user's office subtree
                if not (user.office and procurement_plan.office and procurement_plan.office in user.office.get_descendants(include_self=True)):
                    raise PermissionError("You don't have permission to upload documents for this procurement plan.")

        document = serializer.save(uploaded_by=self.request.user)

        # Update committee completion_date if this is a specification, review, evaluation, decision, or main_contract document
        tracked_types = ['specification', 'review', 'evaluation', 'decision', 'main_contract']
        if document.document_type in tracked_types and document.custom_metadata:
            submission_date = document.custom_metadata.get('submission_date')
            if submission_date:
                try:
                    from committee.models import Committee
                    # Map document type to committee type
                    if document.document_type in ['evaluation', 'decision']:
                        c_type = 'evaluation'
                    elif document.document_type == 'main_contract':
                        c_type = 'contract'
                    else:
                        c_type = document.document_type
                        
                    committees = Committee.objects.filter(
                        procurement_plan=document.procurement_plan,
                        committee_type=c_type
                    )

                    if document.document_type == 'evaluation':
                        eval_type = document.custom_metadata.get('evaluation_type')
                        if eval_type == 'technical':
                            committees.update(technical_evaluation_completion_date=submission_date)
                        elif eval_type == 'financial':
                            committees.update(financial_evaluation_completion_date=submission_date)
                        elif eval_type == 'decision':
                            committees.update(decision_date=submission_date)
                        else:
                            # Primary completion date (fallback or single stage)
                            committees.update(completion_date=submission_date)
                    elif document.document_type == 'decision':
                        committees.update(decision_date=submission_date)
                    else:
                        committees.update(completion_date=submission_date)
                except Exception as e:
                    logger.error(f"Failed to update committee completion date: {str(e)}")

        # Log the upload action
        DocumentAccessLog.objects.create(
            document=document,
            user=self.request.user,
            action='upload',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )

    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

    def get(self, request, *args, **kwargs):
        if not getattr(request.user, 'user_role', None):
            return Response(
                {'error': 'User must have a role to view documents.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().get(request, *args, **kwargs)


class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a document instance.
    Users can only access documents they have permission to view.
    """
    queryset = ProcurementDocument.objects.all()
    serializer_class = ProcurementDocumentSerializer
    permission_classes = [IsAuthenticated, HasPermission('planning.view')]
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), HasPermission('planning.manage')()]
        return [IsAuthenticated(), HasPermission('planning.view')()]

    def get_queryset(self):
        user = self.request.user
        if not getattr(user, 'user_role', None):
            return ProcurementDocument.objects.none()

        action = 'manage' if self.request.method in ['PUT', 'PATCH', 'DELETE'] else 'view'
        # Get scoped documents
        return get_queryset_for_user(user, ProcurementDocument.objects.all(), action=action).select_related('procurement_plan', 'uploaded_by')

    def get_object(self):
        obj = super().get_object()
        if not obj.can_access(self.request.user):
            raise Http404("Document not found or access denied.")
        return obj

    def retrieve(self, request, *args, **kwargs):
        if not getattr(request.user, 'user_role', None):
            return Response(
                {'error': 'User must have a role to view document details.'},
                status=status.HTTP_403_FORBIDDEN
            )

        document = self.get_object()

        # Log the view action
        DocumentAccessLog.objects.create(
            document=document,
            user=request.user,
            action='view',
            ip_address=self.get_client_ip(),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        return super().retrieve(request, *args, **kwargs)

    def perform_update(self, serializer):
        document = serializer.save()

        # Log the update action
        DocumentAccessLog.objects.create(
            document=document,
            user=self.request.user,
            action='update',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )

    def perform_destroy(self, instance):
        # Log the delete action before deletion
        DocumentAccessLog.objects.create(
            document=instance,
            user=self.request.user,
            action='delete',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
        instance.delete()

    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


@api_view(['GET'])
@permission_classes([IsAuthenticated, HasPermission('planning.view')])
def download_document(request, pk):
    """
    Download a document file with proper access control and audit logging.
    """
    if not getattr(request.user, 'user_role', None):
        return Response(
            {'error': 'User must have a role to download documents.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Get user and scoped documents
    user = request.user
    queryset = get_queryset_for_user(user, ProcurementDocument.objects.all(), action="view")

    # Get document with access control
    document = get_object_or_404(queryset, pk=pk)

    # Check if user can access this document
    if not document.can_access(user):
        return Response(
            {'error': 'Access denied to this document.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Check if document is expired
    if document.is_expired():
        return Response(
            {'error': 'Document has expired and is no longer available.'},
            status=status.HTTP_410_GONE
        )

    # Log the download action
    DocumentAccessLog.objects.create(
        document=document,
        user=user,
        action='download',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )

    # Record access in document
    document.record_access(user)

    # Serve the file
    if document.file:
        response = HttpResponse()
        response['Content-Type'] = document.mime_type or 'application/octet-stream'
        response['Content-Disposition'] = f'attachment; filename="{document.file_name}"'
        response['X-Accel-Redirect'] = document.file.url  # For nginx
        response['Content-Length'] = document.file_size or 0

        # For development, serve file directly
        if hasattr(document.file, 'read'):
            response.write(document.file.read())

        return response
    else:
        return Response(
            {'error': 'File not found.'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, HasPermission('planning.manage')])
def create_document_version(request, pk):
    """
    Create a new version of an existing document.
    """
    if not getattr(request.user, 'user_role', None):
        return Response(
            {'error': 'User must have a role to create document versions.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Get user and scoped documents
    user = request.user
    queryset = get_queryset_for_user(user, ProcurementDocument.objects.all(), action="manage")

    # Get original document with access control
    original_document = get_object_or_404(queryset, pk=pk)

    # Check if user can access this document
    if not original_document.can_access(user):
        return Response(
            {'error': 'Access denied to this document.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Get version notes from request
    version_notes = request.data.get('version_notes', '')

    # Create new version
    try:
        new_document = original_document.create_new_version(
            user=user,
            version_notes=version_notes,
            **{k: v for k, v in request.data.items() if k != 'version_notes'}
        )

        # Log the version creation
        DocumentAccessLog.objects.create(
            document=new_document,
            user=user,
            action='upload',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            additional_data={'action_type': 'version_creation', 'parent_document_id': original_document.id}
        )

        serializer = ProcurementDocumentSerializer(new_document, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {'error': f'Failed to create new version: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, HasPermission('planning.view')])
def document_version_history(request, pk):
    """
    Get version history for a document.
    """
    if not getattr(request.user, 'user_role', None):
        return Response(
            {'error': 'User must have a role to view document versions.'},
            status=status.HTTP_403_FORBIDDEN
        )

    user = request.user
    queryset = get_queryset_for_user(user, ProcurementDocument.objects.all(), action="view")

    # Get document with access control
    document = get_object_or_404(queryset, pk=pk)

    if not document.can_access(user):
        return Response(
            {'error': 'Access denied to this document.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Get version history
    versions = document.get_version_history()
    serializer = DocumentVersionSerializer(versions, many=True, context={'request': request})

    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, HasPermission('planning.view')])
def document_access_logs(request, pk):
    """
    Get access logs for a document.
    """
    if not getattr(request.user, 'user_role', None):
        return Response(
            {'error': 'User must have a role to view document access logs.'},
            status=status.HTTP_403_FORBIDDEN
        )

    user = request.user
    queryset = get_queryset_for_user(user, ProcurementDocument.objects.all(), action="view")

    # Get document with access control
    document = get_object_or_404(queryset, pk=pk)

    if not document.can_access(user):
        return Response(
            {'error': 'Access denied to this document.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Get access logs
    logs = DocumentAccessLog.objects.filter(document=document).order_by('-timestamp')
    serializer = DocumentAccessLogSerializer(logs, many=True, context={'request': request})

    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, HasPermission('planning.manage')])
def approve_document(request, pk):
    """
    Approve a document.
    """
    if not getattr(request.user, 'user_role', None):
        return Response(
            {'error': 'User must have a role to approve documents.'},
            status=status.HTTP_403_FORBIDDEN
        )

    user = request.user
    queryset = get_queryset_for_user(user, ProcurementDocument.objects.all(), action="manage")

    # Get document with access control
    document = get_object_or_404(queryset, pk=pk)

    if not document.can_access(user):
        return Response(
            {'error': 'Access denied to this document.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Update document status
    notes = request.data.get('notes', '')
    document.status = 'approved'
    document.approved_by = user
    document.approved_at = timezone.now()
    document.approval_notes = notes
    document.save()

    # Log the approval action
    DocumentAccessLog.objects.create(
        document=document,
        user=user,
        action='approve',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        additional_data={'notes': notes}
    )

    serializer = ProcurementDocumentSerializer(document, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, HasPermission('planning.manage')])
def reject_document(request, pk):
    """
    Reject a document.
    """
    if not getattr(request.user, 'user_role', None):
        return Response(
            {'error': 'User must have a role to reject documents.'},
            status=status.HTTP_403_FORBIDDEN
        )

    user = request.user
    queryset = get_queryset_for_user(user, ProcurementDocument.objects.all(), action="manage")

    # Get document with access control
    document = get_object_or_404(queryset, pk=pk)

    if not document.can_access(user):
        return Response(
            {'error': 'Access denied to this document.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Update document status
    notes = request.data.get('notes', '')
    document.status = 'rejected'
    document.approved_by = user
    document.approved_at = timezone.now()
    document.approval_notes = notes
    document.save()

    # Log the rejection action
    DocumentAccessLog.objects.create(
        document=document,
        user=user,
        action='reject',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        additional_data={'notes': notes}
    )

    serializer = ProcurementDocumentSerializer(document, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, HasPermission('planning.manage')])
def bulk_document_action(request):
    """
    Perform bulk actions on multiple documents.
    """
    if not getattr(request.user, 'user_role', None):
        return Response(
            {'error': 'User must have a role to perform bulk actions.'},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = DocumentBulkActionSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    action = serializer.validated_data['action']
    document_ids = serializer.validated_data['document_ids']
    parameters = serializer.validated_data.get('parameters', {})

    user = request.user
    
    # Get documents with access control
    documents = get_queryset_for_user(user, ProcurementDocument.objects.filter(id__in=document_ids), action='manage')

    # Filter by access permissions
    accessible_docs = [doc for doc in documents if doc.can_access(user)]

    if len(accessible_docs) != len(document_ids):
        return Response(
            {'error': 'Some documents are not accessible.'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        with transaction.atomic():
            results = []
            for document in accessible_docs:
                if action == 'delete':
                    # Log before deletion
                    DocumentAccessLog.objects.create(
                        document=document,
                        user=user,
                        action='delete',
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        additional_data={'bulk_action': True}
                    )
                    document.delete()
                    results.append({'id': document.id, 'status': 'deleted'})

                elif action == 'approve':
                    document.status = 'approved'
                    document.approved_by = user
                    document.approved_at = timezone.now()
                    document.approval_notes = parameters.get('notes', '')
                    document.save()

                    DocumentAccessLog.objects.create(
                        document=document,
                        user=user,
                        action='approve',
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        additional_data={'bulk_action': True, 'notes': parameters.get('notes', '')}
                    )
                    results.append({'id': document.id, 'status': 'approved'})

                elif action == 'reject':
                    document.status = 'rejected'
                    document.approved_by = user
                    document.approved_at = timezone.now()
                    document.approval_notes = parameters.get('notes', '')
                    document.save()

                    DocumentAccessLog.objects.create(
                        document=document,
                        user=user,
                        action='reject',
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        additional_data={'bulk_action': True, 'notes': parameters.get('notes', '')}
                    )
                    results.append({'id': document.id, 'status': 'rejected'})

                elif action == 'change_access_level':
                    new_access_level = parameters.get('access_level')
                    if new_access_level:
                        document.access_level = new_access_level
                        document.save()
                        results.append({'id': document.id, 'status': f'access_level_changed_to_{new_access_level}'})

                elif action == 'add_tags':
                    new_tags = parameters.get('tags', [])
                    if new_tags:
                        existing_tags = set(document.tags)
                        existing_tags.update(new_tags)
                        document.tags = list(existing_tags)
                        document.save()
                        results.append({'id': document.id, 'status': 'tags_added'})

                elif action == 'remove_tags':
                    remove_tags = parameters.get('tags', [])
                    if remove_tags:
                        existing_tags = set(document.tags)
                        existing_tags.difference_update(remove_tags)
                        document.tags = list(existing_tags)
                        document.save()
                        results.append({'id': document.id, 'status': 'tags_removed'})

            return Response({
                'action': action,
                'processed_count': len(results),
                'results': results
            })

    except Exception as e:
        return Response(
            {'error': f'Bulk action failed: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, HasPermission('planning.view')])
def search_documents(request):
    """
    Search documents by query string.
    """
    if not getattr(request.user, 'user_role', None):
        return Response(
            {'error': 'User must have a role to search documents.'},
            status=status.HTTP_403_FORBIDDEN
        )

    query = request.query_params.get('search', '')
    if not query:
        return Response(
            {'error': 'Search query is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = request.user
    
    # Base queryset with access control
    queryset = get_queryset_for_user(user, ProcurementDocument.objects.all(), action='view').select_related('procurement_plan', 'uploaded_by')

    # Apply search filters
    search_queryset = queryset.filter(
        Q(title__icontains=query) |
        Q(description__icontains=query) |
        Q(tags__icontains=query) |
        Q(file_name__icontains=query)
    )

    # Filter by access permissions
    accessible_docs = []
    for doc in search_queryset:
        if doc.can_access(user):
            accessible_docs.append(doc.pk)

    final_queryset = search_queryset.filter(pk__in=accessible_docs).order_by('-created_at')

    # Apply additional filters if provided
    document_type = request.query_params.get('document_type', None)
    if document_type:
        final_queryset = final_queryset.filter(document_type=document_type)

    status_filter = request.query_params.get('status', None)
    if status_filter:
        final_queryset = final_queryset.filter(status=status_filter)

    access_level = request.query_params.get('access_level', None)
    if access_level:
        final_queryset = final_queryset.filter(access_level=access_level)

    # Paginate results
    page_size = min(int(request.query_params.get('page_size', 20)), 100)
    page = int(request.query_params.get('page', 1))
    start = (page - 1) * page_size
    end = start + page_size

    paginated_queryset = final_queryset[start:end]

    serializer = ProcurementDocumentSerializer(paginated_queryset, many=True, context={'request': request})

    return Response({
        'query': query,
        'total_count': final_queryset.count(),
        'page': page,
        'page_size': page_size,
        'results': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, HasPermission('planning.view')])
def document_stats(request):
    """
    Get document statistics.
    """
    if not getattr(request.user, 'user_role', None):
        return Response(
            {'error': 'User must have a role to view document statistics.'},
            status=status.HTTP_403_FORBIDDEN
        )

    user = request.user
    
    # Base queryset with access control
    queryset = get_queryset_for_user(user, ProcurementDocument.objects.all(), action='view')

    # Optional filtering by procurement plan
    procurement_plan_id = request.query_params.get('procurement_plan', None)
    if procurement_plan_id:
        queryset = queryset.filter(procurement_plan_id=procurement_plan_id)

    # Filter by access permissions
    accessible_docs = []
    for doc in queryset:
        if doc.can_access(user):
            accessible_docs.append(doc.pk)

    final_queryset = queryset.filter(pk__in=accessible_docs)

    # Calculate statistics
    total_documents = final_queryset.count()
    document_types = final_queryset.values('document_type').annotate(count=Count('document_type'))
    document_statuses = final_queryset.values('status').annotate(count=Count('status'))
    access_levels = final_queryset.values('access_level').annotate(count=Count('access_level'))

    # Current versions only
    current_versions = final_queryset.filter(is_current_version=True).count()

    # Recent uploads (last 30 days)
    recent_uploads = final_queryset.filter(
        uploaded_at__gte=timezone.now() - timezone.timedelta(days=30)
    ).count()

    return Response({
        'total_documents': total_documents,
        'current_versions': current_versions,
        'recent_uploads': recent_uploads,
        'document_types': list(document_types),
        'document_statuses': list(document_statuses),
        'access_levels': list(access_levels),
    })


def get_client_ip(request):
    """Helper function to get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
