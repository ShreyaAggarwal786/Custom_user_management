import logging

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.mail import send_mail
from rest_framework.views  import APIView
from rest_framework import status, serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.pagination import PageNumberPagination

from .models import  OTP, User, Client
from .serializers import(
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    SendOTPSerializer,
    VerifyOTPSerializer,
    LoginSerializer,
    ClientSerializer,
)



logger= logging.getLogger(__name__)

class Pagination(PageNumberPagination):
    page_size=2
    page_size_query_param= "page_size"
    max_page_size=10


def send_welcome_email(user,otp):
    if otp.purpose== OTP.Purpose.PASSWORD_RESET:
        subject="password reset OTP"
        reason="Reason your password"
    else:
        subject="Your Verification OTP"
        reason="Verify your account"

    send_mail(
        subject,
        f"Hi {user.first_name or user.username},\n\n"
        f"Use this OTP to {reason}: {otp.code}\n\n"
        f"It expires in {settings.OTP_EXPIRY_MINUTES} minutes. "
        "If you did not request this, you can ignore this email.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

def create_otp(user,purpose):
    OTP.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)
    return OTP.objects.create(user=user, purpose=purpose)


def verify_otp(user, code,purpose):
    otp=(
        OTP.objects.filter(user=user,purpose=purpose,is_used=False)
        .order_by("-id").first()
    )
    if otp is None or otp.is_expired():
        raise serializers.ValidationError("OTP not found or expired. Request a new one.")
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise serializers.ValidationError("Too many wrong attempts. Request a new OTP.")
    if otp.code != str(code):
        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        raise serializers.ValidationError("Incorrect OTP.")

    otp.is_used = True
    otp.save(update_fields=["is_used"])



class UserListCreateView(APIView):
    permission_classes=[AllowAny]

    def get_permissions(self):
        if self.request.method=="POST":
            return[AllowAny()]
        return [AllowAny()]

    def get(self,request):
        users=User.objects.all().order_by('id')
        paginator= Pagination()
        page= paginator.paginate_queryset(users, request,view=self)
        serializer= UserSerializer(
            page,  many=True, context={"request":request}
            )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer= UserCreateSerializer(
            data= request.data, context={"request":request}
        )
        serializer.is_valid(raise_exception=True)
        user= serializer.save()

        try:
            send_welcome_email(user)
        except Exception:
            logger.exception("welcome email failed for user id=%s", user.pk)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    permission_classes=[AllowAny]


    def get_object(self,pk):
        return get_object_or_404(User, pk=pk)

    def get(self,request,pk):
        user= self.get_object(pk)
        serializer= UserSerializer(user, context={"request": request})
        return Response(serializer.data)

    def put(self,request,pk):
        return self._update(request,pk,partial=False)

    def patch(self,request,pk):
        return self._update(request,pk,partial=True)

    def _update(self, request, pk, partial):
        user= self.get_object(pk)
        serializer= UserUpdateSerializer(
            user, data=request.data, partial=partial, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self,request, pk):
        user= self.get_object(pk)
        user.status =User.Status.INACTIVE
        user.save(update_fields=["status"])
        return Response({"detail": "User Deactivated"}, status= status.HTTP_200_OK)
    

#OTP
class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
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

        otp = create_otp(user, OTP.Purpose.VERIFY)

        try:
            send_mail(user, otp)
        except Exception:
            logger.exception("OTP email failed for user id=%s", user.pk)
            return Response(
                {"detail": "Could not send OTP email. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {"detail": "OTP sent to your email."},
            status=status.HTTP_200_OK,
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

        verify_otp(user, serializer.validated_data["otp"], OTP.Purpose.VERIFY)
        return Response({"detail": "OTP verified successfully."})

#Forgot/ Reset password

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

        otp = create_otp(user, OTP.Purpose.PASSWORD_RESET)

        try:
            send_mail(user, otp)
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

        verify_otp(user, data["otp"], OTP.Purpose.PASSWORD_RESET)

        user.set_password(data["new_password"])
        user.save(update_fields=["password"])

        return Response({"detail": "Password reset successfully."})  

#Login

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = User.objects.filter(email__iexact=data["email"]).first()
        
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
                "user": UserSerializer(user,context={"request": request}).data,
            }
        )



#CLIENTS

class ClientListCreateView(APIView):
    permission_classes=[IsAuthenticated]

    def get(self,request):
        clients= Client.objects.select_related("created_by","modified_by")
        paginator= Pagination()
        page= paginator.paginate_queryset(clients, request, view= self)
        serializer= ClientSerializer(
            page, many=True, context={"request":request}
        )
        return paginator.get_paginated_response(serializer.data)

    def post(self,request):
        serializer= ClientSerializer(data= request.data, context={"request":request})
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by= request.user, modified_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ClientDetailView(APIView):
    permission_classes=[IsAuthenticated]

    def get_object(self,pk):
        return get_object_or_404(Client,pk=pk)

    def get(self,request,pk):
        client=self.get_object(pk)
        serializer= ClientSerializer(client, context= {"request": request})
        return Response(serializer.data)

    def put(self,request,pk):
        return self._update(request, pk, partial=False)

    def patch(self, request,pk):
        return self._update(request, pk, partial=True)

    def _update(self, request,pk,partial):
        client= self.get_object(pk)
        serializer= ClientSerializer(
            client, data= request.data, partial= partial,context={"request":request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(modified_by=request.user)
        return Response(serializer.data)

    def delete(self,request,pk):
        client=self.get_object(pk)
        client.status= Client.Status.INACTIVE
        client.modified_by= request.user
        client.save(update_fields=['status','modified_by','modified_at'])
        return Response({"detail": "Client Deactivated"},status= status.HTTP_200_OK)


    







