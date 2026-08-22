from rest_framework.permissions import BasePermission

from .context import get_current_workspace_id
from .models import Membership, Workspace


class IsWorkspaceMember(BasePermission):
    def has_permission(self, request, view):
        workspace_id = get_current_workspace_id()
        if workspace_id is None or not request.user.is_authenticated:
            return False
        return Membership.objects.filter(
            user=request.user, workspace_id=workspace_id
        ).exists()


class IsWorkspaceAdmin(BasePermission):
    """
    Grants access only to a workspace's owner/admin members.

    Two check paths, because this permission is used two different ways:

    - View-level (has_permission), for list/create-style actions that have
      no single object yet — falls back to the X-Workspace-ID contextvar,
      same as IsWorkspaceMember. This is skipped for detail actions (an
      object is already named in the URL): trusting the header there would
      let an admin of workspace B act on an unrelated workspace A just by
      setting the header to B while naming A in the URL.
    - Object-level (has_object_permission), for detail actions — checks the
      role against the *actual object being acted on* (a Workspace itself,
      or anything carrying a `workspace_id`), never the header.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        lookup_kwarg = getattr(view, "lookup_url_kwarg", None) or getattr(
            view, "lookup_field", "pk"
        )
        if view.kwargs.get(lookup_kwarg):
            # Detail route — real check happens in has_object_permission
            # against the object actually named in the URL.
            return True
        workspace_id = get_current_workspace_id()
        if workspace_id is None:
            return False
        return self._is_admin(request.user, workspace_id)

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        workspace_id = obj.id if isinstance(obj, Workspace) else getattr(obj, "workspace_id", None)
        if workspace_id is None:
            return False
        return self._is_admin(request.user, workspace_id)

    @staticmethod
    def _is_admin(user, workspace_id):
        return Membership.objects.filter(
            user=user,
            workspace_id=workspace_id,
            role__in=(Membership.Role.OWNER, Membership.Role.ADMIN),
        ).exists()
