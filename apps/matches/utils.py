from datetime import datetime
from typing import Optional
import requests
from django.conf import settings
from core.utils import requests_get

DATE_FORMAT = "%b %d, %Y"


def parse_goalsrv_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    return datetime.strptime(date_str, DATE_FORMAT)


def extract_season_boundaries(matches: list) -> dict:
    buckets = {
        "Regular season": [],
        "Postseason": [],
    }

    for day in matches:
        season_type = day.get("seasonType")
        date = parse_goalsrv_date(day.get("date"))

        if season_type in buckets and date:
            buckets[season_type].append(date)

    return {
        "regular_season": {
            "start": min(buckets["Regular season"]) if buckets["Regular season"] else None,
            "end": max(buckets["Regular season"]) if buckets["Regular season"] else None,
        },
        "playoffs": {
            "start": min(buckets["Postseason"]) if buckets["Postseason"] else None,
            "end": max(buckets["Postseason"]) if buckets["Postseason"] else None,
        },
    }





def get_nba_season_metadata() -> Optional[dict]:
    api_key = settings.GOALSERVE_API_KEY
    url = f"https://www.goalserve.com/getfeed/{api_key}/bsktbl/nba-shedule?json=1"

    try:
        response = requests_get(url)
        if response is None:
             raise Exception("GoalServe API returned None")
             
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        raise Exception(f"GoalServe API error: {e}")

    schedules = data.get("shedules")
    if not schedules:
        return None

    matches = schedules.get("matches", [])
    season = schedules.get("season")

    boundaries = extract_season_boundaries(matches)

    return {
        "season": season,
        **boundaries,
    }
