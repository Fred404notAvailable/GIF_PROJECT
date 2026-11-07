---
name: owasp-top10-auditor
description: >
  Audits codebases against the OWASP Top 10 (2021 edition) via static code
  analysis. Use when a security review is requested, before a production
  release, after a vulnerability is reported, or during a compliance check.
  Activate when you need to systematically check for broken access control,
  injection, cryptographic failures, and the other eight OWASP categories.
  Do NOT use for runtime penetration testing or network-level security testing
  — this skill covers static code analysis only.
license: MIT
compatibility:
  - claude-3-5-sonnet
  - gpt-4o
metadata:
  origin: authored
  review_status: needs-human-review
allowed-tools:
  - read_file
  - write_file
  - run_command
---

# OWASP Top 10 (2021) Code Auditor

## When to Use / When Not to Use

### Use When
- A **security review** has been requested before a release or deployment.
- A **vulnerability** has been found and you need to assess blast radius across the codebase.
- Performing a **compliance check** (SOC 2, PCI-DSS, ISO 27001) that requires OWASP alignment.
- Onboarding a **new codebase** and you need a quick security baseline.
- The team wants to build a **security findings report** as a deliverable.

### Do NOT Use When
- You need **runtime penetration testing** (use Burp Suite, OWASP ZAP, or a professional pentest).
- You need **network-level scanning** (use Nmap, Nessus, etc.).
- You need **dependency vulnerability scanning** as the primary goal (use `npm audit`, `snyk`, `dependabot` directly).
- The ask is **secret scanning** in git history (use `trufflehog` or `gitleaks` directly).

---

## Procedure

Work through each OWASP Top 10 category in order. For each, identify the relevant files, perform the checks, and record findings.

---

### A01 — Broken Access Control

**What to look for:**
- Missing authorization checks on API endpoints / route handlers.
- IDOR (Insecure Direct Object Reference): using user-supplied IDs directly in DB queries without ownership check.
- Privilege escalation paths — can a regular user reach admin endpoints?
- CORS misconfiguration (`Access-Control-Allow-Origin: *` on authenticated endpoints).

**Code-level checks:**
1. List all route/controller methods. Verify each has an authorization decorator/middleware (`[Authorize]`, `requireAuth`, etc.).
2. Search for database queries that accept IDs from request parameters without a `WHERE userId = currentUser` guard.
3. Check CORS configuration; `*` on credentialed routes is a finding.
4. Verify role-based checks are enforced server-side, not just client-side.

---

### A02 — Cryptographic Failures

**What to look for:**
- Sensitive data transmitted over HTTP (not HTTPS).
- Weak hashing algorithms (MD5, SHA-1) for passwords.
- Hardcoded secrets, API keys, or passwords in source code.
- Insufficient key lengths or deprecated cipher suites.
- Sensitive data logged in plaintext.

**Code-level checks:**
1. Search for `http://` in internal API calls and configuration.
2. Grep for `MD5`, `SHA1`, `DES`, `RC4` in crypto/hashing code.
3. Grep for hardcoded strings matching secret patterns (see `references/deep-dive.md` for regexes).
4. Check password storage uses `bcrypt`, `argon2`, or `PBKDF2` with adequate rounds.
5. Check TLS version pinning — no TLS 1.0/1.1.

---

### A03 — Injection

**What to look for:**
- SQL injection via string concatenation in queries.
- NoSQL injection (MongoDB operator injection via `$where`, `$gt`, etc.).
- OS command injection (`exec`, `shell_exec`, `subprocess.call` with user input).
- LDAP injection, XPath injection, template injection.

**Code-level checks:**
1. Search for raw SQL construction using string interpolation or concatenation.
2. Verify all DB queries use parameterized queries or an ORM with safe query building.
3. Find all calls to `exec`, `spawn`, `subprocess`, `child_process` — check if user input is passed.
4. Check template engines for `{{user_input}}` rendered without escaping.
5. Verify NoSQL queries sanitize operators (`$where`, `$regex`, `$gt`).

---

### A04 — Insecure Design

**What to look for:**
- Missing rate limiting on authentication or sensitive endpoints.
- No account lockout after repeated failed logins.
- Sensitive operations (password reset, email change) lack re-authentication.
- Business logic flaws (e.g., negative quantities in cart, skipping payment steps).

