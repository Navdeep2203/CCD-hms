import { useMemo, useState } from "react";

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
import { currency, fmtDate } from "../utils/format";

const EMPTY_SERVICE_FORM = {
  service_name: "",
  price: "",
};

const EMPTY_USAGE_FORM = {
  booking_id: "",
  service_id: "",
  quantity: "1",
};

function bookingLabel(booking) {
  const guest = booking.customer_name ? ` · ${booking.customer_name}` : "";
  const room = booking.room_number ? ` · Room ${booking.room_number}` : "";
  return `Booking #${booking.booking_id}${room}${guest}`;
}

export default function Services() {
  const { user, isOps, isManagement } = useAuth();
  const { notify } = useToast();

  const isCustomer = Boolean(user?.roles?.includes("ROLE_CUSTOMER"));

  const {
    data: services,
    loading: servicesLoading,
    error: servicesError,
    reload: reloadServices,
  } = useFetch("/services");

  const {
    data: usage,
    loading: usageLoading,
    error: usageError,
    reload: reloadUsage,
  } = useFetch("/services/usage");

  const {
    data: checkedInBookings,
    loading: bookingsLoading,
    error: bookingsError,
    reload: reloadBookings,
  } = useFetch("/bookings?status=CHECKED_IN");

  const [usageModalOpen, setUsageModalOpen] = useState(false);
  const [usageForm, setUsageForm] = useState(EMPTY_USAGE_FORM);

  const [serviceModalOpen, setServiceModalOpen] = useState(false);
  const [serviceMode, setServiceMode] = useState("add");
  const [editingServiceId, setEditingServiceId] = useState(null);
  const [serviceForm, setServiceForm] = useState(EMPTY_SERVICE_FORM);
  const [deleteServiceId, setDeleteServiceId] = useState(null);

  const serviceRows = services || [];
  const usageRows = usage || [];
  const bookingRows = checkedInBookings || [];

  const selectedService = useMemo(
    () =>
      serviceRows.find(
        (row) => String(row.service_id) === String(usageForm.service_id),
      ),
    [serviceRows, usageForm.service_id],
  );

  function openAddUsage() {
    setUsageForm({
      ...EMPTY_USAGE_FORM,
      booking_id:
        bookingRows.length === 1 ? String(bookingRows[0].booking_id) : "",
    });
    setUsageModalOpen(true);
  }

  function openAddService() {
    setServiceMode("add");
    setEditingServiceId(null);
    setServiceForm(EMPTY_SERVICE_FORM);
    setServiceModalOpen(true);
  }

  function openEditService(service) {
    setServiceMode("edit");
    setEditingServiceId(service.service_id);
    setServiceForm({
      service_name: service.service_name || "",
      price: String(service.price ?? ""),
    });
    setServiceModalOpen(true);
  }

  const { run: addUsage, busy: usageBusy } = useAction(async () => {
    const bookingId = Number(usageForm.booking_id);
    const serviceId = Number(usageForm.service_id);
    const quantity = Number(usageForm.quantity);

    if (!Number.isInteger(bookingId) || bookingId <= 0) {
      notify("Please select a booking", "error");
      return null;
    }

    if (!Number.isInteger(serviceId) || serviceId <= 0) {
      notify("Please select a service", "error");
      return null;
    }

    if (!Number.isInteger(quantity) || quantity < 1 || quantity > 100) {
      notify("Quantity must be between 1 and 100", "error");
      return null;
    }

    const result = await api.post("/services/usage", {
      booking_id: bookingId,
      service_id: serviceId,
      quantity,
    });

    notify("Service added successfully", "success");
    setUsageModalOpen(false);
    setUsageForm(EMPTY_USAGE_FORM);
    await Promise.all([reloadUsage(), reloadBookings()]);
    return result;
  });

  const { run: saveService, busy: serviceSaveBusy } = useAction(async () => {
    const serviceName = serviceForm.service_name.trim();
    const price = Number(serviceForm.price);

    if (!serviceName) {
      notify("Service name is required", "error");
      return null;
    }

    if (serviceName.length > 100) {
      notify("Service name must be at most 100 characters", "error");
      return null;
    }

    if (!Number.isFinite(price) || price <= 0) {
      notify("Service price must be greater than 0", "error");
      return null;
    }

    const payload = {
      service_name: serviceName,
      price,
    };

    const result =
      serviceMode === "add"
        ? await api.post("/services", payload)
        : await api.put(`/services/${editingServiceId}`, payload);

    notify(
      serviceMode === "add"
        ? "Service added successfully"
        : "Service updated successfully",
      "success",
    );

    setServiceModalOpen(false);
    setEditingServiceId(null);
    setServiceForm(EMPTY_SERVICE_FORM);
    await reloadServices();
    return result;
  });

  const { run: deleteService, busy: deleteBusy } = useAction(
    async (serviceId) => {
      const result = await api.delete(`/services/${serviceId}`);
      notify("Service deleted successfully", "success");
      setDeleteServiceId(null);
      await reloadServices();
      return result;
    },
  );

  if (servicesLoading || servicesError) {
    return (
      <PageState
        loading={servicesLoading}
        error={servicesError}
        onRetry={reloadServices}
      />
    );
  }

  return (
    <section className="workspace">
      <div className="panel wide">
        <div className="panelHead">
          <div>
            <p className="eyebrow">Hotel services</p>
            <h2>{isCustomer ? "My service usage" : "Service usage"}</h2>
          </div>

          <div className="panelActions">
            <span>{usageRows.length} records</span>
            <button
              type="button"
              className="primary"
              onClick={openAddUsage}
              disabled={bookingRows.length === 0 || serviceRows.length === 0}
            >
              Add service
            </button>

            {isManagement && (
              <button type="button" onClick={openAddService}>
                Manage services
              </button>
            )}
          </div>
        </div>

        {bookingsError && (
          <p className="error">
            {bookingsError}{" "}
            <button
              type="button"
              className="inlineButton"
              onClick={reloadBookings}
            >
              Retry
            </button>
          </p>
        )}

        {bookingRows.length === 0 && (
          <p className="muted">
            {isCustomer
              ? "You can add services only while you have a checked-in booking."
              : "There are currently no checked-in bookings available for service usage."}
          </p>
        )}

        <DataTable
          rows={usageRows}
          columns={[
            { key: "usage_id", label: "ID" },
            ...(!isCustomer ? [{ key: "customer_name", label: "Guest" }] : []),
            {
              key: "booking_id",
              label: "Booking",
              render: (row) => `#${row.booking_id}`,
            },
            {
              key: "room_number",
              label: "Room",
              render: (row) => `Room ${row.room_number}`,
            },
            { key: "service_name", label: "Service" },
            { key: "quantity", label: "Qty" },
            {
              key: "total_price",
              label: "Total",
              render: (row) => currency(row.total_price),
            },
            {
              key: "booking_status",
              label: "Status",
              render: (row) => <Badge>{row.booking_status}</Badge>,
            },
          ]}
          empty="No service usage recorded."
        />
      </div>

      <div className="gridTwo">
        <section className="panel">
          <div className="panelHead">
            <div>
              <p className="eyebrow">Available services</p>
              <h2>Service catalogue</h2>
            </div>
            <span>{serviceRows.length} services</span>
          </div>

          <DataTable
            rows={serviceRows}
            columns={[
              { key: "service_name", label: "Service" },
              {
                key: "price",
                label: "Price",
                render: (row) => currency(row.price),
              },
            ]}
            actions={
              isManagement
                ? (row) => (
                    <div className="rowActions">
                      <button
                        type="button"
                        onClick={() => openEditService(row)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeleteServiceId(row.service_id)}
                      >
                        Delete
                      </button>
                    </div>
                  )
                : undefined
            }
            empty="No services configured."
          />
        </section>

        <section className="panel">
          <div className="panelHead">
            <div>
              <p className="eyebrow">Current booking context</p>
              <h2>Checked-in bookings</h2>
            </div>
            <span>{bookingRows.length}</span>
          </div>

          {bookingsLoading ? (
            <p className="muted">Loading checked-in bookings...</p>
          ) : bookingsError ? (
            <p className="error">{bookingsError}</p>
          ) : (
            <DataTable
              rows={bookingRows}
              columns={[
                ...(isCustomer
                  ? []
                  : [{ key: "customer_name", label: "Guest" }]),
                {
                  key: "booking_id",
                  label: "Booking",
                  render: (row) => `#${row.booking_id}`,
                },
                {
                  key: "room_number",
                  label: "Room",
                  render: (row) => `Room ${row.room_number}`,
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
                  key: "booking_status",
                  label: "Status",
                  render: (row) => <Badge>{row.booking_status}</Badge>,
                },
              ]}
              empty="No checked-in bookings."
            />
          )}
        </section>
      </div>

      <Modal
        open={usageModalOpen}
        title="Add service"
        onClose={() => {
          if (!usageBusy) {
            setUsageModalOpen(false);
            setUsageForm(EMPTY_USAGE_FORM);
          }
        }}
      >
        <form
          className="form"
          onSubmit={(event) => {
            event.preventDefault();
            addUsage();
          }}
        >
          <label>
            Booking
            <select
              value={usageForm.booking_id}
              onChange={(event) =>
                setUsageForm((current) => ({
                  ...current,
                  booking_id: event.target.value,
                }))
              }
              required
            >
              <option value="">Select booking</option>
              {bookingRows.map((booking) => (
                <option key={booking.booking_id} value={booking.booking_id}>
                  {bookingLabel(booking)}
                </option>
              ))}
            </select>
          </label>

          <label>
            Service
            <select
              value={usageForm.service_id}
              onChange={(event) =>
                setUsageForm((current) => ({
                  ...current,
                  service_id: event.target.value,
                }))
              }
              required
            >
              <option value="">Select service</option>
              {serviceRows.map((service) => (
                <option key={service.service_id} value={service.service_id}>
                  {service.service_name} · {currency(service.price)}
                </option>
              ))}
            </select>
          </label>

          <label>
            Quantity
            <input
              type="number"
              min="1"
              max="100"
              value={usageForm.quantity}
              onChange={(event) =>
                setUsageForm((current) => ({
                  ...current,
                  quantity: event.target.value,
                }))
              }
              required
            />
          </label>

          {selectedService && (
            <div className="notice">
              Unit price: <strong>{currency(selectedService.price)}</strong>
              {" · "}
              Estimated total:{" "}
              <strong>
                {currency(
                  Number(selectedService.price) *
                    Number(usageForm.quantity || 0),
                )}
              </strong>
            </div>
          )}

          <button type="submit" className="primary" disabled={usageBusy}>
            {usageBusy ? "Adding..." : "Add service"}
          </button>
        </form>
      </Modal>

      <Modal
        open={serviceModalOpen}
        title={serviceMode === "add" ? "Add service" : "Edit service"}
        onClose={() => {
          if (!serviceSaveBusy) {
            setServiceModalOpen(false);
            setEditingServiceId(null);
            setServiceForm(EMPTY_SERVICE_FORM);
          }
        }}
      >
        <form
          className="form"
          onSubmit={(event) => {
            event.preventDefault();
            saveService();
          }}
        >
          <label>
            Service name
            <input
              value={serviceForm.service_name}
              maxLength={100}
              onChange={(event) =>
                setServiceForm((current) => ({
                  ...current,
                  service_name: event.target.value,
                }))
              }
              required
            />
          </label>

          <label>
            Price
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={serviceForm.price}
              onChange={(event) =>
                setServiceForm((current) => ({
                  ...current,
                  price: event.target.value,
                }))
              }
              required
            />
          </label>

          <button type="submit" className="primary" disabled={serviceSaveBusy}>
            {serviceSaveBusy
              ? serviceMode === "add"
                ? "Adding..."
                : "Saving..."
              : serviceMode === "add"
                ? "Add service"
                : "Save changes"}
          </button>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(deleteServiceId)}
        title="Delete service"
        message="Delete this service from the catalogue?"
        confirmLabel="Delete"
        busy={deleteBusy}
        onCancel={() => {
          if (!deleteBusy) setDeleteServiceId(null);
        }}
        onConfirm={() => deleteService(deleteServiceId)}
      />
    </section>
  );
}
