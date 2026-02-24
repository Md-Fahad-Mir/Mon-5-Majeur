from .models import FAQModel, BonusModel, JerseyModel, LegalNoticeModel, PrivacyPolicyModel, AboutusModel, TokenModel
from .serializers import FAQSerializer, BonusSerializer, JerseySerializer, LegalNoticeSerializer, PrivacyPolicySerializer, AboutusSerializer, TokenSerializer
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter
# Create your views here.

class FAQViewSet(viewsets.ModelViewSet):
    queryset = FAQModel.objects.all()
    serializer_class = FAQSerializer

class BonusViewSet(viewsets.ModelViewSet):
    queryset = BonusModel.objects.all()
    serializer_class = BonusSerializer
    filter_backends = [SearchFilter] 
    search_fields = ['bonus_name', 'bonus_type']    

    @action(detail=False, methods=['get'])
    def total_bonuses(self, request):
        total = BonusModel.objects.count()
        return Response({"total_bonuses": total})

    @action(detail=False, methods=['get'])
    def active_bonuses(self, request):
        active = BonusModel.objects.filter(status=True).count()
        return Response({"active_bonuses": active})
    
    @action(detail=False, methods=['get'])
    def search_bonuses(self, request):
        query = request.query_params.get('search', None)
        if query:
            bonuses = BonusModel.objects.filter(bonus_name__icontains=query)
            serializer = BonusSerializer(bonuses, many=True)
            return Response({"search_bonuses": serializer.data})
        else:
            return Response({"detail": "No search query provided."}, status=400)
        

class TokenViewSet(viewsets.ModelViewSet):
    queryset = TokenModel.objects.all()
    serializer_class = TokenSerializer
    filter_backends = [SearchFilter]
    search_fields = ['token_name']

    @action(detail=False, methods=['get'])
    def total_token_packs(self, request):
        total = TokenModel.objects.count()
        return Response({"total_token_packs": total})
    
    @action(detail=False, methods=['get'])
    def active_token_packs(self, request):
        active = TokenModel.objects.filter(status=True).count()
        return Response({"active_token_packs": active})
    
    @action(detail=False, methods=['get'])
    def search_token(self, request):
        query = request.query_params.get('search', None)
        if query:
            token = TokenModel.objects.filter(token_name__icontains=query)
            serializer = TokenSerializer(token, many=True)
            return Response({"search_token": serializer.data})
        else:
            return Response({"detail": "No search query provided."}, status=400)

class JerseyViewSet(viewsets.ModelViewSet):
    queryset = JerseyModel.objects.all()
    serializer_class = JerseySerializer

class LegalNoticeViewSet(viewsets.ModelViewSet):
    queryset = LegalNoticeModel.objects.all()
    serializer_class = LegalNoticeSerializer

class PrivacyPolicyViewSet(viewsets.ModelViewSet):
    queryset = PrivacyPolicyModel.objects.all()
    serializer_class = PrivacyPolicySerializer

class AboutusViewSet(viewsets.ModelViewSet):
    queryset = AboutusModel.objects.all()
    serializer_class = AboutusSerializer