from django.test import TestCase

from apps.integrations.exceptions import IntegrationValidationError
from apps.integrations.validators import validate_email_recipients, validate_storage_path


class IntegrationValidatorTests(TestCase):
    def test_validate_email_recipients_requires_at_least_one_value(self) -> None:
        with self.assertRaises(IntegrationValidationError):
            validate_email_recipients([])

    def test_validate_storage_path_rejects_parent_traversal(self) -> None:
        with self.assertRaises(IntegrationValidationError):
            validate_storage_path("../secret.txt")

    def test_validate_storage_path_normalizes_relative_path(self) -> None:
        self.assertEqual(validate_storage_path("tasks/demo/file.txt"), "tasks/demo/file.txt")
