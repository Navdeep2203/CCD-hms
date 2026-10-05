# Frontend to-do (the backend is finished; the frontend is still the ORIGINAL code)

The old `frontend/src/main.jsx` will break against the new API. Do the steps in order and test after each one.
Interactive API reference: http://127.0.0.1:8000/docs. Demo logins are in the README.

## Step F1 - Hotfixes (`src/main.jsx`, `src/api/client.js`)
1. Token race: call `setToken(...)` synchronously (when reading the stored session and inside `onLogin`), not in a `useEffect`.
2. Register form: send `null` instead of `""` for `phone_number`.
3. `client.js`: parse the body safely (text first, JSON if possible); on 401 (except from /auth/login) clear session and go to login; errors are always a string in `detail`.
4. Wrap every form submit in try/catch and show the error (add a small toast); give every page loading / error / retry states.
5. Remove pre-filled admin credentials and stale text ("Oracle records", "Bengaluru property", "Secure staff console").

## Step F2 - Structure
Split `main.jsx` into `pages/`, `components/` (DataTable, Badge, StatCard, Modal, ConfirmDialog, Toast), `auth/AuthContext`,
`hooks/useFetch`, `utils/format.js` (dates as `5 Oct 2026`). Add `react-router-dom` with a `RequireRole` guard; nav and routes read one config.
Move `vite` and `@vitejs/plugin-react` to `devDependencies`.

## Step F3 - Forced password change
After login, if `user.must_change_password` is true show ONLY a change-password form (`POST /auth/change-password`
with `current_password`, `new_password`), then continue. Until then every other endpoint returns 403.

## Step F4 - Page by page (what each page must call)
| Page | Roles | Endpoints / changes |
|---|---|---|
| Overview | all | `GET /dashboard/overview` returns `kind`. `guest` -> "My Stay" page (current_stay, upcoming, balance_due, loyalty_points). `staff` -> room counts + arrivals_today / departures_today, NO revenue. `management` -> same + today_revenue / month_revenue. |
| Rooms | all | Guests: `GET /rooms?check_in=&check_out=` (needs both dates; no `status` field returned), show nights x price. Staff+: status column, `PATCH /rooms/{id}/status` (OCCUPIED is rejected, it is automatic). Admin/manager: add/edit/delete rooms (`POST/PUT/DELETE /rooms`) and room types (`/rooms/types`). |
| Bookings | all | `GET /bookings?search=&status=`. Guest: create (`POST /bookings`), Cancel, "Request check-in/out". Staff+: Approve, Reject (ask for `rejection_reason`), Check in, Check out, walk-in booking (must send `customer_id`; pick from `GET /customers?search=`), "Create guest" via `POST /customers`. Checkout may return 409 for unpaid balance; managers/admins can resend with `override_balance: true`. Show backend error text in a toast. |
| Billing | all | `GET /billing/invoices` (fields: grand_total, amount_paid, balance_due, payment_state). Payment form: pick from `GET /billing/payable` (no free-text booking id), methods from `GET /billing/methods`, `POST /billing/payments`. Payment history: `GET /billing/payments/{booking_id}`. Replace "Regenerate" with "Recalculate" (`POST /billing/invoices/{booking_id}/generate`). Add Billing to the staff nav. |
| Services | all | Add-service form: booking dropdown from `GET /bookings?status=CHECKED_IN`. Admin/manager: create/edit/delete (`POST/PUT/DELETE /services`). |
| Staff | admin, manager | `GET/POST /staff`, `PUT /staff/{id}`, `PATCH /staff/{id}/active` `{active}`, `POST /staff/{id}/reset-password` `{temporary_password}`. Create form: admin sees a manager dropdown (required), manager does NOT (server uses their own id). Salary shown here only. Show the temporary password once. Departments dropdown: `GET /departments`. Confirm dialog before deactivate. |
| Managers | admin | Same pattern on `/managers` (field `reports_to_manager_id`). Deactivation can return 409 (still has staff / heads a department). |
| Customers | admin, manager, staff | `GET /customers?search=`. Staff see no address/id_proof. |
| Maintenance | admin, manager, staff | `GET /maintenance` (staff only get tasks assigned to them), `POST /maintenance`, `PUT /maintenance/{id}` (staff may only send `status`; only management may assign `staff_id`). Give staff a "My Tasks" page. |
| Departments | admin, manager | `GET /departments`; admin: POST/PUT/DELETE. |
| Reports | admin, manager | `GET /reports/summary` (unchanged shape). |
| Profile | all | `GET /auth/me`, `PUT /auth/profile` (name, phone; guests also address, id_proof, nationality), change-password section. |

Remove calls to `/admin/*` (staff, managers, departments, maintenance, customers) - they no longer exist.

## Step F5 - Final checks (as each role)
Customer sees no hotel-wide data and no staff/admin menu; refresh keeps the URL; a forbidden URL redirects; mobile width works;
`npm run build` passes.
