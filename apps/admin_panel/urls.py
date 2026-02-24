from .views import FAQViewSet, BonusViewSet, JerseyViewSet, LegalNoticeViewSet, PrivacyPolicyViewSet, AboutusViewSet, TokenViewSet
from rest_framework.routers import DefaultRouter
from django.urls import path, include

router = DefaultRouter()

router.register(r'faqs', FAQViewSet, basename='faq')
router.register(r'bonuses', BonusViewSet, basename='bonus')
router.register(r'tokens', TokenViewSet, basename='token')
router.register(r'jerseys', JerseyViewSet, basename='jersey')
router.register(r'legal-notices', LegalNoticeViewSet, basename='legalnotice')
router.register(r'privacy-policies', PrivacyPolicyViewSet, basename='privacypolicy')
router.register(r'aboutus', AboutusViewSet, basename='aboutus')



urlpatterns = [
    path('', include(router.urls)),
]