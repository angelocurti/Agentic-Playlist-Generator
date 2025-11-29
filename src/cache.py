"""
Redis Cache per task queue e caching veloce.

Funzionalità:
- Task queue in tempo reale
- Cache per ricerche Spotify
- Rate limiting
- Session management
"""

import redis
import json
from typing import Optional, Dict, Any, List
from datetime import timedelta
import os

# Configurazione Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Prefissi per le chiavi
PREFIX_TASK = "task:"
PREFIX_CACHE = "cache:"
PREFIX_SESSION = "session:"
PREFIX_RATE = "rate:"

# TTL defaults
TTL_TASK = 3600  # 1 ora
TTL_CACHE = 86400  # 24 ore
TTL_SESSION = 7200  # 2 ore
TTL_RATE = 60  # 1 minuto

# Client Redis singleton
_redis_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    """Ottiene il client Redis singleton."""
    global _redis_client
    
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connessione
            _redis_client.ping()
            print("[Redis] ✓ Connected")
        except redis.ConnectionError as e:
            print(f"[Redis] ⚠ Connection failed: {e}")
            print("[Redis] Running in fallback mode (no cache)")
            return None
        except Exception as e:
            print(f"[Redis] ⚠ Error: {e}")
            return None
    
    return _redis_client


def is_redis_available() -> bool:
    """Controlla se Redis è disponibile."""
    client = get_redis()
    if client:
        try:
            client.ping()
            return True
        except:
            return False
    return False


# --- TASK OPERATIONS ---

def set_task_status(task_id: str, data: Dict[str, Any], ttl: int = TTL_TASK) -> bool:
    """Salva lo stato di un task in Redis."""
    client = get_redis()
    if not client:
        return False
    
    try:
        key = f"{PREFIX_TASK}{task_id}"
        client.setex(key, ttl, json.dumps(data))
        return True
    except Exception as e:
        print(f"[Redis] Error setting task: {e}")
        return False


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Ottiene lo stato di un task da Redis."""
    client = get_redis()
    if not client:
        return None
    
    try:
        key = f"{PREFIX_TASK}{task_id}"
        data = client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        print(f"[Redis] Error getting task: {e}")
        return None


def update_task_progress(task_id: str, progress: str, status: str = "processing") -> bool:
    """Aggiorna solo il progress di un task."""
    client = get_redis()
    if not client:
        return False
    
    try:
        key = f"{PREFIX_TASK}{task_id}"
        data = client.get(key)
        if data:
            task = json.loads(data)
            task["progress"] = progress
            task["status"] = status
            client.setex(key, TTL_TASK, json.dumps(task))
            return True
        return False
    except Exception as e:
        print(f"[Redis] Error updating task: {e}")
        return False


def delete_task(task_id: str) -> bool:
    """Elimina un task da Redis."""
    client = get_redis()
    if not client:
        return False
    
    try:
        key = f"{PREFIX_TASK}{task_id}"
        client.delete(key)
        return True
    except Exception as e:
        print(f"[Redis] Error deleting task: {e}")
        return False


def get_active_tasks() -> List[str]:
    """Ottiene tutti i task attivi."""
    client = get_redis()
    if not client:
        return []
    
    try:
        keys = client.keys(f"{PREFIX_TASK}*")
        return [k.replace(PREFIX_TASK, "") for k in keys]
    except Exception as e:
        print(f"[Redis] Error getting active tasks: {e}")
        return []


# --- CACHE OPERATIONS ---

def cache_set(key: str, value: Any, ttl: int = TTL_CACHE) -> bool:
    """Salva un valore nella cache."""
    client = get_redis()
    if not client:
        return False
    
    try:
        cache_key = f"{PREFIX_CACHE}{key}"
        client.setex(cache_key, ttl, json.dumps(value))
        return True
    except Exception as e:
        print(f"[Redis] Cache set error: {e}")
        return False


def cache_get(key: str) -> Optional[Any]:
    """Ottiene un valore dalla cache."""
    client = get_redis()
    if not client:
        return None
    
    try:
        cache_key = f"{PREFIX_CACHE}{key}"
        data = client.get(cache_key)
        return json.loads(data) if data else None
    except Exception as e:
        print(f"[Redis] Cache get error: {e}")
        return None


def cache_delete(key: str) -> bool:
    """Elimina un valore dalla cache."""
    client = get_redis()
    if not client:
        return False
    
    try:
        cache_key = f"{PREFIX_CACHE}{key}"
        client.delete(cache_key)
        return True
    except Exception as e:
        print(f"[Redis] Cache delete error: {e}")
        return False


def cache_spotify_search(query: str, result: Dict[str, Any]) -> bool:
    """Cache specifico per ricerche Spotify (TTL lungo)."""
    return cache_set(f"spotify:{query}", result, ttl=86400 * 7)  # 7 giorni


def get_cached_spotify_search(query: str) -> Optional[Dict[str, Any]]:
    """Ottiene una ricerca Spotify dalla cache."""
    return cache_get(f"spotify:{query}")


# --- RATE LIMITING ---

def check_rate_limit(identifier: str, limit: int = 10, window: int = TTL_RATE) -> bool:
    """
    Controlla il rate limit per un identificatore.
    Ritorna True se la richiesta è permessa, False se limite superato.
    """
    client = get_redis()
    if not client:
        return True  # Se Redis non disponibile, permetti
    
    try:
        key = f"{PREFIX_RATE}{identifier}"
        current = client.get(key)
        
        if current is None:
            client.setex(key, window, 1)
            return True
        
        if int(current) >= limit:
            return False
        
        client.incr(key)
        return True
    except Exception as e:
        print(f"[Redis] Rate limit error: {e}")
        return True


def get_rate_limit_remaining(identifier: str, limit: int = 10) -> int:
    """Ottiene le richieste rimanenti per un identificatore."""
    client = get_redis()
    if not client:
        return limit
    
    try:
        key = f"{PREFIX_RATE}{identifier}"
        current = client.get(key)
        return limit - int(current) if current else limit
    except:
        return limit


# --- SESSION OPERATIONS ---

def save_session(session_id: str, data: Dict[str, Any], ttl: int = TTL_SESSION) -> bool:
    """Salva dati di sessione."""
    client = get_redis()
    if not client:
        return False
    
    try:
        key = f"{PREFIX_SESSION}{session_id}"
        client.setex(key, ttl, json.dumps(data))
        return True
    except Exception as e:
        print(f"[Redis] Session save error: {e}")
        return False


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Ottiene dati di sessione."""
    client = get_redis()
    if not client:
        return None
    
    try:
        key = f"{PREFIX_SESSION}{session_id}"
        data = client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        print(f"[Redis] Session get error: {e}")
        return None


