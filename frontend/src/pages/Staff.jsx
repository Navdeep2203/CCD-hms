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
import Tabs from "../components/Tabs";
import PageHeader from "../components/PageHeader";
import Toolbar from "../components/Toolbar";
import { currency } from "../utils/format";

const STAFF_EMPTY = {
  name: "",
  email: "",
  phone_country_code: "+91",
  phone_number: "",
  department_id: "",
  job_description: "",
  salary: "",
  temporary_password: "",
  manager_id: "",
};

const MANAGER_EMPTY = {
  name: "",
  email: "",
  phone_country_code: "+91",
  phone_number: "",
  department_id: "",
  reports_to_manager_id: "",
  job_description: "",
  salary: "",
  temporary_password: "",
};

const DEPARTMENT_EMPTY = {
  department_name: "",
  head_manager_id: "",
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

function changedFields(original, current, keys) {
  const payload = {};
  for (const key of keys) {
    if (String(original[key] ?? "") !== String(current[key] ?? "")) {
      if (
        key === "phone_number" ||
        key === "phone_country_code" ||
        key === "job_description"
      ) {
        payload[key] = current[key] || null;
      } else if (
        key === "department_id" ||
        key === "manager_id" ||
        key === "salary"
      ) {
        payload[key] = current[key] === "" ? null : Number(current[key]);
      } else {
        payload[key] = current[key];
      }
    }
  }
  return payload;
}

export default function Staff() {
  const { user, hasRole } = useAuth();
  const { notify } = useToast();

  const isAdmin = hasRole("ROLE_ADMIN");
  const isManager = hasRole("ROLE_MANAGER");

  const [activeTab, setActiveTab] = useState("staff");

  const [staffSearch, setStaffSearch] = useState("");
  const [staffDepartmentId, setStaffDepartmentId] = useState("");
  const [staffActive, setStaffActive] = useState("");
  const [staffQuery, setStaffQuery] = useState({
    search: "",
    department_id: "",
    active: "",
  });

  const staffPath = useMemo(() => {
    const params = new URLSearchParams();
    if (staffQuery.search) params.set("search", staffQuery.search);
    if (staffQuery.department_id) {
      params.set("department_id", staffQuery.department_id);
    }
    if (staffQuery.active !== "") params.set("active", staffQuery.active);

    const suffix = params.toString();
    return `/staff${suffix ? `?${suffix}` : ""}`;
  }, [staffQuery]);

  const {
    data: staff,
    loading: staffLoading,
    error: staffError,
    reload: reloadStaff,
  } = useFetch(staffPath);

  const {
    data: departments,
    loading: departmentsLoading,
    error: departmentsError,
    reload: reloadDepartments,
  } = useFetch("/departments");

  const {
    data: managers,
    loading: managersLoading,
    error: managersError,
    reload: reloadManagers,
  } = useFetch(isAdmin ? "/managers" : "");

  const [staffModalOpen, setStaffModalOpen] = useState(false);
  const [staffMode, setStaffMode] = useState("add");
  const [editingStaffId, setEditingStaffId] = useState(null);
  const [staffForm, setStaffForm] = useState(STAFF_EMPTY);
  const [staffOriginal, setStaffOriginal] = useState(STAFF_EMPTY);

  const [managerModalOpen, setManagerModalOpen] = useState(false);
  const [managerMode, setManagerMode] = useState("add");
  const [editingManagerId, setEditingManagerId] = useState(null);
  const [managerForm, setManagerForm] = useState(MANAGER_EMPTY);
  const [managerOriginal, setManagerOriginal] = useState(MANAGER_EMPTY);

  const [departmentModalOpen, setDepartmentModalOpen] = useState(false);
  const [departmentMode, setDepartmentMode] = useState("add");
  const [editingDepartmentId, setEditingDepartmentId] = useState(null);
  const [departmentForm, setDepartmentForm] = useState(DEPARTMENT_EMPTY);

  const [confirmAction, setConfirmAction] = useState(null);
  const [resetModalOpen, setResetModalOpen] = useState(false);
  const [resetTarget, setResetTarget] = useState(null);
  const [resetPassword, setResetPassword] = useState("");
  const [credentialModalOpen, setCredentialModalOpen] = useState(false);
  const [credentialInfo, setCredentialInfo] = useState(null);

  function refreshPeople() {
    return Promise.all([
      reloadStaff(),
      isAdmin ? reloadManagers() : Promise.resolve(),
      reloadDepartments(),
    ]);
  }

  function updateStaffFilter(event) {
    event.preventDefault();
    setStaffQuery({
      search: staffSearch.trim(),
      department_id: staffDepartmentId,
      active: staffActive,
    });
  }

  function clearStaffFilter() {
    setStaffSearch("");
    setStaffDepartmentId("");
    setStaffActive("");
    setStaffQuery({
      search: "",
      department_id: "",
      active: "",
    });
  }

  function openAddStaff() {
    setStaffMode("add");
    setEditingStaffId(null);
    setStaffForm({
      ...STAFF_EMPTY,
      temporary_password: generateTemporaryPassword(),
    });
    setStaffOriginal(STAFF_EMPTY);
    setStaffModalOpen(true);
  }

  function openEditStaff(row) {
    const value = {
      name: row.name || "",
      email: row.email || "",
      phone_country_code: row.phone_country_code || "+91",
      phone_number: row.phone_number || "",
      department_id: String(row.department_id ?? ""),
      job_description: row.job_description || "",
      salary: String(row.salary ?? ""),
      temporary_password: "",
      manager_id: String(row.manager_id ?? ""),
    };

    setStaffMode("edit");
    setEditingStaffId(row.staff_id);
    setStaffForm(value);
    setStaffOriginal(value);
    setStaffModalOpen(true);
  }

  function openAddManager() {
    setManagerMode("add");
    setEditingManagerId(null);
    setManagerForm({
      ...MANAGER_EMPTY,
      temporary_password: generateTemporaryPassword(),
    });
    setManagerOriginal(MANAGER_EMPTY);
    setManagerModalOpen(true);
  }

  function openEditManager(row) {
    const value = {
      name: row.name || "",
      email: row.email || "",
      phone_country_code: row.phone_country_code || "+91",
      phone_number: row.phone_number || "",
      department_id: String(row.department_id ?? ""),
      reports_to_manager_id: row.reports_to_manager_id
        ? String(row.reports_to_manager_id)
        : "",
      job_description: row.job_description || "",
      salary: String(row.salary ?? ""),
      temporary_password: "",
    };

    setManagerMode("edit");
    setEditingManagerId(row.manager_id);
    setManagerForm(value);
    setManagerOriginal(value);
    setManagerModalOpen(true);
  }

  function openAddDepartment() {
    setDepartmentMode("add");
    setEditingDepartmentId(null);
    setDepartmentForm(DEPARTMENT_EMPTY);
    setDepartmentModalOpen(true);
  }

  function openEditDepartment(row) {
    setDepartmentMode("edit");
    setEditingDepartmentId(row.department_id);
    setDepartmentForm({
      department_name: row.department_name || "",
      head_manager_id: row.head_manager_id ? String(row.head_manager_id) : "",
    });
    setDepartmentModalOpen(true);
  }

  const { run: saveStaff, busy: staffBusy } = useAction(async () => {
    if (!staffForm.name.trim()) {
      notify("Name is required", "error");
      return null;
    }

    if (!staffForm.email.trim()) {
      notify("Email is required", "error");
      return null;
    }

    if (!staffForm.department_id) {
      notify("Department is required", "error");
      return null;
    }

    if (!staffForm.salary || Number(staffForm.salary) < 0) {
      notify("Salary must be zero or greater", "error");
      return null;
    }

    if (staffMode === "add") {
      if (!staffForm.temporary_password) {
        notify("Temporary password is required", "error");
        return null;
      }

      const payload = {
        name: staffForm.name.trim(),
        email: staffForm.email.trim(),
        phone_country_code: staffForm.phone_country_code || "+91",
        phone_number: staffForm.phone_number || null,
        department_id: Number(staffForm.department_id),
        job_description: staffForm.job_description || null,
        salary: Number(staffForm.salary),
        temporary_password: staffForm.temporary_password,
      };

      if (isAdmin) {
        if (!staffForm.manager_id) {
          notify("Choose the manager this staff member reports to", "error");
          return null;
        }
        payload.manager_id = Number(staffForm.manager_id);
      }

      const result = await api.post("/staff", payload);
      setStaffModalOpen(false);
      setCredentialInfo({
        type: "staff",
        name: result?.name || payload.name,
        email: result?.email || payload.email,
        password: staffForm.temporary_password,
      });
      setCredentialModalOpen(true);
      setStaffForm(STAFF_EMPTY);
      await refreshPeople();
      notify("Staff member added successfully", "success");
      return result;
    }

    const keys = [
      "name",
      "phone_country_code",
      "phone_number",
      "department_id",
      "job_description",
      "salary",
    ];
    if (isAdmin) keys.push("manager_id");

    const payload = changedFields(staffOriginal, staffForm, keys);
    if (!Object.keys(payload).length) {
      notify("No fields to update", "error");
      return null;
    }

    const result = await api.put(`/staff/${editingStaffId}`, payload);
    notify("Staff member updated successfully", "success");
    setStaffModalOpen(false);
    setEditingStaffId(null);
    await refreshPeople();
    return result;
  });

  const { run: toggleStaffActive, busy: staffActiveBusy } = useAction(
    async (row) => {
      const result = await api.patch(`/staff/${row.staff_id}/active`, {
        active: !row.is_active,
      });
      notify(
        row.is_active ? "Staff member deactivated" : "Staff member reactivated",
        "success",
      );
      setConfirmAction(null);
      await reloadStaff();
      return result;
    },
  );

  const { run: resetStaffPassword, busy: resetStaffBusy } = useAction(
    async () => {
      if (!resetPassword) {
        notify("Temporary password is required", "error");
        return null;
      }

      const result = await api.post(`/staff/${resetTarget.id}/reset-password`, {
        temporary_password: resetPassword,
      });

      notify("Temporary password reset successfully", "success");
      setResetModalOpen(false);
      setResetPassword("");
      setResetTarget(null);
      return result;
    },
  );

  const { run: saveManager, busy: managerBusy } = useAction(async () => {
    if (!managerForm.name.trim()) {
      notify("Name is required", "error");
      return null;
    }

    if (!managerForm.email.trim()) {
      notify("Email is required", "error");
      return null;
    }

    if (!managerForm.department_id) {
      notify("Department is required", "error");
      return null;
    }

    if (!managerForm.salary || Number(managerForm.salary) < 0) {
      notify("Salary must be zero or greater", "error");
      return null;
    }

    if (managerMode === "add") {
      if (!managerForm.temporary_password) {
        notify("Temporary password is required", "error");
        return null;
      }

      const result = await api.post("/managers", {
        name: managerForm.name.trim(),
        email: managerForm.email.trim(),
        phone_country_code: managerForm.phone_country_code || "+91",
        phone_number: managerForm.phone_number || null,
        department_id: Number(managerForm.department_id),
        reports_to_manager_id: managerForm.reports_to_manager_id
          ? Number(managerForm.reports_to_manager_id)
          : null,
        job_description: managerForm.job_description || null,
        salary: Number(managerForm.salary),
        temporary_password: managerForm.temporary_password,
      });

      setManagerModalOpen(false);
      setCredentialInfo({
        type: "manager",
        name: result?.name || managerForm.name,
        email: result?.email || managerForm.email,
        password: managerForm.temporary_password,
      });
      setCredentialModalOpen(true);
      setManagerForm(MANAGER_EMPTY);
      await refreshPeople();
      notify("Manager added successfully", "success");
      return result;
    }

    const payload = changedFields(managerOriginal, managerForm, [
      "name",
      "phone_country_code",
      "phone_number",
      "department_id",
      "reports_to_manager_id",
      "job_description",
      "salary",
    ]);

    if (!Object.keys(payload).length) {
      notify("No fields to update", "error");
      return null;
    }

    const result = await api.put(`/managers/${editingManagerId}`, payload);
    notify("Manager updated successfully", "success");
    setManagerModalOpen(false);
    setEditingManagerId(null);
    await refreshPeople();
    return result;
  });

  const { run: toggleManagerActive, busy: managerActiveBusy } = useAction(
    async (row) => {
      const result = await api.patch(`/managers/${row.manager_id}/active`, {
        active: !row.is_active,
      });
      notify(
        row.is_active ? "Manager deactivated" : "Manager reactivated",
        "success",
      );
      setConfirmAction(null);
      await refreshPeople();
      return result;
    },
  );

  const { run: resetManagerPassword, busy: resetManagerBusy } = useAction(
    async () => {
      if (!resetPassword) {
        notify("Temporary password is required", "error");
        return null;
      }

      const result = await api.post(
        `/managers/${resetTarget.id}/reset-password`,
        { temporary_password: resetPassword },
      );

      notify("Temporary password reset successfully", "success");
      setResetModalOpen(false);
      setResetPassword("");
      setResetTarget(null);
      return result;
    },
  );

  const { run: saveDepartment, busy: departmentBusy } = useAction(async () => {
    if (!departmentForm.department_name.trim()) {
      notify("Department name is required", "error");
      return null;
    }

    const payload = {
      department_name: departmentForm.department_name.trim(),
      head_manager_id: departmentForm.head_manager_id
        ? Number(departmentForm.head_manager_id)
        : null,
    };

    const result =
      departmentMode === "add"
        ? await api.post("/departments", payload)
        : await api.put(`/departments/${editingDepartmentId}`, payload);

    notify(
      departmentMode === "add"
        ? "Department added successfully"
        : "Department updated successfully",
      "success",
    );

    setDepartmentModalOpen(false);
    setEditingDepartmentId(null);
    setDepartmentForm(DEPARTMENT_EMPTY);
    await refreshPeople();
    return result;
  });

  const { run: deleteDepartment, busy: deleteDepartmentBusy } = useAction(
    async (departmentId) => {
      const result = await api.delete(`/departments/${departmentId}`);
      notify("Department deleted successfully", "success");
      setConfirmAction(null);
      await refreshPeople();
      return result;
    },
  );

  if (staffLoading || staffError) {
    return (
      <PageState
        loading={staffLoading}
        error={staffError}
        onRetry={reloadStaff}
      />
    );
  }

  const staffRows = staff || [];
  const managerRows = managers || [];
  const departmentRows = departments || [];

  const tabs = [
    { id: "staff", label: "Staff" },
    ...(isAdmin ? [{ id: "managers", label: "Managers" }] : []),
    { id: "departments", label: "Departments" },
  ];

  const isStaffEdit = staffMode === "edit";
  const isManagerEdit = managerMode === "edit";

  const credentialTitle =
    credentialInfo?.type === "manager" ? "Manager created" : "Staff created";

  return (
    <section className="workspace">
      <PageHeader
        eyebrow="Personnel"
        title={
          activeTab === "staff"
            ? "Staff Members"
            : activeTab === "managers"
            ? "Department Managers"
            : "Departments"
        }
        subtitle={
          activeTab === "staff"
            ? "Manage employee profiles, department allocations, and roles."
            : activeTab === "managers"
            ? "Manage management personnel and reporting hierarchies."
            : "Organize hotel operational departments and team leads."
        }
        primaryAction={
          activeTab === "staff" ? (
            <button type="button" className="primary" onClick={openAddStaff}>
              Add staff
            </button>
          ) : activeTab === "managers" && isAdmin ? (
            <button type="button" className="primary" onClick={openAddManager}>
              Add manager
            </button>
          ) : activeTab === "departments" && isAdmin ? (
            <button
              type="button"
              className="primary"
              onClick={openAddDepartment}
            >
              Add department
            </button>
          ) : null
        }
        tabs={tabs}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      {activeTab === "staff" && (
        <div className="panel wide">
          <Toolbar>
            <form className="toolbarFilters" onSubmit={updateStaffFilter}>
              <label>
                Search
                <input
                  value={staffSearch}
                  onChange={(event) => setStaffSearch(event.target.value)}
                  placeholder="Name, email or job description"
                />
              </label>

              <label>
                Department
                <select
                  value={staffDepartmentId}
                  onChange={(event) => setStaffDepartmentId(event.target.value)}
                >
                  <option value="">All departments</option>
                  {departmentRows.map((department) => (
                    <option
                      key={department.department_id}
                      value={department.department_id}
                    >
                      {department.department_name}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Status
                <select
                  value={staffActive}
                  onChange={(event) => setStaffActive(event.target.value)}
                >
                  <option value="">All</option>
                  <option value="true">Active</option>
                  <option value="false">Inactive</option>
                </select>
              </label>

              <button type="submit" className="secondary">
                Filter
              </button>
              <button
                type="button"
                className="secondary"
                onClick={clearStaffFilter}
              >
                Clear
              </button>
            </form>
          </Toolbar>

          {departmentsError && <p className="error">{departmentsError}</p>}

          <DataTable
            rows={staffRows}
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
              { key: "department_name", label: "Department" },
              ...(isAdmin ? [{ key: "manager_name", label: "Manager" }] : []),
              { key: "job_description", label: "Title" },
              {
                key: "salary",
                label: "Salary",
                render: (row) => currency(row.salary),
              },
              {
                key: "is_active",
                label: "Status",
                render: (row) => (
                  <Badge>{row.is_active ? "ACTIVE" : "INACTIVE"}</Badge>
                ),
              },
            ]}
            actions={(row) => (
              <div className="rowActions">
                <button type="button" onClick={() => openEditStaff(row)}>
                  Edit
                </button>

                <button
                  type="button"
                  onClick={() =>
                    setConfirmAction({
                      kind: "staff-active",
                      row,
                    })
                  }
                >
                  {row.is_active ? "Deactivate" : "Reactivate"}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setResetTarget({
                      kind: "staff",
                      id: row.staff_id,
                      name: row.name,
                    });
                    setResetPassword(generateTemporaryPassword());
                    setResetModalOpen(true);
                  }}
                >
                  Reset password
                </button>
              </div>
            )}
            empty="No staff found."
          />
        </div>
      )}

      {activeTab === "managers" && isAdmin && (
        <div className="panel wide">
          <Toolbar actions={<span>{managerRows.length} managers</span>} />

          {managersError ? <p className="error">{managersError}</p> : null}

          <DataTable
            rows={managerRows}
            loading={managersLoading}
            columns={[
              { key: "name", label: "Name" },
              { key: "email", label: "Email" },
              { key: "department_name", label: "Department" },
              {
                key: "reports_to_name",
                label: "Reports to",
                render: (row) => row.reports_to_name || "—",
              },
              { key: "active_staff", label: "Active staff" },
              {
                key: "salary",
                label: "Salary",
                render: (row) => currency(row.salary),
              },
              {
                key: "is_active",
                label: "Status",
                render: (row) => (
                  <Badge>{row.is_active ? "ACTIVE" : "INACTIVE"}</Badge>
                ),
              },
            ]}
            actions={(row) => (
              <div className="rowActions">
                <button type="button" onClick={() => openEditManager(row)}>
                  Edit
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setConfirmAction({
                      kind: "manager-active",
                      row,
                    })
                  }
                >
                  {row.is_active ? "Deactivate" : "Reactivate"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setResetTarget({
                      kind: "manager",
                      id: row.manager_id,
                      name: row.name,
                    });
                    setResetPassword(generateTemporaryPassword());
                    setResetModalOpen(true);
                  }}
                >
                  Reset password
                </button>
              </div>
            )}
            empty="No managers found."
          />
        </div>
      )}

      {activeTab === "departments" && (
        <div className="panel wide">
          <Toolbar actions={<span>{departmentRows.length} departments</span>} />

          <DataTable
            rows={departmentRows}
            loading={departmentsLoading}
            columns={[
              { key: "department_name", label: "Name" },
              {
                key: "head_manager_name",
                label: "Head",
                render: (row) => row.head_manager_name || "—",
              },
            ]}
            actions={
              isAdmin
                ? (row) => (
                    <div className="rowActions">
                      <button
                        type="button"
                        onClick={() => openEditDepartment(row)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          setConfirmAction({
                            kind: "department-delete",
                            row,
                          })
                        }
                      >
                        Delete
                      </button>
                    </div>
                  )
                : undefined
            }
            empty="No departments found."
          />
        </div>
      )}

      <Modal
        open={staffModalOpen}
        title={isStaffEdit ? "Edit staff" : "Add staff"}
        onClose={() => {
          if (!staffBusy) {
            setStaffModalOpen(false);
            setEditingStaffId(null);
            setStaffForm(STAFF_EMPTY);
          }
        }}
      >
        <form
          className="form"
          onSubmit={(event) => {
            event.preventDefault();
            saveStaff();
          }}
        >
          <label>
            Name
            <input
              value={staffForm.name}
              onChange={(event) =>
                setStaffForm((current) => ({
                  ...current,
                  name: event.target.value,
                }))
              }
              required
            />
          </label>

          {!isStaffEdit && (
            <label>
              Email
              <input
                type="email"
                value={staffForm.email}
                onChange={(event) =>
                  setStaffForm((current) => ({
                    ...current,
                    email: event.target.value,
                  }))
                }
                required
              />
            </label>
          )}

          <label>
            Phone country code
            <input
              value={staffForm.phone_country_code}
              onChange={(event) =>
                setStaffForm((current) => ({
                  ...current,
                  phone_country_code: event.target.value,
                }))
              }
            />
          </label>

          <label>
            Phone number
            <input
              value={staffForm.phone_number}
              onChange={(event) =>
                setStaffForm((current) => ({
                  ...current,
                  phone_number: event.target.value,
                }))
              }
            />
          </label>

          <label>
            Department
            <select
              value={staffForm.department_id}
              onChange={(event) =>
                setStaffForm((current) => ({
                  ...current,
                  department_id: event.target.value,
                }))
              }
              required
            >
              <option value="">
                {departmentsLoading
                  ? "Loading departments..."
                  : "Select department"}
              </option>
              {departmentRows.map((department) => (
                <option
                  key={department.department_id}
                  value={department.department_id}
                >
                  {department.department_name}
                </option>
              ))}
            </select>
          </label>

          {isAdmin && (
            <label>
              Manager
              <select
                value={staffForm.manager_id}
                onChange={(event) =>
                  setStaffForm((current) => ({
                    ...current,
                    manager_id: event.target.value,
                  }))
                }
                required
              >
                <option value="">
                  {managersLoading ? "Loading managers..." : "Select manager"}
                </option>
                {managerRows
                  .filter((row) => row.is_active)
                  .map((manager) => (
                    <option key={manager.manager_id} value={manager.manager_id}>
                      {manager.name}
                    </option>
                  ))}
              </select>
            </label>
          )}

          <label>
            Job description
            <input
              value={staffForm.job_description}
              onChange={(event) =>
                setStaffForm((current) => ({
                  ...current,
                  job_description: event.target.value,
                }))
              }
            />
          </label>

          <label>
            Salary
            <input
              type="number"
              min="0"
              step="0.01"
              value={staffForm.salary}
              onChange={(event) =>
                setStaffForm((current) => ({
                  ...current,
                  salary: event.target.value,
                }))
              }
              required
            />
          </label>

          {!isStaffEdit && (
            <label>
              Temporary password
              <div className="inlineControl">
                <input
                  type="text"
                  minLength="8"
                  maxLength="72"
                  value={staffForm.temporary_password}
                  onChange={(event) =>
                    setStaffForm((current) => ({
                      ...current,
                      temporary_password: event.target.value,
                    }))
                  }
                  required
                />
                <button
                  type="button"
                  onClick={() =>
                    setStaffForm((current) => ({
                      ...current,
                      temporary_password: generateTemporaryPassword(),
                    }))
                  }
                >
                  Generate
                </button>
              </div>
            </label>
          )}

          <button type="submit" className="primary" disabled={staffBusy}>
            {staffBusy
              ? isStaffEdit
                ? "Saving..."
                : "Creating..."
              : isStaffEdit
                ? "Save changes"
                : "Add staff"}
          </button>
        </form>
      </Modal>

      <Modal
        open={managerModalOpen}
        title={isManagerEdit ? "Edit manager" : "Add manager"}
        onClose={() => {
          if (!managerBusy) {
            setManagerModalOpen(false);
            setEditingManagerId(null);
            setManagerForm(MANAGER_EMPTY);
          }
        }}
      >
        <form
          className="form"
          onSubmit={(event) => {
            event.preventDefault();
            saveManager();
          }}
        >
          <label>
            Name
            <input
              value={managerForm.name}
              onChange={(event) =>
                setManagerForm((current) => ({
                  ...current,
                  name: event.target.value,
                }))
              }
              required
            />
          </label>

          {!isManagerEdit && (
            <label>
              Email
              <input
                type="email"
                value={managerForm.email}
                onChange={(event) =>
                  setManagerForm((current) => ({
                    ...current,
                    email: event.target.value,
                  }))
                }
                required
              />
            </label>
          )}

          <label>
            Phone country code
            <input
              value={managerForm.phone_country_code}
              onChange={(event) =>
                setManagerForm((current) => ({
                  ...current,
                  phone_country_code: event.target.value,
                }))
              }
            />
          </label>

          <label>
            Phone number
            <input
              value={managerForm.phone_number}
              onChange={(event) =>
                setManagerForm((current) => ({
                  ...current,
                  phone_number: event.target.value,
                }))
              }
            />
          </label>

          <label>
            Department
            <select
              value={managerForm.department_id}
              onChange={(event) =>
                setManagerForm((current) => ({
                  ...current,
                  department_id: event.target.value,
                }))
              }
              required
            >
              <option value="">Select department</option>
              {departmentRows.map((department) => (
                <option
                  key={department.department_id}
                  value={department.department_id}
                >
                  {department.department_name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Reports to
            <select
              value={managerForm.reports_to_manager_id}
              onChange={(event) =>
                setManagerForm((current) => ({
                  ...current,
                  reports_to_manager_id: event.target.value,
                }))
              }
            >
              <option value="">No manager</option>
              {managerRows
                .filter(
                  (row) => row.is_active && row.manager_id !== editingManagerId,
                )
                .map((manager) => (
                  <option key={manager.manager_id} value={manager.manager_id}>
                    {manager.name}
                  </option>
                ))}
            </select>
          </label>

          <label>
            Job description
            <input
              value={managerForm.job_description}
              onChange={(event) =>
                setManagerForm((current) => ({
                  ...current,
                  job_description: event.target.value,
                }))
              }
            />
          </label>

          <label>
            Salary
            <input
              type="number"
              min="0"
              step="0.01"
              value={managerForm.salary}
              onChange={(event) =>
                setManagerForm((current) => ({
                  ...current,
                  salary: event.target.value,
                }))
              }
              required
            />
          </label>

          {!isManagerEdit && (
            <label>
              Temporary password
              <div className="inlineControl">
                <input
                  type="text"
                  minLength="8"
                  maxLength="72"
                  value={managerForm.temporary_password}
                  onChange={(event) =>
                    setManagerForm((current) => ({
                      ...current,
                      temporary_password: event.target.value,
                    }))
                  }
                  required
                />
                <button
                  type="button"
                  onClick={() =>
                    setManagerForm((current) => ({
                      ...current,
                      temporary_password: generateTemporaryPassword(),
                    }))
                  }
                >
                  Generate
                </button>
              </div>
            </label>
          )}

          <button type="submit" className="primary" disabled={managerBusy}>
            {managerBusy
              ? isManagerEdit
                ? "Saving..."
                : "Creating..."
              : isManagerEdit
                ? "Save changes"
                : "Add manager"}
          </button>
        </form>
      </Modal>

      <Modal
        open={departmentModalOpen}
        title={departmentMode === "add" ? "Add department" : "Edit department"}
        onClose={() => {
          if (!departmentBusy) {
            setDepartmentModalOpen(false);
            setEditingDepartmentId(null);
            setDepartmentForm(DEPARTMENT_EMPTY);
          }
        }}
      >
        <form
          className="form"
          onSubmit={(event) => {
            event.preventDefault();
            saveDepartment();
          }}
        >
          <label>
            Department name
            <input
              value={departmentForm.department_name}
              onChange={(event) =>
                setDepartmentForm((current) => ({
                  ...current,
                  department_name: event.target.value,
                }))
              }
              required
            />
          </label>

          <label>
            Head manager
            <select
              value={departmentForm.head_manager_id}
              onChange={(event) =>
                setDepartmentForm((current) => ({
                  ...current,
                  head_manager_id: event.target.value,
                }))
              }
            >
              <option value="">No head</option>
              {managerRows
                .filter((row) => row.is_active)
                .map((manager) => (
                  <option key={manager.manager_id} value={manager.manager_id}>
                    {manager.name}
                  </option>
                ))}
            </select>
          </label>

          <button type="submit" className="primary" disabled={departmentBusy}>
            {departmentBusy
              ? "Saving..."
              : departmentMode === "add"
                ? "Add department"
                : "Save changes"}
          </button>
        </form>
      </Modal>

      <Modal
        open={resetModalOpen}
        title={`Reset password: ${resetTarget?.name || ""}`}
        onClose={() => {
          if (!resetStaffBusy && !resetManagerBusy) {
            setResetModalOpen(false);
            setResetTarget(null);
            setResetPassword("");
          }
        }}
      >
        <form
          className="form"
          onSubmit={(event) => {
            event.preventDefault();
            if (resetTarget?.kind === "staff") {
              resetStaffPassword();
            } else {
              resetManagerPassword();
            }
          }}
        >
          <label>
            Temporary password
            <div className="inlineControl">
              <input
                type="text"
                minLength="8"
                maxLength="72"
                value={resetPassword}
                onChange={(event) => setResetPassword(event.target.value)}
                required
              />
              <button
                type="button"
                onClick={() => setResetPassword(generateTemporaryPassword())}
              >
                Generate
              </button>
            </div>
          </label>

          <button
            type="submit"
            className="primary"
            disabled={resetStaffBusy || resetManagerBusy}
          >
            {resetStaffBusy || resetManagerBusy
              ? "Resetting..."
              : "Reset password"}
          </button>
        </form>
      </Modal>

      <Modal
        open={credentialModalOpen}
        title={credentialTitle}
        onClose={() => {
          setCredentialModalOpen(false);
          setCredentialInfo(null);
        }}
      >
        {credentialInfo && (
          <div className="stack">
            <p>
              Temporary credentials for <strong>{credentialInfo.name}</strong>.
              This password is shown once so it can be handed to the new user.
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

      <ConfirmDialog
        open={Boolean(confirmAction)}
        title={
          confirmAction?.kind === "department-delete"
            ? "Delete department"
            : confirmAction?.kind === "manager-active"
              ? `${confirmAction?.row?.is_active ? "Deactivate" : "Reactivate"} manager`
              : `${confirmAction?.row?.is_active ? "Deactivate" : "Reactivate"} staff`
        }
        message={
          confirmAction?.kind === "department-delete"
            ? "Delete this department?"
            : `Are you sure you want to ${
                confirmAction?.row?.is_active ? "deactivate" : "reactivate"
              } this account?`
        }
        confirmLabel={
          confirmAction?.kind === "department-delete"
            ? "Delete"
            : confirmAction?.row?.is_active
              ? "Deactivate"
              : "Reactivate"
        }
        busy={staffActiveBusy || managerActiveBusy || deleteDepartmentBusy}
        onCancel={() => {
          if (!staffActiveBusy && !managerActiveBusy && !deleteDepartmentBusy) {
            setConfirmAction(null);
          }
        }}
        onConfirm={() => {
          if (confirmAction?.kind === "staff-active") {
            toggleStaffActive(confirmAction.row);
          } else if (confirmAction?.kind === "manager-active") {
            toggleManagerActive(confirmAction.row);
          } else if (confirmAction?.kind === "department-delete") {
            deleteDepartment(confirmAction.row.department_id);
          }
        }}
      />
    </section>
  );
}
