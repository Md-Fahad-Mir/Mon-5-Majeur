from .views import (
    MatchListView,
    MatchDetailView,
    LeagueStandingsView,
    LeagueSeasonView,
    PlayoffQualifiersView,
    LeagueWinnerView,
    UserTodayMatchesView
)
from .public_views import (
    PublicMatchListView,
    PublicMatchDetailView,
    PublicLeagueStandingsView,
    PublicLeagueSeasonView,
    PublicPlayoffQualifiersView,
    PublicLeagueWinnerView,
    PublicUserTodayMatchesView
)
from django.urls import path

urlpatterns = [
    # Private Match endpoints
    path('private-leagues/matches/', MatchListView.as_view(), name='match-list'),
    path('private-leagues/matches/my-matches-today/', UserTodayMatchesView.as_view(), name='my-matches-today'),
    path('private-leagues/matches/<int:league_id>/<int:match_day>/', MatchDetailView.as_view(), name='match-detail'),
    
    # Private League standings and season info
    path('private-leagues/<int:league_id>/standings/', LeagueStandingsView.as_view(), name='league-standings'),
    path('private-leagues/<int:league_id>/season/', LeagueSeasonView.as_view(), name='league-season'),
    
    # Private Playoff endpoints
    path('private-leagues/<int:league_id>/playoff-qualifiers/', PlayoffQualifiersView.as_view(), name='playoff-qualifiers'),
    path('private-leagues/<int:league_id>/winner/', LeagueWinnerView.as_view(), name='league-winner'),
    
    # Public Match endpoints
    path('public-leagues/matches/', PublicMatchListView.as_view(), name='public-match-list'),
    path('public-leagues/matches/my-matches-today/', PublicUserTodayMatchesView.as_view(), name='public-my-matches-today'),
    path('public-leagues/matches/<int:league_id>/<int:match_day>/', PublicMatchDetailView.as_view(), name='public-match-detail'),
    
    # Public League standings and season info
    path('public-leagues/<int:league_id>/standings/', PublicLeagueStandingsView.as_view(), name='public-league-standings'),
    path('public-leagues/<int:league_id>/season/', PublicLeagueSeasonView.as_view(), name='public-league-season'),
    
    # Public Playoff endpoints
    path('public-leagues/<int:league_id>/playoff-qualifiers/', PublicPlayoffQualifiersView.as_view(), name='public-playoff-qualifiers'),
    path('public-leagues/<int:league_id>/winner/', PublicLeagueWinnerView.as_view(), name='public-league-winner'),
]