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

Docker is **not** required yet.

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

## Security notes

- Never commit `.env` files or database dumps. The repository's `.gitignore` excludes them; keep it that way.
- The demo passwords are public. Do not load `seed_demo.sql` into a real deployment, and create real admin accounts instead.
- Change `JWT_SECRET` and the database password if they are ever shared or leaked.
- Login lockout is stored in memory, which is fine for one server. Use a shared store if you run several instances.

## Roadmap

Application features are complete. Remaining work for the cloud and DevOps phase:

- [ ] Dockerfiles for backend and frontend, and Docker Compose for local development
- [ ] GitHub Actions CI (tests and build) and CD (automatic deployment)
- [ ] Managed PostgreSQL, backend and frontend hosting
- [ ] Cloud object storage for room images, ID documents and invoice PDFs
- [ ] Structured logging, error tracking and uptime monitoring
- [ ] Optional email notifications

## Authors

Navdeep Singh, Siddhant Gupta and Abhigyan Gupta, School of Computer Engineering.
