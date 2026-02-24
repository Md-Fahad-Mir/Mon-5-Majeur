from rest_framework import serializers

class GameSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    home_team = serializers.CharField(max_length=100)
    home_team_id = serializers.CharField(max_length=50)
    away_team = serializers.CharField(max_length=100)
    away_team_id = serializers.CharField(max_length=50)
    game_time = serializers.CharField()
    status = serializers.CharField(max_length=100)
    venue = serializers.CharField(max_length=20, allow_blank=True, required=False)
    timezone = serializers.CharField(max_length=10, allow_blank=True, required=False)
    datetime_utc = serializers.DateTimeField()