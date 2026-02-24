from .serializers import TeamStatsSerializer
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .models import TeamStatsModel


# Create your views here.

class TeamStatsView(APIView):
    @swagger_auto_schema()
    def get(self, request, team_id):
        team_stats = TeamStatsModel.objects.filter(team_id=team_id)
        serializer = TeamStatsSerializer(team_stats, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
