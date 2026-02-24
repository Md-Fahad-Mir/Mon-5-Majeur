from django.conf import settings
from django.core.cache import cache
from datetime import datetime
from typing import Optional
from core.utils import requests_get


# ---------- SCHEDULE ----------

def fetch_nba_schedule() -> dict:
    """
    Fetches NBA schedule from GoalServe API with caching.
    
    Returns:
        dict: Schedule data or empty dict on failure
    """
    sched_cache_key = "nba_schedule_raw_data"
    data = cache.get(sched_cache_key)
    if data:
        return data

    api_key = settings.GOALSERVE_API_KEY
    url = f"https://www.goalserve.com/getfeed/{api_key}/bsktbl/nba-shedule?json=1"
    
    try:
        r = requests_get(url)
        if r is None:
            return {}
        r.raise_for_status()
        data = r.json()
        
        # Cache raw data for 1 hour
        cache.set(sched_cache_key, data, 3600)
        return data
    except Exception as e:
        # Log the error in production
        # logger.error(f"Failed to fetch NBA schedule: {str(e)}")
        return {}


def get_recent_matches(days_back: int = 7) -> list[dict]:
    """
    Retrieves recent NBA matches within specified days.
    
    Args:
        days_back: Number of days to look back from today
        
    Returns:
        list[dict]: List of match dictionaries with essential info
        
    Why: Filtering by date range client-side allows us to cache the schedule
    data and reduces API calls. The structured response format ensures
    consistent data shape for frontend consumption.
    """
    data = fetch_nba_schedule()
    today = datetime.today().date()
    matches = []

    for day in data.get("shedules", {}).get("matches", []):
        date_str = day.get("formatted_date")
        if not date_str:
            continue

        try:
            match_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        except ValueError:
            continue
            
        if (today - match_date).days > days_back:
            continue

        day_matches = day.get("match", [])
        # Normalize to list for consistent iteration
        if isinstance(day_matches, dict):
            day_matches = [day_matches]

        for m in day_matches:
            matches.append({
                "match_id": m.get("id"),
                "date": date_str,
                "status": m.get("status"),
                "home_team": m.get("hometeam", {}).get("name"),
                "home_team_id": m.get("hometeam", {}).get("id"),
                "away_team": m.get("awayteam", {}).get("name"),
                "away_team_id": m.get("awayteam", {}).get("id"),
            })

    return matches


def get_match_by_id(match_id: str) -> Optional[dict]:
    """
    Finds a specific match by ID from recent matches.
    
    Args:
        match_id: The match identifier
        
    Returns:
        dict or None: Match data if found
        
    Why: Helper function to avoid code duplication. Looking back 30 days
    ensures we cover most use cases while keeping the search space reasonable.
    """
    for match in get_recent_matches(30):
        if str(match["match_id"]) == str(match_id):
            return match
    return None


# ---------- SCORES ----------

def normalize_date_format(date_str: str) -> str:
    """
    Normalizes date format for GoalServe API to DD.MM.YYYY.
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        str: Normalized date string (DD.MM.YYYY)
        
    Why: GoalServe API requires dates with leading zeros (e.g., "09.01.2026").
    This function ensures the format is consistent regardless of input.
    """
    parts = date_str.split('.')
    if len(parts) == 3:
        day, month, year = parts
        return f"{day.zfill(2)}.{month.zfill(2)}.{year}"
    return date_str


