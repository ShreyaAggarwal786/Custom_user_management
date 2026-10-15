from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User

PROFILE_FIELDS= [
    'first_name','last_name','profiles','date_of_birth','gender','nationality','image','blood_group','phone','permanent_address','current_address','emergency_contact_name','emergency_contact_number','emergency_contact_relationship'
]

class UserCreateSerializer(serializers.ModelSerializer):
    password= serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password=serializers.CharField(write_only=True)

    class Meta:
        model= User
        fields= ['id','username','email','password','confirm_password',
                'status']+ PROFILE_FIELDS
        read_only_fields= ['id','status']

    def validate_email(self, value):
        value=value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with email already exists.")
        return value

    def validate(self,attrs):
        if attrs['password']!= attrs['confirm_password']:
            raise serializers.ValidationError(
                {"confirm_password":"password does not match."}
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