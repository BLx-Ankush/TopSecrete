# ALICE Assistant — Security Vulnerability Report

**Project:** Alice-group / Alice-project
**Scan source:** GitLab pipeline #2594367158 (status: SUCCESS)
**Scanners:** SAST (Semgrep/Bandit), Dependency Scanning (Gemnasium), Secret Detection
**Total findings:** 127 — all in `DETECTED` state
**Report date:** 2026-06-11

> **Note:** These findings come from the security-scanning pipeline (now merged to `main`). Once the `main` pipeline completes, they promote into the project Vulnerability Report. Full vulnerability management/automation requires a GitLab **Ultimate** license.

---

## Summary by severity

| Severity | Count |
|---|---|
| Critical | 1 |
| High | 77 |
| Medium | 25 |
| Low | 3 |
| Info | 21 |
| **Total** | **127** |

**By type:** SAST 85 · Dependency Scanning 42

---

## CRITICAL (1)

### C-1 — Prototype Pollution via `parse()` in `flatted`
- **CVE:** CVE-2026-33228 · GHSA-rf6f-7fwh-wjgh
- **Type:** Dependency Scanning · **CWE:** Prototype Pollution
- **Location:** `ALICE/agent-starter-react/pnpm-lock.yaml` (transitive dependency `flatted`)
- **Description:** `flatted.parse()` uses attacker-controlled JSON string values as direct array index keys without validating they are numeric. A key of `__proto__` resolves to `Array.prototype`, which is then assigned onto the output object, leaking a live prototype reference. Any later write to that property pollutes the global prototype chain.
- **Impact:** Global prototype pollution -> potential Denial of Service or remote code execution in downstream code.
- **Remediation:** Upgrade `flatted` to a patched version (confirm exact version from the GHSA advisory before bumping). Since it is transitive, you may need to update the parent package or add a `pnpm` override.

---

## HIGH (77)

### Cluster A — OS Command Injection in Python (CWE-78) — ~55 findings · SAST (Bandit)

The largest and most operationally significant risk. ALICE invokes external processes using `subprocess` with `shell=True` and/or dynamic command content. Confirmed pattern in code, e.g.:

```python
subprocess.Popen(["start", app_name], shell=True)   # os_adapter.py
```

- **CWE:** CWE-78 · **OWASP:** A03:2021 - Injection
- **Bandit rules:** B602 (`subprocess` + `shell=True`), B603 (subprocess without shell), B604, B605, B606 (dynamic content in process spawn)
- **Impact:** If any value reaching these calls is derived from user/voice input, an attacker can execute arbitrary OS commands on the host running ALICE. For a desktop assistant that controls apps, windows, and the system, this is the highest-impact code-level risk.

**Affected files and line numbers:**

| File | Lines |
|---|---|
| `ALICE/Alice_code/alice_personal_safe.py` | 20, 613, 621, 629, 650, 683, 693, 711, 882, 884, 886, 889, 926, 990, 993, 1001, 1003, 1180-1186, 1214 |
| `ALICE/Alice_code/os_adapter.py` | 146, 202, 210, 218, 238, 245, 252, 261, 276, 279, 282, 297, 303, 309, 314, 317, 329, 332, 335 |
| `ALICE/Alice_code/alice_system_controller.py` | 106, 111, 115, 119, 126, 133-136, 139, 160, 254, 332 |
| `ALICE/Alice_code/Alice_window_CTRL.py` | 89, 96, 144 |
| `ALICE/Alice_code/Alice_file_opener.py` | 69, 71 |
| `ALICE/alice_trigger.py` | 17 |

- **Remediation:** Use `shell=False` with an argument list, or use a proper launcher API. Validate/allowlist any input that reaches the call. Where shell features (pipes, globbing, env expansion) are genuinely needed, implement them in Python rather than via the shell.
- **Functional note:** Some of these calls perform ALICE's core actions. A correct `shell=False` rewrite is behavior-neutral for legitimate input, but commands relying on shell syntax must be rewritten and tested individually.

### Cluster B — Insecure Deserialization via `pickle` (CWE-502) — 1 finding · SAST
- **Location:** `ALICE/Learning/alice-rl-project/src/memory/long_term_memory.py:222`
- **CWE:** CWE-502 · **OWASP:** A08:2021 - Software & Data Integrity Failures · Bandit B301
- **Description:** ALICE's RL long-term memory uses `pickle`. Loading a maliciously crafted pickle file can execute arbitrary code during deserialization.
- **Impact:** Code execution if an attacker can supply or tamper with the memory file.
- **Remediation:** Replace `pickle` with a safe format (JSON, or a schema-validated serializer). Existing pickle memory files would need migration to the new format.

### Cluster C — High-severity dependency CVEs (`pnpm-lock.yaml`) — ~21 findings · Dependency Scanning

All in `ALICE/agent-starter-react/pnpm-lock.yaml`. Notable items:

