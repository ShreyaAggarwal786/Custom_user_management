from rest_framework import serializers

from .models import User, Client, Project

USER_FIELDS= [
    'id','username','email','first_name','last_name',
    'profiles','date_of_birth','gender','nationality','image',
    'blood_group','phone','permanent_address','current_address',
    'emergency_contact_name','emergency_contact_number',
    'emergency_contact_relationship','status'
]


class UserCreateSerializer(serializers.ModelSerializer):
    email= serializers.EmailField()
    password= serializers.CharField(write_only=True, required= False)

    class Meta:
        model= User
        fields= USER_FIELDS+ ['password']
        read_only_fields= ['id','status']

    def validate_email(self, value):
        value=value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self,validated_data):
        password= validated_data.pop("password", None)
        if not password:
            password= validated_data['email'].split("@")[0]+"@123"
        user= User(**validated_data)
        user.set_password(password)
        user.save()
        return user

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
        if "email" in attrs and not attrs["email"] :
            raise serializers.ValidationError({"email": "email cannot be empty."})
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
    new_password = serializers.CharField(write_only=True)





class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model= Client
        fields=[
            'id','first_name',
            'last_name','email','contact_number',
            'country','address','status','created_by',
            'created_at','modified_by','modified_at'
        ]
        read_only_fields=[
            'id', 'created_by', 'created_at', 'modified_by', 'modified_at'    
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



    
#project 

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model= Project
        fields=[
            'id','project_title','project_type',
            'project_status','date_of_completion','client',
            'manager','created_by','created_at','modified_by','modified_at'
        ]

        read_only_fields=['id','created_by','created_at','modified_by','modified_at']

    # def validate_project_type(self,value):
    #     if not value:
    #         return value
    #     value= value.strip()
    #     for option, _label in Project.Project_Type:
    #         if value.casefold()== option.casefold():
    #             return option
    #     return value
    
    def validate(self,attrs):
        required_fields= ['project_title','project_type','client','manager']
        for field in required_fields:
            if self.instance is not None and field not in attrs:
                continue
            value= attrs.get(field)
            if value is None:
                raise serializers.ValidationError({field: f'{field} is required.'})
            if field in ['project_title','project_type'] and not value.strip():
                raise serializers.ValidationError({field: f'{field} is required.'})
        client= attrs.get('client')
        if client is not None and client.status != 'active':
            raise serializers.ValidationError({'client': 'client is not active.'})

        manager= attrs.get('manager')
        if manager is not None and manager.status != 'active':
            raise serializers.ValidationError({'manager': 'manager is not active.'})

        return attrs



