import requests
import logging
from django.conf import settings
from django.core.cache import cache

from . import cache_manager
from .utils import make_tmdb_request, TMDBServiceError

logger = logging.getLogger(__name__)
HEADERS = {"Authorization": f"Bearer {settings.TMDB_BEARER_TOKEN}"}

def search_actors(query):
    if not query:
        return []
    url = f"https://api.themoviedb.org/3/search/person"
    params = {'query': query, 'include_adult': 'false', 'language': 'en-US'}

    data = make_tmdb_request(
        url=url,
        headers=HEADERS,
        params=params,
        action_description=f"searching actors for '{query}'"
    )

    top_results = data.get("results", [])[:5]
    results = [{
        'id': actor['id'],
        'name': actor['name'],
        'profile_path': actor.get('profile_path'),
        'popularity': actor.get('popularity', 0),
    } for actor in top_results]
    return sorted(results, key=lambda x: x['popularity'], reverse=True)


def get_actor_info(actor_name):
    search_url = f"https://api.themoviedb.org/3/search/person"
    search_params = {'query': actor_name, 'language': 'en-US'}

    search_data = make_tmdb_request(
        url=search_url,
        headers=HEADERS,
        params=search_params,
        action_description=f"searching for actor '{actor_name}'"
    )

    results = search_data.get('results')
    if not results:
        logger.info(f"Aucun résultat TMDB trouvé pour l'acteur: {actor_name}")
        return None

    actor_data = results[0]
    actor_id = actor_data['id']

    detail_url = f"https://api.themoviedb.org/3/person/{actor_id}/external_ids"
    imdb_id = None
    try:
        detail_data = make_tmdb_request(
            url=detail_url,
            headers=HEADERS,
            action_description=f"getting external IDs for actor ID {actor_id}"
        )
        imdb_id = detail_data.get('imdb_id')
    except TMDBServiceError as e:
        logger.warning(f"Impossible de récupérer les détails externes TMDB (IMDb ID) pour l'acteur ID {actor_id}. Erreur: {e}", exc_info=False)

    imdb_url = f"https://www.imdb.com/name/{imdb_id}/" if imdb_id else None

    return {
        'id': actor_id,
        'image_path': actor_data.get('profile_path'),
        'imdb_url': imdb_url
    }


def get_movies_by_actor(actor_id):
    url = f"https://api.themoviedb.org/3/person/{actor_id}/movie_credits"
    params = {'language': 'en"-US'}

    data = make_tmdb_request(
        url=url,
        headers=HEADERS,
        params=params,
        action_description=f"getting movie credits for actor ID {actor_id}"
    )

    return [{
        'id': movie['id'],
        'title': movie.get('title'),
        'release_date': movie.get('release_date'),
        'character': movie.get('character'),
        'genre_ids': movie.get('genre_ids', [])
    } for movie in data.get('cast', [])]


def fetch_common_movie_details(movie_id, actor1_character, actor2_character):
    cache_key = f"internal_movie_{movie_id}_details"
    cached_movie = cache.get(cache_key)
    if cached_movie:
        movie_data_to_return = cached_movie.copy()
        movie_data_to_return['characters'] = {'actor1_dynamic': actor1_character, 'actor2_dynamic': actor2_character}
        logger.debug(f"Cache Django hit pour détails film: {movie_id}")
        return movie_data_to_return

    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {'append_to_response': 'credits,external_ids', 'language': 'en-US'}
    data = None
    try:
        data = make_tmdb_request(
            url=url,
            headers=HEADERS,
            params=params,
            action_description=f"getting details for movie ID {movie_id}"
        )
    except TMDBServiceError as e:
        logger.warning(f"Impossible de récupérer les détails TMDB pour film ID {movie_id}. Erreur: {e}", exc_info=False)
        return None

    directors = [crew['name'] for crew in data.get('credits', {}).get('crew', []) if crew['job'] == 'Director']
    imdb_id = data.get('external_ids', {}).get('imdb_id')
    imdb_url = f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else None
    release_date = data.get('release_date', '')
    release_year = release_date.split('-')[0] if release_date else ''

    movie_details = {
        'id': movie_id, 'imdb_url': imdb_url, 'title': data.get('title'),
        'genres': data.get('genres', []), 'poster_path': data.get('poster_path'),
        'release_year': release_year, 'directors': directors,
        'characters': {'actor1_dynamic': actor1_character, 'actor2_dynamic': actor2_character}
    }

    cache_payload = movie_details.copy()
    del cache_payload['characters']
    cache.set(cache_key, cache_payload, timeout=60 * 60 * 24)

    return movie_details


def find_common_movies(actor1_name, actor2_name):
    actor1_info = get_actor_info(actor1_name)
    actor2_info = get_actor_info(actor2_name)

    if not actor1_info or not actor2_info:
        logger.info(f"Infos acteur(s) introuvables pour la paire: '{actor1_name}' / '{actor2_name}'")
        return [], actor1_info or {}, actor2_info or {}

    actor1_id = actor1_info['id']
    actor2_id = actor2_info['id']

    cached_data = cache_manager.get_from_cache(actor1_id, actor2_id)
    if cached_data:
        logger.info(f"Cache JSON hit pour la paire d'ID: {actor1_id}_{actor2_id}")
        return cached_data.get('results', []), actor1_info, actor2_info

    logger.info(f"Cache JSON miss pour la paire d'ID: {actor1_id}_{actor2_id}. Calcul en cours...")
    actor1_movies = get_movies_by_actor(actor1_id)
    actor2_movies = get_movies_by_actor(actor2_id)

    actor1_movie_map = {movie['id']: movie for movie in actor1_movies}
    actor2_movie_map = {movie['id']: movie for movie in actor2_movies}
    common_movie_ids = set(actor1_movie_map.keys()).intersection(set(actor2_movie_map.keys()))

    calculated_common_movies_details = []
    if common_movie_ids:
        for common_id in common_movie_ids:
            actor1_character = actor1_movie_map.get(common_id, {}).get('character', 'N/A')
            actor2_character = actor2_movie_map.get(common_id, {}).get('character', 'N/A')

            movie_details = fetch_common_movie_details(common_id, actor1_character, actor2_character)

            if movie_details:
                movie_details['characters'] = { actor1_name: actor1_character, actor2_name: actor2_character }
                calculated_common_movies_details.append(movie_details)
    else:
        logger.info(f"Aucun ID de film commun trouvé entre {actor1_name} et {actor2_name}.")

    payload_to_cache_and_return = {
        'results': calculated_common_movies_details,
        'actor1_image': actor1_info.get('image_path'), 'actor2_image': actor2_info.get('image_path'),
        'actor1_imdb': actor1_info.get('imdb_url'), 'actor2_imdb': actor2_info.get('imdb_url'),
    }

    cache_manager.add_to_cache(actor1_id, actor2_id, payload_to_cache_and_return)

    return payload_to_cache_and_return.get('results', []), actor1_info, actor2_info