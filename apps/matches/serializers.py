from rest_framework import serializers
from .models import (
    MatchModel, MatchScoreModel, LeagueSeason, PlayoffQualification, MatchPair,
    PublicMatchModel, PublicMatchScoreModel, PublicLeagueSeason, PublicPlayoffQualification, PublicMatchPair
)


class MatchScoreSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='player.team_name', read_only=True)
    player_id = serializers.IntegerField(source='player.id', read_only=True)
    username = serializers.CharField(source='player.user.username', read_only=True)

    class Meta:
        model = MatchScoreModel
        fields = ('player_id', 'team_name', 'username', 'points_scored', 'bonus_points', 'total_points', 'position')


class MatchSerializer(serializers.ModelSerializer):
    player_scores = MatchScoreSerializer(many=True, read_only=True)
    league_name = serializers.CharField(source='league_id.leauge_name', read_only=True)
    pairs = serializers.SerializerMethodField()

    class Meta:
        model = MatchModel
        fields = ('id', 'league_id', 'league_name', 'match_day', 'match_type', 'match_date', 'status', 'player_scores', 'pairs', 'created_at')

    def get_pairs(self, obj):
        pairs = obj.pairs.all()
        result = []
        for p in pairs:
            result.append({
                'player_a_id': p.player_a.id,
                'player_a_name': p.player_a.team_name,
                'player_b_id': p.player_b.id if p.player_b else None,
                'player_b_name': p.player_b.team_name if p.player_b else None,
                'score_a': p.score_a,
                'score_b': p.score_b,
            })
        return result


class LeagueSeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeagueSeason
        fields = ('id', 'league', 'nba_season', 'regular_season_start', 'regular_season_end', 
                  'playoff_start', 'playoff_end', 'current_match_day', 'is_regular_season_active', 
                  'is_playoff_active', 'days_remaining_regular')
        read_only_fields = ('is_regular_season_active', 'is_playoff_active', 'days_remaining_regular')


class PlayoffQualificationSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='player.team_name', read_only=True)
    username = serializers.CharField(source='player.user.username', read_only=True)

    class Meta:
        model = PlayoffQualification
        fields = ('id', 'player', 'team_name', 'username', 'regular_season_rank', 'total_points')


# ============================================
# PUBLIC LEAGUE SERIALIZERS
# ============================================

class PublicMatchScoreSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='player.team_name', read_only=True)
    player_id = serializers.IntegerField(source='player.id', read_only=True)
    username = serializers.CharField(source='player.user.username', read_only=True)

    class Meta:
        model = PublicMatchScoreModel
        fields = ('player_id', 'team_name', 'username', 'points_scored', 'bonus_points', 'total_points', 'position')


class PublicMatchSerializer(serializers.ModelSerializer):
    player_scores = PublicMatchScoreSerializer(many=True, read_only=True)
    league_name = serializers.CharField(source='league_id.leauge_name', read_only=True)
    pairs = serializers.SerializerMethodField()

    class Meta:
        model = PublicMatchModel
        fields = ('id', 'league_id', 'league_name', 'match_day', 'match_type', 'match_date', 'status', 'player_scores', 'pairs', 'created_at')

    def get_pairs(self, obj):
        pairs = obj.pairs.all()
        result = []
        for p in pairs:
            result.append({
                'player_a_id': p.player_a.id,
                'player_a_name': p.player_a.team_name,
                'player_b_id': p.player_b.id if p.player_b else None,
                'player_b_name': p.player_b.team_name if p.player_b else None,
                'score_a': p.score_a,
                'score_b': p.score_b,
            })
        return result


class PublicLeagueSeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicLeagueSeason
        fields = ('id', 'league', 'nba_season', 'regular_season_start', 'regular_season_end', 
                  'playoff_start', 'playoff_end', 'current_match_day', 'is_regular_season_active', 
                  'is_playoff_active', 'days_remaining_regular')
        read_only_fields = ('is_regular_season_active', 'is_playoff_active', 'days_remaining_regular')


class PublicPlayoffQualificationSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='player.team_name', read_only=True)
    username = serializers.CharField(source='player.user.username', read_only=True)

    class Meta:
        model = PublicPlayoffQualification
        fields = ('id', 'player', 'team_name', 'username', 'regular_season_rank', 'total_points')

