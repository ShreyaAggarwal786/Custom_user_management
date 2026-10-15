
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import User
from .serializers import(
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

from .emails import send_welcome_email
import logging

logger= logging.getLogger(__name__)

class UserViewSet(viewsets.ModelViewSet):
    queryset= User.objects.all().order_by('id')
    permission_classes=[AllowAny]

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
        user.status= User,Status.INACTIVE
        user.save(update_fields=['status'])
        return Response(
            {"detail": "User deactivated"}, status=status.HTTP_200_OK
        )





# Create your views here.
