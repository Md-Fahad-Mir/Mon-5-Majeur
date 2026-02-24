from django.db import models
from django.conf import settings
from django.utils import timezone
import random

# Create your models here.
class UserProfile(models.Model):
    
    TEAM_LOGO_CHOICES = [
        ("paris_fc", "Paris FC"),
        ("lakers", "Lakers"),
        ("boston_celtics", "Boston Celtics"),
        ("chicago_bulls", "Chicago Bulls"),
        ("atlanta_hawks", "Atlanta Hawks"),
        ("golden_state_warriors", "Golden State Warriors"),
        # Add more logos as needed
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='userprofile')
    team_logo = models.CharField(max_length=100, choices=TEAM_LOGO_CHOICES, blank=True, null=True)
    team_name = models.CharField(max_length=100, unique=True, blank=False, null=False)
    favorite_team = models.CharField(max_length=50, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    accept_terms_conditions = models.BooleanField(default=False)
    recived_notifications = models.BooleanField(default=False)
    
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.team_name}"
        
    @property
    def email(self):
        return self.user.email
    
    @property
    def first_name(self):
        return self.user.first_name        
    

class PendingUser(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)  # temporarily store hashed or plain
    otp = models.CharField(max_length=6, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    OTP_TTL_SECONDS = 15 * 60  # 15 minutes

    def __str__(self):
        return self.email

    def generate_otp(self):
        self.otp = f"{random.randint(0, 999999):06d}"
        self.otp_created_at = timezone.now()
        self.save(update_fields=["otp", "otp_created_at"])
        return self.otp

    def verify_otp(self, otp):
        if not self.otp or not self.otp_created_at:
            return False, "No OTP requested"
        if (timezone.now() - self.otp_created_at).total_seconds() > self.OTP_TTL_SECONDS:
            return False, "OTP expired"
        if str(self.otp) != str(otp):
            return False, "Invalid OTP"
        return True, None


class ForgotPasswordRequest(models.Model):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    OTP_TTL_SECONDS = 15 * 60  # 15 minutes

    def __str__(self):
        return self.email

    def generate_otp(self):
        self.otp = f"{random.randint(0, 999999):06d}"
        self.otp_created_at = timezone.now()
        self.save(update_fields=["otp", "otp_created_at"])
        return self.otp

    def verify_otp(self, otp):
        if not self.otp or not self.otp_created_at:
            return False, "No OTP requested"
        if (timezone.now() - self.otp_created_at).total_seconds() > self.OTP_TTL_SECONDS:
            return False, "OTP expired"
        if str(self.otp) != str(otp):
            return False, "Invalid OTP"
        return True, None