from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.workspaces.context import get_current_workspace_id
from apps.workspaces.permissions import IsWorkspaceMember

from .models import Board, Task
from .serializers import BoardSerializer, TaskSerializer
from .state_machine import get_allowed_transitions


class BoardViewSet(viewsets.ModelViewSet):
    serializer_class = BoardSerializer
    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]

    def get_queryset(self):
        # Must be a method, not a `queryset = Board.objects.all()` class
        # attribute: a class attribute is evaluated once at import time,
        # before any request has set the workspace contextvar, so
        # TenantScopedManager would bake in workspace_id=None (i.e. `.none()`)
        # forever. Calling .all() fresh per-request reads the contextvar at
        # the right time. See notes/skeleton_phaese1.md section 3.
        return Board.objects.all()

    def perform_create(self, serializer):
        # `workspace` is read-only on the serializer specifically so this is
        # the only place it can be set — otherwise a member of workspace A
        # could write a board into workspace B just by putting a different id
        # in the request body, regardless of which workspace they authenticated
        # against (the X-Workspace-ID header IsWorkspaceMember just checked).
        serializer.save(workspace_id=get_current_workspace_id())


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]

    def get_queryset(self):
        # select_related avoids an N+1 query per task on board/assignee once
        # nested serializers are added — see notes/skeleton_phaese1.md section 5.
        return Task.objects.select_related("board", "assignee")

    def perform_create(self, serializer):
        # Same reasoning as BoardViewSet.perform_create — workspace is
        # server-derived from the tenancy context, never client-supplied.
        serializer.save(workspace_id=get_current_workspace_id())


