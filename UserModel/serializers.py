from rest_framework import serializers

from .models import User, Client, Project, ProjectAttachement, Profile

USER_FIELDS= [
    'id','username','email','first_name','last_name',
    'profile','date_of_birth','gender','nationality','image',
    'blood_group','phone','permanent_address','current_address',
    'emergency_contact_name','emergency_contact_number',
    'emergency_contact_relationship','status'
]


class UserCreateSerializer(serializers.ModelSerializer):
    email= serializers.EmailField()
    password= serializers.CharField(write_only=True, required= False)
    profile= serializers.CharField(required=False, allow_null=True, allow_blank= True)

    class Meta:
        model= User
        fields= USER_FIELDS+ ['password']
        read_only_fields= ['id','status']

    def validate_email(self, value):
        value=value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_profile(self,value):
        if not value:
            return None
        profile= None
        if value.isdigit():
            profile= Profile.objects.filter(pk= int(value)).first()
        if profile is None:
            profile= Profile.objects.filter(role__iexact=value).first()
        if profile is None:
            raise serializers.ValidationError("Profile does not exist.")
        return profile

    def validate(self, attrs):
        required_fields= ['email','profile']

        for field in required_fields:
            value= attrs.get(field)
            if value is None or not str(value).strip():
                raise serializers.ValidationError({field: f"{field} is required."})
        return attrs

    def create(self,validated_data):
        password= validated_data.pop("password", None)
        if not password:
            password= validated_data['email'].split("@")[0]+"@123"

            
        user= User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserSerializer(serializers.ModelSerializer):
    profile= serializers.SerializerMethodField()
    class Meta:
        model=User
        fields= USER_FIELDS
        read_only_fields= USER_FIELDS

    def get_profile(self,obj):
        if obj.profile is None:
            return None
        return {"id":obj.profile.id, 
                "role": obj.profile.role}
    

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model= User
        fields= USER_FIELDS
        read_only_fields= ['id','status']


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
        if "profile" in attrs and attrs["profile"] is None:
            raise serializers.ValidationError({"profile":"profile cannot be empty."})
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
    new_password = serializers.CharField(write_only=True, min_length=8)


#profile
class ProfileSerializer(serializers.ModelSerializer):
    users= serializers.SerializerMethodField()

    class Meta:
        model= Profile
        fields=['id','role','is_default','users']
        read_only_fields=['id','is_default']
    def get_users(self,obj):
        result=[]
        for user in obj.users.all():
            result.append({"id": user.id, "email": user.email})
        return result
    def validate_role(self,value):
        if value is None or not value.strip():
            raise serializers.ValidationError("role is required.")
        value= value.strip()

        profiles= Profile.objects.filter(role__iexact=value)
        if self.instance:
            profiles= profiles.exclude(pk= self.instance.pk)
            if self.instance.is_default and value != self.instance.role:
                raise serializers.ValidationError("Default profile role cannot be changed.")
        if profiles.exists():
            raise serializers.ValidationError("A profile with this role already exist.")
        return value

    def validate(self,attrs):
        if not self.partial and "role" not in attrs:
            raise serializers.ValidationError({"role":"role is required."})
        return attrs

    

class ClientSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    modified_by = serializers.SerializerMethodField()

    class Meta:
        model= Client
        fields=[
            'id','first_name',
            'last_name','email','contact_number',
            'country','address','status','created_by',
            'created_at','modified_by','modified_at'
        ]
        read_only_fields=[
            'id', 'status', 'created_by', 'created_at', 'modified_by', 'modified_at'    
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
        required_fields= ["first_name", "last_name","email"]

        for field in required_fields:
            if self.partial and field not in attrs:
                continue
            value= attrs.get(field)
            if not value or not str(value).strip():
                raise serializers.ValidationError({field: f"{field} is required."})
        return attrs
    def get_created_by(self, obj):
        if obj.created_by is None:
            return None
        return {"id": obj.created_by.id, "first_name": obj.created_by.first_name, "last_name": obj.created_by.last_name, "email": obj.created_by.email}

    def get_modified_by(self, obj):
        if obj.modified_by is None:
            return None
        u= obj.modified_by
        return {"id": u.id, "first_name": u.first_name, "last_name": u.last_name, "email": u.email}




    
#project 

class ProjectSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    modified_by = serializers.SerializerMethodField()
    attachements= serializers.SerializerMethodField()
    # total_attachements= serializers.ReadOnlyField()
    # attachement_list= serializers.ReadOnlyField()
    class Meta:
        model= Project
        fields=[
            'id','project_title','project_type','project_status',
            'description','attachements','date_of_completion','client',
            'manager','created_by','created_at','modified_by','modified_at'
        ]

        read_only_fields=['id','created_by','created_at','modified_by','modified_at']

    
    def validate(self,attrs):
        if self.instance and self.instance.project_status == "Inactive":
            new_status = attrs.get("project_status")

        if new_status is not None and new_status != "Inactive":
            raise serializers.ValidationError({
                "project_status": "Project is inactive. Use restore API."
            })

        required_fields= ['project_title','project_type','manager']
        for field in required_fields:
            if self.partial and field not in attrs:
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
    
    def get_created_by(self, obj):
        if obj.created_by is None:
            return None
        return {"id": obj.created_by.id, "first_name": obj.created_by.first_name, "last_name": obj.created_by.last_name, "email": obj.created_by.email}

    def get_modified_by(self, obj):
        if obj.modified_by is None:
            return None        
        u= obj.modified_by
        return {"id": u.id, "first_name": u.first_name, "last_name": u.last_name, "email": u.email}

    def get_attachements(self, obj):
        if obj.project_status == "Inactive":
            return[]
        items= obj.projectattachement_set.all()
        return ProjectAttachementSerializer(items,many= True, context=self.context).data
        


#Project Attachement
    
# ALLOWED_Extensions= (".pdf",".doc",".docx",".xls",".xlsx",".png",".jpg",".txt",".zip")
# Max_FILE_SIZE= 5*1024*1024

class ProjectAttachementSerializer(serializers.ModelSerializer):
    # created_by = serializers.SerializerMethodField()
    # modified_by = serializers.SerializerMethodField()

    class Meta:
        model= ProjectAttachement
        fields=['id','file','file_name']
        read_only_fields=['id','file_name']
    
    def validate(self, attrs):
        required_fields= ['file']
        for field in required_fields:
            if self.partial and field not in attrs:
                continue
            if not attrs.get(field):
                raise serializers.ValidationError({field: f"{field} is required."})
        return attrs

    # def validate_file(self, value):
            
        #     if not value.name.lower():
        #         raise serializers.ValidationError("This file type is not allowed.")
        #     if len(value.name)>255:
        #         raise serializers.ValidationError("File name is too long.")
        #     if value.size == 0:
        #          raise serializers.ValidationError("File is empty.")
        #     if value.size > Max_FILE_SIZE:
        #          raise serializers.ValidationError("File size cannot be more than 5 MB.")
        #     return value

    # def get_created_by(self, obj):
    #     if obj.created_by is None:
    #         return None
    #     return {"id": obj.created_by.id, "first_name": obj.created_by.first_name, "last_name": obj.created_by.last_name, "email": obj.created_by.email}

    # def get_modified_by(self, obj):
    #     if obj.modified_by is None:
    #         return None       
    #     u= obj.modified_by
    #     return {"id": u.id, "first_name": u.first_name, "last_name": u.last_name, "email": u.email}
        
    
#Restore
class RestoreSerializer(serializers.Serializer):
    model= serializers.ChoiceField(
        choices= [
            ('user', 'User'),
            ('client', 'Client'),
            ('project','Project')
        ]
    ) 
    id= serializers.IntegerField(min_value=1)


    



