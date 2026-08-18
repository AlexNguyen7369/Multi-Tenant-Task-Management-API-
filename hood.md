# Under the Hood — One Request, Every Layer

This traces a single API call through **every layer** it passes through, the
same way you'd trace "typing a URL into a browser" through DNS → TCP → TLS →
HTTP. Those four still happen here — an API call is still an HTTP request over
the internet — but this project adds a whole application-layer stack on top
that a static website doesn't have: middleware, JWT decoding, tenancy
resolution, the ORM, the database, and a background job queue.

Two concrete requests are traced so both the "read" and "write" paths are
covered:

- **Request A (read):** `GET /api/workspaces/<ws_id>/boards/<board_id>/tasks/?cursor=...`
- **Request B (write):** `POST /api/workspaces/<ws_id>/boards/<board_id>/tasks/`

Everything below assumes the Phase 1 design in `skeleton_phaese1.md`.

---

## Quick map

| # | Layer | Same as any website? |
|---|---|---|
| 1 | DNS resolution | Yes — identical to any web request |
| 2 | TCP handshake | Yes — identical |
| 3 | TLS handshake | Yes — identical, but **non-negotiable here** (see below) |
| 4 | HTTP request formed | Yes, but with project-specific headers (JWT) |
| 5 | Reverse proxy / load balancer | Same concept, project-specific role |
| 6 | WSGI server (Gunicorn) | Backend-specific, not project-specific |
| 7 | Django middleware chain | **Project-specific** |
| 8 | URL routing | **Project-specific** |
| 9 | DRF authentication (JWT decode) | **Project-specific** |
| 10 | DRF permissions (tenancy + role) | **Project-specific** |
| 11 | View → `get_queryset()` | **Project-specific** |
| 12 | Serializer (validate / render) | **Project-specific** |
| 13 | ORM → SQL translation | **Project-specific** |
| 14 | Database execution | **Project-specific** |
| 15 | Background job hand-off (writes only) | **Project-specific** |
| 16 | Response trip back down | Mirrors 5–7 in reverse |
| 17 | Client receives response | Yes — identical |

---

## 1. DNS resolution

The client (browser, mobile app, `curl`, Postman) resolves `api.yourapp.com`
to an IP address — the OS checks its local cache, then a resolver, then
authoritative DNS servers if needed. Nothing about this is different from any
other website. Included for completeness since it's the first thing that
happens.

## 2. TCP handshake

Client and server exchange SYN → SYN-ACK → ACK to establish a TCP connection
to the server's IP on port 443. Standard, not project-specific.

## 3. TLS handshake

Client and server negotiate a TLS session (certificate presented, key
exchange, symmetric session key derived). **This step matters more here than
on a typical static site**, for one specific reason: the JWT that authenticates
every request after login is a **bearer token** — whoever holds it *is* the
user, no further proof required. If TLS weren't in place, the JWT would be
readable by anyone on the network path, and stealing it means full account
takeover with no password needed. HTTPS isn't a "nice to have" for this API —
the entire auth model depends on the transport being encrypted.

## 4. HTTP request is formed

The client builds the actual request:

```
GET /api/workspaces/7f2e.../boards/9a1c.../tasks/?cursor=eyJjcmVh... HTTP/1.1
Host: api.yourapp.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Accept: application/json
```

For Request B, add `Content-Type: application/json` and a JSON body. The
`Authorization` header carrying the JWT is the one project-specific thing
here — everything else is standard HTTP.

## 5. Reverse proxy / load balancer

The request lands on a reverse proxy (e.g. Nginx) or a cloud load balancer
first, not directly on the Django app. Its job:

- Terminates TLS (or passes it through, depending on setup).
- Picks **which** app server instance handles the request, if more than one
  is running.

This is where the JWT decision from `skeleton_phaese1.md` §1 actually pays
off: because no server holds session state, the load balancer can route this
request to *any* running instance — there's no "sticky session" requirement
tying a user to one specific server. A session-based auth system would need
the load balancer to remember which server a given user's session lives on,
or share session state across servers. JWT sidesteps that entirely.

## 6. WSGI server (Gunicorn)

The chosen app server instance runs Gunicorn (or similar), which keeps a pool
of worker processes/threads. Gunicorn hands the raw HTTP request to a free
worker and translates it into the WSGI `environ` dict — the standardized
format Django (and any WSGI-compatible Python web framework) expects. Not
project-specific — this is how virtually all production Django apps are
served — but it's the boundary where "the web" ends and "your code" begins.

## 7. Django middleware chain (inbound)

Django runs a stack of middleware classes, in order, before the request
reaches any view. Order matters — each middleware wraps the next. Relevant
ones here, in the order they'd run:

1. `SecurityMiddleware` — HTTPS enforcement, security headers.
2. `CorsMiddleware` (if the API is called from browser JS on a different
   origin) — must run early, before responses are generated, so CORS headers
   land on every response including errors.
3. **The custom tenancy middleware from the skeleton doc.**

**A real gotcha worth flagging now, before it's built:** Django's middleware
`process_request` phase runs *before* the URL is resolved to a view. If the
workspace ID comes from the URL path (`/workspaces/<ws_id>/...`), plain
middleware can't read it yet at that point — the URL hasn't been parsed into
its pieces. Django provides a specific hook for this, `process_view`, which
runs *after* URL resolution but *before* the view executes, and it receives
the resolved URL kwargs directly. This is the hook the tenancy middleware
needs to use, not `process_request`. Getting this wrong is exactly the kind
of subtle bug the whole contextvar design is trying to prevent elsewhere —
worth being deliberate about here specifically.

## 8. URL routing

