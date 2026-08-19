"""
Resolves the requesting user's active workspace once per request and stores
it in the contextvar from context.py, so every tenant-scoped model's default
manager can filter to it automatically. See notes/skeleton_phaese1.md
section 3 for the full reasoning.
"""

from uuid import UUID

from .context import clear_current_workspace_id, set_current_workspace_id


class WorkspaceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        workspace_id = self._resolve_workspace_id(request)
        set_current_workspace_id(workspace_id)
        try:
            response = self.get_response(request)
        finally:
            # Always clear, even on an exception, so a failed request can
            # never leak its workspace into whatever request reuses this
            # worker/thread next.
            clear_current_workspace_id()
        return response

    def _resolve_workspace_id(self, request):
        # Deliberately does NOT check membership here. This is Django
        # middleware, so it runs before DRF's own authentication has had a
        # chance to populate request.user from the JWT (that happens later,
        # inside APIView.dispatch) — request.user at this point is still
        # AnonymousUser. So this method only resolves *which* workspace the
        # request claims to be for, via the X-Workspace-ID header; whether
        # the caller is actually allowed to see it is answered separately by
        # IsWorkspaceMember / IsWorkspaceAdmin (permissions.py), which run
        # after real authentication has happened. See
        # notes/skeleton_phaese1.md section 4 for the two-layer reasoning.
        header_value = request.headers.get("X-Workspace-ID")
        if not header_value:
            return None
        try:
            return UUID(header_value)
        except (ValueError, AttributeError, TypeError):
            return None
