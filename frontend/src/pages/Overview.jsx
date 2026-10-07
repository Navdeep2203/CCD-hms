import { Link } from "react-router-dom";

import { api } from "../api/client";
import { useFetch } from "../hooks/useFetch";
import DataTable from "../components/DataTable";
import Badge from "../components/Badge";
import StatCard from "../components/StatCard";
import PageState from "../components/PageState";
import { currency, fmtDate } from "../utils/format";

function GuestOverview({ data }) {
  const currentStay = data.current_stay;

  return (
    <section className="workspace">
      <section className="guestWelcome">
        <div>
          <p className="eyebrow">My stay</p>
          <h2>Welcome back</h2>
          <p>
            Keep track of your current stay, upcoming bookings, balance, and
            loyalty progress.
          </p>
        </div>

        <Link to="/rooms" className="primary">
          Book a room
        </Link>
      </section>

      <section className="statsGrid">
        <StatCard
          label="Balance due"
          value={currency(data.balance_due)}
          note="Across your stays"
          tone="rose"
        />

        <StatCard
          label="Loyalty points"
          value={data.loyalty_points ?? 0}
          note="Current points"
          tone="teal"
        />

        <StatCard
          label="Completed stays"
          value={data.completed_stays ?? 0}
          note="Previous stays"
          tone="blue"
        />
      </section>

      <section className="gridTwo">
        <div className="panel">
          <div className="panelHead">
            <h2>Current stay</h2>
          </div>

          {currentStay ? (
            <div className="stayCard">
              <div>
                <span className="eyebrow">Room</span>
                <strong>Room {currentStay.room_number}</strong>
              </div>

              <div>
                <span className="eyebrow">Type</span>
                <strong>{currentStay.type_name}</strong>
              </div>

              <div>
                <span className="eyebrow">Check-in</span>
                <strong>{fmtDate(currentStay.check_in_date)}</strong>
              </div>

              <div>
                <span className="eyebrow">Check-out</span>
                <strong>{fmtDate(currentStay.check_out_date)}</strong>
              </div>

              <Badge>{currentStay.booking_status}</Badge>
            </div>
          ) : (
            <div className="emptyState">You don't have a current stay.</div>
          )}
        </div>

        <div className="panel">
          <div className="panelHead">
            <h2>Upcoming bookings</h2>
            <span>{data.upcoming?.length || 0} bookings</span>
          </div>

          <div className="bookingList">
            {data.upcoming?.length ? (
              data.upcoming.map((booking) => (
                <div key={booking.booking_id} className="bookingItem">
                  <div>
                    <strong>Room {booking.room_number}</strong>

                    <span>{booking.type_name}</span>
                  </div>

                  <div>
                    <strong>{fmtDate(booking.check_in_date)}</strong>

                    <span>to {fmtDate(booking.check_out_date)}</span>
                  </div>

                  <Badge>{booking.booking_status}</Badge>
                </div>
              ))
            ) : (
              <div className="emptyState">No upcoming bookings.</div>
            )}
          </div>
        </div>
      </section>
    </section>
  );
}

function OperationsOverview({ data }) {
  const totalRooms = Number(data.total_rooms || 0);
  const occupiedRooms = Number(data.occupied_rooms || 0);
  const availableRooms = Number(data.available_rooms || 0);

  const occupancyRate = totalRooms
    ? Math.round((occupiedRooms / totalRooms) * 100)
    : 0;

  const availabilityRate = totalRooms
    ? Math.round((availableRooms / totalRooms) * 100)
    : 0;

  return (
    <section className="workspace">
      <section className="opsBanner">
        <div>
          <p className="eyebrow">Today at a glance</p>

          <h2>{occupancyRate}% occupied</h2>

          <span>
            {availableRooms} rooms available, {data.pending_bookings} booking
            approvals waiting
          </span>
        </div>

        <div className="meterBlock">
          <div className="availabilityMeter" aria-label="Room occupancy meter">
            <i
              style={{
                width: `${occupancyRate}%`,
              }}
            />
          </div>

          <div className="meterLegend">
            <span>Occupied</span>
            <strong>{occupancyRate}%</strong>
          </div>
        </div>

        {data.kind === "management" && (
          <div className="bannerStats">
            <span>
              <strong>{availabilityRate}%</strong> availability
            </span>

            <span>
              <strong>{currency(data.today_revenue)}</strong> today revenue
            </span>
          </div>
        )}

        {data.kind === "staff" && (
          <div className="bannerStats">
            <span>
              <strong>{availabilityRate}%</strong> availability
            </span>
          </div>
        )}
      </section>

      <section className="statsGrid">
        <StatCard
          label="Total rooms"
          value={data.total_rooms}
          note={`${data.available_rooms} available`}
          tone="teal"
        />

        <StatCard
          label="Occupied"
          value={data.occupied_rooms}
          note={`${data.maintenance_rooms} in maintenance`}
          tone="amber"
        />

        <StatCard
          label="Pending bookings"
          value={data.pending_bookings}
          note="Awaiting action"
          tone="rose"
        />

        {data.kind === "management" ? (
          <StatCard
            label="Month revenue"
            value={currency(data.month_revenue)}
            note={`Today ${currency(data.today_revenue)}`}
            tone="blue"
          />
        ) : (
          <StatCard
            label="Maintenance"
            value={data.maintenance_rooms}
            note="Rooms needing attention"
            tone="blue"
          />
        )}
      </section>

      <section className="gridTwo">
        <div className="panel">
          <div className="panelHead">
            <h2>Arrivals today</h2>
            <span>{data.arrivals_today?.length || 0}</span>
          </div>

          <DataTable
            rows={data.arrivals_today || []}
            columns={[
              {
                key: "booking_id",
                label: "ID",
              },
              {
                key: "customer_name",
                label: "Guest",
              },
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
                key: "booking_status",
                label: "Status",
                render: (row) => <Badge>{row.booking_status}</Badge>,
              },
            ]}
            empty="No arrivals today."
          />
        </div>

        <div className="panel">
          <div className="panelHead">
            <h2>Departures today</h2>
            <span>{data.departures_today?.length || 0}</span>
          </div>

          <DataTable
            rows={data.departures_today || []}
            columns={[
              {
                key: "booking_id",
                label: "ID",
              },
              {
                key: "customer_name",
                label: "Guest",
              },
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
            empty="No departures today."
          />
        </div>
      </section>

      {data.kind === "management" && (
        <section className="panel">
          <div className="panelHead">
            <h2>Recent bookings</h2>
            <span>{data.recent_bookings?.length || 0}</span>
          </div>

          <DataTable
            rows={data.recent_bookings || []}
            columns={[
              {
                key: "booking_id",
                label: "ID",
              },
              {
                key: "customer_name",
                label: "Guest",
              },
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
                key: "booking_status",
                label: "Status",
                render: (row) => <Badge>{row.booking_status}</Badge>,
              },
            ]}
            empty="No recent bookings."
          />
        </section>
      )}
    </section>
  );
}

export default function Overview() {
  const { data, loading, error, reload } = useFetch("/dashboard/overview");

  if (loading || error) {
    return <PageState loading={loading} error={error} onRetry={reload} />;
  }

  if (!data) {
    return <PageState error="Unable to load the dashboard." onRetry={reload} />;
  }

  if (data.kind === "guest") {
    return <GuestOverview data={data} />;
  }

  return <OperationsOverview data={data} />;
}
