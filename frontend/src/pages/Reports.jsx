import { useMemo } from "react";

import { useFetch } from "../hooks/useFetch";
import PageState from "../components/PageState";
import DataTable from "../components/DataTable";
import Badge from "../components/Badge";
import StatCard from "../components/StatCard";
import PageHeader from "../components/PageHeader";
import { currency } from "../utils/format";

function sumValues(rows) {
  return (rows || []).reduce((sum, row) => sum + Number(row.value || 0), 0);
}

export default function Reports() {
  const { data, loading, error, reload } = useFetch("/reports/summary");

  const report = data || {
    revenue: [],
    bookings: [],
    status_breakdown: [],
    room_types: [],
    services: [],
  };

  const totalRevenue = useMemo(
    () => sumValues(report.revenue),
    [report.revenue],
  );

  const totalBookings = useMemo(
    () => sumValues(report.bookings),
    [report.bookings],
  );

  const totalRooms = useMemo(
    () => sumValues(report.room_types),
    [report.room_types],
  );

  const totalServiceUnits = useMemo(
    () => sumValues(report.services),
    [report.services],
  );

  if (loading || error) {
    return <PageState loading={loading} error={error} onRetry={reload} />;
  }

  return (
    <section className="workspace">
      <PageHeader
        eyebrow="Analytics"
        title="Operational Reports"
        subtitle="Comprehensive metrics on hotel revenue performance, booking volume, and amenities."
        primaryAction={
          <button type="button" className="secondary" onClick={reload}>
            Refresh
          </button>
        }
      />

      <div className="panel wide">

        <div className="statsGrid">
          <StatCard label="Recorded revenue" value={currency(totalRevenue)} />
          <StatCard label="Total bookings" value={totalBookings} />
          <StatCard label="Rooms configured" value={totalRooms} />
          <StatCard label="Service units used" value={totalServiceUnits} />
        </div>
      </div>

      <div className="gridTwo">
        <section className="panel">
          <div className="panelHead">
            <div>
              <p className="eyebrow">Revenue</p>
              <h2>Monthly revenue</h2>
            </div>
          </div>

          <DataTable
            rows={report.revenue}
            columns={[
              { key: "label", label: "Month" },
              {
                key: "value",
                label: "Revenue",
                render: (row) => currency(row.value),
              },
            ]}
            empty="No revenue data available."
          />
        </section>

        <section className="panel">
          <div className="panelHead">
            <div>
              <p className="eyebrow">Bookings</p>
              <h2>Monthly bookings</h2>
            </div>
          </div>

          <DataTable
            rows={report.bookings}
            columns={[
              { key: "label", label: "Month" },
              { key: "value", label: "Bookings" },
            ]}
            empty="No booking data available."
          />
        </section>
      </div>

      <div className="gridTwo">
        <section className="panel">
          <div className="panelHead">
            <div>
              <p className="eyebrow">Lifecycle</p>
              <h2>Booking status breakdown</h2>
            </div>
          </div>

          <DataTable
            rows={report.status_breakdown}
            columns={[
              { key: "label", label: "Status" },
              {
                key: "value",
                label: "Count",
                render: (row) => <Badge>{row.value}</Badge>,
              },
            ]}
            empty="No booking status data available."
          />
        </section>

        <section className="panel">
          <div className="panelHead">
            <div>
              <p className="eyebrow">Inventory</p>
              <h2>Rooms by type</h2>
            </div>
          </div>

          <DataTable
            rows={report.room_types}
            columns={[
              { key: "label", label: "Room type" },
              { key: "value", label: "Rooms" },
            ]}
            empty="No room type data available."
          />
        </section>
      </div>

      <section className="panel wide">
        <div className="panelHead">
          <div>
            <p className="eyebrow">Services</p>
            <h2>Service usage</h2>
          </div>
        </div>

        <DataTable
          rows={report.services}
          columns={[
            { key: "label", label: "Service" },
            { key: "value", label: "Units used" },
          ]}
          empty="No service usage data available."
        />
      </section>
    </section>
  );
}
