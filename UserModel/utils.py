import hashlib
import hmac
import secrets
# import logging
from datetime import datetime, timedelta


from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import User
# logger= logging.getLogger(__name__)
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

def _hash(user_id,purpose,code):
    msg= f"{user_id}: {purpose}:{code}".encode()
    return hmac.new(
        settings.SECRET_KEY.encode(),
        msg,
        hashlib.sha256,
    ).hexdigest()



# def send_otp(user,purpose):
#     now= timezone.now()
#     # window= timedelta(hours=OTP_LIMIT_WINDOW_HOURS)
#     # blocked= False

#     if purpose not in (VERIFY, PASSWORD_RESET):
#         raise ValidationError("Invalid OTP purpose.")

#     rate_limit_key= f"otp_rate_limit:{user.pk}"
#     otp_key= f"otp:{purpose}:{user.pk}"

#     rate_limit= cache.get(rate_limit_key)
#     if rate_limit is None or now>= rate_limit["reset_at"]:
#         rate_limit={
#             "count":0,
#             "reset_at": now+ timedelta(hours= settings.OTP_LIMIT_HOURS),}

#     if rate_limit["count"]>=OTP_REQUEST_LIMIT:
#         retry_time= timezone.localtime(rate_limit["reset_at"]).strftime("%d %b %y, %I:%M:%P")
#         raise ValidationError({
#             "detail":(
#                 f"{OTP_LIMIT_MESSAGE }\n you can request a new OTP after{retry_time}."
#             ) 
#         })

#     code= generate_code()

#     ttl= settings.OTP_EXPIRY_MINUTES*60
#     subject=("Your verification code" if purpose== VERIFY else "your password reset code")

#     _mail(
#         user, 
#         subject,
#         f"Your OTP is {code}."
#         f"It expires in {settings.OTP_EXPIRY_MINUTES} minutes.",
#     )

#     cache.set(
#         otp_key,{
#             "hash": _hash(user.pk,purpose, code),
#             "attempts":0,
#             "expires_at": now+ timedelta(seconds=ttl),
#         },
#         timeout=ttl,
#     )
#     rate_limit["count"]+=1
#     remaining_time= max(
#         1, int((rate_limit["reset_at"]-now).total_seconds())+1,
#     )
#     cache.set(
#         rate_limit_key,rate_limit, timeout=remaining_time,
#     )

# def verif_otp(user,code,purpose):
#     now= timezone.now()

#     if purpose not in (VERIFY, PASSWORD_RESET):
#         raise ValidationError("Invalid otp purpose.")

#     otp_key= f"otp:{purpose}:{user.pk}"
#     data= cache.get(otp_key)

#     if data is None or now>= data["expires_at"]:
#         raise ValidationError("OTP has expired. Please request new one.")

#     if data["attempts"] >=settings.OTP_MAX_ATTEMPTS:
#         raise ValidationError("Too many incorrect attempts. Request a new OTP.")

#     entered_hash= _hash(user.pk, purpose, code)
#     if not hmac.compare_digest(data["hash"], entered_hash):
#         data["attempts"] +=1
#         remaining_time= max(1, int((data["expires_at"]-now).total_seconds()),)
#         cache.set(otp_key,data, timeout=remaining_time,)
#         raise ValidationError("Invalid OTP.")
    
#     cache.delete(otp_key)



def send_otp(user,purpose):

    if purpose not in (VERIFY, PASSWORD_RESET):
        raise ValidationError("OTP is valid for OTP verification or password reset.")
    now= timezone.now()
    window= timedelta(hours=OTP_LIMIT_WINDOW_HOURS)
    # blocked= False

    with transaction.atomic():
        locked= User.objects.select_for_update().get(pk=user.pk)

        request_timestamps=[]

        for timestamp in (locked.otp_request_timestamps or []):
            timestamp = datetime.fromisoformat(timestamp)

            if timezone.is_naive(timestamp):
                timestamp = timezone.make_aware(timestamp)

            if timestamp >= now - window:
                request_timestamps.append(timestamp.isoformat())

        
        if len(request_timestamps) >= OTP_REQUEST_LIMIT:

            earliest_request = datetime.fromisoformat(request_timestamps[0])
            retry_time = earliest_request + window
            retry_time = timezone.localtime(retry_time).strftime("%d %b %Y, %H:%M")
            raise ValidationError({
                "detail": (
                    f"{OTP_LIMIT_MESSAGE} "
                    f"You can request a new OTP after {retry_time}."
                )
            })

        code = generate_code()
        otp_data = {
            "hash": _hash(locked.pk, purpose, code),
            "purpose": purpose,
            "created_at": now.isoformat(),
        }

        subject = (
            "Your verification code"
            if purpose == VERIFY
            else "Your password reset code"
        )

        _mail(
            locked,
            subject,
            f"Your OTP is {code}. "
            f"It expires in {settings.OTP_EXPIRY_MINUTES} minutes.",
        )

        request_timestamps.append(now.isoformat())

        locked.otp_code = otp_data
        locked.otp_request_timestamps = request_timestamps

        locked.save(
            update_fields=[
                "otp_code",
                "otp_request_timestamps",
            ]
        )

        cache.set(
            f"otp_attempts:{locked.pk}",
            0,
            timeout=settings.OTP_EXPIRY_MINUTES * 60,
        )


# NEW: OTP clear karne ke liye
def _clear_otp(user):
    user.otp_code = {}
    user.save(update_fields=["otp_code"])
    cache.delete(f"otp_attempts:{user.pk}")


def verify_otp(user, code, purpose):

    if purpose not in (VERIFY, PASSWORD_RESET):
        raise ValidationError("OTP is valid for OTP verification and to reset password.")

    with transaction.atomic():
        locked = User.objects.select_for_update().get(pk=user.pk)
        otp_data = locked.otp_code

        if (
            not isinstance(otp_data, dict)
            or not otp_data.get("hash")
            or otp_data.get("purpose") != purpose
        ):
            raise ValidationError(
                "No active OTP. Please request a new one."
            )

        created_at = datetime.fromisoformat(otp_data["created_at"])
        if timezone.is_naive(created_at):
            created_at = timezone.make_aware(created_at)
        expires_at = created_at + timedelta(
            minutes=settings.OTP_EXPIRY_MINUTES
        )

        now = timezone.now()

        if now >= expires_at:
            _clear_otp(locked)
            raise ValidationError("OTP has expired. Please request a new one.")

        attempt_key = f"otp_attempts:{locked.pk}"
        attempts = cache.get(attempt_key, 0)

        if attempts >= settings.OTP_MAX_ATTEMPTS:
            _clear_otp(locked)

            raise ValidationError( "Maximum incorrect OTP attempts exceeded. Please request a new OTP.")

        entered_hash = _hash(locked.pk,purpose,code,)


        if not hmac.compare_digest(otp_data["hash"], entered_hash,):
            attempts += 1

            if attempts >= settings.OTP_MAX_ATTEMPTS:
                _clear_otp(locked)
                raise ValidationError(
                    "Maximum incorrect OTP attempts exceeded. This OTP is no longer valid. Please request a new OTP.")

            remaining_time = max(1,int((expires_at - now).total_seconds()),)

            cache.set(attempt_key, attempts, timeout=remaining_time,)
            raise ValidationError("Invalid OTP.")

        _clear_otp(locked)
