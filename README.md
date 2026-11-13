# REDVAULT

**A private, local-first offensive security lab.** REDVAULT is a self-hosted platform for practicing web exploitation against real, intentionally vulnerable applications. It includes a challenge catalog, multi-stage machines, progressive hints, server-side flag validation, XP and achievements, learning paths, an academy, and a lab process manager.

> **Idioma.** A interface, o conteúdo dos desafios, os hints, os walkthroughs, a academia, o glossário e as mensagens da plataforma estão em **português do Brasil (pt-BR)**. Termos técnicos de segurança (IDOR, BOLA, SSRF, SSTI, JWT, CSRF, SQL injection, payload, header, token etc.) permanecem em inglês, e o código, os comandos e os valores literais dos labs não são traduzidos. Este README e o `INSTALL.md` continuam em inglês para manter compatibilidade com referências externas.

> **Authorized use only.** Every target is intentionally vulnerable. The platform binds to `127.0.0.1` and is designed for one trusted operator on a local machine. Never expose the platform or lab ports to a public network. Do not run third-party lab code you do not trust; the isolation model is explained in [SECURITY.md](SECURITY.md).

---

## Status (honest snapshot)

The original target was **150–200 challenge labs and at least 15 multi-stage machines**. The current repository does **not** meet that target yet.

| Metric | Target | Implemented | Status |
| --- | ---: | ---: | --- |
| Challenge labs | 150–200 | **89** | In progress (61 to go) |
| Multi-stage machines | 15+ | **8** | In progress (7 to go) |
| Total working catalog items | 165+ | **97** | In progress (68 to go) |
| Categories covered | 12 | **12** | Covered |
| Academy articles | — | **17** | Covered |
| Standalone exploit tests | one per lab | **95** | Passing |
| Platform integration tests | auth, flags, labs | **23** | Passing |
| Progressive hints | 3 per item | **291** | Implemented |
| Flags (incl. 3 per machine) | — | **113** | Implemented |
| Real references | ≥1 per item | **291** (151 unique) | Implemented |
| Objective-gated items | — | **57** | Implemented |
| Insane-difficulty items | — | **4** | Implemented |

Implemented items: **89 challenges + 8 machines = 97 working lab applications**. Every item has a real `app.py` or an escaped template, a validated `manifest.json`, three progressive hints, a full walkthrough/root cause/mitigation, and primary-source references. Counts are not inflated with empty manifests.

### Difficulty distribution

| Difficulty | Items |
| --- | ---: |
| Beginner | 6 |
| Easy | 26 |
| Medium | 31 |
| Hard | 30 |
| Insane | 4 |

### Second-wave labs (v0.7)

New in this wave: source-map and cloud-listing recon, API docs discovery, session fixation, JWT `kid` traversal and algorithm confusion, OTP brute force, tenant header and method-override access bypasses, blind and WAF-bypassed SQL injection, attribute-injection and blind stored XSS, NoSQL operator auth, blind command injection, XXE, webhook SSRF with alternate loopback notation, pagination data leak, refund and workflow-skip logic flaws, CORS reflection, filename XSS, zip-slip with template execution, cache poisoning, plus insane chains (`chain-ssrf-internal`, `chain-upload-to-rce`, `chain-sqli-to-admin`) and three new machines with user/API/root flags.

### Third-wave labs (v0.8)

34 new labs: CSP nonce bypass, DOM clobbering, JSONP under CSP, prototype pollution, clickjacking, WebSocket CSRF; GraphQL field authorization and batch-endpoint auth bypass; tar-archive traversal, content-type confusion and GIF/HTML polyglot uploads; JWT `jku` injection, reset-link host poisoning, MFA response manipulation, SSO assertion replay (XSW); HTTP parameter pollution, trusted proxy headers; stacked and `ORDER BY CASE` SQL injection; SSTI to Flask `SECRET_KEY`; five business-logic flaws (coupon race, signup bonus loop, self-approval, cart rounding, invite reuse); host-header cache poisoning, CSRF token reuse, cache-key normalization; five chains (`chain-open-redirect-to-token-theft`, `chain-jwt-to-sqli`, `chain-xss-to-csrf-admin`, `chain-ssti-to-flask-config`, `chain-lfi-to-rce`), a Jinja sandbox escape (`server-ssti-jinja-sandbox`) and an insecure `pickle` session cookie (`server-deserialization-pickle`).

