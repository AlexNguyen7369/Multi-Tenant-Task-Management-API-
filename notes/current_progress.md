# Current Progress

Snapshot of where the project stands right now, and what's next. Update this
file whenever a work session ends — replace it, don't just append, so it
always reflects the real current state.

---

## Done so far

- [x] Stack + architecture decided — `stack.md`, `skeleton_phaese1.md`
- [x] App folder structure scaffolded (`core`, `accounts`, `workspaces`,
      `tasks` + `config/`) — `app_structure.md`
- [x] All model classes, serializers, views, urls, middleware/manager
      **stubs** written (business logic left as `TODO`/`NotImplementedError`
      where noted below)
- [x] Virtualenv (`.venv/`) created, `requirements/dev.txt` installed
- [x] `manage.py check` passes — project boots cleanly
- [x] Postgres 16 installed and running locally (Homebrew service),
      `taskapi` database created — `database_setup.md`
- [x] `makemigrations` + `migrate` run successfully — **real tables now
      exist**: `accounts_user`, `workspaces_workspace`,
      `workspaces_membership`, `tasks_board`, `tasks_task`

## Left off here

Tables exist, but the actual request-handling logic is still stubbed out.
Nothing has been tested end-to-end (no request has successfully gone
through routing → auth → tenancy → database yet).

## Still stubbed / `TODO` (in the order they block each other)

1. `apps/workspaces/middleware.py: WorkspaceMiddleware._resolve_workspace_id`
   — **highest priority**, everything tenant-scoped depends on this
2. `apps/workspaces/permissions.py: IsWorkspaceMember / IsWorkspaceAdmin`
3. `apps/workspaces/views.py: WorkspaceViewSet.get_queryset`
4. `apps/accounts/serializers.py: RegisterSerializer.create` (password hashing)

## Next course of action

1. Implement `_resolve_workspace_id` (unblocks tenancy end-to-end)
2. Implement the two permission classes
3. Implement `WorkspaceViewSet.get_queryset`
4. Fix password hashing in `RegisterSerializer`
5. Manually exercise one full request end-to-end (register → login → create
   workspace → create task) to prove the whole chain actually works
6. Write the tenancy-isolation test from `skeleton_phaese1.md` §7 step 10
   (prove Workspace A can never see Workspace B's data)
