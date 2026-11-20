from rest_framework import serializers
from datetime import date
from .models import User, Client, Project,Project_Status,Project_Type, ProjectAttachement, Profile, ProjectTask, Task_Status, TaskComment

USER_FIELDS= [
    'id','username','email','first_name','last_name',
    'profile','date_of_birth','gender','nationality','image',
    'blood_group','phone','country','permanent_address','current_address',
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
        unknown_fields = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown_fields:
            raise serializers.ValidationError({field: "This field does not exist."for field in unknown_fields})
        
        required_fields= ['email','profile']

        for field in required_fields:
            value= attrs.get(field)
            if value is None or not str(value).strip():
                raise serializers.ValidationError({field: f"{field} is required."})
        profile= attrs.get('profile')      #client model m same email h ya nhi check krta h
        if profile.role and profile.role.lower() == "client":
            if Client.objects.filter(email__iexact=attrs['email']).exists():
                raise serializers.ValidationError({"email": "A client with this email already exists."})
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
        unknown_fields = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown_fields:
            raise serializers.ValidationError({field: "This field does not exist."for field in unknown_fields})
        
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
        unknown_fields = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown_fields:
            raise serializers.ValidationError({field: "This field does not exist."for field in unknown_fields})
        
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
        if not value:
            return value
        value = value.lower()
        clients= Client.objects.filter(email__iexact=value)
        if self.instance:
            clients= clients.exclude(pk= self.instance.pk)
        if clients.exists():
            raise serializers.ValidationError("A client with this  email already exists.")
        return value

    def validate(self,attrs):
        unknown_fields = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown_fields:
            raise serializers.ValidationError({field: "This field does not exist."for field in unknown_fields})
        
        if self.instance is None:
            required_fields= ["first_name", "last_name","email"]
        else:
            required_fields= ["first_name", "last_name"]

        for field in required_fields:
            if self.partial and field not in attrs:
                continue
            value= attrs.get(field)
            if not value or not str(value).strip():
                raise serializers.ValidationError({field: f"{field} is required."})
        if self.instance is not None and "email" in attrs:
            if attrs["email"] != (self.instance.email or "").lower():
                raise serializers.ValidationError({"email": "Email cannot be updated."})
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


# Project Type Serializer
class ProjectTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project_Type
        fields = ['id', 'project_type', 'is_default']
        read_only_fields = ['id', 'is_default']

    def validate_project_type(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Project type is required.")
        project_types = Project_Type.objects.filter( project_type__iexact=value)

        if self.instance:
            project_types = project_types.exclude(pk=self.instance.pk)
        if project_types.exists():
            raise serializers.ValidationError("This project type already exists.")
        return value

    def validate(self, attrs):
        unknown_fields = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown_fields:
            raise serializers.ValidationError({field: "This field does not exist."for field in unknown_fields})
        return attrs

# Project Status Serializer
class ProjectStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project_Status
        fields = ['id', 'project_status', 'is_default']
        read_only_fields = ['id', 'is_default']

    def validate_project_status(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Project status is required.")

        project_statuses = Project_Status.objects.filter(project_status__iexact=value)
        if self.instance:
            project_statuses = project_statuses.exclude(pk=self.instance.pk)
        if project_statuses.exists():
            raise serializers.ValidationError("This project status already exists.")
        return value

    def validate(self, attrs):
        unknown_fields = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown_fields:
            raise serializers.ValidationError({field: "This field does not exist."for field in unknown_fields})
        return attrs


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
    user_client = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
        error_messages={
            "does_not_exist": "User client does not exist.",
            "incorrect_type": "User client must be a valid ID."
        }
    )
    project_type = serializers.PrimaryKeyRelatedField(
        queryset=Project_Type.objects.all(),
        required=False,
        allow_null=True,
        error_messages={"does_not_exist": "Project type does not exist.", "incorrect_type": "Project type must be a valid ID.","null":"Project Type is required."}
    )
    project_status = serializers.PrimaryKeyRelatedField(
        queryset=Project_Status.objects.all(),
        required=False,
        allow_null=True,
        error_messages={ "does_not_exist": "Project status does not exist.", "incorrect_type": "Project status must be a valid ID.","null":"Project Status is required."}
    )
    created_by = serializers.SerializerMethodField()
    modified_by = serializers.SerializerMethodField()
    attachements= serializers.SerializerMethodField()
    
    class Meta:
        model= Project
        fields=[
            'id','project_title','project_type','project_status',
            'description','attachements','start_date','date_of_completion','client','user_client',
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

    def validate(self,attrs):
        unknown_fields = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown_fields:
            raise serializers.ValidationError({field: "This field does not exist."for field in unknown_fields})
        
        required_fields= ['project_title','project_type','project_status','manager']
        for field in required_fields:
            if self.partial and field not in attrs:
                continue
            value= attrs.get(field)
            if value is None:
                raise serializers.ValidationError({field: f'{field} is required.'})
            if field == 'project_title' and not value.strip():
                raise serializers.ValidationError({field: f'{field} is required.'})
        
        client = attrs.get('client')
        user_client = attrs.get('user_client')

        if self.instance:
            if 'client' not in attrs:
                client = self.instance.client

            if 'user_client' not in attrs:
                user_client = self.instance.user_client

        if (client is not None and user_client is not None):
            raise serializers.ValidationError({"client": "Select either Client model ID or User model ID, not both."})

        if client is not None and client.status != 'active':
            raise serializers.ValidationError({'client': 'Client is not active.'})

        if user_client is not None:
            if user_client.status != 'active':
                raise serializers.ValidationError({'user_client': ' client is not active.'})

            if (
                user_client.profile is None or
                user_client.profile.role.lower() != "client"
            ):
                raise serializers.ValidationError({'user_client': 'Only a user with Client role can be assigned.'})

        manager= attrs.get('manager')
        if manager is not None and manager.status != 'active':
            raise serializers.ValidationError({'manager': 'manager is not active.'})

        if manager is not None and (manager.profile is None or manager.profile.role.lower() != "manager"):
            raise serializers.ValidationError({"manager": "only a user with Manager role can be assigned."})

        end= attrs.get('date_of_completion')
        if end:
            start= (
                self.instance.start_date 
                if self.instance and self.instance.start_date 
                else date.today())
            if end < start:
                raise serializers.ValidationError({'date_of_completion': 'date_of_completion cannot be before start_date.'})
        return attrs
    
    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.client:
            data['client'] = {
                "id": instance.client.id,
                "first_name": instance.client.first_name,
                "last_name": instance.client.last_name,
                "email": instance.client.email,
            }
        else:
            data['client'] = None

        if instance.user_client:
            data['user_client'] = {
                "id": instance.user_client.id,
                "first_name": instance.user_client.first_name,
                "last_name": instance.user_client.last_name,
                "email": instance.user_client.email,
                "profile": instance.user_client.profile.role
            }
        else:
            data['user_client'] = None

        if instance.manager:
            data['manager'] = {
                "id": instance.manager.id,
                "first_name": instance.manager.first_name,
                "last_name": instance.manager.last_name,
                "email": instance.manager.email,
                "profile": instance.manager.profile.role 
                
            }
        else:
            data['manager'] = None

        if instance.project_type:
            data['project_type'] = {
                'id': instance.project_type.id,
                'project_type': instance.project_type.project_type,
                'is_default': instance.project_type.is_default
            }
        else:
            data['project_type'] = None

        if instance.project_status:
            data['project_status'] = {
                'id': instance.project_status.id,
                'project_status': instance.project_status.project_status,
                'is_default': instance.project_status.is_default
            }
        else:
            data['project_status'] = None

        return data
    
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
class ProjectAttachementSerializer(serializers.ModelSerializer):
    class Meta:
        model= ProjectAttachement
        fields=['id','file','file_name']
        read_only_fields=['id','file_name']
    
    def validate(self, attrs):
        unknown_fields = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown_fields:
            raise serializers.ValidationError({field: "This field does not exist."for field in unknown_fields})
        
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

# Task Status Serializer
class TaskStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task_Status
        fields = ['id', 'status', 'is_default']
        read_only_fields = ['id', 'is_default']

    def validate_status(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Task status is required.")
        task_statuses = Task_Status.objects.filter(status__iexact=value)
        
        if self.instance:
            task_statuses = task_statuses.exclude(pk=self.instance.pk)
        if task_statuses.exists():
            raise serializers.ValidationError( "This task status already exists.")
        return value

    def validate(self, attrs):
        unknown_fields = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown_fields:
            raise serializers.ValidationError({field: "This field does not exist."for field in unknown_fields})
        return attrs


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
    task_status = serializers.PrimaryKeyRelatedField(
        queryset=Task_Status.objects.all(),
        required=False,
        allow_null=True,
        error_messages={
            "does_not_exist": "Task status does not exist.",
            "incorrect_type": "Task status must be a valid ID.",
            "null": "Task Status is required."}
    )
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
                'project_type': {
                    'id': project.project_type.id,
                    'project_type': project.project_type.project_type,
                    'is_default': project.project_type.is_default
                }if project.project_type else None,
                'project_status': {
                    'id': project.project_status.id,
                    'project_status': project.project_status.project_status,
                    'is_default': project.project_status.is_default
                } if project.project_status else None,
                'start_date': project.start_date,
                'date_of_completion': project.date_of_completion,              
            }
            task_status = instance.task_status
            if task_status is None:
                data['task_status'] = None
            else:
                data['task_status'] = {
                    'id': task_status.id,
                    'status': task_status.status,
                    'is_default': task_status.is_default
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
        unknown_fields = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown_fields:
            raise serializers.ValidationError({field: "This field does not exist."for field in unknown_fields})
        
        required_fields = ['project', 'assign_by', 'assign_to', 'title','task_status']
        for field in required_fields:
            if self.partial and field not in attrs:
                continue

            value = attrs.get(field)
            if value is None:
                raise serializers.ValidationError({field: f"{field} is required."})

            if field == 'title' and not value.strip():
                raise serializers.ValidationError({field: "title is required."})
            
        assign_by = attrs.get('assign_by',self.instance.assign_by if self.instance else None)
        if assign_by is not None:
            if assign_by.status != 'active':
                raise serializers.ValidationError({'assign_by': 'Assign by user is not active.'})

            if (assign_by.profile is None or assign_by.profile.role.lower() not in ['manager', 'team leader']):
                raise serializers.ValidationError({'assign_by': 'Only Manager or Team Leader can assign a task.'})
     
        assign_to = attrs.get('assign_to',self.instance.assign_to if self.instance else None)
        if assign_to is not None and assign_to.status != 'active':
            raise serializers.ValidationError({ 'assign_to': 'Assign to user is not active.'})        

        task_start_date = (self.instance.task_start_date if self.instance else date.today())
        task_complete_date = attrs.get('task_complete_date', self.instance.task_complete_date if self.instance else None)

        if (task_complete_date is not None and task_complete_date < task_start_date):
            raise serializers.ValidationError({'task_complete_date':'task_complete_date cannot be before task_start_date.'})
        return attrs

# Task Comment
class TaskCommentSerializer(serializers.ModelSerializer):
    project_task = serializers.PrimaryKeyRelatedField(
        queryset=ProjectTask.objects.filter(is_deleted=False),
        source='task',
        write_only=True,
        required=True,
        error_messages={
            "does_not_exist": "Project task does not exist.",
            "incorrect_type": "Project task must be a valid ID."
        }
    )
    class Meta:
        model = TaskComment
        fields = ['id','project_task', 'user', 'comment']
        read_only_fields = ['id', 'user']

    def validate(self,attrs):
        unknown_fields = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown_fields:
            raise serializers.ValidationError({field: "This field does not exist."for field in unknown_fields})
        
        comment= attrs.get('comment')
        if comment is None or not comment.strip():
            raise serializers.ValidationError({'comment': 'comment is required.'})
        
        if 'task' not in attrs:
            raise serializers.ValidationError({'project_task': 'project_task is required.'})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        task = instance.task

        if task is None:
            data['project_task'] = None
        else:
            project = task.project
            task_status = task.task_status

            data['project_task'] = {
                'id': task.id,
                'title': task.title,
                'project': {
                    'id': project.id,
                    'project_title': project.project_title
                } if project else None
            }

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

