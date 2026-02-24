from .views import PrivateLeagueViewSet
from django.urls import path
from rest_framework.routers import DefaultRouter
from django.urls import include
router = DefaultRouter()


router.register(r'private-leagues', PrivateLeagueViewSet, basename='private-leagues')


urlpatterns = [
    path('', include(router.urls)),
]