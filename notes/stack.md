# Stack

## Phase 1

| Category | Technology |
|---|---|
| Backend framework | Django |
| API layer | Django REST Framework (DRF) |
| Database | PostgreSQL |
| Primary keys | UUID |
| Authentication | JWT (`djangorestframework-simplejwt`) |
| Tenancy isolation | Custom Django middleware + `contextvars` + custom model managers |
| Authorization | DRF permission classes (role-based, via `Membership` model) |
| Pagination | Cursor-based (DRF) |
| Background jobs | Celery |
| Message broker | Redis |
| App server (WSGI) | Gunicorn |
| Reverse proxy / load balancer | Nginx |
| Transport security | TLS / HTTPS |
| Config/secrets | `.env`-based settings |

## Phase 2 (deferred)

| Category | Technology |
|---|---|
| Connection pooling | PgBouncer |
| Caching | Redis (cache layer) |
| Read scaling | PostgreSQL read replicas |
| Write scaling | Table partitioning |
| Defense-in-depth tenancy | PostgreSQL Row-Level Security (RLS) |

---

## Running / testing locally

Assumes Postgres 16 is installed and running (Homebrew: `brew services start postgresql@16`)
and `.env` exists (`cp .env.example .env` and fill in real values — never commit `.env`).

```bash
source .venv/bin/activate
pip install -r requirements/dev.txt   # first time only, or after requirements change
python manage.py migrate              # first time only, or after new migrations
python manage.py runserver
```

Then either:

- **Manual test console** — open `http://127.0.0.1:8000/testui/` in a browser.
  Same-origin page (`templates/testui.html`), no CORS setup needed. Walks
  through register → login → create workspace → create board → create task,
  with a live request/response log and a suggested test script for proving
  tenancy isolation by eye (create two workspaces, flip the active one, watch
  the board/task lists change).
- **Direct API calls** — everything under `/api/accounts/`, `/api/workspaces/`,
  `/api/boards/`, `/api/tasks/` (see `config/urls.py`). Tenant-scoped
  endpoints (`boards`, `tasks`) require an `X-Workspace-ID: <workspace id>`
  header in addition to the JWT `Authorization: Bearer <access token>` header.
- **Automated tests** (once written — none exist yet, see
  `notes/current_progress.md`) — `python manage.py test`.

Celery/Redis are part of the Phase 1 stack but nothing depends on them being
up yet for manual API testing — no background job is wired to a request path
so far.
