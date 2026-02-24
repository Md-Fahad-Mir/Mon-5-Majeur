import requests
from django.conf import settings
from django.core.cache import cache
from datetime import datetime
from core.utils import requests_get

from zoneinfo import ZoneInfo

def get_today_games(date_str: str = None):
    api_key = settings.GOALSERVE_API_KEY

    # Use provided date or fallback to NBA Timer (US Eastern)
    if not date_str:
        target_date = datetime.now(ZoneInfo("America/New_York")).strftime("%d.%m.%Y")
    else:
        target_date = date_str

    # 1. Check process results cache (15 mins)
    res_cache_key = f"today_games_list_{target_date}"
    cached_res = cache.get(res_cache_key)
    if cached_res:
        return cached_res

    # Log that we're missing background data
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Cache miss for {res_cache_key}. Background worker may be delayed.")

    # 2. Check raw schedule cache (1 hour)
    sched_cache_key = "nba_schedule_raw_data"
    data = cache.get(sched_cache_key)
    
    if not data:
        url = f'https://www.goalserve.com/getfeed/{api_key}/bsktbl/nba-shedule?json=1'
        try:
            # Fallback only if absolutely necessary
            response = requests_get(url) 
            if response is None:
                return []
            response.raise_for_status()
            data = response.json()
            cache.set(sched_cache_key, data, 3600)
        except Exception as e:
            logger.error(f"Fallback fetch failed: {e}")
            return []
    
    today_games = []
    # ... extraction logic remains same ...

    for matchday in data.get("shedules", {}).get("matches", []):
        if matchday.get("formatted_date") == target_date:
            matches = matchday.get("match", [])
            if isinstance(matches, dict):
                matches = [matches]  # normalize

            for game in matches:
                today_games.append({
                    "id": game.get("id"),
                    "home_team": game["hometeam"]["name"],
                    "home_team_id": game["hometeam"]["id"],
                    "away_team": game["awayteam"]["name"],
                    "away_team_id": game["awayteam"]["id"],
                    "game_time": game.get("time"),
                    "status": game.get("status"),
                    "venue": game.get("venue_name"),
                    "timezone": game.get("timezone"),
                    "datetime_utc": game.get("datetime_utc"),
                })

    # Cache the final list for 15 minutes
    if today_games:
        cache.set(res_cache_key, today_games, 900)

    return today_games
                

