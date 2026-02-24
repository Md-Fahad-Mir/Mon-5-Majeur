from django.db import models
from apps.users.models import UserProfile
# Create your models here.
    
class TeamStatsModel(models.Model):
    # team = models.OneToOneField(TeamModel, on_delete=models.CASCADE, related_name='stats')
    matches_played = models.IntegerField(default=0)
    trophies = models.JSONField(default=list, blank=True, null=True)
    average_point_scored = models.FloatField(default=0.0, blank=True, null=True)
    average_point_conceded = models.FloatField(default=0.0, blank=True, null=True)
    league_played = models.IntegerField(default=0, blank=False, null=False)
    league_won = models.IntegerField(default=0, blank=False, null=False)
    league_loss = models.IntegerField(default=0, blank=False, null=False)
    no_battle = models.IntegerField(default=0, blank=False, null=False)
    regular_season_won = models.IntegerField(default=0, blank=False, null=False)

    def __str__(self):
        return f"Stats for {self.team.team_name}"

