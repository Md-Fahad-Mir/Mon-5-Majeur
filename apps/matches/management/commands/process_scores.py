from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.matches.models import MatchModel, PublicMatchModel
from apps.matches.services import MatchSchedulerService

class Command(BaseCommand):
    help = 'Process scores and complete active matches from yesterday'

    def handle(self, *args, **kwargs):
        # We process matches from yesterday to ensure all real NBA games are finished
        yesterday = timezone.now().date() - timedelta(days=1)
        
        # Process private league matches
        active_matches = MatchModel.objects.filter(
            status='active',
            match_date__date=yesterday
        )
        
        count = active_matches.count()
        for match in active_matches:
            try:
                self.stdout.write(f"Processing private match {match.id} ({match.league_id.leauge_name})...")
                MatchSchedulerService.process_match_results(match)
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error processing private match {match.id}: {str(e)}"))
        
        # Process public league matches
        active_public_matches = PublicMatchModel.objects.filter(
            status='active',
            match_date__date=yesterday
        )
        
        public_count = active_public_matches.count()
        for match in active_public_matches:
            try:
                self.stdout.write(f"Processing public match {match.id} ({match.league_id.leauge_name})...")
                MatchSchedulerService.process_public_match_results(match)
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error processing public match {match.id}: {str(e)}"))
            
        self.stdout.write(self.style.SUCCESS(f'Successfully processed {count} private and {public_count} public active matches from {yesterday}'))

