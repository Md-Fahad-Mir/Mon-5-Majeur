from .models import TeamStatsModel
from rest_framework import serializers

class TeamStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamStatsModel
        fields = '__all__'