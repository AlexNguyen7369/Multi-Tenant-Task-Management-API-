from rest_framework.permissions import BasePermission

from .models import Membership


class IsWorkspaceMember(BasePermission):
    def has_permission(self, request, view):
        # TODO: check Membership.objects.filter(user=request.user, workspace=<resolved ws>).exists()
        raise NotImplementedError


class IsWorkspaceAdmin(BasePermission):
    def has_permission(self, request, view):
        # TODO: same as IsWorkspaceMember, plus role in (Role.OWNER, Role.ADMIN)
        raise NotImplementedError
