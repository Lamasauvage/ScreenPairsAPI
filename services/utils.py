import requests
import logging
from requests.exceptions import RequestException, HTTPError, Timeout
import json

logger = logging.getLogger(__name__)

class TMDBServiceError(Exception):
    pass

def make_tmdb_request(url, headers, method='GET', params=None, timeout=5, action_description="making TMDB request"):
    logger.debug(f"TMDB API call: {method} {url} - Action: {action_description}")
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            timeout=timeout
        )
        response.raise_for_status()

        data = response.json()
        return data

    except Timeout:
        logger.error(f"TMDB Timeout while {action_description} (URL: {url})")
        raise TMDBServiceError(f"Timeout communicating with TMDB API while {action_description}.")
    except HTTPError as http_err:
        status_code = http_err.response.status_code
        logger.error(f"TMDB HTTP error {status_code} while {action_description} (URL: {url}): {http_err}")
        raise TMDBServiceError(f"TMDB API returned HTTP error {status_code} while {action_description}.")
    except RequestException as req_err:
        logger.error(f"TMDB Request error while {action_description} (URL: {url}): {req_err}")
        raise TMDBServiceError(f"Network error connecting to TMDB API while {action_description}.")
    except json.JSONDecodeError as json_err:
        logger.error(f"TMDB JSON decode error while {action_description} (URL: {url}): {json_err}")
        raise TMDBServiceError(f"Invalid JSON response from TMDB API while {action_description}.")
    except Exception as e:
        logger.exception(f"Unexpected error during TMDB request while {action_description} (URL: {url})")
        raise TMDBServiceError(f"An unexpected error occurred while {action_description}.")