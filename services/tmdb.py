import requests
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)
HEADERS = {"Authorization": f"Bearer {settings.TMDB_BEARER_TOKEN}"}


def search_actors(query):
    if not query:
        return []

    url = f"https://api.themoviedb.org/3/search/person?query={query}&include_adult=false"
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.warning(f"TMDB search_actors error: {e}")
        return []

    top_results = data.get("results", [])[:5]
    results = [{
        'id': actor['id'],
        'name': actor['name'],
        'profile_path': actor.get('profile_path'),
        'popularity': actor.get('popularity', 0),
    } for actor in top_results]
    return sorted(results, key=lambda x: x['popularity'], reverse=True)


def get_actor_info(actor_name):
    url = f"https://api.themoviedb.org/3/search/person?query={actor_name}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.warning(f"TMDB get_actor_info error: {e}")
        return None

    if data.get('results'):
        return {
            'id': data['results'][0]['id'],
            'image_path': data['results'][0].get('profile_path')
        }
    return None


def get_movies_by_actor(actor_id):
    url = f"https://api.themoviedb.org/3/person/{actor_id}/movie_credits"
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.warning(f"TMDB get_movies_by_actor error: {e}")
        return []

    return [{
        'id': movie['id'],
        'character': movie.get('character')
    } for movie in data.get('cast', [])]


def fetch_common_movie_details(movie_id, actor1_character, actor2_character):
    cache_key = f"movie_{movie_id}_details"
    cached_movie = cache.get(cache_key)
    if cached_movie:
        return cached_movie

    url = f"https://api.themoviedb.org/3/movie/{movie_id}?append_to_response=credits,external_ids"
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.warning(f"TMDB fetch_common_movie_details error: {e}")
        return None

    directors = [crew['name'] for crew in data.get('credits', {}).get('crew', []) if crew['job'] == 'Director']
    imdb_id = data.get('external_ids', {}).get('imdb_id')
    imdb_url = f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else None

    movie_details = {
        'id': movie_id,
        'imdb_url': imdb_url,
        'title': data.get('title'),
        'poster_path': data.get('poster_path'),
        'release_year': data.get('release_date', '').split('-')[0],
        'directors': directors,
        'characters': {
            'actor1': actor1_character,
            'actor2': actor2_character
        }
    }

    cache.set(cache_key, movie_details, timeout=60 * 60 * 24)
    return movie_details


def find_common_movies(actor1_name, actor2_name):
    actor1_info = get_actor_info(actor1_name)
    actor2_info = get_actor_info(actor2_name)

    if not actor1_info or not actor2_info:
        return []

    actor1_movies = get_movies_by_actor(actor1_info['id'])
    actor2_movies = get_movies_by_actor(actor2_info['id'])

    actor1_movie_ids = {movie['id'] for movie in actor1_movies}
    actor2_movie_ids = {movie['id'] for movie in actor2_movies}

    common_movie_ids = actor1_movie_ids.intersection(actor2_movie_ids)

    common_movies = []
    for common_id in common_movie_ids:
        actor1_character = next((m['character'] for m in actor1_movies if m['id'] == common_id), 'N/A')
        actor2_character = next((m['character'] for m in actor2_movies if m['id'] == common_id), 'N/A')

        movie_details = fetch_common_movie_details(common_id, actor1_character, actor2_character)
        if movie_details:
            movie_details['characters'] = {actor1_name: actor1_character, actor2_name: actor2_character}
            common_movies.append(movie_details)

    return common_movies