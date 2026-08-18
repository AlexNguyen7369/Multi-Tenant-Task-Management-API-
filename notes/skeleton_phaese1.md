# Multi-Tenant Task Management API — Phase 1 Skeleton

This document is the architecture skeleton for Phase 1. Nothing here is built yet —
this is the plan, and the *reasoning* behind each decision, written down before
writing code so the design can be reviewed and questioned first.

Scale target for Phase 1: **tens to hundreds of workspaces.** Phase 2 (documented
at the bottom) covers what changes if this grows to tens of thousands of users.

---

## 1. General Overview

**Stack:** Django + Django REST Framework + PostgreSQL.

**Data hierarchy:** `Workspace → Board → Task`, with a `Membership` model
connecting `User ↔ Workspace` (many-to-many with a role attached).

**Tenancy model:** single shared database, every tenant-owned row carries a
`workspace_id`. Isolation is enforced by application code (Phase 1), not by
separate databases or schemas per tenant.

*Why shared DB instead of DB-per-tenant or schema-per-tenant?* At tens-to-hundreds
of workspaces, a separate database per tenant is operational overhead (migrations
have to run N times, connection pooling gets harder, cross-tenant admin queries
become painful) for a benefit you don't need yet. Shared DB + a `workspace_id`
column is the standard SaaS starting point and is what lets you scale to
thousands of tenants before this decision needs revisiting.

**Auth:** JWT (JSON Web Tokens).

*Why JWT over Django sessions?* Sessions require the server to remember who's
logged in (session store, usually in the DB or a cache), which means every
request has to be routed to a server that can see that state, or the state has
to be shared across servers. JWTs are self-contained — the token itself proves
who the user is — so any server can validate any request with no shared state.
This is what makes it trivial to run multiple copies of the API behind a load
balancer later (see Phase 2). The tradeoff: revoking a JWT before it expires is
harder than killing a session, so token lifetime and refresh strategy need to be
deliberate (see §4).

---

## 2. Data Model

```
User
 └── Membership (role: owner | admin | member)  ──┐
                                                     ├── Workspace
                                                     │     └── Board
                                                     │           └── Task (status: todo → in_progress → review → done)
```

**Primary keys: UUIDs, not auto-incrementing integers.**

*Why?* Two reasons specific to a multi-tenant system:
1. Integer PKs leak information (e.g., "task #4102" tells a competitor roughly
   how many tasks exist system-wide) and make IDs guessable/enumerable across
   tenants — a security smell in a multi-tenant API.
2. UUIDs can be generated client-side or in application code before an insert,
   which matters once you have background jobs or distributed writes (Phase 2)
   — you're not dependent on the DB handing back the next integer.

The cost is a slightly larger index and marginally slower joins than integers —
acceptable at this scale, and standard practice for multi-tenant SaaS.

**`Membership` as an explicit join model, not a plain `ManyToManyField`.**

*Why?* A user's relationship to a workspace isn't just "is a member" — it carries
a `role` (owner/admin/member) that determines what they're allowed to do. A bare
`ManyToManyField` can't carry that extra attribute. Making `Membership` its own
model also gives a natural home for future fields (e.g., `invited_by`,
`joined_at`) without a schema migration that changes the shape of the relationship.

**Task status as a state machine (`todo → in_progress → review → done`), not a
free-text or arbitrary-choice field.**

*Why?* An open `CharField` lets any status be set from any other status via a
bug or a bad API call (e.g., `done → todo` skipping review, or a typo'd status
string). Modeling it as a state machine means transitions are validated —
only certain "next states" are legal from a given state — which is what
"low bug rate" concretely means for this piece: invalid states become
impossible to represent, not just discouraged by convention.

---

## 3. Tenancy Isolation — the middleware approach

**Mechanism:** a Django middleware resolves the requesting user's active
workspace (from the JWT / request) at the start of every request, and stores it
in a `contextvar` (a thread-local-like slot Python provides for exactly this
purpose). Every tenant-scoped model uses a **custom manager** that reads this
contextvar and automatically filters every query to that workspace — so
`Task.objects.all()` *is* `Task.objects.filter(workspace=current_workspace)`,
with no view author needing to remember to add the filter.

*Why this instead of filtering manually in every view?* Manual per-view
filtering means the isolation guarantee lives in N different places (one per
view), and a single missed `.filter()` in a new view is a cross-tenant data
leak. Centralizing the filter in the manager means the guarantee lives in
**one place** — the default query behavior itself — which directly matches the
goal of eliminating per-view filtering risk.

