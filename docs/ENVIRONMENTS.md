# Environments

How the Hotel Management System runs in each environment, how configuration differs between them, and how a change travels from a laptop to the live deployment.

> **Status:** parts of the target workflow depend on workstreams still in progress (CI, CD, S3, monitoring). Those items are marked **(planned)**. Update this file as they land.
>
> **This file lists variable names only. Never put real values in it.**

## 1. Overview

There are three ways to run the application:

| Mode | Purpose | How |
|---|---|---|
| Local development | Editing code with hot reload | Backend in a Python venv, Vite dev server for the frontend, your own PostgreSQL. Settings in `backend/.env` and `frontend/.env` (see `backend/.env.example` and `frontend/.env.example`). |
| **Test environment** | Try a change in a production-shaped, containerised stack **before** it reaches prod | Docker Compose. See "Running with Docker" in the README. |
| **Production** | The hosted application | Neon (database), Render (backend), Vercel (frontend) |

**The principle: same code, same backend image definition, different configuration.** There are no `if environment == "prod"` branches in the code. If the application behaves differently in two environments, the cause is a configuration value, and that is the first place to look.

## 2. Test and prod side by side

| | Test (local, Docker Compose) | Prod (hosted) |
|---|---|---|
| Database | `postgres:16.10` container with a named volume | Neon managed PostgreSQL |
| Backend | `backend/Dockerfile`, `prod` stage, built by Compose | The same Dockerfile, built by Render |
| Frontend | `frontend/Dockerfile` (nginx) built by Compose | Built from source by Vercel. `frontend/Dockerfile` is **not** used |
| Settings and secrets | Root `.env` (git-ignored) | Render and Vercel environment settings, GitHub Secrets |
| Demo data | Loaded (`--seed`) | **Never loaded** |
| Reachable from | `127.0.0.1` only, plain HTTP | Public internet, HTTPS |
| Database connection | `DATABASE_HOST=db` plus separate user, password and name | `DATABASE_URL` (Neon string) |
| `CORS_ORIGINS` | `http://localhost:<FRONTEND_PORT>` | The exact Vercel URL, no trailing slash |
| `VITE_API_BASE` | `http://localhost:<BACKEND_PORT>/api` | Render URL plus `/api` |
| How it is started or deployed | `docker compose ... up --build` | Platform deploy (automatic on merge to `main` once CD exists, **planned**) |

## 3. Production configuration (names only)

### Backend on Render

| Variable | Kind | Notes |
|---|---|---|
| `DATABASE_URL` | **Secret** | Neon **direct (non-pooled)** connection string with `sslmode=require`. It overrides the separate `DATABASE_*` fields, so those are not set in prod. |
| `JWT_SECRET` | **Secret** | Generated for prod only. At least 32 characters. Never reuse a test value. |
| `CORS_ORIGINS` | Config | The exact production frontend origin(s). Leaving it unset silently allows only localhost, so the browser reports CORS errors and the backend logs nothing. |
| `DB_POOL_MAX` | Config | Small, about 5, to respect free-tier connection limits. |
| `TAX_RATE` | Config | Business rule. Set it explicitly. |
| `PORT` | Supplied by Render | Read by `entrypoint.sh`. |
| `MIGRATIONS_DIR` | Set by the image | Do not set it on Render. |
| `SEED_FILE` and the `--seed` argument | **Not set in prod** | The prod image does not contain the seed file. |

Render health check path: `/api/health/ready`. Choose a region close to the database.

**(planned)** S3 credentials and bucket name, and the Sentry DSN. Exact names will be fixed when those workstreams land.

### Frontend on Vercel

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Build command / output | `npm run build` / `dist` |
| `VITE_API_BASE` | Render URL plus `/api`. **Public**, because Vite compiles it into the JavaScript that every visitor downloads. |
| `frontend/vercel.json` | Rewrites every path to `index.html` (**planned**) |

### GitHub

Deploy hook URL and other tokens live in GitHub Secrets (**planned**). Optionally use a GitHub Environment named `production` with a required approval.

## 4. Secrets rules

1. **Never commit** `.env` files, database dumps, keys or passwords. `.gitignore` and `.dockerignore` enforce this for the common cases, but they do not replace care.
2. **Generate secrets, do not invent them:**
   `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`
3. **Prod secrets are never the test secrets.** Generate fresh values for each environment.
4. **A secret that appears in a terminal command, chat, ticket, screenshot or commit is compromised.** Rotate it.
5. **Anything prefixed `VITE_` is public** and ends up in the browser. It must never hold a secret.
6. **Images contain no secrets.** Dockerfiles use `ENV` and `ARG` only for non-secret values. Check an image with `docker history --no-trunc <image>`.
7. **Rotation:** changing `JWT_SECRET` signs every user out. Changing the database password means changing it in Neon first, then in Render, then redeploying.

