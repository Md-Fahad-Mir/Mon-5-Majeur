# players/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from .utils import get_today_players, get_player_details, format_currency
from .serializers import PlayerSerializer, PlayerDetailSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.permissions import IsAuthenticated
from .serializers import TeamSelectionSerializer
from .models import TeamSelection
from apps.matches.models import MatchModel
from apps.scoring.utils import get_all_player_scores_for_date
from rest_framework.exceptions import ValidationError


class TeamSelectionAPIView(APIView):
    """Create or retrieve a user's selection for a given match."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=TeamSelectionSerializer)
    def post(self, request):
        serializer = TeamSelectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        match_id = serializer.validated_data['match']
        players = serializer.validated_data['selected_players']

        # Validate match exists
        try:
            match = MatchModel.objects.get(pk=match_id)
        except MatchModel.DoesNotExist:
            return Response({"detail": "Match not found."}, status=status.HTTP_404_NOT_FOUND)

        owner = request.user.userprofile

        # Upsert selection
        selection, created = TeamSelection.objects.update_or_create(
            match=match, owner=owner,
            defaults={'selected_players': players}
        )

        return Response({
            'match': match.id,
            'selected_players': selection.selected_players,
            'total_points': selection.total_points
        }, status=status.HTTP_200_OK)

    def get(self, request):
        match_id = request.query_params.get('match_id')
        owner = request.user.userprofile
        if not match_id:
            return Response({"detail": "match_id query param required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            selection = TeamSelection.objects.get(match_id=match_id, owner=owner)
        except TeamSelection.DoesNotExist:
            return Response({"detail": "Selection not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'match': selection.match.id,
            'selected_players': selection.selected_players,
            'total_points': selection.total_points
        }, status=status.HTTP_200_OK)

class TodayPlayersAPIView(APIView):
    """
    API endpoint to list all available players in today's games.
    Combines schedule, roster, and injuries.
    """

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "date",
                openapi.IN_QUERY,
                description="Date in DD.MM.YYYY format (e.g., 10.01.2026)",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "page",
                openapi.IN_QUERY,
                description="Page number for pagination",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={200: PlayerSerializer(many=True)}
    )
    def get(self, request):
        try:
            date_str = request.query_params.get("date")
            players = get_today_players(date_str)
            
            # Format prices
            for p in players:
                p['price'] = format_currency(p.get('price', 0))
            
            # Pagination
            paginator = PageNumberPagination()
            paginator.page_size = 10  # Set a reasonable page size
            result_page = paginator.paginate_queryset(players, request)
            
            serializer = PlayerSerializer(result_page, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )


class PlayerDetailAPIView(APIView):
    """
    Get full information about a player by his ID and team ID.
    """

    @swagger_auto_schema(responses={200: PlayerDetailSerializer()})
    def get(self, request, team_id, player_id):
        try:
            player = get_player_details(team_id, player_id)
            serializer = PlayerDetailSerializer(player)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )



from .serializers import MatchSelectionSerializer

class MatchSelectionAPIView(APIView):
    """
    Retrieve or update team selection for a specific league and match day.
    """
    permission_classes = [IsAuthenticated]
    


    def _parse_price(self, price_str):
        """Parse price string like '1.2M' or '500000' to float."""
        try:
            s = str(price_str).upper().replace(',', '')
            if 'M' in s:
                return float(s.replace('M', '')) * 1_000_000
            if 'K' in s:
                return float(s.replace('K', '')) * 1_000
            return float(s)
        except (ValueError, TypeError):
            return 0.0



    def _get_budget_details(self, league_budget_str, selected_players):
        # Parse budget
        try:
            budget_val = float(str(league_budget_str).upper().replace('M', '')) * 1_000_000
        except ValueError:
            budget_val = 100_000_000 # Default fallback
            
        total_price = sum(self._parse_price(player.get('price', 0)) for player in selected_players)
        return budget_val, budget_val - total_price

    @swagger_auto_schema(responses={200: MatchSelectionSerializer()})
    def get(self, request, league_id, match_day):
        """Get selection for a specific league match day."""
        try:
            owner = request.user.userprofile
            
            try:
                match = MatchModel.objects.get(
                    league_id=league_id,
                    match_day=match_day
                )
            except MatchModel.DoesNotExist:
                 return Response({"detail": "Match not found for this league/day."}, status=status.HTTP_404_NOT_FOUND)
    
            try:
                selection = TeamSelection.objects.get(match=match, owner=owner)
                # Create a copy to avoid mutating cache/db object if any
                selected_players = [dict(p) for p in selection.selected_players]
            except TeamSelection.DoesNotExist:
                selected_players = []
            
            # Integrate live scoring
            date_str = match.match_date.strftime("%d.%m.%Y")
            live_scores = get_all_player_scores_for_date(date_str)
            
            total_points = 0
            for p in selected_players:
                p_id = str(p.get('id'))
                if p_id in live_scores:
                    points = live_scores[p_id].get('points', 0)
                    p['score'] = points
                    total_points += points
                else:
                    p['score'] = 0
                
            max_bal_val, cur_bal_val = self._get_budget_details(match.league_id.team_budget, selected_players)
    
            # Format everything
            max_balance = format_currency(max_bal_val)
            current_balance = format_currency(cur_bal_val)
            
            # Format players
            for p in selected_players:
                raw_price = self._parse_price(p.get('price', 0))
                p['price'] = format_currency(raw_price)
    
            data = {
                'match_id': match.id,
                'match_day': match.match_day,
                'selected_players': selected_players,
                'total_points': total_points,
                'max_balance': max_balance,
                'current_balance': current_balance
            }
            return Response(data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(request_body=MatchSelectionSerializer)
    def post(self, request, league_id, match_day):
        """Update selection for a specific league match day."""
        try:
            owner = request.user.userprofile
            
            try:
                match = MatchModel.objects.get(
                    league_id=league_id,
                    match_day=match_day
                )
            except MatchModel.DoesNotExist:
                 return Response({"detail": "Match not found for this league/day."}, status=status.HTTP_404_NOT_FOUND)
                 
            # Check if match is locked/started
            if match.status != "scheduled":
                 return Response({"detail": "Cannot edit selection for active/completed match."}, status=status.HTTP_400_BAD_REQUEST)
    
            serializer = MatchSelectionSerializer(
                data=request.data, 
                context={'league_budget': match.league_id.team_budget}
            )
            serializer.is_valid(raise_exception=True)
            # We store the list of dicts directly
            selected_players = serializer.validated_data['selected_players']
    
            # Upsert
            selection, created = TeamSelection.objects.update_or_create(
                match=match, owner=owner,
                defaults={'selected_players': selected_players}
            )
            
            # Calculation for response
            # Create a copy for response formatting
            response_players = [dict(p) for p in selected_players]
            
            max_bal_val, cur_bal_val = self._get_budget_details(match.league_id.team_budget, response_players)
    
            max_balance = format_currency(max_bal_val)
            current_balance = format_currency(cur_bal_val)
            
            for p in response_players:
                raw_price = self._parse_price(p.get('price', 0))
                p['price'] = format_currency(raw_price)
    
            return Response({
                'match_id': match.id,
                'match_day': match.match_day,
                'selected_players': response_players,
                'total_points': selection.total_points,
                'max_balance': max_balance,
                'current_balance': current_balance
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
