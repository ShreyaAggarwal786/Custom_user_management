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
    ProfileListCreateView,
    ProfileDetailView,
    UserRestoreView,
    ClientRestoreView,
    ProjectRestoreView,
    ProjectTaskListCreateView,
    ProjectTaskDetailView,
    TaskCommentCreateView,
    TaskCommentDeleteView,
    ProjectTaskRestoreView,
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
    path("profile/", ProfileListCreateView.as_view()),
    path("profile/<int:id>/", ProfileDetailView.as_view()),
    path("users/restore/", UserRestoreView.as_view()),
    path("users/<int:id>/restore/", UserRestoreView.as_view()),
    path("client/restore/", ClientRestoreView.as_view()),
    path("client/<int:id>/restore/", ClientRestoreView.as_view()),
    path("project/restore/",ProjectRestoreView.as_view()),
    path("project/<int:id>/restore/",ProjectRestoreView.as_view()),
    path("tasks/", ProjectTaskListCreateView.as_view()),
    path("tasks/<int:id>/", ProjectTaskDetailView.as_view()),
    path("tasks/<int:id>/comments/", TaskCommentCreateView.as_view()),
    path("tasks/<int:id>/comments/<int:comment_id>/",TaskCommentDeleteView.as_view()),
    path("tasks/<int:id>/restore/", ProjectTaskRestoreView.as_view()),

]