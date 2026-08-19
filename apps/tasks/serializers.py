from rest_framework import serializers

from .models import Board, Task


class BoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Board
        fields = ("id", "workspace", "name", "created_at", "updated_at")
        # workspace is set server-side from the tenancy context (see
        # BoardViewSet.perform_create), never taken from the request body —
        # otherwise a member of one workspace could target another one by id.
        read_only_fields = ("workspace",)


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            "id",
            "workspace",
            "board",
            "title",
            "status",
            "assignee",
            "created_at",
            "updated_at",
        )
        # Same reasoning as BoardSerializer — see TaskViewSet.perform_create.
        read_only_fields = ("workspace",)
