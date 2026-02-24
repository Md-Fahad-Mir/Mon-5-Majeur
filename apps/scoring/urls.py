from django.urls import path
from .views import (
    NBARecentMatchesAPIView,
    NBAMatchPlayersAPIView,
    NBAMatchPlayerScoreAPIView,
)

urlpatterns = [
    path("nba/matches/recent/", NBARecentMatchesAPIView.as_view()),
    path("nba/match/players/", NBAMatchPlayersAPIView.as_view()),
    path("nba/match/player-scores/", NBAMatchPlayerScoreAPIView.as_view()),
]
