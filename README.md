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
| Library documents | — | **135** | Imported (MIT) |
| Library payloads | — | **477** | With context |
| Document ↔ lab links | — | **291** | Implemented |
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
- **Learning paths** built from real catalog slugs: 18 structured tracks in three phases — Phase 1 (Web, API, Linux, Windows), Phase 2 (Active Directory, Network, Wireless, Hardware) and Phase 3 (Análise de Malware, Forense Digital, Cloud e Containers, Segurança Mobile, Exploit Development, Engenharia Reversa, Criptografia Aplicada, OSINT, Red Team, IoT e Embarcados) — with modules, gated units, theory, labs, graded assessments, capstones and internal certificates: **78 modules, 151 units, 788 activities**. Every Phase-2 and Phase-3 activity declares what it physically needs (`SOMENTE SOFTWARE`, `EQUIPAMENTO SIMULADO`, `EQUIPAMENTO OPCIONAL`, `EXIGE EQUIPAMENTO`), so nothing assumes you own a scope, a probe, a radio or a Windows domain — and a blocked exercise always accepts a software-only delivery. See [Learning paths](#learning-paths).
- **Biblioteca técnica (`/kb`)**, a searchable knowledge base next to the Academy: 1.279 imported documents (incl. the full HackTricks wiki, PT-BR edition), contextualised payloads, FTS5 full-text search, licence/commit provenance per document and links to platform labs. See [Library](#library-academy-20).
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

The tested suite is **153 tests** in seven modules: 61 Phase 1–2 lab tests, 34 Phase 3 lab tests, 13 platform tests, 10 Phase 3 platform tests, 15 knowledge-base tests, 3 LAN-mode tests and 5 traffic tests. Each module runs in its own process because `REDVAULT_DATA` is read once at import time; `run_tests.py` handles that. Platform and knowledge-base tests use a temporary `REDVAULT_DATA` directory and do not touch the operator database; the knowledge-base tests build a tiny local git repository instead of cloning anything.

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
│   ├── kb_models.py       Library schema (sources, categories, docs, payloads, links)
│   ├── kb_import.py       Offline importer with licence gate and provenance
│   ├── kb_hacktricks.py   HackTricks importer (CC BY-NC): SUMMARY tree, links, images
│   ├── kb_seed.py         Canonical category tree, payload extraction, lab links
│   ├── kb_search.py       FTS5 index and query builder
│   ├── kb_sync.py         Upstream change handling that preserves reviewed work
│   ├── kb_views.py        Library routes (/kb, reader, payloads, sources)
│   ├── kb_links.py        Challenge → documentation mapping
│   ├── security.py        Sessions, CSRF, bcrypt, flash, rate limits
│   ├── models.py          SQLAlchemy schema
│   ├── services/          Progress, XP and achievements
│   ├── templates/         Jinja2 UI
│   └── static/            CSS and vanilla JS
├── content/
│   ├── academy/           Markdown articles with frontmatter
│   ├── kb_licenses/       Upstream licence texts kept with the import
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
│   ├── test_kb.py         Library: import, licence gate, search, sync, UI
│   ├── test_kb_hacktricks.py  HackTricks import: NC licence, attribution, links, images
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

## Learning paths

`/learning-paths` turns the catalog into structured programmes. A path is a sequence of **modules** (stages with a gate), each holding **units** (disciplines) and **activities** (theory, exercises, labs, graded assessments, project milestones). Curricula are JSON files under `content/learning_paths/`, validated strictly on every start: a slug that does not exist in the platform aborts the seed instead of silently producing a dead link.

| Track | Focus | Platform labs | Practice requires |
| --- | --- | --- | --- |
| Web Application Pentesting | The full web catalog | 61 | software only |
| API Security | BOLA/BFLA, JWT, OIDC, GraphQL | 26 | software only |
| Linux Security | privilege escalation, GTFOBins | 1 | software only |
| Windows Security | tokens, ACLs, DLL hijacking, LOLBAS | 0 | your own Windows VM |
| Active Directory | Kerberos, ACLs, AD CS, domain persistence | 0 | your own domain lab |
| Network Pentesting | services, pivoting, segmentation | 0 | software + own VMs for SMB/pivoting |
| Wireless Security | 802.11, PSK, 802.1X, RFID/BLE/sub-GHz | 0 | a Wi-Fi adapter with monitor/injection |
| Hardware Hacking | debug interfaces, firmware, signals, SDR | 0 | software (75%+); devices only where marked |
| Análise de Malware | triage, static, dynamic, YARA/Sigma report | 0 | software only (own binaries or samples you supply) |
| Forense Digital | custody, artifacts, memory, network, timeline | 0 | software only (your own host/images) |
| Cloud e Containers | IAM, RBAC, containers, serverless posture | 0 | software only (no cloud account needed) |
| Segurança Mobile | manifest, decompilation, Frida, components | 0 | software; dynamic steps need an AVD/device |
| Exploit Development | stack, canary, heap, arbitrary write | 0 | software only (you compile the target) |
| Engenharia Reversa | Ghidra, angr, anti-debug, macros, stego | 0 | software only |
| Criptografia Aplicada | hash/MAC/KDF, RSA, PKI, JWT | 1 | software only |
| OSINT | scope, certificates, DNS, exposure, identity | 0 | software only (passive sources) |
| Red Team | rules of engagement, infra, C2, phishing | 0 | software; operations in your own lab VMs |
| IoT e Embarcados | Modbus, MQTT, OPC UA, firmware, BLE | 0 | software; BLE/radio need your own adapter |

Where the platform has no target for a track, the curriculum says so in the exercise text instead of pretending. The **Hardware** track is the clearest case: it is built so that most of it runs on a normal machine — board reconnaissance from photos and datasheets, firmware extraction and Ghidra analysis, protocol decoding with the sigrok `demo` device — and the four activities that need an instrument are tagged `EXIGE EQUIPAMENTO` with the minimum device, the cost, and the software exercise that covers the same concept. The same rule holds in **IoT**: the single activity that needs the board's UART accepts the written procedure as a valid delivery.

Every Phase-2 and Phase-3 track states in its own description what the platform does **not** provide — no malware lab, no forensic image, no cloud account, no device, no C2 infrastructure — and the exercises are built from binaries you compile, hosts you own, images you create and passive public sources. Phase 3 added **14 own KB documents** covering the gaps the audit found (YARA, fileless execution, chain of custody, Volatility, IAM, serverless, Ghidra, anti-debugging, binary protections, HMAC, PKI and three OSINT articles), each citing primary sources verified by HTTP.

Progress is persisted per activity (`not_started`, `in_progress`, `completed`, `review`) with notes, difficulties, results, favourites and revisit flags. Completion requires every required activity, not page visits; the capstone is a tracked `project` activity. Certificates issued at the end are **private study records**, not professional certifications, and say so on the document.

Commands:

```bash
python3 scripts/check_learning_paths.py        # validate every curriculum, report coverage
python3 scripts/build_path_<name>.py           # regenerate one curriculum from its script
python3 scripts/lp_phase3.py                   # shared emitter for the Phase-3 generators
```

## Library (Academy 2.0)

`/kb` is the technical library: a hierarchical catalog of techniques, a document reader, a payload library, and a provenance page. The original `/academy` (17 articles) is still there; the library is the part that scales.

| Surface | What it does |
| --- | --- |
| `/kb` | Library home: groups, categories, recently read, favourites, full-text search |
| `/kb/c/<slug>` | Category listing with breadcrumbs |
| `/kb/d/<slug>` | Document reader: table of contents, provenance block, payloads, references, related docs, linked labs |
| `/kb/payloads` | Payload library, filterable by technique and language, paginated |
| `/kb/sources` | Every upstream project with its licence, commit and sync state |

### Where the content comes from

Only projects whose licence allows reuse are imported, and the reuse terms are honoured exactly. Anything else is cited, never copied.

| Source | Licence | Handling |
| --- | --- | --- |
| PayloadsAllTheThings | MIT | imported verbatim (English), with commit, path and author |
| HackTricks (edição PT-BR, branch `pt`) | CC BY-NC 4.0 | imported verbatim (Portuguese) for **non-commercial use with attribution**: credits to Carlos Polop and the licence on every document |
| OWASP WSTG | CC BY-SA 4.0 | reference only |

This is enforced in code, not by convention. `kb_sources` carries two flags: `redistributable` (permissive licences such as MIT) and `noncommercial_reuse` (CC BY-NC, i.e. reuse allowed only non-commercially with attribution). The permissive importer still raises `ImportRefused` for anything that is neither, and the HackTricks importer (`app/kb_hacktricks.py`) only runs for a source flagged `noncommercial_reuse`. The upstream `LICENSE` is copied to `content/kb_licenses/` at import time so attribution survives even if the clone is deleted.

> **HackTricks is CC BY-NC 4.0.** It may not be used in a commercial or paid product and must keep attribution to Carlos Polop. REDVAULT imports the **Brazilian-Portuguese edition**, which the wiki keeps on the `pt` branch (`git clone --depth 1 --branch pt …`); the importer detects the language from the checked-out branch. Each document shows an "Uso não comercial" notice and the source commit. Imported images are localised under `app/static/hacktricks/` (git-ignored, recreated by the importer) because the app's CSP only allows same-origin images.

Every imported document stores `origin`, `source_path`, `source_url` (pinned to the commit SHA), `source_commit`, `content_hash` and `imported_at`.

### Importing or syncing

```bash
git clone --depth 1 https://github.com/swisskyrepo/PayloadsAllTheThings /tmp/patt
python3 scripts/import_kb.py --path /tmp/patt --rebuild-index
```

The real import into this installation produced: **135 documents, 64 categories, 477 payloads, 291 document↔lab links**, FTS5 index rebuilt over all 135 documents (commit `08ea40e77db3f42ef8f20c65196f3936a19b6c86`).

Re-running the import is safe. A document marked `reviewed` is never overwritten: the new upstream hash is recorded and `review_status` becomes `needs_review`, so a human decides.

### Translation states

Documents are `untranslated` → `translated` → `reviewed`. Imports arrive `untranslated` and the UI says so on the page and in the category listing. Imported payloads are never machine-translated: a payload is code, and translated code is broken code. Translations are written by hand into `body_md`; the original stays in `body_original_md`.

### Payload extraction

Fenced code blocks under a technique heading become payload rows only if they contain something runnable — SQL, HTML/JS, a request line, a shell command, an encoded value. Prose, markdown headings and credit lines are rejected, so the library does not fill up with blocks that only *describe* an attack.

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
- Imported library text keeps its upstream licence (see `content/kb_licenses/`); do not re-publish it under another licence.
- Reset lab state after experiments.

## License

No license file is included in this repository. Treat the code as private and all rights reserved until a license is chosen by the owner.
