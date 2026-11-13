# Security Model

REDVAULT is a local training environment. It contains intentionally vulnerable applications. This document describes what the platform protects, what it does not protect, and how to operate it without turning a lab into an incident.

## 1. Threat model

### In scope

The intended deployment is one trusted operator on a personal Linux machine:

- The operator owns the host and the repository.
- The platform and labs bind only to loopback.
- Lab applications are project code; they are intentionally vulnerable but not assumed to be hostile.
- The operator may run untrusted *payloads* against labs, but not untrusted lab *implementations*.
- The local OS user account is trusted.

### Out of scope

REDVAULT is **not** designed to:

- Host labs for multiple untrusted users.
- Expose challenge ports to a LAN, VPN, container network or the internet.
- Safely execute third-party code from a random lab repository.
- Resist a local attacker who already has the operator's UID.
- Provide production-grade secrecy against root, memory scraping or a compromised host.
- Replace a VM, container runtime or dedicated assessment workstation.

If you need hostile multi-user isolation, run each lab in a separate VM or a hardened container with a network namespace, read-only root, dropped capabilities and cgroup limits. The current `bwrap` wrapper is not that boundary.

## 2. Network exposure

- `run.py` defaults to `REDVAULT_HOST=127.0.0.1`.
- Lab ports are allocated in `42000–42999` and bound to `127.0.0.1` by default (`REDVAULT_LAB_BIND`).
- The platform is not designed to run behind a reverse proxy; asset paths and loopback assumptions are absolute.
- Do not set `REDVAULT_HOST=0.0.0.0`. The platform has no login: anyone who reaches it is the operator. Exposing it publishes your progress, hints, walkthroughs and the ability to submit flags and reset labs.
- Do not port-forward, tunnel or publish lab ports to the internet.

### Opt-in: attacking the labs from a second machine on the LAN

There is a supported way to let another computer on the same network hit the labs directly, like a TryHackMe room without a VPN, while keeping the platform itself on loopback:

```bash
REDVAULT_LAB_BIND=0.0.0.0 \
REDVAULT_LAB_PUBLIC_HOST=192.168.1.10 \
python3 run.py
```

- Labs bind to every interface and their URLs are advertised as `http://192.168.1.10:<port>/`, so the second machine opens exactly the address shown in the lab card.
- The platform stays on `127.0.0.1:8000`; the second machine cannot reach the dashboard, hints or the flag submission.
- The lab footer switches from `LOCAL ONLY` to `LAN SHARED` so the mode is visible on the target itself.

**Accepted risk.** Every lab is intentionally vulnerable and now reachable by whoever shares the network. The `bwrap` sandbox confines a successful exploit to the lab process (read-only system view, private `/tmp`, only `/state` writable), and flags are injected per process, but this is *not* a hostile multi-user boundary. Use it only on a trusted, isolated network (your home LAN, a lab VLAN, a hotspot dedicated to the exercise), never on shared or public Wi-Fi, and stop the labs when you are done.

### Load and runaway brute force

A brute force against a lab does not reach the router: source and destination are the same host, so the traffic never leaves the machine. Measured with `scripts/bruteforce_load.py`, a realistic OTP brute force sustains ~400 req/s (~23 Mbps) against the lab, and the limiting factor is the lab's single-process Flask, not the network.

What the platform does about it:

- `REDVAULT_LAB_MAX_LIFETIME` (default 2 h) stops a forgotten lab even if it is still active.
- Traffic from another machine counts as activity, so a lab is not reaped mid-exercise, and an abandoned one is not kept alive by it either.
- Sustained load above 300 req/s is logged in the lab log and marked `X-Redvault-Traffic: warn`; above 1500 req/s the first occurrence is recorded as a `lab_abuse` activity entry.

None of that protects the *router* from a lab that is itself used as an SSRF pivot (see above). The defence there is network isolation, not rate limiting.

A single uncovered service on that network is enough for an attacker to pivot. If the second machine needs the full experience — hints, flag submission, progress — put it in front of a reverse proxy that terminates authentication; the platform itself does not provide one.

Check listeners:

```bash
ss -ltnp | grep -E ':(8000|42[0-9]{3})'
```

Port 8000 should show `127.0.0.1`. Lab ports show `127.0.0.1` by default and `0.0.0.0` only after the explicit opt-in above.

## 3. Authentication and session security

| Control | Implementation |
| --- | --- |
| Password storage | bcrypt, cost 12; max 72 bytes (bcrypt limit) |
| Password policy | Minimum 10 characters; no forced composition/rotation |
| Session token | 48 random bytes, SHA-256 hash stored server-side |
| Cookie | `rv_session`, `HttpOnly`, `SameSite=Lax`, 72-hour TTL |
| CSRF | Per-session token in a meta tag and hidden forms; constant-time check |
| Login throttling | 8 failures per IP + username in 5 minutes (in-memory) |
| Post-login redirect | Local absolute paths only; `//host` is rejected |
| Password change | Revokes all other sessions; issues a new session |
| Progress reset | Requires typing `RESET MY LAB` and a valid CSRF token |

