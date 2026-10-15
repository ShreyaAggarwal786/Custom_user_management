from django.conf import settings
from django.core.mail import send_mail

def send_welcome_email(user):
    subject= "welcome to our platform"
    message= (
        f"hii {user.first_name or user.username},\n\n"
        "Your account has been created successfully.\n\n"
        "Thank you for joining us."
    )
    send_mail(
        subject,
        message, 
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently= False
    )
    