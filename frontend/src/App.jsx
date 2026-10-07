import React, { useEffect, useMemo, useState } from "react";
import ChangePassword from "./ChangePassword";
import {
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";

import { api } from "./api/client";
import { useAuth } from "./auth/AuthContext";
import { ALL_ROLES, HOTEL_NAME, navItems } from "./nav";
import { ToastProvider } from "./components/Toast";
import Badge from "./components/Badge";
import DataTable from "./components/DataTable";
import StatCard from "./components/StatCard";
import PageState from "./components/PageState";
import { currency } from "./utils/format";
import "./styles.css";
import Overview from "./pages/Overview";
import Rooms from "./pages/Rooms";
import BookingsPage from "./pages/Bookings";
import BillingPage from "./pages/Billing";
import ServicesPage from "./pages/Services";
import StaffPage from "./pages/Staff";
import CustomersPage from "./pages/Customers";
import MaintenancePage from "./pages/Maintenance";
import ReportsPage from "./pages/Reports";
import ProfilePage from "./pages/Profile";

function Login() {
  const { login } = useAuth();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    phone_country_code: "+91",
    phone_number: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();

    setBusy(true);
    setError("");

    try {
      if (mode === "login") {
        const data = await api.post("/auth/login", {
          email: form.email,
          password: form.password,
        });

        login(data);
      } else {
        const data = await api.post("/auth/register", {
          name: form.name,
          email: form.email,
          password: form.password,
          phone_country_code: form.phone_country_code,
          phone_number: form.phone_number.trim() || null,
        });

        login(data);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="authPage">
      <section className="authVisual">
        <div className="authCopy">
          <div className="brandLockup">
            <div className="brandMark large">MH</div>
            <span>{HOTEL_NAME}</span>
          </div>
          <p className="eyebrow">PROPERTY OPERATIONS SUITE</p>
          <h1>Front desk clarity for every stay.</h1>
          <p>
            Coordinate rooms, reservations, services, billing, and teams from a
            calm operational workspace built for hotel staff.
          </p>
          <div className="authMetrics">
            <span>
              <strong>Live</strong> occupancy
            </span>
            <span>
              <strong>Role</strong> dashboards
            </span>
            <span>
              <strong>Guest</strong> records
            </span>
          </div>
        </div>
      </section>
      <section className="authPanel">
        <div className="authCardHead">
          <div className="brandMark">MH</div>
          <div>
            <strong>Meridian HMS</strong>
            <span>Hotel operations console</span>
          </div>
        </div>
        <h2>{mode === "login" ? "Welcome back" : "Create customer account"}</h2>
        <form onSubmit={submit} className="form">
          {mode === "register" && (
            <label>
              Name
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
            </label>
          )}
          <label>
            Email
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              minLength={mode === "register" ? 8 : undefined}
              pattern={
                mode === "register"
                  ? "^(?=.*[A-Za-z])(?=.*\\d).{8,72}$"
                  : undefined
              }
              required
            />
            {mode === "register" && (
              <small className="fieldHint">
                At least 8 characters with a letter and a digit.
              </small>
            )}
          </label>
          {mode === "register" && (
            <div className="split">
              <label>
                Code
                <input
                  value={form.phone_country_code}
                  onChange={(e) =>
                    setForm({ ...form, phone_country_code: e.target.value })
                  }
                />
              </label>
              <label>
                Phone
                <input
                  value={form.phone_number}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      phone_number: e.target.value,
                    })
                  }
                  minLength={6}
                  maxLength={15}
                  pattern="\d{6,15}"
                  inputMode="numeric"
                />
                <small className="fieldHint">6–15 digits.</small>
              </label>
            </div>
          )}
          {error && <p className="error">{error}</p>}
          <button className="primary" disabled={busy}>
            {busy ? "Working..." : mode === "login" ? "Sign in" : "Register"}
          </button>
        </form>
        <button
          className="linkButton"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "Create a customer account" : "Back to sign in"}
        </button>
      </section>
    </main>
  );
}

function Shell({ user, children }) {
  const { logout, hasRole } = useAuth();
  const location = useLocation();

  const visibleNav = navItems.filter((item) => hasRole(...item.roles));

  const activePage =
    navItems.find((item) => item.path === location.pathname) || navItems[0];

  const roles = user.roles || [];

  return (
    <div className="appShell">
      <aside>
        <div className="sideBrand">
          <div className="brandMark">MH</div>

          <div>
            <strong>{HOTEL_NAME}</strong>
            <span>Hotel operations</span>
          </div>
        </div>

        <nav>
          {visibleNav.map((item) => (
            <NavLink
              key={item.id}
              to={item.path}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              <b>{item.code}</b>

              <span>
                {item.label}
                <small>{item.detail}</small>
              </span>
            </NavLink>
          ))}
        </nav>

        <div className="sidePanel">
          <span>Shift board</span>

          <strong>
            {new Date().toLocaleTimeString("en-IN", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </strong>

          <small>
            {new Date().toLocaleDateString("en-IN", {
              weekday: "long",
              day: "numeric",
              month: "short",
            })}
          </small>
        </div>

        <div className="userBox">
          <strong>{user.name}</strong>

          <span>
            {roles.map((role) => role.replace("ROLE_", "")).join(" / ")}
          </span>

          <button onClick={logout}>Sign out</button>
        </div>
      </aside>

      <main className="content">
        <header>
          <div>
            <p className="eyebrow">{HOTEL_NAME} Management</p>

            <h1>{activePage?.label || "Overview"}</h1>

            <span className="pageDetail">{activePage?.detail}</span>
          </div>

          <div className="headerMeta">
            <span className="propertyChip">{HOTEL_NAME} property</span>

            <span>
              {new Date().toLocaleDateString("en-IN", {
                dateStyle: "medium",
              })}
            </span>

            <Badge>{roles[0]?.replace("ROLE_", "") || "USER"}</Badge>
          </div>
        </header>

        {children}
      </main>
    </div>
  );
}

export default function App() {
  const { user } = useAuth();

  if (!user) {
    return <Login />;
  }

  if (user.must_change_password) {
    return <ChangePassword />;
  }

  const pageMap = {
    "/": () => <Overview />,
    "/rooms": () => <Rooms />,
    "/bookings": () => <BookingsPage />,
    "/billing": () => <BillingPage />,
    "/services": () => <ServicesPage />,
    "/maintenance": () => <MaintenancePage />,
    "/staff": () => <StaffPage />,
    "/customers": () => <CustomersPage />,
    "/reports": () => <ReportsPage />,
    "/profile": () => <ProfilePage />,
  };

  return (
    <Shell user={user}>
      <Routes>
        {navItems.map((item) => {
          const renderPage = pageMap[item.path];

          return (
            <Route
              key={item.path}
              path={item.path}
              element={
                <RequireRole roles={item.roles}>{renderPage()}</RequireRole>
              }
            />
          );
        })}

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Shell>
  );
}

function RequireRole({ roles, children }) {
  const { hasRole } = useAuth();

  if (!hasRole(...roles)) {
    return <Navigate to="/" replace />;
  }

  return children;
}
