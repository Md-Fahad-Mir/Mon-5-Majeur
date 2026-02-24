import logging
from celery import shared_task
from django.core.cache import cache
from .utils import get_today_games
from apps.scoring.utils import fetch_nba_schedule

logger = logging.getLogger(__name__)

@shared_task
def fetch_nba_schedule_task():
    """
    Background task to fetch NBA schedule and populate Redis.
    Runs every hour.
    """
    logger.info("Executing fetch_nba_schedule_task")
    # This will use the internal caching logic of fetch_nba_schedule 
    # but we force a fresh fetch by bypass (or relying on its own expiry)
    # Actually, fetch_nba_schedule already handles caching.
    # We want this task to actively refresh even if not expired.
    
    # Let's directly call the API and update cache
    data = fetch_nba_schedule()
    if data:
        logger.info("Successfully refreshed NBA schedule via background task.")
    else:
        logger.warning("Failed to refresh NBA schedule via background task.")
    
    # also pre-populate today's games list for common dates
    from datetime import datetime
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("America/New_York")).strftime("%d.%m.%Y")
    get_today_games(today)
    logger.info(f"Pre-populated today's games for {today}")
