# Under the Hood — Following One User Through Every Folder

This document follows one real person — call her Alice — using the API from
first sign-up to her first task, and at each step points at exactly which
folder and file does the work. The goal is to make the project's folder
structure click: not "what does Django do in general" but "what does *this*
project's `apps/accounts`, `apps/workspaces`, `apps/tasks`, and `config` each
actually do, and how does a single click travel between them."

Every step below is a real, working endpoint — this isn't hypothetical. It's
the same chain that was tested by hand with `curl` and is repeatable through
the browser test page at `templates/testui.html` (`/testui/`).

---

## The folders, at a glance

Before following Alice through them, here's what each one is *for*, in one
line each:

| Folder | Job |
|---|---|
| `config/` | The control room. Settings, and the master list of URLs that points into every app below. Holds no business logic itself. |
| `apps/core/` | A small shared toolbox. Generic building blocks (like "every table gets an id and a timestamp") that every other app reuses. Knows nothing about users, workspaces, or tasks. |
| `apps/accounts/` | Answers "who are you?" — registering and logging in. |
| `apps/workspaces/` | Answers "which company/team are you acting as right now, and are you actually allowed to?" — this is the tenancy layer, the walls between different customers' data. |
| `apps/tasks/` | The actual product — boards and tasks — built on top of the walls `workspaces` puts up. |
| `templates/` | One plain HTML page (`testui.html`) for manually clicking through the API in a browser instead of typing `curl` commands. |
| `requirements/` | Plain text lists of which external libraries (Django, DRF, etc.) need to be installed. |
| `notes/` | The project's own documentation — this file included. |

The four `apps/` folders aren't independent — they're stacked, each one
allowed to lean on the ones before it but never the other way around:

```
apps/core  <-  apps/accounts  <-  apps/workspaces  <-  apps/tasks
(toolbox)      (who you are)      (which team,          (the actual
                                    walls between          product)
                                    teams)
```

`tasks` is allowed to use something from `workspaces`. `workspaces` is never
allowed to reach back into `tasks`. Keeping the arrow pointing one direction
is what stops the project from turning into a tangle where every file secretly
depends on every other file — it's a deliberate boundary, not an accident of
where a file happened to get created.

---

## Alice's walk through the system

### 1. Alice registers

`POST /api/accounts/register/` with a username, email, and password.

- `config/urls.py` sees the `/api/accounts/` prefix and hands the request to
  `apps/accounts/urls.py`, which points `register/` at `RegisterView`.
- `apps/accounts/views.py` — `RegisterView` is a plain "create a thing" view.
  It doesn't decide *how* a user gets created, it just hands the incoming
  data to a serializer.
- `apps/accounts/serializers.py` — `RegisterSerializer` is where the actual
  decision lives: it takes Alice's plaintext password and runs it through
  Django's password hasher before saving, so what actually lands in the
  database is never her real password, just a one-way scrambled version of
  it.
- `apps/accounts/models.py` — `User` is the table this actually gets saved
  into. It's a custom user model (not Django's stock one) specifically so the
  project could give it a UUID instead of a plain counting number as its id
  — that choice comes from `apps/core/models.py`'s `BaseModel`, which every
  model in every app quietly inherits from. This is `accounts` leaning on
  `core`, the one-directional arrow from the diagram above in action.

Alice now exists as a row in the database. She isn't logged in yet — she just
has an account.

### 2. Alice logs in

`POST /api/accounts/login/` with her username and password.

This one doesn't even touch `views.py` — `apps/accounts/urls.py` points
`login/` directly at a ready-made view from the JWT library the project uses
(`djangorestframework-simplejwt`). It checks her password against the hashed
one from step 1, and if it matches, hands back two tokens: a short-lived
**access token** and a longer-lived **refresh token**.

Think of the access token as a wristband: from now on, Alice attaches it to
every request (`Authorization: Bearer <token>`) instead of typing her
password again. Nothing needs to be "remembered" about Alice on the server
between requests — the wristband itself proves who she is each time.

### 3. Alice creates a workspace

`POST /api/workspaces/` with `{"name": "Alice's Team"}`, wristband attached.

- `config/urls.py` routes `/api/workspaces/` into `apps/workspaces/urls.py`
  → `WorkspaceViewSet`.
- `apps/workspaces/views.py` does two things here, not one: it saves the new
  `Workspace` row, *and* it immediately creates a `Membership` row linking
  Alice to that workspace as its `owner`. This second part matters — without
  it, Alice would create a workspace and then immediately be locked out of
  it, because every check from here on asks "does a Membership row exist for
  this person and this workspace?"
- `apps/workspaces/models.py` is where both `Workspace` and `Membership` are
  defined. `Membership` isn't just "Alice is in this workspace" — it also
  carries a `role` (owner / admin / member), which is what step 5 below
  checks when it needs to know not just "are you in this team" but "are you
  allowed to do *this specific thing*."

Alice now has a workspace, and — crucially — a `Membership` proving she
belongs to it.

### 4. Alice creates a board inside her workspace

`POST /api/boards/` with `{"name": "Sprint 1"}`, wristband attached, plus one
more header: `X-Workspace-ID: <Alice's workspace id>`. This is where the
"walls between tenants" machinery actually switches on:

