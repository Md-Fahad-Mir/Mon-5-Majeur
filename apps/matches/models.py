from django.db import models
from apps.private_leagues.models import PrivateLeagueModel
from apps.public_leagues.models import PublicLeagueModel
from apps.users.models import UserProfile
from django.utils import timezone


class MatchModel(models.Model):
    MATCH_TYPE_CHOICES = [
        ("regular_season", "Regular Season"),
        ("playoffs", "Playoffs"),
    ]

    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("active", "Active"),
        ("completed", "Completed"),
    ]

    league_id = models.ForeignKey(PrivateLeagueModel, on_delete=models.CASCADE, related_name='matches')
    match_day = models.IntegerField()
    match_type = models.CharField(max_length=20, choices=MATCH_TYPE_CHOICES, default="regular_season")
    match_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="scheduled")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-match_date']
        indexes = [
            models.Index(fields=['league_id', 'match_type']),
            models.Index(fields=['league_id', 'status']),
        ]

    def __str__(self):
        return f"{self.league_id.leauge_name} - Match {self.match_day} ({self.match_type}) on {self.match_date.strftime('%Y-%m-%d')}"

    def mark_active(self):
        """Mark match as active when it starts."""
        self.status = "active"
        self.save(update_fields=['status', 'updated_at'])

    def mark_completed(self):
        """Mark match as completed and calculate final scores."""
        self.status = "completed"
        self.save(update_fields=['status', 'updated_at'])


class MatchScoreModel(models.Model):
    """Track individual player scores in a match."""
    
    match = models.ForeignKey(MatchModel, on_delete=models.CASCADE, related_name='player_scores')
    player = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='match_scores')
    
    # Points from different sources
    points_scored = models.IntegerField(default=0)  # Points from real NBA players
    bonus_points = models.IntegerField(default=0)   # Bonus/penalty points
    total_points = models.IntegerField(default=0)   # Total points in this match
    
    position = models.IntegerField(null=True, blank=True)  # 1st, 2nd, 3rd, etc. in the match
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('match', 'player')
        ordering = ['-total_points']

    def __str__(self):
        return f"{self.player.team_name} - {self.total_points} points (Match {self.match.match_day})"

    def calculate_total(self):
        """Calculate total points from all sources."""
        self.total_points = self.points_scored + self.bonus_points
        self.save(update_fields=['total_points', 'updated_at'])


class MatchPair(models.Model):
    """Represents a head-to-head pairing inside a match between two league players."""

    match = models.ForeignKey(MatchModel, on_delete=models.CASCADE, related_name='pairs')
    player_a = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='pairs_as_a')
    player_b = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='pairs_as_b', null=True, blank=True)

    # Optional aggregated scores for the pair (kept in sync from MatchScoreModel)
    score_a = models.IntegerField(default=0)
    score_b = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['match', 'player_a']), models.Index(fields=['match', 'player_b'])]

    def __str__(self):
        name_a = self.player_a.team_name if self.player_a else 'Unknown'
        name_b = self.player_b.team_name if self.player_b else 'BYE'
        return f"{name_a} vs {name_b} (Match {self.match.match_day})"


class LeagueSeason(models.Model):
    """Track season metadata and standings for a league."""
    
    league = models.OneToOneField(PrivateLeagueModel, on_delete=models.CASCADE, related_name='season')
    nba_season = models.CharField(max_length=20)  # e.g., "2025/2026"
    
    regular_season_start = models.DateTimeField()
    regular_season_end = models.DateTimeField()
    playoff_start = models.DateTimeField()
    playoff_end = models.DateTimeField()
    
    current_match_day = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.league.leauge_name} - Season {self.nba_season}"

    @property
    def is_regular_season_active(self):
        """Check if regular season is currently active."""
        now = timezone.now()
        return self.regular_season_start <= now <= self.regular_season_end

    @property
    def is_playoff_active(self):
        """Check if playoffs are currently active."""
        now = timezone.now()
        return self.playoff_start <= now <= self.playoff_end

    @property
    def days_remaining_regular(self):
        """Calculate remaining days in regular season."""
        if self.is_regular_season_active:
            return (self.regular_season_end - timezone.now()).days
        return 0


class PlayoffQualification(models.Model):
    """Track which players qualified for playoffs and their positions."""
    
    league = models.ForeignKey(PrivateLeagueModel, on_delete=models.CASCADE, related_name='playoff_qualifications')
    player = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    
    regular_season_rank = models.IntegerField()  # 1-4 for top 4 players
    total_points = models.IntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('league', 'player')
        ordering = ['regular_season_rank']

    def __str__(self):
        return f"{self.player.team_name} - Rank {self.regular_season_rank} in {self.league.leauge_name}"