**Code-level checks:**
1. Check authentication endpoints for rate limiting middleware.
2. Verify password reset flows: tokens are time-limited, single-use, and not predictable.
3. Review multi-step workflows — can steps be skipped by direct API call?
4. Check if financial/quantity fields have server-side range validation.

---

### A05 — Security Misconfiguration

**What to look for:**
- Default credentials left in place.
- Debug mode / stack traces enabled in production.
- Unnecessary features, ports, services, or pages enabled.
- Missing security headers (`Content-Security-Policy`, `X-Frame-Options`, `Strict-Transport-Security`).
- Verbose error messages exposing internal details.

**Code-level checks:**
1. Check environment configuration files — `DEBUG=True` or `NODE_ENV=development` committed.
2. Inspect HTTP response headers setup for missing security headers.
3. Search for `app.use(errorHandler())` in Node.js or similar — ensure it doesn't expose stack traces in production.
4. Check cloud/infra config (if present) for public S3 buckets, open security groups.

---

### A06 — Vulnerable and Outdated Components

**What to look for:**
- Dependencies with known CVEs.
- Unpinned or wildcard dependency versions.
- Abandoned packages with no security support.

**Code-level checks:**
1. Run `npm audit` / `pip-audit` / `dotnet list package --vulnerable` / `bundle audit`.
2. Check `package.json`, `requirements.txt`, or `.csproj` for versions pinned to `^latest` or `*`.
3. Cross-reference critical dependencies against [osv.dev](https://osv.dev).
4. Flag packages not updated in 2+ years with no stated EOL policy.

---

### A07 — Identification and Authentication Failures

**What to look for:**
- Weak or absent session management.
- JWT weaknesses: `alg: none`, weak secret, no expiry, no audience/issuer validation.
- Password requirements not enforced server-side.
- Multi-factor authentication absent for privileged operations.
- Session tokens not invalidated on logout.

**Code-level checks:**
1. Inspect JWT configuration: check `algorithms` whitelist (never accept `none`), expiry (`exp`), `iss`, and `aud`.
2. Check session invalidation on logout — not just client-side cookie deletion.
3. Verify password policy is enforced at the API layer, not just the UI.
4. Search for hardcoded JWT secrets or secrets sourced from low-entropy values.

---

### A08 — Software and Data Integrity Failures

**What to look for:**
- Dependencies fetched without integrity checks (no `package-lock.json` / `yarn.lock`).
- Deserialization of untrusted data without validation.
- CI/CD pipeline executing unsigned or unverified scripts.
- Auto-update mechanisms that don't verify signatures.

**Code-level checks:**
1. Confirm lock files are committed and used in CI builds.
2. Search for `pickle.loads`, `yaml.load(unsafe)`, `BinaryFormatter`, `ObjectInputStream` — deserialization danger zones.
3. Review CI pipeline files (`.github/workflows/*.yml`, `Jenkinsfile`) for `curl | bash` or pinned vs. unpinned action references.
4. Verify deserialization uses allowlists, not blocklists.

---

### A09 — Security Logging and Monitoring Failures

**What to look for:**
- Authentication events (success/failure) not logged.
- No alerting on repeated failures or anomalous access.
- Sensitive data (PII, passwords, tokens) written to logs.
- Log files writable by unprivileged processes.

**Code-level checks:**
1. Confirm login success, login failure, and logout are logged with IP, timestamp, and user ID.
2. Search log statements for accidental inclusion of `password`, `token`, `ssn`, `credit_card`.
3. Verify log level is not set to `DEBUG` in production (may expose sensitive data).
4. Check log destination configuration — are logs stored and retained?

---

### A10 — Server-Side Request Forgery (SSRF)

**What to look for:**
- User-supplied URLs fetched server-side (webhooks, URL preview, file import features).
- Internal metadata endpoints accessible (AWS `169.254.169.254`, GCP `metadata.google.internal`).
- Missing allowlist for outbound request destinations.

**Code-level checks:**
1. Find all HTTP client calls (`fetch`, `axios`, `HttpClient`, `requests.get`) — check if URL is user-controlled.
2. Verify URL allowlist/blocklist is enforced before making outbound requests.
3. Check if the app can be tricked into reaching `localhost`, `127.0.0.1`, or cloud metadata IPs.
4. Confirm that redirect-following is disabled or limited for user-supplied URLs.

---

## Checklist

| # | Category | Check | Status |
|---|---|---|---|
| A01 | Broken Access Control | All endpoints have authorization checks | YES / NO / N-A |
| A01 | Broken Access Control | No IDOR — ownership validated before data access | YES / NO / N-A |
| A01 | Broken Access Control | CORS not wildcard on authenticated endpoints | YES / NO / N-A |
| A02 | Cryptographic Failures | No MD5/SHA-1 for password hashing | YES / NO / N-A |
| A02 | Cryptographic Failures | No hardcoded secrets in source | YES / NO / N-A |
| A02 | Cryptographic Failures | Sensitive data encrypted at rest and in transit | YES / NO / N-A |
| A03 | Injection | All DB queries use parameterized statements | YES / NO / N-A |
| A03 | Injection | No OS command construction from user input | YES / NO / N-A |
| A04 | Insecure Design | Rate limiting on auth endpoints | YES / NO / N-A |
| A04 | Insecure Design | Password reset tokens are single-use and time-limited | YES / NO / N-A |
| A05 | Security Misconfiguration | Security headers configured | YES / NO / N-A |
| A05 | Security Misconfiguration | Debug mode off in production | YES / NO / N-A |
| A06 | Vulnerable Components | No high/critical CVEs in dependencies | YES / NO / N-A |
| A07 | Auth Failures | JWT `alg: none` rejected | YES / NO / N-A |
| A07 | Auth Failures | Sessions invalidated on logout | YES / NO / N-A |
| A08 | Software Integrity | Lock files committed and used in CI | YES / NO / N-A |
| A08 | Software Integrity | No unsafe deserialization | YES / NO / N-A |
| A09 | Logging Failures | Auth events logged with IP and timestamp | YES / NO / N-A |
| A09 | Logging Failures | No PII/secrets in log statements | YES / NO / N-A |
| A10 | SSRF | User-supplied URLs validated against allowlist | YES / NO / N-A |

---

## Common Pitfalls

| Pitfall | Example | Fix |
|---|---|---|
| **Trusting user input in SQL** | `"SELECT * FROM users WHERE id=" + req.params.id` | Use parameterized queries or ORM |
| **Hardcoded JWT secret** | `const secret = "mysecret123"` | Load from environment variable; enforce minimum 256-bit entropy |
| **Missing HTTPS enforcement** | No HSTS header, HTTP allowed in production | Add `Strict-Transport-Security` header; redirect HTTP → HTTPS |
| **Wildcard CORS** | `Access-Control-Allow-Origin: *` with `credentials: include` | Explicit origin allowlist; `*` and credentials are mutually exclusive |
| **Logging sensitive fields** | `logger.info("User login", { password })` | Scrub sensitive fields before logging |
| **Pickle deserialization** | `obj = pickle.loads(user_data)` | Never deserialize untrusted data with pickle; use JSON with schema validation |

---

## Worked Example: Node.js Express Endpoint Audit

**Target code:**
```javascript
app.get('/api/orders/:id', async (req, res) => {
  const order = await db.query(`SELECT * FROM orders WHERE id = ${req.params.id}`);
  res.json(order);
});
```

**Findings:**

1. **A01 — Broken Access Control (HIGH):** No authentication middleware. Any unauthenticated caller can access any order.
2. **A01 — IDOR (HIGH):** No check that the requesting user owns the order.
3. **A03 — SQL Injection (CRITICAL):** `req.params.id` is interpolated directly into the SQL string.

**Remediated code:**
```javascript
app.get('/api/orders/:id', authenticate, async (req, res) => {
  const order = await db.query(
    'SELECT * FROM orders WHERE id = $1 AND user_id = $2',
    [req.params.id, req.user.id]  // parameterized + ownership check
  );
  if (!order) return res.status(404).json({ error: 'Not found' });
  res.json(order);
});
```

See `references/deep-dive.md` for detailed reference material.
