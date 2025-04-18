# scripts/fetch_selected_pairs.py

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ScreenPairsAPI.settings")
django.setup()

import logging
from django.conf import settings
from services.tmdb import get_actor_info, get_movies_by_actor
from api.models import ActorPair

logger = logging.getLogger(__name__)

# Paires manuelles
ACTOR_PAIRS = [
    ("Robert De Niro", "Joe Pesci"),
    ("Tom Hanks", "Meg Ryan"),
    ("Ben Stiller", "Owen Wilson"),
    ("Johnny Depp", "Helena Bonham Carter"),
    ("Nick Frost", "Simon Pegg"),
    ("Emma Stone", "Ryan Gosling"),
]

DOCUMENTARY_GENRE_ID = 99

# Récupérer les IDs et filmographies
actor_infos = {}
actor_movies = {}

for name1, name2 in set(ACTOR_PAIRS):
    for name in (name1, name2):
        if name in actor_infos:
            continue
        info = get_actor_info(name)
        if info:
            actor_infos[name] = info
            actor_movies[name] = get_movies_by_actor(info['id'])
        else:
            logger.warning(f"Acteur non trouvé : {name}")

# Analyse des films communs
for actor1, actor2 in ACTOR_PAIRS:
    if actor1 not in actor_infos or actor2 not in actor_infos:
        logger.warning(f"Paire ignorée : {actor1} / {actor2}")
        continue

    movies1 = {m['id']: m for m in actor_movies[actor1]}
    movies2 = {m['id']: m for m in actor_movies[actor2]}
    common_ids = set(movies1.keys()) & set(movies2.keys())

    common_movies = []
    for mid in common_ids:
        movie = movies1[mid]
    genre_ids = movie.get("genre_ids", [])

    if DOCUMENTARY_GENRE_ID not in genre_ids and "title" in movie:
        common_movies.append({
            "id": mid,
            "title": movie["title"],
            "release_date": movie.get("release_date", ""),
            "is_documentary": False
        })
    elif "title" in movie:
        common_movies.append({
            "id": mid,
            "title": movie["title"],
            "release_date": movie.get("release_date", ""),
            "is_documentary": True
        })


# Sauvegarde dans la base
    ActorPair.objects.update_or_create(
        actor1_id=actor_infos[actor1]["id"],
        actor2_id=actor_infos[actor2]["id"],
        defaults={
            "actor1_name": actor1,
            "actor2_name": actor2,
            "common_movies_count": len(common_movies),
            "common_movies": [
                {
                    "title": m["title"],
                    "release_date": m["release_date"]
                }
                for m in sorted(common_movies, key=lambda m: m["release_date"])
            ]
        },
    )

    # Affichage console
    print(f"{actor1} & {actor2} → {len(common_movies)} films communs :")
    for m in sorted(common_movies, key=lambda m: m["release_date"]):
        print(f"- {m['title']} ({m['release_date']})")
    print()
