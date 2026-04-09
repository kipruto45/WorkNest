from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SMSMessagePayload:
    to: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseSMSProvider:
    provider_name = "base"

    def send_sms(self, to: str, message: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError
