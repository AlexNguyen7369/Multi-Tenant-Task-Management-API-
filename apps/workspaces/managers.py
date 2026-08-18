from django.db import models

from .context import get_current_workspace_id


class TenantScopedManager(models.Manager):
    """
    Every tenant-owned model (Board, Task, ...) uses this instead of the
    default manager, so `Model.objects.all()` is automatically scoped to the
    current workspace — no view author needs to remember to add the filter
    themselves. See notes/skeleton_phaese1.md section 3.
    """

    def get_queryset(self):
        workspace_id = get_current_workspace_id()
        queryset = super().get_queryset()
        if workspace_id is None:
            return queryset.none()
        return queryset.filter(workspace_id=workspace_id)
