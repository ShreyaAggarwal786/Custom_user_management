from django.conf import settings
from django.core.mail import send_mail


def send_welcome_email(user):
    subject = "Welcome to our platform"
    message = (
        f"Hi {user.first_name or user.username},\n\n"
        "Your account has been created successfully.\n\n"
        "Thank you for joining us."
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def send_otp_email(user, otp):
    if otp.purpose == "password_reset":
        subject = "Password reset OTP"
        reason = "reset your password"
    else:
        subject = "Your verification OTP"
        reason = "verify your account"

    message = (
        f"Hi {user.first_name or user.username},\n\n"
        f"Use this OTP to {reason}: {otp.code}\n\n"
        f"It expires in {settings.OTP_EXPIRY_MINUTES} minutes. "
        "If you did not request this, you can ignore this email."
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )