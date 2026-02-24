from django.db import models
from apps.users.models import UserProfile
from django.utils import timezone


class PublicLeagueModel(models.Model):
    """Represents a public fantasy league that anyone can join without a code."""

    MAX_TEAM_NUMBERS_CHOICES = [
        ("4", "4"),
        ("6", "6"),
        ("8", "8"),
        ("10", "10"),
    ]

    LEAUGE_LOGO_CHOICES = [
        ("paris_fc", "Paris FC"),
        ("lakers", "Lakers"),
        ("boston_celtics", "Boston Celtics"),
        ("chicago_bulls", "Chicago Bulls"),
        ("atlanta_hawks", "Atlanta Hawks"),
        ("golden_state_warriors", "Golden State Warriors"),
    ]

    TEAM_BUDGET_CHOICES = [
        ("50M", "50 Million"),
        ("80M", "80 Million"),
        ("100M", "100 Million"),
        ("120M", "120 Million"),
        ("150M", "150 Million"),
        ("200M", "200 Million"),

    ]

    creator = models.ForeignKey(UserProfile, on_delete=models.CASCADE, blank=False, null=False, related_name='created_public_leagues')
    leauge_name = models.CharField(max_length=100, null=False, blank=False)
    leauge_description = models.TextField(max_length=150, null=True, blank=True)
    leauge_logo = models.CharField(max_length=200, choices=LEAUGE_LOGO_CHOICES, null=False, blank=False)
    team_budget = models.CharField(max_length=10, choices=TEAM_BUDGET_CHOICES, default="100M", null=False, blank=False,)
    max_team_number = models.CharField(max_length=20, choices=MAX_TEAM_NUMBERS_CHOICES, default="10", null=False, blank=False,)
    teams = models.ManyToManyField(UserProfile, related_name='joined_public_leagues', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateTimeField(blank=True, null=True)
    is_ready = models.BooleanField(default=False)
    is_started = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['creator', 'leauge_name'], name='unique_user_public_league_name')
        ]

    def save(self, *args, **kwargs):
        # Ensure instance is saved before accessing many-to-many relations.
        # If this is a new instance (no PK yet), save first to obtain an ID,
        # then evaluate `is_ready` based on the actual teams count.
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Determine max teams (choices are stored as strings)
        try:
            max_teams = int(self.max_team_number)
        except Exception:
            max_teams = 0

        # Now it's safe to access `self.teams`
        is_ready_now = (self.teams.count() == max_teams)
        if self.is_ready != is_ready_now:
            # Update only the field that changed to avoid recursion and extra work
            self.is_ready = is_ready_now
            super().save(update_fields=["is_ready"])

    def start_league(self):
        """Mark league as started and set start date."""
        if not self.is_ready:
            raise ValueError("Cannot start league before all teams have joined.")
        self.is_started = True
        self.start_date = timezone.now()
        self.save()

    def has_expired(self):
        """Check if 7 days have passed since start."""
        if not self.start_date:
            return False
        from datetime import timedelta
        return timezone.now() >= self.start_date + timedelta(days=7)
