"""Administrator activity logging helper (never records passwords or tokens)."""
import json

from flask import has_request_context, request
from flask_login import current_user

from extensions import db
from models import ActivityLog

SENSITIVE_KEYS = ("password", "password_hash", "csrf_token", "token", "secret", "current_password")


def _safe_detail(detail):
    if detail is None:
        return None
    if not isinstance(detail, dict):
        return str(detail)[:900]
    clean = {}
    for key, value in detail.items():
        if str(key).lower() in SENSITIVE_KEYS:
            continue
        if isinstance(value, str) and len(value) > 300:
            value = value[:300] + "..."
        clean[key] = value
    return json.dumps(clean)


def log_activity(action, entity=None, entity_id=None, detail=None):
    """Record an admin action. Safe to call anywhere; failures never break the request."""
    try:
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
        ip = None
        if has_request_context():
            ip = request.remote_addr
        db.session.add(ActivityLog(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            detail=_safe_detail(detail),
            ip=ip,
        ))
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()
