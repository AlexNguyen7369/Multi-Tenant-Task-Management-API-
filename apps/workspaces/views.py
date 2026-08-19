from rest_framework import viewsets

from .models import Membership, Workspace
from .serializers import WorkspaceSerializer


class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceSerializer

    def get_queryset(self):
        # Workspace itself isn't tenant-scoped by TenantScopedManager (it IS
        # the tenant) — scope it to the requesting user's memberships instead.
        return Workspace.objects.filter(memberships__user=self.request.user).distinct()

    def perform_create(self, serializer):
        # Creating a workspace with no membership would immediately lock its
        # creator out of it — get_queryset above and IsWorkspaceMember both
        # gate on Membership, so the creator must become a member (as owner)
        # in the same operation.
        workspace = serializer.save()
        Membership.objects.create(
            user=self.request.user,
            workspace=workspace,
            role=Membership.Role.OWNER,
        )
