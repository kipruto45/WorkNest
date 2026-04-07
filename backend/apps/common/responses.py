from __future__ import annotations

from rest_framework.response import Response


def build_response_payload(*, request, success: bool, message: str, data=None, errors=None) -> dict:
    payload = {
        "success": success,
        "message": message,
        "request_id": getattr(request, "request_id", None),
    }
    if success:
        payload["data"] = data
    else:
        payload["errors"] = errors
    return payload


def success_response(*, request, message: str, data=None, status_code: int = 200) -> Response:
    return Response(build_response_payload(request=request, success=True, message=message, data=data), status=status_code)


def error_response(*, request, message: str, errors=None, status_code: int = 400) -> Response:
    return Response(
        build_response_payload(request=request, success=False, message=message, errors=errors),
        status=status_code,
    )
