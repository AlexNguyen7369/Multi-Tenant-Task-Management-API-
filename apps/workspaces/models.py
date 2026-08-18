from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Workspace(BaseModel):
    name = models.CharField(max_length=255)


class Membership(BaseModel):
    """
    Explicit join model between User and Workspace, not a bare
    ManyToManyField — a membership carries a role, and a plain M2M can't
    attach extra attributes to the relationship. See
    notes/skeleton_phaese1.md section 2.
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)

    class Meta:
        unique_together = ("user", "workspace")
