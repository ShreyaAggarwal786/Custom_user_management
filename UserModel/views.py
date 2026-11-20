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
from django.db.models.deletion import ProtectedError
from .models import  User, Client, Project,Project_Type, Project_Status, ProjectAttachement, Profile, ProjectTask, Task_Status, TaskComment
from .serializers import(
    UserCreateSerializer,UserSerializer,UserUpdateSerializer,ProfileSerializer,
    ForgotPasswordSerializer,ResetPasswordSerializer,
    SendOTPSerializer,VerifyOTPSerializer,LoginSerializer,
    ClientSerializer,ProjectSerializer,ProjectAttachementSerializer,
    ProjectTypeSerializer,ProjectStatusSerializer,TaskStatusSerializer, ProjectTaskSerializer,TaskCommentSerializer,
)

from .utils import(PASSWORD_RESET, VERIFY, send_otp, send_welcome_email, verify_otp,)


class Pagination(PageNumberPagination):
    page_size=10
    page_size_query_param= "page_size"
    max_page_size=100


class UserListCreateView(APIView):
    permission_classes=[IsAuthenticated]

    def get(self,request):
        users=User.objects.order_by('id')
        has_admin_access=(
            request.user.profile is not None and 
            request.user.profile.role.lower() in['super admin','admin']
        )
        if not has_admin_access:
            users= users.filter(id=request.user.id)

       
        search = request.query_params.get("search", "").strip()
        if search:
            for word in search.split():
                users = users.filter(
                    Q(username__icontains=word) |Q(email__icontains=word) |
                    Q(first_name__icontains=word) |Q(last_name__icontains=word) |
                    Q(phone__icontains=word) |Q(profile__role__icontains=word)
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

        if profile.lower() == "null":
            return Response({"detail": "Invalid URL parameter."},status=status.HTTP_400_BAD_REQUEST)
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
        if (
            request.user.profile is None or
            request.user.profile.role.lower() not in ["super admin", "admin"]):
            return Response({"detail": "Only Super Admin and Admin can create users."},status=status.HTTP_403_FORBIDDEN)
        serializer= UserCreateSerializer(data= request.data, context={"request":request})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user= serializer.save(
                created_by=request.user,
                modified_by=request.user
            )
            # if user.profile and user.profile.role.lower() == "client":
            #     Client.objects.create(
            #         first_name=user.first_name,
            #         last_name=user.last_name,
            #         email=user.email,
            #         contact_number=user.phone,
            #         address=user.current_address,
            #         country=user.country,
            #         status=user.status,
            #         created_by=request.user,
            #         modified_by=request.user,
            #     )

        try:
            send_welcome_email(user)
        except Exception:
            print("Welcome email failed")
        return Response((UserSerializer(user, context={"request":request})).data, status=status.HTTP_201_CREATED)
    
    def patch(self, request):
        if (
            request.user.profile is None or
            request.user.profile.role.lower() not in ["super admin", "admin"]):
            return Response({"detail": "Only Super Admin and Admin can delete users."}, status=status.HTTP_403_FORBIDDEN)

        raw= request.query_params.get("ids","") + "," + str(request.data.get("ids","")).strip("[]")
        ids= {int(x) for x in raw.replace(" ","").split(",") if x.isdigit()}
        if not ids:
            return Response({"detail": "Please provide user ids to delete."}, status=status.HTTP_400_BAD_REQUEST)

        users= User.objects.filter(pk__in=ids).exclude(status=User.Status.INACTIVE)
        deleted= list(users.values_list("id", flat=True))
        if not deleted:
            return Response({"detail": "No active user found for given ids."}, status=status.HTTP_400_BAD_REQUEST)

        client_emails= list(users.filter(profile__role__iexact="client").values_list("email", flat=True))
        with transaction.atomic():
            users.update(status=User.Status.INACTIVE, modified_by=request.user, modified_at=timezone.now())
            for email in client_emails:
                Client.objects.filter(email__iexact=email).update(
                    status=Client.Status.INACTIVE,
                    modified_by=request.user,
                    modified_at=timezone.now(),
                )
        return Response({"details": "users deleted successfully."},status=status.HTTP_200_OK)

class UserDetailView(APIView):
    permission_classes=[IsAuthenticated]

    def get_object(self,id):
        return get_object_or_404(User, pk=id)

    def get(self,request,id):
        user= self.get_object(id)
        has_admin_access=(
            request.user.profile is not None and
            request.user.profile.role.lower() in ['super admin','admin']
        )
        if not has_admin_access and user.id != request.user.id:
            return Response({"detail": "you can only access your own data."},status=status.HTTP_403_FORBIDDEN)
        
        if user.status == User.Status.INACTIVE:
            return Response({"detail": "User is inactive."}, status=status.HTTP_400_BAD_REQUEST)
        serializer= UserSerializer(user, context={"request": request})
        return Response(serializer.data)

    def put(self,request,id):
        return self._update(request,id,partial=False)

    def patch(self,request,id):
        return self._update(request,id,partial=True)

    def _update(self, request, id, partial):
        user = self.get_object(id)
        has_admin_access=(
            request.user.profile is not None and 
            request.user.profile.role.lower() in['super admin','admin']
        )
        if not has_admin_access and user.id != request.user.id:
            return Response({"detail": "you can only modify your own data."},status=status.HTTP_403_FORBIDDEN)

        if not has_admin_access and "profile" in request.data:
            return Response({"detail": "You cannot change your own profile."},status=status.HTTP_403_FORBIDDEN)

        serializer= UserUpdateSerializer(
            user, data=request.data, partial=partial, context={"request": request})
        # with transaction.atomic():
        #     user = serializer.save(modified_by=request.user)

        #     if user.profile and user.profile.role.lower() == "client":
        #         updated = Client.objects.filter(email__iexact=user.email).update(
        #             first_name=user.first_name,
        #             last_name=user.last_name,
        #             contact_number=user.phone,
        #             address=user.current_address,
        #             country=user.country,
        #             modified_by=request.user,
        #             modified_at=timezone.now(),
        #         )
        #         if not updated:
        #             raise ValidationError({"detail": "Client record does not exist for this user."})
        serializer.is_valid(raise_exception=True)
        user=serializer.save(modified_by=request.user)
        return Response(UserSerializer(user, context={"request":request}).data)

    # def delete(self,request, id):
    #     user= self.get_object(id)
    #     if user.status ==User.Status.INACTIVE:       
    #         return Response({"detail": "User is already inactive."}, status= status.HTTP_400_BAD_REQUEST)
        
    #     user.status= User.status.INACTIVE
    #     user.modified_by= request.user
    #     user.save(update_fields=["status","modified_by"])
    #     return Response({"detail": "User is deleted successfully."}, status=status.HTTP_200_OK)


#profile
DEFAULT_PROFILES=[
    "Super Admin",
    "Admin",
    "Manager",
    "Team Leader",
    "Developer",
    "Human Resources",
    "Client",
]

class ProfileListCreateView(APIView):
    permission_classes=[AllowAny]

    def initial(self,request,*args, **kwargs):
        super().initial(request, *args, **kwargs)
        Profile.objects.exclude(role__in= DEFAULT_PROFILES).update(is_default=False)
        for role in DEFAULT_PROFILES:
            profile= Profile.objects.filter(role__iexact= role).first()
            if profile:
                profile.is_default=True
                profile.save(update_fields=['is_default'])
            else:
                Profile.objects.create(role=role, is_default=True)

    def get(self, request):
        value = request.query_params.get("profile", "").strip()

        if value.lower() == "null":
            return Response({"detail": "Invalid URL parameter."},status=status.HTTP_400_BAD_REQUEST)
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
        try:
            profile.delete()
        except ProtectedError:
            return Response({"detail": "This profile is being used and cannot be deleted."},status=status.HTTP_400_BAD_REQUEST)
        profile.delete()                         
        return Response({"detail": "Profile Deleted successfully"}, status=status.HTTP_200_OK)

    

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

    def patch(self, request):
        raw= request.query_params.get("ids","") + "," + str(request.data.get("ids","")).strip("[]")
        ids= {int(x) for x in raw.replace(" ","").split(",") if x.isdigit()}
        if not ids:
            return Response({"detail": "Please provide client ids to delete."}, status=status.HTTP_400_BAD_REQUEST)

        clients= Client.objects.filter(pk__in=ids).exclude(status=Client.Status.INACTIVE)
        client_emails= list(clients.values_list("email", flat=True))
        if not client_emails:
            return Response({"detail": "No active client found for given ids."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            clients.update(status=Client.Status.INACTIVE, modified_by=request.user, modified_at=timezone.now())
            for email in client_emails:
                if email:
                    User.objects.filter(email__iexact=email, profile__role__iexact="client").update(
                        status=User.Status.INACTIVE,
                        modified_by=request.user,
                        modified_at=timezone.now(),
                    )
        return Response({"detail": "Clients deleted successfully."}, status=status.HTTP_200_OK)

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
        if "status" in request.data:
            return Response({"status": "Client status cannot be updated,"},status=status.HTTP_400_BAD_REQUEST)
        serializer= ClientSerializer(
            client, data= request.data, partial= partial,context={"request":request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(modified_by=request.user)
        return Response(serializer.data)

    # def delete(self,request,id):
    #     client=self.get_object(id)
    #     client.status= Client.Status.INACTIVE
    #     client.modified_by= request.user
    #     client.save(update_fields=['status','modified_by','modified_at'])
    #     return Response({"detail": "Client Deactivated"},status= status.HTTP_200_OK)


# PROJECT TYPE
DEFAULT_PROJECT_TYPES = [
    "Web Development",
    "App Development",
    "Software Development",
    "UI/UX Design",
    "Digital Marketing",
]
class ProjectTypeListCreateView(APIView):
    permission_classes = [AllowAny]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        Project_Type.objects.update(is_default=False)

        for value in DEFAULT_PROJECT_TYPES:
            project_type = Project_Type.objects.filter(project_type__iexact=value).first()
            if project_type:
                project_type.is_default = True
                project_type.save(update_fields=['is_default'])
            else:
                Project_Type.objects.create(project_type=value,is_default=True)

    def get(self, request):
        project_types = Project_Type.objects.all().order_by("id")
        project_type_id = request.query_params.get("project_type_id", "").strip()
        project_type = request.query_params.get("project_type", "").strip()
        is_default = request.query_params.get("is_default", "").strip().lower()

        if project_type_id:
            if not project_type_id.isdigit():
                return Response({"project_type_id": "Enter a valid project type ID."},status=status.HTTP_400_BAD_REQUEST)
            project_types = project_types.filter(id=int(project_type_id))

        if project_type:
            project_types = project_types.filter(project_type__icontains=project_type)

        if is_default:
            if is_default not in ["true", "false"]:
                return Response({"is_default": "Only true or false is allowed."},status=status.HTTP_400_BAD_REQUEST)
            project_types = project_types.filter(is_default=(is_default == "true"))

        paginator = Pagination()
        page = paginator.paginate_queryset(project_types, request, view=self)
        serializer = ProjectTypeSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ProjectTypeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data,status=status.HTTP_201_CREATED)


class ProjectTypeDetailView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, id):
        return get_object_or_404(Project_Type, pk=id)

    def get(self, request, id):
        project_type = self.get_object(id)
        serializer = ProjectTypeSerializer(project_type, context={"request": request})
        return Response(serializer.data)

    def put(self, request, id):
        return self._update(request, id, partial=False)

    def patch(self, request, id):
        return self._update(request, id, partial=True)

    def _update(self, request, id, partial):
        project_type = self.get_object(id)
        if project_type.is_default:
            return Response({"detail": "Default project type cannot be modified."},status=status.HTTP_400_BAD_REQUEST )

        serializer = ProjectTypeSerializer( project_type,data=request.data,partial=partial,context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, id):
        project_type = self.get_object(id)
        if project_type.is_default:
            return Response({"detail": "Default project type cannot be deleted."},status=status.HTTP_400_BAD_REQUEST)
        try:
            project_type.delete()
        except ProtectedError:
            return Response({"detail": "This project type is being used in a project and cannot be deleted."},status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Project type deleted successfully."},status=status.HTTP_200_OK)


# PROJECT STATUS
DEFAULT_PROJECT_STATUSES = [
    "Active",
    "Completed",
    "Inprogress",
    "Pending",
    "Inactive",
]
class ProjectStatusListCreateView(APIView):
    permission_classes = [AllowAny]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        Project_Status.objects.update(is_default=False)

        for value in DEFAULT_PROJECT_STATUSES:
            project_status = Project_Status.objects.filter(project_status__iexact=value).first()
            if project_status:
                project_status.is_default = True
                project_status.save(update_fields=['is_default'])
            else:
                Project_Status.objects.create(project_status=value, is_default=True)

    def get(self, request):
        project_statuses = Project_Status.objects.all().order_by("id")
        project_status_id = request.query_params.get( "project_status_id", "").strip()
        project_status = request.query_params.get("project_status", "").strip()
        is_default = request.query_params.get("is_default", "").strip().lower()

        if project_status_id:
            if not project_status_id.isdigit():
                return Response({"project_status_id": "Enter a valid project status ID."}, status=status.HTTP_400_BAD_REQUEST)
            project_statuses = project_statuses.filter(id=int(project_status_id))

        if project_status:
            project_statuses = project_statuses.filter( project_status__icontains=project_status)

        if is_default:
            if is_default not in ["true", "false"]:
                return Response({"is_default": "Only true or false is allowed."},status=status.HTTP_400_BAD_REQUEST)
            project_statuses = project_statuses.filter( is_default=(is_default == "true"))

        paginator = Pagination()
        page = paginator.paginate_queryset(project_statuses, request, view=self)
        serializer = ProjectStatusSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ProjectStatusSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data,status=status.HTTP_201_CREATED)


class ProjectStatusDetailView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, id):
        return get_object_or_404(Project_Status, pk=id)

    def get(self, request, id):
        project_status = self.get_object(id)
        serializer = ProjectStatusSerializer(project_status, context={"request": request})
        return Response(serializer.data)

    def put(self, request, id):
        return self._update(request, id, partial=False)

    def patch(self, request, id):
        return self._update(request, id, partial=True)

    def _update(self, request, id, partial):
        project_status = self.get_object(id)
        if project_status.is_default:
            return Response({"detail": "Default project status cannot be modified."},status=status.HTTP_400_BAD_REQUEST)

        serializer = ProjectStatusSerializer(project_status, data=request.data, partial=partial, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, id):
        project_status = self.get_object(id)
        if project_status.is_default:
            return Response({"detail": "Default project status cannot be deleted."},status=status.HTTP_400_BAD_REQUEST)
        try:
            project_status.delete()
        except ProtectedError:
            return Response({"detail": "This project status is being used in a project and cannot be deleted."},status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Project status deleted successfully."},status=status.HTTP_200_OK)


# TASK STATUS
DEFAULT_TASK_STATUSES = [
    "Pending",
    "Active",
    "Inactive",
    "Inprogress",
    "Completed",
    "On Hold",
    "Cancelled",
]
class TaskStatusListCreateView(APIView):
    permission_classes = [AllowAny]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        Task_Status.objects.update(is_default=False)

        for value in DEFAULT_TASK_STATUSES:
            task_status = Task_Status.objects.filter(status__iexact=value).first()

            if task_status:
                task_status.is_default = True
                task_status.save(update_fields=['is_default'])
            else:
                Task_Status.objects.create(
                    status=value,
                    is_default=True
                )

    def get(self, request):
        task_statuses = Task_Status.objects.all().order_by("id")

        task_status_id = request.query_params.get("task_status_id", "").strip()
        task_status = request.query_params.get( "status", "").strip()
        is_default = request.query_params.get( "is_default", "").strip().lower()

        if task_status_id:
            if not task_status_id.isdigit():
                return Response({"task_status_id": "Enter a valid task status ID."},status=status.HTTP_400_BAD_REQUEST)
            task_statuses = task_statuses.filter(id=int(task_status_id))

        if task_status:
            task_statuses = task_statuses.filter(status__icontains=task_status)

        if is_default:
            if is_default not in ["true", "false"]:
                return Response({"is_default": "Only true or false is allowed."},status=status.HTTP_400_BAD_REQUEST)
            task_statuses = task_statuses.filter(is_default=(is_default == "true"))

        paginator = Pagination()
        page = paginator.paginate_queryset(task_statuses, request, view=self)
        serializer = TaskStatusSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = TaskStatusSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data,status=status.HTTP_201_CREATED)




#project
#send client notification
def send_client_notification(project):
    client= project.client or project.user_client
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
            recipient_list=[client.email]
            # recipient_list=[project.client.email],
        )
    except Exception:
        print("Client email failed")


# send manager notification
def send_manager_notification(project):
    manager= project.manager
    if not manager or not manager.email:
        return False
    client = project.client or project.user_client
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
            'client','user_client','manager','created_by','modified_by','project_type','project_status'
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
                    Q(project_type__project_type__icontains=word) |
                    Q(description__icontains=word) |
                    Q(client__first_name__icontains=word) |
                    Q(client__last_name__icontains=word) |
                    Q(client__email__icontains=word) |
                    Q(user_client__first_name__icontains=word) |
                    Q(user_client__last_name__icontains=word) |
                    Q(user_client__email__icontains=word)|
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
        user_client= request.query_params.get("user_client", "").strip()
        user_client_id = request.query_params.get("user_client_id", "").strip()
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
            projects= projects.filter(project_type__project_type__icontains=project_type)
        if description:
            projects= projects.filter(description__icontains=description)
        if project_status:
            projects= projects.filter(project_status__project_status__iexact=project_status)

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

        if user_client.isdigit():
            projects= projects.filter(user_client_id=int(client))        
        user_client_first_name = request.query_params.get("client_first_name")
        user_client_last_name = request.query_params.get("client_last_name")
        user_client_email = request.query_params.get("client_email")

        if user_client_id:
            if not user_client_id.isdigit():
                return Response(
                    {"user_client_id": "Enter a valid user client ID."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            projects = projects.filter(user_client_id=int(user_client_id))

        if user_client_first_name:
            projects = projects.filter(
                user_client__first_name__icontains=user_client_first_name
            )

        if user_client_last_name:
            projects = projects.filter(
                user_client__last_name__icontains=user_client_last_name
            )

        if user_client_email:
            projects = projects.filter(
                user_client__email__icontains=user_client_email
            )

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
            projects= projects.filter(project_status__project_status__iexact=project_status)
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

        projects = projects.filter(
            Q(user_client=request.user) |
            Q(manager=request.user)
        )
        
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
    def patch(self, request):
        raw = request.query_params.get("ids", "") + "," + str( request.data.get("ids", "")).strip("[]")
        ids = {int(x) for x in raw.replace(" ", "").split(",")if x.isdigit()}
        if not ids:
            return Response({"detail": "Please provide project ids to delete."},status=status.HTTP_400_BAD_REQUEST)

        projects = Project.objects.filter(pk__in=ids, is_deleted=False)
        deleted_ids = list(projects.values_list("id", flat=True))

        if not deleted_ids:
            return Response({"detail": "No active project found for given ids."},status=status.HTTP_400_BAD_REQUEST)

        projects.update(
            is_deleted=True,
            modified_by=request.user,
            modified_at=timezone.now()
        )
        return Response({"detail": "Projects deleted successfully."},status=status.HTTP_200_OK)

class ProjectDetailView(APIView):

    permission_classes=[IsAuthenticated]
    parser_classes=[MultiPartParser, FormParser, JSONParser]

    def get_object(self,id):
        return get_object_or_404(Project, pk=id)

    def get(self, request,id):
        project= self.get_object(id)
        if project.is_deleted == True:
            return Response({"detail": "Project is deleted."},status= status.HTTP_400_BAD_REQUEST)
        
        if project.user_client_id != request.user.id and project.manager_id != request.user.id:
            return Response({"detail": "You do not have permission to access this project."},status=status.HTTP_403_FORBIDDEN)
        
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
        if project.is_deleted:                               
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
            return Response({"detail": f" Attachement(s) has been  deleted.", "deleted_ids": sorted(found_ids)},status=status.HTTP_200_OK,) 
        
# TASK STATUS
DEFAULT_TASK_STATUSES = [
    "Pending",
    "Active",
    "Inactive",
    "Inprogress",
    "Completed",
    "On Hold",
    "Cancelled",
]
class TaskStatusListCreateView(APIView):
    permission_classes = [AllowAny]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        Task_Status.objects.update(is_default=False)

        for value in DEFAULT_TASK_STATUSES:
            task_status = Task_Status.objects.filter(status__iexact=value).first()

            if task_status:
                task_status.is_default = True
                task_status.save(update_fields=['is_default'])
            else:
                Task_Status.objects.create(
                    status=value,
                    is_default=True
                )

    def get(self, request):
        task_statuses = Task_Status.objects.all().order_by("id")

        task_status_id = request.query_params.get("task_status_id", "").strip()
        task_status = request.query_params.get( "status", "").strip()
        is_default = request.query_params.get( "is_default", "").strip().lower()

        if task_status_id:
            if not task_status_id.isdigit():
                return Response({"task_status_id": "Enter a valid task status ID."},status=status.HTTP_400_BAD_REQUEST)
            task_statuses = task_statuses.filter(id=int(task_status_id))

        if task_status:
            task_statuses = task_statuses.filter(status__icontains=task_status)

        if is_default:
            if is_default not in ["true", "false"]:
                return Response({"is_default": "Only true or false is allowed."},status=status.HTTP_400_BAD_REQUEST)
            task_statuses = task_statuses.filter(is_default=(is_default == "true"))

        paginator = Pagination()
        page = paginator.paginate_queryset(task_statuses, request, view=self)
        serializer = TaskStatusSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = TaskStatusSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data,status=status.HTTP_201_CREATED)


class TaskStatusDetailView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, id):
        return get_object_or_404(Task_Status, pk=id)

    def get(self, request, id):
        task_status = self.get_object(id)
        serializer = TaskStatusSerializer(task_status, context={"request": request})
        return Response(serializer.data)

    def put(self, request, id):
        return self._update(request, id, partial=False)

    def patch(self, request, id):
        return self._update(request, id, partial=True)

    def _update(self, request, id, partial):
        task_status = self.get_object(id)
        if task_status.is_default:
            return Response({"detail": "Default task status cannot be modified."},status=status.HTTP_400_BAD_REQUEST)

        serializer = TaskStatusSerializer( task_status,data=request.data,partial=partial,context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, id):
        task_status = self.get_object(id)
        if task_status.is_default:
            return Response({"detail": "Default task status cannot be deleted."},status=status.HTTP_400_BAD_REQUEST)
        try:
            task_status.delete()
        except ProtectedError:
            return Response({"detail": "This task status is being used in a task and cannot be deleted."},status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Task status deleted successfully."},status=status.HTTP_200_OK)


# PROJECT TASK
class ProjectTaskListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        
        tasks = ProjectTask.objects.select_related(
            'project',
            'task_status',
            'assign_by__profile',
            'assign_to__profile',
            'created_by__profile',
            'modified_by__profile'
        ).prefetch_related(
            'comments__user'
        )
        is_deleted = request.query_params.get("is_deleted", "false").strip().lower()
        if is_deleted not in ["true", "false"]:
            return Response({"is_deleted": "Only true or false is allowed."}, status=status.HTTP_400_BAD_REQUEST)
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
                return Response({"project": "Enter a valid project ID."},status=status.HTTP_400_BAD_REQUEST)
            tasks = tasks.filter(project_id=int(project))

        if assign_by:
            if not assign_by.isdigit():
                return Response({"assign_by": "Enter a valid user ID."},status=status.HTTP_400_BAD_REQUEST)
            tasks = tasks.filter(assign_by_id=int(assign_by))

        if assign_to:
            if not assign_to.isdigit():
                return Response({"assign_to": "Enter a valid user ID."},status=status.HTTP_400_BAD_REQUEST)
            tasks = tasks.filter(assign_to_id=int(assign_to))

        if task_status:
            tasks = tasks.filter(task_status__status__iexact=task_status)


        task_start_date = request.query_params.get("task_start_date", "").strip()
        task_complete_date = request.query_params.get("task_complete_date", "").strip()

        if task_start_date:
            date_value = parse_date(task_start_date)
            if date_value is None:
                return Response({"task_start_date": "Enter date in YYYY-MM-DD format."},status=status.HTTP_400_BAD_REQUEST)
            tasks = tasks.filter(task_start_date=date_value)

        if task_complete_date:
            date_value = parse_date(task_complete_date)
            if date_value is None:
                return Response({"task_complete_date": "Enter date in YYYY-MM-DD format."}, status=status.HTTP_400_BAD_REQUEST)
            tasks = tasks.filter(task_complete_date=date_value)


        start_date_from = request.query_params.get("start_date_from", "").strip()
        start_date_to = request.query_params.get("start_date_to", "").strip()

        if start_date_from:
            date_value = parse_date(start_date_from)
            if date_value is None:
                return Response({"start_date_from": "Enter date in YYYY-MM-DD format."},status=status.HTTP_400_BAD_REQUEST)
            tasks = tasks.filter(task_start_date__gte=date_value)

        if start_date_to:
            date_value = parse_date(start_date_to)
            if date_value is None:
                return Response({"start_date_to": "Enter date in YYYY-MM-DD format."},status=status.HTTP_400_BAD_REQUEST)
            tasks = tasks.filter(task_start_date__lte=date_value)


        complete_date_from = request.query_params.get("complete_date_from", "").strip()
        complete_date_to = request.query_params.get("complete_date_to", "").strip()

        if complete_date_from:
            date_value = parse_date(complete_date_from)
            if date_value is None:
                return Response({"complete_date_from": "Enter date in YYYY-MM-DD format."},status=status.HTTP_400_BAD_REQUEST)
            tasks = tasks.filter(task_complete_date__gte=date_value)

        if complete_date_to:
            date_value = parse_date(complete_date_to)
            if date_value is None:
                return Response(
                    {"complete_date_to": "Enter date in YYYY-MM-DD format."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            tasks = tasks.filter(task_complete_date__lte=date_value)

        tasks = tasks.filter(
            Q(project__user_client=request.user) |
            Q(project__manager=request.user)
        )

        paginator = Pagination()
        page = paginator.paginate_queryset(tasks, request, view=self)
        serializer = ProjectTaskSerializer(page,many=True,context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ProjectTaskSerializer(data=request.data,context={"request": request})
        serializer.is_valid(raise_exception=True)

        task = serializer.save(created_by=request.user,modified_by=request.user)

        return Response(
            ProjectTaskSerializer(task,context={"request": request}).data,status=status.HTTP_201_CREATED)
    def patch(self, request):
        raw = request.query_params.get("ids", "") + "," + str(request.data.get("ids", "")).strip("[]")
        ids = {int(x) for x in raw.replace(" ", "").split(",")if x.isdigit()}

        if not ids:
            return Response( {"detail": "Please provide task ids to delete."},status=status.HTTP_400_BAD_REQUEST)
        tasks = ProjectTask.objects.filter(pk__in=ids,is_deleted=False)

        deleted_ids = list(tasks.values_list("id", flat=True))

        if not deleted_ids:
            return Response({"detail": "No active task found for given ids."},status=status.HTTP_400_BAD_REQUEST)

        tasks.update(
            is_deleted=True,
            modified_by=request.user,
            modified_at=timezone.now()
        )

        return Response({"detail": "Tasks deleted successfully."},status=status.HTTP_200_OK)


class ProjectTaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, id):
        return get_object_or_404(ProjectTask, pk=id, is_deleted=False)

    def get(self, request, id):
        task = self.get_object(id)
        if (task.project is None or
            (task.project.user_client_id != request.user.id and
            task.project.manager_id != request.user.id)):
            return Response({"detail": "You do not have permission to access this task."},status=status.HTTP_403_FORBIDDEN)
        
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
        task = serializer.save(modified_by=request.user)
        return Response(
            ProjectTaskSerializer(task,context={"request": request}).data)


# TASK COMMENT
class TaskCommentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, comment_id=None):
        task = get_object_or_404(ProjectTask,pk=project_task_id)
        
        project_task_id = request.query_params.get("project_task")
        if not project_task_id:
            return Response(
                {"project_task": "project_task is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not project_task_id.isdigit():
            return Response(
                {"project_task": "Enter a valid project task ID."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if task.is_deleted:
            return Response({"detail": "Cannot access comments of a deleted task."},status=status.HTTP_400_BAD_REQUEST)

        if (
            request.user != task.assign_by and
            request.user != task.assign_to and
            (task.project is None or task.project.user_client_id != request.user.id)
        ):
            return Response({"detail":"You do not have permission to view these comments."},status=status.HTTP_403_FORBIDDEN)

        comments = task.comments.select_related(
            'task',
            'task__project',
            'task__task_status',
            'user'
        ).order_by("-id")

        serializer = TaskCommentSerializer(
            comments,
            many=True,
            context={"request": request}
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    # POST: Create a comment
    def post(self, request, comment_id=None):
        project_task_id = request.data.get("project_task")

        if not project_task_id:
            return Response({"project_task": "project_task is required."},status=status.HTTP_400_BAD_REQUEST)
        if not str(project_task_id).isdigit():
            return Response({"project_task": "Enter a valid project task ID."},status=status.HTTP_400_BAD_REQUEST)
        
        task = get_object_or_404( ProjectTask,pk=project_task_id)
        if task.is_deleted:
            return Response(
                {"detail": "Cannot comment on a deleted task."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.user not in [task.assign_by, task.assign_to]:
            return Response(
                {"detail": "Only assigned users can comment on this task."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = TaskCommentSerializer(
            data=request.data,
            context={"request": request}
        )

        serializer.is_valid(raise_exception=True)
        comment = serializer.save(task=task, user=request.user)

        return Response(
            TaskCommentSerializer(
                comment,
                context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED
        )

    # PATCH: Update own comment
    def patch(self, request, comment_id=None):
        if comment_id is None:
            return Response(
                {"comment_id": "Comment ID is required in URL."},
                status=status.HTTP_400_BAD_REQUEST
            )

        comment = get_object_or_404(
            TaskComment.objects.select_related(
                'task',
                'task__project',
                'user'
            ),
            pk=comment_id
        )

        task = comment.task

        if task is None or task.is_deleted:
            return Response(
                {"detail": "Cannot update comments of a deleted task."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.user not in [task.assign_by, task.assign_to]:
            return Response(
                {"detail": "Only assigned users can update comments."},
                status=status.HTTP_403_FORBIDDEN
            )
        if comment.user != request.user:
            return Response(
                {"detail": "You can only update your own comment."},
                status=status.HTTP_403_FORBIDDEN
            )
        if str(request.data.get("project_task")) != str(task.id):
            return Response(
                {"project_task": "This comment does not belong to the provided project task."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = TaskCommentSerializer(
            comment,
            data={"comment": request.data.get("comment")},
            partial=True,
            context={"request": request}
        )

        serializer.is_valid(raise_exception=True)
        comment = serializer.save()

        return Response(
            TaskCommentSerializer(
                comment,
                context={"request": request}
            ).data,
            status=status.HTTP_200_OK
        )

    # DELETE: Delete a comment
    def delete(self, request, comment_id=None):
        if comment_id is None:
            return Response(
                {"comment_id": "Comment ID is required in URL."},
                status=status.HTTP_400_BAD_REQUEST
            )

        comment = get_object_or_404(
            TaskComment.objects.select_related('task'),
            pk=comment_id
        )

        task = comment.task

        if task is None or task.is_deleted:
            return Response(
                {"detail": "Cannot delete comments of a deleted task."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.user not in [task.assign_by, task.assign_to]:
            return Response(
                {"detail": "Only assigned users can delete comments."},
                status=status.HTTP_403_FORBIDDEN
            )

        comment.delete()

        return Response(
            {"detail": "Comment deleted successfully."},
            status=status.HTTP_200_OK
        )

# class TaskCommentCreateView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request, id):
#         task = get_object_or_404(ProjectTask,pk=id)

#         if task.is_deleted:
#             return Response({"detail": "Cannot comment on a deleted task."},status=status.HTTP_400_BAD_REQUEST)

#         if request.user not in [task.assign_by,task.assign_to]:
#             return Response({"detail":"Only assigned users can comment on this task."},status=status.HTTP_403_FORBIDDEN)

#         serializer = TaskCommentSerializer(data=request.data,context={"request": request})
#         serializer.is_valid(raise_exception=True)
#         comment = serializer.save(task=task,user=request.user)

#         return Response(TaskCommentSerializer(comment,context={"request": request}).data,status=status.HTTP_201_CREATED)


# class TaskCommentDeleteView(APIView):
#     permission_classes = [IsAuthenticated]
#     def delete(self, request, id, comment_id):
#         task = get_object_or_404(ProjectTask,pk=id,is_deleted=False)
#         comment = get_object_or_404(TaskComment,pk=comment_id,task=task)
#         if request.user not in [task.assign_by,task.assign_to]:
#             return Response({"detail":"Only assigned users can delete comments."},status=status.HTTP_403_FORBIDDEN)
#         comment.delete()
#         return Response({"detail": "Comment deleted successfully."},status=status.HTTP_200_OK)


# USER RESTORE
class UserRestoreView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self, request, id=None):
        raw= request.query_params.get("ids","") + "," + str(request.data.get("ids","")).strip("[]")
        ids= {int(x) for x in raw.replace(" ","").split(",") if x.isdigit()}
        if id:
            ids.add(id)
        users= User.objects.filter(pk__in=ids, status=User.Status.INACTIVE)       
        restored_users = list(users.select_related("profile"))
        if not restored_users:
            return Response({"detail": "No inactive user found for given ids."}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        with transaction.atomic():
            users.update(status=User.Status.ACTIVE)
            client_emails = [
            user.email
            for user in restored_users
            if user.profile
            and user.profile.role
            and user.profile.role.lower() == "client"
            and user.email
        ]
            Client.objects.filter(email__in=client_emails).update(status=Client.Status.ACTIVE)
        return Response({"detail": "Users restored successfully."}, status=status.HTTP_200_OK)


# CLIENT RESTORE
class ClientRestoreView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self, request, id=None):
        raw= request.query_params.get("ids","") + "," + str(request.data.get("ids","")).strip("[]")
        ids= {int(x) for x in raw.replace(" ","").split(",") if x.isdigit()}
        if id:
            ids.add(id)
        clients= Client.objects.filter(pk__in=ids, status=Client.Status.INACTIVE)
        restored= list(clients.values_list("id", flat=True))
        if not restored:
            return Response({"detail": "No inactive client found for given ids."}, status=status.HTTP_400_BAD_REQUEST)
        clients.update(status=Client.Status.ACTIVE)
        return Response({"detail": "client restored successfully."}, status=status.HTTP_200_OK)


# PROJECT RESTORE
class ProjectRestoreView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self, request, id=None):
        raw= request.query_params.get("ids","") + "," + str(request.data.get("ids","")).strip("[]")
        ids= {int(x) for x in raw.replace(" ","").split(",") if x.isdigit()}
        if id:
            ids.add(id)
        projects= Project.objects.filter(pk__in=ids, is_deleted=True)
        restored= list(projects.values_list("id", flat=True))
        if not restored:
            return Response({"detail": "No deleted project found for given ids."}, status=status.HTTP_400_BAD_REQUEST)
        projects.update(is_deleted=False)
        return Response({"detail": "Projects restored successfully."}, status=status.HTTP_200_OK)


# TASK RESTORE
class ProjectTaskRestoreView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, id):
        task = get_object_or_404(ProjectTask,pk=id,is_deleted=True)
        task.is_deleted = False
        task.save(update_fields=['is_deleted'])
        return Response({"detail": "Task restored successfully."},status=status.HTTP_200_OK)

  

