from rest_framework import viewsets

from .models import Workspace
from .serializers import WorkspaceSerializer


class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceSerializer

    def get_queryset(self):
        # Workspace itself isn't tenant-scoped by TenantScopedManager (it IS
        # the tenant) — scope it to the requesting user's memberships instead.
        # TODO: return Workspace.objects.filter(memberships__user=self.request.user)
        raise NotImplementedError
