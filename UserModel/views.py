from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework.views  import APIView
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction
from django.db.models import Q
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.dateparse import parse_date
from .models import  User, Client, Project, ProjectAttachement, Profile, ProjectTask, TaskComment
from .serializers import(
    UserCreateSerializer,UserSerializer,UserUpdateSerializer,
    ForgotPasswordSerializer,ResetPasswordSerializer,
    SendOTPSerializer,VerifyOTPSerializer,LoginSerializer,
    ClientSerializer,ProjectSerializer,ProjectAttachementSerializer,
    ProfileSerializer, ProjectTaskSerializer,TaskCommentSerializer,
)

from .utils import(PASSWORD_RESET, VERIFY, send_otp, send_welcome_email, verify_otp,)


class Pagination(PageNumberPagination):
    page_size=10
    page_size_query_param= "page_size"
    max_page_size=100


class UserListCreateView(APIView):
    permission_classes=[AllowAny]

    def get(self,request):
        users=User.objects.order_by('id')

       
        search = request.query_params.get("search", "").strip()
        if search:
            for word in search.split():
                users = users.filter(
                    Q(username__icontains=word) |
                    Q(email__icontains=word) |
                    Q(first_name__icontains=word) |
                    Q(last_name__icontains=word) |
                    Q(phone__icontains=word) |
                    Q(profile__role__icontains=word)
                )
    # Individual filters
        first_name = request.query_params.get("first_name", "").strip()
        last_name = request.query_params.get("last_name", "").strip()
        email = request.query_params.get("email", "").strip()
        profile = request.query_params.get("profile", "").strip()
        phone = request.query_params.get("phone", "").strip()
        username = request.query_params.get("username", "").strip()
        gender = request.query_params.get("gender", "").strip()
        is_superuser = request.query_params.get("is_superuser", "").strip().lower()
        profile_id = request.query_params.get("profile_id", "").strip()
        role = request.query_params.get("role", "").strip()
        is_default = request.query_params.get("is_default", "").strip().lower()

        if first_name:
            users = users.filter(first_name__icontains=first_name)

        if last_name:
            users = users.filter(last_name__icontains=last_name)

        if email:
            users = users.filter(email__icontains=email)

        if profile:
            users = users.filter(profile__role__iexact=profile)

        if phone:
            users = users.filter(phone__icontains=phone)

        if username:
            users = users.filter(username__icontains=username)

        if gender:
            users = users.filter(gender__iexact=gender)

        if is_superuser:
            if is_superuser not in ["true", "false"]:
                return Response({"is_superuser": "Only true or false is allowed."},status=status.HTTP_400_BAD_REQUEST)
            users = users.filter(is_superuser=(is_superuser == "true"))

        if profile_id:
            if not profile_id.isdigit():
                return Response({"profile_id": "Enter a valid profile ID."},status=status.HTTP_400_BAD_REQUEST)
            users = users.filter(profile_id=int(profile_id))

        if role:
            users = users.filter(profile__role__iexact=role)

        if is_default:
            if is_default not in ["true", "false"]:
                return Response({"is_default": "Only true or false is allowed."},status=status.HTTP_400_BAD_REQUEST)
            users = users.filter(profile__is_default=(is_default == "true"))

        status_value= request.query_params.get("status","").strip()
        if status_value:                                                     # NAYA
            users= users.filter(status__iexact=status_value)
        else:
            users= users.exclude(status=User.Status.INACTIVE)

        paginator= Pagination()
        page= paginator.paginate_queryset(users, request,view=self)
        serializer= UserSerializer(
            page,  many=True, context={"request":request}
            )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer= UserCreateSerializer(data= request.data, context={"request":request})
        serializer.is_valid(raise_exception=True)
        user= serializer.save()

        try:
            send_welcome_email(user)
        except Exception:
            print("Welcome email failed")
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    permission_classes=[AllowAny]


    def get_object(self,id):
        return get_object_or_404(User, pk=id)

    def get(self,request,id):
        user= self.get_object(id)
        if user.status == User.Status.INACTIVE:
            return Response({"detail": "User is inactive."}, status=status.HTTP_400_BAD_REQUEST)
        serializer= UserSerializer(user, context={"request": request})
        return Response(serializer.data)

    def put(self,request,id):
        return self._update(request,id,partial=False)

    def patch(self,request,id):
        return self._update(request,id,partial=True)

    def _update(self, request, id, partial):
        user= self.get_object(id)
        serializer= UserUpdateSerializer(
            user, data=request.data, partial=partial, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user=serializer.save()
        return Response(UserSerializer(user, context={"request":request}).data)

    def delete(self,request, id):
        user= self.get_object(id)
        user.status =User.Status.INACTIVE
        user.save(update_fields=["status"])
        return Response({"detail": "User Deactivated"}, status= status.HTTP_200_OK)
    

#OTP
class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)


        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
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
        try:
            send_otp(user, VERIFY)
        except ValidationError:
            raise
        except Exception:
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

        verify_otp(user, serializer.validated_data["otp"],VERIFY) 
        return Response({"detail": "OTP verified successfully."})

