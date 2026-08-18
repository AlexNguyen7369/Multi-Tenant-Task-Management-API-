# Multi-Tenant Task Management API — App Structure (Phase 1)

This document sketches how the Django project is split into separate apps
(modules), and what lives inside each one. Nothing is built yet — this is the
folder-level plan, written down so the boundaries are decided before any code
is written, same spirit as `skeleton_phaese1.md`.

---

## Folder tree

```
project_root/
├── manage.py
├── .env.example
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
│
├── config/                      # the Django "project" wiring itself — not a domain app
│   ├── __init__.py
│   ├── settings/
│   │   ├── base.py               # shared settings
│   │   ├── dev.py                # local overrides
│   │   └── prod.py                # production overrides
│   ├── urls.py                    # top-level router; includes each app's urls.py
│   ├── celery.py                   # Celery app instance + config
│   ├── wsgi.py
│   └── asgi.py
│
└── apps/
    ├── core/                     # generic, shared code — depends on nothing else
    │   ├── __init__.py
    │   ├── apps.py
    │   ├── models.py               # abstract BaseModel: UUID primary key, created_at/updated_at
    │   ├── pagination.py           # shared cursor-pagination class
    │   ├── exceptions.py           # custom DRF exception handler
    │   └── tests/
    │
    ├── accounts/                 # users + login — depends on: core
    │   ├── __init__.py
    │   ├── apps.py
    │   ├── models.py               # User (extends Django's built-in user model)
    │   ├── serializers.py          # login / refresh / register serializers
    │   ├── views.py                # login, refresh, register endpoints
    │   ├── urls.py
    │   ├── migrations/
    │   └── tests/
    │
    ├── workspaces/                # tenancy itself — depends on: core, accounts
    │   ├── __init__.py
    │   ├── apps.py
    │   ├── models.py                # Workspace, Membership (role: owner/admin/member)
    │   ├── managers.py              # TenantScopedManager — the base every tenant-owned model reuses
    │   ├── context.py               # the contextvar + get/set/clear helpers
    │   ├── middleware.py            # resolves current workspace from the JWT, sets the contextvar
    │   ├── permissions.py           # role-based DRF permission classes (e.g. IsWorkspaceAdmin)
    │   ├── serializers.py
    │   ├── views.py
    │   ├── urls.py
    │   ├── migrations/
    │   └── tests/
    │
    └── tasks/                     # the actual product surface — depends on: core, accounts, workspaces
        ├── __init__.py
        ├── apps.py
        ├── models.py                # Board, Task — both use TenantScopedManager from workspaces
        ├── state_machine.py         # legal Task.status transitions (todo → in_progress → review → done)
        ├── serializers.py
        ├── views.py                 # ViewSets using select_related + cursor pagination
        ├── urls.py
        ├── migrations/
        └── tests/
```

---

## Explanation

**`config/` is not an app — it's the project itself.** It only holds wiring
(settings, the top-level URL router, Celery setup). It never contains business
logic, so it never needs to be "imported" by an app; apps get plugged into it,
not the other way around.

**`core/` sits at the bottom of the dependency chain on purpose.** It has zero
knowledge of users, workspaces, or tasks — just generic building blocks (the
UUID+timestamp base model, pagination, error formatting) that every other app
reuses. Anything placed here must never import from `accounts`, `workspaces`,
or `tasks` — the moment it does, it stops being generic.

**The dependency direction is one-way, matching the data hierarchy already
defined:** `core ← accounts ← workspaces ← tasks`. Each app only imports from
apps to its left, never to its right:
- `accounts` needs nothing but `core`'s base model.
- `workspaces` needs to know who a `User` is (`accounts`), so it can attach a
  `Membership` to one.
- `tasks` needs `workspaces`' `TenantScopedManager` so `Board` and `Task` get
  automatic per-workspace filtering "for free," the same way described in
  `skeleton_phaese1.md` §3.

**Tenancy code lives inside `workspaces/`, not in `core/`.** It's tempting to
put the contextvar/middleware in `core` since it feels like "infrastructure,"
but the middleware has to look up `Membership` to resolve which workspace a
request belongs to — that's a `workspaces` concept. Putting it in `core` would
force `core` to import from `workspaces`, breaking the one-way dependency rule
and creating a circular import. Keeping it in `workspaces` keeps the arrow
pointing one direction.

**Each app owns its own `views.py`, `serializers.py`, and `urls.py`.** This is
what actually prevents the "one giant file" clutter problem: adding a feature
to tasks means editing files inside `apps/tasks/`, full stop — never reaching
into `accounts/` or `workspaces/` to make it work.
