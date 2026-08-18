from rest_framework.pagination import CursorPagination


class WorkspaceCursorPagination(CursorPagination):
    """
    Cursor pagination, not offset/limit: OFFSET forces the database to scan
    and discard every prior row before returning a page, which gets slower as
    a workspace's data grows. A cursor seeks via an index instead, so
    page-fetch time stays flat regardless of table size or page depth. See
    notes/skeleton_phaese1.md section 5.

    Pairs with the (workspace_id, created_at) composite index every
    tenant-scoped model should carry.
    """

    page_size = 20
    ordering = "-created_at"