| Package | Issue | CVE |
|---|---|---|
| Next.js | Middleware/proxy auth bypass (dynamic route injection) | CVE-2026-44574 |
| Next.js | Middleware bypass via segment-prefetch routes | CVE-2026-44575 |
| Next.js | Middleware bypass (Pages Router i18n) | CVE-2026-44573 |
| Next.js | Segment-prefetch bypass incomplete-fix follow-up | CVE-2026-45109 |
| Next.js | SSRF via WebSocket upgrade | CVE-2026-44578 |
| Next.js | DoS via connection exhaustion (Cache Components) | CVE-2026-44579 |
| Next.js | DoS - Server Components deserialization | GHSA-8h8q-6873-q5fj / GHSA-q4gf-8mx6-v5v3 / GHSA-h25m-26qc-wcjf |
| Next.js | Unbounded postponed resume buffering DoS | CVE-2026-27979 |
| Next.js | Unbounded next/image disk cache | CVE-2026-27980 |
| node-tar | Hardlink path traversal | CVE-2026-29786 |
| node-tar | Symlink path traversal (drive-relative) | CVE-2026-31802 |
| node-tar | Hardlink path traversal (resolution mismatch) | CVE-2026-24842 |
| node-tar | Arbitrary file read/write via symlink chain | CVE-2026-26960 |
| node-tar | Race condition via Unicode collisions (APFS) | CVE-2026-23950 |
| lodash | Code injection via `_.template` imports keys | CVE-2026-4800 |
| minimatch | ReDoS (multiple variants) | CVE-2026-26996, CVE-2026-27903, CVE-2026-27904 |
| picomatch | ReDoS via extglob quantifiers | CVE-2026-33671 |
| flatted | Unbounded recursion DoS | CVE-2026-32141 |

- **Remediation:** Update each package to its advisory-confirmed patched version. A major Next.js bump may introduce frontend breaking changes - do this in an isolated MR with a build + smoke test.

---

## MEDIUM (25)

### SAST
| ID | Issue | Location | CWE |
|---|---|---|---|
| M-S1 | Weak PRNG (`Math.random()`) for security-sensitive value | `agent-starter-react/app/api/connection-details/route.ts:55, 56` | CWE-338 |
| M-S2 | Weak PRNG (`Math.random()`) | `agent-starter-react/components/welcome-backup.tsx:338, 339, 340, 344, 350, 351` | CWE-338 |
| M-S3 | Broken/risky crypto algorithm (MD5/SHA1) | `ALICE/Alice_code/alice_semantic_vision.py:188` | CWE-327 |

- **Remediation:** Use `crypto.randomBytes()` for security-relevant randomness; use SHA-256+ (or Argon2id/PBKDF2 for passwords). If the weak hash is used as a cache/dedup key, changing it invalidates existing keys.

### Dependency Scanning (in `pnpm-lock.yaml`)
| Package | Issue | CVE |
|---|---|---|
| Next.js | CSRF bypass via `origin: null` (Server Actions) | CVE-2026-27978 |
| Next.js | Dev HMR websocket CSRF bypass (`origin: null`) | CVE-2026-27977 |
| Next.js | XSS in `beforeInteractive` scripts | CVE-2026-44580 |
| Next.js | XSS via CSP nonce reflection | CVE-2026-44581 |
| Next.js | HTTP request smuggling in rewrites | CVE-2026-29057 |
| Next.js | Cache poisoning in RSC responses | CVE-2026-44576 |
| Next.js | Unbounded memory via PPR resume endpoint | CVE-2025-59472 |
| Next.js | DoS - Image Optimization API (local) | CVE-2026-44577 |
| Next.js | DoS - Image Optimizer `remotePatterns` | CVE-2025-59471 |
| js-yaml | Prototype pollution in merge (`<<`) | CVE-2025-64718 |
| lodash | Prototype pollution in `_.unset`/`_.omit` | CVE-2026-2950 |
| lodash | Prototype pollution in `_.unset`/`_.omit` | CVE-2025-13465 |
| brace-expansion | DoS via zero-step sequence | CVE-2026-33750 |
| picomatch | Method injection in POSIX classes | CVE-2026-33672 |
| postcss | XSS via unescaped `</style>` | CVE-2026-41305 |
| node-tar | Arbitrary file overwrite / symlink poisoning | CVE-2026-23745 |

---

## LOW (3) — Dependency Scanning (`pnpm-lock.yaml`)
| Package | Issue | CVE |
|---|---|---|
| ajv | ReDoS when using `$data` option | CVE-2025-69873 |
| Next.js | Cache poisoning via `_rsc` collisions | CVE-2026-44582 |
| Next.js | Middleware redirect cache poisoning | CVE-2026-44572 |

---

## INFO (21) — SAST (Bandit B101, CWE-754)

Use of `assert` in non-test contexts (asserts are stripped under Python optimization).

- **Locations:** `ALICE/Alice_code/test_alice_universal.py` (lines 97, 129, 139, 140, 167, 168, 169, 172, 173, 187, 188, 189, 217-220, 233, 244, 245, 273, 274) and `ALICE/Alice_code/test_alice_tools_automated.py` (lines 40, 41, 42).
- **Impact / note:** These are test files - minimal runtime risk to ALICE. Lowest priority.

---

## Recommended remediation order

1. **C-1 `flatted`** — patch the dependency.
2. **Cluster A — command injection (~55)** — highest real-world risk; fix per-call with `shell=False` + input validation, test each.
3. **Cluster B — `pickle`** — switch to JSON/safe serializer + migrate memory files.
4. **Cluster C — Next.js / node-tar / lodash** — update to patched versions (isolated MR + smoke test).
5. **Medium crypto/PRNG** — `crypto.randomBytes()`, SHA-256+.
6. **Info asserts** — optional cleanup.

---

## Important caveats

- **Dependency fix versions are intentionally not listed.** Always confirm the patched version from the linked GHSA/CVE advisory or the package registry before upgrading - do not infer version numbers.
- **Reachability:** These are SAST + Dependency Scanning findings. Reachability analysis was not applied, so treat the command-injection findings as requiring manual confirmation of whether user/voice input actually reaches each `subprocess` call.
- **Functional impact:** Command-injection, pickle, and major dependency upgrades can change ALICE's behavior and require testing.
