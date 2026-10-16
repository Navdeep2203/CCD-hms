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

const DEMO_ACCOUNTS = [
  { role: "Admin", email: "admin@hotel.com", pass: "Admin@2026", badge: "Superuser" },
  { role: "Manager", email: "manager@hotel.com", pass: "Manager@2026", badge: "Operations" },
  { role: "Staff", email: "staff@hotel.com", pass: "Staff@2026", badge: "Front Desk" },
  { role: "Guest", email: "customer@hotel.com", pass: "Guest@2026", badge: "Customer" },
];

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

  function fillDemo(d) {
    setForm((prev) => ({
      ...prev,
      email: d.email,
      password: d.pass,
    }));
    setError("");
    if (mode !== "login") setMode("login");
  }

  return (
    <main className="authPage">
      <section className="authVisual">
        <div className="authVisualOverlay"></div>
        <div className="authCopy">
          <div className="brandLockup">
            <div className="brandMark large">GH</div>
            <div>
              <span className="brandTitle">{HOTEL_NAME}</span>
              <span className="brandStars">★★★★★ Luxury Hotel &amp; Suites</span>
            </div>
          </div>
          <p className="eyebrow">ENTERPRISE PROPERTY MANAGEMENT SYSTEM</p>
          <h1>Next-generation hospitality &amp; property intelligence.</h1>
          <p>
            Effortlessly coordinate front desk check-in, real-time room inventory,
            concierge services, billing folios, and housekeeping from an integrated
            cloud workspace.
          </p>
          <div className="authMetrics">
            <div className="authMetricItem">
              <strong>98.4%</strong>
              <span>Live Occupancy</span>
            </div>
            <div className="authMetricItem">
              <strong>24 / 7</strong>
              <span>Front Desk Synced</span>
            </div>
            <div className="authMetricItem">
              <strong>Multi-Role</strong>
              <span>RBAC Security</span>
            </div>
            <div className="authMetricItem">
              <strong>Auto</strong>
              <span>Folio Invoicing</span>
            </div>
          </div>
        </div>
      </section>

      <section className="authPanel">
        <div className="authCardWrapper">
          <div className="authCardHead">
            <div className="brandMark">GH</div>
            <div>
              <strong>The Grand Horizon PMS</strong>
              <span>Hospitality Operations &amp; Guest Portal</span>
            </div>
          </div>

          <div className="authTabSwitch">
            <button
              type="button"
              className={mode === "login" ? "active" : ""}
              onClick={() => {
                setMode("login");
                setError("");
              }}
            >
              Staff &amp; Guest Sign In
            </button>
            <button
              type="button"
              className={mode === "register" ? "active" : ""}
              onClick={() => {
                setMode("register");
                setError("");
              }}
            >
              New Guest Register
            </button>
          </div>

          <div className="authTitleGroup">
            <h2>{mode === "login" ? "Portal Sign In" : "Create Guest Account"}</h2>
            <p className="authSubtext">
              {mode === "login"
                ? "Enter your credentials or click a demo profile below to enter the portal."
                : "Create an account to book luxury suites, order services, and track bills."}
            </p>
          </div>

          {mode === "login" && (
            <div className="demoAccountsBar">
              <span className="demoAccountsLabel">Quick Demo Sign-In:</span>
              <div className="demoChips">
                {DEMO_ACCOUNTS.map((d) => (
                  <button
                    key={d.role}
                    type="button"
                    className="demoChip"
                    onClick={() => fillDemo(d)}
                    title={`Click to fill ${d.role} credentials`}
                  >
                    <span className="demoChipRole">{d.role}</span>
                    <span className="demoChipBadge">{d.badge}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <form onSubmit={submit} className="form">
            {mode === "register" && (
              <label>
                Full Name
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. Alexander Vance"
                  required
                />
              </label>
            )}

            <label>
              Email Address
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder={mode === "login" ? "admin@hotel.com" : "guest@example.com"}
                required
              />
            </label>

            <label>
              Password
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="••••••••••••"
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
                  Must be at least 8 characters with at least one letter and one number.
                </small>
              )}
            </label>

            {mode === "register" && (
              <div className="split">
                <label>
                  Country Code
                  <input
                    value={form.phone_country_code}
                    onChange={(e) =>
                      setForm({ ...form, phone_country_code: e.target.value })
                    }
                    placeholder="+91"
                  />
                </label>
                <label>
                  Phone Number
                  <input
                    value={form.phone_number}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        phone_number: e.target.value,
                      })
                    }
                    placeholder="9000000001"
                    minLength={6}
                    maxLength={15}
                    pattern="\d{6,15}"
                    inputMode="numeric"
                  />
                  <small className="fieldHint">6–15 digits.</small>
                </label>
              </div>
            )}

            {error && <div className="errorBanner">{error}</div>}

            <button type="submit" className="primary submitBtn" disabled={busy}>
              {busy
                ? "Authenticating..."
                : mode === "login"
                ? "Sign In to Portal →"
                : "Create Guest Account →"}
            </button>
          </form>

          <div className="authCardFooter">
            <span>🔒 256-Bit TLS Encrypted • PMS Enterprise Console v4.2</span>
          </div>
        </div>
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
  const primaryRole = roles[0]?.replace("ROLE_", "") || "USER";
  const userInitials = (user.name || "U")
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div className="appShell">
      <aside className="appSidebar">
        <div className="sideBrand">
          <div className="brandMark">GH</div>
          <div>
            <strong>{HOTEL_NAME}</strong>
            <span className="sideBrandSub">Luxury Hotel PMS</span>
          </div>
        </div>

        <nav className="sidebarNav">
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
          <div className="shiftStatus">
            <span className="liveDot"></span>
            <span>LIVE SHIFT</span>
          </div>
          <strong>
            {new Date().toLocaleTimeString("en-IN", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </strong>
          <small>
            {new Date().toLocaleDateString("en-IN", {
              weekday: "short",
              day: "numeric",
              month: "short",
              year: "numeric",
            })}
          </small>
        </div>

        <div className="userBox">
          <div className="userAvatar">{userInitials}</div>
          <div className="userInfo">
            <strong>{user.name}</strong>
            <span className="userRoleBadge">{primaryRole}</span>
          </div>
          <button className="signOutBtn" onClick={logout} title="Sign out of system">
            Sign out
          </button>
        </div>
      </aside>

      <main className="content">
        <header className="shellHeader">
          <div className="shellHeaderBrand">
            <span className="propertyChip">★ {HOTEL_NAME} • 5-Star Luxury</span>
            <span className="pageDetail">{activePage?.detail}</span>
          </div>

          <div className="headerMeta">
            <span className="propertyChip">★ {HOTEL_NAME}</span>
            <span>
              {new Date().toLocaleDateString("en-IN", {
                dateStyle: "medium",
              })}
            </span>
            <Badge>{primaryRole}</Badge>
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
