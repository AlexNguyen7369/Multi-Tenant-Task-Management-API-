"""
The contextvar tenancy pivots on: which workspace is the current request
scoped to. Set by WorkspaceMiddleware at the start of every request, read by
TenantScopedManager on every query, cleared at the end of every request so
nothing leaks between requests.
"""
from contextvars import ContextVar
from typing import Optional
from uuid import UUID

_current_workspace_id: ContextVar[Optional[UUID]] = ContextVar(
    "current_workspace_id", default=None
)


def set_current_workspace_id(workspace_id: Optional[UUID]) -> None:
    _current_workspace_id.set(workspace_id)


def get_current_workspace_id() -> Optional[UUID]:
    return _current_workspace_id.get()


def clear_current_workspace_id() -> None:
    _current_workspace_id.set(None)
