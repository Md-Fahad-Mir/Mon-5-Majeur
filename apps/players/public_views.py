# players/public_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils import format_currency
from rest_framework.permissions import IsAuthenticated
from .serializers import PublicMatchSelectionSerializer
from .models import PublicTeamSelection
from apps.matches.models import PublicMatchModel
from apps.scoring.utils import get_all_player_scores_for_date
from rest_framework.exceptions import ValidationError
from drf_yasg.utils import swagger_auto_schema


class PublicMatchSelectionAPIView(APIView):
    """
    Retrieve or update team selection for a specific public league and match day.
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

    @swagger_auto_schema(responses={200: PublicMatchSelectionSerializer()})
    def get(self, request, league_id, match_day):
        """Get selection for a specific public league match day."""
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=401)
            
        try:
            owner = request.user.userprofile
            
            try:
                match = PublicMatchModel.objects.get(
                    league_id=league_id,
                    match_day=match_day
                )
            except PublicMatchModel.DoesNotExist:
                 return Response({"detail": "Match not found for this league/day."}, status=status.HTTP_404_NOT_FOUND)
    
            try:
                selection = PublicTeamSelection.objects.get(match=match, owner=owner)
                # Create a copy to avoid mutating cache/db object if any
                selected_players = [dict(p) for p in selection.selected_players]
            except PublicTeamSelection.DoesNotExist:
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

    @swagger_auto_schema(request_body=PublicMatchSelectionSerializer)
    def post(self, request, league_id, match_day):
        """Update selection for a specific public league match day."""
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=401)
            
        try:
            owner = request.user.userprofile
            
            try:
                match = PublicMatchModel.objects.get(
                    league_id=league_id,
                    match_day=match_day
                )
            except PublicMatchModel.DoesNotExist:
                 return Response({"detail": "Match not found for this league/day."}, status=status.HTTP_404_NOT_FOUND)
                 
            # Check if match is locked/started
            if match.status != "scheduled":
                 return Response({"detail": "Cannot edit selection for active/completed match."}, status=status.HTTP_400_BAD_REQUEST)
    
            serializer = PublicMatchSelectionSerializer(
                data=request.data, 
                context={'league_budget': match.league_id.team_budget}
            )
            serializer.is_valid(raise_exception=True)
            # We store the list of dicts directly
            selected_players = serializer.validated_data['selected_players']
    
            # Upsert
            selection, created = PublicTeamSelection.objects.update_or_create(
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
