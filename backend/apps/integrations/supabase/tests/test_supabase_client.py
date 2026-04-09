from __future__ import annotations

import json
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.integrations.supabase.client import SupabaseClient
from apps.integrations.supabase.storage import SupabaseStorageClient


class DummyResponse:
    def __init__(self, payload: dict[str, str]) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


@override_settings(SUPABASE_URL="https://example.supabase.co", SUPABASE_KEY="service-key")
class SupabaseClientTests(TestCase):
    @override_settings(SUPABASE_URL="", SUPABASE_KEY="")
    def test_client_allows_explicit_credentials_without_settings(self) -> None:
        client = SupabaseClient(base_url="https://example.supabase.co", api_key="service-key")

        self.assertEqual(client.base_url, "https://example.supabase.co")
        self.assertEqual(client.api_key, "service-key")

    def test_client_includes_supabase_auth_headers(self) -> None:
        captured = {}

        def fake_urlopen(request, timeout=30):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            return DummyResponse({})

        with patch("apps.integrations.supabase.client.urlopen", side_effect=fake_urlopen):
            client = SupabaseClient()
            with client.request(method="GET", url="https://example.supabase.co/health"):
                pass

        self.assertEqual(captured["url"], "https://example.supabase.co/health")
        self.assertIn("Authorization", captured["headers"])

    def test_storage_client_normalizes_signed_url_response(self) -> None:
        client = SupabaseStorageClient(client=SupabaseClient())
        mocked_response = DummyResponse({"signedURL": "/storage/v1/object/sign/files/demo.pdf?token=test"})

        with patch.object(client.client, "request", return_value=mocked_response):
            url = client.create_signed_url(
                bucket="files",
                file_path="demo.pdf",
                expires_in=300,
                download_filename="demo.pdf",
            )

        self.assertIn("token=test", url)
        self.assertIn("download=demo.pdf", url)

    @override_settings(SUPABASE_KEY="", SUPABASE_SERVICE_ROLE_KEY="service-role-key")
    def test_client_falls_back_to_service_role_key(self) -> None:
        client = SupabaseClient()

        self.assertEqual(client.api_key, "service-role-key")
