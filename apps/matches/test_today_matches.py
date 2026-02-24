from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from apps.matches.models import MatchModel, MatchPair
from apps.private_leagues.models import PrivateLeagueModel
from apps.users.models import UserProfile

class TodayMatchesTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create users
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')
        self.user3 = User.objects.create_user(username='user3', password='password123')
        
        # Create profiles
        self.profile1 = UserProfile.objects.create(user=self.user1, team_name='Team 1')
        self.profile2 = UserProfile.objects.create(user=self.user2, team_name='Team 2')
        self.profile3 = UserProfile.objects.create(user=self.user3, team_name='Team 3')
        
        # Create a league
        self.league = PrivateLeagueModel.objects.create(
            creator=self.profile1,
            leauge_name='Test League',
            leauge_logo='lakers',
            max_team_number='4'
        )
        self.league.teams.add(self.profile1, self.profile2, self.profile3)
        
        # Get current date in local time
        self.today = timezone.localtime(timezone.now())
        self.tomorrow = self.today + timedelta(days=1)
        self.yesterday = self.today - timedelta(days=1)
        
        # Create matches
        # Match today for user1 vs user2
        self.match_today = MatchModel.objects.create(
            league_id=self.league,
            match_day=1,
            match_date=self.today,
            status='scheduled'
        )
        MatchPair.objects.create(match=self.match_today, player_a=self.profile1, player_b=self.profile2)
        
        # Match tomorrow for user1
        self.match_tomorrow = MatchModel.objects.create(
            league_id=self.league,
            match_day=2,
            match_date=self.tomorrow,
            status='scheduled'
        )
        MatchPair.objects.create(match=self.match_tomorrow, player_a=self.profile1, player_b=self.profile3)
        
        # Match today for others (not user1)
        self.match_others_today = MatchModel.objects.create(
            league_id=self.league,
            match_day=3,
            match_date=self.today,
            status='scheduled'
        )
        MatchPair.objects.create(match=self.match_others_today, player_a=self.profile2, player_b=self.profile3)

    def test_get_today_matches_unauthenticated(self):
        url = '/api/private-leagues/matches/my-matches-today/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_today_matches_authenticated(self):
        self.client.force_authenticate(user=self.user1)
        url = '/api/private-leagues/matches/my-matches-today/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see both today and tomorrow's matches where user1 is participating
        self.assertEqual(len(response.data), 2)
        match_ids = [m['id'] for m in response.data]
        self.assertIn(self.match_today.id, match_ids)
        self.assertIn(self.match_tomorrow.id, match_ids)
        
        # Check team names in pairs
        pairs = response.data[0]['pairs']
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]['player_a_name'], 'Team 1')
        self.assertEqual(pairs[0]['player_b_name'], 'Team 2')

    def test_get_today_matches_different_user(self):
        self.client.force_authenticate(user=self.user2)
        url = '/api/private-leagues/matches/my-matches-today/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # user2 is in match_today and match_others_today
        self.assertEqual(len(response.data), 2)
        match_ids = [m['id'] for m in response.data]
        self.assertIn(self.match_today.id, match_ids)
        self.assertIn(self.match_others_today.id, match_ids)