# ============================================
# PUBLIC LEAGUE MODELS (Mirror of Private League Models)
# ============================================

class PublicMatchModel(models.Model):
    MATCH_TYPE_CHOICES = [
        ("regular_season", "Regular Season"),
        ("playoffs", "Playoffs"),
    ]

    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("active", "Active"),
        ("completed", "Completed"),
    ]

    league_id = models.ForeignKey(PublicLeagueModel, on_delete=models.CASCADE, related_name='public_matches')
    match_day = models.IntegerField()
    match_type = models.CharField(max_length=20, choices=MATCH_TYPE_CHOICES, default="regular_season")
    match_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="scheduled")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-match_date']
        indexes = [
            models.Index(fields=['league_id', 'match_type']),
            models.Index(fields=['league_id', 'status']),
        ]

    def __str__(self):
        return f"{self.league_id.leauge_name} - Match {self.match_day} ({self.match_type}) on {self.match_date.strftime('%Y-%m-%d')}"

    def mark_active(self):
        """Mark match as active when it starts."""
        self.status = "active"
        self.save(update_fields=['status', 'updated_at'])

    def mark_completed(self):
        """Mark match as completed and calculate final scores."""
        self.status = "completed"
        self.save(update_fields=['status', 'updated_at'])


class PublicMatchScoreModel(models.Model):
    """Track individual player scores in a public match."""
    
    match = models.ForeignKey(PublicMatchModel, on_delete=models.CASCADE, related_name='player_scores')
    player = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='public_match_scores')
    
    # Points from different sources
    points_scored = models.IntegerField(default=0)  # Points from real NBA players
    bonus_points = models.IntegerField(default=0)   # Bonus/penalty points
    total_points = models.IntegerField(default=0)   # Total points in this match
    
    position = models.IntegerField(null=True, blank=True)  # 1st, 2nd, 3rd, etc. in the match
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('match', 'player')
        ordering = ['-total_points']

    def __str__(self):
        return f"{self.player.team_name} - {self.total_points} points (Match {self.match.match_day})"

    def calculate_total(self):
        """Calculate total points from all sources."""
        self.total_points = self.points_scored + self.bonus_points
        self.save(update_fields=['total_points', 'updated_at'])


class PublicMatchPair(models.Model):
    """Represents a head-to-head pairing inside a public match between two league players."""

    match = models.ForeignKey(PublicMatchModel, on_delete=models.CASCADE, related_name='pairs')
    player_a = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='public_pairs_as_a')
    player_b = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='public_pairs_as_b', null=True, blank=True)

    # Optional aggregated scores for the pair (kept in sync from PublicMatchScoreModel)
    score_a = models.IntegerField(default=0)
    score_b = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['match', 'player_a']), models.Index(fields=['match', 'player_b'])]

    def __str__(self):
        name_a = self.player_a.team_name if self.player_a else 'Unknown'
        name_b = self.player_b.team_name if self.player_b else 'BYE'
        return f"{name_a} vs {name_b} (Match {self.match.match_day})"


class PublicLeagueSeason(models.Model):
    """Track season metadata and standings for a public league."""
    
    league = models.OneToOneField(PublicLeagueModel, on_delete=models.CASCADE, related_name='season')
    nba_season = models.CharField(max_length=20)  # e.g., "2025/2026"
    
    regular_season_start = models.DateTimeField()
    regular_season_end = models.DateTimeField()
    playoff_start = models.DateTimeField()
    playoff_end = models.DateTimeField()
    
    current_match_day = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.league.leauge_name} - Season {self.nba_season}"

    @property
    def is_regular_season_active(self):
        """Check if regular season is currently active."""
        now = timezone.now()
        return self.regular_season_start <= now <= self.regular_season_end

    @property
    def is_playoff_active(self):
        """Check if playoffs are currently active."""
        now = timezone.now()
        return self.playoff_start <= now <= self.playoff_end

    @property
    def days_remaining_regular(self):
        """Calculate remaining days in regular season."""
        if self.is_regular_season_active:
            return (self.regular_season_end - timezone.now()).days
        return 0


class PublicPlayoffQualification(models.Model):
    """Track which players qualified for playoffs and their positions in public leagues."""
    
    league = models.ForeignKey(PublicLeagueModel, on_delete=models.CASCADE, related_name='playoff_qualifications')
    player = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    
    regular_season_rank = models.IntegerField()  # 1-4 for top 4 players
    total_points = models.IntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('league', 'player')
        ordering = ['regular_season_rank']

    def __str__(self):
        return f"{self.player.team_name} - Rank {self.regular_season_rank} in {self.league.leauge_name}"