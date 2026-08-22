from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .models import Membership, Workspace
from .permissions import IsWorkspaceAdmin
from .serializers import AddMemberSerializer, MembershipSerializer, WorkspaceSerializer

User = get_user_model()


class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceSerializer

    def get_permissions(self):
        # Any member may view a workspace — get_queryset below already
        # scopes list/retrieve to the requester's own memberships, so a
        # non-member never even sees it to try. Renaming/deleting the
        # workspace itself, and managing who belongs to it, are owner/admin
        # only — IsWorkspaceAdmin checks that against the real object named
        # in the URL (see permissions.py for why).
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsWorkspaceAdmin()]
        return [permissions.IsAuthenticated()]

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

    def _require_admin(self, request, workspace):
        # Manual check rather than a permission_class on the whole action:
        # `members` (GET) is open to any member, only its POST branch (and
        # member_detail entirely) needs the admin gate. Reuses the same
        # object-level check update/destroy go through above.
        if not IsWorkspaceAdmin().has_object_permission(request, self, workspace):
            raise PermissionDenied("Only workspace owners/admins can manage members.")

    @staticmethod
    def _guard_last_owner(workspace, membership, *, new_role=None):
        # Removing or demoting a workspace's only owner would strand it with
        # no one able to manage membership at all — refuse rather than let
        # that happen silently.
        is_demotion_or_removal = new_role is None or new_role != Membership.Role.OWNER
        if (
            membership.role == Membership.Role.OWNER
            and is_demotion_or_removal
            and workspace.memberships.filter(role=Membership.Role.OWNER).count() == 1
        ):
            raise ValidationError("Can't remove or demote the workspace's only owner.")

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        """GET: list this workspace's members (any member). POST: add an
        existing user by username (owner/admin only)."""
        workspace = self.get_object()

        if request.method == "POST":
            self._require_admin(request, workspace)
            serializer = AddMemberSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            username = serializer.validated_data["username"]
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise ValidationError({"username": "No user with that username."})
            if Membership.objects.filter(user=user, workspace=workspace).exists():
                raise ValidationError({"username": "Already a member of this workspace."})
            membership = Membership.objects.create(
                user=user, workspace=workspace, role=serializer.validated_data["role"]
            )
            return Response(MembershipSerializer(membership).data, status=201)

        memberships = workspace.memberships.select_related("user")
        return Response(MembershipSerializer(memberships, many=True).data)

    @action(detail=True, methods=["patch", "delete"], url_path=r"members/(?P<user_id>[^/.]+)")
    def member_detail(self, request, pk=None, user_id=None):
        """PATCH: change a member's role. DELETE: remove a member. Both
        owner/admin only."""
        workspace = self.get_object()
        self._require_admin(request, workspace)
        membership = get_object_or_404(Membership, workspace=workspace, user_id=user_id)

        if request.method == "DELETE":
            self._guard_last_owner(workspace, membership)
            membership.delete()
            return Response(status=204)

        self._guard_last_owner(workspace, membership, new_role=request.data.get("role"))
        serializer = MembershipSerializer(membership, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
