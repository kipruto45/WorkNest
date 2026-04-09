from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.integrations.models import SMSDelivery
from apps.integrations.sms.africastalking import AfricasTalkingSMSProvider
from apps.integrations.sms.celcom import CelcomSMSProvider
from apps.integrations.sms.exceptions import SMSConfigurationError
from apps.integrations.sms.services import normalize_phone_number, queue_sms

User = get_user_model()


@override_settings(SMS_ENABLED=True, CELERY_TASK_ALWAYS_EAGER=True)
class SMSServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            email="sms@example.com",
            password="StrongPass123!",
            name="SMS User",
            phone_number="+254712345678",
            phone_verified=True,
            sms_opt_in=True,
        )

    def test_normalize_phone_number_uses_default_country_code(self) -> None:
        self.assertEqual(normalize_phone_number("0712345678", "+254"), "+254712345678")

    def test_queue_sms_marks_delivery_sent_when_provider_succeeds(self) -> None:
        with patch(
            "apps.integrations.sms.services.deliver_sms_message",
            return_value={"provider": "africas_talking", "message_id": "msg-1", "status": "sent"},
        ):
            delivery = queue_sms(
                user=self.user,
                phone_number=self.user.phone_number,
                message_type="task_assigned",
                message_body="You have been assigned a task.",
                dedupe_key="sms:test:sent",
            )

        delivery.refresh_from_db()
        self.assertEqual(delivery.status, SMSDelivery.Status.SENT)
        self.assertEqual(delivery.provider, "africas_talking")

    @override_settings(SMS_PROVIDER="celcom", CELERY_TASK_ALWAYS_EAGER=False)
    @patch(
        "apps.integrations.sms.services.deliver_sms_message",
        return_value={"provider": "celcom", "message_id": "msg-celcom-1", "status": "sent"},
    )
    @patch("apps.integrations.sms.services.threading.Thread")
    def test_queue_sms_can_force_immediate_celcom_delivery(self, thread_mock, _deliver_sms_message) -> None:
        with self.captureOnCommitCallbacks(execute=True):
            delivery = queue_sms(
                user=self.user,
                phone_number=self.user.phone_number,
                message_type="phone_verification",
                message_body="Your verification code is 123456.",
                dedupe_key="sms:test:immediate",
                force=True,
                deliver_immediately=True,
            )

        delivery.refresh_from_db()
        thread_mock.assert_not_called()
        self.assertEqual(delivery.status, SMSDelivery.Status.SENT)
        self.assertEqual(delivery.provider, "celcom")

    def test_queue_sms_skips_delivery_when_user_opted_out(self) -> None:
        self.user.sms_opt_in = False
        self.user.save(update_fields=["sms_opt_in", "updated_at"])

        delivery = queue_sms(
            user=self.user,
            phone_number=self.user.phone_number,
            message_type="task_assigned",
            message_body="You have been assigned a task.",
            dedupe_key="sms:test:skip",
        )

        self.assertEqual(delivery.status, SMSDelivery.Status.SKIPPED)
        self.assertIn("opted out", delivery.error_message.lower())

    def test_queue_sms_skips_delivery_when_phone_number_is_invalid(self) -> None:
        self.user.phone_number = "invalid-number"
        self.user.save(update_fields=["phone_number", "updated_at"])

        delivery = queue_sms(
            user=self.user,
            phone_number=self.user.phone_number,
            message_type="task_assigned",
            message_body="You have been assigned a task.",
            dedupe_key="sms:test:invalid-phone",
        )

        self.assertEqual(delivery.status, SMSDelivery.Status.SKIPPED)
        self.assertIn("valid phone number", delivery.error_message.lower())

    @override_settings(SMS_ENABLED=True, CELERY_TASK_ALWAYS_EAGER=False)
    @patch("apps.integrations.sms.services.threading.Thread")
    def test_queue_sms_schedules_background_delivery_when_not_eager(self, thread_mock) -> None:
        with self.captureOnCommitCallbacks(execute=True):
            delivery = queue_sms(
                user=self.user,
                phone_number=self.user.phone_number,
                message_type="task_assigned",
                message_body="You have been assigned a task.",
                dedupe_key="sms:test:background",
            )

        delivery.refresh_from_db()
        thread_mock.assert_called_once()
        thread_mock.return_value.start.assert_called_once()
        self.assertEqual(delivery.status, SMSDelivery.Status.QUEUED)


