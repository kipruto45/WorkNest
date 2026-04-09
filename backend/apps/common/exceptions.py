from __future__ import annotations

import logging

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.exceptions import ErrorDetail
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class AppAPIException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Request failed."
    default_code = "request_failed"

    def __init__(self, detail=None, *, errors=None):
        self.error_payload = errors
        super().__init__(detail or self.default_detail)


class ConflictError(AppAPIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A conflicting resource already exists."
    default_code = "conflict"


class ServiceUnavailableError(AppAPIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "The service is temporarily unavailable."
    default_code = "service_unavailable"


def _stringify_errors(errors):
    if isinstance(errors, list):
        return [_stringify_errors(item) for item in errors]
    if isinstance(errors, dict):
        return {key: _stringify_errors(value) for key, value in errors.items()}
    if isinstance(errors, ErrorDetail):
        return str(errors)
    return errors


def _collect_error_messages(errors) -> list[str]:
    if isinstance(errors, list):
        messages = []
        for item in errors:
            messages.extend(_collect_error_messages(item))
        return messages
    if isinstance(errors, dict):
        messages = []
        for item in errors.values():
            messages.extend(_collect_error_messages(item))
        return messages
    if isinstance(errors, ErrorDetail):
        return [str(errors)]
    if isinstance(errors, str):
        return [errors]
    return []


def _resolve_error_message(*, status_code: int, errors) -> str:
    if status_code == status.HTTP_400_BAD_REQUEST:
        explicit_messages = _collect_error_messages(errors)
        if explicit_messages:
            return explicit_messages[0]
        return "Validation failed."

    if status_code == status.HTTP_401_UNAUTHORIZED:
        combined_messages = " ".join(_collect_error_messages(errors)).lower()
        if any(fragment in combined_messages for fragment in ("token", "expired", "not valid", "jwt")):
            return "Your session expired. Please log in again."
        explicit_messages = _collect_error_messages(errors)
        if explicit_messages:
            return explicit_messages[0]
        return "Authentication credentials were not provided or are invalid."

    if status_code == status.HTTP_403_FORBIDDEN:
        return "You do not have permission to perform this action."
    if status_code == status.HTTP_404_NOT_FOUND:
        return "The requested resource was not found."
    if status_code == status.HTTP_409_CONFLICT:
        return "Request could not be completed due to a conflict."
    if status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return "Too many requests were made."
    if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        return "Server error while processing request."
    return "Request failed."


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    request = context.get("request")
    request_id = getattr(request, "request_id", None)

    if response is None:
        logger.exception("unhandled_api_exception", exc_info=exc, extra={"request_id": request_id})
        errors = {"detail": "Internal server error."}
        if settings.DEBUG:
            errors["debug"] = f"{exc.__class__.__name__}: {exc}"
        return Response(
            {
                "success": False,
                "message": "Server error while processing request.",
                "errors": errors,
                "request_id": request_id,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    errors = getattr(exc, "error_payload", None)
    if errors is None:
        errors = response.data
    errors = _stringify_errors(errors)
    message = _resolve_error_message(status_code=response.status_code, errors=errors)

    response.data = {
        "success": False,
        "message": message,
        "errors": errors,
        "request_id": request_id,
    }
    return response
