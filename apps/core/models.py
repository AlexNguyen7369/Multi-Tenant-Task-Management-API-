import uuid

from django.db import models


class BaseModel(models.Model):
    """
    Abstract base every domain model inherits from.

    UUID primary keys instead of auto-incrementing integers: integer PKs leak
    information (e.g. "task #4102" hints at total row count) and are
    guessable/enumerable across tenants — a real concern in a multi-tenant
    API. See notes/skeleton_phaese1.md section 2 for the full reasoning.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
