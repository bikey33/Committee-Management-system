from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..models import DocumentCategory
from ..serializers import DocumentCategorySerializer
from users.permissions import HasPermission


class DocumentCategoryListCreateView(generics.ListCreateAPIView):
    """List all active document categories or create a new one."""
    serializer_class = DocumentCategorySerializer
    permission_classes = [IsAuthenticated, HasPermission('planning.view')]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), HasPermission('planning.manage')()]
        return [IsAuthenticated(), HasPermission('planning.view')()]

    def get_queryset(self):
        return DocumentCategory.objects.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save()


class DocumentCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or soft-delete a document category."""
    serializer_class = DocumentCategorySerializer
    permission_classes = [IsAuthenticated, HasPermission('planning.view')]
    queryset = DocumentCategory.objects.all()

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), HasPermission('planning.manage')()]
        return [IsAuthenticated(), HasPermission('planning.view')()]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()
