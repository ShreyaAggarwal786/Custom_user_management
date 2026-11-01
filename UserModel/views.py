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

from .models import  User, Client, Project, ProjectAttachement, Profile
from .serializers import(
    UserCreateSerializer,UserSerializer,UserUpdateSerializer,
    ForgotPasswordSerializer,ResetPasswordSerializer,
    SendOTPSerializer,VerifyOTPSerializer,LoginSerializer,
    ClientSerializer,ProjectSerializer,ProjectAttachementSerializer,
    ProfileSerializer, RestoreSerializer,
)

from .utils import(PASSWORD_RESET, VERIFY, send_otp, send_welcome_email, verify_otp,)


class Pagination(PageNumberPagination):
    page_size=10
    page_size_query_param= "page_size"
    max_page_size=100


class UserListCreateView(APIView):
    permission_classes=[AllowAny]

    def get(self,request):
        users=User.objects.all().order_by('id')

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
    "Administrator",
    "Standard",
    "Developer",
    "Client",
    "Human Resources",
]

class ProfileListCreateView(APIView):
    permission_classes=[AllowAny]

    def initial(self,request,*args, **kwargs):
        super().initial(request, *args, **kwargs)
        for role in DEFAULT_PROFILES:
            Profile.objects.get_or_create(
                role=role,
                defaults= {"is_default": True},
            )

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


        profiles= Profile.objects.prefetch_related("users")
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
class ProjectListCreateView(APIView):
    permission_classes=[IsAuthenticated]
    parser_classes= [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        projects= Project.objects.select_related(
            'client','manager','created_by','modified_by'
        ).order_by("-id")
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
        for f in request.FILES.getlist("attachements"):
            file_serializer= ProjectAttachementSerializer(data={'file': f}, context={"request": request})
            file_serializer.is_valid(raise_exception=True)
            file_serializers.append(file_serializer)

        with transaction.atomic():
            project= serializer.save(created_by= request.user, modified_by= request.user)
            for file_serializer in file_serializers:
                f= file_serializer.validated_data['file']
                file_serializer.save(project=project, file_name= f.name)
        return Response(ProjectSerializer(project, context={"request": request}).data, status=status.HTTP_201_CREATED)

class ProjectDetailView(APIView):
    permission_classes=[IsAuthenticated]
    parser_classes=[MultiPartParser, FormParser, JSONParser]

    def get_object(self,id):
        return get_object_or_404(Project, pk=id)

    def get(self, request,id):
        project= self.get_object(id)
        serializer= ProjectSerializer(project, context={"request": request})
        return Response(serializer.data)

    def put(self, request,id):
        return self._update(request, id, partial= False)

    def patch(self, request,id):
            return self._update(request, id, partial= True)

    def post(self, request, id):
        project= self.get_object(id)

        if project.project_status== "Inactive":
            return Response({"detail": "Project is inactive."}, status=status.HTTP_400_BAD_REQUEST)

        file_serializers=[]
        for f in request.FILES.getlist("attachements"):
            file_serializer= ProjectAttachementSerializer(data= {"file":f}, context={"request": request}) 
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
        serializer= ProjectSerializer(project, data= request.data, partial= partial, context={"request":request})
        serializer.is_valid(raise_exception= True)

        files= request.FILES.getlist("attachements")
        final_status= serializer.validated_data.get("project_status", project.project_status)
        if files and final_status == "Inactive":
            return Response({"detail": "Project is inactive."}, status=status.HTTP_400_BAD_REQUEST)



        file_serializers=[]
        for f in files:
            file_serializer= ProjectAttachementSerializer(data={"file":f}, context={"request": request})
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

            if project.project_status == "Inactive":
                return Response({"detail": "Project is inactive."}, status=status.HTTP_400_BAD_REQUEST)

            if hasattr(request.data, "getlist"):
                raw_ids= request.data.getlist("attachements_ids")
            else:
                raw_ids= request.data.get("attachements_ids")
            if not isinstance(raw_ids, list) or not raw_ids:
                return Response({"attachement_ids": "attachement_ids must be a non-empty list. Example: {\"attachements_ids\":[1,2]"}, status= status.HTTP_400_BAD_REQUEST)

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
                {"detail": f"{len(attachements)} attachement(s) deleted.", "deleted_ids": sorted(found_ids)},
                status=status.HTTP_200_OK,
            ) 
            
        project.project_status= "Inactive"
        project.modified_by= request.user
        project.save(update_fields=['project_status','modified_by','modified_at'])
        return Response({"detail": "Project Deactivated"}, status=status.HTTP_200_OK)


