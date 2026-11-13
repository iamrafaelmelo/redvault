# Roadmap

This roadmap is deliberately explicit about the gap between the original target and what exists today. Nothing below is counted as complete until it has a working lab, a manifest, hints, a solution, real references, and an exploit test.

## Current status

**Target:** 150–200 challenge labs and at least 15 independent multi-stage machines.

**Implemented:** 89 challenge labs + 8 machines = **97 working catalog items**.

| Metric | Target | Implemented | Gap |
| --- | ---: | ---: | ---: |
| Challenge labs | 150–200 | **89** | **61 to reach 150** |
| Multi-stage machines | 15+ | **8** | **7 to reach 15** |
| Total minimum catalog | 165 | **97** | **68** |
| Catalog categories | 12 | **12** | 0 — every category has ≥4 challenge labs |
| Progressive hints | 3 per item | **291** | Scales with labs |
| Flags | — | **113** | Scales with machines |
| Real references | ≥1 per item | **291** (151 unique URLs) | Scales with labs |
| Objective-gated items | — | **57** | Scales with stateful labs |
| Academy articles | — | **17** | Content expansion |
| Lab exploit tests | one per lab | **95** | One per new lab |
| Platform integration tests | auth/flags/labs | **23** | Expand with features |
| Insane-difficulty items | — | **4** | Need more depth |

The suite of 118 tests runs as four isolated modules (`python3 run_tests.py`): 61 Phase 1–2 lab tests, 34 Phase 3 lab tests, 13 platform tests and 10 Phase 3 platform tests. The platform modules must run in separate interpreters because `REDVAULT_DATA` is read once at import time.

### Catalog distribution

| Category | Items (including machines) | Challenge-only depth |
| --- | ---: | --- |
| Recon & Discovery | 5 | 5 |
| Authentication | 12 | 11 + 1 machine |
| Access Control | 8 | 8 |
| SQL Injection | 7 | 7 |
| Cross-Site Scripting | 8 | 8 |
| Server-Side Attacks | 10 | 10 |
| API Security | 5 | 5 |
| Business Logic | 10 | 10 |
| File Upload | 6 | 6 |
| Client-Side Security | 5 | 5 |
| Advanced Web Attacks | 5 | 5 |
| Vulnerability Chaining | 16 | 9 + 7 machines |
| **Total** | **97** | **89 challenges + 8 machines** |

### Difficulty distribution (all 97 items)

| Difficulty | Count |
| --- | ---: |
| Beginner | 6 |
| Easy | 26 |
| Medium | 31 |
| Hard | 30 |
| Insane | 4 |

Insane tier: `chain-ssrf-internal`, `chain-upload-to-rce`, `chain-sqli-to-admin`, `chain-lfi-to-rce`.

### Implemented machines

- `machine-nexus-commerce` — commerce chain with user, API and root flags.
- `machine-meridian-bank` — JWT forgery, IDOR and command injection.
- `realistic-horizon-health` — healthcare-style multi-stage assessment.
- `machine-fintech-support` — onboarding backup, BOLA case API, recovery takeover, diagnostics shell.
- `machine-logistics-api` — API docs, carrier SSRF, dispatch token, command injection.
- `machine-insurance-claims` — published onboarding, profile mass assignment, adjuster SSTI.
- `machine-saas-admin-console` (ORBIT, hard) — stale onboarding preview leaks the console JWT secret, claim forgery on the tenant export API, SSRF into the internal worker shell.
- `machine-hr-onboarding` (ATLAS HR, medium) — public onboarding share, payroll IDOR plus profile mass assignment, converter command injection.

Seven machine slots remain. They are not represented by placeholder manifests.

## Completed foundation

- FastAPI + SQLite + Jinja2 + vanilla JS platform, loopback-only.
- First-run setup, login, hashed sessions, CSRF, login throttling, security headers and CSP.
- Challenge/machine catalog, filters, search, tags, detail pages, active lab panel.
- Lab runtime: process spawn, port allocation, readiness checks, reset/stop, idle reaper, max concurrency.
- `bubblewrap` sandbox when available, `prlimit` resource caps, per-lab state directories.
- HMAC-derived flags; server-side validation; no flag values in the database or frontend.
- Objective-gated flags with token-authenticated lab callbacks.
- Progressive hints with XP penalties, solution gating and unlock history.
- XP, levels, achievements, notes, time tracking, activity, profile export.
- 10 learning paths seeded from real catalog slugs.
- 17 academy articles, 22 tools, 27 glossary terms, 10 real CVEs.
- 61 standalone exploit tests and 13 platform integration tests.
- Required documentation set.