The cookie is not marked `Secure` because the platform is HTTP on loopback. Do not run it over plain HTTP on a network.

There is no MFA, no account recovery service and no administrator role in the platform. The first setup account is the local operator. Anyone with filesystem access to `data/redvault.db` can replace the password hash while the platform is stopped.

### Login rate limiting caveats

The failure buckets are in process memory. Restarting the platform clears them, and multiple workers would not share state. Run one worker. The limit is a speed bump for a local UI, not a distributed brute-force defense.

## 4. Web hardening

The middleware sets, for non-development routes:

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
Content-Security-Policy:
  default-src 'self';
  script-src 'self';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data:;
  font-src 'self';
  connect-src 'self';
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self'
```

Notes and limits:

- `style-src 'unsafe-inline'` is allowed for the UI's inline layout styles. Scripts remain external and same-origin.
- `connect-src 'self'` prevents the platform page from calling arbitrary origins, but does **not** constrain the intentionally vulnerable labs.
- There is no HSTS because the platform is HTTP-only on loopback.
- There is no `TrustedHostMiddleware`; do not expose the app behind a proxy that forwards arbitrary Host headers.
- CORS is not enabled. The JSON API is same-origin and requires the CSRF header for mutations.

### Cross-port cookie scope

Cookies are scoped by host, not port. A browser talking to `127.0.0.1:42000` (a lab) and `127.0.0.1:8000` (the platform) treats both as the same host. `rv_session` is `HttpOnly`, so lab JavaScript cannot read it, but a lab-origin XSS can still cause the browser to send requests to the platform.

The platform mitigations are:

- CSRF tokens on state-changing requests.
- JSON content type plus a custom `X-CSRF-Token` header for API mutations, which triggers CORS preflight and is blocked without a permissive CORS policy.
- No CORS response headers, so cross-origin reads fail.
- `frame-ancestors 'none'` and `X-Frame-Options: DENY` to prevent framing the platform UI.

Do not weaken these controls to make a lab easier. If you need stronger origin separation, use a separate hostname per lab and a browser profile dedicated to REDVAULT.

## 5. Flag handling

Flags are derived, not stored in plaintext:

```text
HMAC-SHA256(data/secret.key, "flag:<slug>:<flag_key>")
→ base32 token → RV{<prefix>_<token>}
```

- `data/secret.key` is generated with 48 random bytes and `chmod 0600`.
- The `flags` table has metadata only; no value column.
- The challenge catalog, detail page, hints and walkthrough never receive derived values.
- Lab processes receive only their own flags through `LAB_FLAGS`.
- Submissions store a SHA-256 hash and a masked value, not the raw flag.
- Validation uses `hmac.compare_digest`.
- Objective-gated flags additionally require `ObjectiveState` written by a lab callback authenticated with a per-session random token.

### Residual risks

- A local process with the operator's UID may read `data/secret.key` if it can access the project directory. The threat model trusts local code; use a dedicated OS account if that is not acceptable.
- A compromised lab process can read its own flags. That is by design.
- If `secret.key` is leaked, all current flags can be derived. Rotate it by stopping the platform and replacing the file; all existing flag values change, and old submissions remain in the audit history.
- The database contains password hashes, session hashes, objective evidence and notes. Protect it like a credential store.

## 6. Lab process isolation

When `bubblewrap` is available, `lab_manager.py` runs each lab with:

- Read-only binds of `/usr`, `/bin`, `/lib`, `/lib64`, `/etc`.
- Read-only bind of the lab directory at `/lab`.
- Read-only bind of `labs/_shared` at `/shared`.
- A private writable state directory at `/state`.
- `tmpfs` at `/tmp` and `/run`.
- A new `/proc` and `/dev`.
- `--unshare-pid`, `--new-session`, `--die-with-parent`.
- `prlimit`: core dumps disabled, 768 MiB address space, 512 file descriptors, 64 MiB file size.
- A minimal environment; the operator's home directory is not bound into the sandbox.

This reduces accidental access to the home directory and gives each lab a private process tree and writable state. It does **not**:

- Create a network namespace or block outbound network access.
- Drop the operator UID or apply a seccomp filter.
- Limit CPU with cgroups.
- Protect against a kernel or bwrap escape.
- Make malicious lab code safe.

If `bwrap` is unavailable, the lab runs as a native process with `prlimit` only and can access files readable by the operator. The Environments page warns about this. Install `bubblewrap` before using labs you did not write.

Labs are never run as root. Do not run the platform as root.

### Cleanup

Stopping, resetting or shutting down a lab terminates its process group and removes its state directory. The idle reaper stops labs after 45 minutes of inactivity by default. If the platform crashes, `reconcile_startup()` marks stale sessions stopped; orphan processes should be killed with the platform's process group.

## 7. Browser bot

The Selenium bot is a controlled victim for XSS and client-side labs.

- It only runs when `REDVAULT_BOT=1`.
- It accepts `http`/`https` URLs whose hostname is an IP literal, whose address is loopback, and whose port exactly matches the requesting lab.
- It rejects userinfo, external hosts and other ports.
- Cookies are name/value filtered, length-bounded and never returned to the caller.
- It does not return page HTML, DOM, cookies or network bodies.
- A global lock serializes runs; the last error is exposed as status.
- Chromium runs with `--no-sandbox` because the execution environment requires it. That is a significant hardening gap; the bot must only visit disposable local labs.

Do not expose the bot endpoint or run it against third-party sites. The URL validator is intentionally strict, but defense in depth should not rely on it alone.

## 8. SSRF and internal trust in labs

Some labs intentionally contain SSRF, open redirects or internal endpoints. These are contained in their own process and port. The platform's internal callback endpoints are protected by per-session tokens. For example, the SSRF lab's `/internal/flag` requires the header added by its own vulnerable fetcher, so direct unauthenticated loopback requests return 403; the exercise is to make the vulnerable service add it.

Labs are disposable. Reset them after testing. Do not reuse their code outside the lab.

## 9. Data protection

- The SQLite database stores user state, not challenge flag values.
- Notes may contain sensitive observations; they are stored in plaintext in SQLite and exported as JSON on request.
- The JSON export includes progress, submissions (flag keys/status), achievements, XP and notes. It does not include raw flag values or password hashes. Treat the export as personal data.
- Logs under `data/labs/logs/` may contain lab request paths and error output. They are local files; review before sharing.
- Back up `data/redvault.db` and `data/secret.key` securely. Losing the secret invalidates all current flag values.

## 10. Known limitations

1. **Not a container boundary.** `bwrap` plus `prlimit` is useful but not equivalent to a VM.
2. **Egress exists.** Labs can make outbound network connections. Do not run untrusted lab code.
3. **No CPU/cgroup limits.** A buggy lab can consume CPU until stopped.
4. **No TLS.** Cookies are not `Secure`; loopback only.
5. **Single-process rate limiting.** Restart clears login failures; multiple workers would not share limits.
6. **No migrations.** Schema upgrades require manual handling.
7. **No platform admin role/MFA.** The first account is the operator.
8. **Content trust.** Manifest references and code are not sandboxed at review time; a malicious manifest can include misleading links or dangerous lab code.
9. **Bot serialization.** One browser at a time; long runs delay other browser labs.
10. **Local OS trust.** Same-UID processes can read the database and secret.

## 11. Safe operation checklist

- [ ] Platform and labs bound to `127.0.0.1`
- [ ] `bubblewrap` installed and enabled
- [ ] Chromium/chromedriver versions match, bot enabled only when needed
- [ ] No reverse proxy or port forwarding
- [ ] Dedicated OS account if running third-party lab code
- [ ] `data/` permissions restricted to the operator
- [ ] Backups of `redvault.db` and `secret.key` stored securely
- [ ] Labs stopped/reset after use
- [ ] No real credentials or personal data entered into a lab
- [ ] Payloads and callbacks confined to assigned loopback targets
- [ ] Dependencies reviewed and updated deliberately

## 12. Incident response

If you suspect the platform or a lab was compromised:

1. Stop the platform and kill any remaining lab process groups.
2. Disconnect the host from untrusted networks if you deviated from loopback-only operation.
3. Preserve logs, but treat them as potentially sensitive.
4. Rotate `data/secret.key` (invalidates all current flags) and any credentials that appeared in lab data or notes.
5. Replace the database if you cannot account for modifications.
6. Review the bot's last error and the lab logs for unexpected targets.
7. Reinstall dependencies in a clean virtual environment.

## 13. Reporting a platform vulnerability

This is a private local project with no public security contact or bug bounty. If you find a vulnerability in the **platform core** (not an intentional lab flaw), do not publish exploit details before the owner has had a chance to fix it. Record the affected version, reproduction steps, impact and suggested fix in a private issue or note. Intentional vulnerabilities inside `labs/` are training content, not platform defects.

## 14. References

- [OWASP Application Security Verification Standard](https://owasp.org/www-project-application-security-verification-standard/)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [NIST SP 800-63B — Digital Identity Guidelines](https://pages.nist.gov/800-63-4/sp800-63b.html)
- [CWE-918 — Server-Side Request Forgery](https://cwe.mitre.org/data/definitions/918.html)
- [bubblewrap documentation](https://github.com/containers/bubblewrap)
- [RFC 6265 — HTTP State Management Mechanism](https://www.rfc-editor.org/rfc/rfc6265)
