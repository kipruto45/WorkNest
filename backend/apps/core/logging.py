from __future__ import annotations

from apps.core.request_id import get_request_id


class RequestIDLogFilter:
    def filter(self, record) -> bool:
        record.request_id = get_request_id()
        record.method = getattr(record, "method", "-")
        record.path = getattr(record, "path", "-")
        record.status_code = getattr(record, "status_code", "-")
        record.duration_ms = getattr(record, "duration_ms", "-")
        return True
