from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response

# Create your views here.
class LeaderboardView(APIView):
    def get(self, request):
        return Response({"message": "Leaderboard endpoint"}, status=status.HTTP_200_OK)




















