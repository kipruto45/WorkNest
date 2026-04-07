from rest_framework.throttling import AnonRateThrottle


class RegisterThrottle(AnonRateThrottle):
    scope = "auth_register"
    rate = "5/hour"


class LoginThrottle(AnonRateThrottle):
    scope = "auth_login"
    rate = "10/hour"


class PasswordResetThrottle(AnonRateThrottle):
    scope = "auth_password_reset"
    rate = "5/hour"
