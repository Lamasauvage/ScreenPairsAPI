import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ScreenPairsAPI.settings")
django.setup()

import logging
from api.models import ActorPair
from services.tmdb import get_actor_info, get_movies_by_actor

logger = logging.getLogger(__name__)

ACTOR_PAIRS = [
    ("Robert De Niro", "Joe Pesci"),
    ("Tom Hanks", "Meg Ryan"),
    ("Ben Stiller", "Owen Wilson"),
    ("Johnny Depp", "Helena Bonham Carter"),
    ("Nick Frost", "Simon Pegg"),
    ("Emma Stone", "Ryan Gosling"),
]

DOCUMENTARY_GENRE_ID = 99

def fetch_common_movies(actor1, actor2, movies1, movies2):
    ids1 = {m['id']: m for m in movies1}
    ids2 = {m['id']: m for m in movies2}
    common_ids = set(ids1.keys()) & set(ids2.keys())

    common_movies = []
    for mid in common_ids:
        movie = ids1[mid]
        genre_ids = movie.get("genre_ids", [])
        if "title" not in movie:
            continue
        common_movies.append({
            "id": mid,
            "title": movie["title"],
            "release_date": movie.get("release_date", ""),
            "is_documentary": DOCUMENTARY_GENRE_ID in genre_ids,
        })
    return sorted(common_movies, key=lambda m: m["release_date"] or "9999")

def run():
    actor_infos = {}
    actor_movies = {}

    for name in {n for pair in ACTOR_PAIRS for n in pair}:
        info = get_actor_info(name)
        if not info:
            logger.warning(f"Acteur non trouvé : {name}")
            continue
        actor_infos[name] = info
        actor_movies[name] = get_movies_by_actor(info["id"])

    for actor1, actor2 in ACTOR_PAIRS:
        if actor1 not in actor_infos or actor2 not in actor_infos:
            logger.warning(f"Paire ignorée : {actor1} / {actor2}")
            continue

        movies = fetch_common_movies(actor1, actor2, actor_movies[actor1], actor_movies[actor2])

        ActorPair.objects.update_or_create(
            actor1_id=actor_infos[actor1]["id"],
            actor2_id=actor_infos[actor2]["id"],
            defaults={
                "actor1_name": actor1,
                "actor2_name": actor2,
                "common_movies_count": len(movies),
                "common_movies": [
                    {"title": m["title"], "release_date": m["release_date"]}
                    for m in movies
                ],
            },
        )

        print(f"{actor1} & {actor2} → {len(movies)} films communs :")
        for m in movies:
            print(f"- {m['title']} ({m['release_date'] or 'N/A'})")
        print()

if __name__ == "__main__":
    run()
