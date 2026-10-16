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
import PageHeader from "../components/PageHeader";
import Toolbar from "../components/Toolbar";
import { fmtDate } from "../utils/format";

const EMPTY_FORM = {
  room_id: "",
  description: "",
  staff_id: "",
};

const STATUS_LABELS = {
  PENDING: "PENDING",
  IN_PROGRESS: "IN PROGRESS",
  COMPLETED: "COMPLETED",
};

export default function Maintenance() {
  const { hasRole } = useAuth();
  const { notify } = useToast();

  const isManagement = hasRole("ROLE_ADMIN") || hasRole("ROLE_MANAGER");

  const {
    data: maintenance,
    loading,
    error,
    reload,
  } = useFetch("/maintenance");

  const {
    data: rooms,
    loading: roomsLoading,
    error: roomsError,
  } = useFetch("/rooms");

  const {
    data: staff,
    loading: staffLoading,
    error: staffError,
    reload: reloadStaff,
  } = useFetch(isManagement ? "/staff" : "");

  const [statusFilter, setStatusFilter] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [mode, setMode] = useState("add");
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);

  const rows = maintenance || [];
  const roomRows = rooms || [];
  const staffRows = staff || [];

  const filteredRows = statusFilter
    ? rows.filter((row) => row.status === statusFilter)
    : rows;

  function openCreate() {
    setMode("add");
    setEditingId(null);
    setForm(EMPTY_FORM);
    setModalOpen(true);
  }

  function openEdit(row) {
    setMode("edit");
    setEditingId(row.maintenance_id);
    setForm({
      room_id: String(row.room_id ?? ""),
      description: row.description || "",
      staff_id: row.staff_id ? String(row.staff_id) : "",
    });
    setModalOpen(true);
  }

  const { run: createMaintenance, busy: createBusy } = useAction(async () => {
    const description = form.description.trim();

    if (!form.room_id) {
      notify("Room is required", "error");
      return null;
    }

    if (!description) {
      notify("Description is required", "error");
      return null;
    }

    const payload = {
      room_id: Number(form.room_id),
      description,
    };

    if (isManagement && form.staff_id) {
      payload.staff_id = Number(form.staff_id);
    }

    const result = await api.post("/maintenance", payload);

    notify("Maintenance request created", "success");
    setModalOpen(false);
    setForm(EMPTY_FORM);
    await Promise.all([
      reload(),
      isManagement ? reloadStaff() : Promise.resolve(),
    ]);
    return result;
  });

  const { run: updateMaintenance, busy: updateBusy } = useAction(async () => {
    const description = form.description.trim();

    if (!description) {
      notify("Description is required", "error");
      return null;
    }

    const payload = {
      description,
    };

    if (isManagement) {
      payload.staff_id = form.staff_id ? Number(form.staff_id) : null;
    }

    const result = await api.put(`/maintenance/${editingId}`, payload);

    notify("Maintenance request updated", "success");
    setModalOpen(false);
    setEditingId(null);
    setForm(EMPTY_FORM);
    await reload();
    return result;
  });

  const { run: updateStatus, busy: statusBusy } = useAction(
    async (maintenanceId, status) => {
      const result = await api.put(`/maintenance/${maintenanceId}`, { status });

      notify(
        status === "IN_PROGRESS"
          ? "Maintenance task started"
          : "Maintenance task completed",
        "success",
      );

      await reload();
      return result;
    },
  );

  if (loading || error) {
    return <PageState loading={loading} error={error} onRetry={reload} />;
  }

  return (
    <section className="workspace">
      <PageHeader
        eyebrow="Room Operations"
        title={isManagement ? "Maintenance Management" : "My Tasks"}
        subtitle={
          isManagement
            ? "Track and manage hotel room repair requests and housekeeping issues."
            : "View assigned maintenance tickets and update resolution progress."
        }
        primaryAction={
          <button type="button" className="primary" onClick={openCreate}>
            Report issue
          </button>
        }
      />

      <Toolbar
        filters={
          <label>
            Status
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              <option value="">All statuses</option>
              <option value="PENDING">PENDING</option>
              <option value="IN_PROGRESS">IN PROGRESS</option>
              <option value="COMPLETED">COMPLETED</option>
            </select>
          </label>
        }
        actions={<span>{filteredRows.length} tasks</span>}
      />

      <div className="panel wide">

        {roomsError && <p className="error">{roomsError}</p>}

        {staffError && isManagement && <p className="error">{staffError}</p>}

        <DataTable
          rows={filteredRows}
          columns={[
            {
              key: "room_number",
              label: "Room",
              render: (row) => `Room ${row.room_number}`,
            },
            {
              key: "description",
              label: "Issue",
            },
            {
              key: "staff_name",
              label: "Assigned to",
              render: (row) => row.staff_name || "Unassigned",
            },
            {
              key: "maintenance_date",
              label: "Date",
              render: (row) => fmtDate(row.maintenance_date),
            },
            {
              key: "status",
              label: "Status",
              render: (row) => (
                <Badge>{STATUS_LABELS[row.status] || row.status}</Badge>
              ),
            },
          ]}
          actions={(row) => (
            <div className="rowActions">
              {row.status === "PENDING" && (
                <button
                  type="button"
                  disabled={statusBusy}
                  onClick={() =>
                    updateStatus(row.maintenance_id, "IN_PROGRESS")
                  }
                >
                  Start
                </button>
              )}

              {row.status === "IN_PROGRESS" && (
                <button
                  type="button"
                  disabled={statusBusy}
                  onClick={() => updateStatus(row.maintenance_id, "COMPLETED")}
                >
                  Complete
                </button>
              )}

              {isManagement && row.status !== "COMPLETED" && (
                <button type="button" onClick={() => openEdit(row)}>
                  Edit
                </button>
              )}
            </div>
          )}
          empty={
            isManagement
              ? "No maintenance tasks found."
              : "No maintenance tasks assigned to you."
          }
        />
      </div>

      <Modal
        open={modalOpen}
        title={mode === "add" ? "Report issue" : "Edit maintenance"}
        onClose={() => {
          if (!createBusy && !updateBusy) {
            setModalOpen(false);
            setEditingId(null);
            setForm(EMPTY_FORM);
          }
        }}
      >
        <form
          className="form"
          onSubmit={(event) => {
            event.preventDefault();

            if (mode === "add") {
              createMaintenance();
            } else {
              updateMaintenance();
            }
          }}
        >
          {mode === "add" ? (
            <label>
              Room
              <select
                value={form.room_id}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    room_id: event.target.value,
                  }))
                }
                required
              >
                <option value="">
                  {roomsLoading ? "Loading rooms..." : "Select room"}
                </option>

                {roomRows.map((room) => (
                  <option key={room.room_id} value={room.room_id}>
                    Room {room.room_number} · {room.status}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <label>
              Room
              <input
                value={`Room ${
                  rows.find((row) => row.maintenance_id === editingId)
                    ?.room_number ?? ""
                }`}
                disabled
              />
            </label>
          )}

          <label>
            Issue
            <textarea
              rows="4"
              maxLength="255"
              value={form.description}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  description: event.target.value,
                }))
              }
              required
            />
          </label>

          {isManagement && (
            <label>
              Assign to
              <select
                value={form.staff_id}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    staff_id: event.target.value,
                  }))
                }
              >
                <option value="">
                  {staffLoading ? "Loading staff..." : "Unassigned"}
                </option>

                {staffRows.map((member) => (
                  <option key={member.staff_id} value={member.staff_id}>
                    {member.name}
                  </option>
                ))}
              </select>
            </label>
          )}

          <button
            type="submit"
            className="primary"
            disabled={createBusy || updateBusy}
          >
            {createBusy || updateBusy
              ? "Saving..."
              : mode === "add"
                ? "Report issue"
                : "Save changes"}
          </button>
        </form>
      </Modal>
    </section>
  );
}
