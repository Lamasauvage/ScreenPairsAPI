import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ScreenPairsAPI.settings")
django.setup()

import requests
import logging
from django.conf import settings
from django.db import models
from services.tmdb import get_movies_by_actor
from itertools import combinations
from collections import defaultdict
from api.models import ActorPair

HEADERS = {"Authorization": f"Bearer {settings.TMDB_BEARER_TOKEN}"}
logger = logging.getLogger(__name__)


def fetch_popular_actors(page=1):
    url = f"https://api.themoviedb.org/3/person/popular?page={page}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.warning(f"TMDB fetch_popular_actors error: {e}")
        return []

    return [{
        'id': actor['id'],
        'name': actor['name'],
        'popularity': actor.get('popularity', 0),
        'profile_path': actor.get('profile_path'),
    } for actor in data.get("results", [])]


def fetch_all_popular_actors():
    all_actors = []
    max_pages = 10
    page = 1
    while page <= max_pages:
        actors = fetch_popular_actors(page)
        if not actors:
            break
        all_actors.extend(actors)
        page += 1
    return all_actors


all_actors = fetch_all_popular_actors()
cooccurrence = defaultdict(int)

for actor in all_actors:
    actor_id = actor['id']
    movies = get_movies_by_actor(actor_id)
    movies_ids = [movie['id'] for movie in movies]
    actor['movie_ids'] = set(movies_ids)

for actor1, actor2 in combinations(all_actors, 2):
    if actor1['id'] == actor2['id']:
        continue
    common_movies = actor1['movie_ids'].intersection(actor2['movie_ids'])
    if common_movies:
        pair_key = tuple(sorted((actor1['id'], actor2['id'])))
        cooccurrence[pair_key] = len(common_movies)

ActorPair.objects.filter(actor1_id=models.F('actor2_id')).delete()

for (id1, id2), count in cooccurrence.items():
    actor1 = next(a for a in all_actors if a['id'] == id1)
    actor2 = next(a for a in all_actors if a['id'] == id2)

    ActorPair.objects.update_or_create(
        actor1_id=id1,
        actor2_id=id2,
        defaults={
            'actor1_name': actor1['name'],
            'actor2_name': actor2['name'],
            'common_movies_count': count
        }
    )
