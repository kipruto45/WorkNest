from __future__ import annotations

from contextvars import ContextVar

_audit_request_context: ContextVar[dict | None] = ContextVar("audit_request_context", default=None)


def _get_client_ip(request) -> str | None:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def set_current_audit_request_context(*, request) -> None:
    _audit_request_context.set(
        {
            "ip_address": _get_client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:1000],
            "request_id": getattr(request, "request_id", None),
        }
    )


def get_current_audit_request_context() -> dict:
    return _audit_request_context.get() or {}


def clear_current_audit_request_context() -> None:
    _audit_request_context.set(None)


class AuditLogContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_audit_request_context(request=request)
        try:
            return self.get_response(request)
        finally:
            clear_current_audit_request_context()
