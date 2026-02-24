from .models import FAQModel, BonusModel, JerseyModel, LegalNoticeModel, PrivacyPolicyModel, AboutusModel, TokenModel
from rest_framework import serializers

class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQModel
        fields = ['id', 'question', 'answer']
        read_only_fields = ['id']

class BonusSerializer(serializers.ModelSerializer):
    class Meta:
        model = BonusModel
        fields = '__all__'

class TokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = TokenModel
        fields = '__all__'

class JerseySerializer(serializers.ModelSerializer):
    class Meta:
        model = JerseyModel
        fields = '__all__'

class LegalNoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalNoticeModel
        fields = '__all__'

class PrivacyPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacyPolicyModel
        fields = '__all__'

class AboutusSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutusModel
        fields = '__all__'