def extend_session(session_id: str, ttl: int = TTL_SESSION) -> bool:
    """Estende la durata di una sessione."""
    client = get_redis()
    if not client:
        return False
    
    try:
        key = f"{PREFIX_SESSION}{session_id}"
        client.expire(key, ttl)
        return True
    except Exception as e:
        print(f"[Redis] Session extend error: {e}")
        return False


# --- PUBSUB (per notifiche real-time) ---

def publish_task_update(task_id: str, data: Dict[str, Any]) -> bool:
    """Pubblica un aggiornamento task via PubSub."""
    client = get_redis()
    if not client:
        return False
    
    try:
        channel = f"task_updates:{task_id}"
        client.publish(channel, json.dumps(data))
        return True
    except Exception as e:
        print(f"[Redis] Publish error: {e}")
        return False


# --- STATS ---

def get_cache_stats() -> Dict[str, Any]:
    """Ottiene statistiche della cache."""
    client = get_redis()
    if not client:
        return {"status": "unavailable"}
    
    try:
        info = client.info("memory")
        keys_count = client.dbsize()
        
        return {
            "status": "connected",
            "memory_used": info.get("used_memory_human", "unknown"),
            "keys_count": keys_count,
            "active_tasks": len(get_active_tasks())
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def flush_cache() -> bool:
    """Svuota tutta la cache (solo cache, non task)."""
    client = get_redis()
    if not client:
        return False
    
    try:
        keys = client.keys(f"{PREFIX_CACHE}*")
        if keys:
            client.delete(*keys)
        return True
    except Exception as e:
        print(f"[Redis] Flush error: {e}")
        return False

