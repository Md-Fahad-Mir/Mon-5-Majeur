# players/utils.py
import logging
import time
import requests
from requests.exceptions import ReadTimeout, RequestException
from django.conf import settings
from django.core.cache import cache
from datetime import datetime
from apps.games.utils import get_today_games   # re-use existing schedule function
from core.utils import requests_get

GOALSERVE_BASE = "https://www.goalserve.com/getfeed"

# Pricing configuration
PRICE_MIN = 5000000
PRICE_MAX = 25000000

# Weights for fantasy score calculation
FANTASY_WEIGHTS = {
    "points_per_game": 1.0,
    "rebounds_per_game": 1.2,
    "assists_per_game": 1.5,
    "steals_per_game": 3.0,
    "blocks_per_game": 3.0,
}


def get_team_roster(team_id: str):
    """Fetch roster of a team by ID."""
    cache_key = f"team_roster_v2_{team_id}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    api_key = settings.GOALSERVE_API_KEY
    url = f"{GOALSERVE_BASE}/{api_key}/bsktbl/{team_id}_rosters?json=1"
    r = requests_get(url)
    if r is None:
        return {}
    try:
        r.raise_for_status()
        data = r.json()
        if data:
            cache.set(cache_key, data, 43200)  # 12 hours
        return data
    except Exception:
        return {}


def get_team_injuries(team_id: str):
    """Fetch injury report of a team by ID."""
    cache_key = f"team_injuries_{team_id}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    api_key = settings.GOALSERVE_API_KEY
    url = f"{GOALSERVE_BASE}/{api_key}/bsktbl/{team_id}_injuries?json=1"
    r = requests_get(url)
    if r is None:
        return {}
    try:
        r.raise_for_status()
        data = r.json()
        if data:
            cache.set(cache_key, data, 3600)  # 1 hour
        return data
    except Exception:
        return {}


