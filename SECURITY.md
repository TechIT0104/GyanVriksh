# Security Posture — GyanVriksh

> **Demo build notice.** This is a hackathon **demonstration** build. It ships with a
> small, **synthetic** dataset (Bharat Chemicals "Unit-3") and runs its databases
> locally in Docker — it is **not** connected to any real plant system or production
> data. All security controls below are nonetheless **fully implemented** in the code;
> a production rollout would additionally enable TLS, a secrets manager, and a
> Redis-backed rate limiter (noted inline).

## Authentication & authorization
- **Passwords** are hashed with **bcrypt** (per-user salt); plaintext is never stored.
- **Sessions** use signed **JWT (HS256)** with an expiry (`JWT_EXPIRE_HOURS`). The
  decoder pins `algorithms=["HS256"]`, preventing `alg=none` / algorithm-confusion attacks.
- **Role-based access control (RBAC)**: every API area is guarded by a `require(area)`
  dependency; a role that lacks permission gets `403`. Roles: plant_manager,
  maintenance_engineer, field_technician, compliance_auditor, admin.

## Transport & browser hardening
- Security headers on every response: `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY` (clickjacking), `Referrer-Policy: no-referrer`,
  `Permissions-Policy`, `Strict-Transport-Security` (HSTS, active under HTTPS),
  `Cache-Control: no-store`.
- **CORS** is restricted to explicit origins (no wildcard) with credentials.

## Abuse & injection protection
- **Login brute-force**: per-IP sliding-window rate limiter (10 attempts / 5 min → `429`).
  In-memory for the demo; back it with Redis in production.
- **Cypher injection**: the graph query endpoint rejects destructive Cypher
  (`delete`, `detach`, `remove`, `drop`, `create user`, `set password`).
- **Uploads**: constrained by `MAX_UPLOAD_SIZE_MB` and accepted document types.

## Secrets & supply chain
- `.env` is **git-ignored**; a placeholder `.env.example` documents required variables.
- **No real credentials** are committed. GPU-server credentials were scrubbed to
  `<GPU_USER>@<GPU_HOST>` placeholders.
- The app boots with a **weak-secret guard**: it logs a loud warning if `JWT_SECRET`
  is short/default or if default database credentials are detected.

## Data privacy (why this design matters for industry)
- The platform can run **fully on-premise** with a **local LLM (Ollama)** — plant
  documents and queries **never leave the site**. This is deliberate: industrial
  knowledge is sensitive, and many plants cannot send data to third-party clouds.

## Hardening checklist before a real deployment
1. Set a strong random `JWT_SECRET` (`openssl rand -hex 32`) and rotate DB/MinIO creds.
2. Terminate TLS at a reverse proxy; keep HSTS on.
3. Move the rate limiter and sessions to Redis; add per-user lockout + audit alerts.
4. Put databases on a private network; never expose Postgres/Neo4j/Qdrant publicly.
5. Add dependency scanning (pip-audit / npm audit) to CI.
