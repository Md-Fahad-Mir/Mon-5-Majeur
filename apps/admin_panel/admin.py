from django.contrib import admin
from .models import TokenModel, JerseyModel, FAQModel, BonusModel
# Register your models here.

admin.site.register(TokenModel)
admin.site.register(JerseyModel)
admin.site.register(FAQModel)
admin.site.register(BonusModel)