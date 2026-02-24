from django.db import models

# Create your models here.
class FAQModel(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()

    def __str__(self):
        return self.question
    

class BonusModel(models.Model):
    bonus_name = models.CharField(max_length=100, unique=True, blank=False, null=False)
    bonus_type = models.CharField(max_length=50, blank=True, null=True)
    price = models.IntegerField(default=100, blank=False, null=False)

    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField(blank=False, null=False)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=False)

    def __str__(self):
        return self.bonus_name
    
class TokenModel(models.Model):
    token_name = models.CharField(max_length=100, unique=True, blank=False, null=False)
    token = models.IntegerField(default=100, blank=False, null=False)
    price = models.IntegerField(default=100, blank=False, null=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expired_at = models.DateTimeField(blank=False, null=False)
    status = models.BooleanField(default=False)

    def __str__(self):
        return self.token_name



class JerseyModel(models.Model):
    jersey_name = models.CharField(max_length=100, unique=True, blank=False, null=False)
    jersey_image = models.ImageField(upload_to='jerseys/', max_length=255, blank=False, null=False)

    def __str__(self):
        return self.jersey_name
    

class LegalNoticeModel(models.Model):
    content = models.TextField()

    def __str__(self):
        return f"Legal Notice {self.id}"
    
class PrivacyPolicyModel(models.Model):
    content = models.TextField()

    def __str__(self):
        return f"Privacy Policy {self.id}"
    
class AboutusModel(models.Model):
    content = models.TextField()

    def __str__(self):
        return f"About Us {self.id}"