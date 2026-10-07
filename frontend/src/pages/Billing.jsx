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
import { currency, fmtDate } from "../utils/format";

function paymentStateLabel(value) {
  return String(value || "UNPAID").replaceAll("_", " ");
}

export default function Billing() {
  const { user, isOps } = useAuth();
  const { notify } = useToast();

  const isCustomer = Boolean(user?.roles?.includes("ROLE_CUSTOMER"));

  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [details, setDetails] = useState(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [detailsError, setDetailsError] = useState("");

  const [paymentModalOpen, setPaymentModalOpen] = useState(false);
  const [paymentForm, setPaymentForm] = useState({
    booking_id: "",
    method_id: "",
    amount: "",
  });

  const invoiceQuery = useMemo(() => {
    const params = new URLSearchParams();
    if (appliedSearch.trim()) params.set("search", appliedSearch.trim());
    const query = params.toString();
    return query ? `/billing/invoices?${query}` : "/billing/invoices";
  }, [appliedSearch]);

  const { data: invoices, loading, error, reload } = useFetch(invoiceQuery);

  const {
    data: methods,
    loading: methodsLoading,
    error: methodsError,
    reload: reloadMethods,
  } = useFetch("/billing/methods");

  const {
    data: payable,
    loading: payableLoading,
    error: payableError,
    reload: reloadPayable,
  } = useFetch("/billing/payable");

  const rows = invoices || [];
  const payableRows = payable || [];
  const methodRows = methods || [];

  const selectedPayable = payableRows.find(
    (row) => String(row.booking_id) === String(paymentForm.booking_id),
  );

  const { run: generateInvoice, busy: generateBusy } = useAction(
    async (bookingId) => {
      const result = await api.post(
        `/billing/invoices/${bookingId}/generate`,
        {},
      );
      notify("Invoice generated successfully", "success");
      await reload();
      if (selectedInvoice?.booking_id === bookingId) {
        await loadDetails(result || selectedInvoice);
      }
      return result;
    },
  );

  const { run: createPayment, busy: paymentBusy } = useAction(async () => {
    const amount = Number(paymentForm.amount);
    if (!Number.isFinite(amount) || amount <= 0) {
      notify("Payment amount must be greater than 0", "error");
      return null;
    }

    const result = await api.post("/billing/payments", {
      booking_id: Number(paymentForm.booking_id),
      method_id: Number(paymentForm.method_id),
      amount,
    });

    notify("Payment recorded successfully", "success");
    setPaymentForm({ booking_id: "", method_id: "", amount: "" });
    setPaymentModalOpen(false);
    await Promise.all([reload(), reloadPayable()]);
    if (selectedInvoice?.booking_id === result?.booking_id) {
      await loadDetails(selectedInvoice);
    }
    return result;
  });

  async function loadDetails(invoice) {
    if (!invoice) return;

    setSelectedInvoice(invoice);
    setDetailsLoading(true);
    setDetailsError("");

    try {
      const [payments, usage] = await Promise.all([
        api.get(`/billing/payments/${invoice.booking_id}`),
        api.get("/services/usage"),
      ]);

      const serviceRows = (usage || []).filter(
        (row) => Number(row.booking_id) === Number(invoice.booking_id),
      );

      const serviceTotal = serviceRows.reduce(
        (sum, row) => sum + Number(row.total_price || 0),
        0,
      );

      setDetails({
        invoice,
        payments: payments || [],
        services: serviceRows,
        roomCharge: Math.max(
          Number(invoice.total_amount || 0) - serviceTotal,
          0,
        ),
        serviceTotal,
      });
    } catch (err) {
      setDetailsError(err.message || "Unable to load invoice details");
      setDetails({
        invoice,
        payments: [],
        services: [],
        roomCharge: 0,
        serviceTotal: 0,
      });
    } finally {
      setDetailsLoading(false);
    }
  }

  function openPayment(bookingId = "") {
    setPaymentForm({
      booking_id: bookingId ? String(bookingId) : "",
      method_id: "",
      amount: "",
    });
    setPaymentModalOpen(true);
  }

  function closePayment() {
    if (paymentBusy) return;
    setPaymentModalOpen(false);
    setPaymentForm({ booking_id: "", method_id: "", amount: "" });
  }

  function handleSearch(event) {
    event.preventDefault();
    setAppliedSearch(search.trim());
  }

  if (loading || error) {
    return <PageState loading={loading} error={error} onRetry={reload} />;
  }

  return (
    <section className="workspace">
      <div className="panel wide">
        <div className="panelHead">
          <div>
            <p className="eyebrow">Finance</p>
            <h2>{isCustomer ? "My invoices" : "Invoices and payments"}</h2>
          </div>
          <div className="panelActions">
            <span>{rows.length} invoices</span>
            {payableRows.some((row) => Number(row.balance_due) > 0) && (
              <button
                type="button"
                className="primary"
                onClick={() => openPayment()}
              >
                Make payment
              </button>
            )}
          </div>
        </div>

        <div className="filterBar">
          <form onSubmit={handleSearch}>
            <label>
              Search
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={
                  isCustomer
                    ? "Invoice ID or room"
                    : "Guest, room or invoice ID"
                }
              />
            </label>
            <button type="submit" className="secondary">
              Search
            </button>
          </form>
        </div>

        <DataTable
          rows={rows}
          columns={[
            {
              key: "invoice_id",
              label: "Invoice",
              render: (row) => `#${row.invoice_id}`,
            },
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
            {
              key: "generated_date",
              label: "Generated",
              render: (row) => fmtDate(row.generated_date),
            },
            {
              key: "grand_total",
              label: "Total",
              render: (row) => currency(row.grand_total),
            },
            {
              key: "amount_paid",
              label: "Paid",
              render: (row) => currency(row.amount_paid),
            },
            {
              key: "balance_due",
              label: "Due",
              render: (row) => currency(row.balance_due),
            },
            {
              key: "payment_state",
              label: "Status",
              render: (row) => (
                <Badge>{paymentStateLabel(row.payment_state)}</Badge>
              ),
            },
          ]}
          actions={(row) => (
            <div className="rowActions">
              <button type="button" onClick={() => loadDetails(row)}>
                View
              </button>
              {Number(row.balance_due || 0) > 0 && (
                <button
                  type="button"
                  onClick={() => openPayment(row.booking_id)}
                >
                  Pay
                </button>
              )}
              {isOps && (
                <button
                  type="button"
                  onClick={() => generateInvoice(row.booking_id)}
                  disabled={generateBusy}
                >
                  {generateBusy ? "Updating..." : "Regenerate"}
                </button>
              )}
            </div>
          )}
          empty="No invoices found."
        />
      </div>

      <div className="gridTwo">
        <section className="panel">
          <div className="panelHead">
            <div>
              <p className="eyebrow">Outstanding</p>
              <h2>Payable bookings</h2>
            </div>
            <span>{payableRows.length} due</span>
          </div>

          {payableLoading && <p className="muted">Loading balances...</p>}
          {payableError && (
            <p className="error">
              {payableError}{" "}
              <button
                type="button"
                className="inlineButton"
                onClick={reloadPayable}
              >
                Retry
              </button>
            </p>
          )}

          <DataTable
            rows={payableRows}
            columns={[
              ...(isCustomer ? [] : [{ key: "customer_name", label: "Guest" }]),
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
                key: "booking_status",
                label: "Booking",
                render: (row) => <Badge>{row.booking_status}</Badge>,
              },
              {
                key: "balance_due",
                label: "Balance",
                render: (row) => currency(row.balance_due),
              },
            ]}
            actions={(row) => (
              <button type="button" onClick={() => openPayment(row.booking_id)}>
                Pay
              </button>
            )}
            empty="No outstanding balances."
          />
        </section>

        <section className="panel">
          <div className="panelHead">
            <div>
              <p className="eyebrow">Methods</p>
              <h2>Payment methods</h2>
            </div>
          </div>
          {methodsLoading ? (
            <p className="muted">Loading payment methods...</p>
          ) : methodsError ? (
            <p className="error">
              {methodsError}{" "}
              <button
                type="button"
                className="inlineButton"
                onClick={reloadMethods}
              >
                Retry
              </button>
            </p>
          ) : (
            <div className="roleList">
              {methodRows.map((method) => (
                <Badge key={method.method_id}>{method.method_name}</Badge>
              ))}
            </div>
          )}
        </section>
      </div>

      <Modal
        open={Boolean(selectedInvoice)}
        title={
          selectedInvoice ? `Invoice #${selectedInvoice.invoice_id}` : "Invoice"
        }
        onClose={() => {
          if (!detailsLoading) {
            setSelectedInvoice(null);
            setDetails(null);
            setDetailsError("");
          }
        }}
      >
        {detailsLoading && <p className="muted">Loading invoice details...</p>}

        {detailsError && <p className="error">{detailsError}</p>}

        {details && !detailsLoading && (
          <div className="stack">
            <div className="statsGrid">
              <div className="statCard">
                <span>Room charge</span>
                <strong>{currency(details.roomCharge)}</strong>
              </div>
              <div className="statCard">
                <span>Services</span>
                <strong>{currency(details.serviceTotal)}</strong>
              </div>
              <div className="statCard">
                <span>Subtotal</span>
                <strong>{currency(details.invoice.total_amount)}</strong>
              </div>
              <div className="statCard">
                <span>Tax</span>
                <strong>{currency(details.invoice.tax)}</strong>
              </div>
              <div className="statCard">
                <span>Grand total</span>
                <strong>{currency(details.invoice.grand_total)}</strong>
              </div>
              <div className="statCard">
                <span>Balance due</span>
                <strong>{currency(details.invoice.balance_due)}</strong>
              </div>
            </div>

            <section className="panel">
              <div className="panelHead">
                <h3>Service charges</h3>
              </div>
              <DataTable
                rows={details.services}
                columns={[
                  { key: "service_name", label: "Service" },
                  { key: "quantity", label: "Qty" },
                  {
                    key: "total_price",
                    label: "Total",
                    render: (row) => currency(row.total_price),
                  },
                ]}
                empty="No service charges for this booking."
              />
            </section>

            <section className="panel">
              <div className="panelHead">
                <h3>Payment history</h3>
              </div>
              <DataTable
                rows={details.payments}
                columns={[
                  { key: "payment_id", label: "ID" },
                  { key: "method_name", label: "Method" },
                  {
                    key: "amount",
                    label: "Amount",
                    render: (row) => currency(row.amount),
                  },
                  {
                    key: "payment_date",
                    label: "Date",
                    render: (row) => fmtDate(row.payment_date),
                  },
                  {
                    key: "status",
                    label: "Status",
                    render: (row) => <Badge>{row.status}</Badge>,
                  },
                ]}
                empty="No payments recorded yet."
              />
            </section>
          </div>
        )}
      </Modal>

      <Modal
        open={paymentModalOpen}
        title="Record payment"
        onClose={closePayment}
      >
        <form
          className="form"
          onSubmit={(event) => {
            event.preventDefault();
            createPayment();
          }}
        >
          <label>
            Booking
            <select
              value={paymentForm.booking_id}
              onChange={(event) =>
                setPaymentForm((current) => ({
                  ...current,
                  booking_id: event.target.value,
                  amount: "",
                }))
              }
              required
            >
              <option value="">
                {payableLoading ? "Loading bookings..." : "Select booking"}
              </option>
              {payableRows.map((row) => (
                <option key={row.booking_id} value={row.booking_id}>
                  Booking #{row.booking_id} · Room {row.room_number} ·{" "}
                  {currency(row.balance_due)} due
                </option>
              ))}
            </select>
          </label>

          {selectedPayable && (
            <div className="notice">
              <strong>{currency(selectedPayable.balance_due)}</strong> currently
              due.
            </div>
          )}

          <label>
            Payment method
            <select
              value={paymentForm.method_id}
              onChange={(event) =>
                setPaymentForm((current) => ({
                  ...current,
                  method_id: event.target.value,
                }))
              }
              required
            >
              <option value="">Select method</option>
              {methodRows.map((method) => (
                <option key={method.method_id} value={method.method_id}>
                  {method.method_name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Amount
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={paymentForm.amount}
              onChange={(event) =>
                setPaymentForm((current) => ({
                  ...current,
                  amount: event.target.value,
                }))
              }
              required
            />
          </label>

          <div className="panelActions">
            <button type="button" className="secondary" onClick={closePayment}>
              Cancel
            </button>
            <button type="submit" className="primary" disabled={paymentBusy}>
              {paymentBusy ? "Saving..." : "Record payment"}
            </button>
          </div>
        </form>
      </Modal>
    </section>
  );
}
