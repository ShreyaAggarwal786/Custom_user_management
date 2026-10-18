from rest_framework.permissions import BasePermission

from .models import User


class IsSelfOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        return (
            obj.pk == user.pk
            or user.is_superuser
            or user.profiles == User.Profile.ADMINISTRATOR
        )