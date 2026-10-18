import secrets

from django.conf import settings
from rest_framework import serializers

from .models import OTP


class OTPService:
    """Handles creating and verifying OTPs."""

    @staticmethod
    def create(user, purpose):
        # Invalidate older unused codes so only the newest works
        OTP.objects.filter(
            user=user, purpose=purpose, is_used=False
        ).update(is_used=True)
        return OTP.objects.create(user=user, purpose=purpose)

    @classmethod
    def verify(cls, user, code, purpose):
        otp = cls._get_active_otp(user, purpose)
        cls._check_expiry_and_attempts(otp)

        if not secrets.compare_digest(
            otp.code.encode(), str(code).encode()
        ):
            otp.attempts += 1
            otp.save(update_fields=["attempts"])
            raise serializers.ValidationError("Incorrect OTP.")

        otp.is_used = True
        otp.save(update_fields=["is_used"])
        return otp

    @staticmethod
    def _get_active_otp(user, purpose):
        otp = (
            OTP.objects.filter(user=user, purpose=purpose, is_used=False)
            .order_by("-created_at")
            .first()
        )
        if otp is None:
            raise serializers.ValidationError(
                "No active OTP. Please request a new one."
            )
        return otp

    @staticmethod
    def _check_expiry_and_attempts(otp):
        if otp.is_expired():
            raise serializers.ValidationError(
                "OTP has expired. Please request a new one."
            )
        if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
            raise serializers.ValidationError(
                "Too many incorrect attempts. Please request a new OTP."
            )