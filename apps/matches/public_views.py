from django.shortcuts import render
from apps.matches.models import PublicMatchModel, PublicMatchScoreModel, PublicLeagueSeason, PublicPlayoffQualification
from apps.matches.serializers import (
    PublicMatchSerializer, PublicMatchScoreSerializer, PublicLeagueSeasonSerializer, 
    PublicPlayoffQualificationSerializer
)
from apps.matches.services import MatchSchedulerService

from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import action
from django.db.models import Sum
from django.utils import timezone
from django.db.models import Q
from apps.scoring.utils import get_all_player_scores_for_date

from apps.public_leagues.models import PublicLeagueModel


class PublicMatchListView(ListAPIView):
    serializer_class = PublicMatchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        league_id = self.request.query_params.get('league_id')
        match_type = self.request.query_params.get('match_type')  # 'regular_season' or 'playoffs'
        
        queryset = PublicMatchModel.objects.all()
        
        if league_id:
            queryset = queryset.filter(league_id=league_id)
        
        if match_type:
            queryset = queryset.filter(match_type=match_type)
        
        return queryset.order_by('-match_date')


class PublicUserTodayMatchesView(ListAPIView):
    """Get all public matches for the logged-in user scheduled for today."""
    serializer_class = PublicMatchSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response([])
            
        user_profile = self.request.user.userprofile
        
        # Initial queryset within the date range
        base_queryset = PublicMatchModel.objects.filter(
            Q(match_date__date__in=[today_utc, tomorrow_utc]) &
            (Q(pairs__player_a=user_profile) | Q(pairs__player_b=user_profile))
        ).distinct()

        # Group by league and find the maximum match_day for each league
        from django.db.models import Max
        # .order_by() clears default ordering which can interfere with values().annotate() grouping
        league_latest_days = base_queryset.order_by().values('league_id').annotate(max_day=Max('match_day'))
        
        # Build a Q object to filter only those specific (league, match_day) combinations
        filter_q = Q()
        for item in league_latest_days:
            filter_q |= Q(league_id=item['league_id'], match_day=item['max_day'])
        
        if not filter_q:
            return Response([])

        final_queryset = base_queryset.filter(filter_q).order_by('match_date')
        
        serializer = self.get_serializer(final_queryset, many=True)
        return Response(serializer.data)


class PublicMatchDetailView(APIView):
    """Get a specific public match by league and match_day."""
    permission_classes = [IsAuthenticated]

    def get(self, request, league_id, match_day):
        try:
            match = PublicMatchModel.objects.get(league_id=league_id, match_day=match_day)
        except PublicMatchModel.DoesNotExist:
            return Response({"detail": "Match not found."}, status=status.HTTP_404_NOT_FOUND)

        # Integrate live scoring
        date_str = match.match_date.strftime("%d.%m.%Y")
        live_scores = get_all_player_scores_for_date(date_str)
        
        # We'll use a local mapping to avoid multiple DB hits for the same selection
        # owner_id -> total_live_points
        owner_live_scores = {}
        
        # 1. Calculate live scores for all participants based on their selections
        from apps.players.models import PublicTeamSelection
        from apps.users.models import UserProfile
        
        # Prefetch users to avoid N+1 queries in the loop
        selections = match.public_selections.all().select_related('owner__user')
        
        for selection in selections:
            total = 0
            for pid in selection.selected_players:
                p_id_str = str(pid)
                if p_id_str in live_scores:
                    total += live_scores[p_id_str].get('points', 0)
            owner_live_scores[selection.owner_id] = total

        serializer = PublicMatchSerializer(match)
        data = serializer.data
        
        # 2. Update player_scores in the response
        participant_scores = []
        for selection in selections:
            user = selection.owner
            
            # Create a breakdown of individual player scores for this participant
            p_breakdown = []
            for p_data in (selection.selected_players or []):
                p_id_str = str(p_data.get('id'))
                p_breakdown.append({
                    "id": p_id_str,
                    "name": p_data.get('name'),
                    "position": p_data.get('position'),
                    "score": live_scores.get(p_id_str, {}).get('points', 0)
                })

            participant_scores.append({
                "player_id": user.id,
                "team_name": user.team_name,
                "username": user.user.username,
                "total_points": owner_live_scores.get(user.id, 0),
                "selection": p_breakdown
            })
        
        # If we have live scores, override/populate player_scores
        if participant_scores:
            data['player_scores'] = participant_scores

        # 3. Update pairs in the response with live scores
        for pair in data.get('pairs', []):
            pair['score_a'] = owner_live_scores.get(pair['player_a_id'], 0)
            if pair.get('player_b_id'):
                pair['score_b'] = owner_live_scores.get(pair['player_b_id'], 0)
            else:
                pair['score_b'] = 0

        return Response(data, status=status.HTTP_200_OK)


class PublicLeagueStandingsView(APIView):
    """Get current standings for a public league."""
    permission_classes = [IsAuthenticated]

    def get(self, request, league_id):
        try:
            league = PublicLeagueModel.objects.get(pk=league_id)
        except PublicLeagueModel.DoesNotExist:
            return Response(
                {"detail": "League not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        match_type = request.query_params.get('match_type', 'regular_season')
        
        standings = MatchSchedulerService.get_public_league_standings(league, match_type)
        
        return Response({
            "league_id": league.id,
            "league_name": league.leauge_name,
            "match_type": match_type,
            "standings": standings
        }, status=status.HTTP_200_OK)


class PublicLeagueSeasonView(APIView):
    """Get season information for a public league."""
    permission_classes = [IsAuthenticated]

    def get(self, request, league_id):
        try:
            league = PublicLeagueModel.objects.get(pk=league_id)
        except PublicLeagueModel.DoesNotExist:
            return Response(
                {"detail": "League not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            season = league.season
            serializer = PublicLeagueSeasonSerializer(season)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except PublicLeagueSeason.DoesNotExist:
            return Response(
                {"detail": "Season not initialized for this league."},
                status=status.HTTP_404_NOT_FOUND
            )


class PublicPlayoffQualifiersView(ListAPIView):
    """Get playoff qualifiers for a public league."""
    serializer_class = PublicPlayoffQualificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        league_id = self.kwargs.get('league_id')
        return PublicPlayoffQualification.objects.filter(league_id=league_id).order_by('regular_season_rank')

    def get(self, request, league_id):
        try:
            league = PublicLeagueModel.objects.get(pk=league_id)
        except PublicLeagueModel.DoesNotExist:
            return Response(
                {"detail": "League not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            "league_id": league.id,
            "league_name": league.leauge_name,
            "qualifiers": serializer.data
        }, status=status.HTTP_200_OK)


class PublicLeagueWinnerView(APIView):
    """Get playoff winner of a public league."""
    permission_classes = [IsAuthenticated]

    def get(self, request, league_id):
        try:
            league = PublicLeagueModel.objects.get(pk=league_id)
        except PublicLeagueModel.DoesNotExist:
            return Response(
                {"detail": "League not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        winner = MatchSchedulerService.get_public_playoff_winner(league)
        
        if not winner:
            return Response(
                {"detail": "Playoffs not completed or no matches found."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            "league_id": league.id,
            "league_name": league.leauge_name,
            "winner_id": winner.id,
            "winner_team_name": winner.team_name,
            "winner_username": winner.user.username
        }, status=status.HTTP_200_OK)
