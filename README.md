# Hotel Management System - React + FastAPI

Full-stack conversion of the original JavaFX hotel management system into a resume-ready web application.

## Stack

- React + Vite frontend
- FastAPI backend
- Oracle SQL database
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
  backend/    FastAPI API, Oracle data layer, JWT auth
  frontend/   React dashboard app
  database/   Oracle schema and demo seed script
```

## Database Setup

1. Create a fresh Oracle schema/user.
2. Run `database/complete_schema.sql`.
3. Run `database/seed_demo.sql`.
4. Copy `backend/.env.example` to `backend/.env`.
5. Update:

```env
DATABASE_USER=your_oracle_user
DATABASE_PASSWORD=your_oracle_password
DATABASE_DSN=localhost:1521/XEPDB1
JWT_SECRET=replace-with-a-long-random-secret
```

If your old JavaFX `.env` uses `jdbc:oracle:thin:@localhost:1521/xe`, the backend also accepts that format through `DATABASE_DSN`.

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

The seed script creates these accounts. The demo password is `admin123`.

| Role | Email |
| --- | --- |
| Admin | admin@hotel.com |
| Manager | manager@hotel.com |
| Staff | staff@hotel.com |
| Customer | customer@hotel.com |

## Notes From The Conversion

The JavaFX code referenced `SERVICE_REQUESTS` and `SERVICE_CHARGES`, while the supplied complete schema uses `SERVICE_USAGE`. The converted FastAPI backend uses `SERVICE_USAGE` directly and exposes it in the UI as hotel services/service usage.

The original Java business logic was rewritten into Python/FastAPI instead of copied directly. The API preserves the same major workflows: authentication, room management, customer booking, staff/manager booking actions, invoicing, payments, services, reporting, and maintenance visibility.

