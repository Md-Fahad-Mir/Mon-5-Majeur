from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import TeamStatsView

urlpatterns = [
    path('teams/<int:team_id>/stats/', TeamStatsView.as_view(), name='team-stats'),
]