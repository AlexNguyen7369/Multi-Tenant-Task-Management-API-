from rest_framework.permissions import BasePermission

from .context import get_current_workspace_id
from .models import Membership


class IsWorkspaceMember(BasePermission):
    def has_permission(self, request, view):
        workspace_id = get_current_workspace_id()
        if workspace_id is None or not request.user.is_authenticated:
            return False
        return Membership.objects.filter(
            user=request.user, workspace_id=workspace_id
        ).exists()


class IsWorkspaceAdmin(BasePermission):
    def has_permission(self, request, view):
        workspace_id = get_current_workspace_id()
        if workspace_id is None or not request.user.is_authenticated:
            return False
        return Membership.objects.filter(
            user=request.user,
            workspace_id=workspace_id,
            role__in=(Membership.Role.OWNER, Membership.Role.ADMIN),
        ).exists()
