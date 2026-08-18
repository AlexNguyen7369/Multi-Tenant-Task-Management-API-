from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.workspaces.managers import TenantScopedManager
from apps.workspaces.models import Workspace


class Board(BaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="boards")
    name = models.CharField(max_length=255)

    objects = TenantScopedManager()

    class Meta:
        indexes = [models.Index(fields=["workspace", "created_at"])]


class Task(BaseModel):
    class Status(models.TextChoices):
        TODO = "todo", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        REVIEW = "review", "Review"
        DONE = "done", "Done"

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="tasks")
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )

    objects = TenantScopedManager()

    class Meta:
        indexes = [models.Index(fields=["workspace", "created_at"])]