@override_settings(
    AFRICAS_TALKING_USERNAME="sandbox",
    AFRICAS_TALKING_API_KEY="test-key",
    AFRICAS_TALKING_ENVIRONMENT="sandbox",
    AFRICAS_TALKING_USE_SANDBOX=True,
    SMS_USE_SANDBOX=True,
)
class AfricasTalkingProviderTests(TestCase):
    def test_provider_uses_sandbox_base_url(self) -> None:
        provider = AfricasTalkingSMSProvider()

        self.assertTrue(provider.use_sandbox)
        self.assertIn("sandbox", provider.api_url)

    def test_provider_maps_successful_response(self) -> None:
        provider = AfricasTalkingSMSProvider()
        response_body = (
            b'{"SMSMessageData":{"Message":"Sent to 1/1","Recipients":[{"status":"Success","messageId":"msg-1","cost":"KES 0.80","number":"+254712345678"}]}}'
        )

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return response_body

        with patch("apps.integrations.sms.africastalking.request.urlopen", return_value=FakeResponse()):
            result = provider.send_sms(to="+254712345678", message="Hello from WorkNest")

        self.assertEqual(result["provider"], "africas_talking")
        self.assertEqual(result["message_id"], "msg-1")
        self.assertEqual(result["status"], "sent")

    @override_settings(
        AFRICAS_TALKING_USERNAME="worknest",
        AFRICAS_TALKING_API_KEY="test-key",
        AFRICAS_TALKING_ENVIRONMENT="sandbox",
        AFRICAS_TALKING_USE_SANDBOX=True,
        SMS_USE_SANDBOX=True,
    )
    def test_provider_rejects_non_sandbox_username_in_sandbox_mode(self) -> None:
        with self.assertRaisesMessage(SMSConfigurationError, "Sandbox mode requires AFRICAS_TALKING_USERNAME=sandbox."):
            AfricasTalkingSMSProvider()

    @override_settings(
        AFRICAS_TALKING_USERNAME="sandbox",
        AFRICAS_TALKING_API_KEY="test-key",
        AFRICAS_TALKING_ENVIRONMENT="live",
        AFRICAS_TALKING_USE_SANDBOX=False,
        SMS_USE_SANDBOX=False,
    )
    def test_provider_rejects_sandbox_username_in_live_mode(self) -> None:
        with self.assertRaisesMessage(SMSConfigurationError, "Live mode cannot use AFRICAS_TALKING_USERNAME=sandbox."):
            AfricasTalkingSMSProvider()

    @override_settings(
        AFRICAS_TALKING_USERNAME="sandbox",
        AFRICAS_TALKING_API_KEY="test-key",
        AFRICAS_TALKING_ENVIRONMENT="live",
        AFRICAS_TALKING_USE_SANDBOX=True,
        SMS_USE_SANDBOX="",
    )
    def test_provider_rejects_conflicting_environment_and_sandbox_flags(self) -> None:
        with self.assertRaisesMessage(SMSConfigurationError, "AFRICAS_TALKING_ENVIRONMENT and sandbox flags disagree."):
            AfricasTalkingSMSProvider()


class CheckSMSConfigCommandTests(TestCase):
    @override_settings(
        SMS_ENABLED=True,
        SMS_PROVIDER="africas_talking",
        AFRICAS_TALKING_USERNAME="sandbox",
        AFRICAS_TALKING_API_KEY="sandbox-key-12345",
        AFRICAS_TALKING_ENVIRONMENT="sandbox",
        AFRICAS_TALKING_USE_SANDBOX=True,
        SMS_USE_SANDBOX="",
    )
    def test_command_outputs_masked_json_summary(self) -> None:
        stdout = StringIO()

        call_command("check_sms_config", "--format=json", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn('"valid": true', output)
        self.assertIn('"environment": "sandbox"', output)
        self.assertIn('"username": "sandbox"', output)
        self.assertIn('"api_key_loaded": true', output)
        self.assertIn('"api_key_masked": "san', output)
        self.assertNotIn("sandbox-key-12345", output)

    @override_settings(
        SMS_ENABLED=True,
        SMS_PROVIDER="celcom",
        CELCOM_PARTNER_ID="36",
        CELCOM_API_KEY="celcom-key-12345",
        CELCOM_SHORTCODE="TEXTME",
    )
    def test_command_outputs_masked_celcom_json_summary(self) -> None:
        stdout = StringIO()

        call_command("check_sms_config", "--format=json", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn('"provider": "celcom"', output)
        self.assertIn('"partner_id": "36"', output)
        self.assertIn('"shortcode_configured": true', output)
        self.assertIn('"api_key_masked": "cel', output)
        self.assertNotIn("celcom-key-12345", output)


@override_settings(
    SMS_ENABLED=True,
    SMS_PROVIDER="celcom",
    CELCOM_PARTNER_ID="36",
    CELCOM_API_KEY="test-key",
    CELCOM_SHORTCODE="TEXTME",
)
class CelcomProviderTests(TestCase):
    def test_provider_maps_successful_response(self) -> None:
        provider = CelcomSMSProvider()
        response_body = (
            b'{"responses":[{"respose-code":200,"response-description":"Success","mobile":254712345678,"messageid":8290842,"networkid":"1"}]}'
        )

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return response_body

        with patch("apps.integrations.sms.celcom.request.urlopen", return_value=FakeResponse()):
            result = provider.send_sms(to="+254712345678", message="Hello from WorkNest")

        self.assertEqual(result["provider"], "celcom")
        self.assertEqual(result["message_id"], "8290842")
        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["recipient"], "254712345678")

    @override_settings(
        SMS_PROVIDER="celcom",
        CELCOM_PARTNER_ID="36",
        CELCOM_API_KEY="test-key",
        CELCOM_SHORTCODE="",
    )
    def test_provider_rejects_missing_shortcode(self) -> None:
        with self.assertRaisesMessage(SMSConfigurationError, "Missing required Celcom settings: CELCOM_SHORTCODE."):
            CelcomSMSProvider()
