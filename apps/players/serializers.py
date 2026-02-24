# players/serializers.py
from rest_framework import serializers


class PlayerSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    position = serializers.CharField()
    team = serializers.CharField()
    team_id = serializers.CharField()
    status = serializers.CharField()  # OUT / Uncertain / OK
    price = serializers.CharField()


class PlayerStatsSerializer(serializers.Serializer):
    games_played = serializers.IntegerField(allow_null=True)
    minutes = serializers.FloatField(allow_null=True)
    points = serializers.FloatField(allow_null=True)
    rebounds = serializers.FloatField(allow_null=True)
    assists = serializers.FloatField(allow_null=True)
    steals = serializers.FloatField(allow_null=True)
    blocks = serializers.FloatField(allow_null=True)
    fg_pct = serializers.FloatField(allow_null=True)
    three_pct = serializers.FloatField(allow_null=True)
    ft_pct = serializers.FloatField(allow_null=True)
    fg_attempts = serializers.FloatField(allow_null=True)
    three_attempts = serializers.FloatField(allow_null=True)
    ft_attempts = serializers.FloatField(allow_null=True)
    turnovers = serializers.FloatField(allow_null=True)
    personal_fouls = serializers.FloatField(allow_null=True)

class PlayerDetailSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    team = serializers.CharField()
    position = serializers.CharField()
    age = serializers.CharField(required=False)
    height = serializers.CharField(required=False)
    weight = serializers.CharField(required=False)
    college = serializers.CharField(required=False)
    salary = serializers.CharField(required=False)
    stats = serializers.DictField()


class TeamSelectionSerializer(serializers.Serializer):
    match = serializers.IntegerField()
    selected_players = serializers.ListField(child=serializers.CharField())
    total_points = serializers.IntegerField(read_only=True)

    def validate_selected_players(self, value):
        if not isinstance(value, list) or len(value) == 0:
            raise serializers.ValidationError("selected_players must be a non-empty list of player ids")
        if len(value) > 20:
            raise serializers.ValidationError("selected_players list too large")
        return value



class PlayerSelectionItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    position = serializers.CharField()
    team = serializers.CharField()
    team_id = serializers.CharField()
    price = serializers.CharField()
    score = serializers.IntegerField(required=False, default=0)


class MatchSelectionSerializer(serializers.Serializer):
    match_id = serializers.IntegerField(read_only=True)
    match_day = serializers.IntegerField(read_only=True)
    selected_players = serializers.ListField(child=PlayerSelectionItemSerializer())
    total_points = serializers.IntegerField(read_only=True)

    def validate_selected_players(self, value):
        if not isinstance(value, list) or len(value) == 0:
            raise serializers.ValidationError("selected_players must be a non-empty list of players")
        
        # Max 5 players
        if len(value) > 5:
            raise serializers.ValidationError("You can select up to 5 players only.")
        
        return value

    def _parse_price(self, price_str):
        """Parse price string like '1.2M' or '500000' to float."""
        try:
            s = str(price_str).upper().replace(',', '')
            if 'M' in s:
                return float(s.replace('M', '')) * 1_000_000
            return float(s)
        except (ValueError, TypeError):
            return 0.0

    def validate(self, data):
        selected_players = data.get('selected_players', [])
        
        # Calculate total price
        total_price = sum(self._parse_price(player.get('price')) for player in selected_players)
        
        # Get budget from context
        league_budget_str = self.context.get('league_budget', '100M')
        
        # Parse budget
        try:
            budget_val = float(str(league_budget_str).upper().replace('M', '')) * 1_000_000
        except ValueError:
            budget_val = 100_000_000 # Default fallback
        
        # Checking with a small buffer for float precision issues
        if total_price > budget_val + 1.0:
            raise serializers.ValidationError(
                f"Total player price exceeds league budget ({league_budget_str}). Please remove some players or select cheaper ones to fit your budget."
            )
            
        return data


class PublicMatchSelectionSerializer(serializers.Serializer):
    """Serializer for public league match player selection."""
    match_id = serializers.IntegerField(read_only=True)
    match_day = serializers.IntegerField(read_only=True)
    selected_players = serializers.ListField(child=PlayerSelectionItemSerializer())
    total_points = serializers.IntegerField(read_only=True)

    def validate_selected_players(self, value):
        if not isinstance(value, list) or len(value) == 0:
            raise serializers.ValidationError("selected_players must be a non-empty list of players")
        
        # Max 5 players
        if len(value) > 5:
            raise serializers.ValidationError("You can select up to 5 players only.")
        
        return value

    def _parse_price(self, price_str):
        """Parse price string like '1.2M' or '500000' to float."""
        try:
            s = str(price_str).upper().replace(',', '')
            if 'M' in s:
                return float(s.replace('M', '')) * 1_000_000
            return float(s)
        except (ValueError, TypeError):
            return 0.0

    def validate(self, data):
        selected_players = data.get('selected_players', [])
        
        # Calculate total price
        total_price = sum(self._parse_price(player.get('price')) for player in selected_players)
        
        # Get budget from context
        league_budget_str = self.context.get('league_budget', '100M')
        
        # Parse budget
        try:
            budget_val = float(str(league_budget_str).upper().replace('M', '')) * 1_000_000
        except ValueError:
            budget_val = 100_000_000 # Default fallback
        
        # Checking with a small buffer for float precision issues
        if total_price > budget_val + 1.0:
            raise serializers.ValidationError(
                f"Total player price exceeds league budget ({league_budget_str}). Please remove some players or select cheaper ones to fit your budget."
            )
            
        return data

