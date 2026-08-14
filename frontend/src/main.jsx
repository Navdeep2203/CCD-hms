import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, setToken } from "./api/client";
import "./styles.css";

const navItems = [
  { id: "overview", label: "Overview", roles: ["ROLE_ADMIN", "ROLE_MANAGER", "ROLE_STAFF", "ROLE_CUSTOMER"], detail: "Live property pulse", code: "OV" },
  { id: "rooms", label: "Rooms", roles: ["ROLE_ADMIN", "ROLE_MANAGER", "ROLE_STAFF", "ROLE_CUSTOMER"], detail: "Inventory grid", code: "RM" },
  { id: "bookings", label: "Bookings", roles: ["ROLE_ADMIN", "ROLE_MANAGER", "ROLE_STAFF", "ROLE_CUSTOMER"], detail: "Arrivals to checkout", code: "BK" },
  { id: "billing", label: "Billing", roles: ["ROLE_ADMIN", "ROLE_MANAGER", "ROLE_CUSTOMER"], detail: "Invoices and payments", code: "BL" },
  { id: "services", label: "Services", roles: ["ROLE_ADMIN", "ROLE_MANAGER", "ROLE_STAFF", "ROLE_CUSTOMER"], detail: "Guest add-ons", code: "SV" },
  { id: "staff", label: "Staff", roles: ["ROLE_ADMIN", "ROLE_MANAGER"], detail: "Teams and upkeep", code: "ST" },
  { id: "reports", label: "Reports", roles: ["ROLE_ADMIN", "ROLE_MANAGER"], detail: "Commercial insight", code: "RP" },
  { id: "profile", label: "Profile", roles: ["ROLE_ADMIN", "ROLE_MANAGER", "ROLE_STAFF", "ROLE_CUSTOMER"], detail: "Access profile", code: "PF" }
];

function currency(value) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(value || 0));
}

function statusTone(value = "") {
  const key = value.toUpperCase();
  if (["AVAILABLE", "APPROVED", "CHECKED_IN", "COMPLETED"].includes(key)) return "good";
  if (["PENDING", "CHECKIN_PENDING", "CHECKOUT_PENDING", "RESERVED", "IN_PROGRESS"].includes(key)) return "warn";
  if (["REJECTED", "CANCELLED", "FAILED", "MAINTENANCE"].includes(key)) return "bad";
  return "neutral";
}

function Badge({ children }) {
  return <span className={`badge ${statusTone(String(children))}`}>{children}</span>;
}

