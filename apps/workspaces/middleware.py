"""
Resolves the requesting user's active workspace once per request and stores
it in the contextvar from context.py, so every tenant-scoped model's default
manager can filter to it automatically. See notes/skeleton_phaese1.md
section 3 for the full reasoning.
"""

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
        # TODO: derive from request.user + a Membership lookup, or from a
        # header/URL segment identifying which workspace this request is for.
        raise NotImplementedError
