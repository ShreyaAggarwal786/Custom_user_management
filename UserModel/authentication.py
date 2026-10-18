from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import User


class ActiveStatusJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if user.status == User.Status.INACTIVE:
            raise AuthenticationFailed("User account is inactive.", code="user_inactive")
        return user