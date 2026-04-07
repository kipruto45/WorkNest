from __future__ import annotations

import logging
import time
import uuid

from apps.core.request_id import set_request_id

logger = logging.getLogger("apps.request")


class RequestIDMiddleware:
    header_name = "HTTP_X_REQUEST_ID"
    response_header_name = "X-Request-ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.META.get(self.header_name, str(uuid.uuid4()))
        request.request_id = request_id
        set_request_id(request_id)
        response = self.get_response(request)
        response[self.response_header_name] = request_id
        return response


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started_at = time.perf_counter()
        response = self.get_response(request)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)

        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.get_full_path(),
                "status_code": getattr(response, "status_code", 500),
                "duration_ms": duration_ms,
                "request_id": getattr(request, "request_id", "-"),
            },
        )
        return response
