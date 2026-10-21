# Hotel Management System

A full-stack hotel management web application with role-based access for **admins, managers, staff and guests**.
It covers rooms and room types, bookings with an approval workflow, check-in and check-out, services, invoicing and
payments, staff and maintenance management, and reports.

> Built as a Cloud Computing & DevOps course project (School of Computer Engineering, 5th semester).
> This repository contains the complete application. Docker, CI/CD and cloud deployment are the next phase (see [Roadmap](#roadmap)).

---

## Table of contents

1. [Features](#features)
2. [Tech stack](#tech-stack)
3. [Prerequisites](#prerequisites)
4. [Quick start](#quick-start)
5. [Demo accounts](#demo-accounts)
6. [Configuration](#configuration)
7. [Running the tests](#running-the-tests)
8. [How the system behaves](#how-the-system-behaves)
9. [API overview](#api-overview)
10. [Project structure](#project-structure)
11. [Troubleshooting](#troubleshooting)
12. [Running With Docker](#running-with-docker)
12. [Security notes](#security-notes)
13. [Roadmap](#roadmap)
14. [Authors](#authors)

---

## Features

| Role | What they can do |
|---|---|
| **Guest** | Register, search rooms by date, book, cancel, request check-in/out, add services during a stay, pay invoices, view loyalty points, edit profile |
| **Staff** | Approve or reject bookings, check guests in and out, book on behalf of walk-in guests, record payments, add services, report and work on maintenance tasks assigned to them |
| **Manager** | Everything staff can do, plus: create and manage **their own team's** staff, manage rooms, room types and services, assign maintenance, view reports |
| **Admin** | Everything above for the whole hotel, plus: create and manage managers and departments |

Highlights:

- JWT authentication with bcrypt password hashing and login lockout after repeated failures
- Temporary passwords for accounts created by staff; users must change them at first login
- Guests only ever see their own data (no hotel-wide figures, no internal room status)
- Double bookings are prevented by the database itself (PostgreSQL exclusion constraint)
- Invoices recalculate automatically when services are added; payments cannot exceed the balance
- Role-specific dashboards (guest "My Stay", staff operations view, management view with revenue)
- 61 automated integration tests, including a role-access matrix

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite 6, React Router 7, plain CSS |
| Backend | Python, FastAPI, Pydantic v2, psycopg 3 (with connection pool), PyJWT, passlib/bcrypt |
| Database | PostgreSQL (SQL migrations + demo seed data) |
| Tests | pytest, httpx |

## Prerequisites

| Tool | Version | Check with |
|---|---|---|
| Git | any recent | `git --version` |
| Python | 3.10 or newer (tested on 3.12) | `python --version` |
| Node.js | 18 or newer (tested on 22) | `node --version` |
| PostgreSQL | 14 or newer (tested on 16) | `psql --version` |

Docker is not required for the Quick start. It is needed only for Running with Docker

## Quick start

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd hotel-management-fullstack
```

### 2. Create the database

Open `psql` as a superuser (on Windows use "SQL Shell (psql)", on Linux `sudo -u postgres psql`) and run:

```sql
CREATE USER hotel_user WITH PASSWORD 'choose-a-password';
CREATE DATABASE hotel_management OWNER hotel_user;
```

The app uses the `btree_gist` extension, which the migrations create automatically. If you see
`permission denied to create extension`, connect to `hotel_management` as a superuser and run
`CREATE EXTENSION IF NOT EXISTS btree_gist;` once.

### 3. Set up and start the backend

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

| OS / shell | Command |
|---|---|
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` (if blocked: `Set-ExecutionPolicy -Scope Process Bypass`) |
| Windows (cmd) | `.venv\Scripts\activate.bat` |
| macOS / Linux | `source .venv/bin/activate` |

Install dependencies and create your environment file:

```bash
pip install -r requirements-dev.txt
cp .env.example .env          # Windows: copy .env.example .env
```

Edit `backend/.env`:

1. Set `DATABASE_USER`, `DATABASE_PASSWORD` and `DATABASE_NAME` to what you created in step 2.
2. Generate a secret and paste it as `JWT_SECRET`:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   The backend **refuses to start** if `JWT_SECRET` is missing, still a placeholder, or shorter than 32 characters.

Create the tables and load demo data, then start the API:

```bash
python -m app.migrate --seed
uvicorn app.main:app --reload
```

The API is now at <http://127.0.0.1:8000>. Interactive docs: <http://127.0.0.1:8000/docs>.
Health checks: `/api/health` (is it running) and `/api/health/ready` (can it reach the database).

### 4. Set up and start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Optional: create `frontend/.env` if your API is not at the default address:

```
VITE_API_BASE=http://127.0.0.1:8000/api
```

Open <http://127.0.0.1:5173> and log in with a demo account below.

> **Windows shortcut:** after editing `backend/.env` once, double-click `run-all.bat`. It opens the backend and frontend
> in two windows. Do not run it before setting `JWT_SECRET`.

## Demo accounts

Created by `python -m app.migrate --seed`. **For local demos only, never use these passwords anywhere real.**

| Role | Email | Password |
|---|---|---|
| Admin | `admin@hotel.com` | `Admin@2026` |
| Manager | `manager@hotel.com` | `Manager@2026` |
| Staff | `staff@hotel.com` | `Staff@2026` |
| Guest | `customer@hotel.com` | `Guest@2026` |

You can also register a new guest account from the login page.

## Configuration

All backend settings are environment variables, read from `backend/.env` (real environment variables take priority).

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | empty | Full connection string. If set, it replaces the fields below (use this for cloud databases, with `?sslmode=require`) |
| `DATABASE_HOST` / `DATABASE_PORT` | `localhost` / `5432` | Database location |
| `DATABASE_NAME` / `DATABASE_USER` / `DATABASE_PASSWORD` | none | Database credentials (required unless `DATABASE_URL` is set) |
| `DB_POOL_MIN` / `DB_POOL_MAX` | `1` / `10` | Connection pool size |
| `JWT_SECRET` | none, **required** | Signs login tokens, at least 32 random characters |
| `JWT_ALGORITHM` | `HS256` | Token algorithm |
| `ACCESS_TOKEN_MINUTES` | `480` | How long a login lasts |
| `LOGIN_MAX_ATTEMPTS` / `LOGIN_LOCK_MINUTES` | `5` / `15` | Lock an email after repeated failed logins |
| `TAX_RATE` | `0.12` | Tax added to invoices (12%) |
| `LOYALTY_UNIT` | `100` | One loyalty point per this much paid |
| `CORS_ORIGINS` | localhost and 127.0.0.1 on port 5173 | Comma-separated list of allowed frontend origins |

Frontend: `VITE_API_BASE` (default `http://127.0.0.1:8000/api`). Vite reads it at **build time**.

## Running the tests

The tests run against a real PostgreSQL database and **wipe and rebuild it for every test module**. Use a separate database:

```sql
CREATE DATABASE hotel_test OWNER hotel_user;
```

Then from `backend/` with the virtual environment active:

```bash
pytest
```

They reuse `DATABASE_USER` and `DATABASE_PASSWORD` from your environment or `.env`. To use another database name,
set `TEST_DATABASE_NAME`. Expected result: all tests pass.

Frontend production build check:

```bash
cd frontend
npm run build
```

## How the system behaves

**Booking lifecycle**

```
PENDING -> APPROVED -> CHECKIN_PENDING -> CHECKED_IN -> CHECKOUT_PENDING -> CHECKED_OUT
   |           |              |
   +-> REJECTED / CANCELLED (a guest can cancel until the check-in date)
```

- A guest's booking starts as `PENDING`. Staff approve or reject it (with a reason). Bookings created by staff for a
  walk-in guest start as `APPROVED`.
- A room cannot have two overlapping active bookings. The check-out day is free for the next guest.
- Check-in is only possible between the booked dates. The room then becomes `OCCUPIED`, and returns to `AVAILABLE` at check-out.
- Services can only be added while the guest is checked in.
- Payments are accepted once the guest has checked in. A payment cannot exceed the balance due, and each payment earns loyalty points.
- Check-out is blocked until the balance is paid. A manager or admin can override this.
- Rooms under maintenance cannot be booked. Completing the last open maintenance task frees the room.

**People management**

- Admins create managers and staff. Managers create staff only, always under themselves, and only see and edit their own team.
- Accounts are **deactivated**, never deleted, so history stays intact. A deactivated user is locked out immediately.
- Every account created by someone else gets a temporary password and must set a new one at first login.

## API overview

Full interactive reference at `/docs`. All routes are under `/api`.

| Area | Prefix | Who can use it |
|---|---|---|
| Authentication, profile | `/auth` | everyone |
| Dashboard | `/dashboard` | everyone (different response per role) |
| Rooms and room types | `/rooms` | read: everyone, change: manager/admin (status: staff too) |
| Bookings | `/bookings` | everyone (guests see only their own) |
| Billing, invoices, payments | `/billing` | everyone (guests see only their own) |
| Services | `/services` | read: everyone, catalogue changes: manager/admin |
| Staff | `/staff` | manager (own team) and admin |
| Managers | `/managers` | admin |
| Customers | `/customers` | staff, manager, admin |
| Departments | `/departments` | manager (read), admin (change) |
| Maintenance | `/maintenance` | staff (own tasks), manager, admin |
| Reports | `/reports` | manager, admin |

## Project structure

```
hotel-management-fullstack/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, error handlers, health checks
│   │   ├── database.py        # connection pool, transactions, error mapping
│   │   ├── migrate.py         # SQL migration runner (python -m app.migrate)
│   │   ├── schemas.py         # request validation (Pydantic)
│   │   ├── billing_logic.py   # invoice and balance calculation
│   │   ├── core/              # config, security (JWT, roles), audit log
│   │   └── routers/           # one file per API area
│   ├── tests/                 # pytest integration tests
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── api/               # fetch client
│       ├── auth/              # login state and role helpers
│       ├── components/        # shared UI (tables, modals, tabs, toasts)
│       ├── hooks/             # useFetch, useAction
│       ├── pages/             # one file per screen
│       └── App.jsx, nav.js    # routing and role-based navigation
├── database/
│   ├── migrations/            # versioned SQL, applied in order
│   └── seed_demo.sql          # demo data (never run in production)
├── docs/                      # project synopsis and planning documents
├── run-all.bat, run-backend.bat, run-frontend.bat   # Windows shortcuts
└── README.md
```

Applied migrations are recorded in a `schema_migrations` table, so `python -m app.migrate` is safe to run repeatedly.
To add a schema change, add a new numbered file such as `003_your_change.sql` to `database/migrations/`.

## Troubleshooting

| Problem | Fix |
|---|---|
| `JWT_SECRET is required` or `still looks like a placeholder` | Generate a real secret (step 3) and put it in `backend/.env` |
| `password authentication failed` | `DATABASE_USER` / `DATABASE_PASSWORD` in `.env` do not match the PostgreSQL user |
| `relation "users" does not exist` | The tables were never created. Run `python -m app.migrate --seed` |
| `permission denied to create extension "btree_gist"` | Run `CREATE EXTENSION IF NOT EXISTS btree_gist;` once as a superuser on that database |
| Browser shows a network or CORS error | Backend is not running, or `CORS_ORIGINS` does not include the exact frontend address. `localhost` and `127.0.0.1` count as different origins |
| Login worked before but now returns 401 | You changed `JWT_SECRET`. Log in again |
| `Too many failed attempts` (429) | Wait `LOGIN_LOCK_MINUTES`, or restart the backend |
| Everything redirects to a password screen | That account has a temporary password. Set a new one |
| Port 8000 or 5173 already in use | Stop the other process, or start with `--port` / change the `dev` script |
| `Activate.ps1 cannot be loaded` (PowerShell) | `Set-ExecutionPolicy -Scope Process Bypass`, or use `activate.bat` in cmd |
| Seed says "users already exist; skipping seed" | Expected on a database that already has data. Drop and recreate it for a clean demo |

## Running with Docker

The Docker setup runs the whole stack (PostgreSQL, backend, frontend) on one machine. It is the **test environment**: use it to try changes locally before they reach the hosted deployment. It is not meant for hosting.

### Prerequisites

- Docker Desktop (with the WSL2 backend on Windows) or Docker Engine, with Compose v2.
- Nothing else. PostgreSQL, Python and Node run inside containers.

### Quick start

```bash
# 1. Create your local settings file (it is git-ignored; never commit it)
cp .env.example .env

# 2. Generate the two secrets and paste them into .env
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # DATABASE_PASSWORD
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # JWT_SECRET

# 3. Build and start everything
docker compose -f docker-compose.yml -f docker-compose.test.yml up --build
```

When all three services show `healthy` in `docker compose ps`:

- Frontend: <http://localhost:3000>
- Backend API: <http://localhost:8000> (the interactive API docs are at `/docs`)

Open the site as `localhost`, not `127.0.0.1`. The backend allows exactly one origin, and a browser treats the two addresses as different origins.

Log in with one of the demo accounts listed at the top of `database/seed_demo.sql`. They exist only because this environment loads the demo seed.

To avoid typing the two `-f` flags, set `COMPOSE_FILE` in `.env` (see the table below), after which `docker compose up --build` is enough.

### Everyday commands

| Task | Command |
|---|---|
| Start in the background | `docker compose -f docker-compose.yml -f docker-compose.test.yml up -d --build` |
| Show service health | `docker compose ps` |
| Follow backend logs | `docker compose logs -f backend` |
| Stop, keeping the database | `docker compose down` |
| Stop and **erase the database** (also reloads the demo seed next time) | `docker compose down -v` |

### How the setup is organised

| File | Purpose |
|---|---|
| `docker-compose.yml` | Shared definition of the three services. Deliberately not runnable on its own: it has no host ports, no CORS origin and no frontend API URL. |
| `docker-compose.test.yml` | Local test values layered on top: ports bound to `127.0.0.1` only, the browser-facing URLs, and the demo seed. |
| `backend/Dockerfile` | Backend image. Build it from the **repository root**, because it copies `database/migrations/`, which lives outside `backend/`. Stages: `base` (dependencies) and `prod` (the image that runs). |
| `backend/entrypoint.sh` | Container start script: applies database migrations, then starts the API server. With `--seed` it also loads demo data. Any other argument is run as a command. |
| `frontend/Dockerfile` | Frontend image. Stage one builds with Node, stage two serves the static files with unprivileged nginx. Build context is `frontend/`. |
| `frontend/nginx.conf` | Serves the app, falls back to `index.html` for client-side routes, caches hashed assets, compresses text. |

Building the images without Compose:

```bash
docker build -f backend/Dockerfile -t hms-backend .
docker build --build-arg VITE_API_BASE=http://localhost:8000/api -t hms-frontend frontend
```

### Settings

**Variables in `.env`** (Compose reads these to fill in the YAML):

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_NAME` | yes | Database name, used by both the database container and the backend |
| `DATABASE_USER` | yes | Database user, used by both |
| `DATABASE_PASSWORD` | yes | **Secret.** Generate it; used by both |
| `JWT_SECRET` | yes | **Secret.** At least 32 characters; used by the backend only |
| `FRONTEND_PORT` | yes | Host port for the frontend; also used to build the allowed CORS origin |
| `BACKEND_PORT` | yes | Host port for the API; also baked into the frontend as its API URL |
| `COMPOSE_FILE` | no | Loads both Compose files automatically. Separator is `:` on Linux, macOS and WSL, `;` on native Windows |

**Set by the Compose files** (not in `.env`):

| Setting | Where | Value |
|---|---|---|
| `DATABASE_HOST` | `docker-compose.yml` | `db`, the name of the database service on the Compose network |
| `CORS_ORIGINS` | `docker-compose.test.yml` | `http://localhost:${FRONTEND_PORT}` |
| `VITE_API_BASE` (build argument) | `docker-compose.test.yml` | `http://localhost:${BACKEND_PORT}/api` |
| `SEED_FILE` and the `--seed` argument | `docker-compose.test.yml` | Mounts `database/seed_demo.sql` read-only and loads it |

**Built into the backend image:** `MIGRATIONS_DIR` and a default `PORT` of 8000. Everything else, including every secret, is supplied when the container starts. The backend's full list of settings and defaults is in `backend/app/core/config.py` and, for running without Docker, `backend/.env.example`.

`VITE_API_BASE` is public, not secret: Vite compiles it into the JavaScript bundle that every visitor downloads. It is a build argument, so changing a port means rebuilding the frontend (`up --build`). The frontend build fails with a clear error if it is not provided.

### Notes and limits

- **Demo data loads only on the first start**, when the `users` table is empty. Restarting does not load it twice. `docker compose down -v` erases the database so the next start reloads it.
- **Changing `DATABASE_PASSWORD` after the first start does not change the database's password.** PostgreSQL reads these settings only when it creates an empty volume, so the backend will fail to log in until you run `docker compose down -v`.
- **Ports are bound to `127.0.0.1`**, so the stack is not reachable from other machines on your network.
- **Never use this configuration for a real deployment.** The demo seed contains accounts with publicly known passwords. Real deployments do not seed demo data.
- **The hosted environment is different.** The backend runs from the same `backend/Dockerfile`, with settings supplied by the hosting platform. The frontend is built from source by Vercel, so `frontend/Dockerfile` is used for local testing only. See `docs/ENVIRONMENTS.md`.

### Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `required variable ... is missing` when running Compose | `.env` is missing or the value is empty. Check each variable in the table above. |
| Compose uses a different secret than your `.env` | A variable exported in your shell overrides `.env`. Run `unset JWT_SECRET` (or the variable named) and retry. |
| Backend exits at once with `JWT_SECRET is required` | The value is empty. The message mentions `backend/.env`, which applies only when running without Docker. |
| Browser shows a CORS error | Open the site at exactly `http://localhost:<FRONTEND_PORT>`. After changing ports, rerun with `--build`. |
| Backend cannot authenticate to the database | The password changed after the volume was created. Run `docker compose down -v`. |
| No demo accounts exist | The database already had users. Run `docker compose down -v` and start again. |
| `exec /app/entrypoint.sh: no such file or directory` | The script was checked out with Windows (CRLF) line endings. Run `git add --renormalize .` or re-clone. `.gitattributes` forces LF for new clones. |
| `port is already allocated` | Change `FRONTEND_PORT` or `BACKEND_PORT` in `.env`. |

## Security notes

- Never commit `.env` files or database dumps. The repository's `.gitignore` excludes them; keep it that way.
- The demo passwords are public. Do not load `seed_demo.sql` into a real deployment, and create real admin accounts instead.
- Change `JWT_SECRET` and the database password if they are ever shared or leaked.
- Login lockout is stored in memory, which is fine for one server. Use a shared store if you run several instances.

## Roadmap

Application features are complete. Remaining work for the cloud and DevOps phase:
- [x] Docker images and a Compose-based local test environment
- [ ] GitHub Actions CI (tests and build) and CD (automatic deployment)
- [ ] Managed PostgreSQL, backend and frontend hosting
- [ ] Cloud object storage for room images, ID documents and invoice PDFs
- [ ] Structured logging, error tracking and uptime monitoring
- [ ] Optional email notifications

## Authors

Navdeep Singh, Siddhant Gupta and Abhigyan Gupta, School of Computer Engineering.
