from __future__ import annotations

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.utils import timezone

from apps.common.validators import normalize_email, parse_bool, validate_date_range


class CommonValidatorTests(SimpleTestCase):
    def test_normalize_email_strips_and_lowercases(self) -> None:
        self.assertEqual(normalize_email("  USER@Example.COM "), "user@example.com")

    def test_parse_bool_handles_true_and_false_values(self) -> None:
        self.assertTrue(parse_bool("true"))
        self.assertFalse(parse_bool("0"))
        self.assertIsNone(parse_bool(""))

    def test_parse_bool_rejects_invalid_value(self) -> None:
        with self.assertRaises(ValidationError):
            parse_bool("maybe")

    def test_validate_date_range_rejects_reversed_range(self) -> None:
        now = timezone.now()
        later = now - timedelta(days=1)

        with self.assertRaises(ValidationError):
            validate_date_range(start=now, end=later)
