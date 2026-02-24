from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterAPI, LoginAPI, LogoutAPIView, VerifyOTPView, UserProfileViewSet, ForgotPasswordAPI, VerifyForgotPasswordOTPView, ChangePasswordAPI, GoogleLogin, AppleLogin


# Set up the router for the UserProfile view
router = DefaultRouter()
router.register(r'UserProfiles', UserProfileViewSet, basename='userprofile')

urlpatterns = [
    path('auth/register/', RegisterAPI.as_view(), name='register'),
    path('auth/verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),  
    path('auth/login/', LoginAPI.as_view(), name='login'),  
    path('auth/logout/', LogoutAPIView.as_view(), name='logout'), 
    path('auth/forgot-password/', ForgotPasswordAPI.as_view(), name='forgot-password'),
    path('auth/verify-forgot-password-otp/', VerifyForgotPasswordOTPView.as_view(), name='verify-forgot-password-otp'),
    path('auth/change-password/', ChangePasswordAPI.as_view(), name='change-password'),
    path('djoser/', include('djoser.urls')),
    # Social login endpoints
    path('dj-rest-auth/google/', GoogleLogin.as_view(), name='google_login'),
    path('dj-rest-auth/apple/', AppleLogin.as_view(), name='apple_login'),

] + router.urls

