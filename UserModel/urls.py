from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ForgotPasswordView,
    ResetPasswordView,
    SendOTPView,
    UserViewSet,
    VerifyOTPView,
    LoginView,
    # TokenRefreshView,


    )

router= DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns= [
    path("", include(router.urls)),
    path("auth/login/", LoginView.as_view()),
    path("auth/send-otp/", SendOTPView.as_view()),
    path("auth/verify-otp/", VerifyOTPView.as_view()),
    path("auth/forgot-password/", ForgotPasswordView.as_view()),
    path("auth/reset-password/", ResetPasswordView.as_view()),
    path("auth/token/refresh/", TokenRefreshView.as_view()),
]