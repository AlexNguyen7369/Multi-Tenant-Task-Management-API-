# Database Setup — From Model Code to Real Tables

This traces the path from the model files already sitting in `apps/*/models.py`
to actual tables you can query, in the order it happens. Nothing is skipped or
combined — each arrow below is a separate, real step.

---

## The pipeline

```
 1. Python model classes                    apps/core/models.py
    (BaseModel, User, Workspace,             apps/accounts/models.py
     Membership, Board, Task)                apps/workspaces/models.py
                                              apps/tasks/models.py
            │
            │  these are just Python classes right now —
            │  Postgres has never heard of them
            ▼
 2. Postgres server running                 a real, running database process
    (empty — no tables yet)                  listening for connections
            │
            │  manage.py makemigrations
            │  Django reads the model classes and writes a
            │  migration file describing "create these tables,
            │  with these columns/types/foreign keys"
            ▼
 3. Migration files                         apps/*/migrations/0001_initial.py
    (a plan, not applied yet)                (plain Python — reviewable,
                                               like any other code change)
            │
            │  manage.py migrate
            │  Django reads the migration file and actually
            │  runs the CREATE TABLE / ALTER TABLE statements
            │  against the running Postgres server from step 2
            ▼
 4. Real tables exist in Postgres           \d users, \d workspaces,
    ready to be queried                      \d memberships, \d boards, \d tasks
```

**The two commands that matter:**
- `makemigrations` — turns "what my models look like" into a written, saved
  plan (a migration file). Does **not** touch the database at all.
- `migrate` — takes that saved plan and actually applies it to a running
  database, creating/altering the real tables.

This is why Postgres has to be running *before* `migrate` (step 2 happens
before step 4's arrow), but `makemigrations` (step 1 → 3) doesn't need
Postgres running at all — it only reads your Python code.

---

## What the tables themselves look like

Simplified shape of the five tables `migrate` will create, based on the models
already scaffolded (full reasoning for each choice is in
`skeleton_phaese1.md` §2):

```
 users
 ┌────────────┐
 │ id (uuid)  │◄──┐
 │ username   │   │
 │ email      │   │
 │ ...        │   │
 └────────────┘   │
                   │ user_id
 memberships       │
 ┌────────────┐    │
 │ id (uuid)  │    │
 │ user_id    │────┘
 │ workspace_id│───┐
 │ role       │   │
 └────────────┘   │
                   │ workspace_id
 workspaces        │
 ┌────────────┐    │
 │ id (uuid)  │◄───┴──────┐
 │ name       │           │
 └────────────┘           │
                           │ workspace_id
 boards                    │
 ┌────────────┐            │
 │ id (uuid)  │◄───────────┘
 │ workspace_id│───────────┘
 │ name       │
 └────────────┘
       ▲
       │ board_id
 tasks │
 ┌────────────┐
 │ id (uuid)  │
 │ workspace_id│
 │ board_id   │
 │ title      │
 │ status     │
 │ assignee_id│──► users.id
 └────────────┘
```

`memberships` is the join between `users` and `workspaces`, carrying a `role`.
`boards` and `tasks` both carry their own `workspace_id` directly (not just
inherited through `board`) — this is what lets `TenantScopedManager` filter
either table by workspace in a single `WHERE`, without an extra join.

---

## Explanation

The reason this project keeps model code and the actual database as two
separate, sequential steps (rather than something that "just happens") is that
**migrations are the reviewable history of every schema change** — each
`makemigrations` run produces a file that sits in git next to the code that
caused it, so anyone (including future you) can see exactly when and why a
column or table changed, and roll it back if needed. Skipping straight to a
database GUI and clicking "add column" would lose that trail entirely.

The practical order going forward, matching the pipeline above:
1. Get Postgres running (step 2) — done once per machine.
2. `makemigrations` (step 1 → 3) — done every time a model changes.
3. `migrate` (step 3 → 4) — done every time there's a new migration file to
   apply, including right after the first `makemigrations`.
