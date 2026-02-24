from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.scoring.utils import (
    get_recent_matches,
    get_match_players,
    get_selected_players_live_score,
)


class NBARecentMatchesAPIView(APIView):
    """
    API endpoint to retrieve recent NBA matches.
    
    Query Parameters:
        - days (optional): Number of days to look back (default: 7)
        
    Why: Provides a simple way to get recent matches for the frontend.
    The days parameter allows flexible time windows without requiring
    the frontend to handle date calculations.
    """
    
    @swagger_auto_schema(
        operation_description="Get recent NBA matches within specified days",
        manual_parameters=[
            openapi.Parameter(
                "days",
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description="Number of days to look back (default: 7)",
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of recent matches",
                examples={
                    "application/json": [
                        {
                            "match_id": "310823",
                            "date": "9.01.2026",
                            "status": "Final",
                            "home_team": "Boston Celtics",
                            "home_team_id": "1067",
                            "away_team": "Toronto Raptors",
                            "away_team_id": "1212"
                        }
                    ]
                }
            )
        }
    )
    def get(self, request):
        try:
            days = int(request.query_params.get("days", 7))
            
            # Validate days parameter
            if days < 1 or days > 90:
                return Response(
                    {"error": "days parameter must be between 1 and 90"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except ValueError:
            return Response(
                {"error": "days parameter must be a valid integer"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        matches = get_recent_matches(days)
        return Response(matches, status=status.HTTP_200_OK)


class NBAMatchPlayersAPIView(APIView):
    """
    API endpoint to retrieve all players for a specific match.
    
    Query Parameters:
        - match_id (required): The match identifier
        - date (required): Date in DD.MM.YYYY format
        
    Why: Date is now mandatory because we need it to query the GoalServe API
    for historical match data. This ensures we always get the correct player roster.
    """
    
    @swagger_auto_schema(
        operation_description="Get all players for a specific NBA match",
        manual_parameters=[
            openapi.Parameter(
                "match_id",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="The ID of the NBA match",
            ),
            openapi.Parameter(
                "date",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="Date in DD.MM.YYYY format (e.g., 09.01.2026)",
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of players",
                examples={
                    "application/json": [
                        {
                            "player_id": "4431893",
                            "name": "J. Battle",
                            "position": "F",
                            "team": "Toronto Raptors"
                        }
                    ]
                }
            ),
            400: "Bad Request - Missing required parameters"
        }
    )
    def get(self, request):
        match_id = request.query_params.get("match_id")
        date = request.query_params.get("date")
        
        # Validate required parameters
        if not match_id:
            return Response(
                {"error": "match_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not date:
            return Response(
                {"error": "date is required (format: DD.MM.YYYY)"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate date format
        try:
            from datetime import datetime
            datetime.strptime(date, "%d.%m.%Y")
        except ValueError:
            return Response(
                {"error": "date must be in DD.MM.YYYY format (e.g., 09.01.2026)"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        players = get_match_players(match_id, date)
        
        if not players:
            return Response(
                {"error": "No players found for this match. Match may not have started yet or data is unavailable."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(players, status=status.HTTP_200_OK)


class NBAMatchPlayerScoreAPIView(APIView):
    """
    API endpoint to retrieve scores for selected players in a match.
    
    Query Parameters:
        - match_id (required): The match identifier
        - player_ids (required): Comma-separated player IDs
        - date (required): Date in DD.MM.YYYY format
        
    Response:
        Returns a flat list of player score objects (NOT wrapped in match object)
        
    Why: This endpoint returns only the player scores as requested. Date is
    mandatory because GoalServe's API requires it for historical data queries.
    The response is a simple list format for easier frontend consumption.
    """
    
    @swagger_auto_schema(
        operation_description="Get scores for selected players in a match",
        manual_parameters=[
            openapi.Parameter(
                "match_id",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="The ID of the NBA match",
            ),
            openapi.Parameter(
                "player_ids",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="Comma-separated player IDs (e.g., '4431893,5107897')",
            ),
            openapi.Parameter(
                "date",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="Date in DD.MM.YYYY format (e.g., 09.01.2026)",
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of player scores",
                examples={
                    "application/json": [
                        {
                            "player_id": "4431893",
                            "name": "J. Battle",
                            "points": 2,
                            "rebounds": 2,
                            "assists": 1,
                            "minutes": "12"
                        },
                        {
                            "player_id": "5107897",
                            "name": "J. Mogbo",
                            "points": 6,
                            "rebounds": 3,
                            "assists": 3,
                            "minutes": "19"
                        }
                    ]
                }
            ),
            400: "Bad Request - Missing required parameters",
            404: "Not Found - No data available for specified players"
        }
    )
    def get(self, request):
        match_id = request.query_params.get("match_id")
        player_ids = request.query_params.get("player_ids", "")
        date = request.query_params.get("date")

        # Validate required parameters
        if not match_id:
            return Response(
                {"error": "match_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not date:
            return Response(
                {"error": "date is required (format: DD.MM.YYYY)"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not player_ids:
            return Response(
                {"error": "player_ids is required (comma-separated)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate date format
        try:
            from datetime import datetime
            datetime.strptime(date, "%d.%m.%Y")
        except ValueError:
            return Response(
                {"error": "date must be in DD.MM.YYYY format (e.g., 09.01.2026)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse and validate player IDs
        selected_ids = [
            pid.strip() for pid in player_ids.split(",") if pid.strip()
        ]
        
        if not selected_ids:
            return Response(
                {"error": "No valid player IDs provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get player scores - returns only list of player objects
        player_list = get_selected_players_live_score(match_id, selected_ids, date=date)
        
        if not player_list:
            return Response(
                {"error": "No scores found for the specified players. Match data may not be available yet."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(player_list, status=status.HTTP_200_OK)