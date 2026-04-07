class StructuredExtraFormatter:
    @staticmethod
    def format_message(record) -> str:
        method = getattr(record, "method", "-")
        path = getattr(record, "path", "-")
        status_code = getattr(record, "status_code", "-")
        duration_ms = getattr(record, "duration_ms", "-")
        request_id = getattr(record, "request_id", "-")
        return (
            f"{record.levelname} {record.asctime} request_id={request_id} "
            f"method={method} path={path} status={status_code} duration_ms={duration_ms} "
            f"{record.name} {record.getMessage()}"
        )
