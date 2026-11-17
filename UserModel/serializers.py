from rest_framework import serializers
from datetime import date
from .models import User, Client, Project, ProjectAttachement, Profile, ProjectTask, TaskComment

USER_FIELDS= [
    'id','username','email','first_name','last_name',
    'profile','date_of_birth','gender','nationality','image',
    'blood_group','phone','permanent_address','current_address',
    'emergency_contact_name','emergency_contact_number',
    'emergency_contact_relationship','status','created_by','created_at','modified_by','modified_at'
]


class UserCreateSerializer(serializers.ModelSerializer):
    email= serializers.EmailField()
    password= serializers.CharField(write_only=True, required= False)
    profile= serializers.CharField(required=False, allow_null=True, allow_blank= True)

    class Meta:
        model= User
        fields= USER_FIELDS+ ['password']
        read_only_fields= ['id','status','created_by','modified_by','created_at','modified_at']

    def validate_email(self, value):
        value=value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        if value and User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
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
    created_by= serializers.SerializerMethodField() 
    modified_by= serializers.SerializerMethodField() 
    class Meta:
        model=User
        fields= USER_FIELDS
        read_only_fields= USER_FIELDS

    def get_profile(self,obj):
        if obj.profile is None:
            return None
        return {"id":obj.profile.id, 
                "role": obj.profile.role}

    def get_created_by(self, obj):
        user= obj.created_by
        if user is None:
            return None
        profile= None
        if user.profile:
            profile={
                "id": user.profile.id,
                "role":user.profile.role
            }
        return {
            "id":user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "profile":profile
        }
    def get_modified_by(self, obj):
        user= obj.modified_by
        if user is None:
            return None
        profile= None
        if user.profile:
            profile={
                "id": user.profile.id,
                "role":user.profile.role
            }
        return {
            "id":user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "profile":profile
        }
    
    

class UserUpdateSerializer(serializers.ModelSerializer):

    profile = serializers.PrimaryKeyRelatedField(
        queryset=Profile.objects.all(),
        required=False,
        allow_null=True,
        error_messages={
            "does_not_exist": "Invalid profile ID. Please provide a valid profile.",
            "incorrect_type": "Profile ID must be a valid integer."
        }
    )
    class Meta:
        model= User
        fields= USER_FIELDS
        read_only_fields= ['id','status','created_by','created_at','modified_by','modified_at']


    def validate_email(self,value):
        if not value:
            return value
        value=value.lower()
        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        if "username" in self.initial_data:
            raise serializers.ValidationError({"username": "Username cannot be updated."})
        if "email" in self.initial_data:
            raise serializers.ValidationError({"detail": "Email cannot be updated."})
        if "status" in self.initial_data:
            raise serializers.ValidationError({"status": "Status cannot be updated."})
        if "email" in attrs and not attrs["email"] :
            raise serializers.ValidationError({"email": "email cannot be empty."})
        if "profile" in attrs and attrs["profile"] is None:
            raise serializers.ValidationError({"profile":"profile cannot be empty."})
        return attrs

#profile
class ProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model= Profile
        fields=['id','role','is_default']
        read_only_fields=['id','is_default']

    def validate_role(self,value):
        if value is None or not value.strip():
            raise serializers.ValidationError("role is required.")
        value= value.strip()       

        role_name = value.replace(" ", "")
        if not role_name.isascii() or not role_name.isalpha():
            raise serializers.ValidationError("Role must contain only letters.")

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
        profile= None
        if obj.created_by.profile is not None:
            profile= {"id": obj.created_by.profile.id, "role": obj.created_by.profile.role}
        return {"id": obj.created_by.id, "first_name": obj.created_by.first_name, "last_name": obj.created_by.last_name, "email": obj.created_by.email,"profile":profile}


    def get_modified_by(self, obj):
        u= obj.modified_by
        if u is None:
            return None
        profile= None
        if u.profile is not None:
            profile= {"id": u.profile.id, "role": u.profile.role}
        
        return {"id": u.id, "first_name": u.first_name, "last_name": u.last_name, "email": u.email,"profile": profile}





    
#project 

