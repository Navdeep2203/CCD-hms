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

import { addDays, currency, fmtDate, nullify, today } from "../utils/format";

const EMPTY_ROOM_FORM = {
  room_number: "",

  room_type_id: "",

  floor: "1",

  status: "AVAILABLE",
};

export default function Rooms() {
  const { user, isOps, isManagement } = useAuth();

  const { notify } = useToast();

  const isCustomer = user?.roles?.includes("ROLE_CUSTOMER");

  const [checkIn, setCheckIn] = useState(today());

  const [checkOut, setCheckOut] = useState(addDays(today(), 1));

  const guestPath = isCustomer
    ? `/rooms?check_in=${checkIn}&check_out=${checkOut}`
    : "/rooms";

  const {
    data: rooms,

    loading,

    error,

    reload,
  } = useFetch(guestPath);

  const {
    data: roomTypes,

    loading: roomTypesLoading,

    error: roomTypesError,

    reload: reloadRoomTypes,
  } = useFetch(isManagement ? "/rooms/types" : "");

  const [roomModalOpen, setRoomModalOpen] = useState(false);

  const EMPTY_ROOM_TYPE_FORM = {
    type_name: "",

    capacity: "1",

    price_per_night: "",

    description: "",
  };

  const [activeTab, setActiveTab] = useState("rooms");

  const [roomTypeModalOpen, setRoomTypeModalOpen] = useState(false);

  const [roomTypeMode, setRoomTypeMode] = useState("add");

  const [editingRoomTypeId, setEditingRoomTypeId] = useState(null);

  const [roomTypeForm, setRoomTypeForm] = useState(EMPTY_ROOM_TYPE_FORM);

  const [deleteRoomTypeId, setDeleteRoomTypeId] = useState(null);

  const [roomMode, setRoomMode] = useState("add");

  const [editingRoomId, setEditingRoomId] = useState(null);

  const [roomForm, setRoomForm] = useState(EMPTY_ROOM_FORM);

  const [deleteRoomId, setDeleteRoomId] = useState(null);

  const {
    run: updateRoomStatus,

    busy: statusBusy,
  } = useAction(async (roomId, status) => {
    await api.patch(`/rooms/${roomId}/status`, {
      status,
    });

    notify("Room status updated", "success");

    reload();
  });

  const {
    run: saveRoom,

    busy: saveBusy,
  } = useAction(async () => {
    const payload = nullify({
      room_number: Number(roomForm.room_number),

      room_type_id: Number(roomForm.room_type_id),

      floor: Number(roomForm.floor),

      status: roomForm.status,
    });

    if (roomMode === "add") {
      await api.post("/rooms", payload);

      notify("Room added successfully", "success");
    } else {
      await api.put(
        `/rooms/${editingRoomId}`,

        payload,
      );

      notify("Room updated successfully", "success");
    }

    setRoomModalOpen(false);

    setEditingRoomId(null);

    setRoomForm(EMPTY_ROOM_FORM);

    reload();
  });

  const {
    run: saveRoomType,

    busy: roomTypeSaveBusy,
  } = useAction(async () => {
    const payload = nullify({
      type_name: roomTypeForm.type_name.trim(),

      capacity: Number(roomTypeForm.capacity),

      price_per_night: Number(roomTypeForm.price_per_night),

      description: roomTypeForm.description.trim(),
    });

    if (roomTypeMode === "add") {
      await api.post("/rooms/types", payload);

      notify("Room type added successfully", "success");
    } else {
      await api.put(
        `/rooms/types/${editingRoomTypeId}`,

        payload,
      );

      notify("Room type updated successfully", "success");
    }

    setRoomTypeModalOpen(false);

    setEditingRoomTypeId(null);

    setRoomTypeForm(EMPTY_ROOM_TYPE_FORM);

    reloadRoomTypes();
  });

  const { run: deleteRoomType } = useAction(async (roomTypeId) => {
    await api.delete(`/rooms/types/${roomTypeId}`);

    notify(
      "Room type deleted successfully",

      "success",
    );

    setDeleteRoomTypeId(null);

    reloadRoomTypes();
  });

  const { run: deleteRoom } = useAction(async (roomId) => {
    await api.delete(`/rooms/${roomId}`);

    notify("Room deleted successfully", "success");

    setDeleteRoomId(null);

    reload();
  });

  const nights = useMemo(() => {
    const start = new Date(`${checkIn}T00:00:00`);

    const end = new Date(`${checkOut}T00:00:00`);

    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
      return 0;
    }

    return Math.max(
      0,

      Math.round((end - start) / 86400000),
    );
  }, [checkIn, checkOut]);

  function handleCheckInChange(value) {
    setCheckIn(value);

    if (checkOut <= value) {
      setCheckOut(addDays(value, 1));
    }
  }

  function openAddRoom() {
    setRoomMode("add");

    setEditingRoomId(null);

    setRoomForm(EMPTY_ROOM_FORM);

    setRoomModalOpen(true);
  }

  function openEditRoom(room) {
    setRoomMode("edit");

    setEditingRoomId(room.room_id);

    setRoomForm({
      room_number: String(room.room_number ?? ""),

      room_type_id: String(room.room_type_id ?? ""),

      floor: String(room.floor ?? 1),

      status: room.status || "AVAILABLE",
    });

    setRoomModalOpen(true);
  }

  function openAddRoomType() {
    setRoomTypeMode("add");

    setEditingRoomTypeId(null);

    setRoomTypeForm(EMPTY_ROOM_TYPE_FORM);

    setRoomTypeModalOpen(true);
  }

  function openEditRoomType(roomType) {
    setRoomTypeMode("edit");

    setEditingRoomTypeId(roomType.room_type_id);

    setRoomTypeForm({
      type_name: roomType.type_name || "",

      capacity: String(roomType.capacity ?? 1),

      price_per_night: String(roomType.price_per_night ?? ""),

      description: roomType.description || "",
    });

    setRoomTypeModalOpen(true);
  }

  async function handleSaveRoomType(event) {
    event.preventDefault();

    const name = roomTypeForm.type_name.trim();

    const capacity = Number(roomTypeForm.capacity);

    const price = Number(roomTypeForm.price_per_night);

    if (!name) {
      notify("Room type name is required", "error");

      return;
    }

    if (name.length > 50) {
      notify(
        "Room type name must be at most 50 characters",

        "error",
      );

      return;
    }

    if (!Number.isInteger(capacity) || capacity < 1 || capacity > 20) {
      notify(
        "Capacity must be between 1 and 20",

        "error",
      );

      return;
    }

    if (!Number.isFinite(price) || price <= 0) {
      notify(
        "Price per night must be greater than 0",

        "error",
      );

      return;
    }

    await saveRoomType();
  }

  async function handleSaveRoom(event) {
    event.preventDefault();

    if (!roomForm.room_number) {
      notify("Room number is required", "error");

      return;
    }

    if (!roomForm.room_type_id) {
      notify("Room type is required", "error");

      return;
    }

    await saveRoom();
  }

  async function handleStatusChange(roomId, nextStatus) {
    if (!nextStatus) return;

    try {
      await updateRoomStatus(roomId, nextStatus);
    } catch {
      // useAction already displays the backend error
    }
  }

  if (loading || error) {
    return (
      <PageState
        loading={loading}

        error={error}

        onRetry={reload}
      />
    );
  }

  const roomRows = rooms || [];

  const typeRows = roomTypes || [];

  /*

   * --------------------------------

   * GUEST ROOMS

   * --------------------------------

   */

  if (isCustomer) {
    return (
      <section className="workspace">
        <div className="panel wide">
          <div className="panelHead">
            <div>
              <p className="eyebrow">Room search</p>

              <h2>Find a room</h2>
            </div>

            <span>{roomRows.length} rooms available</span>
          </div>

          <div className="dateSearch">
            <label>
              Check-in
              <input
                type="date"

                value={checkIn}

                min={today()}

                onChange={(e) => handleCheckInChange(e.target.value)}
              />
            </label>

            <label>
              Check-out
              <input
                type="date"

                value={checkOut}

                min={addDays(checkIn, 1)}

                onChange={(e) => setCheckOut(e.target.value)}
              />
            </label>
          </div>
        </div>

        {roomRows.length === 0 ? (
          <PageState empty={"No rooms are available for those dates."} />
        ) : (
          <div className="roomGrid">
            {roomRows.map((room) => {
              const nightly = Number(room.price_per_night) || 0;

              const total = nightly * nights;

              return (
                <article
                  className="roomCard"

                  key={room.room_id}
                >
                  <div className="roomCardTop">
                    <div>
                      <p className="eyebrow">{room.type_name}</p>

                      <h3>Room {room.room_number}</h3>
                    </div>

                    <span className="roomFloor">Floor {room.floor}</span>
                  </div>

                  <div className="roomFacts">
                    <div>
                      <span>Capacity</span>

                      <strong>{room.capacity} guests</strong>
                    </div>

                    <div>
                      <span>Price / night</span>

                      <strong>{currency(nightly)}</strong>
                    </div>
                  </div>

                  <div className="roomDates">
                    <div>
                      <span>Stay</span>

                      <strong>
                        {fmtDate(checkIn)} → {fmtDate(checkOut)}
                      </strong>
                    </div>

                    <div>
                      <span>Total</span>

                      <strong>
                        {nights} night
                        {nights === 1 ? "" : "s"} × {currency(nightly)}
                      </strong>
                    </div>
                  </div>

                  <div className="roomCardBottom">
                    <strong>{currency(total)}</strong>

                    <button
                      type="button"

                      className="primary"

                      disabled={nights <= 0}

                      onClick={async () => {
                        try {
                          await api.post("/bookings", {
                            room_id: Number(room.room_id),

                            check_in_date: checkIn,

                            check_out_date: checkOut,
                          });

                          notify(
                            "Room booked successfully",

                            "success",
                          );

                          reload();
                        } catch (err) {
                          notify(
                            err?.message || "Unable to book room",

                            "error",
                          );
                        }
                      }}
                    >
                      Book
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    );
  }

  /*

   * --------------------------------

   * OPS ROOMS

   * --------------------------------

   */

  return (
    <section className="workspace">
      <Tabs
        tabs={
          isManagement
            ? [
                { id: "rooms", label: "Rooms" },
                { id: "roomTypes", label: "Room Types" },
              ]
            : [{ id: "rooms", label: "Rooms" }]
        }
        activeTab={activeTab}
        onChange={setActiveTab}
      />

      {activeTab === "rooms" && (
        <div className="panel wide">
          <div className="panelHead">
            <div>
              <p className="eyebrow">Inventory</p>

              <h2>Room inventory</h2>
            </div>

            <div className="panelActions">
              <span>{roomRows.length} rooms</span>

              {isManagement && (
                <button
                  type="button"

                  className="primary"

                  onClick={openAddRoom}
                >
                  Add room
                </button>
              )}
            </div>
          </div>

          <DataTable
            rows={roomRows}

            columns={[
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
                key: "floor",

                label: "Floor",
              },

              {
                key: "capacity",

                label: "Capacity",
              },

              {
                key: "price_per_night",

                label: "Price / night",

                render: (row) => currency(row.price_per_night),
              },

              {
                key: "status",

                label: "Status",

                render: (row) => (
                  <div className="roomStatusCell">
                    <Badge>{row.status}</Badge>

                    {isOps && (
                      <select
                        value={row.status}

                        disabled={statusBusy || row.status === "OCCUPIED"}

                        onChange={(event) =>
                          handleStatusChange(
                            row.room_id,

                            event.target.value,
                          )
                        }
                      >
                        <option value={row.status}>{row.status}</option>

                        {row.status !== "AVAILABLE" && (
                          <option value="AVAILABLE">AVAILABLE</option>
                        )}

                        {row.status !== "MAINTENANCE" && (
                          <option value="MAINTENANCE">MAINTENANCE</option>
                        )}
                      </select>
                    )}
                  </div>
                ),
              },
            ]}

            actions={
              isManagement
                ? (row) => (
                    <div className="rowActions">
                      <button
                        type="button"

                        className="secondary"

                        onClick={() => openEditRoom(row)}
                      >
                        Edit
                      </button>

                      <button
                        type="button"

                        className="dangerButton"

                        onClick={() => setDeleteRoomId(row.room_id)}
                      >
                        Delete
                      </button>
                    </div>
                  )
                : undefined
            }

            empty="No rooms found."
          />
        </div>
      )}

      {activeTab === "roomTypes" && isManagement && (
        <div className="panel wide">
          <div className="panelHead">
            <div>
              <p className="eyebrow">Room configuration</p>
              <h2>Room types</h2>
            </div>

            <div className="panelActions">
              <span>{typeRows.length} types</span>
              <button
                type="button"
                className="primary"
                onClick={openAddRoomType}
              >
                Add room type
              </button>
            </div>
          </div>

          {roomTypesLoading ? (
            <PageState loading />
          ) : roomTypesError ? (
            <PageState error={roomTypesError} onRetry={reloadRoomTypes} />
          ) : (
            <DataTable
              rows={typeRows}
              columns={[
                {
                  key: "type_name",
                  label: "Name",
                },
                {
                  key: "capacity",
                  label: "Capacity",
                  render: (row) => `${row.capacity} guests`,
                },
                {
                  key: "price_per_night",
                  label: "Price / night",
                  render: (row) => currency(row.price_per_night),
                },
                {
                  key: "description",
                  label: "Description",
                  render: (row) => row.description || "No description",
                },
              ]}
              actions={(row) => (
                <div className="rowActions">
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => openEditRoomType(row)}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="dangerButton"
                    onClick={() => setDeleteRoomTypeId(row.room_type_id)}
                  >
                    Delete
                  </button>
                </div>
              )}
              empty="No room types found."
            />
          )}
        </div>
      )}

      {isManagement && (
        <>
          <Modal
            open={roomModalOpen}

            title={roomMode === "add" ? "Add room" : "Edit room"}

            onClose={() => {
              if (saveBusy) return;

              setRoomModalOpen(false);

              setEditingRoomId(null);

              setRoomForm(EMPTY_ROOM_FORM);
            }}
          >
            <form
              className="form"

              onSubmit={handleSaveRoom}
            >
              <label>
                Room number
                <input
                  type="number"

                  min="1"

                  value={roomForm.room_number}

                  onChange={(e) =>
                    setRoomForm({
                      ...roomForm,

                      room_number: e.target.value,
                    })
                  }

                  required
                />
              </label>

              <label>
                Room type
                <select
                  value={roomForm.room_type_id}

                  onChange={(e) =>
                    setRoomForm({
                      ...roomForm,

                      room_type_id: e.target.value,
                    })
                  }

                  disabled={roomTypesLoading}

                  required
                >
                  <option value="">
                    {roomTypesLoading
                      ? "Loading room types..."
                      : "Select room type"}
                  </option>

                  {typeRows.map((type) => (
                    <option
                      key={type.room_type_id}

                      value={type.room_type_id}
                    >
                      {type.type_name}
                    </option>
                  ))}
                </select>
                {roomTypesError && (
                  <small className="fieldError">
                    {roomTypesError}{" "}
                    <button
                      type="button"

                      className="inlineButton"

                      onClick={reloadRoomTypes}
                    >
                      Retry
                    </button>
                  </small>
                )}
              </label>

              <label>
                Floor
                <input
                  type="number"

                  min="0"

                  value={roomForm.floor}

                  onChange={(e) =>
                    setRoomForm({
                      ...roomForm,

                      floor: e.target.value,
                    })
                  }

                  required
                />
              </label>

              <label>
                Status
                <select
                  value={roomForm.status}

                  onChange={(e) =>
                    setRoomForm({
                      ...roomForm,

                      status: e.target.value,
                    })
                  }

                  disabled={
                    roomMode === "edit" && roomForm.status === "OCCUPIED"
                  }

                  required
                >
                  {roomForm.status === "OCCUPIED" && (
                    <option value="OCCUPIED">OCCUPIED</option>
                  )}

                  <option value="AVAILABLE">AVAILABLE</option>

                  <option value="MAINTENANCE">MAINTENANCE</option>
                </select>
                {roomMode === "edit" && roomForm.status === "OCCUPIED" && (
                  <small className="fieldHint">
                    Occupied status is managed automatically by check-in.
                  </small>
                )}
              </label>

              <div className="formActions">
                <button
                  type="button"

                  className="secondary"

                  onClick={() => {
                    setRoomModalOpen(false);

                    setEditingRoomId(null);

                    setRoomForm(EMPTY_ROOM_FORM);
                  }}

                  disabled={saveBusy}
                >
                  Cancel
                </button>

                <button
                  type="submit"

                  className="primary"

                  disabled={saveBusy}
                >
                  {saveBusy
                    ? "Saving..."
                    : roomMode === "add"
                      ? "Add room"
                      : "Save changes"}
                </button>
              </div>
            </form>
          </Modal>

          <ConfirmDialog
            open={Boolean(deleteRoomId)}

            title="Delete room"

            message="Are you sure you want to delete this room?"

            confirmLabel="Delete"

            cancelLabel="Cancel"

            onCancel={() => setDeleteRoomId(null)}

            onConfirm={async () => {
              try {
                await deleteRoom(deleteRoomId);
              } catch {
                // useAction already shows the error
              }
            }}
          />

          <Modal
            open={roomTypeModalOpen}
            title={roomTypeMode === "add" ? "Add room type" : "Edit room type"}
            onClose={() => {
              if (roomTypeSaveBusy) return;

              setRoomTypeModalOpen(false);
              setEditingRoomTypeId(null);
              setRoomTypeForm(EMPTY_ROOM_TYPE_FORM);
            }}
          >
            <form className="form" onSubmit={handleSaveRoomType}>
              <label>
                Name
                <input
                  type="text"
                  maxLength={50}
                  value={roomTypeForm.type_name}
                  onChange={(event) =>
                    setRoomTypeForm({
                      ...roomTypeForm,
                      type_name: event.target.value,
                    })
                  }
                  required
                />
                <small className="fieldHint">Maximum 50 characters.</small>
              </label>

              <label>
                Capacity
                <input
                  type="number"
                  min="1"
                  max="20"
                  value={roomTypeForm.capacity}
                  onChange={(event) =>
                    setRoomTypeForm({
                      ...roomTypeForm,
                      capacity: event.target.value,
                    })
                  }
                  required
                />
                <small className="fieldHint">1–20 guests.</small>
              </label>

              <label>
                Price per night
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={roomTypeForm.price_per_night}
                  onChange={(event) =>
                    setRoomTypeForm({
                      ...roomTypeForm,
                      price_per_night: event.target.value,
                    })
                  }
                  required
                />
              </label>

              <label>
                Description
                <textarea
                  rows="4"
                  value={roomTypeForm.description}
                  onChange={(event) =>
                    setRoomTypeForm({
                      ...roomTypeForm,
                      description: event.target.value,
                    })
                  }
                />
              </label>

              <div className="formActions">
                <button
                  type="button"
                  className="secondary"
                  disabled={roomTypeSaveBusy}
                  onClick={() => {
                    setRoomTypeModalOpen(false);
                    setEditingRoomTypeId(null);
                    setRoomTypeForm(EMPTY_ROOM_TYPE_FORM);
                  }}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="primary"
                  disabled={roomTypeSaveBusy}
                >
                  {roomTypeSaveBusy
                    ? "Saving..."
                    : roomTypeMode === "add"
                      ? "Add room type"
                      : "Save changes"}
                </button>
              </div>
            </form>
          </Modal>

          <ConfirmDialog
            open={Boolean(deleteRoomTypeId)}
            title="Delete room type"
            message="Are you sure you want to delete this room type?"
            confirmLabel="Delete"
            cancelLabel="Cancel"
            onCancel={() => setDeleteRoomTypeId(null)}
            onConfirm={async () => {
              try {
                await deleteRoomType(deleteRoomTypeId);
              } catch {
                // useAction already shows the error
              }
            }}
          />
        </>
      )}
    </section>
  );
}
