function statusTone(value = "") {
  const key = String(value).toUpperCase();

  if (["AVAILABLE", "APPROVED", "CHECKED_IN", "COMPLETED"].includes(key)) {
    return "good";
  }

  if (
    [
      "PENDING",
      "CHECKIN_PENDING",
      "CHECKOUT_PENDING",
      "RESERVED",
      "IN_PROGRESS",
    ].includes(key)
  ) {
    return "warn";
  }

  if (["REJECTED", "CANCELLED", "FAILED", "MAINTENANCE"].includes(key)) {
    return "bad";
  }

  return "neutral";
}

export default function Badge({ children }) {
  return <span className={`badge ${statusTone(children)}`}>{children}</span>;
}
