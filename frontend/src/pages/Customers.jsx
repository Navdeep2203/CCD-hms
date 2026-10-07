import { useState } from "react";

import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { useFetch } from "../hooks/useFetch";
import { useAction } from "../hooks/useAction";
import { useToast } from "../components/Toast";
import DataTable from "../components/DataTable";
import Badge from "../components/Badge";
import PageState from "../components/PageState";
import Modal from "../components/Modal";

const EMPTY_FORM = {
  name: "",
  email: "",
  phone_country_code: "+91",
  phone_number: "",
  temporary_password: "",
};

function generateTemporaryPassword(length = 12) {
  const letters = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
  const digits = "23456789";

  let result =
    letters[Math.floor(Math.random() * letters.length)] +
    digits[Math.floor(Math.random() * digits.length)];

  while (result.length < length) {
    const pool = `${letters}${digits}`;
    result += pool[Math.floor(Math.random() * pool.length)];
  }

  return result
    .split("")
    .sort(() => Math.random() - 0.5)
    .join("");
}

export default function Customers() {
  const { hasRole } = useAuth();
  const { notify } = useToast();

  const isManagement = hasRole("ROLE_ADMIN") || hasRole("ROLE_MANAGER");

  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [credentialModalOpen, setCredentialModalOpen] = useState(false);
  const [credentialInfo, setCredentialInfo] = useState(null);

  const path = appliedSearch
    ? `/customers?search=${encodeURIComponent(appliedSearch)}`
    : "/customers";

  const { data: customers, loading, error, reload } = useFetch(path);

  const rows = customers || [];

  function submitSearch(event) {
    event.preventDefault();
    setAppliedSearch(search.trim());
  }

  function clearSearch() {
    setSearch("");
    setAppliedSearch("");
  }

  function openCreateGuest() {
    setForm({
      ...EMPTY_FORM,
      temporary_password: generateTemporaryPassword(),
    });
    setModalOpen(true);
  }

  const { run: createGuest, busy } = useAction(async () => {
    const name = form.name.trim();
    const email = form.email.trim();
    const password = form.temporary_password;

    if (!name) {
      notify("Name is required", "error");
      return null;
    }

    if (!email) {
      notify("Email is required", "error");
      return null;
    }

    if (!password || password.length < 8 || password.length > 72) {
      notify("Temporary password must be 8 to 72 characters", "error");
      return null;
    }

    if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      notify("Temporary password must contain a letter and a digit", "error");
      return null;
    }

    const result = await api.post("/customers", {
      name,
      email,
      phone_country_code: form.phone_country_code || "+91",
      phone_number: form.phone_number || null,
      temporary_password: password,
    });

    setModalOpen(false);
    setForm(EMPTY_FORM);
    setCredentialInfo({
      name: result?.name || name,
      email: result?.email || email,
      password,
    });
    setCredentialModalOpen(true);

    notify("Guest created successfully", "success");
    await reload();
    return result;
  });

  if (loading || error) {
    return <PageState loading={loading} error={error} onRetry={reload} />;
  }

  return (
    <section className="workspace">
      <div className="panel wide">
        <div className="panelHead">
          <div>
            <p className="eyebrow">Guest records</p>
            <h2>Customers</h2>
          </div>

          <div className="panelActions">
            <span>{rows.length} guests</span>
            <button type="button" className="primary" onClick={openCreateGuest}>
              Create guest
            </button>
          </div>
        </div>

        <div className="filterBar">
          <form onSubmit={submitSearch}>
            <label>
              Search
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Name, email or phone"
              />
            </label>

            <button type="submit" className="secondary">
              Search
            </button>

            {appliedSearch && (
              <button type="button" onClick={clearSearch}>
                Clear
              </button>
            )}
          </form>
        </div>

        <DataTable
          rows={rows}
          columns={[
            { key: "name", label: "Name" },
            { key: "email", label: "Email" },
            {
              key: "phone_number",
              label: "Phone",
              render: (row) =>
                row.phone_number
                  ? `${row.phone_country_code || ""} ${row.phone_number}`
                  : "—",
            },
            { key: "nationality", label: "Nationality" },
            {
              key: "loyalty_points",
              label: "Loyalty points",
              render: (row) => row.loyalty_points ?? 0,
            },
            ...(isManagement
              ? [
                  {
                    key: "address",
                    label: "Address",
                    render: (row) => row.address || "—",
                  },
                  {
                    key: "id_proof",
                    label: "ID proof",
                    render: (row) => row.id_proof || "—",
                  },
                ]
              : []),
          ]}
          empty="No customers found."
        />
      </div>

      <Modal
        open={modalOpen}
        title="Create guest"
        onClose={() => {
          if (!busy) {
            setModalOpen(false);
            setForm(EMPTY_FORM);
          }
        }}
      >
        <form
          className="form"
          onSubmit={(event) => {
            event.preventDefault();
            createGuest();
          }}
        >
          <label>
            Name
            <input
              value={form.name}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  name: event.target.value,
                }))
              }
              required
            />
          </label>

          <label>
            Email
            <input
              type="email"
              value={form.email}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  email: event.target.value,
                }))
              }
              required
            />
          </label>

          <label>
            Phone country code
            <input
              value={form.phone_country_code}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  phone_country_code: event.target.value,
                }))
              }
            />
          </label>

          <label>
            Phone number
            <input
              value={form.phone_number}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  phone_number: event.target.value,
                }))
              }
            />
          </label>

          <label>
            Temporary password
            <div className="inlineControl">
              <input
                type="text"
                minLength="8"
                maxLength="72"
                value={form.temporary_password}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    temporary_password: event.target.value,
                  }))
                }
                required
              />
              <button
                type="button"
                onClick={() =>
                  setForm((current) => ({
                    ...current,
                    temporary_password: generateTemporaryPassword(),
                  }))
                }
              >
                Generate
              </button>
            </div>
          </label>

          <button type="submit" className="primary" disabled={busy}>
            {busy ? "Creating..." : "Create guest"}
          </button>
        </form>
      </Modal>

      <Modal
        open={credentialModalOpen}
        title="Guest created"
        onClose={() => {
          setCredentialModalOpen(false);
          setCredentialInfo(null);
        }}
      >
        {credentialInfo && (
          <div className="stack">
            <p>
              These are the guest&apos;s temporary credentials. The password is
              shown once so it can be handed over securely.
            </p>

            <div className="notice">
              <div>
                <strong>Email:</strong> {credentialInfo.email}
              </div>
              <div>
                <strong>Temporary password:</strong>{" "}
                <code>{credentialInfo.password}</code>
              </div>
            </div>

            <button
              type="button"
              className="primary"
              onClick={() => {
                setCredentialModalOpen(false);
                setCredentialInfo(null);
              }}
            >
              Done
            </button>
          </div>
        )}
      </Modal>
    </section>
  );
}
