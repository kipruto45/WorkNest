from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class RegisterThrottle(AnonRateThrottle):
    scope = "auth_register"
    rate = "5/hour"


class LoginThrottle(AnonRateThrottle):
    scope = "auth_login"
    rate = "10/hour"


class PasswordResetThrottle(AnonRateThrottle):
    scope = "auth_password_reset"
    rate = "5/hour"


class PhoneVerificationThrottle(UserRateThrottle):
    scope = "auth_phone_verification"


class AdminSMSBroadcastThrottle(UserRateThrottle):
    scope = "admin_sms_broadcast"
