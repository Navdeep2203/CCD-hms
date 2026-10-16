export default function DataTable({
  rows = [],
  columns = [],
  actions,
  empty = "No records found.",
  loading = false,
}) {
  if (loading) {
    return <div className="tableState">Loading...</div>;
  }

  if (!rows.length) {
    return <div className="tableState">{empty}</div>;
  }

  return (
    <div className="tableScroll">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.label}</th>
            ))}
            {actions && <th className="actionHeader">Actions</th>}
          </tr>
        </thead>

        <tbody>
          {rows.map((row, index) => (
            <tr
              key={
                row.id ??
                row.department_id ??
                row.booking_id ??
                row.invoice_id ??
                row.maintenance_id ??
                row.room_id ??
                row.room_type_id ??
                row.service_id ??
                row.usage_id ??
                row.staff_id ??
                row.manager_id ??
                row.customer_id ??
                index
              }
            >
              {columns.map((column) => (
                <td key={column.key} data-label={column.label}>
                  {typeof column.render === "function"
                    ? column.render(row)
                    : (row[column.key] ?? "—")}
                </td>
              ))}

              {actions && (
                <td className="actionCellCol" data-label="Actions">
                  {typeof actions === "function" ? actions(row) : actions}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
