# System Design Concepts Used In This Project

Quick reference: the general concept, in one line, and exactly where/how this
project applies it. This is an index, not the full reasoning — that lives in
`skeleton_phaese1.md`, `app_structure.md`, `database_setup.md`, and `hood.md`.
Update this file when a *new* concept enters the design, not just when an
existing one gets implemented.

---

## Authentication & Authorization

| Concept | What it means | Used here as |
|---|---|---|
| **Stateless authentication (JWT)** | The server remembers nothing between requests — a signed token itself proves who the caller is. | `djangorestframework-simplejwt`; short-lived access token + longer-lived refresh token (`config/settings/base.py`, `apps/accounts/urls.py`). Lets any server instance handle any request with no shared session store. |
| **Auth vs. authorization split** | "Who are you" and "what are you allowed to do" are different questions, checked separately. | JWT decode happens first (DRF), then two more independent checks below — never one combined check. |
| **Two-layer authorization: tenancy + role** | Split "do you belong here at all" from "what can you do here." | `IsWorkspaceMember` (tenancy) and `IsWorkspaceAdmin` (role, via `Membership.role`) — `apps/workspaces/permissions.py`. Kept separate because they fail for different reasons and are easier to debug apart. |

## Multi-tenancy

| Concept | What it means | Used here as |
|---|---|---|
| **Shared-schema multi-tenancy** | One database, one set of tables; every tenant's rows are tagged with an id rather than isolated in a separate database/schema per customer. | Every tenant-owned table carries `workspace_id` (`apps/tasks/models.py`). Cheaper to operate at this scale than DB-per-tenant. |
| **Request-scoped context** | A per-request "notepad" that unrelated layers of code can read/write without passing a value through every function call between them. | `contextvars`-based slot in `apps/workspaces/context.py` — written by middleware, read later by permissions and the ORM manager. |
| **Middleware-based resolution** | Decide something once, in one place, before every request — instead of re-deriving it inside each view. | `apps/workspaces/middleware.py` resolves which workspace a request is for, from an `X-Workspace-ID` header. |
| **Scoped default queries (custom manager)** | Override a model's default manager so "give me all rows" is automatically filtered, instead of trusting every view to add the filter by hand. | `TenantScopedManager` (`apps/workspaces/managers.py`), used by `Board`/`Task`. One missed `.filter()` in a new view can no longer leak another tenant's data. |
| **Never trust client-supplied identity fields** | A value that determines *access* must be derived server-side from already-verified context, never taken from the request body. | `workspace` is `read_only` on `Board`/`Task` serializers, set from the request-scoped context instead — closed after testing found it was spoofable. |

## Data Layer

| Concept | What it means | Used here as |
|---|---|---|
| **UUID primary keys** | Non-guessable, non-sequential ids instead of auto-incrementing integers. | `apps/core/models.py`'s `BaseModel`, inherited by every model. Avoids leaking row counts and cross-tenant id guessing. |
| **Explicit join model over bare many-to-many** | When a relationship itself carries data, model it as its own table, not a plain M2M field. | `Membership` (user ↔ workspace, carries `role`) — `apps/workspaces/models.py`. |
| **State machine over free-text status** | Restrict a field to a fixed set of legal transitions instead of an open string any value can be written into. | `Task.status` transition rules in `apps/tasks/state_machine.py` (defined, not yet enforced by a view — see `current_progress.md`). |
| **N+1 query problem / eager loading** | Serializing a list naively triggers one extra query per related object; joining up front avoids it. | `select_related("board", "assignee")` in `TaskViewSet.get_queryset` (`apps/tasks/views.py`). |
| **Composite indexing matched to query shape** | An index only helps if it matches the actual filter + sort a query uses. | `(workspace_id, created_at)` index on `Board`/`Task` — matches "filter by workspace, sort by created_at" exactly. |
| **Cursor-based pagination** | Page by "rows after this point" (index seek) instead of "skip N rows" (scan-and-discard), so fetch time doesn't degrade as data grows. | `WorkspaceCursorPagination` (`apps/core/pagination.py`). |

## API & Code Structure

| Concept | What it means | Used here as |
|---|---|---|
| **Layered, one-way dependency architecture** | Each module may depend on modules "below" it, never the reverse — prevents circular imports and "everything depends on everything." | `core ← accounts ← workspaces ← tasks` (`app_structure.md`). |
| **Serializer as a validation/shaping boundary** | One dedicated layer that both validates incoming JSON and shapes outgoing JSON, kept separate from view logic. | `*/serializers.py` in every app. |
| **Single source of truth for a cross-cutting rule** | A rule that applies everywhere (like tenant filtering) should live in exactly one place, not be repeated per call site. | The tenancy filter lives once, in the manager — not copy-pasted into every view's queryset. |

## Concurrency & Background Work

| Concept | What it means | Used here as |
|---|---|---|
| **Deferred work via a task queue** | Anything not needed for the immediate response runs asynchronously, so a slow dependency never adds latency to the API. | Celery + Redis configured (`config/celery.py`) — not yet wired to a request path. |
| **Transactional commit hooks** | Enqueue a background job only after its data is durably committed, not the instant it's written in-process. | `transaction.on_commit(...)` pattern documented in `hood.md`; not yet built. |

## Deferred (Phase 2) — designed for, not built

| Concept | Why deferred |
|---|---|
| Connection pooling (PgBouncer) | Not a bottleneck until app servers exhaust Postgres's connection limit |
| Read replicas | Needs replication-lag handling — real complexity, only worth it under real load |
| Caching (Redis) | Premature caching risks stale-data bugs before there's a proven performance problem |
| Table partitioning | Hard to undo cleanly — a much-later-scale concern |
| Row-Level Security (RLS) | Real operational cost; the contextvar/manager layer is sufficient at this scale |
| Horizontal scaling behind a load balancer | Already unblocked by choosing JWT — just not needed yet |

Full reasoning for each: `skeleton_phaese1.md` §8.
