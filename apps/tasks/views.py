from rest_framework import viewsets

from .models import Board, Task
from .serializers import BoardSerializer, TaskSerializer


class BoardViewSet(viewsets.ModelViewSet):
    serializer_class = BoardSerializer
    queryset = Board.objects.all()  # already workspace-scoped via TenantScopedManager


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        # select_related avoids an N+1 query per task on board/assignee once
        # nested serializers are added — see notes/skeleton_phaese1.md section 5.
        return Task.objects.select_related("board", "assignee")
