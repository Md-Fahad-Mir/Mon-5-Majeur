from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.matches.models import MatchModel, PublicMatchModel

class Command(BaseCommand):
    help = 'Activate scheduled matches for today'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        
        # Activate private league matches
        scheduled_matches = MatchModel.objects.filter(
            status='scheduled',
            match_date__date=today
        )
        
        count = scheduled_matches.count()
        for match in scheduled_matches:
            match.status = 'active'
            match.save()
            
        # Activate public league matches
        scheduled_public_matches = PublicMatchModel.objects.filter(
            status='scheduled',
            match_date__date=today
        )
        
        public_count = scheduled_public_matches.count()
        for match in scheduled_public_matches:
            match.status = 'active'
            match.save()
            
        self.stdout.write(self.style.SUCCESS(f'Successfully activated {count} private and {public_count} public matches for {today}'))

