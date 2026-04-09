from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import hmac
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from django.conf import settings

from apps.integrations.constants import DEFAULT_SIGNED_URL_TTL, DEFAULT_SUPABASE_TIMEOUT, STORAGE_PROVIDER_SUPABASE
from apps.integrations.exceptions import (
    ExternalProviderUnavailableError,
    IntegrationConfigurationError,
    StorageDeleteFailedError,
    StorageDownloadUrlError,
    StorageProviderError,
    StorageUploadFailedError,
)
from apps.integrations.storage.base import BaseStorageProvider, StoredFile
from apps.integrations.validators import sanitize_provider_error, validate_storage_path


class SupabaseS3StorageProvider(BaseStorageProvider):
    provider_name = STORAGE_PROVIDER_SUPABASE

    def __init__(
        self,
        *,
        bucket: str | None = None,
        endpoint: str | None = None,
        region: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        force_path_style: bool | None = None,
        timeout: int | None = None,
    ) -> None:
        self.endpoint = str(endpoint if endpoint is not None else getattr(settings, "SUPABASE_S3_ENDPOINT", "")).rstrip("/")
        self.region = str(region if region is not None else getattr(settings, "SUPABASE_S3_REGION", "eu-west-1")).strip() or "eu-west-1"
        self.access_key_id = str(
            access_key_id if access_key_id is not None else getattr(settings, "SUPABASE_S3_ACCESS_KEY_ID", "")
        ).strip()
        self.secret_access_key = str(
            secret_access_key if secret_access_key is not None else getattr(settings, "SUPABASE_S3_SECRET_ACCESS_KEY", "")
        ).strip()
        self.bucket = str(
            bucket
            or getattr(settings, "SUPABASE_S3_BUCKET", "")
            or getattr(settings, "ATTACHMENTS_SUPABASE_BUCKET", "")
        ).strip()
        if force_path_style is None:
            force_path_style = bool(getattr(settings, "SUPABASE_S3_FORCE_PATH_STYLE", True))
        self.force_path_style = bool(force_path_style)
        self.timeout = int(timeout or getattr(settings, "SUPABASE_TIMEOUT", DEFAULT_SUPABASE_TIMEOUT))
        self._parsed_endpoint = urlsplit(self.endpoint)

        missing = []
        if not self.endpoint:
            missing.append("SUPABASE_S3_ENDPOINT")
        if not self.bucket:
            missing.append("SUPABASE_S3_BUCKET")
        if not self.access_key_id:
            missing.append("SUPABASE_S3_ACCESS_KEY_ID")
        if not self.secret_access_key:
            missing.append("SUPABASE_S3_SECRET_ACCESS_KEY")
        if missing:
            raise IntegrationConfigurationError(
                f"Supabase S3 storage requires {', '.join(sorted(missing))}."
            )
        if not self._parsed_endpoint.scheme or not self._parsed_endpoint.netloc:
            raise IntegrationConfigurationError("SUPABASE_S3_ENDPOINT must be a valid absolute URL.")

    def upload_file(self, *, file_obj, destination_path: str, mime_type: str) -> StoredFile:
        safe_path = validate_storage_path(destination_path)
        try:
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            payload = file_obj.read()
            self._signed_request(
                method="PUT",
                file_path=safe_path,
                payload=payload,
                headers={"Content-Type": mime_type or "application/octet-stream"},
            )
        except Exception as exc:
            raise StorageUploadFailedError(
                sanitize_provider_error(exc, fallback_message="Supabase S3 upload failed.")
            ) from exc
        return StoredFile(file_path=safe_path, storage_provider=self.provider_name)

    def delete_file(self, *, file_path: str) -> None:
        safe_path = validate_storage_path(file_path)
        try:
            self._signed_request(method="DELETE", file_path=safe_path, payload=b"")
        except Exception as exc:
            raise StorageDeleteFailedError(
                sanitize_provider_error(exc, fallback_message="Supabase S3 delete failed.")
            ) from exc

    def open_file(self, *, file_path: str):
        raise StorageProviderError("Supabase S3 files are served through signed URLs, not direct streaming.")

    def generate_download_url(self, *, file_path: str, expires_in: int, download_filename: str | None = None) -> str:
        safe_path = validate_storage_path(file_path)
        resolved_expires_in = max(1, int(expires_in or getattr(settings, "SUPABASE_S3_SIGNED_URL_TTL", DEFAULT_SIGNED_URL_TTL)))
        try:
            return self._build_presigned_get_url(
                file_path=safe_path,
                expires_in=resolved_expires_in,
                download_filename=download_filename,
            )
        except Exception as exc:
            raise StorageDownloadUrlError(
                sanitize_provider_error(exc, fallback_message="Supabase S3 signed URL generation failed.")
            ) from exc

    def _build_presigned_get_url(self, *, file_path: str, expires_in: int, download_filename: str | None = None) -> str:
        amz_date, datestamp = self._timestamps()
        host, canonical_uri, request_url = self._resolve_target(file_path=file_path)
        credential_scope = f"{datestamp}/{self.region}/s3/aws4_request"
        params: list[tuple[str, str]] = [
            ("X-Amz-Algorithm", "AWS4-HMAC-SHA256"),
            ("X-Amz-Credential", f"{self.access_key_id}/{credential_scope}"),
            ("X-Amz-Date", amz_date),
            ("X-Amz-Expires", str(expires_in)),
            ("X-Amz-SignedHeaders", "host"),
        ]
        if download_filename:
            safe_name = str(download_filename or "").replace('"', "")
            params.append(("response-content-disposition", f'attachment; filename="{safe_name}"'))
        canonical_query = self._canonical_query_string(params)
        canonical_request = "\n".join(
            [
                "GET",
                canonical_uri,
                canonical_query,
                f"host:{host}\n",
                "host",
                "UNSIGNED-PAYLOAD",
            ]
        )
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )
        signature = hmac.new(
            self._get_signing_key(datestamp=datestamp),
            string_to_sign.encode("utf-8"),
            sha256,
        ).hexdigest()
        query_string = f"{canonical_query}&X-Amz-Signature={signature}"
        return f"{request_url}?{query_string}"

    def _signed_request(
        self,
        *,
        method: str,
        file_path: str,
        payload: bytes,
        headers: dict[str, str] | None = None,
    ):
        amz_date, datestamp = self._timestamps()
        payload_hash = sha256(payload).hexdigest()
        host, canonical_uri, request_url = self._resolve_target(file_path=file_path)
        request_headers = {"host": host, "x-amz-content-sha256": payload_hash, "x-amz-date": amz_date}
        if headers:
            request_headers.update(headers)
        canonical_headers, signed_headers = self._canonical_headers(request_headers)
        canonical_request = "\n".join(
            [
                method.upper(),
                canonical_uri,
                "",
                canonical_headers,
                signed_headers,
                payload_hash,
            ]
        )
        credential_scope = f"{datestamp}/{self.region}/s3/aws4_request"
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )
        signature = hmac.new(
            self._get_signing_key(datestamp=datestamp),
            string_to_sign.encode("utf-8"),
            sha256,
        ).hexdigest()
        authorization = (
            "AWS4-HMAC-SHA256 "
            f"Credential={self.access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )
        outgoing_headers = dict(request_headers)
        outgoing_headers["Authorization"] = authorization
        request = Request(request_url, data=payload, headers=outgoing_headers, method=method.upper())
        try:
            return urlopen(request, timeout=self.timeout)
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            message = sanitize_provider_error(Exception(body), fallback_message="Supabase S3 request failed.")
            raise ExternalProviderUnavailableError(message) from exc
        except URLError as exc:
            raise ExternalProviderUnavailableError("Supabase S3 could not be reached.") from exc

    def _resolve_target(self, *, file_path: str) -> tuple[str, str, str]:
        prefix = self._build_prefix_path()
        encoded_bucket = quote(self.bucket, safe="-_.~")
        encoded_file_path = quote(file_path, safe="/-_.~")
        if self.force_path_style or prefix:
            host = self._parsed_endpoint.netloc
            canonical_uri = f"{prefix}/{encoded_bucket}/{encoded_file_path}" if prefix else f"/{encoded_bucket}/{encoded_file_path}"
            request_netloc = host
        else:
            host = f"{self.bucket}.{self._parsed_endpoint.netloc}"
            canonical_uri = f"/{encoded_file_path}"
            request_netloc = host
        request_url = urlunsplit((self._parsed_endpoint.scheme, request_netloc, canonical_uri, "", ""))
        return host, canonical_uri, request_url

    def _build_prefix_path(self) -> str:
        parts = [quote(part, safe="-_.~") for part in self._parsed_endpoint.path.split("/") if part]
        if not parts:
            return ""
        return "/" + "/".join(parts)

    def _canonical_headers(self, headers: dict[str, str]) -> tuple[str, str]:
        normalized = []
        for key, value in headers.items():
            normalized.append((str(key).strip().lower(), " ".join(str(value).strip().split())))
        normalized.sort(key=lambda item: item[0])
        canonical_headers = "".join(f"{key}:{value}\n" for key, value in normalized)
        signed_headers = ";".join(key for key, _value in normalized)
        return canonical_headers, signed_headers

    def _canonical_query_string(self, items: list[tuple[str, str]]) -> str:
        ordered = sorted((str(key), str(value)) for key, value in items)
        return urlencode(ordered, quote_via=quote, safe="-_.~")

    def _timestamps(self) -> tuple[str, str]:
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        return amz_date, now.strftime("%Y%m%d")

    def _get_signing_key(self, *, datestamp: str) -> bytes:
        key_date = hmac.new(f"AWS4{self.secret_access_key}".encode("utf-8"), datestamp.encode("utf-8"), sha256).digest()
        key_region = hmac.new(key_date, self.region.encode("utf-8"), sha256).digest()
        key_service = hmac.new(key_region, b"s3", sha256).digest()
        return hmac.new(key_service, b"aws4_request", sha256).digest()
