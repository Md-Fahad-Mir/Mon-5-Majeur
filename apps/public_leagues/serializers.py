from rest_framework import serializers
from .models import PublicLeagueModel
from apps.users.models import UserProfile
from django.utils import timezone
from datetime import timedelta


class PublicTeamInfoSerializer(serializers.ModelSerializer):
    team_id = serializers.IntegerField(source='id', read_only=True)

    class Meta:
        model = UserProfile
        fields = ('team_id', 'team_name', 'team_logo')


class PublicLeagueSerializer(serializers.ModelSerializer):
    teams = PublicTeamInfoSerializer(many=True, read_only=True)
    current_match_day = serializers.SerializerMethodField()

    class Meta:
        model = PublicLeagueModel
        fields = '__all__'
        read_only_fields = ['creator', 'created_at', 'is_started', 'is_active', 'is_ready', 'start_date']

    def get_current_match_day(self, obj):
        """
        Calculates the active match day based on current time.
        Finds the latest match day that is either today or in the past (UTC).
        We use a +1 day buffer to accommodate users in timezones ahead of UTC (like UTC+6).
        """
        if not obj.is_started:
            return 0
        
        now = timezone.now()
        # Find the latest match day that is not far in the future
        # Using date comparison with a 1-day look-ahead for timezone differences
        latest_match = obj.public_matches.filter(
            match_date__date__lte=(now + timedelta(days=1)).date()
        ).order_by('-match_day').first()
        
        if latest_match:
            return latest_match.match_day
        
        # Fallback to the first match if somehow nothing is found
        return 1


class JoinPublicLeagueSerializer(serializers.Serializer):
    league_id = serializers.IntegerField()


class LeavePublicLeagueSerializer(serializers.Serializer):
    league_id = serializers.IntegerField()


class PublicKickTeamSerializer(serializers.Serializer):
    team_id = serializers.IntegerField()
    league_id = serializers.IntegerField()


class PublicStartLeagueSerializer(serializers.Serializer):
    league_id = serializers.IntegerField()
