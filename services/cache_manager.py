import json
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


CACHE_FILE_PATH = Path(__file__).resolve().parent.parent / 'api_cache.json'
CACHE_DURATION = timedelta(days=1)

def _load_cache():
    if not CACHE_FILE_PATH.exists():
        return {}
    try:
        with open(CACHE_FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Erreur lors du chargement du cache JSON ({CACHE_FILE_PATH}): {e}")
        return {}

def _save_cache(cache_data):
    try:
        with open(CACHE_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logger.error(f"Erreur lors de la sauvegarde du cache JSON ({CACHE_FILE_PATH}): {e}")

def _get_cache_key(actor1_id, actor2_id):
    try:
        id1 = int(actor1_id)
        id2 = int(actor2_id)
        return f"{min(id1, id2)}_{max(id1, id2)}"
    except (ValueError, TypeError):
        logger.warning(f"Impossible de générer la clé de cache pour les IDs : {actor1_id}, {actor2_id}")
        return None

def get_from_cache(actor1_id, actor2_id):
    cache_key = _get_cache_key(actor1_id, actor2_id)
    if not cache_key:
        return None

    cache_data = _load_cache()
    cached_entry = cache_data.get(cache_key)

    if cached_entry:
        timestamp_str = cached_entry.get("timestamp")
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                if datetime.now(timestamp.tzinfo) - timestamp < CACHE_DURATION:
                    logger.info(f"Cache hit pour la clé: {cache_key}")
                    return {k: v for k, v in cached_entry.items() if k != 'timestamp'}
                else:
                    logger.info(f"Cache expiré pour la clé: {cache_key}")
            except ValueError:
                logger.warning(f"Format de timestamp invalide dans le cache pour la clé: {cache_key}")
        else:
            logger.info(f"Entrée de cache sans timestamp pour la clé: {cache_key}")


    logger.info(f"Cache miss pour la clé: {cache_key}")
    return None

def add_to_cache(actor1_id, actor2_id, data_to_cache):
    cache_key = _get_cache_key(actor1_id, actor2_id)
    if not cache_key:
        return

    cache_data = _load_cache()

    entry_to_store = data_to_cache.copy()
    entry_to_store["timestamp"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    cache_data[cache_key] = entry_to_store
    _save_cache(cache_data)
    logger.info(f"Données ajoutées au cache pour la clé: {cache_key}")