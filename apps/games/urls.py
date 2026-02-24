from django.urls import path
from .views import TodayGamesView

urlpatterns = [
    path('games-today/', TodayGamesView.as_view(), name='today-games'),
]