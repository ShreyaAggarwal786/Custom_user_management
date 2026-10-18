from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User

PROFILE_FIELDS= [
    'first_name','last_name','profiles','date_of_birth','gender',
    'nationality','image','blood_group','phone',
    'permanent_address','current_address',
    'emergency_contact_name','emergency_contact_number',
    'emergency_contact_relationship',
]

class UserCreateSerializer(serializers.ModelSerializer):
    password= serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password=serializers.CharField(write_only=True)

    class Meta:
        model= User
        fields= ['id','username','email','password','confirm_password',
                'status']+ PROFILE_FIELDS
        read_only_fields= ['id','status','profiles']

    def validate_email(self, value):
        value=value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this  email already exists.")
        return value

    def validate(self,attrs):
        if attrs['password']!= attrs['confirm_password']:
            raise serializers.ValidationError(
                {"confirm_password":"passwords do not match."}
            )
        return attrs

    def create(self,validated_data):
        validated_data.pop("confirm_password")
        return User.objects.create_user(**validated_data)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields=['id','username','email','status']+ PROFILE_FIELDS
        read_only_fields= fields

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model= User
        fields= ['id','username','email','status']+PROFILE_FIELDS
        read_only_fields= ['id','status']


    def validate_email(self,value):
        value=value.lower()
        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("A user with email already exists.")
        return value

    def validate_profiles(self, value):
        user = self.context["request"].user
        is_admin = user.is_superuser or user.profiles == User.Profile.ADMINISTRATOR
        if value != self.instance.profiles and not is_admin:
            raise serializers.ValidationError("Only an administrator can change profiles.")
        return value

    
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()   
    password = serializers.CharField(write_only=True)


class SendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return attrs




