from rest_framework import serializers

from .models import Board, Task


class BoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Board
        fields = ("id", "workspace", "name", "created_at", "updated_at")


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