def get_today_players(date_str: str = None):
    """
    Build list of all players from today's games:
    - Get schedule
    - Fetch rosters
    - Mark injuries
    """
    logger = logging.getLogger(__name__)
    
    # Normalize date for cache key
    if not date_str:
        from zoneinfo import ZoneInfo
        target_date = datetime.now(ZoneInfo("America/New_York")).strftime("%d.%m.%Y")
    else:
        target_date = date_str

    cache_key = f"today_players_list_{target_date}"
    cached_players = cache.get(cache_key)
    if cached_players:
        return cached_players

    # Log cache miss for background data
    logger.warning(f"Cache miss for {cache_key}. Background worker may be delayed.")

    games = get_today_games(target_date) or []
    players = []

    seen = set()  # dedupe by player id

    # helper to safely cast string numbers to float
    def _to_float(val):
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0

    for game in games:
        # prefer flattened keys, fall back to legacy nested keys
        home_id = game.get("home_team_id") or (game.get("hometeam") or {}).get("id")
        away_id = game.get("away_team_id") or (game.get("awayteam") or {}).get("id")

        for tid in (home_id, away_id):
            if not tid:
                logger.debug("Skipping empty team id for game: %s", game.get("id"))
                continue

            try:
                roster = get_team_roster(tid) or {}
            except Exception as e:
                logger.exception("Failed to fetch roster for team %s: %s", tid, e)
                continue

            try:
                injuries = get_team_injuries(tid) or {}
            except Exception as e:
                logger.exception("Failed to fetch injuries for team %s: %s", tid, e)
                injuries = {}

            try:
                stats = get_team_stats(tid) or {}
            except Exception as e:
                logger.exception("Failed to fetch stats for team %s: %s", tid, e)
                stats = {}

            # Build set of injured player ids
            injured_ids = set()
            for item in (injuries.get("injuries", {}).get("player") or []):
                pid = item.get("id")
                if pid:
                    injured_ids.add(str(pid))

            # Build stats map: id -> aggregated player stats
            stats_map = {}
            stats_name_map = {}
            for category in stats.get("statistic", {}).get("category", []) or []:
                players_list = category.get("player", [])
                if isinstance(players_list, dict):
                    players_list = [players_list]
                for s in players_list:
                    sid = s.get("id")
                    name = (s.get("name") or "").strip().lower()
                    if sid:
                        stats_map[str(sid)] = s
                    if name:
                        stats_name_map[name] = s

            # Roster may appear under roster['team']['player'] or roster['rosters']['player']
            roster_players = []
            team_name = None
            team_id_from_roster = None
            if roster.get("team") and roster["team"].get("player"):
                roster_players = roster["team"].get("player") or []
                team_name = roster.get("team", {}).get("name")
                team_id_from_roster = roster.get("team", {}).get("id")
            elif roster.get("rosters") and roster["rosters"].get("player"):
                roster_players = roster["rosters"].get("player") or []
                team_name = roster.get("rosters", {}).get("name")
                team_id_from_roster = roster.get("rosters", {}).get("id")
            else:
                roster_players = roster.get("player") or []

            # If no id was found in roster payload, use tid (the team id we called)
            if not team_id_from_roster:
                team_id_from_roster = str(tid)

            # Normalize single dict to list
            if isinstance(roster_players, dict):
                roster_players = [roster_players]

            for player in roster_players:
                pid = player.get("id")
                if not pid:
                    continue
                pid_str = str(pid)
                if pid_str in seen:
                    continue
                seen.add(pid_str)

                # derive status
                status = "OUT" if pid_str in injured_ids else "OK"

                # compute fantasy score from stats_map (try id then name)
                pstats = stats_map.get(pid_str)
                if not pstats:
                    pname = (player.get("name") or player.get("full_name") or "").strip().lower()
                    pstats = stats_name_map.get(pname, {})
                pts = _to_float(pstats.get("points_per_game") or pstats.get("pts") or pstats.get("points"))
                reb = _to_float(pstats.get("rebounds_per_game") or pstats.get("reb") or pstats.get("rebounds"))
                ast = _to_float(pstats.get("assists_per_game") or pstats.get("ast") or pstats.get("assists"))
                stl = _to_float(pstats.get("steals_per_game") or pstats.get("stl") or pstats.get("steals"))
                blk = _to_float(pstats.get("blocks_per_game") or pstats.get("blk") or pstats.get("blocks"))

                raw_score = (
                    pts * FANTASY_WEIGHTS["points_per_game"] +
                    reb * FANTASY_WEIGHTS["rebounds_per_game"] +
                    ast * FANTASY_WEIGHTS["assists_per_game"] +
                    stl * FANTASY_WEIGHTS["steals_per_game"] +
                    blk * FANTASY_WEIGHTS["blocks_per_game"]
                )

                # capture salary numeric for fallback normalization
                salary_raw = player.get("salary") or player.get("salary_usd") or ""
                players.append({
                    "id": pid_str,
                    "name": player.get("name") or player.get("full_name"),
                    "position": player.get("pos") or player.get("position"),
                    "team": team_name or player.get("team") or "Unknown",
                    "team_id": str(team_id_from_roster),
                    "status": status,
                    "_raw_score": raw_score,
                    "_salary_raw": salary_raw,
                })

    # Normalize scores to prices
    # Prefer to normalize using positive raw scores
    positive_scores = [p.get("_raw_score", 0.0) for p in players if p.get("_raw_score", 0.0) > 0]
    max_score = max(positive_scores) if positive_scores else 0.0

    if max_score <= 0:
        # Fallback: derive scores from salary if available
        def parse_salary(sal):
            if not sal:
                return 0.0
            # remove non-digits and convert to millions
            import re
            digits = re.sub(r"[^0-9]", "", str(sal))
            try:
                v = float(digits)
                return v / 1_000_000.0
            except Exception:
                return 0.0

        salary_scores = [parse_salary(p.get("_salary_raw")) for p in players]
        max_salary_score = max(salary_scores) if salary_scores else 0.0
        if max_salary_score <= 0:
            # last resort: assign min price to everyone
            for p in players:
                p["price"] = PRICE_MIN
                p.pop("_raw_score", None)
                p.pop("_salary_raw", None)
            return players

        for p, s_val in zip(players, salary_scores):
            # scale salary-derived score into price range
            price = PRICE_MIN + (s_val / max_salary_score) * (PRICE_MAX - PRICE_MIN)
            p["price"] = int(round(price))
            p.pop("_raw_score", None)
            p.pop("_salary_raw", None)
        return players

    # Normal path: scale by raw_score
    for p in players:
        score = p.get("_raw_score", 0.0)
        price = PRICE_MIN + (score / max_score) * (PRICE_MAX - PRICE_MIN)
        p["price"] = int(round(price))
        p.pop("_raw_score", None)
        p.pop("_salary_raw", None)

    if players:
        cache.set(cache_key, players, 3600)  # 1 hour top-level cache

    return players




def get_team_stats(team_id: str):
    """Fetch season stats for a team."""
    cache_key = f"team_stats_v2_{team_id}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    api_key = settings.GOALSERVE_API_KEY
    url = f"{GOALSERVE_BASE}/{api_key}/bsktbl/{team_id}_stats?json=1"
    r = requests_get(url)
    if r is None:
        return {}
    try:
        r.raise_for_status()
        data = r.json()
        if data:
            cache.set(cache_key, data, 43200)  # 12 hours
        return data
    except Exception:
        return {}

def get_player_images():
    """Fetch NBA/NCAA player images."""
    api_key = settings.GOALSERVE_API_KEY
    url = f"{GOALSERVE_BASE}/{api_key}/bsktbl/usa?playerimage=2011&json=1"
    r = requests_get(url)
    if r is None:
        return {}
    try:
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def _num(v):
    """Helper to safely parse numeric stat values"""
    try:
        return float(v) if v not in (None, "", " ") else None
    except Exception:
        return None