## Definition of done for a catalog item

A lab is complete only when all of these are true:

1. `labs/<slug>/app.py` implements a real, reachable vulnerability (not a static paragraph).
2. The exploit is reproducible from a clean reset.
3. `labs/<slug>/manifest.json` validates: slug, category, difficulty, `lab_dir`, flags, 3 sequential hints, solution, references.
4. Hints are progressive and do not print the flag value.
5. The solution has walkthrough, root cause and mitigation.
6. Every reference is a real HTTP(S) source, preferably primary documentation/research.
7. A standalone exploit test passes in `tests/test_labs.py`.
8. The test-name → slug mapping exists in `tests/conftest.py`.
9. If stateful, the objective callback works and the flag is gated.
10. Reset returns the lab to a clean, solvable state.
11. The slug is optional in paths; if referenced, it exists.
12. `python3 run_tests.py` passes (each module in its own interpreter).

A manifest without a working application is not counted. A hint that reveals the flag is not counted. A reference that 404s or is invented is not counted.

## Phase plan

### Phase 1 — Foundation and first catalog (complete)

Delivered: platform core, 28 challenges, 3 machines, academy, tests, docs.

### Phase 2 — Depth and Insane tier (complete: 55 challenges, 6 machines)

**Goal:** 53 challenges + 5 machines. **Status:** reached (55 challenges, 6 machines, 3 Insane). Exit criteria below are met; keep the tier balanced as Phase 3 adds content.

- Add **25 real challenges**, prioritizing underrepresented categories:
  - Recon: cloud storage enumeration, source-map disclosure, cache metadata, API docs.
  - XSS: blind XSS with admin bot, CSP bypass, mutation XSS, DOM clobbering.
  - Upload: polyglot image, archive traversal, content-type confusion, image parser.
  - Client-side: postMessage origin confusion, prototype pollution, CORS misconfiguration, clickjacking chain.
  - Advanced: HTTP request smuggling (where implementable safely), cache poisoning, host-header reset.
  - Server: SSTI sandbox escape, XXE, insecure deserialization in a controlled format, log injection.
  - API: GraphQL field authorization, mass assignment, JWT `kid`/JWKS confusion.
- Add **2 machines** with 3 flags each and distinct stories:
  - A fintech support portal (BOLA → reset poisoning → admin).
  - A logistics API (SSRF → internal metadata → signed token → RCE-style command).
- Add at least **2 Insane** challenges with genuinely complex chains.
- Add tests, paths and academy references for each.
- Add platform tests for simultaneous labs, max-limit enforcement and bot rejection of external targets.

**Exit criteria:** 53 real challenges, 5 machines, 2+ Insane, all tests passing.

### Phase 3 — Breadth and realism (complete, with one gap)

**Goal:** 93 challenges + 9 machines. **Status:** 89 challenges (4 short) and 8 machines (1 short) delivered.

- 34 new challenge labs across every category, including `server-ssti-jinja-sandbox` and `server-deserialization-pickle`, which were finished after the parallel authoring wave; the thinnest categories now hold 4–5 challenge labs (`advanced`, `api`, `client`, `upload`, `xss`).
- 2 new machines: `machine-saas-admin-console` (ORBIT) and `machine-hr-onboarding` (ATLAS HR), three flags each with objective-gated root.
- Every new lab was verified by an independent exploit script before being wired into the suite; all 34 pass.
- Platform work: active-lab cap, login throttling, path/catalog integrity, achievements, profile export, accessibility (lang/title/alt/viewport), mobile breakpoint and search escaping are covered by 10 new tests.
- Two real defects found and fixed while testing: the activity list rendered masked flag values with the literal prefix `RV{` (now shows only the masked form), and achievement unlocks were not flushed before later conditions read the database.
- Test isolation: `app.config` reads `REDVAULT_DATA` once, so a single `pytest` run silently reused the first module's database. `run_tests.py` now runs each module in its own interpreter.

