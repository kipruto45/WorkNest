from __future__ import annotations

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.exceptions import ErrorDetail
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


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


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    request = context.get("request")
    request_id = getattr(request, "request_id", None)

    if response is None:
        errors = {"detail": "Internal server error."}
        if settings.DEBUG:
            errors["debug"] = f"{exc.__class__.__name__}: {exc}"
        return Response(
            {
                "success": False,
                "message": "An unexpected error occurred.",
                "errors": errors,
                "request_id": request_id,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    errors = getattr(exc, "error_payload", None)
    if errors is None:
        errors = response.data
    errors = _stringify_errors(errors)
    message = "Request failed."
    if response.status_code == status.HTTP_400_BAD_REQUEST:
        message = "Validation failed."
    elif response.status_code == status.HTTP_401_UNAUTHORIZED:
        message = "Authentication credentials were not provided or are invalid."
    elif response.status_code == status.HTTP_403_FORBIDDEN:
        message = "You do not have permission to perform this action."
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        message = "The requested resource was not found."
    elif response.status_code == status.HTTP_409_CONFLICT:
        message = "Request could not be completed due to a conflict."
    elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        message = "Too many requests were made."
    elif response.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        message = "An unexpected error occurred."

    response.data = {
        "success": False,
        "message": message,
        "errors": errors,
        "request_id": request_id,
    }
    return response
