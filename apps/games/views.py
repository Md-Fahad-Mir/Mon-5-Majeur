from .utils import get_today_games
from .serializers import GameSerializer

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Create your views here.
class TodayGamesView(APIView):
    """API view to fetch today's NBA games from GoalServe API.
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
        ],
        responses={200: GameSerializer(many=True)}
    )
    def get(self, request):
        try:
            date_str = request.query_params.get("date")
            games = get_today_games(date_str)
            serializer = GameSerializer(games, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
