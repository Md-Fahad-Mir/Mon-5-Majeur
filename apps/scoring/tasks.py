import logging
from celery import shared_task
from .utils import get_all_player_scores_for_date

logger = logging.getLogger(__name__)

@shared_task
def fetch_live_scores_task():
    """
    Background task to fetch and cache live scores for today's NBA games.
    Runs every 5 minutes.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    
    # Live scores are relevant for today's date in New York
    today = datetime.now(ZoneInfo("America/New_York")).strftime("%d.%m.%Y")
    logger.info(f"Executing fetch_live_scores_task for date: {today}")
    
    try:
        # get_all_player_scores_for_date handles caching internally
        scores = get_all_player_scores_for_date(today)
        logger.info(f"Successfully refreshed live scores for {len(scores)} players")
    except Exception as e:
        logger.error(f"Failed to fetch live scores in background: {str(e)}")
