from django.db import models
from django.utils import timezone
from apps.users.models import UserProfile
from apps.matches.models import MatchModel, PublicMatchModel


# Create your models here.
class TeamSelection(models.Model):
	"""Stores the list of external player IDs a team owner selects for a specific match."""

	match = models.ForeignKey(MatchModel, on_delete=models.CASCADE, related_name='selections')
	owner = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='selections')
	# list of external player ids (strings) taken from /api/players-today
	selected_players = models.JSONField(default=list)
	total_points = models.IntegerField(default=0)

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = ('match', 'owner')

	def __str__(self):
		return f"Selection for {self.owner.team_name} in Match {self.match.match_day}"

	def compute_total_from_scores(self):
		"""Compute total_points by summing MatchScoreModel.total_points of selected players.

		This expects MatchScoreModel.player to map to a UserProfile; if you're storing external
		player ids (from goalserve), you'll need to map them to UserProfile players in your own
		domain. For now, this method is a placeholder to be invoked after match scoring.
		"""
		# Placeholder: actual mapping logic depends on how external players are linked to UserProfile
		return self.total_points


class PublicTeamSelection(models.Model):
	"""Stores the list of external player IDs a team owner selects for a specific public match."""

	match = models.ForeignKey(PublicMatchModel, on_delete=models.CASCADE, related_name='public_selections')
	owner = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='public_selections')
	# list of external player ids (strings) taken from /api/players-today
	selected_players = models.JSONField(default=list)
	total_points = models.IntegerField(default=0)

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = ('match', 'owner')

	def __str__(self):
		return f"Public Selection for {self.owner.team_name} in Match {self.match.match_day}"

	def compute_total_from_scores(self):
		"""Compute total_points by summing PublicMatchScoreModel.total_points of selected players.

		This expects PublicMatchScoreModel.player to map to a UserProfile; if you're storing external
		player ids (from goalserve), you'll need to map them to UserProfile players in your own
		domain. For now, this method is a placeholder to be invoked after match scoring.
		"""
		# Placeholder: actual mapping logic depends on how external players are linked to UserProfile
		return self.total_points

