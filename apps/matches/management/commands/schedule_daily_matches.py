from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.private_leagues.models import PrivateLeagueModel
from apps.public_leagues.models import PublicLeagueModel
from apps.matches.services import MatchSchedulerService
from apps.matches.models import LeagueSeason, PublicLeagueSeason


class Command(BaseCommand):
    help = 'Create daily matches for all active leagues'

    def handle(self, *args, **options):
        match_count = 0
        
        # 1. Process Private Leagues
        private_leagues = PrivateLeagueModel.objects.filter(is_started=True)
        for league in private_leagues:
            try:
                if not hasattr(league, 'season'):
                    self.stdout.write(self.style.WARNING(f'Private League "{league.leauge_name}" has no season initialized'))
                    continue

                if MatchSchedulerService.create_daily_matches(league):
                    match_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ Match active for private league "{league.leauge_name}"'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error for private league "{league.leauge_name}": {str(e)}'))

        # 2. Process Public Leagues
        public_leagues = PublicLeagueModel.objects.filter(is_started=True)
        for league in public_leagues:
            try:
                if not hasattr(league, 'season'):
                    self.stdout.write(self.style.WARNING(f'Public League "{league.leauge_name}" has no season initialized'))
                    continue

                if MatchSchedulerService.create_public_daily_matches(league):
                    match_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ Match active for public league "{league.leauge_name}"'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error for public league "{league.leauge_name}": {str(e)}'))

        self.stdout.write(self.style.SUCCESS(f'\nTotal active matches processed: {match_count}'))

