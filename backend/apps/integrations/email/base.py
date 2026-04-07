from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class EmailMessagePayload:
    to: list[str]
    subject: str
    text_body: str
    html_body: str | None = None
    from_email: str | None = None
    reply_to: list[str] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    provider_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class QueuedEmailPayload:
    email_type: str
    template_name: str
    recipient_email: str
    subject: str
    context: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    provider_metadata: dict[str, Any] = field(default_factory=dict)
    provider_name: str | None = None
    from_email: str | None = None
    reply_to: list[str] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    dedupe_key: str = ""
    source: str = ""
    related_object_type: str = ""
    related_object_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "QueuedEmailPayload":
        return cls(**value)


@dataclass(frozen=True)
class RenderedEmailTemplate:
    html_body: str
    text_body: str


class BaseEmailProvider(ABC):
    provider_name = ""

    @abstractmethod
    def send_email(self, payload: EmailMessagePayload) -> dict[str, Any]:
        raise NotImplementedError
