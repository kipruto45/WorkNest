from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError


def normalize_email(value: str) -> str:
    email = str(value or "").strip().lower()
    if not email:
        raise DjangoValidationError("Email address is required.")
    return email


def parse_bool(value):
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise DjangoValidationError("Boolean value is invalid.")


def validate_date_range(*, start=None, end=None, start_label: str = "start", end_label: str = "end") -> None:
    if start and end and start > end:
        raise DjangoValidationError({end_label: f"Must be on or after {start_label}."})

