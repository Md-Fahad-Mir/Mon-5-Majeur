import random
from datetime import datetime
from django.utils import timezone
from django.db.models import Sum
from apps.matches.models import (
    MatchModel, MatchPair, LeagueSeason, MatchScoreModel,
    PublicMatchModel, PublicMatchPair, PublicLeagueSeason, PublicMatchScoreModel, PublicPlayoffQualification
)
from apps.scoring.utils import fetch_nba_schedule

class MatchSchedulerService:
    @staticmethod
    def get_active_nba_dates(since_date=None):
        """Fetches NBA schedule and returns a list of dates with games."""
        if since_date is None:
            since_date = timezone.now().date()
            
        data = fetch_nba_schedule()
        active_dates = []
        
        # Check if "shedules" key exists
        shedules = data.get("shedules", {})
        if not shedules:
            return []
            
        for day in shedules.get("matches", []):
            date_str = day.get("formatted_date")
            matches = day.get("match", [])
            
            # Ensure it's a list for consistent check
            if isinstance(matches, dict):
                matches = [matches]
                
            if date_str and len(matches) > 0:
                try:
                    # Convert DD.MM.YYYY to date object
                    date_obj = datetime.strptime(date_str, "%d.%m.%Y").date()
                    # Only include dates from since_date onwards
                    if date_obj >= since_date:
                        active_dates.append(date_obj)
                except ValueError:
                    continue
        
        # Sort dates to ensure chronological order
        active_dates.sort()
        return active_dates

    @staticmethod
    def initialize_season(league):
        """Initializes the LeagueSeason metadata."""
        # Check if season already exists
        if hasattr(league, 'season'):
            return league.season
            
        # Determine season string (e.g., 2025/2026)
        now = timezone.now()
        year = now.year
        if now.month >= 10:
            nba_season = f"{year}/{year+1}"
        else:
            nba_season = f"{year-1}/{year}"
            
        # For simplicity, we define a 30-day regular season for now
        # In a real app, these would come from NBA calendar
        from datetime import timedelta
        season = LeagueSeason.objects.create(
            league=league,
            nba_season=nba_season,
            regular_season_start=now,
            regular_season_end=now + timedelta(days=30),
            playoff_start=now + timedelta(days=31),
            playoff_end=now + timedelta(days=45)
        )
        return season

    @classmethod
    def generate_season_matches(cls, league):
        """
        Generates a full round-robin schedule for a league.
        Assigns each round to an available NBA game day.
        """
        teams = list(league.teams.all())
        if not teams:
            return
            
        num_teams = len(teams)
        if num_teams % 2 != 0:
            teams.append(None)  # Add BYE team (None)
            num_teams += 1
            
        rounds = num_teams - 1
        matches_per_round = num_teams // 2
        
        active_dates = cls.get_active_nba_dates()
        
        # Fallback if no NBA dates found
        if not active_dates:
            from datetime import timedelta
            active_dates = [(timezone.now() + timedelta(days=i+1)).date() for i in range(rounds)]
            
        # Ensure we have enough dates
        if len(active_dates) < rounds:
            from datetime import timedelta
            last_date = active_dates[-1] if active_dates else timezone.now().date()
            for i in range(rounds - len(active_dates)):
                active_dates.append(last_date + timedelta(days=i+1))

        # Generate matches for all available active dates, repeating rounds if necessary
        for date_idx, match_date in enumerate(active_dates):
            round_idx = date_idx % rounds
            match_datetime = timezone.make_aware(datetime.combine(match_date, datetime.min.time()))
            
            match_obj = MatchModel.objects.create(
                league_id=league,
                match_day=date_idx + 1,
                match_type="regular_season",
                match_date=match_datetime,
                status="scheduled"
            )
            
            # Temporary list for rotation for this specific round
            temp_teams = list(teams)
            # Perform rotation to get the state for round_idx
            for _ in range(round_idx):
                temp_teams = [temp_teams[0]] + [temp_teams[-1]] + temp_teams[1:-1]
                
            for match_idx in range(matches_per_round):
                player_a = temp_teams[match_idx]
                player_b = temp_teams[num_teams - 1 - match_idx]
                
                if player_a and player_b:
                    MatchPair.objects.create(
                        match=match_obj,
                        player_a=player_a,
                        player_b=player_b
                    )
                elif player_a or player_b:
                    # One team has a BYE
                    MatchPair.objects.create(
                        match=match_obj,
                        player_a=player_a or player_b,
                        player_b=None
                    )

    @staticmethod
    def get_league_standings(league, match_type="regular_season"):
        """Calculates standings for a league based on match results."""
        teams = league.teams.all()
        standings = []
        
        for team in teams:
            # sum scores from MatchScoreModel for this team in this league/type
            total_points = MatchScoreModel.objects.filter(
                match__league_id=league,
                match__match_type=match_type,
                player=team
            ).aggregate(total=Sum('total_points'))['total'] or 0
            
            standings.append({
                "team_id": team.id,
                "team_name": team.team_name,
                "total_points": total_points
            })
            
        # Sort by points descending
        standings.sort(key=lambda x: x['total_points'], reverse=True)
        return standings

    @staticmethod
    def get_playoff_winner(league):
        """Returns the winner of the playoffs (highest score in completed playoff matches)."""
        playoff_matches = MatchModel.objects.filter(
            league_id=league,
            match_type="playoffs",
            status="completed"
        ).order_by('-match_day')
        
        if not playoff_matches.exists():
            return None
            
        # For simple playoffs, the winner of the last match or top total playoff score
        # Let's use the top score in the latest playoff match as the winner for now
        latest_match = playoff_matches.first()
        top_score = latest_match.player_scores.all().first() # Ordered by -total_points in Meta
        if top_score:
            return top_score.player
        return None

    @classmethod
    def process_match_results(cls, match):
        """Processes scores for all selections in a match and updates pairs."""
        from apps.scoring.utils import get_selected_players_live_score
        from apps.players.models import TeamSelection
        
        # 1. Get all selections for this match
        selections = match.selections.all()
        
        # Collect all unique GoalServe player IDs across all selections
        all_gs_player_ids = set()
        for s in selections:
            all_gs_player_ids.update(s.selected_players)
            
        # 2. Fetch real scores from GoalServe for the match date
        from apps.games.utils import get_today_games
        date_str = match.match_date.strftime("%d.%m.%Y")
        nba_games = get_today_games(date_str)
        
        real_player_scores = {} # gs_id -> points
        for game in nba_games:
            game_id = game.get('id')
            if game_id:
                scores = get_selected_players_live_score(game_id, list(all_gs_player_ids), date_str)
                for score_item in scores:
                    real_player_scores[str(score_item['player_id'])] = score_item.get('points', 0)
        
        # 3. Calculate total score for each selection
        for selection in selections:
            total = 0
            for pid in selection.selected_players:
                total += real_player_scores.get(str(pid), 0)
            selection.total_points = total
            selection.save()
            
            # Update or create MatchScoreModel for standings
            MatchScoreModel.objects.update_or_create(
                match=match,
                player=selection.owner,
                defaults={'total_points': total}
            )

        # 4. Update MatchPairs
        for pair in match.pairs.all():
            # Get score for player_a
            try:
                sel_a = match.selections.get(owner=pair.player_a)
                pair.score_a = sel_a.total_points
            except Exception:
                pair.score_a = 0 # No selection = 0 points
                MatchScoreModel.objects.update_or_create(
                    match=match, player=pair.player_a, defaults={'total_points': 0}
                )
                
            # Get score for player_b
            if pair.player_b:
                try:
                    sel_b = match.selections.get(owner=pair.player_b)
                    pair.score_b = sel_b.total_points
                except Exception:
                    pair.score_b = 0 # No selection = 0 points
                    MatchScoreModel.objects.update_or_create(
                        match=match, player=pair.player_b, defaults={'total_points': 0}
                    )
            else:
                pair.score_b = 0 # BYE
                
            pair.save()
            
        # 5. Mark match as completed
        match.status = "completed"
        match.save()
        
        # 6. If it's the last regular season match, trigger playoff transition
        if match.match_type == "regular_season":
            last_match = MatchModel.objects.filter(
                league_id=match.league_id, match_type="regular_season"
            ).order_by('-match_day').first()
            
            if last_match and last_match.id == match.id:
                cls.transition_to_playoffs(match.league_id)

    @classmethod
    def transition_to_playoffs(cls, league):
        """Qualifies top teams and generates playoff schedule."""
        # Logic for selecting top 8, 4, etc. based on max_team_number
        stands = cls.get_league_standings(league, "regular_season")
        
        max_teams = int(league.max_team_number)
        num_qualifiers = 8 if max_teams >= 8 else 4
        
        qualifiers = stands[:num_qualifiers]
        
        from apps.users.models import UserProfile
        for i, q in enumerate(qualifiers):
            player = UserProfile.objects.get(id=q['team_id'])
            PlayoffQualification.objects.get_or_create(
                league=league,
                player=player,
                defaults={
                    'regular_season_rank': i + 1,
                    'total_points': q['total_points']
                }
            )
            
        # Generate Playoff Matches (Simplified: Round Robin for now, or Brackets)
        # The user said "they will play playoff season", logic same.
        # So we can generate another round-robin for qualifiers.
        teams = [UserProfile.objects.get(id=q['team_id']) for q in qualifiers]
        
        # Reuse round-robin logic for playoffs
        # We need a new set of dates for playoffs
        cls.generate_playoff_matches(league, teams)

    @classmethod
    def generate_playoff_matches(cls, league, teams):
        """Generates round-robin matches for playoff qualifiers."""
        num_teams = len(teams)
        if num_teams % 2 != 0:
            teams.append(None)
            num_teams += 1
            
        rounds = num_teams - 1
        matches_per_round = num_teams // 2
        
        # Determine start date for playoffs (next available date after regular season)
        from datetime import timedelta
        last_match = MatchModel.objects.filter(
            league=league, match_type="regular_season"
        ).order_by('-match_date').first()
        
        start_date = (last_match.match_date + timedelta(days=1)).date() if last_match else timezone.now().date()
        
        # Get active NBA dates starting from start_date
        active_dates = cls.get_active_nba_dates(since_date=start_date)
        
        # Fallback if no dates found
        if len(active_dates) < rounds:
            for i in range(rounds - len(active_dates)):
                d = active_dates[-1] if active_dates else start_date
                active_dates.append(d + timedelta(days=i+1))

        # Generate matches
        for round_idx in range(rounds):
            match_date = active_dates[round_idx]
            match_datetime = timezone.make_aware(datetime.combine(match_date, datetime.min.time()))
            
            match_obj = MatchModel.objects.create(
                league_id=league,
                match_day=round_idx + 1,
                match_type="playoffs",
                match_date=match_datetime,
                status="scheduled"
            )
            
            round_teams = list(teams)
            for match_idx in range(matches_per_round):
                player_a = round_teams[match_idx]
                player_b = round_teams[num_teams - 1 - match_idx]
                
                if player_a and player_b:
                    MatchPair.objects.create(
                        match=match_obj,
                        player_a=player_a,
                        player_b=player_b
                    )
                elif player_a or player_b:
                    MatchPair.objects.create(
                        match=match_obj,
                        player_a=player_a or player_b,
                        player_b=None
                    )
            
            # Rotate
            teams = [teams[0]] + [teams[-1]] + teams[1:-1]

    # ============================================
    # PUBLIC LEAGUE METHODS (Mirror of Private League Methods)
    # ============================================

    @staticmethod
    def initialize_public_season(league):
        """Initializes the PublicLeagueSeason metadata."""
        # Check if season already exists
        if hasattr(league, 'season'):
            return league.season
            
        # Determine season string (e.g., 2025/2026)
        now = timezone.now()
        year = now.year
        if now.month >= 10:
            nba_season = f"{year}/{year+1}"
        else:
            nba_season = f"{year-1}/{year}"
            
        # For simplicity, we define a 30-day regular season for now
        # In a real app, these would come from NBA calendar
        from datetime import timedelta
        season = PublicLeagueSeason.objects.create(
            league=league,
            nba_season=nba_season,
            regular_season_start=now,
            regular_season_end=now + timedelta(days=30),
            playoff_start=now + timedelta(days=31),
            playoff_end=now + timedelta(days=45)
        )
        return season

    @classmethod
    def generate_public_season_matches(cls, league):
        """
        Generates a full round-robin schedule for a public league.
        Assigns each round to an available NBA game day.
        """
        teams = list(league.teams.all())
        if not teams:
            return
            
        num_teams = len(teams)
        if num_teams % 2 != 0:
            teams.append(None)  # Add BYE team (None)
            num_teams += 1
            
        rounds = num_teams - 1
        matches_per_round = num_teams // 2
        
        active_dates = cls.get_active_nba_dates()
        
        # Fallback if no NBA dates found
        if not active_dates:
            from datetime import timedelta
            active_dates = [(timezone.now() + timedelta(days=i+1)).date() for i in range(rounds)]
            
        # Ensure we have enough dates
        if len(active_dates) < rounds:
            from datetime import timedelta
            last_date = active_dates[-1] if active_dates else timezone.now().date()
            for i in range(rounds - len(active_dates)):
                active_dates.append(last_date + timedelta(days=i+1))

        # Generate matches for all available active dates, repeating rounds if necessary
        for date_idx, match_date in enumerate(active_dates):
            round_idx = date_idx % rounds
            match_datetime = timezone.make_aware(datetime.combine(match_date, datetime.min.time()))
            
            match_obj = PublicMatchModel.objects.create(
                league_id=league,
                match_day=date_idx + 1,
                match_type="regular_season",
                match_date=match_datetime,
                status="scheduled"
            )
            
            # Temporary list for rotation for this specific round
            temp_teams = list(teams)
            # Perform rotation to get the state for round_idx
            for _ in range(round_idx):
                temp_teams = [temp_teams[0]] + [temp_teams[-1]] + temp_teams[1:-1]
                
            for match_idx in range(matches_per_round):
                player_a = temp_teams[match_idx]
                player_b = temp_teams[num_teams - 1 - match_idx]
                
                if player_a and player_b:
                    PublicMatchPair.objects.create(
                        match=match_obj,
                        player_a=player_a,
                        player_b=player_b
                    )
                elif player_a or player_b:
                    # One team has a BYE
                    PublicMatchPair.objects.create(
                        match=match_obj,
                        player_a=player_a or player_b,
                        player_b=None
                    )

    @staticmethod
    def get_public_league_standings(league, match_type="regular_season"):
        """Calculates standings for a public league based on match results."""
        teams = league.teams.all()
        standings = []
        
        for team in teams:
            # sum scores from PublicMatchScoreModel for this team in this league/type
            total_points = PublicMatchScoreModel.objects.filter(
                match__league_id=league,
                match__match_type=match_type,
                player=team
            ).aggregate(total=Sum('total_points'))['total'] or 0
            
            standings.append({
                "team_id": team.id,
                "team_name": team.team_name,
                "total_points": total_points
            })
            
        # Sort by points descending
        standings.sort(key=lambda x: x['total_points'], reverse=True)
        return standings

    @staticmethod
    def get_public_playoff_winner(league):
        """Returns the winner of the playoffs (highest score in completed playoff matches)."""
        playoff_matches = PublicMatchModel.objects.filter(
            league_id=league,
            match_type="playoffs",
            status="completed"
        ).order_by('-match_day')
        
        if not playoff_matches.exists():
            return None
            
        # For simple playoffs, the winner of the last match or top total playoff score
        # Let's use the top score in the latest playoff match as the winner for now
        latest_match = playoff_matches.first()
        top_score = latest_match.player_scores.all().first() # Ordered by -total_points in Meta
        if top_score:
            return top_score.player
        return None

    @classmethod
    def process_public_match_results(cls, match):
        """Processes scores for all selections in a public match and updates pairs."""
        from apps.scoring.utils import get_selected_players_live_score
        from apps.players.models import PublicTeamSelection
        
        # 1. Get all selections for this match
        selections = match.public_selections.all()
        
        # Collect all unique GoalServe player IDs across all selections
        all_gs_player_ids = set()
        for s in selections:
            all_gs_player_ids.update(s.selected_players)
            
        # 2. Fetch real scores from GoalServe for the match date
        from apps.games.utils import get_today_games
        date_str = match.match_date.strftime("%d.%m.%Y")
        nba_games = get_today_games(date_str)
        
        real_player_scores = {} # gs_id -> points
        for game in nba_games:
            game_id = game.get('id')
            if game_id:
                scores = get_selected_players_live_score(game_id, list(all_gs_player_ids), date_str)
                for score_item in scores:
                    real_player_scores[str(score_item['player_id'])] = score_item.get('points', 0)
        
        # 3. Calculate total score for each selection
        for selection in selections:
            total = 0
            for pid in selection.selected_players:
                total += real_player_scores.get(str(pid), 0)
            selection.total_points = total
            selection.save()
            
            # Update or create PublicMatchScoreModel for standings
            PublicMatchScoreModel.objects.update_or_create(
                match=match,
                player=selection.owner,
                defaults={'total_points': total}
            )

        # 4. Update PublicMatchPairs
        for pair in match.pairs.all():
            # Get score for player_a
            try:
                sel_a = match.public_selections.get(owner=pair.player_a)
                pair.score_a = sel_a.total_points
            except Exception:
                pair.score_a = 0 # No selection = 0 points
                PublicMatchScoreModel.objects.update_or_create(
                    match=match, player=pair.player_a, defaults={'total_points': 0}
                )
                
            # Get score for player_b
            if pair.player_b:
                try:
                    sel_b = match.public_selections.get(owner=pair.player_b)
                    pair.score_b = sel_b.total_points
                except Exception:
                    pair.score_b = 0 # No selection = 0 points
                    PublicMatchScoreModel.objects.update_or_create(
                        match=match, player=pair.player_b, defaults={'total_points': 0}
                    )
            else:
                pair.score_b = 0 # BYE
                
            pair.save()
            
        # 5. Mark match as completed
        match.status = "completed"
        match.save()
        
        # 6. If it's the last regular season match, trigger playoff transition
        if match.match_type == "regular_season":
            last_match = PublicMatchModel.objects.filter(
                league_id=match.league_id, match_type="regular_season"
            ).order_by('-match_day').first()
            
            if last_match and last_match.id == match.id:
                cls.transition_public_to_playoffs(match.league_id)

    @classmethod
    def transition_public_to_playoffs(cls, league):
        """Qualifies top teams and generates playoff schedule for public leagues."""
        # Logic for selecting top 8, 4, etc. based on max_team_number
        stands = cls.get_public_league_standings(league, "regular_season")
        
        max_teams = int(league.max_team_number)
        num_qualifiers = 8 if max_teams >= 8 else 4
        
        qualifiers = stands[:num_qualifiers]
        
        from apps.users.models import UserProfile
        for i, q in enumerate(qualifiers):
            player = UserProfile.objects.get(id=q['team_id'])
            PublicPlayoffQualification.objects.get_or_create(
                league=league,
                player=player,
                defaults={
                    'regular_season_rank': i + 1,
                    'total_points': q['total_points']
                }
            )
            
        # Generate Playoff Matches (Simplified: Round Robin for now, or Brackets)
        # The user said "they will play playoff season", logic same.
        # So we can generate another round-robin for qualifiers.
        teams = [UserProfile.objects.get(id=q['team_id']) for q in qualifiers]
        
        # Reuse round-robin logic for playoffs
        # We need a new set of dates for playoffs
        cls.generate_public_playoff_matches(league, teams)

    @classmethod
    def generate_public_playoff_matches(cls, league, teams):
        """Generates round-robin matches for playoff qualifiers in public leagues."""
        num_teams = len(teams)
        if num_teams % 2 != 0:
            teams.append(None)
            num_teams += 1
            
        rounds = num_teams - 1
        matches_per_round = num_teams // 2
        
        # Determine start date for playoffs (next available date after regular season)
        from datetime import timedelta
        last_match = PublicMatchModel.objects.filter(
            league=league, match_type="regular_season"
        ).order_by('-match_date').first()
        
        start_date = (last_match.match_date + timedelta(days=1)).date() if last_match else timezone.now().date()
        
        # Get active NBA dates starting from start_date
        active_dates = cls.get_active_nba_dates(since_date=start_date)
        
        # Fallback if no dates found
        if len(active_dates) < rounds:
            for i in range(rounds - len(active_dates)):
                d = active_dates[-1] if active_dates else start_date
                active_dates.append(d + timedelta(days=i+1))

        # Generate matches
        for round_idx in range(rounds):
            match_date = active_dates[round_idx]
            match_datetime = timezone.make_aware(datetime.combine(match_date, datetime.min.time()))
            
            match_obj = PublicMatchModel.objects.create(
                league_id=league,
                match_day=round_idx + 1,
                match_type="playoffs",
                match_date=match_datetime,
                status="scheduled"
            )
            
            round_teams = list(teams)
            for match_idx in range(matches_per_round):
                player_a = round_teams[match_idx]
                player_b = round_teams[num_teams - 1 - match_idx]
                
                if player_a and player_b:
                    PublicMatchPair.objects.create(
                        match=match_obj,
                        player_a=player_a,
                        player_b=player_b
                    )
                elif player_a or player_b:
                    PublicMatchPair.objects.create(
                        match=match_obj,
                        player_a=player_a or player_b,
                        player_b=None
                    )
            
            # Rotate
            teams = [teams[0]] + [teams[-1]] + teams[1:-1]

    @staticmethod
    def create_daily_matches(league):
        """
        Ensures a match exists for the league today (Private).
        In this implementation, matches are pre-generated, so we just
        check if today's match is ready.
        """
        now = timezone.now()
        league_season = getattr(league, 'season', None)
        if not league_season:
            return False
            
        if not (league_season.is_regular_season_active or league_season.is_playoff_active):
            return False
            
        # Check if match exists for today OR if we need to advance match day
        today_match = MatchModel.objects.filter(
            league_id=league,
            match_date__date=now.date()
        ).exists()
        
        return today_match

    @staticmethod
    def create_public_daily_matches(league):
        """
        Ensures a match exists for the league today (Public).
        """
        now = timezone.now()
        league_season = getattr(league, 'season', None)
        if not league_season:
            return False
            
        if not (league_season.is_regular_season_active or league_season.is_playoff_active):
            return False
            
        today_match = PublicMatchModel.objects.filter(
            league_id=league,
            match_date__date=now.date()
        ).exists()
        
        return today_match


