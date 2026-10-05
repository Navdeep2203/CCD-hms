# Backend setup (updated)

1. `cd backend`, create a venv, `pip install -r requirements-dev.txt`.
2. Copy `.env.example` to `.env`. Set the DB values and a real `JWT_SECRET`
   (`python -c "import secrets; print(secrets.token_urlsafe(48))"`). The app refuses to start otherwise.
3. Create the database, then `python -m app.migrate --seed` (migrations live in `database/migrations/`;
   an existing database that already has the old schema + improvements is detected and baselined).
4. `uvicorn app.main:app --reload` -> API docs at http://127.0.0.1:8000/docs, readiness at `/api/health/ready`.
5. Tests: `createdb hotel_test` once, then `pytest` (WARNING: wipes and rebuilds `hotel_test` each module).

**API changes the frontend must follow:** `/api/admin/*` is gone. Use `/api/staff`, `/api/managers`, `/api/customers`,
`/api/departments`, `/api/maintenance`. `GET /dashboard/overview` returns a `kind` (`guest`/`staff`/`management`).
Login returns `user.must_change_password`. See `docs/FRONTEND_TODO.md`.

---

# Hotel Management System - React + FastAPI

Full-stack conversion of the original JavaFX hotel management system into a resume-ready web application.

## Stack

- React + Vite frontend
- FastAPI backend
- PostgreSQL database
- JWT authentication
- Role-based workflows for admin, manager, staff, and customer users

## Features

- Login and customer registration
- Role-based dashboards
- Room inventory and room type management
- Booking lifecycle: pending, approved, check-in, check-out, cancelled
- Invoice generation and payment recording
- Service usage tracking
- Staff, department, and maintenance views
- Reports for revenue, bookings, room types, status breakdowns, and service usage

## Project Structure

```text
hotel-management-fullstack/
  backend/    FastAPI API, PostgreSQL data layer, JWT auth
  frontend/   React dashboard app
  database/   PostgreSQL schema and demo seed script
```

## Database Setup

1. Install PostgreSQL and make sure the PostgreSQL service is running.
2. Create a database named `hotel_management`.
3. Run `python -m app.migrate --seed` from `backend/` (see 'Backend setup' above).
4. Run `database/seed_demo.sql`.
5. Copy `backend/.env.example` to `backend/.env`.
6. Update the PostgreSQL username and password:

```env
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=hotel_management
DATABASE_USER=your_postgres_user
DATABASE_PASSWORD=your_postgres_password
JWT_SECRET=replace-with-a-long-random-secret
```

Command-line example:

```bat
createdb -U postgres hotel_management
cd backend && python -m app.migrate --seed
psql -U postgres -d hotel_management -f database\seed_demo.sql
```

If `createdb` is not available in your terminal, create the database from pgAdmin and run both SQL files in the Query Tool.

## Run Locally

Open two terminals.

Backend:

```bat
run-backend.bat
```

Frontend:

```bat
run-frontend.bat
```

Then open:

```text
http://127.0.0.1:5173
```

## Demo Accounts

The seed script creates these accounts. Demo logins (DEMO ONLY): admin@hotel.com / Admin@2026, manager@hotel.com / Manager@2026, staff@hotel.com / Staff@2026, customer@hotel.com / Guest@2026.

| Role | Email |
| --- | --- |
| Admin | admin@hotel.com |
| Manager | manager@hotel.com |
| Staff | staff@hotel.com |
| Customer | customer@hotel.com |

## Notes From The Conversion

The JavaFX code referenced `SERVICE_REQUESTS` and `SERVICE_CHARGES`, while the supplied complete schema uses `SERVICE_USAGE`. The converted FastAPI backend uses `SERVICE_USAGE` directly and exposes it in the UI as hotel services/service usage.

The original Java business logic was rewritten into Python/FastAPI instead of copied directly. The API preserves the same major workflows: authentication, room management, customer booking, staff/manager booking actions, invoicing, payments, services, reporting, and maintenance visibility. The current backend and database scripts target PostgreSQL.
