from .views import PublicLeagueViewSet
from django.urls import path
from rest_framework.routers import DefaultRouter
from django.urls import include

router = DefaultRouter()

router.register(r'public-leagues', PublicLeagueViewSet, basename='public-leagues')

urlpatterns = [
    path('', include(router.urls)),
]
