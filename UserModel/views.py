import logging

from rest_framework.views  import APIView
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from .permissions import IsSelfOrAdmin
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken


from .emails import send_otp_email, send_welcome_email
from .models import  OTP, User
from .otp_utils import OTPService
from .serializers import(
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    SendOTPSerializer,
    VerifyOTPSerializer,
    LoginSerializer,
)






logger= logging.getLogger(__name__)

class UserViewSet(viewsets.ModelViewSet):
    queryset= User.objects.all().order_by('id')



    def get_serializer_class(self):
        if self.action== "create":
            return UserCreateSerializer
        if self.action in ("update","partial_update"):
            return UserUpdateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        user= serializer.save()
        try:
            send_welcome_email(user)
        except Exception:
            logger.exception("welcome email failed for user id=%s", user.pk)

    def destroy(self, request, *args, **kwargs):
        user= self.get_object()
        user.status= User.Status.INACTIVE
        user.save(update_fields=['status'])
        return Response(
            {"detail": "User deactivated"}, status=status.HTTP_200_OK
        )

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        if self.action in ("update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsSelfOrAdmin()]
        return [IsAuthenticated()]


class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
        if user is None:
            return Response(
                {"detail": "No such user exists."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.status == User.Status.INACTIVE:
            return Response(
                {"detail": "This account is inactive."},
                status=status.HTTP_403_FORBIDDEN,
            )

        otp = OTPService.create(user, OTP.Purpose.VERIFY)

        try:
            send_otp_email(user, otp)
        except Exception:
            logger.exception("OTP email failed for user id=%s", user.pk)
            return Response(
                {"detail": "Could not send OTP email. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {"detail": "OTP sent to your email."},
            # status=status.HTTP_200_OK,
        )

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(
            email__iexact=serializer.validated_data["email"]
        ).first()
        if user is None:
            return Response(
                {"detail": "No such user exists."},
                status=status.HTTP_404_NOT_FOUND,
            )

        OTPService.verify(user, serializer.validated_data["otp"], OTP.Purpose.VERIFY)
        return Response({"detail": "OTP verified successfully."})

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(
            email__iexact=serializer.validated_data["email"]
        ).first()
        if user is None:
            return Response(
                {"detail": "No such user exists."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if user.status == User.Status.INACTIVE:
            return Response(
                {"detail": "This account is inactive."},
                status=status.HTTP_403_FORBIDDEN,
            )

        otp = OTPService.create(user, OTP.Purpose.PASSWORD_RESET)

        try:
            send_otp_email(user, otp)
        except Exception:
            logger.exception("Reset OTP email failed for user id=%s", user.pk)
            return Response(
                {"detail": "Could not send OTP email. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({"detail": "Password reset OTP sent to your email."})


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = User.objects.filter(email__iexact=data["email"]).first()
        if user is None:
            return Response(
                {"detail": "No such user exists."},
                status=status.HTTP_404_NOT_FOUND,
            )

        OTPService.verify(user, data["otp"], OTP.Purpose.PASSWORD_RESET)

        user.set_password(data["new_password"])
        user.save(update_fields=["password"])

        return Response({"detail": "Password reset successfully."})  


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = User.objects.filter(email__iexact=data["email"]).first()
          # DEBUG (baad mein delete karna)
        
        if user is None or not user.check_password(data["password"]):
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if user.status == User.Status.INACTIVE:
            return Response(
                {"detail": "This account is inactive."},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            }
        )
