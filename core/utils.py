import logging
import time
import requests
import gzip
from requests.exceptions import ReadTimeout, RequestException
from django.conf import settings

def requests_get(url: str, timeout: int | None = None, max_retries: int = 3, backoff_factor: float = 0.5):
    """Perform requests.get with simple retry/backoff and configurable timeout.

    Returns the `requests.Response` on success or `None` on repeated failures.
    """
    logger = logging.getLogger(__name__)
    t = timeout or getattr(settings, "GOALSERVE_TIMEOUT", 10)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=t)
            
            # Manual decompression if server forgot Content-Encoding header
            # Magic number for gzip is 1f 8b
            if response.content[:2] == b'\x1f\x8b':
                try:
                    # Decompress and replace content
                    decompressed_data = gzip.decompress(response.content)
                    response._content = decompressed_data
                    # Add header to prevent downstream confusion
                    response.headers['Content-Encoding'] = 'gzip' 
                except Exception as e:
                    logger.warning("Failed to manually decompress gzip content: %s", e)

            return response

        except ReadTimeout as e:
            logger.warning("ReadTimeout fetching %s (attempt %d/%d)", url, attempt, max_retries)
            if attempt == max_retries:
                logger.exception("Giving up fetching %s after %d attempts", url, attempt)
                return None
            time.sleep(backoff_factor * attempt)
        except RequestException as e:
            # Non-timeout network errors (DNS, connection, etc.) - log and stop
            logger.exception("Request failed for %s: %s", url, e)
            return None