class ProjectSerializer(serializers.ModelSerializer):
    manager= serializers.PrimaryKeyRelatedField(
        queryset= User.objects.all(), required= False, allow_null=True,
        error_messages={"does_not_exist": "Manager does not exist.", "incorrect_type": "Manager must be a valid id."}
    )
    client= serializers.PrimaryKeyRelatedField(
        queryset= Client.objects.all(), required= False, allow_null=True,
        error_messages={"does_not_exist": "client does not exist.", "incorrect_type": "client must be a valid id."}
    )
    created_by = serializers.SerializerMethodField()
    modified_by = serializers.SerializerMethodField()
    attachements= serializers.SerializerMethodField()
    
    class Meta:
        model= Project
        fields=[
            'id','project_title','project_type','project_status',
            'description','attachements','start_date','date_of_completion','client',
            'manager','is_deleted','created_by','created_at','modified_by','modified_at'
        ]
        read_only_fields=['id','start_date','is_deleted','created_by','created_at','modified_by','modified_at']

    def validate_project_title(self, value):
        if value and value.strip():
            projects= Project.objects.filter(project_title__iexact=value.strip())
            if self.instance:
                projects= projects.exclude(pk= self.instance.pk)
            if projects.exists():
                raise serializers.ValidationError("A project with this title already exists.")
        return value
    
    def to_representation(self, instance):
        data= super().to_representation(instance)

        manager= instance.manager
        if manager is None:
            data["manager"]= None
        else:
            data["manager"]= {
                "id": manager.id,
                "username": manager.username,
                "first_name": manager.first_name,
                "last_name": manager.last_name,
                "email": manager.email,
                "profile_id": manager.profile_id,          
            }

        client= instance.client
        if client is None:
            data["client"]= None
        else:
            data["client"]= {
                "id": client.id,
                "first_name": client.first_name,
                "last_name": client.last_name,
                "email": client.email,
            }
        return data

    def validate(self,attrs):
        
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

        if manager is not None and (manager.profile is None or manager.profile.role.lower() != "manager"):
            raise serializers.ValidationError({"manager": "only a user with Manager role can be assigned."})

                # NAYA: date_of_completion start_date se pehle nahi ho sakti
        end= attrs.get('date_of_completion')
        if end:
            from datetime import date
            start= self.instance.start_date if self.instance and self.instance.start_date else date.today()
            if end < start:
                raise serializers.ValidationError({'date_of_completion': 'date_of_completion cannot be before start_date.'})

        return attrs
    
    def get_created_by(self, obj):
        if obj.created_by is None:
            return None
        profile= None
        if obj.created_by.profile is not None:
            profile= {"id": obj.created_by.profile.id, "role": obj.created_by.profile.role}
        return {"id": obj.created_by.id, "first_name": obj.created_by.first_name, "last_name": obj.created_by.last_name, "email": obj.created_by.email,"profile":profile}
    
    def get_modified_by(self, obj):
        u= obj.modified_by
        if u is None:
            return None        
        profile= None
        if u.profile is not None:
            profile={"id": u.profile.id, "role": u.profile.role}

        return {"id": u.id, "first_name": u.first_name, "last_name": u.last_name, "email": u.email, "profile":profile}

    def get_attachements(self, obj):
        if obj.is_deleted:
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
            f= attrs.get("file")
            project=self.context.get("project")
            names= self.context.get("names")
            if f is not None:
                if (project and ProjectAttachement.objects.filter(project=project, file_name=f.name).exists()) or (names is not None and f.name in names):
                    raise serializers.ValidationError({"file": f"Attachement '{f.name}' already exists in this project."})
                if names is not None:
                    names.append(f.name)
        return attrs

    
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


# Project Task
class ProjectTaskSerializer(serializers.ModelSerializer):
    assign_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
        error_messages={
            "does_not_exist": "Assign by user does not exist.",
            "incorrect_type": "Assign by must be a valid id."
        })
    assign_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
        error_messages={
            "does_not_exist": "Assign to user does not exist.",
            "incorrect_type": "Assign to must be a valid id."
        })

    comments = serializers.SerializerMethodField()

    class Meta:
        model = ProjectTask
        fields = [
            'id', 'project', 'assign_by', 'assign_to',
            'title', 'description', 'task_status',
            'is_deleted', 'task_start_date',
            'task_complete_date', 'comments',
            'created_at', 'created_by',
            'modified_at', 'modified_by'
        ]

        read_only_fields = [
            'id', 'task_start_date', 'is_deleted',
            'created_at', 'created_by',
            'modified_at', 'modified_by'
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        project = instance.project
        if project is None:
            data['project'] = None
        else:
            data['project'] = {
                'id': project.id,
                'project_title': project.project_title,
                'project_type': project.project_type,
                'project_status': project.project_status,
                'start_date': project.start_date,
                'date_of_completion': project.date_of_completion,
            }
        
        for field in ['assign_by', 'assign_to', 'created_by', 'modified_by']:
            u = getattr(instance, field)
            if u is None:
                data[field] = None
            else:
                profile = None
                if u.profile is not None:
                    profile = {'id': u.profile.id, 'role': u.profile.role}
                data[field] = {
                    'id': u.id,
                    'email': u.email,
                    'first_name': u.first_name,
                    'last_name': u.last_name,
                    'profile': profile,
                }
        return data

    def get_comments(self, obj):
        if obj.is_deleted:
            return []
        comments = obj.comments.all()
        return TaskCommentSerializer(comments, many=True, context=self.context).data

    def validate(self, attrs):
        required_fields = ['project', 'assign_by', 'assign_to', 'title']

        for field in required_fields:
            if self.partial and field not in attrs:
                continue
            value = attrs.get(field)

            if value is None:
                raise serializers.ValidationError({field: f"{field} is required."})

            if field == 'title' and not value.strip():
                raise serializers.ValidationError({field: "title is required."})

        
        assign_by = attrs.get(
            'assign_by',
            self.instance.assign_by if self.instance else None
        )

        if assign_by is not None:
            if assign_by.status != 'active':
                raise serializers.ValidationError({'assign_by': 'Assign by user is not active.'})

            if (assign_by.profile is None or assign_by.profile.role.lower() not in ['manager', 'team leader']):
                raise serializers.ValidationError({'assign_by': 'Only Manager or Team Leader can assign a task.'})

        
        assign_to = attrs.get(
            'assign_to',
            self.instance.assign_to if self.instance else None)

        if assign_to is not None and assign_to.status != 'active':
            raise serializers.ValidationError({ 'assign_to': 'Assign to user is not active.'})        
        # from datetime import date

        task_start_date = (self.instance.task_start_date if self.instance else date.today())

        task_complete_date = attrs.get('task_complete_date', self.instance.task_complete_date if self.instance else None)

        if (task_complete_date is not None and task_complete_date < task_start_date):
            raise serializers.ValidationError({'task_complete_date':'task_complete_date cannot be before task_start_date.'})

        return attrs

# Task Comment
class TaskCommentSerializer(serializers.ModelSerializer):

    class Meta:
        model = TaskComment
        fields = ['id', 'user', 'comment']
        read_only_fields = ['id', 'user']

    def validate(self,attrs):
        comment= attrs.get('comment')
        if comment is None or not comment.strip():
            raise serializers.ValidationError({'comment': 'comment is required.'})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = instance.user
        if user is None:
            data['user'] = None
        else:
            data['user'] = {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email
            }

        return data

