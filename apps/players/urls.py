from django.urls import path
from .views import TodayPlayersAPIView, PlayerDetailAPIView, TeamSelectionAPIView, MatchSelectionAPIView
from .public_views import PublicMatchSelectionAPIView
from django.urls import include

urlpatterns = [
    path('players-today/', TodayPlayersAPIView.as_view(), name='player-list'),
    path("player-details/<int:team_id>/<int:player_id>/", PlayerDetailAPIView.as_view(), name="player-detail")
]

urlpatterns += [
    path('private-leagues/<int:league_id>/<int:match_day>/players-selection/', MatchSelectionAPIView.as_view(), name='league-match-selection'),
    path('public-leagues/<int:league_id>/<int:match_day>/players-selection/', PublicMatchSelectionAPIView.as_view(), name='public-league-match-selection'),
]