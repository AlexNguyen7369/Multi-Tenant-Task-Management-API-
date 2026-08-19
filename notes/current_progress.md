# Current Progress

Snapshot of where the project stands right now, and what's next. Update this
file whenever a work session ends — replace it, don't just append, so it
always reflects the real current state.

---

## Done so far

- [x] Stack + architecture decided — `stack.md`, `skeleton_phaese1.md`
- [x] App folder structure scaffolded (`core`, `accounts`, `workspaces`,
      `tasks` + `config/`) — `app_structure.md`
- [x] Virtualenv (`.venv/`) created, `requirements/dev.txt` installed
- [x] Postgres 16 installed and running locally (Homebrew service),
      `taskapi` database created, tables migrated — `database_setup.md`
- [x] **Tenancy middleware implemented** — `WorkspaceMiddleware._resolve_workspace_id`
      reads an `X-Workspace-ID` header and sets the contextvar. Deliberately
      does *not* check membership itself: Django middleware runs before DRF's
      own authentication populates `request.user` from the JWT, so membership
      checking is left to the permission classes below, which run later.
- [x] **Role/tenancy permission classes implemented** —
      `IsWorkspaceMember` / `IsWorkspaceAdmin` (`apps/workspaces/permissions.py`),
      backed by a real `Membership` lookup. Wired onto `BoardViewSet` and
      `TaskViewSet`.
- [x] **`WorkspaceViewSet.get_queryset` implemented** — scoped to the
      requesting user's memberships. `perform_create` now also creates an
      owner `Membership` for the creator (without this, creating a workspace
      would immediately lock its creator out of it).
- [x] **`RegisterSerializer.create` implemented** — uses
      `User.objects.create_user(...)` so passwords are hashed, not stored
      plain.
- [x] **Closed a write-side tenancy leak found while testing**: `workspace`
      was a client-writable field on `Board`/`Task`, so a member of workspace
      A could `POST` with `"workspace": "<B's id>"` in the body and write into
      a tenant they don't belong to. `workspace` is now `read_only` on both
      serializers and set server-side in `perform_create` from the tenancy
      context instead.
- [x] **Fixed a latent bug surfaced by the above**: `BoardViewSet` had
      `queryset = Board.objects.all()` as a *class attribute*, which
      evaluates once at import time — before any request sets the workspace
      contextvar — so `TenantScopedManager` baked in `workspace_id=None`
      (i.e. always empty) permanently. Changed to a `get_queryset()` method,
      matching `TaskViewSet`, so it re-reads the contextvar per request.
- [x] **Manual test console added** — `templates/testui.html`, served
      same-origin at `/testui/` (see `config/urls.py`, no CORS setup needed).
      Vanilla HTML/JS, no build step: register/login, create/select
      workspace, create/select board, create/update tasks, and a live
      request+response log for every call. Includes a suggested manual test
      script (create two workspaces, flip the active one, watch board/task
      lists change).
- [x] **Full chain verified end-to-end via curl** (register → login → create
      workspace → create board → create task), plus:
      - tenancy isolation holds (workspace B sees none of workspace A's data)
      - the write-side spoofing attempt above is correctly ignored
      - a non-member correctly gets `403` on another workspace's boards
      - a request with no `X-Workspace-ID` header correctly gets `403`

## Left off here

The core tenancy chain works and is proven end-to-end. Not yet done:

- No automated tests exist yet — everything above was verified manually via
  curl and the test console, not committed as a test suite.
- `Task.status` transitions are **not** enforced yet — `state_machine.py`'s
  `validate_transition` exists but nothing calls it, so `PATCH status` can
  currently jump from any status to any other (the test console's status
  dropdown will let you do this; it's demonstrating the gap, not a UI bug).
- No validation that a `Task.board` actually belongs to the active workspace
  (narrower version of the leak that was fixed for `workspace` itself —
  lower risk since board ids come from an already tenant-scoped list, but
  not explicitly checked).
- `RegisterSerializer` has no duplicate-username/email handling beyond
  whatever Django's model constraints raise by default.

## Next course of action

1. Wire `state_machine.validate_transition` into `TaskViewSet` (or a
   `Task.save()`/serializer hook) so illegal status jumps are rejected —
   currently the only unenforced piece of the data model design.
2. Write the tenancy-isolation test from `skeleton_phaese1.md` §7 step 10 as
   an actual automated test (it's been proven manually via curl above; now
   pin it down so it can't regress silently).
3. Add role-permission tests (`IsWorkspaceAdmin` exists but nothing in the
   views uses it yet — no admin-only action is defined; decide if one is
   needed, e.g. only owner/admin can delete a workspace).
4. Validate `Task.board.workspace_id == <active workspace>` on create/update.