## 5. Moving a change to production

### Today

1. Branch from `main`. Nobody pushes directly to `main`.
2. Run the change in the **test environment** and check the behaviour you changed.
3. Run `pytest` (backend) and `npm run build` (frontend).
4. Open a pull request and get it reviewed.
5. Merge to `main`.
6. Deploy, then confirm `GET /api/health/ready` on the live backend and try a login, a booking and a payment.

### Target workflow (planned)

CI runs on every pull request (tests, frontend build, image builds, dependency audits), and branch protection requires it to pass. Merging to `main` triggers the Render deploy hook, Vercel deploys through its GitHub integration, and a smoke test calls `/api/health/ready` and fails the run if the backend is not ready. A `production` environment approval can gate the deploy.

### Pull request checklist

- [ ] Tried in the test environment, with a hard refresh on a deep link if the frontend changed
- [ ] `pytest` and `npm run build` pass
- [ ] No secrets, `.env` files or dumps in the diff
- [ ] New or changed settings are added to `.env.example`, the README tables and section 3 above
- [ ] Database changes are a new migration (see below)

### Database changes

- `entrypoint.sh` applies pending migrations every time the backend container starts, including in prod. A deploy that contains a migration therefore changes the Neon database during startup.
- Migrations are **forward-only**. Add a new numbered file. Never edit one that has already been applied anywhere.
- A failing migration stops the container before the server starts, by design. The hosting platform should keep the previous version running while the new one fails its health check. Confirm this against Render's current behaviour.
- Test migrations that change or delete data against seeded data in the test environment first, and take a backup or a database branch before applying them to prod.
- The runner does not lock, so run a single backend instance, or two instances starting together could race.

## 6. First admin and reference data (open items)

- Prod is **never** seeded. The demo seed contains accounts with publicly known passwords.
- The role rows (and other common initial data) currently exist only in the demo seed. The maintainer is moving common initialisation into migrations. Until that lands, a prod database has no roles, and registered users would get none.
- The first admin account will be created with a `create_admin` script that prompts for the password, so no credential ever appears in a file or an image (**planned**).
- Do not make the production deployment public until both items are in place.

## 7. Known differences between test and prod

These are the places where a passing test environment can still hide a prod problem. Check them when something works locally and fails live.

| Difference | Effect |
|---|---|
| Frontend serving: nginx container vs Vercel | Client-side route refresh works through `try_files` in one and `vercel.json` rewrites in the other. Headers and caching are configured separately. |
| PostgreSQL 16 container vs Neon | Version, extensions, TLS (`sslmode=require`), connection limits, and a pooled endpoint that breaks prepared statements. Use the direct connection string. |
| HTTP on localhost vs HTTPS public | Cookies, mixed-content and CORS issues appear only live. |
| Demo data vs an empty database | Features that assume existing rooms, payment methods or roles fail on a fresh prod database. |
| Free-tier cold starts and limits | The first request after idle can be slow or time out. |
| Secrets storage | A local `.env` vs the platform's settings. A missing prod variable fails differently from a missing local one. |

## 8. Rollback and incidents

The platforms' rollback features and limits change, so check their current documentation before relying on this list.

| Problem | Response |
|---|---|
| Bad backend deploy | Redeploy the last known good commit (the platform's rollback or redeploy feature, or revert the commit on `main`). Then check `/api/health/ready`. |
| Bad frontend deploy | Promote the previous Vercel deployment, or revert the commit. |
| Bad migration | Migrations are forward-only, so write a new corrective migration. For destructive mistakes, restore from the backup or database branch taken beforehand. |
| Leaked secret | Rotate it immediately (section 4), redeploy, and check the logs for misuse. |
| Backend down | Check the UptimeRobot alert (**planned**), the Render logs and Neon status, in that order. |

## 9. Related files

| File | Purpose |
|---|---|
| `README.md` ("Running with Docker") | Commands, settings tables and troubleshooting for the test environment |
| `docker-compose.yml`, `docker-compose.test.yml` | The Compose definitions |
| `backend/Dockerfile`, `backend/entrypoint.sh` | Backend image and start script |
| `frontend/Dockerfile`, `frontend/nginx.conf` | Frontend image and web server config |
| `.env.example`, `backend/.env.example`, `frontend/.env.example` | Templates for Compose, backend-only and frontend-only runs |