#Forgot/ Reset password

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
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

        try:
            send_otp(user, PASSWORD_RESET)
        except ValidationError:
            raise
        except Exception:
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

        verify_otp(user, data["otp"], PASSWORD_RESET)

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


#profile
DEFAULT_PROFILES=[
    "Super Admin",
    "Admin",
    "Manager",
    "Team Leader",
    "Developer",
    "Human Resources",
]

class ProfileListCreateView(APIView):
    permission_classes=[AllowAny]

    def initial(self,request,*args, **kwargs):
        super().initial(request, *args, **kwargs)
        Profile.objects.exclude(role__in= DEFAULT_PROFILES).update(is_default=False)
        for role in DEFAULT_PROFILES:
            Profile.objects.update_or_create(role= role, defaults={"is_default":True})

    def get(self, request):
        value = request.query_params.get("profile", "").strip()

        if value:
            profile = None
            if value.isdigit():
                profile = Profile.objects.filter(pk=int(value)).first()
            if profile is None:
                profile = Profile.objects.filter(role__iexact=value).first()
            if profile is None:
                return Response({"profile": "Profile does not exist."},
                                status=status.HTTP_404_NOT_FOUND)

            users = (User.objects.filter(profile=profile)
                     .order_by("id").values("id", "email"))
            return Response(list(users))


        profiles= Profile.objects.all().order_by("id")

        profile_id = request.query_params.get("profile_id", "").strip()
        role = request.query_params.get("role", "").strip()
        is_default = request.query_params.get("is_default", "").strip().lower()

        if profile_id:
            if not profile_id.isdigit():
                return Response({"profile_id": "Enter a valid profile ID."},status=status.HTTP_400_BAD_REQUEST)
            profiles = profiles.filter(id=int(profile_id))

        if role:
            profiles = profiles.filter(role__icontains=role)

        if is_default:
            if is_default not in ["true", "false"]:
                return Response({"is_default": "Only true or false is allowed."},status=status.HTTP_400_BAD_REQUEST)
            profiles = profiles.filter(is_default=(is_default == "true"))

        paginator= Pagination()
        page= paginator.paginate_queryset(profiles, request, view=self)
        serializer= ProfileSerializer(page, many=True, context={"request":request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer= ProfileSerializer(data=request.data, context={"request":request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ProfileDetailView(APIView):
    permission_classes=[AllowAny]

    def get_object(self, id):
        return get_object_or_404(Profile, pk=id)

    def get(self, request, id):
        profile= self.get_object(id)
        serializer= ProfileSerializer(profile, context={"request":request})
        return Response(serializer.data)

    def put(self, request, id):
        return self._update(request, id, partial=False)

    def patch(self, request, id):
        return self._update(request, id, partial=True)

    def _update(self, request, id, partial):
        profile= self.get_object(id)
        if profile.is_default:
            return Response({"detail":"Default profile cannot be modified."}, status= status.HTTP_400_BAD_REQUEST)
        serializer= ProfileSerializer(profile, data=request.data, partial=partial, context={"request":request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, id):
        profile = Profile.objects.get(pk=id)

        if profile.is_default:
            return Response({"detail":"Default profile cannot be deleted."},status=status.HTTP_400_BAD_REQUEST)
        profile.delete()                         
        return Response({"detail": "Profile Deleted successfully"}, status=status.HTTP_200_OK)



#CLIENTS

class ClientListCreateView(APIView):
    permission_classes=[IsAuthenticated]

    def get(self,request):
        clients= Client.objects.select_related("created_by","modified_by")
        search= request.query_params.get("search", "").strip()
        if search:
            for word in search.split():
                clients= clients.filter(
                    Q(first_name__icontains=word) |
                    Q(last_name__icontains=word) |
                    Q(email__icontains=word) |
                    Q(contact_number__icontains=word) |
                    Q(country__icontains=word) |
                    Q(address__icontains=word)
                )

        # Individual filters
        client_id = request.query_params.get("client_id", "").strip()
        first_name= request.query_params.get("first_name", "").strip()
        last_name= request.query_params.get("last_name", "").strip()
        email= request.query_params.get("email", "").strip()
        contact_number= request.query_params.get("contact_number", "").strip()
        country= request.query_params.get("country", "").strip()
        address= request.query_params.get("address", "").strip()

        if client_id:
            if not client_id.isdigit():
                return Response({"client_id": "Enter a valid client ID."},status=status.HTTP_400_BAD_REQUEST)
            clients = clients.filter(id=int(client_id))
        if first_name:
            clients= clients.filter(first_name__icontains=first_name)
        if last_name:
            clients= clients.filter(last_name__icontains=last_name)
        if email:
            clients= clients.filter(email__icontains=email)
        if contact_number:
            clients= clients.filter(contact_number__icontains=contact_number)
        if country:
            clients= clients.filter(country__iexact=country)
        if address:
            clients= clients.filter(address__icontains=address)
        status_value= request.query_params.get("status","").strip()
        if status_value:                                                     # NAYA
            clients= clients.filter(status__iexact=status_value)
        else:
            clients= clients.exclude(status=Client.Status.INACTIVE)

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

    def get_object(self,id):
        return get_object_or_404(Client,pk=id)

    def get(self,request,id):
        client=self.get_object(id)
        if client.status == Client.Status.INACTIVE:                                # NAYA
            return Response({"detail": "Client is inactive."}, status=status.HTTP_400_BAD_REQUEST)
        serializer= ClientSerializer(client, context= {"request": request})
        return Response(serializer.data)

    def put(self,request,id):
        return self._update(request, id, partial=False)

    def patch(self, request,id):
        return self._update(request, id, partial=True)

    def _update(self, request,id,partial):
        client= self.get_object(id)
        serializer= ClientSerializer(
            client, data= request.data, partial= partial,context={"request":request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(modified_by=request.user)
        return Response(serializer.data)

    def delete(self,request,id):
        client=self.get_object(id)
        client.status= Client.Status.INACTIVE
        client.modified_by= request.user
        client.save(update_fields=['status','modified_by','modified_at'])
        return Response({"detail": "Client Deactivated"},status= status.HTTP_200_OK)


#project
#send client notification
def send_client_notification(project):
    client= project.client
    if not client or not client.email:
        return False
    
    manager= project.manager
    if manager is not None:
        manager_info= (
            f"Name: {manager.first_name} {manager.last_name}\n"
            f"email: {manager.email}\n"            
        )
    else:
        manager_info= "No manager assigned.\n"

    message= (
        f"Hello {client.first_name} {client.last_name or 'Client'},\n\n"
        f"A new project has been created for you.\n\n"
        f"Project Title: {project.project_title}\n"
        f"Status: {project.project_status}\n"
        f"Description: {project.description or 'Not Provided'}\n\n"
        f"Assigned Manager:\n"
        f"{manager_info}\n"
        f"Regards,\nTeam"
    )
    try:
        send_mail(
            subject=f"New Project Assigned: {project.project_title}",
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[project.client.email],
        )
    except Exception:
        print("Client email failed")


# send manager notification
def send_manager_notification(project):
    manager= project.manager
    if not manager or not manager.email:
        return False
    client = project.client
    if client is not None:
        client_info= (
            f"Name: {client.first_name} {client.last_name}\n"
            f"Email: {client.email}\n"
        )
    else:
        client_info= "No client assigned.\n"

    subject= f"New Project Assigned: {project.project_title}\n"

    message= (
        f"Hello {manager.first_name} {manager.last_name or "Manager"},\n\n"
        f"A new project has been assigned to you.\n\n"
        f"Project Title: {project.project_title}\n"
        f"Status: {project.project_status}\n"
        f"Description: {project.description or 'NOT Provided'}\n\n"
        f"Client Information:\n"
        f"{client_info}\n"
        f"Regards,\nTeam"
    )
    try:
        send_mail(
            subject=f"Project Assigned: {project.project_title}",
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[manager.email],
        )
    except Exception:
        print("Manager email failed")

class ProjectListCreateView(APIView):
    permission_classes=[IsAuthenticated]
    parser_classes= [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        projects= Project.objects.select_related(
            'client','manager','created_by','modified_by'
        ).order_by("-id")

        if request.query_params.get("is_deleted","").lower() == "true":
            projects= projects.filter(is_deleted=True)
        else:
            projects= projects.filter(is_deleted=False)

        search= request.query_params.get("search", "").strip()
        if search:
            for word in search.split():
                projects= projects.filter(
                    Q(project_title__icontains=word) |
                    Q(project_type__icontains=word) |
                    Q(description__icontains=word) |
                    Q(client__first_name__icontains=word) |
                    Q(client__last_name__icontains=word) |
                    Q(client__email__icontains=word) |
                    Q(manager__first_name__icontains=word) |
                    Q(manager__last_name__icontains=word) |
                    Q(manager__email__icontains=word)
                )

        # Individual filters
        project_id = request.query_params.get("project_id", "").strip()
        project_title= request.query_params.get("project_title", "").strip()
        project_type= request.query_params.get("project_type", "").strip()
        description= request.query_params.get("description", "").strip()
        project_status= request.query_params.get("project_status", "").strip()
        client= request.query_params.get("client", "").strip()
        client_id = request.query_params.get("client_id", "").strip()
        manager= request.query_params.get("manager", "").strip()
        manager_id = request.query_params.get("manager_id", "").strip()
        manager_profile_id = request.query_params.get("manager_profile_id", "").strip()
        start_date = request.query_params.get("start_date", "").strip()
        date_of_completion = request.query_params.get("date_of_completion", "").strip()

        if project_id:
            if not project_id.isdigit():
                return Response({"project_id": "Enter a valid project ID."},status=status.HTTP_400_BAD_REQUEST)
            projects = projects.filter(id=int(project_id))
        if project_title:
            projects= projects.filter(project_title__icontains=project_title)
        if project_type:
            projects= projects.filter(project_type__icontains=project_type)
        if description:
            projects= projects.filter(description__icontains=description)
        if project_status:
            projects= projects.filter(project_status__iexact=project_status)

        if client.isdigit():
            projects= projects.filter(client_id=int(client))        
        client_first_name = request.query_params.get("client_first_name")
        client_last_name = request.query_params.get("client_last_name")
        client_email = request.query_params.get("client_email")

        if client_id:
            if not client_id.isdigit():
                return Response({"client_id": "Enter a valid client ID."},status=status.HTTP_400_BAD_REQUEST)
            projects = projects.filter(client_id=int(client_id))
        if client_first_name:
            projects = projects.filter(client__first_name__icontains=client_first_name)
        if client_last_name:
            projects = projects.filter(client__last_name__icontains=client_last_name)
        if client_email:
            projects = projects.filter(client__email__icontains=client_email)


        if manager.isdigit():
            projects= projects.filter(manager_id=int(manager))
        manager_first_name = request.query_params.get("manager_first_name")
        manager_last_name = request.query_params.get("manager_last_name")
        manager_username = request.query_params.get("manager_username")
        manager_email = request.query_params.get("manager_email")

        if manager_id:
            if not manager_id.isdigit():
                return Response({"manager_id": "Enter a valid manager ID."},status=status.HTTP_400_BAD_REQUEST)
            projects = projects.filter(manager_id=int(manager_id))
        if manager_profile_id:
            if not manager_profile_id.isdigit():
                return Response({"manager_profile_id": "Enter a valid profile ID."}, status=status.HTTP_400_BAD_REQUEST)
            projects = projects.filter(manager__profile_id=int(manager_profile_id))
        if manager_first_name:
            projects = projects.filter(manager__first_name__icontains=manager_first_name)
        if manager_last_name:
            projects = projects.filter(manager__last_name__icontains=manager_last_name)
        if manager_username:
            projects = projects.filter(manager__username__icontains=manager_username)
        if manager_email:
            projects = projects.filter(manager__email__icontains=manager_email) 

        project_status= request.query_params.get("project_status","").strip()
        if project_status:                                                   # CHANGE
            projects= projects.filter(project_status__iexact=project_status)
        if start_date:
            date_value = parse_date(start_date)
            if date_value is None:
                return Response({"start_date": "Enter date in YYYY-MM-DD format."},status=status.HTTP_400_BAD_REQUEST)
            projects = projects.filter(start_date=date_value)

        if date_of_completion:
            date_value = parse_date(date_of_completion)
            if date_value is None:
                return Response({"date_of_completion": "Enter date in YYYY-MM-DD format."},status=status.HTTP_400_BAD_REQUEST)
            projects = projects.filter(date_of_completion=date_value)

        paginator= Pagination()
        page= paginator.paginate_queryset(projects, request, view=self)
        serializer= ProjectSerializer(
            page, many=True, context={"request":request}
        )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer= ProjectSerializer(data= request.data, context={"request":request})
        serializer.is_valid(raise_exception=True)

        file_serializers=[]
        names=[]
        for f in request.FILES.getlist("attachements"):
            file_serializer= ProjectAttachementSerializer(data={'file': f}, context={"request": request, "names":names})
            file_serializer.is_valid(raise_exception=True)
            file_serializers.append(file_serializer)

        with transaction.atomic():
            project= serializer.save(created_by= request.user, modified_by= request.user)
            for file_serializer in file_serializers:
                f= file_serializer.validated_data['file']
                file_serializer.save(project=project, file_name= f.name)

        if serializer.is_valid():
            transaction.on_commit(lambda: send_client_notification(project))
            transaction.on_commit(lambda: send_manager_notification(project))
        return Response(ProjectSerializer(project, context={"request": request}).data, status=status.HTTP_201_CREATED)

class ProjectDetailView(APIView):

    permission_classes=[IsAuthenticated]
    parser_classes=[MultiPartParser, FormParser, JSONParser]

    def get_object(self,id):
        return get_object_or_404(Project, pk=id)

    def get(self, request,id):
        project= self.get_object(id)
        if project.is_deleted == "True":
            return Response({"detail": "Project is deleted."},status= status.HTTP_400_BAD_REQUEST)
        serializer= ProjectSerializer(project, context={"request": request})
        return Response(serializer.data)

    def put(self, request,id):
        return self._update(request, id, partial= False)

    def patch(self, request,id):
            return self._update(request, id, partial= True)

    def post(self, request, id):
        project= self.get_object(id)

        if project.is_deleted:
            return Response({"detail": "Project is deleted."}, status=status.HTTP_400_BAD_REQUEST)

        file_serializers=[]
        names=[]
        for f in request.FILES.getlist("attachements"):
            file_serializer= ProjectAttachementSerializer(data= {"file":f}, context={"request": request, "project": project, "names":names}) 
            file_serializer.is_valid(raise_exception=True)
            file_serializers.append(file_serializer)

        if not file_serializers:
            return Response({"attachements":"At least one file is required."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            for file_serializer in file_serializers:
                f= file_serializer.validated_data["file"]
                file_serializer.save(project=project, file_name= f.name)
            project.modified_by= request.user
            project.save(update_fields= ['modified_by','modified_at'])
        return Response(ProjectSerializer(project, context={"request":request}).data, status= status.HTTP_201_CREATED)


    def _update(self, request, id, partial):
        project= self.get_object(id)
        if project.is_deleted:                               # CHANGE: deleted project update nahi hoga
            return Response({"detail": "Project is already deleted."}, status=status.HTTP_400_BAD_REQUEST)

        serializer= ProjectSerializer(project, data= request.data, partial= partial, context={"request":request})
        serializer.is_valid(raise_exception= True)

        files= request.FILES.getlist("attachements")
        file_serializers=[]
        names=[]
        for f in files:
            file_serializer= ProjectAttachementSerializer(data={"file":f}, context={"request": request,"project":project, "names":names})
            file_serializer.is_valid(raise_exception=True)
            file_serializers.append(file_serializer)

        with transaction.atomic():
            serializer.save(modified_by= request.user)            
            for file_serializer in file_serializers:
                f= file_serializer.validated_data["file"]
                file_serializer.save(project=project,file_name= f.name)        
        return Response(ProjectSerializer(project, context={"request":request}).data)

    def delete(self, request,id):
        project= self.get_object(id)
        if not isinstance(request.data, dict):
            return Response({"detail": "Invalid request body."}, status= status.HTTP_400_BAD_REQUEST)

        if "attachements_ids" in request.data:
            if project.is_deleted:
                return Response({"detail": "Project is already deleted."}, status=status.HTTP_400_BAD_REQUEST)

            if hasattr(request.data, "getlist"):
                raw_ids= request.data.getlist("attachements_ids")
            else:
                raw_ids= request.data.get("attachements_ids")
            if not isinstance(raw_ids, list) or not raw_ids:
                return Response({"attachement_ids": "attachement_ids must be a non-empty list. Example: {\"attachements_ids\":[1,2]}"}, status= status.HTTP_400_BAD_REQUEST)

            ids=[]
            for i in raw_ids:
                if isinstance(i, bool):
                    return Response({"attachement_ids": "only integer ids are allowed."}, status= status.HTTP_400_BAD_REQUEST)
                try:
                    ids.append(int(i))
                except(TypeError, ValueError):
                    return Response({"attachement_ids": "only integer ids are allowed."}, status=status.HTTP_400_BAD_REQUEST)
            ids= list(set(ids))

            attachements= list(ProjectAttachement.objects.filter(project=project, pk__in=ids))
            found_ids= [a.id for a in attachements]

            invalid_ids= sorted([i for i in ids if i not in found_ids])
            if invalid_ids:
                return Response(
                    {"attachement_ids": f"Invalid ids or not part of this project: {invalid_ids}. Nothing was deleted."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            files_to_remove=[]
            for a in attachements:
                if a.file:
                    files_to_remove.append((a.file.storage, a.file.name))

            with transaction.atomic():
                for a in attachements:
                    a.delete()                  

                project.modified_by= request.user
                project.save(update_fields=['modified_by','modified_at'])

            for storage, name in files_to_remove:
                storage.delete(name)           
            return Response(
                {"detail": f" Attachement(s) has been  deleted.", "deleted_ids": sorted(found_ids)},
                status=status.HTTP_200_OK,
            ) 
        if project.is_deleted:
            return Response({"detail": "Project is already deleted."},status=status.HTTP_200_OK)    
        project.is_deleted= True
        project.modified_by= request.user
        project.save(update_fields=['is_deleted','modified_by','modified_at'])
        return Response({"detail": "Project deleted successfully."}, status=status.HTTP_400_BAD_REQUEST)



# PROJECT TASK
class ProjectTaskListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        tasks = ProjectTask.objects.filter(
            is_deleted=False
        ).select_related(
            'project',
            'assign_by__profile',
            'assign_to__profile',
            'created_by__profile',
            'updated_by__profile'
        ).prefetch_related(
            'comments__user'
        )
        is_deleted = request.query_params.get("is_deleted", "false").strip().lower()
        if is_deleted not in ["true", "false"]:
            return Response(
                {"is_deleted": "Only true or false is allowed."},
                status=status.HTTP_400_BAD_REQUEST
            )
        tasks = tasks.filter(is_deleted=(is_deleted == "true"))

        search = request.query_params.get("search", "").strip()
        if search:
            for word in search.split():
                tasks = tasks.filter(
                    Q(title__icontains=word) |Q(description__icontains=word) |Q(project__project_title__icontains=word) |
                    Q(assign_by__first_name__icontains=word) |Q(assign_by__last_name__icontains=word) |Q(assign_by__email__icontains=word) |
                    Q(assign_to__first_name__icontains=word) |Q(assign_to__last_name__icontains=word) |Q(assign_to__email__icontains=word)
                )

        title = request.query_params.get("title", "").strip()
        project = request.query_params.get("project", "").strip()
        assign_by = request.query_params.get("assign_by", "").strip()
        assign_to = request.query_params.get("assign_to", "").strip()
        task_status = request.query_params.get("status", "").strip()

        if title:
            tasks = tasks.filter(title__icontains=title)

        if project:
            if not project.isdigit():
                return Response(
                    {"project": "Enter a valid project ID."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            tasks = tasks.filter(project_id=int(project))

        if assign_by:
            if not assign_by.isdigit():
                return Response(
                    {"assign_by": "Enter a valid user ID."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            tasks = tasks.filter(assign_by_id=int(assign_by))

        if assign_to:
            if not assign_to.isdigit():
                return Response(
                    {"assign_to": "Enter a valid user ID."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            tasks = tasks.filter(assign_to_id=int(assign_to))

        if task_status:
            tasks = tasks.filter(task_status__iexact=task_status)


        task_start_date = request.query_params.get("task_start_date", "").strip()
        task_complete_date = request.query_params.get("task_complete_date", "").strip()

        if task_start_date:
            date_value = parse_date(task_start_date)
            if date_value is None:
                return Response(
                    {"task_start_date": "Enter date in YYYY-MM-DD format."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            tasks = tasks.filter(task_start_date=date_value)

        if task_complete_date:
            date_value = parse_date(task_complete_date)
            if date_value is None:
                return Response(
                    {"task_complete_date": "Enter date in YYYY-MM-DD format."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            tasks = tasks.filter(task_complete_date=date_value)


        start_date_from = request.query_params.get("start_date_from", "").strip()
        start_date_to = request.query_params.get("start_date_to", "").strip()

        if start_date_from:
            date_value = parse_date(start_date_from)
            if date_value is None:
                return Response(
                    {"start_date_from": "Enter date in YYYY-MM-DD format."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            tasks = tasks.filter(task_start_date__gte=date_value)

        if start_date_to:
            date_value = parse_date(start_date_to)
            if date_value is None:
                return Response(
                    {"start_date_to": "Enter date in YYYY-MM-DD format."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            tasks = tasks.filter(task_start_date__lte=date_value)


        complete_date_from = request.query_params.get("complete_date_from", "").strip()
        complete_date_to = request.query_params.get("complete_date_to", "").strip()

        if complete_date_from:
            date_value = parse_date(complete_date_from)
            if date_value is None:
                return Response(
                    {"complete_date_from": "Enter date in YYYY-MM-DD format."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            tasks = tasks.filter(task_complete_date__gte=date_value)

        if complete_date_to:
            date_value = parse_date(complete_date_to)
            if date_value is None:
                return Response(
                    {"complete_date_to": "Enter date in YYYY-MM-DD format."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            tasks = tasks.filter(task_complete_date__lte=date_value)


        paginator = Pagination()
        page = paginator.paginate_queryset(tasks, request, view=self)
        serializer = ProjectTaskSerializer(page,many=True,context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ProjectTaskSerializer(data=request.data,context={"request": request})
        serializer.is_valid(raise_exception=True)

        task = serializer.save(created_by=request.user,updated_by=request.user)

        return Response(
            ProjectTaskSerializer(task,context={"request": request}).data,status=status.HTTP_201_CREATED)


class ProjectTaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, id):
        return get_object_or_404(ProjectTask, pk=id, is_deleted=False)

    def get(self, request, id):
        task = self.get_object(id)
        serializer = ProjectTaskSerializer(task,context={"request": request})
        return Response(serializer.data)

    def put(self, request, id):
        return self._update(request, id, partial=False)

    def patch(self, request, id):
        return self._update(request, id, partial=True)

    def _update(self, request, id, partial):
        task = self.get_object(id)
        serializer = ProjectTaskSerializer(task,data=request.data,partial=partial,context={"request": request})
        serializer.is_valid(raise_exception=True)
        task = serializer.save(updated_by=request.user)
        return Response(
            ProjectTaskSerializer(task,context={"request": request}).data)

    def delete(self, request, id):
        task = self.get_object(id)
        task.is_deleted = True
        task.updated_by = request.user

        task.save(
            update_fields=[
                'is_deleted',
                'updated_by',
                'updated_at'
            ])

        return Response({"detail": "Task deleted successfully."}, status=status.HTTP_200_OK)


# TASK COMMENT
class TaskCommentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        task = get_object_or_404(ProjectTask,pk=id)

        if task.is_deleted:
            return Response({"detail": "Cannot comment on a deleted task."},status=status.HTTP_400_BAD_REQUEST)

        if request.user not in [task.assign_by,task.assign_to]:
            return Response({"detail":"Only assigned users can comment on this task."},status=status.HTTP_403_FORBIDDEN)

        serializer = TaskCommentSerializer(data=request.data,context={"request": request})
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(task=task,user=request.user)

        return Response(TaskCommentSerializer(comment,context={"request": request}).data,status=status.HTTP_201_CREATED)


class TaskCommentDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id, comment_id):
        task = get_object_or_404(ProjectTask,pk=id,is_deleted=False)
        comment = get_object_or_404(TaskComment,pk=comment_id,task=task)

        if request.user not in [task.assign_by,task.assign_to]:
            return Response({"detail":"Only assigned users can delete comments."},status=status.HTTP_403_FORBIDDEN)
        comment.delete()
        return Response({"detail": "Comment deleted successfully."},status=status.HTTP_200_OK)



# USER RESTORE
class UserRestoreView(APIView):
    permission_classes=[AllowAny]

    def post(self, request, id=None):
        raw= request.query_params.get("ids","") + "," + str(request.data.get("ids","")).strip("[]")
        ids= {int(x) for x in raw.replace(" ","").split(",") if x.isdigit()}
        if id:
            ids.add(id)
        users= User.objects.filter(pk__in=ids, status=User.Status.INACTIVE)
        restored= list(users.values_list("id", flat=True))
        if not restored:
            return Response({"detail": "No inactive user found for given ids.", "skipped_ids": sorted(ids)}, status=status.HTTP_400_BAD_REQUEST)
        users.update(status=User.Status.ACTIVE)
        result= {"detail": f"{len(restored)} user(s) restored.", "restored_ids": sorted(restored)}
        skipped= sorted(ids - set(restored))
        if skipped:
            result["skipped_ids"]= skipped
        return Response(result)


# CLIENT RESTORE
class ClientRestoreView(APIView):
    permission_classes=[AllowAny]

    def post(self, request, id=None):
        raw= request.query_params.get("ids","") + "," + str(request.data.get("ids","")).strip("[]")
        ids= {int(x) for x in raw.replace(" ","").split(",") if x.isdigit()}
        if id:
            ids.add(id)
        clients= Client.objects.filter(pk__in=ids, status=Client.Status.INACTIVE)
        restored= list(clients.values_list("id", flat=True))
        if not restored:
            return Response({"detail": "No inactive client found for given ids.", "skipped_ids": sorted(ids)}, status=status.HTTP_400_BAD_REQUEST)
        data= {"status": Client.Status.ACTIVE, "modified_at": timezone.now()}
        if request.user.is_authenticated:                       # NAYA: login ho tabhi modified_by
            data["modified_by"]= request.user
        clients.update(**data)

        result= {"detail": f"{len(restored)} client(s) restored.", "restored_ids": sorted(restored)}
        skipped= sorted(ids - set(restored))
        if skipped:
            result["skipped_ids"]= skipped
        return Response(result)


# PROJECT RESTORE
class ProjectRestoreView(APIView):
    permission_classes=[AllowAny]

    def post(self, request, id=None):
        raw= request.query_params.get("ids","") + "," + str(request.data.get("ids","")).strip("[]")
        ids= {int(x) for x in raw.replace(" ","").split(",") if x.isdigit()}
        if id:
            ids.add(id)
        projects= Project.objects.filter(pk__in=ids, is_deleted=True)
        restored= list(projects.values_list("id", flat=True))
        if not restored:
            result= {"detail": "No deleted project found for given ids."}
            if ids:
                result["skipped_ids"]= sorted(ids)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        data= {"is_deleted": False, "modified_at": timezone.now()}
        if request.user.is_authenticated:                       # login ho tabhi modified_by
            data["modified_by"]= request.user
        projects.update(**data)

        result= {"detail": f" project(s) restored.", "restored_ids": sorted(restored)}
        skipped= sorted(ids - set(restored))
        if skipped:
            result["skipped_ids"]= skipped
        return Response(result)


# TASK RESTORE
class ProjectTaskRestoreView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        task = get_object_or_404(ProjectTask,pk=id,is_deleted=True)
        task.is_deleted = False
        task.save(
            update_fields=[
                'is_deleted',
                'updated_at'
            ])

        return Response({"detail": "Task restored successfully.","restored_id": task.id},status=status.HTTP_200_OK)

    

