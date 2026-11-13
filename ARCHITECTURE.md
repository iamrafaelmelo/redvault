# Architecture

REDVAULT is a single-operator, local-first web application. The platform serves the UI and validates progress; each vulnerable lab is a separate Flask process on a loopback port. Content is file-based; user state is SQLite.

## 1. Design goals

1. **Real targets, not simulations.** Every lab is an executable application with a genuine vulnerability and an exploit test.
2. **Local by default.** Platform and labs bind to `127.0.0.1`; no cloud dependency.
3. **Flags never leak.** Values are derived at runtime and validated server-side. They are not stored in SQLite or rendered in HTML.
4. **Stateful exploits are provable.** Objective-gated flags require a lab callback tied to the active session.
5. **Content is data.** Adding a lab should not require editing the platform core.
6. **Honest progress.** The catalog only shows implemented manifests; counts reflect real applications.

Non-goals: multi-tenant SaaS, public internet exposure, production application hosting, or a hardened container orchestration platform.

## 2. Runtime topology

```text
                      ┌─────────────────────────────────────────┐
                      │ Browser (operator)                      │
                      │ http://127.0.0.1:8000                   │
                      └───────────────┬─────────────────────────┘
                                      │ HTML + JSON API
                                      ▼
┌────────────────────────────────────────────────────────────────────┐
│ FastAPI platform (one process)                                     │
│                                                                    │
│  web.py       HTML routes, auth, dashboard, catalog, academy       │
│  api.py       start/stop/reset, hints, flags, notes, heartbeat      │
│  internal.py  lab callback + browser bot bridge                    │
│  content.py   manifest discovery, validation, seeding               │
│  security.py  sessions, CSRF, bcrypt, rate limiting, flash          │
│  flags.py     HMAC derivation + objective validation                │
│  lab_manager  process lifecycle, ports, bwrap, prlimit, reaper      │
│                                                                    │
│  SQLite: data/redvault.db                                          │
│  Secret: data/secret.key (0600)                                    │
└───────────────┬───────────────────────────────┬────────────────────┘
                │ spawn / stop / health         │ HTTP callback
                ▼                               │
┌──────────────────────────────┐                │
│ Lab process (Flask)          │────────────────┘
│ 127.0.0.1:42000-42999        │  token-bound objective
│ bwrap (optional) + prlimit   │  / internal/bot
│ own state directory          │
└──────────────────────────────┘
```

Optional for browser labs:

```text
lab → /internal/bot (token) → Selenium/Chromium → lab page (loopback, exact port)
```

The bot never returns page contents to the lab; the lab collects its own exfiltrated evidence.

## 3. Components

### `app/main.py`

FastAPI application factory. On lifespan startup it:

1. Ensures `data/` directories exist.
2. Calls `init_db()` (`Base.metadata.create_all`).
3. Seeds categories, manifests, paths and achievements.
4. Reconciles lab sessions left over from a previous process.
5. Starts the idle reaper on first lab start.
6. On shutdown, terminates active lab process groups.

Middleware adds security headers and a CSP for all paths except `/api/docs` when development docs are enabled.

### `app/web.py`

HTML routes: setup/login/logout, dashboard, challenges, machines, details, paths, academy, tools, glossary, CVEs, profile/export, environments, settings, search. It creates a `Progress` row lazily when a detail page is opened, renders markdown through a `Markup` helper, and never includes raw flag values.

### `app/api.py`

