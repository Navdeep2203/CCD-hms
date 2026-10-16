import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { useFetch } from "../hooks/useFetch";
import { useAction } from "../hooks/useAction";
import { useToast } from "../components/Toast";
import DataTable from "../components/DataTable";
import Badge from "../components/Badge";
import PageState from "../components/PageState";
import Modal from "../components/Modal";
import ConfirmDialog from "../components/ConfirmDialog";
import PageHeader from "../components/PageHeader";
import Toolbar from "../components/Toolbar";
import { addDays, currency, fmtDate, today } from "../utils/format";

const BOOKING_STATUSES = [
  "PENDING",
  "APPROVED",
  "REJECTED",
  "CHECKIN_PENDING",
  "CHECKED_IN",
  "CHECKOUT_PENDING",
  "CHECKED_OUT",
  "CANCELLED",
];

const createEmptyBookingForm = () => ({
  customer_id: "",
  room_id: "",
  check_in_date: today(),
  check_out_date: addDays(today(), 1),
});

const createEmptyGuestForm = () => ({
  name: "",
  email: "",
  phone_country_code: "+91",
  phone_number: "",
  temporary_password: "",
});

function displayStatus(status) {
  return String(status || "").replaceAll("_", " ");
}

export default function Bookings() {
  const navigate = useNavigate();
  const { user, isOps, isManagement } = useAuth();
  const { notify } = useToast();

  const isCustomer = user?.roles?.includes("ROLE_CUSTOMER");

  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");

  const [bookingModalOpen, setBookingModalOpen] = useState(false);
  const [bookingForm, setBookingForm] = useState(createEmptyBookingForm());

  const [customerSearch, setCustomerSearch] = useState("");
  const [appliedCustomerSearch, setAppliedCustomerSearch] = useState("");

  const [createGuestModalOpen, setCreateGuestModalOpen] = useState(false);
  const [guestForm, setGuestForm] = useState(createEmptyGuestForm());

  const [rejectBooking, setRejectBooking] = useState(null);
  const [rejectionReason, setRejectionReason] = useState("");

  const [overrideCheckoutBooking, setOverrideCheckoutBooking] = useState(null);

  const bookingQuery = useMemo(() => {
    const params = new URLSearchParams();

    if (appliedSearch.trim()) {
      params.set("search", appliedSearch.trim());
    }

    if (statusFilter) {
      params.set("status", statusFilter);
    }

    const query = params.toString();
    return query ? `/bookings?${query}` : "/bookings";
  }, [appliedSearch, statusFilter]);

  const { data: bookings, loading, error, reload } = useFetch(bookingQuery);

  const customerQuery =
    isOps && bookingModalOpen
      ? `/customers?search=${encodeURIComponent(appliedCustomerSearch)}`
      : "";

  const {
    data: customers,
    loading: customersLoading,
    error: customersError,
    reload: reloadCustomers,
  } = useFetch(customerQuery);

  const hasValidBookingDates =
    Boolean(bookingForm.check_in_date) &&
    Boolean(bookingForm.check_out_date) &&
    bookingForm.check_out_date > bookingForm.check_in_date;

  const roomQuery =
    isOps && bookingModalOpen && hasValidBookingDates
      ? `/rooms?check_in=${encodeURIComponent(
          bookingForm.check_in_date,
        )}&check_out=${encodeURIComponent(bookingForm.check_out_date)}`
      : "";

  const {
    data: rooms,
    loading: roomsLoading,
    error: roomsError,
    reload: reloadRooms,
  } = useFetch(roomQuery);

  const { run: createBooking, busy: createBookingBusy } = useAction(
    async () => {
      const payload = {
        room_id: Number(bookingForm.room_id),
        check_in_date: bookingForm.check_in_date,
        check_out_date: bookingForm.check_out_date,
        customer_id: Number(bookingForm.customer_id),
      };

      const result = await api.post("/bookings", payload);

      notify("Booking created successfully", "success");
      setBookingModalOpen(false);
      setBookingForm(createEmptyBookingForm());
      setCustomerSearch("");
      setAppliedCustomerSearch("");
      reload();

      return result;
    },
  );

  const { run: createGuest, busy: createGuestBusy } = useAction(async () => {
    const result = await api.post("/customers", {
      name: guestForm.name.trim(),
      email: guestForm.email.trim(),
      phone_country_code: guestForm.phone_country_code.trim() || null,
      phone_number: guestForm.phone_number.trim() || null,
      temporary_password: guestForm.temporary_password,
    });

    notify("Guest created successfully", "success");

    const returnedCustomerId = result?.customer_id;

    setBookingForm((current) => ({
      ...current,
      customer_id: returnedCustomerId ? String(returnedCustomerId) : "",
    }));

    setCustomerSearch(result?.email || "");
    setAppliedCustomerSearch(result?.email || "");
    setGuestForm(createEmptyGuestForm());
    setCreateGuestModalOpen(false);
    reloadCustomers();

    return result;
  });

  const { run: updateBookingStatus, busy: statusBusy } = useAction(
    async (bookingId, status, extra = {}) => {
      const result = await api.patch(`/bookings/${bookingId}/status`, {
        status,
        ...extra,
      });

      notify(
        `Booking ${displayStatus(status).toLowerCase()} successfully`,
        "success",
      );
      reload();

      return result;
    },
  );

  const { run: generateInvoice, busy: invoiceBusy } = useAction(
    async (bookingId) => {
      const result = await api.post(
        `/billing/invoices/${bookingId}/generate`,
        {},
      );

      notify("Invoice generated successfully", "success");
      reload();

      return result;
    },
  );

  const rows = bookings || [];
  const customerRows = customers || [];
  const roomRows = rooms || [];

  function openNewBooking() {
    setBookingForm(createEmptyBookingForm());
    setCustomerSearch("");
    setAppliedCustomerSearch("");
    setBookingModalOpen(true);
  }

  function closeBookingModal() {
    if (createBookingBusy) return;

    setBookingModalOpen(false);
    setBookingForm(createEmptyBookingForm());
    setCustomerSearch("");
    setAppliedCustomerSearch("");
  }

  function openCreateGuest() {
    setGuestForm(createEmptyGuestForm());
    setCreateGuestModalOpen(true);
  }

  function closeCreateGuest() {
    if (createGuestBusy) return;

    setCreateGuestModalOpen(false);
    setGuestForm(createEmptyGuestForm());
  }

  function openReject(booking) {
    setRejectBooking(booking);
    setRejectionReason("");
  }

  function closeReject() {
    if (statusBusy) return;

    setRejectBooking(null);
    setRejectionReason("");
  }

  function handleBookingSearch(event) {
    event.preventDefault();
    setAppliedSearch(search.trim());
  }

  function handleCustomerSearch(event) {
    event.preventDefault();
    setAppliedCustomerSearch(customerSearch.trim());
  }

  function handleCheckInChange(value) {
    setBookingForm((current) => ({
      ...current,
      check_in_date: value,
      check_out_date:
        !current.check_out_date || current.check_out_date <= value
          ? addDays(value, 1)
          : current.check_out_date,
      room_id: "",
    }));
  }

  function handleCheckOutChange(value) {
    setBookingForm((current) => ({
      ...current,
      check_out_date: value,
      room_id: "",
    }));
  }

  function validateBookingForm() {
    if (!bookingForm.customer_id) {
      notify("Choose the guest this booking is for", "error");
      return false;
    }

    if (!bookingForm.check_in_date || !bookingForm.check_out_date) {
      notify("Choose both booking dates", "error");
      return false;
    }

    if (bookingForm.check_out_date <= bookingForm.check_in_date) {
      notify("Check-out must be after check-in", "error");
      return false;
    }

    if (!bookingForm.room_id) {
      notify("Choose a room", "error");
      return false;
    }

    return true;
  }

  function validateGuestForm() {
    if (!guestForm.name.trim()) {
      notify("Guest name is required", "error");
      return false;
    }

    if (!guestForm.email.trim()) {
      notify("Guest email is required", "error");
      return false;
    }

    if (!guestForm.phone_country_code.trim()) {
      notify("Phone country code is required", "error");
      return false;
    }

    if (!guestForm.temporary_password) {
      notify("Temporary password is required", "error");
      return false;
    }

    return true;
  }

  async function handleCreateBookingSubmit(event) {
    event.preventDefault();

    if (!validateBookingForm()) return;

    try {
      await createBooking();
    } catch {
      // useAction displays the backend message in the error toast.
    }
  }

  async function handleCreateGuestSubmit(event) {
    event.preventDefault();

    if (!validateGuestForm()) return;

    try {
      await createGuest();
    } catch {
      // useAction displays the backend message in the error toast.
    }
  }

  async function handleRejectSubmit(event) {
    event.preventDefault();

    if (!rejectBooking) return;

    try {
      await updateBookingStatus(rejectBooking.booking_id, "REJECTED", {
        rejection_reason: rejectionReason.trim() || null,
      });
      setRejectBooking(null);
      setRejectionReason("");
    } catch {
      // useAction displays the backend message in the error toast.
    }
  }

  async function handleStatusAction(bookingId, status, extra = {}) {
    try {
      await updateBookingStatus(bookingId, status, extra);
    } catch {
      // useAction displays the backend message in the error toast.
    }
  }

  async function handleCheckout(booking) {
    try {
      await updateBookingStatus(booking.booking_id, "CHECKED_OUT");
    } catch (err) {
      if (
        isManagement &&
        String(err?.message || "")
          .toLowerCase()
          .includes("outstanding balance")
      ) {
        setOverrideCheckoutBooking(booking);
      }
    }
  }

  async function handleInvoice(booking) {
    try {
      await generateInvoice(booking.booking_id);
    } catch {
      // useAction displays the backend message in the error toast.
    }
  }

  async function handleOverrideCheckout() {
    if (!overrideCheckoutBooking) return;

    try {
      await updateBookingStatus(
        overrideCheckoutBooking.booking_id,
        "CHECKED_OUT",
        { override_balance: true },
      );
      setOverrideCheckoutBooking(null);
    } catch {
      // useAction displays the backend message in the error toast.
    }
  }

  if (loading || error) {
    return <PageState loading={loading} error={error} onRetry={reload} />;
  }

  return (
    <section className="workspace">
      <PageHeader
        eyebrow="Reservations"
        title={isCustomer ? "My Bookings" : "Booking Lifecycle"}
        subtitle={
          isCustomer
            ? "Track and manage your upcoming and past room reservations."
            : "Review booking requests, check guests in/out, and process invoices."
        }
        primaryAction={
          isCustomer ? (
            <button
              type="button"
              className="primary"
              onClick={() => navigate("/rooms")}
            >
              Book a room
            </button>
          ) : (
            <button
              type="button"
              className="primary"
              onClick={openNewBooking}
            >
              New booking
            </button>
          )
        }
      />

      <Toolbar
        search={search}
        onSearchChange={setSearch}
        onSearchSubmit={handleBookingSearch}
        searchPlaceholder={
          isCustomer ? "Booking ID or room" : "Guest, room or booking ID"
        }
        filters={
          <label>
            Status
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              <option value="">All statuses</option>
              {BOOKING_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {displayStatus(status)}
                </option>
              ))}
            </select>
          </label>
        }
        actions={<span>{rows.length} records</span>}
      />

      <div className="panel wide">

        <DataTable
          rows={rows}
          columns={[
            {
              key: "booking_id",
              label: "ID",
              render: (row) => `#${row.booking_id}`,
            },
            ...(!isCustomer
              ? [
                  {
                    key: "customer_name",
                    label: "Guest",
                  },
                ]
              : []),
            {
              key: "room_number",
              label: "Room",
              render: (row) => `Room ${row.room_number}`,
            },
            {
              key: "type_name",
              label: "Type",
            },
            {
              key: "check_in_date",
              label: "Check-in",
              render: (row) => fmtDate(row.check_in_date),
            },
            {
              key: "check_out_date",
              label: "Check-out",
              render: (row) => fmtDate(row.check_out_date),
            },
            {
              key: "nights",
              label: "Nights",
            },
            {
              key: "room_total",
              label: "Total",
              render: (row) => currency(row.room_total),
            },
            {
              key: "booking_status",
              label: "Status",
              render: (row) => <Badge>{row.booking_status}</Badge>,
            },
          ]}
          actions={(row) => {
            const actions = [];
            const status = row.booking_status;

            if (isCustomer) {
              if (["PENDING", "APPROVED", "CHECKIN_PENDING"].includes(status)) {
                actions.push(
                  <button
                    key="cancel"
                    type="button"
                    className="dangerButton"
                    onClick={() =>
                      handleStatusAction(row.booking_id, "CANCELLED")
                    }
                    disabled={statusBusy}
                  >
                    Cancel
                  </button>,
                );
              }

              if (status === "APPROVED") {
                actions.push(
                  <button
                    key="request-checkin"
                    type="button"
                    className="secondary"
                    onClick={() =>
                      handleStatusAction(row.booking_id, "CHECKIN_PENDING")
                    }
                    disabled={statusBusy}
                  >
                    Request check-in
                  </button>,
                );
              }

              if (status === "CHECKED_IN") {
                actions.push(
                  <button
                    key="request-checkout"
                    type="button"
                    className="secondary"
                    onClick={() =>
                      handleStatusAction(row.booking_id, "CHECKOUT_PENDING")
                    }
                    disabled={statusBusy}
                  >
                    Request check-out
                  </button>,
                );
              }
            }

            if (isOps) {
              if (status === "PENDING") {
                actions.push(
                  <button
                    key="approve"
                    type="button"
                    className="primary"
                    onClick={() =>
                      handleStatusAction(row.booking_id, "APPROVED")
                    }
                    disabled={statusBusy}
                  >
                    Approve
                  </button>,
                );

                actions.push(
                  <button
                    key="reject"
                    type="button"
                    className="dangerButton"
                    onClick={() => openReject(row)}
                    disabled={statusBusy}
                  >
                    Reject
                  </button>,
                );
              }

              if (["APPROVED", "CHECKIN_PENDING"].includes(status)) {
                actions.push(
                  <button
                    key="checkin"
                    type="button"
                    className="primary"
                    onClick={() =>
                      handleStatusAction(row.booking_id, "CHECKED_IN")
                    }
                    disabled={statusBusy}
                  >
                    Check in
                  </button>,
                );
              }

              if (["PENDING", "APPROVED", "CHECKIN_PENDING"].includes(status)) {
                actions.push(
                  <button
                    key="cancel"
                    type="button"
                    className="secondary"
                    onClick={() =>
                      handleStatusAction(row.booking_id, "CANCELLED")
                    }
                    disabled={statusBusy}
                  >
                    Cancel
                  </button>,
                );
              }

              if (["CHECKED_IN", "CHECKOUT_PENDING"].includes(status)) {
                actions.push(
                  <button
                    key="checkout"
                    type="button"
                    className="primary"
                    onClick={() => handleCheckout(row)}
                    disabled={statusBusy}
                  >
                    Check out
                  </button>,
                );

                actions.push(
                  <button
                    key="invoice"
                    type="button"
                    className="secondary"
                    onClick={() => handleInvoice(row)}
                    disabled={invoiceBusy}
                  >
                    Invoice
                  </button>,
                );
              }
            }

            return actions.length ? (
              <div className="rowActions">{actions}</div>
            ) : null;
          }}
          empty="No bookings found."
        />
      </div>

      {!isCustomer && (
        <>
          <Modal
            open={bookingModalOpen}
            title="New booking"
            onClose={closeBookingModal}
          >
            <form className="form" onSubmit={handleCreateBookingSubmit}>
              <label>
                Guest
                <div className="inlineForm">
                  <input
                    type="search"
                    value={customerSearch}
                    onChange={(event) => setCustomerSearch(event.target.value)}
                    placeholder="Search by name, email or phone"
                  />
                  <button
                    type="button"
                    className="secondary"
                    onClick={handleCustomerSearch}
                    disabled={customersLoading}
                  >
                    Search
                  </button>
                </div>
                <select
                  value={bookingForm.customer_id}
                  onChange={(event) =>
                    setBookingForm((current) => ({
                      ...current,
                      customer_id: event.target.value,
                    }))
                  }
                  disabled={customersLoading}
                  required
                >
                  <option value="">
                    {customersLoading ? "Loading guests..." : "Select guest"}
                  </option>

                  {customerRows.map((customer) => (
                    <option
                      key={customer.customer_id}
                      value={customer.customer_id}
                    >
                      {customer.name} · {customer.email || "No email"}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="inlineButton"
                  onClick={openCreateGuest}
                >
                  Create guest
                </button>
                {customersError && (
                  <small className="fieldError">
                    {customersError}{" "}
                    <button
                      type="button"
                      className="inlineButton"
                      onClick={reloadCustomers}
                    >
                      Retry
                    </button>
                  </small>
                )}
              </label>

              <label>
                Check-in
                <input
                  type="date"
                  value={bookingForm.check_in_date}
                  min={today()}
                  max={addDays(today(), 30)}
                  onChange={(event) => handleCheckInChange(event.target.value)}
                  required
                />
              </label>

              <label>
                Check-out
                <input
                  type="date"
                  value={bookingForm.check_out_date}
                  min={addDays(bookingForm.check_in_date || today(), 1)}
                  max={addDays(bookingForm.check_in_date || today(), 30)}
                  onChange={(event) => handleCheckOutChange(event.target.value)}
                  required
                />
              </label>

              <label>
                Room
                <select
                  value={bookingForm.room_id}
                  onChange={(event) =>
                    setBookingForm((current) => ({
                      ...current,
                      room_id: event.target.value,
                    }))
                  }
                  disabled={
                    roomsLoading || !hasValidBookingDates || Boolean(roomsError)
                  }
                  required
                >
                  <option value="">
                    {roomsLoading ? "Loading rooms..." : "Select room"}
                  </option>

                  {roomRows.map((room) => (
                    <option key={room.room_id} value={room.room_id}>
                      Room {room.room_number} · {room.type_name} ·{" "}
                      {currency(room.price_per_night)}/night
                    </option>
                  ))}
                </select>
                {roomsError && (
                  <small className="fieldError">
                    {roomsError}{" "}
                    <button
                      type="button"
                      className="inlineButton"
                      onClick={reloadRooms}
                    >
                      Retry
                    </button>
                  </small>
                )}
                {!roomsLoading &&
                  !roomsError &&
                  hasValidBookingDates &&
                  roomRows.length === 0 && (
                    <small className="fieldHint">
                      No rooms are available for those dates.
                    </small>
                  )}
              </label>

              <div className="formActions">
                <button
                  type="button"
                  className="secondary"
                  onClick={closeBookingModal}
                  disabled={createBookingBusy}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="primary"
                  disabled={createBookingBusy}
                >
                  {createBookingBusy ? "Creating..." : "Create booking"}
                </button>
              </div>
            </form>
          </Modal>

          <Modal
            open={createGuestModalOpen}
            title="Create guest"
            onClose={closeCreateGuest}
          >
            <form className="form" onSubmit={handleCreateGuestSubmit}>
              <label>
                Name
                <input
                  value={guestForm.name}
                  onChange={(event) =>
                    setGuestForm((current) => ({
                      ...current,
                      name: event.target.value,
                    }))
                  }
                  maxLength="100"
                  required
                />
              </label>

              <label>
                Email
                <input
                  type="email"
                  value={guestForm.email}
                  onChange={(event) =>
                    setGuestForm((current) => ({
                      ...current,
                      email: event.target.value,
                    }))
                  }
                  maxLength="100"
                  required
                />
              </label>

              <label>
                Phone country code
                <input
                  value={guestForm.phone_country_code}
                  onChange={(event) =>
                    setGuestForm((current) => ({
                      ...current,
                      phone_country_code: event.target.value,
                    }))
                  }
                  placeholder="+91"
                  pattern="^\+\d{1,4}$"
                  required
                />
              </label>

              <label>
                Phone number
                <input
                  value={guestForm.phone_number}
                  onChange={(event) =>
                    setGuestForm((current) => ({
                      ...current,
                      phone_number: event.target.value,
                    }))
                  }
                  placeholder="Optional"
                  inputMode="numeric"
                  pattern="\d{6,15}"
                />
              </label>

              <label>
                Temporary password
                <input
                  type="password"
                  value={guestForm.temporary_password}
                  onChange={(event) =>
                    setGuestForm((current) => ({
                      ...current,
                      temporary_password: event.target.value,
                    }))
                  }
                  minLength="8"
                  maxLength="72"
                  pattern="(?=.*[A-Za-z])(?=.*\d).{8,72}"
                  required
                />
                <small className="fieldHint">
                  At least 8 characters with a letter and a digit.
                </small>
              </label>

              <div className="formActions">
                <button
                  type="button"
                  className="secondary"
                  onClick={closeCreateGuest}
                  disabled={createGuestBusy}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="primary"
                  disabled={createGuestBusy}
                >
                  {createGuestBusy ? "Creating..." : "Create guest"}
                </button>
              </div>
            </form>
          </Modal>

          <Modal
            open={Boolean(rejectBooking)}
            title="Reject booking"
            onClose={closeReject}
          >
            <form className="form" onSubmit={handleRejectSubmit}>
              <p>
                Reject booking #{rejectBooking?.booking_id}
                {rejectBooking?.customer_name
                  ? ` for ${rejectBooking.customer_name}.`
                  : "."}
              </p>

              <label>
                Reason (optional)
                <textarea
                  rows="4"
                  maxLength="255"
                  value={rejectionReason}
                  onChange={(event) => setRejectionReason(event.target.value)}
                  placeholder="Optional rejection reason"
                />
              </label>

              <div className="formActions">
                <button
                  type="button"
                  className="secondary"
                  onClick={closeReject}
                  disabled={statusBusy}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="dangerButton"
                  disabled={statusBusy}
                >
                  {statusBusy ? "Rejecting..." : "Reject"}
                </button>
              </div>
            </form>
          </Modal>

          <ConfirmDialog
            open={Boolean(overrideCheckoutBooking)}
            title="Check out anyway"
            message={
              overrideCheckoutBooking
                ? `Booking #${overrideCheckoutBooking.booking_id} has an outstanding balance. Check out anyway?`
                : "Check out anyway?"
            }
            confirmLabel="Check out anyway"
            cancelLabel="Cancel"
            onCancel={() => setOverrideCheckoutBooking(null)}
            onConfirm={handleOverrideCheckout}
          />
        </>
      )}
    </section>
  );
}
