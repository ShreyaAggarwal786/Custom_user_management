import re
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from django.utils import timezone

from .models import User
from .models import Client

USER_FIELDS= [
    'id','username','email','first_name','last_name',
    'profiles','date_of_birth','gender','nationality','image',
    'blood_group','phone','permanent_address','current_address',
    'emergency_contact_name','emergency_contact_number',
    'emergency_contact_relationship','status'
]


class UserCreateSerializer(serializers.ModelSerializer):
    password= serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password=serializers.CharField(write_only=True)

    class Meta:
        model= User
        fields= USER_FIELDS+ ['password','confirm_password']
        read_only_fields= ['id','status','profiles']

    def validate_email(self, value):
        if not value:
            return value
        value=value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this  email already exists.")
        return value

    def validate(self,attrs):
        for field in ["username", "email"]:
            value=attrs.get(field)
            if not value or not str(value).strip():
                raise serializers.ValidationError({field: f"{field} is required."})
            
        if attrs['password']!= attrs['confirm_password']:
            raise serializers.ValidationError(
                {"confirm_password":"passwords do not match."}
            )
        return attrs

    def create(self,validated_data):
        validated_data.pop("confirm_password")
        self.password= self.validated_data.pop("password")
        user= User(**validated_data)
        user.set_password(self.password)
        user.save()
        return User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields= USER_FIELDS
        read_only_fields= USER_FIELDS

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model= User
        fields= USER_FIELDS
        read_only_fields= ['id']


    def validate_email(self,value):
        if not value:
            return value
        value=value.lower()
        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        for field in["username","email"]:
            if field in attrs and (not attrs[field] or not str(attrs[field]).strip()):
                raise serializers.ValidationError({field: f"{field} cannot be empty."})
        return attrs

    
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




class ClientSerializer(serializers.ModelSerializer):
    created_by= serializers.EmailField(source="created_by.email", read_only=True)
    modified_by= serializers.EmailField(source="modified_by.email", read_only=True)


    class Meta:
        model= Client
        fields=[
            'id','first_name',
            'last_name','email','contact_number',
            'country','address','status','created_by',
            'created_at','modified_by','modified_at'
        ]
        read_only_fields=[
            'id', 'created_at', 'modified_at'    
        ]
        
    def validate_email(self,value):
        value = value.lower()
        clients= Client.objects.filter(email__iexact=value)
        if self.instance:
            clients= clients.exclude(pk= self.instance.pk)
        if clients.exists():
            raise serializers.ValidationError("A client with this  email already exists.")
        return value

    def validate(self,attrs):
        required_fields= ["first_name", "last_name", "contact_number", "address", "country"]

        for field in required_fields:
            if self.instance is not None and field not in attrs:
                continue
            value= attrs.get(field)
            if not value or not str(value).strip():
                raise serializers.ValidationError({field: f"{field} is required."})
        return attrs



    


