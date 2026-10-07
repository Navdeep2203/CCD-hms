export default function StatCard({ label, value, note, tone = "default" }) {
  return (
    <div className={`statCard ${tone}`}>
      <div className="statTop">
        <span>{label}</span>
        <i />
      </div>

      <strong>{value}</strong>

      {note && <small>{note}</small>}
    </div>
  );
}