**Not delivered in Phase 3:** the healthcare scheduling and e-commerce checkout machines (2 of the 4 planned), and 4 of the 40 planned challenges. They stay in the Phase 4 backlog rather than being replaced by placeholders.
- Review every lab's mitigation text against current primary sources.

**Exit criteria:** 93 challenges, 9 machines, no category with fewer than 3 challenge labs.

### Phase 4 — Target completion (next)

**Goal:** 150 challenges + 15 machines. Current: 89 challenges, 8 machines. Needs **61 challenges and 7 machines**.

- Add the remaining **61 challenges** (including the 4 deferred from Phase 3) and **7 machines**.
- Balance difficulty: target approximately 15% Beginner, 35% Easy, 30% Medium, 15% Hard, 5% Insane.
- Ensure every challenge has at least one objective-gated or real-browser proof where the class demands it.
- Add cross-lab chaining exercises and a final capstone path.
- Run a full content audit: every reference reachable, every hint non-revealing, every lab reset-testable.
- Freeze content counts and update `README.md`/`ROADMAP.md` with final numbers.

**Exit criteria:** 150+ challenges, 15+ machines, all tests green, documentation counts match the filesystem.

## Machine backlog (not implemented)

These are concepts for future work. They are not manifests and must not be presented as available.

1. ~~**Fintech support portal** — BOLA, reset token leakage, admin console.~~ Implemented as `machine-fintech-support`.
2. ~~**Logistics API** — SSRF to internal metadata, signed request forgery, command injection.~~ Implemented as `machine-logistics-api`.
3. **Healthcare scheduling** — tenant isolation, IDOR, audit-log tampering.
4. **E-commerce checkout** — negative quantity, coupon race, refund abuse.
5. ~~**SaaS admin console** — weak JWT, `kid` injection, BFLA.~~ Implemented as `machine-saas-admin-console`.
6. **CI/CD dashboard** — upload, SVG XSS, template injection, secret exposure.
7. ~~**Insurance claims** — mass assignment, workflow skip, document traversal.~~ Implemented as `machine-insurance-claims`.
8. **University portal** — enumeration, reset poisoning, second-order SQLi.
9. **Travel booking** — price manipulation, race, cache deception.
10. **Internal helpdesk** — blind XSS, stored XSS, admin bot, CSRF chain.
11. **Crypto exchange** — API version downgrade, excessive data, race withdrawal.
12. **Municipal portal** — SSRF, LFI, file upload, privilege escalation.

Deferred from Phase 3 (planned, never built): **HR onboarding** was delivered as `machine-hr-onboarding`; still open are the healthcare scheduling and e-commerce checkout machines.

## Platform backlog

- Database migrations (Alembic) instead of `create_all`.
- Per-lab CPU/memory cgroups and optional network namespace.
- Structured audit log with rotation and redaction.
- Two-factor authentication for the operator account.
- Content validation that checks reference URLs and duplicate slugs before seeding.
- Automated API tests for every route and permission boundary.
- UI tests for the lab panel, hint unlocks and mobile layout.
- Optional per-lab hostnames to strengthen browser-origin separation.
- Backup/restore command for database + secret.
- Lab packaging documentation and a signed-content workflow for third-party labs.

## Non-goals

- Public multi-tenant hosting.
- A marketplace of untrusted labs.
- Replacing a professional penetration-testing lab or a VM-based range.
- Claiming 150 labs before 150 working applications exist.
- Using fake tests, static "flags", or invented references to inflate counts.

## How progress is measured

```bash
# Count real manifests and kinds
python3 - <<'PY'
import glob, json, collections
items = [json.load(open(p)) for p in glob.glob("labs/*/manifest.json")]
print("total", len(items))
print(collections.Counter(i.get("kind", "challenge") for i in items))
print(collections.Counter(i["difficulty"] for i in items))
PY

# Run the real exploit suite
python3 -m pytest tests/test_labs.py -q
```

If the count and the tests disagree, the tests win.
