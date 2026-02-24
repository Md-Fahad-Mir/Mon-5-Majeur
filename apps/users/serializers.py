from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "user", "id", "balance", "email", "first_name"]
    
    def get_first_name(self, obj):
        """Return first_name if exists, otherwise generate from email"""
        if obj.user.first_name:
            return obj.user.first_name
        # Generate name from email (part before @)
        email = obj.user.email
        if email:
            name = email.split('@')[0]
            return name.capitalize()
        return ""


# Registration Serializers
class RegisterSerializer(serializers.Serializer):
    """Serializer for user registration"""
    email = serializers.EmailField(
        required=True,
        help_text="User's email address (e.g., john.doe@example.com)"
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="User's password - minimum 8 characters recommended (e.g., SecurePass123!)"
    )

    def validate_email(self, value):
        """Validate that email is not already registered"""
        User = get_user_model()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value


class VerifyOTPSerializer(serializers.Serializer):
    """Serializer for OTP verification"""
    email = serializers.EmailField(
        required=True,
        help_text="Email address used during registration (e.g., john.doe@example.com)"
    )
    otp = serializers.CharField(
        required=True,
        max_length=6,
        min_length=6,
        help_text="6-digit OTP code sent to your email (e.g., 123456)"
    )


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField(
        required=True,
        help_text="User's email address (e.g., john.doe@example.com)"
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="User's password (e.g., SecurePass123!)"
    )


class LogoutSerializer(serializers.Serializer):
    """Serializer for user logout"""
    refresh_token = serializers.CharField(
        required=True,
        help_text="JWT refresh token to blacklist (e.g., eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...)"
    )


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for forgot password request"""
    email = serializers.EmailField(
        required=True,
        help_text="User's email address (e.g., john.doe@example.com)"
    )

class VerifyForgotPasswordOTPSerializer(serializers.Serializer):
    """Serializer for verifying OTP during forgot password"""
    email = serializers.EmailField(
        required=True,
        help_text="Email address used during forgot password request (e.g., john.doe@example.com)"
    )
    otp = serializers.CharField(
        required=True,
        max_length=6,
        min_length=6,
        help_text="6-digit OTP code sent to your email (e.g., 123456)"
    )

class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password after email verification"""
    email = serializers.EmailField(
        required=True,
        help_text="User's email address (e.g., john.doe@example.com)"
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="New password for your account (e.g., NewSecurePass123!)"
    )
    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="Confirm your new password (e.g., NewSecurePass123!)"
    )

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data