*Why not Postgres Row-Level Security (RLS) instead?* RLS enforces isolation at
the database layer, which is a stronger guarantee (even a buggy raw SQL query
can't leak data). It's the right answer once the data is sensitive enough or
the team large enough that a defense-in-depth guarantee justifies the added
operational complexity: managing a per-connection session variable, and making
migrations/admin scripts deliberately bypass it. That complexity isn't worth
paying for at this scale. **RLS is listed here as a known, deliberate Phase 2+
option, not a rejection** — the contextvar approach doesn't preclude adding RLS
underneath it later as a second layer.

*Known limitation to be aware of, not solved in Phase 1:* contextvars are safe
as long as Django runs in its normal one-thread-per-request mode (the default).
If the project ever moves to fully async views or shares threads across
requests in an unusual way, the contextvar has to be explicitly reset at the
start/end of each request to avoid leaking state between requests. Phase 1's
middleware will set and clear it explicitly for this reason, even though it's
not strictly required at this scale — cheap insurance.

---

## 4. Auth & Authorization

- **Authentication:** JWT, issued on login, containing the user's identity.
  Short-lived access token + longer-lived refresh token (standard pattern) —
  short access token life limits the damage if a token is stolen, refresh token
  lets the user avoid re-logging-in constantly.
- **Authorization:** two layers.
  1. *Tenancy* — "can you see this workspace's data at all?" — enforced by the
     middleware/manager described in §3.
  2. *Role* — "what are you allowed to do within a workspace you belong to?" —
     enforced by DRF permission classes checking the requesting user's
     `Membership.role` for the workspace in question (e.g., only `owner`/`admin`
     can delete a board).

  These are kept as two separate checks rather than one combined check, because
  they answer different questions and fail differently: a tenancy failure means
  "this data isn't yours," a role failure means "this is your workspace but not
  your permission level." Keeping them separate makes each one easier to test
  in isolation and easier to reason about when debugging an access-denied bug.

---

## 5. Query Performance

- **`select_related` across the Workspace → Board → Task → (User via
  assignee/creator) chain** to avoid N+1 queries on list/detail endpoints —
  identified as a risk specifically because nested serializers naturally
  trigger a query per related object unless the queryset explicitly joins them
  upfront.
- **Cursor-based pagination on `created_at`**, not offset/limit pagination.

  *Why cursor over offset?* `OFFSET 10000 LIMIT 20` forces the database to scan
  and discard 10,000 rows before returning the page — this gets linearly slower
  as the table grows and as users page deeper. Cursor pagination ("give me the
  20 rows after this specific point") uses an index seek instead of a scan, so
  page-fetch time stays flat regardless of table size or page depth. This is a
  scalability decision baked in from Phase 1 rather than retrofitted later,
  because switching pagination strategy after clients depend on offset-based
  page numbers is a breaking API change.

- **Composite index on `(workspace_id, created_at)`** on every tenant-scoped
  table. *Why now, not deferred to Phase 2?* Every query in the system is
  already filtered by `workspace_id` (via §3) and ordered by `created_at` (via
  cursor pagination) — this index is what makes both of those fast. Without it,
  every list endpoint does a full table scan filtered down after the fact,
  which is the single most common cause of "worked fine with test data, fell
  over with real data."

---

## 6. Background Jobs

Anything not required to compute the immediate HTTP response — email
notifications, audit log writes, future digest/report generation — goes through
a task queue (Celery + Redis as the broker) instead of running inline during
the request.

*Why build this in Phase 1 even at small scale?* Two reasons:
1. It keeps request/response time flat as load grows — a slow email provider
   or a slow report calculation never adds latency to the API response.
2. Retrofitting "move this into a background job" after other code has grown
   to assume synchronous behavior (e.g., "the notification was already sent by
   the time this function returns") is a real refactor. Building it in from the
   start avoids that.

---

## 7. Phase 1 — What Actually Gets Built

In build order (each step depends on the previous):

1. **Project scaffold** — Django project, DRF installed, PostgreSQL connection
   configured, `.env`-based settings (never hardcode secrets/DB creds).
2. **Core models** — `User` (Django's built-in, extended if needed), `Workspace`,
   `Membership` (with `role`), `Board`, `Task` (with status state machine),
   all with UUID PKs.
3. **Migrations + composite indexes** — `(workspace_id, created_at)` on `Board`
   and `Task` from the first migration, not added later.
4. **JWT auth** — login/refresh endpoints, token issuance.
5. **Tenancy middleware + custom managers** — the contextvar mechanism from §3,
   applied to `Board` and `Task`.
6. **Role-based permission classes** — the DRF layer from §4.
7. **Serializers + ViewSets** using `select_related`, wired to the cursor
   pagination class.
8. **Task state machine enforcement** — transition validation on `Task.status`.
9. **Background task queue wiring** (Celery + Redis) — even if the only job at
   first is something simple like an audit-log write, to prove the plumbing
   works before anything depends on it.
10. **Tests** — tenancy isolation tests are the highest priority (a test that
    proves Workspace A can never see Workspace B's data), then role-permission
    tests, then state-machine transition tests.

---

## 8. Phase 2 — Deferred Until Scale Demands It

Documented now so the design doesn't paint itself into a corner, **not built
in Phase 1**:

| Concern | Trigger to revisit | Why deferred |
|---|---|---|
| Connection pooling (PgBouncer) | App servers start exhausting Postgres's connection limit under concurrent load | Not a bottleneck at tens-hundreds of workspaces; adding it early is complexity with no payoff yet |
| Redis caching on read-heavy endpoints | Read query volume (not data volume) becomes the bottleneck | Premature caching risks stale-data bugs before there's a performance problem to justify it |
| Read replicas | A single Postgres instance's read throughput becomes the limit | Requires replication lag handling in application logic — real complexity, only worth it under real load |
| Table partitioning (e.g. `Task` by `workspace_id` or time) | Table size/write volume degrades query performance despite indexing | Advanced, hard to undo cleanly — a "tens of thousands of users" concern, not a "hundreds of workspaces" one |
| Postgres Row-Level Security | Data sensitivity or team size grows enough to justify defense-in-depth beyond the contextvar/manager layer | Real operational cost (session vars per connection, migration bypass) not justified by Phase 1's data/risk profile |
| Horizontal app-server scaling behind a load balancer | Single server's request throughput becomes the limit | Already unblocked by choosing JWT (§1) — just not needed yet |

---

## 9. Open Decisions Still to Confirm

- Exact JWT library (`djangorestframework-simplejwt` is the standard DRF
  choice) and access/refresh token lifetimes.
- Whether `Membership.role` is a fixed choice field (`owner`/`admin`/`member`)
  or needs to support custom roles later — fixed choices are simpler and
  sufficient for Phase 1 unless there's a known future requirement for
  custom permissions.
