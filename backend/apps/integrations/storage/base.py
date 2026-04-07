from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class StoredFile:
    file_path: str
    storage_provider: str
    file_url: str = ""


class BaseStorageProvider(ABC):
    provider_name = ""

    @abstractmethod
    def upload_file(self, *, file_obj, destination_path: str, mime_type: str) -> StoredFile:
        raise NotImplementedError

    @abstractmethod
    def delete_file(self, *, file_path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def open_file(self, *, file_path: str):
        raise NotImplementedError

    @abstractmethod
    def generate_download_url(self, *, file_path: str, expires_in: int, download_filename: str | None = None) -> str:
        raise NotImplementedError
