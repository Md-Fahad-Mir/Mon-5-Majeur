from django.contrib import admin
from .models import UserProfile,PendingUser

# Register your models here.
admin.site.register(UserProfile)
admin.site.register(PendingUser)