JSON API used by `static/js/app.js`:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/challenges/{slug}/status` | Active lab state and progress |
| POST | `/api/challenges/{slug}/start` | Spawn a lab (CSRF) |
| POST | `/api/challenges/{slug}/stop` | Stop the user's lab (CSRF) |
| POST | `/api/challenges/{slug}/reset` | Fresh state, clear objectives (CSRF) |
| POST | `/api/challenges/{slug}/hints/{level}` | Unlock a hint (CSRF) |
| POST | `/api/challenges/{slug}/solution` | Unlock walkthrough (CSRF) |
| POST | `/api/challenges/{slug}/flags` | Submit a flag (CSRF) |
| POST | `/api/challenges/{slug}/heartbeat` | Add capped time on target (CSRF) |
| POST | `/api/challenges/{slug}/notes` | Save private notes (CSRF) |
| GET | `/api/labs` | Active labs for the operator |
| GET | `/api/search` | Challenge and academy search |

Authentication failures return 401; CSRF failures return 403; missing content returns 404.

### `app/internal.py`

Private endpoints, not part of the UI contract:

- `POST /internal/lab-callback` — a lab records objective completion. The body carries the per-session token. The platform hashes it, finds the `LabSession`, confirms the process is active, validates that the flag key exists, and writes `ObjectiveState`.
- `POST /internal/bot` — a lab requests the victim browser. The token must map to an active lab; the URL must be an IP literal on loopback and exactly the lab's own port; cookies are sanitized and bounded.

These endpoints are on the platform's loopback interface. They are not exposed publicly, but a local process could reach them if it obtained a token. Tokens are random 32-byte values and are only injected into the owning lab process.

### `app/lab_manager.py`

`LabManager` owns an in-memory map of active labs and a set of allocated ports.

Responsibilities:

- Allocate free ports in `[LAB_PORT_START, LAB_PORT_END]`.
- Enforce `MAX_ACTIVE_LABS`.
- Create a unique state directory: `data/labs/state/<slug>-<user>-<timestamp>`.
- Build a command with optional `bwrap` and `prlimit`.
- Inject environment: port, state dir, callback URL/token, session id, challenge slug/id, user id, and only that lab's derived flags.
- Store a `LabSession` row with a hash of the callback token.
- Poll `/health` until ready or timeout.
- Stop process groups on stop/reset/shutdown.
- Reap idle labs after `LAB_IDLE_TIMEOUT`.
- On reset, stop the old process, clear objective state for the session, start fresh, and carry the reset counter.

Port allocation probes the port with a bind before claiming it, so it skips ports already used by a previous or external process.

### `app/security.py`

- bcrypt password hashes (cost 12).
- Session tokens: 48 random bytes, stored as SHA-256 hashes. Cookie `rv_session`, `HttpOnly`, `SameSite=Lax`, 72-hour TTL.
- CSRF: a per-session random token in a meta tag and hidden forms, checked with constant-time comparison.
- Login throttling: in-memory failure buckets per IP + username, 8 failures in 5 minutes.
- Flash messages: signed with `itsdangerous`, two-minute max age.
- `sanitize_next()` restricts post-login redirects to local absolute paths.

### `app/content.py`

Discovers `labs/*/manifest.json`, validates required fields, upserts categories/challenges/flags/hints/solutions/references, removes rows for missing labs, then seeds paths and achievements. Manifest errors are logged and reported; invalid labs still appear in discovery output but should be treated as broken content.

### `app/services/progress.py`

Progress status (`in_progress`/`completed`), XP calculation, hint penalties, achievement evaluation, category/difficulty statistics, activity feed, and learning-path progress.

## 4. Data model

```text
User 1─* AuthSession
User 1─* Progress *─1 Challenge 1─* Flag
User 1─* FlagSubmission       Challenge 1─* Hint
User 1─* HintUnlock          Challenge 1─1 Solution
User 1─* ObjectiveState      Challenge 1─* Reference
User 1─* Activity            Challenge 1─* LabSession
User 1─* UserAchievement *─1 Achievement
Category 1─* Challenge
Path 1─* PathChallenge *─1 Challenge
User 1─* UserSetting
```

Key tables:

- **`challenges`** — catalog item; `kind` is `challenge`, `machine` or `realistic`.
- **`flags`** — metadata only (`key`, label, type, points, required, `requires_objective`). No value column.
- **`flag_submissions`** — hash and masked value for audit, never the raw flag.
- **`lab_sessions`** — port, PID, hashed callback token, state directory, status, reset count.
- **`objective_states`** — per user/challenge/flag key; set only by a validated lab callback.
- **`progress`** — status, hints, penalty, XP, time, solution flag, notes.

SQLite uses WAL, foreign keys, a 5-second busy timeout and `NORMAL` synchronous mode. There is no migration framework; schema changes rely on `create_all` for new tables and should be handled manually for existing columns.

## 5. Content contract

Each lab directory must contain `app.py` and `manifest.json`. A manifest is validated for:

- `slug`, `title`, `summary`, `category`, `difficulty`, `lab_dir`
- at least one flag with unique keys and a valid type
- exactly sequential hint levels starting at 1, at least 3, each with title and body
- a solution with `walkthrough`, `root_cause`, `mitigation`
- at least one HTTP(S) reference

Example skeleton:

```json
{
  "slug": "example-lab",
  "title": "Example Target",
  "summary": "What the operator must understand.",
  "category": "sqli",
  "difficulty": "medium",
  "kind": "challenge",
  "lab_dir": "example-lab",
  "estimated_minutes": 20,
  "xp": 150,
  "flags": [
    {"key": "flag", "label": "Target flag", "flag_type": "user", "points": 150, "required": true}
  ],
  "hints": [
    {"level": 1, "title": "Orient", "body": "...", "cost": 10},
    {"level": 2, "title": "Focus", "body": "...", "cost": 20},
    {"level": 3, "title": "Execute", "body": "...", "cost": 25}
  ],
  "solution": {"walkthrough": "...", "root_cause": "...", "mitigation": "..."},
  "references": [
    {"title": "Primary source", "url": "https://...", "source_type": "standard"}
  ]
}
```

The lab reads configuration from `labkit`:

- `LAB_PORT`, `LAB_STATE_DIR`
- `LAB_FLAGS` (JSON object keyed by flag key)
- `LAB_CALLBACK_URL`, `LAB_CALLBACK_TOKEN`, `LAB_SESSION_ID`
- `LAB_PLATFORM_URL`
- `LAB_CHALLENGE_SLUG`, `LAB_CHALLENGE_ID`, `LAB_USER_ID`

`labs/_shared/labkit.py` provides flag lookup, objective callbacks and the browser bot bridge. A lab must not hardcode a flag value.

## 6. Flag derivation and objective gating

The master secret is created once at `data/secret.key` with `0600` permissions. For each challenge and flag key:

```text
digest = HMAC-SHA256(secret, "flag:<slug>:<flag_key>")
token  = base32(digest[0:15]).lower().rstrip("=")
flag   = "RV{<slug-prefix>_<token>}"
```

Properties:

- Deterministic for a given secret, so resetting a lab does not change the expected value.
- Not stored in `flags` or on disk in plaintext.
- Only the owning lab receives its own values through `LAB_FLAGS`.
- Submission validation uses constant-time comparison.
- `requires_objective` flags additionally require an `ObjectiveState` row written by a token-authenticated lab callback.

The platform does not expose a "flag reveal" API. Hints and walkthroughs are reviewed to avoid printing actual derived values.

## 7. Browser bot

Selenium/Chromium is optional. The bot:

- Validates the URL scheme, hostname and port: must be an IP literal, loopback, and the exact port of the requesting lab.
- Rejects userinfo, external hosts and other ports.
- Sets a readable victim cookie on the lab origin.
- Visits the supplied lab URL and waits briefly.
- Returns only `ok`, elapsed time and final URL (no DOM, cookies or response body).

Labs collect their own exfiltration and call the objective endpoint. This keeps the bot from becoming a generic browser-as-a-service.

## 8. Testing architecture

### Lab tests (`tests/test_labs.py`)

`tests/conftest.py` maps each test function to one lab slug, starts the real `app.py` on an ephemeral loopback port with dummy `LAB_FLAGS`, waits for `/health`, and tears down the process group. Tests perform real exploits (SQLi, JWT forgery, SSRF, LFI, command injection, XSS collection, etc.) and assert the dummy flag appears.

### Platform tests (`tests/test_platform.py`)

Sets a temporary `REDVAULT_DATA` before importing app modules, boots the real FastAPI lifespan with `TestClient`, and covers:

- first-run validation and setup
- login/logout, `next` sanitization and CSRF
- catalog and detail pages never containing derived flags
- CSRF enforcement on lab mutation
- start/status/reset/stop with a real lab process
- hint progression, penalties and solution gating
- flag validation, completion, XP and duplicate handling
- objective-gated flags
- invalid internal callback tokens
- all primary UI pages
- academy loading, filters and references
- private profile export
- confirmation-gated progress reset

The platform tests use the same real lab runtime as production and clean up their temporary data at exit.

## 9. Extension points

### Add a challenge

1. Create `labs/<slug>/app.py` using `labkit`.
2. Add `labs/<slug>/manifest.json` with real hints, solution and references.
3. Add an exploit test in `tests/test_labs.py`.
4. Add the test-name → slug mapping in `tests/conftest.py`.
5. Optionally add the slug to a path in `content/paths.json`.
6. Restart the platform; content is re-seeded.

### Add a machine

Use `kind: "machine"` (or `"realistic"`) and multiple flags with keys such as `user`, `api`, `root`. The machine page groups required flags and only marks completion when all required flags are accepted. Implement every stage in one `app.py`, and make reset restore the initial state.

### Add an academy article

Drop a Markdown file in `content/academy/` with YAML frontmatter. Required frontmatter keys used by the UI: `slug`, `title`, `category`, `difficulty`, `summary`, `tags`, `updated`, `source_type`, `order`. The loader caches by mtime, so edits appear without restart.

## 10. Known constraints

- SQLite and one platform process; no horizontal scaling.
- No TLS; loopback only.
- `bwrap` is a process sandbox, not a VM or container. Labs share the host network namespace by default, so outbound egress exists.
- No seccomp profile or cgroup memory limit; `prlimit` caps address space and files, not CPU or all kernel surfaces.
- No database migrations.
- Content seeding deletes catalog rows for manifests that disappear; user submissions reference flags with `SET NULL` where configured.
- The bot is serialized by a global lock; long bot runs can delay other browser labs.
- The platform does not scan uploaded files; labs are intentionally vulnerable and should not receive real user data.

See [SECURITY.md](SECURITY.md) for the threat model and deployment guidance.