Django's URL resolver (and DRF's router on top of it, since this project uses
ViewSets) matches the path to a specific view class and action —
`TaskViewSet.list` for Request A, `TaskViewSet.create` for Request B. This
resolution is what makes the URL kwargs (`ws_id`, `board_id`) available to
`process_view` in step 7.

## 9. DRF authentication — JWT decode

This is a separate stage from Django's middleware, and it's a common point of
confusion, so it's worth being precise: **JWT verification happens inside
DRF, not Django middleware.** When the view is about to run, DRF calls
`request.user`, which lazily triggers the configured authentication class
(e.g. `SimpleJWT`'s `JWTAuthentication`). That class:

1. Reads the `Authorization: Bearer <token>` header.
2. Verifies the token's signature against the server's secret/public key —
   this proves the token wasn't tampered with.
3. Checks the `exp` (expiry) claim — a token past its lifetime is rejected
   even if the signature is valid.
4. Looks up the user the token claims to represent, attaches it to
   `request.user`.

If any of these fail, DRF short-circuits with a 401 before the view body ever
runs — the request never reaches the database at all.

## 10. DRF permissions — tenancy + role, the two-layer check from the skeleton

Once `request.user` is known, permission classes run **two separate checks**
(deliberately kept separate, per `skeleton_phaese1.md` §4):

1. **Tenancy check** — does this user have a `Membership` row for
   `ws_id` at all? If not: 403, request stops here.
2. **Role check** — does their `Membership.role` allow this specific action?
   (e.g. Request B, creating a task, might require at least `member`; deleting
   a board might require `admin`/`owner`.)

Only after both pass does execution reach the view body.

## 11. View → `get_queryset()`

This is where the contextvar set back in step 7 actually gets used. The
view's `get_queryset()` calls `Task.objects.filter(board_id=board_id)` (or
similar) — and because `Task`'s manager is the custom one from the skeleton
doc, that call is **already implicitly filtered to `workspace=current_workspace`**
before any explicit filter is applied. This is the payoff of the whole
design: even if a future developer writes a careless queryset here, the
manager still won't leak another workspace's rows.

## 12. Serializer

- **Request A (read):** the queryset (already `select_related`'d — see step
  13) is handed to the serializer, which walks each `Task` instance and
  produces a JSON-shaped dict: id, title, status, assignee, timestamps.
- **Request B (write):** the incoming JSON body is validated *against* the
  serializer's fields first. This is also where the **task state-machine
  check** lives — if the request tries to set `status` directly to `done`
  from nothing, or tries an illegal transition, validation fails here with a
  400, before anything touches the database.

## 13. ORM → SQL translation

Django QuerySets are lazy — nothing hits the database until the queryset is
actually iterated (which the serializer does in step 12). At that point:

- `.select_related(...)` becomes a SQL `JOIN` across the related tables in a
  **single query**, instead of DRF triggering a separate query per related
  object while serializing (the N+1 problem the skeleton doc calls out).
- Cursor pagination becomes something like:
  ```sql
  SELECT * FROM task
  WHERE workspace_id = :ws_id AND created_at < :cursor
  ORDER BY created_at DESC
  LIMIT 21;   -- 21, not 20: the extra row tells the API whether a "next page" exists
  ```
- The `WHERE workspace_id = ... AND ... ORDER BY created_at` shape is exactly
  what the `(workspace_id, created_at)` composite index from the skeleton doc
  exists to serve — without it, Postgres would scan every row for the
  workspace and sort them in memory instead of walking the index in order.

## 14. Database execution

- The query goes out over a **database connection** — in Phase 1, one of
  Django's normal persistent connections (via `CONN_MAX_AGE`); in Phase 2,
  through PgBouncer once connection volume justifies pooling.
- Postgres's query planner picks an **index scan** on `(workspace_id,
  created_at)` rather than a sequential scan, because the index matches the
  query's filter and sort exactly.
- **For Request B specifically**, the `INSERT` runs inside a database
  transaction. If anything else in the same request needs to happen
  atomically with the insert (e.g., updating a board's `updated_at`), it's
  wrapped in the same transaction — either everything commits, or none of it
  does.

## 15. Background job hand-off (Request B only)

If creating a task should trigger a notification, the request does **not**
send that notification inline — per the skeleton doc's background jobs
section, it enqueues a Celery task instead. The detail that matters for bug
rate:

```python
transaction.on_commit(lambda: send_task_notification.delay(task.id))
```

`on_commit` — not calling `.delay()` directly — matters because Celery's
Redis broker can hand the job to a worker *faster than the database commit
finishes*. Without `on_commit`, a fast worker could try to read a `Task` row
that the transaction hasn't actually committed yet, and fail. `on_commit`
guarantees the job is only enqueued once the transaction is durably saved.
The Celery worker itself is a **separate process**, running independently of
the request/response cycle — the HTTP response does not wait for it.

## 16. Response travels back down

The serialized JSON becomes the HTTP response body, content-negotiated to
`application/json` by DRF's renderer. It passes back up through the Django
middleware stack in **reverse** order (outbound phase), through Gunicorn,
through the reverse proxy, and back over the **same already-established TCP
connection and TLS session** — no new DNS lookup, no new handshake, as long
as the connection is kept alive.

## 17. Client

The client parses the JSON body and updates whatever it needed to (a UI list,
a mobile app's local state, etc.). Request complete.

---

## Why this level of detail matters

Two bugs classes live specifically in the layers that don't exist on a plain
website: **step 7's `process_view`-vs-`process_request` distinction** (get it
wrong and the tenancy middleware silently never applies, because it never
sees the workspace ID) and **step 15's `on_commit`** (skip it and background
jobs occasionally race the transaction that created their own data). Both are
the kind of bug that passes every test written against a fast local database
and only shows up under real latency — worth having written down before
they're built, not after they're debugged.
