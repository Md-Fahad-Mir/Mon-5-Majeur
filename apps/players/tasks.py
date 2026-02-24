import logging
from celery import shared_task
from .utils import get_today_players

logger = logging.getLogger(__name__)

@shared_task
def fetch_today_players_task():
    """
    Background task to pre-fetch and cache all players for today's games.
    Runs every hour.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    
    today = datetime.now(ZoneInfo("America/New_York")).strftime("%d.%m.%Y")
    logger.info(f"Executing fetch_today_players_task for date: {today}")
    
    try:
        # get_today_players handles the internal multi-layer caching
        players = get_today_players(today)
        logger.info(f"Successfully cached {len(players)} players for {today}")
    except Exception as e:
        logger.error(f"Failed to fetch today's players in background: {str(e)}")
