from __future__ import annotations

from rest_framework.exceptions import PermissionDenied

from apps.common.pagination import DefaultPageNumberPagination
from apps.common.responses import success_response
from apps.common.utils import build_paginated_payload


class PermissionEnforcerMixin:
    def enforce_permission(self, *, request, permission_class, obj=None):
        permission = permission_class()
        allowed = (
            permission.has_object_permission(request, self, obj)
            if obj is not None
            else permission.has_permission(request, self)
        )
        if not allowed:
            raise PermissionDenied(detail=getattr(permission, "message", "You do not have permission to perform this action."))


class PaginatedAPIViewMixin:
    pagination_class = DefaultPageNumberPagination

    def paginate_success_response(self, *, request, queryset, serializer_class, message: str, serializer_context=None):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        target = page if page is not None else queryset
        serializer = serializer_class(target, many=True, context=serializer_context or {"request": request})
        data = (
            build_paginated_payload(paginator=paginator, serializer_data=serializer.data)
            if page is not None
            else serializer.data
        )
        return success_response(
            request=request,
            message=message,
            data=data,
        )
