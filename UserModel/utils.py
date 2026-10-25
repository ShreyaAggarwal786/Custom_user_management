import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import User


logger= logging.getLogger(__name__)

VERIFY= "verify"
PASSWORD_RESET = "password_reset"

OTP_REQUEST_LIMIT= 3
OTP_LIMIT_WINDOW_HOURS= 12
OTP_LIMIT_MESSAGE= (
    "You have exceeded the maximum number of OTP requests. "
    "Please try again after 12 hours. "
)


def _mail(user, subject,body):
    send_mail(
        subject,
        f"Hi {user.first_name or user.username}, \n\n{body}",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently= False,
    )

def send_welcome_email(user):
    _mail(
        user,
        "Welcome to our platform",
        "Your account has been created successfully. \n\n Thank you for joining us.",
    )
def generate_code():
    return  f"{secrets.randbelow(1_000_000):06d}"


def send_otp(user,purpose):
    now= timezone.now()
    window= timedelta(hours=OTP_LIMIT_WINDOW_HOURS)
    blocked= False

    with transaction.atomic():
        locked= User.objects.select_for_update().get(pk=user.pk)

        if purpose== VERIFY:
            if locked.verify_blocked_until and now< locked.verify_blocked_until:
                blocked= True
            else:
                if(
                    locked.verify_blocked_until
                    or locked.verify_window_start is None
                    or now >= locked.verify_window_start + window
                ):
                    locked.verify_request_count=0
                    locked.verify_window_start= now
                    locked.verify_blocked_until= None

                if locked.verify_request_count>= OTP_REQUEST_LIMIT:
                    locked.verify_blocked_until = now+ window
                    locked.save()
                    blocked= True
                else:
                    locked.verify_request_count +=1

    if not blocked:
        locked.otp_code= generate_code()
        locked.otp_purpose= purpose
        locked.otp_expires_at= now+timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        locked.otp_attempts= 0
        locked.save()

        subject= (
            "Your verification code" if purpose == VERIFY
            else "Your password reset code"
        )
        _mail(
            locked,
            subject,
            f"Your OTP is{locked.otp_code}."
            f"It expires in{settings.OTP_EXPIRY_MINUTES}minutes.",
        )
        
    if blocked:
        retry_time= timezone.localtime(locked.verify_blocked_until).strftime(
            "%d %b %Y, %I:%M %p"
        )
        raise ValidationError({
            "detail": f"{OTP_LIMIT_MESSAGE} You can request a new OTP after {retry_time}."})

def _clear_otp(user):
    user.otp_code = None
    user.otp_purpose = None
    user.otp_expires_at = None
    user.otp_attempts = 0
    user.save(update_fields=["otp_code", "otp_purpose", "otp_expires_at", "otp_attempts"])
        
def verify_otp(user,code,purpose):
    if not user.otp_code or user.otp_purpose !=purpose:
        raise ValidationError("No active OTP. Please request a new one.")
    if user.otp_expires_at is None or timezone.now() >= user.otp_expires_at:
        raise ValidationError("OTP has expired.Request a new one.")
    if user.otp_attempts>= settings.OTP_MAX_ATTEMPTS:
        raise ValidationError("Too many incorrect attempts. Request a new OTP.")

    if not secrets.compare_digest(user.otp_code, code):
        user.otp_attempts +=1
        user.save(update_fields= ["otp_attempts"])
        raise ValidationError("Invalid OTP.")


    _clear_otp(user)