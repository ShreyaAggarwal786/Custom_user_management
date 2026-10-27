from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework.views  import APIView
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.pagination import PageNumberPagination

from .models import  User, Client, Project
from .serializers import(
    UserCreateSerializer,UserSerializer,UserUpdateSerializer,
    ForgotPasswordSerializer,ResetPasswordSerializer,
    SendOTPSerializer,VerifyOTPSerializer,LoginSerializer,
    ClientSerializer,ProjectSerializer,
)

from .utils import(PASSWORD_RESET, VERIFY, send_otp, send_welcome_email, verify_otp,)


class Pagination(PageNumberPagination):
    page_size=2
    page_size_query_param= "page_size"
    max_page_size=10


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
        serializer.save()
        return Response(serializer.data)

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
        serializer.save(created_by= request.user, modified_by= request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ProjectDetailView(APIView):
    permission_classes=[IsAuthenticated]

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

    def _update(self, request, id, partial):
        project= self.get_object(id)
        serializer= ProjectSerializer(project, data= request.data, partial= partial, context={"request":request})
        serializer.is_valid(raise_exception= True)
        serializer.save(modified_by= request.user)
        return Response(serializer.data)

    def delete(self, request,id):
        project= self.get_object(id)
        project.project_status= "Inactive"
        project.modified_by= request.user
        project.save(update_fields=['project_status','modified_by','modified_at'])
        return Response({"detail": "Project Deactivated"}, status=status.HTTP_200_OK)

# class ProjectTypeListView(APIView):
#     permission_classes=[IsAuthenticated]
    
#     def get(self, request):
#         types=[]

#         for option, _label in Project.Project_Type:
#             types.append(option)

#         saved_types= Project.objects.exclude(project_type= None).values_list(
#             "project_type", flat= True
#         ).distinct()
#         for name in saved_types:
#             if name not in types:
#                 types.append(name)
#         return Response(types) 