- `apps/workspaces/middleware.py` runs first, before anything else touches
  the request. Its only job is to read that `X-Workspace-ID` header and
  write it down somewhere every later step can see it.
- "Somewhere every later step can see it" is `apps/workspaces/context.py` —
  a small shared notepad (technically called a *contextvar*) that isn't tied
  to any one file. The middleware writes the workspace id onto this notepad
  at the very start of the request, and wipes it clean at the very end — so
  one person's request can never accidentally leave a note that the *next*
  request reads by mistake.
- Next, `apps/workspaces/permissions.py` checks the notepad and asks: does a
  `Membership` row exist for Alice and this workspace? If not: reject the
  request right here, before it ever reaches the database for boards or
  tasks. This is deliberately a *separate* check from "is your wristband
  valid" (step 2) — one proves who you are, this one proves you're allowed
  into *this specific* workspace.
- Only once that passes does `apps/tasks/views.py` (`BoardViewSet`) actually
  save the board — and it reads the same notepad to stamp the new board with
  the right workspace id, rather than trusting whatever the request body
  claims.
- `apps/tasks/models.py` defines `Board`, and uses a special manager from
  `apps/workspaces/managers.py` (`TenantScopedManager`) — this is the part
  that makes every *future* "give me all the boards" query automatically
  filter down to Alice's workspace, without any view file having to remember
  to add that filter by hand.

Notice the shape of this: `apps/tasks` (the product) leans on
`apps/workspaces` (the walls) to do its job — again, the one-way arrow.

### 5. Alice creates a task on that board

`POST /api/tasks/` with `{"title": "Write the report", "board": "<board id>",
"status": "todo"}`, same wristband and `X-Workspace-ID` header.

Same path as step 4 — middleware notes the workspace, permissions check
membership, `apps/tasks/views.py` (`TaskViewSet`) saves it stamped with the
workspace from the notepad, not from anything Alice's request body claims.

One more file exists here that isn't wired in yet:
`apps/tasks/state_machine.py` defines which task statuses are allowed to
follow which (`todo → in_progress → review → done`, never backwards past
`review`, never straight to `done`). It exists and is correct, but nothing
currently calls it — so today, a task's status can technically be changed to
anything from anything. That's a known, written-down gap (see
`notes/current_progress.md`), not a hidden one.

### 6. Alice comes back later and lists her tasks

`GET /api/tasks/` with just her wristband and `X-Workspace-ID` header — no
body needed.

This is the payoff of everything above: `apps/tasks/views.py` asks for "all
tasks," and because `Task`'s manager is the same `TenantScopedManager` from
step 4, that request is *already* silently filtered to only Alice's
workspace before anything else happens. No view file anywhere had to
remember to write `.filter(workspace=...)` by hand — it's the default
behavior, not something that can be forgotten.

### 7. What happens if someone who *isn't* on Alice's team tries to look?

Say Bob registers and logs in (same path as steps 1–2), but was never given
a `Membership` on Alice's workspace. If Bob sends `GET /api/boards/` with
`X-Workspace-ID: <Alice's workspace id>`, `apps/workspaces/permissions.py`
finds no `Membership` row for Bob on that workspace and rejects the request
with a 403 — before Bob's request ever reaches a single row of Alice's data.
This was verified for real, not just designed on paper: Bob gets 403,
Alice's data never leaves the database for that request.

### 8. Trying all of this without typing raw requests

`templates/testui.html` is a single, plain HTML+JavaScript page — no separate
build step, no framework — that does exactly the eight steps above from
buttons in a browser instead of `curl`. `config/urls.py` serves it at
`/testui/` from the *same* server the API runs on, specifically so a browser
calling it never has to deal with cross-origin restrictions. Every button
click shows the exact request and response in a log panel, which is what
makes it useful for testing changes to any of the folders above by hand.

---

## Two real bugs this design caught (and why the folder boundaries mattered)

Both of these were found by actually running the steps above, not by reading
the code — worth keeping as concrete examples of what "the walls between
tenants" is protecting against:

1. **A workspace id sent in the request body was initially trusted.**
   `apps/tasks/serializers.py` originally let `workspace` be set directly
   from the request body. That meant Alice — a legitimate member of her own
   workspace — could technically write `"workspace": "<Bob's workspace id>"`
   into a task creation request and have it accepted, sneaking a row into a
   workspace she's not a member of. The fix: `workspace` is now read-only on
   the serializer, and is only ever set from the notepad in
   `apps/workspaces/context.py` (step 4/5 above), never from anything the
   client sends.

2. **A queryset was captured too early.** `apps/tasks/views.py`'s
   `BoardViewSet` originally read `Board.objects.all()` once, as a fixed
   value, when the file was first loaded — before any request (and therefore
   before the notepad had anything written on it). That meant it permanently
   baked in "no workspace selected yet," so it silently returned nothing,
   for every request, forever. The fix: read `Board.objects.all()` fresh
   inside a method that runs *per request*, after the notepad has actually
   been written to.

Both bugs are the same shape: something needed a piece of information from
`apps/workspaces/context.py`'s notepad, but read it at the wrong moment or
trusted the wrong source instead. That notepad — set early by
`apps/workspaces/middleware.py`, read late by `apps/workspaces/permissions.py`
and `apps/tasks/views.py` — is the single thread that ties nearly every
folder in this walkthrough together.