function DataTable({ columns, rows, empty = "No records found.", actions }) {
  return (
    <div className="tableWrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => <th key={column.key}>{column.label}</th>)}
            {actions && <th className="right">Actions</th>}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={columns.length + (actions ? 1 : 0)} className="empty">{empty}</td>
            </tr>
          )}
          {rows.map((row, index) => (
            <tr key={row.id || row.booking_id || row.room_id || row.invoice_id || row.usage_id || index}>
              {columns.map((column) => (
                <td key={column.key}>{column.render ? column.render(row) : row[column.key]}</td>
              ))}
              {actions && <td className="right actionCell">{actions(row)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatCard({ label, value, note, tone = "default" }) {
  return (
    <div className={`statCard ${tone}`}>
      <div className="statTop">
        <span>{label}</span>
        <i />
      </div>
      <strong>{value}</strong>
      {note && <small>{note}</small>}
    </div>
  );
}

function Login({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "admin@hotel.com", password: "admin123", phone_country_code: "+91", phone_number: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = mode === "login"
        ? await api.post("/auth/login", { email: form.email, password: form.password })
        : await api.post("/auth/register", form);
      onLogin(data);
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
            <span>Meridian House</span>
          </div>
          <p className="eyebrow">PROPERTY OPERATIONS SUITE</p>
          <h1>Front desk clarity for every stay.</h1>
          <p>Coordinate rooms, reservations, services, billing, and teams from a calm operational workspace built for hotel staff.</p>
          <div className="authMetrics">
            <span><strong>Live</strong> occupancy</span>
            <span><strong>Role</strong> dashboards</span>
            <span><strong>Oracle</strong> records</span>
          </div>
        </div>
      </section>
      <section className="authPanel">
        <div className="authCardHead">
          <div className="brandMark">MH</div>
          <div>
            <strong>Meridian HMS</strong>
            <span>Secure staff console</span>
          </div>
        </div>
        <h2>{mode === "login" ? "Welcome back" : "Create customer account"}</h2>
        <form onSubmit={submit} className="form">
          {mode === "register" && (
            <label>Name<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label>
          )}
          <label>Email<input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required /></label>
          <label>Password<input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required /></label>
          {mode === "register" && (
            <div className="split">
              <label>Code<input value={form.phone_country_code} onChange={(e) => setForm({ ...form, phone_country_code: e.target.value })} /></label>
              <label>Phone<input value={form.phone_number} onChange={(e) => setForm({ ...form, phone_number: e.target.value })} /></label>
            </div>
          )}
          {error && <p className="error">{error}</p>}
          <button className="primary" disabled={busy}>{busy ? "Working..." : mode === "login" ? "Sign in" : "Register"}</button>
        </form>
        <button className="linkButton" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "Create a customer account" : "Back to sign in"}
        </button>
      </section>
    </main>
  );
}

function Shell({ user, page, setPage, logout, children }) {
  const roles = user.roles || [];
  const visibleNav = navItems.filter((item) => item.roles.some((role) => roles.includes(role)));
  const activePage = visibleNav.find((item) => item.id === page) || visibleNav[0];
  return (
    <div className="appShell">
      <aside>
        <div className="sideBrand">
          <div className="brandMark">MH</div>
          <div><strong>Meridian HMS</strong><span>Hotel operations</span></div>
        </div>
        <nav>
          {visibleNav.map((item) => (
            <button key={item.id} className={page === item.id ? "active" : ""} onClick={() => setPage(item.id)}>
              <b>{item.code}</b>
              <span>{item.label}<small>{item.detail}</small></span>
            </button>
          ))}
        </nav>
        <div className="sidePanel">
          <span>Shift board</span>
          <strong>{new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}</strong>
          <small>{new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "short" })}</small>
        </div>
        <div className="userBox">
          <strong>{user.name}</strong>
          <span>{roles.map((role) => role.replace("ROLE_", "")).join(" / ")}</span>
          <button onClick={logout}>Sign out</button>
        </div>
      </aside>
      <main className="content">
        <header>
          <div>
            <p className="eyebrow">Meridian Hotel Management</p>
            <h1>{activePage?.label || "Overview"}</h1>
            <span className="pageDetail">{activePage?.detail}</span>
          </div>
          <div className="headerMeta">
            <span className="propertyChip">Bengaluru property</span>
            <span>{new Date().toLocaleDateString("en-IN", { dateStyle: "medium" })}</span>
            <Badge>{roles[0]?.replace("ROLE_", "") || "USER"}</Badge>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}

function Overview() {
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/dashboard/overview").then(setData).catch(console.error); }, []);
  if (!data) return <Loading />;
  const occupancyRate = data.total_rooms ? Math.round((Number(data.occupied_rooms || 0) / Number(data.total_rooms)) * 100) : 0;
  const availabilityRate = data.total_rooms ? Math.round((Number(data.available_rooms || 0) / Number(data.total_rooms)) * 100) : 0;
  return (
    <>
      <section className="opsBanner">
        <div>
          <p className="eyebrow">Today at a glance</p>
          <h2>{occupancyRate}% occupied</h2>
          <span>{data.available_rooms} rooms available, {data.pending_bookings} booking approvals waiting</span>
        </div>
        <div className="meterBlock">
          <div className="availabilityMeter" aria-label="Room availability meter">
            <i style={{ width: `${occupancyRate}%` }} />
          </div>
          <div className="meterLegend">
            <span>Occupied</span>
            <strong>{occupancyRate}%</strong>
          </div>
        </div>
        <div className="bannerStats">
          <span><strong>{availabilityRate}%</strong> availability</span>
          <span><strong>{currency(data.today_revenue)}</strong> today revenue</span>
        </div>
      </section>
      <section className="statsGrid">
        <StatCard label="Total rooms" value={data.total_rooms} note={`${data.available_rooms} available`} tone="teal" />
        <StatCard label="Occupied" value={data.occupied_rooms} note={`${data.maintenance_rooms} in maintenance`} tone="amber" />
        <StatCard label="Pending bookings" value={data.pending_bookings} note="Awaiting action" tone="rose" />
        <StatCard label="Month revenue" value={currency(data.month_revenue)} note={`Today ${currency(data.today_revenue)}`} tone="blue" />
      </section>
      <section className="panel">
        <div className="panelHead"><h2>Recent bookings</h2></div>
        <DataTable
          rows={data.recent_bookings || []}
          columns={[
            { key: "booking_id", label: "ID" },
            { key: "customer_name", label: "Guest" },
            { key: "room_number", label: "Room", render: (r) => `Room ${r.room_number}` },
            { key: "type_name", label: "Type" },
            { key: "check_in_date", label: "Check-in" },
            { key: "booking_status", label: "Status", render: (r) => <Badge>{r.booking_status}</Badge> }
          ]}
        />
      </section>
    </>
  );
}

function Rooms({ user }) {
  const [rooms, setRooms] = useState([]);
  const [types, setTypes] = useState([]);
  const [form, setForm] = useState({ room_number: "", room_type_id: "", floor: 1, status: "AVAILABLE" });
  const canEdit = (user.roles || []).some((role) => ["ROLE_ADMIN", "ROLE_MANAGER"].includes(role));
  const load = () => Promise.all([api.get("/rooms"), api.get("/rooms/types")]).then(([roomData, typeData]) => { setRooms(roomData); setTypes(typeData); });
  useEffect(() => { load().catch(console.error); }, []);
  async function addRoom(event) {
    event.preventDefault();
    await api.post("/rooms", { ...form, room_number: Number(form.room_number), room_type_id: Number(form.room_type_id), floor: Number(form.floor) });
    setForm({ room_number: "", room_type_id: "", floor: 1, status: "AVAILABLE" });
    load();
  }
  return (
    <section className="workspace">
      <div className="panel wide">
        <div className="panelHead"><h2>Room inventory</h2><span>{rooms.length} rooms</span></div>
        <DataTable
          rows={rooms}
          columns={[
            { key: "room_number", label: "Room", render: (r) => `Room ${r.room_number}` },
            { key: "type_name", label: "Type" },
            { key: "floor", label: "Floor" },
            { key: "capacity", label: "Capacity" },
            { key: "price_per_night", label: "Nightly", render: (r) => currency(r.price_per_night) },
            { key: "status", label: "Status", render: (r) => <Badge>{r.status}</Badge> }
          ]}
        />
      </div>
      {canEdit && (
        <form className="panel formPanel" onSubmit={addRoom}>
          <h2>Add room</h2>
          <label>Room number<input value={form.room_number} onChange={(e) => setForm({ ...form, room_number: e.target.value })} required /></label>
          <label>Room type<select value={form.room_type_id} onChange={(e) => setForm({ ...form, room_type_id: e.target.value })} required><option value="">Select</option>{types.map((type) => <option key={type.room_type_id} value={type.room_type_id}>{type.type_name}</option>)}</select></label>
          <label>Floor<input type="number" value={form.floor} onChange={(e) => setForm({ ...form, floor: e.target.value })} /></label>
          <label>Status<select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}><option>AVAILABLE</option><option>RESERVED</option><option>OCCUPIED</option><option>MAINTENANCE</option></select></label>
          <button className="primary">Add room</button>
        </form>
      )}
    </section>
  );
}

function Bookings({ user }) {
  const [bookings, setBookings] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [form, setForm] = useState({ room_id: "", check_in_date: "", check_out_date: "" });
  const roles = user.roles || [];
  const isCustomer = roles.includes("ROLE_CUSTOMER");
  const isOps = roles.some((role) => ["ROLE_ADMIN", "ROLE_MANAGER", "ROLE_STAFF"].includes(role));
  const load = () => Promise.all([api.get(`/bookings${isCustomer && !isOps ? "?mine=true" : ""}`), api.get("/rooms?status=AVAILABLE")]).then(([bookingData, roomData]) => { setBookings(bookingData); setRooms(roomData); });
  useEffect(() => { load().catch(console.error); }, []);
  async function book(event) {
    event.preventDefault();
    await api.post("/bookings", { ...form, room_id: Number(form.room_id) });
    setForm({ room_id: "", check_in_date: "", check_out_date: "" });
    load();
  }
  async function setStatus(row, status) {
    await api.patch(`/bookings/${row.booking_id}/status`, { status });
    load();
  }
  async function generateInvoice(row) {
    await api.post(`/billing/invoices/${row.booking_id}/generate`, {});
    load();
  }
  return (
    <section className="workspace">
      <div className="panel wide">
        <div className="panelHead"><h2>Booking lifecycle</h2><span>{bookings.length} records</span></div>
        <DataTable
          rows={bookings}
          columns={[
            { key: "booking_id", label: "ID" },
            { key: "customer_name", label: "Guest" },
            { key: "room_number", label: "Room", render: (r) => `Room ${r.room_number}` },
            { key: "check_in_date", label: "Check-in" },
            { key: "check_out_date", label: "Check-out" },
            { key: "booking_status", label: "Status", render: (r) => <Badge>{r.booking_status}</Badge> }
          ]}
          actions={(row) => (
            <>
              {isOps && row.booking_status === "PENDING" && <button onClick={() => setStatus(row, "APPROVED")}>Approve</button>}
              {isOps && row.booking_status === "CHECKIN_PENDING" && <button onClick={() => setStatus(row, "CHECKED_IN")}>Check in</button>}
              {isOps && row.booking_status === "CHECKOUT_PENDING" && <button onClick={() => setStatus(row, "CHECKED_OUT")}>Check out</button>}
              {isOps && ["CHECKED_IN", "CHECKED_OUT"].includes(row.booking_status) && <button onClick={() => generateInvoice(row)}>Invoice</button>}
              {isCustomer && row.booking_status === "APPROVED" && <button onClick={() => setStatus(row, "CHECKIN_PENDING")}>Request check-in</button>}
              {isCustomer && row.booking_status === "CHECKED_IN" && <button onClick={() => setStatus(row, "CHECKOUT_PENDING")}>Request check-out</button>}
            </>
          )}
        />
      </div>
      {isCustomer && (
        <form className="panel formPanel" onSubmit={book}>
          <h2>Book a room</h2>
          <label>Available room<select value={form.room_id} onChange={(e) => setForm({ ...form, room_id: e.target.value })} required><option value="">Select</option>{rooms.map((room) => <option key={room.room_id} value={room.room_id}>Room {room.room_number} - {room.type_name}</option>)}</select></label>
          <label>Check-in<input type="date" value={form.check_in_date} onChange={(e) => setForm({ ...form, check_in_date: e.target.value })} required /></label>
          <label>Check-out<input type="date" value={form.check_out_date} onChange={(e) => setForm({ ...form, check_out_date: e.target.value })} required /></label>
          <button className="primary">Create booking</button>
        </form>
      )}
    </section>
  );
}

function Billing({ user }) {
  const [invoices, setInvoices] = useState([]);
  const [methods, setMethods] = useState([]);
  const [payment, setPayment] = useState({ booking_id: "", method_id: "", amount: "" });
  const roles = user.roles || [];
  const isCustomer = roles.includes("ROLE_CUSTOMER") && !roles.some((role) => ["ROLE_ADMIN", "ROLE_MANAGER"].includes(role));
  const load = () => Promise.all([api.get(`/billing/invoices${isCustomer ? "?mine=true" : ""}`), api.get("/billing/methods")]).then(([invoiceData, methodData]) => { setInvoices(invoiceData); setMethods(methodData); });
  useEffect(() => { load().catch(console.error); }, []);
  async function pay(event) {
    event.preventDefault();
    await api.post("/billing/payments", { booking_id: Number(payment.booking_id), method_id: Number(payment.method_id), amount: Number(payment.amount) });
    setPayment({ booking_id: "", method_id: "", amount: "" });
    load();
  }
  async function generate(row) {
    await api.post(`/billing/invoices/${row.booking_id}/generate`, {});
    load();
  }
  return (
    <section className="workspace">
      <div className="panel wide">
        <div className="panelHead"><h2>Invoices and payments</h2><span>{invoices.length} invoices</span></div>
        <DataTable
          rows={invoices}
          columns={[
            { key: "invoice_id", label: "Invoice" },
            { key: "customer_name", label: "Guest" },
            { key: "room_number", label: "Room" },
            { key: "total_amount", label: "Subtotal", render: (r) => currency(r.total_amount) },
            { key: "tax", label: "Tax", render: (r) => currency(r.tax) },
            { key: "balance_due", label: "Due", render: (r) => currency(r.balance_due) }
          ]}
          actions={!isCustomer ? (row) => <button onClick={() => generate(row)}>Regenerate</button> : undefined}
        />
      </div>
      <form className="panel formPanel" onSubmit={pay}>
        <h2>Record payment</h2>
        <label>Booking ID<input value={payment.booking_id} onChange={(e) => setPayment({ ...payment, booking_id: e.target.value })} required /></label>
        <label>Method<select value={payment.method_id} onChange={(e) => setPayment({ ...payment, method_id: e.target.value })} required><option value="">Select</option>{methods.map((method) => <option key={method.method_id} value={method.method_id}>{method.method_name}</option>)}</select></label>
        <label>Amount<input value={payment.amount} onChange={(e) => setPayment({ ...payment, amount: e.target.value })} required /></label>
        <button className="primary">Save payment</button>
      </form>
    </section>
  );
}

function Services({ user }) {
  const [services, setServices] = useState([]);
  const [usage, setUsage] = useState([]);
  const [form, setForm] = useState({ booking_id: "", service_id: "", quantity: 1 });
  const roles = user.roles || [];
  const mine = roles.includes("ROLE_CUSTOMER") && !roles.some((role) => ["ROLE_ADMIN", "ROLE_MANAGER", "ROLE_STAFF"].includes(role));
  const load = () => Promise.all([api.get("/services"), api.get(`/services/usage${mine ? "?mine=true" : ""}`)]).then(([serviceData, usageData]) => { setServices(serviceData); setUsage(usageData); });
  useEffect(() => { load().catch(console.error); }, []);
  async function requestService(event) {
    event.preventDefault();
    await api.post("/services/usage", { booking_id: Number(form.booking_id), service_id: Number(form.service_id), quantity: Number(form.quantity) });
    setForm({ booking_id: "", service_id: "", quantity: 1 });
    load();
  }
  return (
    <section className="workspace">
      <div className="panel wide">
        <div className="panelHead"><h2>Service usage</h2><span>{usage.length} records</span></div>
        <DataTable
          rows={usage}
          columns={[
            { key: "usage_id", label: "ID" },
            { key: "customer_name", label: "Guest" },
            { key: "room_number", label: "Room" },
            { key: "service_name", label: "Service" },
            { key: "quantity", label: "Qty" },
            { key: "total_price", label: "Total", render: (r) => currency(r.total_price) }
          ]}
        />
      </div>
      <form className="panel formPanel" onSubmit={requestService}>
        <h2>Add service</h2>
        <label>Booking ID<input value={form.booking_id} onChange={(e) => setForm({ ...form, booking_id: e.target.value })} required /></label>
        <label>Service<select value={form.service_id} onChange={(e) => setForm({ ...form, service_id: e.target.value })} required><option value="">Select</option>{services.map((service) => <option key={service.service_id} value={service.service_id}>{service.service_name} - {currency(service.price)}</option>)}</select></label>
        <label>Quantity<input type="number" min="1" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} /></label>
        <button className="primary">Add service</button>
      </form>
    </section>
  );
}

function Staff() {
  const [data, setData] = useState({ staff: [], managers: [], departments: [], maintenance: [], customers: [] });
  useEffect(() => {
    Promise.all([api.get("/admin/staff"), api.get("/admin/managers"), api.get("/admin/departments"), api.get("/admin/maintenance"), api.get("/admin/customers")])
      .then(([staff, managers, departments, maintenance, customers]) => setData({ staff, managers, departments, maintenance, customers }))
      .catch(console.error);
  }, []);
  return (
    <div className="stack">
      <section className="panel">
        <div className="panelHead"><h2>Staff management</h2></div>
        <DataTable rows={data.staff} columns={[
          { key: "staff_id", label: "ID" },
          { key: "name", label: "Name" },
          { key: "department_name", label: "Department" },
          { key: "manager_name", label: "Manager" },
          { key: "job_description", label: "Title" },
          { key: "salary", label: "Salary", render: (r) => currency(r.salary) }
        ]} />
      </section>
      <section className="gridTwo">
        <div className="panel">
          <div className="panelHead"><h2>Customers</h2></div>
          <DataTable rows={data.customers} columns={[
            { key: "customer_id", label: "ID" },
            { key: "name", label: "Name" },
            { key: "email", label: "Email" },
            { key: "nationality", label: "Nationality" },
            { key: "loyalty_points", label: "Points" }
          ]} />
        </div>
        <div className="panel">
          <div className="panelHead"><h2>Departments</h2></div>
          <DataTable rows={data.departments} columns={[
            { key: "department_id", label: "ID" },
            { key: "department_name", label: "Department" },
            { key: "head_manager_name", label: "Head" }
          ]} />
        </div>
        <div className="panel">
          <div className="panelHead"><h2>Maintenance</h2></div>
          <DataTable rows={data.maintenance} columns={[
            { key: "room_number", label: "Room" },
            { key: "staff_name", label: "Staff" },
            { key: "description", label: "Issue" },
            { key: "status", label: "Status", render: (r) => <Badge>{r.status}</Badge> }
          ]} />
        </div>
      </section>
    </div>
  );
}

function Profile({ user }) {
  return (
    <section className="workspace">
      <div className="panel wide">
        <div className="panelHead"><h2>Account profile</h2><Badge>{user.roles?.[0]?.replace("ROLE_", "")}</Badge></div>
        <div className="profileGrid">
          <StatCard label="Name" value={user.name} />
          <StatCard label="Email" value={user.email || "Not set"} />
          <StatCard label="Phone" value={`${user.phone_country_code || ""} ${user.phone_number || ""}`.trim() || "Not set"} />
          <StatCard label="Customer ID" value={user.customer_id || "N/A"} />
        </div>
      </div>
      <div className="panel formPanel">
        <h2>Access scope</h2>
        <div className="roleList">
          {(user.roles || []).map((role) => <Badge key={role}>{role.replace("ROLE_", "")}</Badge>)}
        </div>
      </div>
    </section>
  );
}

function Reports() {
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/reports/summary").then(setData).catch(console.error); }, []);
  if (!data) return <Loading />;
  const blocks = [
    ["Revenue", data.revenue, currency],
    ["Bookings", data.bookings, (v) => v],
    ["Booking status", data.status_breakdown, (v) => v],
    ["Room types", data.room_types, (v) => v],
    ["Services", data.services, (v) => v]
  ];
  return (
    <section className="reportGrid">
      {blocks.map(([title, rows, format]) => (
        <div className="panel chartPanel" key={title}>
          <div className="panelHead"><h2>{title}</h2></div>
          <div className="bars">
            {(rows || []).map((row) => {
              const max = Math.max(...rows.map((item) => Number(item.value || 0)), 1);
              return (
                <div className="barRow" key={row.label}>
                  <span>{row.label}</span>
                  <div><i style={{ width: `${Math.max(8, (Number(row.value || 0) / max) * 100)}%` }} /></div>
                  <strong>{format(row.value)}</strong>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </section>
  );
}

function Loading() {
  return <div className="panel loading">Loading...</div>;
}

function App() {
  const [session, setSession] = useState(() => {
    const raw = localStorage.getItem("hms.session");
    return raw ? JSON.parse(raw) : null;
  });
  const [page, setPage] = useState("overview");

  useEffect(() => { setToken(session?.access_token || ""); }, [session]);
  const user = session?.user;
  const pageComponent = useMemo(() => {
    if (!user) return null;
    return {
      overview: <Overview />,
      rooms: <Rooms user={user} />,
      bookings: <Bookings user={user} />,
      billing: <Billing user={user} />,
      services: <Services user={user} />,
      staff: <Staff />,
      reports: <Reports />,
      profile: <Profile user={user} />
    }[page] || <Overview />;
  }, [page, user]);

  function onLogin(data) {
    localStorage.setItem("hms.session", JSON.stringify(data));
    setSession(data);
    setPage("overview");
  }

  function logout() {
    localStorage.removeItem("hms.session");
    setSession(null);
    setPage("overview");
  }

  if (!session) return <Login onLogin={onLogin} />;
  return <Shell user={user} page={page} setPage={setPage} logout={logout}>{pageComponent}</Shell>;
}

createRoot(document.getElementById("root")).render(<App />);