def get_player_details(team_id: str, player_id: str):
    roster = get_team_roster(team_id) or {}
    stats_data = get_team_stats(team_id) or {}
    
    player_info = None

    # 1. Find player in roster (basic info)
    roster_players = []
    if roster.get("team") and roster["team"].get("player"):
        roster_players = roster["team"].get("player") or []
    elif roster.get("rosters") and roster["rosters"].get("player"):
        roster_players = roster["rosters"].get("player") or []
    else:
        roster_players = roster.get("player") or []

    if isinstance(roster_players, dict):
        roster_players = [roster_players]

    for p in roster_players:
        if str(p.get("id")) == str(player_id):
            player_info = p
            break

    if not player_info:
        raise ValueError("Player not found in roster")

    # 2. Find player in stats (performance info) - try by id, then by name
    stats_map = {}
    stats_name_map = {}
    
    # GoalServe stats can be a list of categories or a single category dict
    categories = stats_data.get("statistic", {}).get("category", [])
    if isinstance(categories, dict):
        categories = [categories]
        
    for category in categories:
        players_list = category.get("player", [])
        if isinstance(players_list, dict):
            players_list = [players_list]
            
        for s in players_list:
            sid = str(s.get("id")) if s.get("id") else None
            name = (s.get("name") or "").strip().lower()
            
            target_obj = None
            if sid and sid != "None":
                if sid not in stats_map:
                    stats_map[sid] = {}
                target_obj = stats_map[sid]
            elif name:
                if name not in stats_name_map:
                    stats_name_map[name] = {}
                target_obj = stats_name_map[name]
            
            if target_obj is not None:
                # Merge new stats into existing ones
                target_obj.update(s)

    player_stats = stats_map.get(str(player_id))
    if not player_stats and player_info:
        pname = (player_info.get("name") or player_info.get("full_name") or "").strip().lower()
        player_stats = stats_name_map.get(pname, {})

    # Build the stats dict with all possible aliases
    all_stats = {
        "games_played": _num(player_stats.get("games_played") or player_stats.get("gp") or player_stats.get("g")),
        "minutes": _num(player_stats.get("minutes_per_game") or player_stats.get("minutes") or player_stats.get("min") or player_stats.get("m")),
        "points": _num(player_stats.get("points_per_game") or player_stats.get("pts") or player_stats.get("points") or player_stats.get("p")),
        "rebounds": _num(player_stats.get("rebounds_per_game") or player_stats.get("reb") or player_stats.get("rebounds") or player_stats.get("tot_reb") or player_stats.get("r")),
        "assists": _num(player_stats.get("assists_per_game") or player_stats.get("ast") or player_stats.get("assists") or player_stats.get("a")),
        "steals": _num(player_stats.get("steals_per_game") or player_stats.get("stl") or player_stats.get("steals") or player_stats.get("s")),
        "blocks": _num(player_stats.get("blocks_per_game") or player_stats.get("blk") or player_stats.get("blocks") or player_stats.get("b")),
        "fg_pct": _num(player_stats.get("fg_pct") or player_stats.get("fgp") or player_stats.get("fg_percentage")),
        "three_pct": _num(player_stats.get("three_point_pct") or player_stats.get("tpp") or player_stats.get("3p_pct") or player_stats.get("3p_percentage") or player_stats.get("fg3_pct")),
        "ft_pct": _num(player_stats.get("free_throws_pct") or player_stats.get("ftp") or player_stats.get("ft_percentage")),
        "fg_attempts": _num(player_stats.get("fg_attempts_per_game") or player_stats.get("fga") or player_stats.get("fg_att")),
        "three_attempts": _num(player_stats.get("three_point_attempts_per_game") or player_stats.get("tpa") or player_stats.get("3pa") or player_stats.get("fg3a")),
        "ft_attempts": _num(player_stats.get("free_throws_attempts_per_game") or player_stats.get("fta") or player_stats.get("ft_att")),
        "turnovers": _num(player_stats.get("turnovers_per_game") or player_stats.get("to") or player_stats.get("tov")),
        "personal_fouls": _num(player_stats.get("personal_fouls_per_game") or player_stats.get("pf")),
    }
    
    # Remove null values from stats
    valid_stats = {k: v for k, v in all_stats.items() if v is not None}

    response_data = {
        "id": player_id,
        "name": player_info.get("name") or player_info.get("full_name"),
        "team": roster.get("team", {}).get("name") or roster.get("rosters", {}).get("name") or player_info.get("team"),
        "position": player_info.get("pos") or player_info.get("position"),
        "age": player_info.get("age"),
        "height": player_info.get("height") or player_info.get("heigth"),   
        "weight": player_info.get("weight") or player_info.get("weigth"),  
        "college": player_info.get("college"),
        "salary": player_info.get("salary"),
        "stats": valid_stats
    }
    
    # Final cleanup of null values from the main player record
    return {k: v for k, v in response_data.items() if v is not None}




def format_currency(value):
    """Format 1200000 -> 1.2M with max 1 decimal."""
    try:
        val = float(value)
    except (ValueError, TypeError):
        return "0M"
        
    if val < 1_000_000:
        m_val = val / 1_000_000
        return f"{m_val:.1f}M".replace(".0M", "M")
        
    m_val = val / 1_000_000
    formatted = f"{m_val:.1f}"
    if formatted.endswith('.0'):
        return f"{int(m_val)}M"
    return f"{formatted}M"
