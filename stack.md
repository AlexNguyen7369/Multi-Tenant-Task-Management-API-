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
