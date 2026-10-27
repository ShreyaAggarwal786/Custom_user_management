from django.urls import  path

from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ForgotPasswordView,
    ResetPasswordView,
    SendOTPView,
    UserDetailView,
    UserListCreateView,
    VerifyOTPView,
    LoginView,
    ClientListCreateView,
    ClientDetailView,
    ProjectListCreateView,
    ProjectDetailView,
    
    )



urlpatterns= [
    path("users/",UserListCreateView.as_view()),
    path("users/<int:id>/", UserDetailView.as_view()),
    path("auth/login/", LoginView.as_view()),
    path("auth/send-otp/", SendOTPView.as_view()),
    path("auth/verify-otp/", VerifyOTPView.as_view()),
    path("auth/forgot-password/", ForgotPasswordView.as_view()),
    path("auth/reset-password/", ResetPasswordView.as_view()),
    path("auth/token/refresh/", TokenRefreshView.as_view()),
    path("client/",ClientListCreateView.as_view()),
    path("client/<int:id>/",ClientDetailView.as_view()),
    path("project/",ProjectListCreateView.as_view()),
    path("project/<int:id>/",ProjectDetailView.as_view()),
    # path("project-types/",ProjectTypeListView.as_view()),

]