### Implemented machines

| Machine | Category | Flags | Focus |
| --- | --- | --- | --- |
| `machine-nexus-commerce` | chain | user, api, root | commerce chain, object access, privilege escalation |
| `machine-meridian-bank` | auth | user, api, root | JWT, IDOR, command injection |
| `realistic-horizon-health` | chain | user, api, root | healthcare-style multi-stage assessment |
| `machine-fintech-support` | chain | user, api, root | onboarding backup, BOLA case API, reset flow, diagnostics shell |
| `machine-logistics-api` | chain | user, api, root | API docs, carrier SSRF, dispatch token, command injection |
| `machine-insurance-claims` | chain | user, api, root | published onboarding, mass assignment, adjuster SSTI |
| `machine-saas-admin-console` | chain | user, api, root | leaked console JWT secret, claim forgery, SSRF to internal worker shell |
| `machine-hr-onboarding` | chain | user, api, root | public share, payroll IDOR, mass assignment, converter injection |

### Implemented challenge categories

Recon & Discovery, Authentication, Access Control, SQL Injection, XSS, Server-Side Attacks, API Security, Business Logic, File Upload, Client-Side Security, Advanced Web Attacks, Vulnerability Chaining. Every category holds at least 4 challenge labs.

---

## What works

- **No login.** REDVAULT is a single-operator, loopback-only installation: every request is served as the local operator, which is created on first start. Browser sessions exist only to carry a CSRF token.
- **LAN sharing (opt-in)**: with `REDVAULT_LAB_BIND=0.0.0.0` + `REDVAULT_LAB_PUBLIC_HOST=<your-ip>`, a second computer on the same network attacks the labs directly, no VPN. The dashboard stays on loopback. See [SECURITY.md](SECURITY.md#opt-in-attacking-the-labs-from-a-second-machine-on-the-lan).
- **One room page per target**: `/lab/<slug>` opens the challenge or machine full screen, like a TryHackMe room, with its own top bar instead of the dashboard sidebar. The dashboard detail view stays available.
- **Lab lifecycle**: start, status, reset, stop, port allocation, readiness checks, idle reaper, five concurrent labs by default.
- **Isolation**: separate process per lab, loopback-only ports `42000–42999`, optional `bubblewrap` sandbox and `prlimit` resource caps.
- **Per-lab flags** derived with HMAC-SHA256 from a local master secret. Flag values are never stored in SQLite or rendered in the frontend.
- **Objective-gated flags** for stateful exploits. The lab must record a real callback before the platform accepts the flag.
- **Progressive hints** with XP penalties, locked until requested, and a full walkthrough that requires all hints (or a completed target).
- **Progress, XP, levels, achievements, notes, heartbeat time tracking, activity feed and JSON export.**
- **Learning paths** built from real catalog slugs.
- **Academy** with 17 articles and 94 lab references from OWASP, PortSwigger, CWE, RFC, MDN, MITRE ATT&CK, NIST, HackTricks and other primary sources.
- **Real browser victim** for XSS/postMessage/upload labs through a loopback-only Selenium/Chromium bot.
- **Server-side validation, CSRF protection, CSP and security headers.**
- **Automated exploit tests** against every lab process plus platform integration tests against a temporary database.

---

## Quick start

```bash
git clone <your-local-remote> redvault   # or use the existing project directory
cd redvault

python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

python3 run.py
```

Open **http://127.0.0.1:8000**: the dashboard loads directly, with no account creation and no password. The local operator (`operator`, rename it with `REDVAULT_OPERATOR`) is created in the SQLite database on first start.

For a sandboxed lab runtime, install `bubblewrap`; for the browser-based XSS labs, install Chromium and `chromedriver`. Full instructions: [INSTALL.md](INSTALL.md).

### Tests

```bash
# Standalone exploit-level tests: one real process per lab
python3 -m pytest tests/test_labs.py -q

# Platform integration tests: isolated temporary database
python3 -m pytest tests/test_platform.py -q

# Everything (each module in its own interpreter)
python3 run_tests.py
```

The tested suite is **118 tests** in four modules: 61 Phase 1–2 lab tests, 34 Phase 3 lab tests, 13 platform tests and 10 Phase 3 platform tests. Each module runs in its own process because `REDVAULT_DATA` is read once at import time; `run_tests.py` handles that. Platform tests use a temporary `REDVAULT_DATA` directory and do not touch the operator database.

Each Phase 3 lab was additionally verified by an independent exploit script (34/34 passing) before its test was added to the suite.

---

## Project layout

```text
redvault/
├── app/
│   ├── main.py            FastAPI factory, lifespan, security middleware
│   ├── web.py             HTML routes
│   ├── api.py             UI JSON API (labs, hints, flags, notes)
│   ├── internal.py        Lab callbacks and browser bot bridge
│   ├── lab_manager.py     Process lifecycle, ports, bwrap, prlimit
│   ├── flags.py           HMAC flag derivation and objective gating
│   ├── content.py         Manifest discovery, validation and seeding
│   ├── security.py        Sessions, CSRF, bcrypt, flash, rate limits
│   ├── models.py          SQLAlchemy schema
│   ├── services/          Progress, XP and achievements
│   ├── templates/         Jinja2 UI
│   └── static/            CSS and vanilla JS
├── content/
│   ├── academy/           Markdown articles with frontmatter
│   ├── cves.json          Curated real CVE index
│   ├── glossary.json      Terminology
│   ├── paths.json         Learning paths
│   └── tools.json         Tool library
├── labs/
│   ├── _shared/labkit.py  Shared lab runtime
│   ├── _shared/serve_lab.py Escaped-template dev runner for tests
│   └── <slug>/app.py      Real vulnerable application
│       └── manifest.json  Metadata, flags, hints, solution, refs
├── tests/
│   ├── conftest.py        Lab process fixture
│   ├── test_labs.py       Exploit tests for all 61 labs
│   └── test_platform.py   Auth, CSRF, flags, lifecycle, UI
├── data/                  Runtime database, secret, lab state (gitignored)
├── docs/                  Supplementary notes
├── README.md
├── INSTALL.md
├── ARCHITECTURE.md
├── SECURITY.md
├── CHANGELOG.md
├── ROADMAP.md
├── requirements.txt
└── run.py
```

---

## How a lab works

```text
Browser
  │  POST /api/challenges/<slug>/start  (CSRF token)
  ▼
FastAPI platform ── allocates port, derives flags ──► lab process (127.0.0.1:42000+)
  │                                                        │
  │  status/reset/stop                                     │ objective callback
  │◄───────────────────────────────────────────────────────┘
  │
  └─ server-side flag validation → progress, XP, achievements
```

1. The operator starts a challenge. The platform allocates a loopback port and spawns the lab under `bwrap` when available.
2. The lab receives only its own derived flags and a per-session callback token.
3. The operator attacks the lab UI/API directly.
4. A stateful lab calls `/internal/lab-callback` to record the objective; the token is validated and tied to the active session.
5. The operator submits a flag to the platform. The platform derives the expected value and checks the objective state server-side.
6. Reset stops the process, clears objectives for that session, wipes state and starts a clean instance.

Read [ARCHITECTURE.md](ARCHITECTURE.md) for the full design and [SECURITY.md](SECURITY.md) for the threat model and limitations.

---

## Documentation

- [INSTALL.md](INSTALL.md) — prerequisites, setup, environment variables, troubleshooting.
- [ARCHITECTURE.md](ARCHITECTURE.md) — components, data model, lab runtime, flag flow.
- [SECURITY.md](SECURITY.md) — isolation, authentication, flag handling, known limitations.
- [ROADMAP.md](ROADMAP.md) — actual counts versus targets and remaining catalog work.
- [CHANGELOG.md](CHANGELOG.md) — release history.

---

## Safety and ethics

- Use REDVAULT only on infrastructure you own or are explicitly authorized to test.
- Keep the platform and lab ports on loopback. Do not reverse-proxy them to the internet.
- Labs are intentionally vulnerable; do not reuse their code in production.
- Do not point lab payloads, scanners or callbacks at third-party systems.
- Treat the flag database, master secret and session cookies as sensitive local data.
- Reset lab state after experiments.

## License

No license file is included in this repository. Treat the code as private and all rights reserved until a license is chosen by the owner.
