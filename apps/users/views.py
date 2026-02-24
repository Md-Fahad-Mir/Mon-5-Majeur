from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView 
from rest_framework_simplejwt.tokens import RefreshToken 
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import UserProfile, PendingUser, ForgotPasswordRequest
from .serializers import (
    UserProfileSerializer,
    RegisterSerializer,
    VerifyOTPSerializer,
    LoginSerializer,
    LogoutSerializer,
    ForgotPasswordSerializer,
    VerifyForgotPasswordOTPSerializer,
    ChangePasswordSerializer
)
from django.core.mail import send_mail
from django.conf import settings

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

from allauth.socialaccount.providers.apple.views import AppleOAuth2Adapter
from allauth.socialaccount.providers.apple.client import AppleOAuth2Client

from dj_rest_auth.registration.views import SocialLoginView

from core.custom_permission import IsOwner


class UserProfileViewSet(ModelViewSet):
    """
    ViewSet for managing user profiles.
    
    Provides CRUD operations for authenticated users to manage their profile data.
    """
    permission_classes = [IsAuthenticated, IsOwner]
    serializer_class = UserProfileSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return UserProfile.objects.none()
        return UserProfile.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        if UserProfile.objects.filter(user=request.user).exists():
            return Response(
                {"error": "this user already created a profile"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @swagger_auto_schema(
        operation_summary="List user profiles",
        operation_description="Retrieve all profiles for the authenticated user.",
        tags=['User Profile'],
        responses={
            200: UserProfileSerializer(many=True),
            401: "Unauthorized - Authentication required"
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_summary="Retrieve user profile",
        operation_description="Get details of a specific user profile.",
        tags=['User Profile'],
        responses={
            200: UserProfileSerializer(),
            401: "Unauthorized - Authentication required",
            404: "Profile not found"
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_summary="Create user profile",
        operation_description="Create a new profile for the authenticated user.",
        tags=['User Profile'],
        request_body=UserProfileSerializer,
        responses={
            201: UserProfileSerializer(),
            400: "Bad Request - Invalid data",
            401: "Unauthorized - Authentication required"
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_summary="Update user profile",
        operation_description="Update all fields of a user profile.",
        tags=['User Profile'],
        request_body=UserProfileSerializer,
        responses={
            200: UserProfileSerializer(),
            400: "Bad Request - Invalid data",
            401: "Unauthorized - Authentication required",
            404: "Profile not found"
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_summary="Partial update user profile",
        operation_description="Update specific fields of a user profile.",
        tags=['User Profile'],
        request_body=UserProfileSerializer,
        responses={
            200: UserProfileSerializer(),
            400: "Bad Request - Invalid data",
            401: "Unauthorized - Authentication required",
            404: "Profile not found"
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_summary="Delete user profile",
        operation_description="Delete a user profile.",
        tags=['User Profile'],
        responses={
            204: "Profile deleted successfully",
            401: "Unauthorized - Authentication required",
            404: "Profile not found"
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)




class RegisterAPI(APIView):
    """
    Register a new user and send OTP for verification.
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_summary="Register new user",
        operation_description="Register a new user account. An OTP will be sent to the provided email for verification. The OTP expires in 15 minutes.",
        tags=['Authentication'],
        request_body=RegisterSerializer,
        responses={
            201: openapi.Response(
                description="OTP sent successfully",
                examples={
                    "application/json": {
                        "message": "OTP sent to your email. Verify to complete registration."
                    }
                }
            ),
            400: openapi.Response(
                description="Bad Request",
                examples={
                    "application/json": {
                        "error": "User already exists."
                    }
                }
            )
        }
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        User = get_user_model()
        if User.objects.filter(email=email).exists():
            return Response({"error": "User already exists."}, status=status.HTTP_400_BAD_REQUEST)

        pending_user, created = PendingUser.objects.get_or_create(email=email)
        pending_user.password = password  
        otp = pending_user.generate_otp()  
        pending_user.save()

        send_mail(
            subject="Your MON5MAJEUR verification code",
            message=f"Your OTP code is {otp}. It expires in 15 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )
        return Response({"message": "OTP sent to your email. Verify to complete registration."}, status=status.HTTP_201_CREATED)

class VerifyOTPView(APIView):
    """
    Verify OTP and complete user registration.
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_summary="Verify OTP code",
        operation_description="Verify the 6-digit OTP code sent to your email to complete user registration. OTP codes expire after 15 minutes.",
        tags=['Authentication'],
        request_body=VerifyOTPSerializer,
        responses={
            200: openapi.Response(
                description="Registration completed",
                examples={
                    "application/json": {
                        "message": "Registration complete. You can now log in."
                    }
                }
            ),
            400: openapi.Response(
                description="Bad Request - Invalid or expired OTP",
                examples={
                    "application/json": {
                        "error": "Invalid or expired OTP."
                    }
                }
            ),
            404: openapi.Response(
                description="Pending registration not found",
                examples={
                    "application/json": {
                        "error": "Pending registration not found."
                    }
                }
            )
        }
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]

        pending = PendingUser.objects.filter(email=email).first()
        if not pending:
            return Response({"error": "Pending registration not found."}, status=status.HTTP_404_NOT_FOUND)

        ok, msg = pending.verify_otp(otp)
        if not ok:
            return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)

        raw_password = pending.password

        User = get_user_model()
        base_username = email.split("@")[0].lower()
        username = base_username
        counter = 0
        while User.objects.filter(username=username).exists():
            counter += 1
            username = f"{base_username}{counter}"

        user = User.objects.create_user(username=username, email=email, password=raw_password)
        user.is_active = True
        user.save()
        pending.delete()

        return Response({"message": "Registration complete. You can now log in."}, status=status.HTTP_200_OK)

class LoginAPI(APIView):
    """
    Login with email and password to receive JWT tokens.
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_summary="User login",
        operation_description="Authenticate with email and password to receive JWT access and refresh tokens. Use the access token for authenticated API requests.",
        tags=['Authentication'],
        request_body=LoginSerializer,
        responses={
            200: openapi.Response(
                description="Login successful",
                examples={
                    "application/json": {
                        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTY0...",
                        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNjQ...",
                        "user": {
                            "user_id": 1,
                            "email": "john.doe@example.com",
                            "username": "johndoe",
                            "is_superuser": False
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="Bad Request - Missing credentials",
                examples={
                    "application/json": {
                        "email": ["This field is required."],
                        "password": ["This field is required."]
                    }
                }
            ),
            401: openapi.Response(
                description="Unauthorized - Invalid credentials",
                examples={
                    "application/json": {
                        "error": "Invalid credentials."
                    }
                }
            )
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            user = get_user_model().objects.get(email=email)
        except get_user_model().DoesNotExist:
            return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.check_password(password):
            return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        return Response({
            'refresh': str(refresh),
            'access': str(access_token),
            'user': {
                'user_id': user.id,
                'email': user.email,
                'username': user.username,
                'is_superuser': user.is_superuser
            }
        })

class LogoutAPIView(APIView):
    """
    Logout by blacklisting the refresh token.
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_summary="User logout",
        operation_description="Logout by blacklisting the JWT refresh token. After logout, the refresh token cannot be used to obtain new access tokens.",
        tags=['Authentication'],
        request_body=LogoutSerializer,
        responses={
            200: openapi.Response(
                description="Logout successful",
                examples={
                    "application/json": {
                        "message": "Logged out successfully"
                    }
                }
            ),
            400: openapi.Response(
                description="Bad Request - Invalid token",
                examples={
                    "application/json": {
                        "error": "Token is invalid or expired"
                    }
                }
            ),
            401: "Unauthorized - Authentication required"
        }
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            refresh_token = serializer.validated_data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()  
            return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ForgotPasswordAPI(APIView):
    """
    Request password reset and send OTP to email.
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_summary="Forgot password",
        operation_description="Request password reset. An OTP will be sent to the provided email. OTP expires in 15 minutes.",
        tags=['Authentication'],
        request_body=ForgotPasswordSerializer,
        responses={
            200: openapi.Response(
                description="OTP sent successfully",
                examples={
                    "application/json": {
                        "message": "OTP sent to your email."
                    }
                }
            ),
            404: openapi.Response(
                description="User not found",
                examples={
                    "application/json": {
                        "error": "User with this email does not exist."
                    }
                }
            )
        }
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data["email"]
        
        User = get_user_model()
        if not User.objects.filter(email=email).exists():
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)
        
        forgot_request, created = ForgotPasswordRequest.objects.get_or_create(email=email)
        otp = forgot_request.generate_otp()
        
        send_mail(
            subject="Your MON5MAJEUR password reset code",
            message=f"Your OTP code is {otp}. It expires in 15 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )
        return Response({"message": "OTP sent to your email."}, status=status.HTTP_200_OK)

class VerifyForgotPasswordOTPView(APIView):
    """
    Verify OTP for forgot password request.
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_summary="Verify forgot password OTP",
        operation_description="Verify the OTP sent to your email for password reset.",
        tags=['Authentication'],
        request_body=VerifyForgotPasswordOTPSerializer,
        responses={
            200: openapi.Response(
                description="OTP verified successfully",
                examples={
                    "application/json": {
                        "message": "OTP verified successfully. You can now reset your password."
                    }
                }
            ),
            400: openapi.Response(
                description="Bad Request - Invalid or expired OTP",
                examples={
                    "application/json": {
                        "error": "Invalid OTP"
                    }
                }
            ),
            404: openapi.Response(
                description="Password reset request not found",
                examples={
                    "application/json": {
                        "error": "Password reset request not found."
                    }
                }
            )
        }
    )
    def post(self, request):
        serializer = VerifyForgotPasswordOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]
        
        forgot_request = ForgotPasswordRequest.objects.filter(email=email).first()
        if not forgot_request:
            return Response({"error": "Password reset request not found."}, status=status.HTTP_404_NOT_FOUND)
        
        ok, msg = forgot_request.verify_otp(otp)
        if not ok:
            return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({"message": "OTP verified successfully. You can now reset your password."}, status=status.HTTP_200_OK)


class ChangePasswordAPI(APIView):
    """
    Change password after email verification.
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_summary="Change password",
        operation_description="Change your password after email verification. Requires new_password and confirm_password fields.",
        tags=['Authentication'],
        request_body=ChangePasswordSerializer,
        responses={
            200: openapi.Response(
                description="Password changed successfully",
                examples={
                    "application/json": {
                        "message": "Password changed successfully."
                    }
                }
            ),
            400: openapi.Response(
                description="Bad Request",
                examples={
                    "application/json": {
                        "error": "Passwords do not match."
                    }
                }
            ),
            401: "Unauthorized - Authentication required"
        }
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data["email"]
        new_password = serializer.validated_data["new_password"]
        
        User = get_user_model()
        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)
        
        user.set_password(new_password)
        user.save()
        
        return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)


# Google 
class GoogleLogin(SocialLoginView):
    """
    Google OAuth2 social authentication.
    
    Authenticate users via Google OAuth2. Returns JWT tokens upon successful authentication.
    """
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client


# Apple
class AppleLogin(SocialLoginView):
    """
    Apple OAuth2 social authentication.
    
    Authenticate users via Apple OAuth2. Returns JWT tokens upon successful authentication.
    """
    adapter_class = AppleOAuth2Adapter
    client_class = AppleOAuth2Client
