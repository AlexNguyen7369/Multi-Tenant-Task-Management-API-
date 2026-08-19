# CLAUDE.md

Notes for Claude Code sessions working in this repository.

## What this project is

A multi-tenant task management API — Django + Django REST Framework +
PostgreSQL, shared-schema multi-tenancy (every tenant-owned row carries a
`workspace_id`, enforced via middleware + a contextvar + custom model
managers, not separate databases/schemas per tenant).

Full reasoning for every decision lives in `notes/`, not here:
- `notes/stack.md` — chosen technologies
- `notes/skeleton_phaese1.md` — architecture + reasoning, Phase 1 build order
- `notes/app_structure.md` — app/folder layout + why
- `notes/database_setup.md` — model → migration → table pipeline
- `notes/hood.md` — one request traced through every layer
- `notes/current_progress.md` — **current state, read this first**

## Working conventions

- Keep `notes/current_progress.md` accurate — it's the single source of
  truth for "where did we leave off." Update it (don't just append) at the
  end of any session that changes project state.
- Follow the app dependency direction from `app_structure.md`:
  `core ← accounts ← workspaces ← tasks`. Never import right-to-left.
- Don't fill in a `TODO`/`NotImplementedError` stub without checking
  `notes/current_progress.md` for why it was left that way.

## Session Log

**Always update at the end of a session that produced commits — rewrite the
top entry, don't just append prose from memory.** The entry must be grounded
in what actually changed, not a recollection of the conversation:

1. Run `git log` (and `git diff` against the previous entry's last commit if
   more detail is needed) to see every commit made this session.
2. Rewrite that session's entry as a short bullet list of what those commits
   actually did — one bullet per meaningful change, derived from the real
   diff/commit messages, not paraphrased from the discussion that led to them.
3. End the entry with a **Next** line: the next logical development step,
   plus one short clause on *why* — specifically, what already-built piece
   depends on it or is blocked without it. Not "next we could..." — name the
   real dependency.
4. If a session produced no commits, don't add an entry.

Newest entry on top. Keep entries short — a handful of bullets, not a
narrative.

### 2026-08-18
- `first commit` — repo initialized
- `Add Phase 1 architecture skeleton and design reasoning` — tenancy model,
  data model, auth strategy decided and written down (`skeleton_phaese1.md`)
- `Add under-the-hood request lifecycle walkthrough` — full request trace,
  DNS through response (`hood.md`)
- `Add stack.md listing project technologies by category` — Phase 1 / Phase 2
  tech choices recorded with reasoning
- `skeleton for phase1, folder scaffolding for app structure` — `core`,
  `accounts`, `workspaces`, `tasks`, `config/` scaffolded with
  model/view/serializer/middleware stubs; `.venv` created, `requirements/dev.txt`
  installed, `manage.py check` passes
- `postgres running, created relational tables to allow for middleware logic
  and routing` — Postgres 16 installed + running locally (Homebrew),
  `taskapi` db created, `makemigrations`/`migrate` run — real tables now exist

**Next:** implement `WorkspaceMiddleware._resolve_workspace_id`
(`apps/workspaces/middleware.py`). Every tenant-scoped piece already built —
`TenantScopedManager` (reads the contextvar this middleware sets),
`IsWorkspaceMember`/`IsWorkspaceAdmin`, and `WorkspaceViewSet.get_queryset` —
is a stub that depends on this contextvar actually being populated. None of
them can be implemented or tested against real behavior until this method
resolves a real workspace from the request.