class Restoreview(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = RestoreSerializer(data= request.data)
        serializer.is_valid(raise_exception=True)

        model= serializer.validated_data['model']
        id= serializer.validated_data['id']

        if model== 'user':
            obj = get_object_or_404(User, pk=id)

            if obj.status == User.Status.ACTIVE:
                return Response(
                    {"detail":"User is already active."},status=status.HTTP_400_BAD_REQUEST)

            obj.status= User.Status.ACTIVE
            obj.save(update_fields=['status'])

        elif model=='client':
            obj = get_object_or_404(Client, pk=id)

            if obj.status == Client.Status.ACTIVE:
                return Response(
                    {"detail":"Client is already active."},status=status.HTTP_400_BAD_REQUEST)

            obj.status= Client.Status.ACTIVE
            # obj.modified_by = request.user
            obj.save(update_fields=['status','modified_by','modified_at'])

        elif model=='project':
            obj = get_object_or_404(Project, pk=id)

            if obj.project_status != "Inactive":
                return Response(
                    {"detail":"Project is already active."},status=status.HTTP_400_BAD_REQUEST)

            obj.project_status= "ACTIVE"
            # obj.modified_by = request.user
            obj.save(update_fields=['project_status','modified_by','modified_at'])
        
        return Response({"detail": f'{model.capitalize()} Restored'}, status= status.HTTP_200_OK)





# Project Attachement
# MAX_FILES_PER_REQUEST= 5
# MAX_FILES_PER_PROJECT= 20

# class ProjectAttachementListCreateView(APIView):
#     permission_classes=[IsAuthenticated]
#     parser_classes=[MultiPartParser, FormParser]

#     def get(self, request, id):
#         project= get_object_or_404(Project, pk= id)
#         attachements= ProjectAttachement.objects.select_related(
#             'created_by','modified_by'
#         ).filter(project= project)

#         paginator= Pagination()
#         page= paginator.paginate_queryset(attachements, request, view=self)
#         serializer= ProjectAttachementSerializer(page, many= True, context={"request":request})
#         return paginator.get_paginated_response(serializer.data)

#     def post(self, request, id):
#         project= get_object_or_404(Project, pk= id)
#         if project.project_status== "Inactive":
#             return Response({"detail": "Cannot add attachments to an inactive project."}, status=status.HTTP_400_BAD_REQUEST)

#         files= request.FILES.getlist("file")
#         if not files:
#             return Response({"file": "At least one file is required."}, status=status.HTTP_400_BAD_REQUEST)
#         # if len(files) > MAX_FILES_PER_REQUEST:
#         #     return Response({"file": f" You can upload maximum {MAX_FILES_PER_REQUEST} files at a time. "}) 

#         # active_count= ProjectAttachement.objects.filter(
#         #     project=project).count()
#         # if active_count + len(files) > MAX_FILES_PER_PROJECT:
#         #     return Response({"file": f"A project can have maximum {MAX_FILES_PER_PROJECT} attachments."}, status=status.HTTP_400_BAD_REQUEST)

#         serializers_list=[]
#         for f in files:
#             serializer = ProjectAttachementSerializer(data={"file":f}, context={"request":request})
#             serializer.is_valid(raise_exception=True)
#             serializers_list.append(serializer)

#         result=[]
#         for serializer in serializers_list:
#             f= serializer.validated_data["file"]
#             serializer.save(project=project, file_name=f.name, 
#                             created_by= request.user, modified_by= request.user )
#             result.append(serializer.data)
#         return Response(result, status= status.HTTP_201_CREATED)


# # class ProjectAttachementDetailView(APIView):
# #     permission_classes=[IsAuthenticated]
# #     parser_classes=[MultiPartParser, FormParser]

# #     def get_object(self, id, attachement_id):
# #         return get_object_or_404(
# #         ProjectAttachement, pk=attachement_id, project_id=id)

# #     def get(self, request, id, attachement_id):
# #         attachement= self.get_object(id, attachement_id)
# #         serializer= ProjectAttachementSerializer(attachement, context={"request":request})
# #         return Response(serializer.data)

# #     def put(self, request, id, attachement_id):
# #         return self._update(request, id, attachement_id, partial=False)
    
# #     def patch(self, request, id, attachement_id):
# #             return self._update(request, id, attachement_id, partial=True)

    
# #     def _update(self, request,id,attachement_id, partial):
# #         attachement= self.get_object(id, attachement_id)
# #         if attachement.project.project_status == "Inactive":
# #             return Response({"detail":"Cannot update attachments of an inactive project."},status=status.HTTP_400_BAD_REQUEST)
        
# #         f= request.FILES.get("file")
# #         if not f:
# #             return Response({"file":"file is required."},status=status.HTTP_400_BAD_REQUEST)

# #         old_name= attachement.file.name
# #         storage= attachement.file.storage

# #         serializer= ProjectAttachementSerializer(
# #             attachement, data={"file": f},partial=partial, context={"request":request})
# #         serializer.is_valid(raise_exception=True)
# #         serializer.save(file_name=f.name,modified_by= request.user)

# #         if old_name:
# #             storage.delete(old_name)
# #         return Response(serializer.data)



# #     def delete(self,request,id, attachement_id):
# #         attachement= self.get_object(id,attachement_id)

# #         if attachement.file:
# #             attachement.file.delete(save=False)

# #         attachement.delete()
# #         return Response({"detail":"Attachement Deleted"},status=status.HTTP_200_OK)


        

    