def get_match_boxscore(match_id: str, date: str) -> dict:
    """
    Fetches boxscore data for a specific match and date.
    
    Args:
        match_id: The match identifier
        date: Date string in DD.MM.YYYY or D.MM.YYYY format (mandatory)
        
    Returns:
        dict: Match boxscore data or empty dict if not found
        
    Why: Date is mandatory because GoalServe's historical data endpoint requires it.
    This ensures we're always querying the correct game data. The function handles
    both single match and multi-match responses from the API.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    api_key = settings.GOALSERVE_API_KEY
    date_normalized = normalize_date_format(date)
    
    url = f"https://www.goalserve.com/getfeed/{api_key}/bsktbl/nba-scores?date={date_normalized}&json=1"
    
    logger.info(f"Fetching boxscore: match_id={match_id}, original_date={date}, normalized_date={date_normalized}")
    
    try:
        r = requests_get(url)
        if r is None:
            logger.error(f"requests_get returned None for URL: {url}")
            return {}
            
        r.raise_for_status()
        data = r.json()
        
        # Log the structure for debugging
        logger.debug(f"API response keys: {data.keys()}")
        
        matches = data.get("scores", {}).get("category", {}).get("match", [])
        
        # Normalize to list for consistent processing
        if isinstance(matches, dict):
            matches = [matches]
        
        logger.info(f"Found {len(matches)} matches for date {date_normalized}")
        
        # Log all available match IDs for debugging
        available_ids = [str(m.get("id")) for m in matches]
        logger.info(f"Available match IDs: {available_ids}")
        
        # Find the specific match by ID
        for match in matches:
            if str(match.get("id")) == str(match_id):
                logger.info(f"Match found: {match_id}")
                return match
        
        logger.warning(f"Match {match_id} not found in {len(matches)} matches for date {date_normalized}")
                
    except Exception as e:
        logger.error(f"Failed to fetch boxscore for match {match_id}, date {date}: {str(e)}", exc_info=True)
    
    return {}


def extract_player_scores(boxscore: dict) -> dict:
    """
    Extracts player statistics from boxscore data.
    
    Args:
        boxscore: Match boxscore dictionary from GoalServe API
        
    Returns:
        dict: Player ID mapped to their stats {player_id: {name, points, rebounds, assists, minutes}}
        
    Why: GoalServe returns nested player data under 'player_stats' with separate
    'starting' and 'bench' categories. This function flattens the structure and
    normalizes it to a simple player_id: stats mapping for easier lookup.
    We handle both dict and list formats since the API returns single players as dicts.
    """
    players = {}
    
    stats_root = boxscore.get("player_stats")
    if not stats_root:
        return {}

    def parse_player_list(p_list):
        """
        Inner helper to parse player list/dict and extract stats.
        
        Why: DRY principle - both teams have the same structure, so we
        extract this logic to avoid duplication.
        """
        if not p_list:
            return
            
        # Normalize single player dict to list
        if isinstance(p_list, dict):
            p_list = [p_list]
            
        for p in p_list:
            pid = str(p.get("id"))
            if not pid:
                continue
                
            players[pid] = {
                "name": p.get("name"),
                "points": int(p.get("points", 0)),
                "rebounds": int(p.get("total_rebounds", 0)),
                "assists": int(p.get("assists", 0)),
                "minutes": p.get("minutes"),
            }

    # Process both teams
    for side in ("hometeam", "awayteam"):
        team_data = stats_root.get(side)
        if not team_data:
            continue
        
        # Check for both 'starting' and 'bench' categories
        for subgroup in ["starting", "bench"]:
            if subgroup in team_data:
                sub = team_data[subgroup]
                if "player" in sub:
                    parse_player_list(sub.get("player"))

    return players


# ---------- PLAYERS ----------

def get_match_players(match_id: str, date: str) -> list[dict]:
    """
    Retrieves all players who participated in a specific match.
    
    Args:
        match_id: The match identifier
        date: Date string in DD.MM.YYYY format (mandatory)
        
    Returns:
        list[dict]: List of player dictionaries with id, name, position, team
        
    Why: This endpoint is used to show available players before the user
    selects specific ones for detailed stats. Date is mandatory to ensure
    we query the correct game data. Using a set for 'seen' ensures no
    duplicate players in the response.
    """
    boxscore = get_match_boxscore(match_id, date)
    if not boxscore:
        return []

    stats_root = boxscore.get("player_stats")
    if not stats_root:
        return []

    players = []
    seen = set()

    def extract_from_list(p_list, team_name):
        """
        Helper to extract player metadata from list/dict.
        
        Why: Keeps track of seen players to avoid duplicates and
        associates each player with their team.
        """
        if not p_list:
            return
            
        if isinstance(p_list, dict):
            p_list = [p_list]
            
        for p in p_list:
            pid = str(p.get("id"))
            if not pid or pid in seen:
                continue
                
            seen.add(pid)
            players.append({
                "player_id": pid,
                "name": p.get("name"),
                "position": p.get("pos") or p.get("position"),
                "team": team_name,
            })

    # Process both teams
    for side in ("hometeam", "awayteam"):
        team_data = stats_root.get(side)
        if not team_data:
            continue
        
        # Get team name from the parent boxscore object
        team_name = boxscore.get(side, {}).get("name", side)
        
        # Process starting and bench players
        for subgroup in ["starting", "bench"]:
            if subgroup in team_data:
                sub = team_data[subgroup]
                if "player" in sub:
                    extract_from_list(sub.get("player"), team_name)

    return players


def get_all_player_scores_for_date(date_str: str) -> dict:
    """
    Fetches and flattens all player scores for all NBA games on a specific date.
    Caches the results for 5 minutes.
    
    Args:
        date_str: Date string in DD.MM.YYYY format
        
    Returns:
        dict: Mapping of player_id -> stats dict
    """
    import logging
    logger = logging.getLogger(__name__)
    
    date_normalized = normalize_date_format(date_str)
    cache_key = f"nba_scores_all_players_{date_normalized}"
    cached_data = cache.get(cache_key)
    
    # cached_data could be {} from a previous failure (negative cache)
    if cached_data is not None:
        return cached_data

    logger.warning(f"Cache miss for {cache_key}. Background scoring task may be delayed.")

    api_key = settings.GOALSERVE_API_KEY
    url = f"https://www.goalserve.com/getfeed/{api_key}/bsktbl/nba-scores?date={date_normalized}&json=1"
    
    all_player_scores = {}
    
    try:
        logger.info(f"Fetching ALL NBA scores for date: {date_normalized}")
        r = requests_get(url)
        if r is None:
            raise Exception("No response from GoalServe")
            
        r.raise_for_status()
        data = r.json()
        
        matches = data.get("scores", {}).get("category", {}).get("match", [])
        if isinstance(matches, dict):
            matches = [matches]
            
        for match_data in matches:
            game_player_scores = extract_player_scores(match_data)
            all_player_scores.update(game_player_scores)
            
        # Cache successful results for 5 minutes
        cache.set(cache_key, all_player_scores, 300)
        logger.info(f"Successfully cached scores for {len(all_player_scores)} players on {date_normalized}")
        
    except Exception as e:
        logger.error(f"Failed to fetch global NBA scores for {date_normalized}: {str(e)}")
        # Negative cache: cache empty result for 2 minutes to prevent hammering the failing API
        cache.set(cache_key, {}, 120)
        
    return all_player_scores


def get_selected_players_live_score(
    match_id: str,
    selected_player_ids: list[str],
    date: str
) -> list[dict]:
    """
    Retrieves scores for specific players in a match.
    
    Args:
        match_id: The match identifier
        selected_player_ids: List of player IDs to retrieve scores for
        date: Date string in DD.MM.YYYY format (mandatory)
        
    Returns:
        list[dict]: List of player score dictionaries with id, name, points, rebounds, assists, minutes
        
    Why: This is the main endpoint for getting player stats. We only return
    data for requested players to reduce response size. Date is mandatory
    because we need it to query the historical data API. The response is a
    simple list of player objects (not wrapped in match object) as per requirements.
    """
    # Use the new cached global score fetcher
    all_scores = get_all_player_scores_for_date(date)
    if not all_scores:
        return []

    players = []
    for pid in selected_player_ids:
        pid_str = str(pid)
        if pid_str in all_scores:
            players.append({
                "player_id": pid_str,
                **all_scores[pid_str],
            })

    return players