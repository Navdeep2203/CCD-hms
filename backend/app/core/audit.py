import logging

_audit = logging.getLogger("audit")


def audit(actor_user_id: int | None, action: str, **details) -> None:
    """One structured log line per sensitive action (who did what to whom)."""
    extra = " ".join(f"{key}={value}" for key, value in details.items())
    _audit.info("actor=%s action=%s %s", actor_user_id, action, extra)
