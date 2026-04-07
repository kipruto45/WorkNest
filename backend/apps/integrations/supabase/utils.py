from __future__ import annotations

from urllib.parse import quote, urlencode, urljoin


def build_storage_object_url(*, base_url: str, bucket: str, file_path: str) -> str:
    return f"{base_url.rstrip('/')}/storage/v1/object/{quote(bucket, safe='')}/{quote(file_path, safe='/')}"


def build_storage_sign_url(*, base_url: str, bucket: str, file_path: str) -> str:
    return f"{base_url.rstrip('/')}/storage/v1/object/sign/{quote(bucket, safe='')}/{quote(file_path, safe='/')}"


def normalize_signed_url(*, base_url: str, signed_url: str, download_filename: str | None = None) -> str:
    absolute_url = signed_url if signed_url.startswith("http") else urljoin(f"{base_url.rstrip('/')}/", signed_url.lstrip("/"))
    if download_filename:
        separator = "&" if "?" in absolute_url else "?"
        absolute_url = f"{absolute_url}{separator}{urlencode({'download': download_filename})}"
    return absolute_url
