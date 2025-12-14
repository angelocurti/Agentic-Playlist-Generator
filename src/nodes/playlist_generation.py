import spotipy
from spotipy.oauth2 import SpotifyOAuth, CacheHandler
from src.state import State
from src.config import SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI
from src.models import llm_orch
from langchain_core.messages import SystemMessage, HumanMessage
import json
import random
import time
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Tuple
import threading

# --- CACHE HANDLER IN MEMORIA PER TOKEN UTENTE ---
class MemoryCacheHandler(CacheHandler):
    """Cache handler in memoria per token utente."""
    def __init__(self, token_info: Dict[str, Any]):
        self._token_info = token_info
    
    def get_cached_token(self):
        return self._token_info
    
    def save_token_to_cache(self, token_info):
        self._token_info = token_info


# --- SPOTIFY CLIENT CACHING (SOLO PER SERVER) ---
_server_spotify_client = None
_server_spotify_user_id = None
_server_client_lock = threading.Lock()

def get_server_spotify_client() -> Tuple[spotipy.Spotify, str]:
    """
    Restituisce un client Spotify cached per uso server.
    Usa SOLO auth_manager - refresh automatico garantito.
    """
    global _server_spotify_client, _server_spotify_user_id
    
    with _server_client_lock:
        if _server_spotify_client is None:
            auth_manager = SpotifyOAuth(
                client_id=SPOTIPY_CLIENT_ID,
                client_secret=SPOTIPY_CLIENT_SECRET,
                redirect_uri=SPOTIPY_REDIRECT_URI,
                scope="playlist-modify-public playlist-modify-private user-read-email",
                cache_path=".spotify_server_cache"
            )
            _server_spotify_client = spotipy.Spotify(auth_manager=auth_manager)
            _server_spotify_user_id = _server_spotify_client.current_user()["id"]
            print(f"[Spotify] Server client initialized for user: {_server_spotify_user_id}")
    
    return _server_spotify_client, _server_spotify_user_id


def get_user_spotify_client(access_token: str, refresh_token: Optional[str] = None, expires_at: Optional[int] = None) -> Tuple[Optional[spotipy.Spotify], Optional[str]]:
    """
    Crea un client Spotify per utente usando SOLO auth_manager.
    Nessun token manuale - tutto gestito da SpotifyOAuth.
    """
    if not refresh_token:
        print(f"[Spotify] ✗ No refresh_token provided for user")
        return None, None
    
    try:
        # Costruisci token_info completo
        token_info = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at or int(time.time()) + 3600,  # Default 1h se non specificato
            "token_type": "Bearer"
        }
        
        # Crea cache handler con token_info
        cache_handler = MemoryCacheHandler(token_info)
        
        # Crea auth_manager con cache handler custom
        auth_manager = SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope="playlist-modify-public playlist-modify-private user-read-email",
            cache_handler=cache_handler  # Usa il nostro cache handler
        )
        
        # Crea client - auth_manager gestisce refresh automatico
        sp = spotipy.Spotify(auth_manager=auth_manager)
        user_id = sp.current_user()["id"]
        print(f"[Spotify] ✓ User client initialized for user: {user_id}")
        return sp, user_id
        
    except Exception as e:
        print(f"[Spotify] ✗ User auth failed: {e}")
        return None, None


# --- LRU CACHE PER RICERCHE SPOTIFY (SENZA CLIENT CONDIVISO) ---
# Cache di 1000 query recenti - evita ricerche duplicate
@lru_cache(maxsize=1000)
def _cached_spotify_search(query: str, client_type: str = "server") -> Optional[str]:
    """
    Cerca una traccia su Spotify con cache LRU.
    Crea un nuovo client per ogni ricerca (thread-safe).
    Ritorna JSON string dei risultati o None.
    """
    # Crea sempre un nuovo client per evitare problemi di thread
    sp, _ = get_server_spotify_client()
    try:
        results = sp.search(q=query, type="track", limit=1)
        tracks = results["tracks"]["items"]
        if tracks:
            track = tracks[0]
            return json.dumps({
                "uri": track["uri"],
                "duration_ms": track["duration_ms"],
                "name": track["name"],
                "artist": track["artists"][0]["name"],
                "album": track["album"]["name"],
                "album_image": track["album"]["images"][0]["url"] if track["album"]["images"] else ""
            })
    except Exception as e:
        print(f"[Spotify Cache] Error: {e}")
    return None


def search_track_cached(song: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Cerca una traccia usando la cache LRU"""
    query = f"track:{song['title']} artist:{song['artist']}"
    cached_result = _cached_spotify_search(query)
    
    if cached_result:
        data = json.loads(cached_result)
        return {
            "uri": data["uri"],
            "duration_ms": data["duration_ms"],
            "artist": song['artist'],
            "title": song['title'],
            "album": data.get("album", ""),
            "album_image": data.get("album_image", ""),
            "track_data": data
        }
    return None


def playlist_generation(state: State) -> dict:
    """
    Node that generates the playlist on Spotify.
    OTTIMIZZATO: 
    - Cache LRU per ricerche
    - Batch LLM (parsing + titolo combinati)
    - Ricerche parallele
    """
    messages = state.get("messages", [])
    search_results = messages[-1] if messages else ""
    
    playlist_context = state.get("playlist_context", "")
    user_request = state.get("messages", [{}])[0]
    user_query = user_request.content if hasattr(user_request, 'content') else str(user_request)
    
    # --- BATCH LLM: Parsing + Titolo in una sola chiamata (OTTIMIZZAZIONE 4) ---
    combined_prompt = f"""Hai due compiti:

1. ESTRAI CANZONI: Dal testo seguente, estrai tutte le canzoni menzionate.
2. GENERA TITOLO: Crea un titolo accattivante per la playlist (max 50 caratteri).

TESTO DA ANALIZZARE:
{str(search_results)}

CONTESTO:
- Richiesta utente: {user_query}
- Contesto musicale: {playlist_context[:200]}

RISPONDI IN QUESTO FORMATO JSON ESATTO:
{{
    "songs": [
        {{"artist": "Nome Artista", "title": "Titolo Canzone"}},
        ...
    ],
    "playlist_title": "Titolo Playlist Creativo"
}}

IMPORTANTE: Rispondi SOLO con il JSON, senza altro testo."""

    try:
        start_llm = time.time()
        extraction = llm_orch.invoke([
            SystemMessage(content="Sei un esperto di musica e data extraction. Rispondi sempre in JSON valido."),
            HumanMessage(content=combined_prompt)
        ])
        content = extraction.content.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(content)
        
        songs_to_add = parsed.get("songs", [])
        playlist_name = parsed.get("playlist_title", "AI Generated Playlist")[:50]
        
        llm_time = time.time() - start_llm
        print(f"[Playlist] ✓ Batch LLM completato in {llm_time:.1f}s: {len(songs_to_add)} songs, titolo: '{playlist_name}'")
        
    except Exception as e:
        print(f"[Playlist] Batch LLM failed: {e}, trying fallback...")
        
        # Fallback: parsing tradizionale
        parsing_prompt = """
        You are a music data extractor. 
        Extract the list of songs from the provided text.
        Return ONLY a JSON array of objects with "artist" and "title" keys.
        Example: [{"artist": "Queen", "title": "Bohemian Rhapsody"}, ...]
        """
        
        try:
            extraction = llm_orch.invoke([
                SystemMessage(content=parsing_prompt),
                HumanMessage(content=str(search_results))
            ])
            content = extraction.content.replace("```json", "").replace("```", "").strip()
            songs_to_add = json.loads(content)
            playlist_name = "AI Generated Playlist"
            print(f"[Playlist] Fallback parsed {len(songs_to_add)} songs")
        except Exception as e2:
            print(f"Error parsing songs: {e2}")
            return {"error": "Failed to parse songs from search results"}

    # 2. Get Spotify Client (User or Server) - SOLO auth_manager
    spotify_token = state.get("spotify_token")
    refresh_token = state.get("refresh_token")
    expires_at = state.get("expires_at")
    
    try:
        if spotify_token and refresh_token:
            print(f"[Playlist] Using USER Spotify token (auth_manager)")
            sp, user_id = get_user_spotify_client(spotify_token, refresh_token, expires_at)
            if sp is None:
                # Fallback to server client if user auth fails
                print(f"[Playlist] User auth failed, falling back to SERVER client")
                sp, user_id = get_server_spotify_client()
        else:
            print(f"[Playlist] Using SERVER Spotify client (auth_manager)")
            sp, user_id = get_server_spotify_client()
            
    except Exception as e:
        return {"error": f"Spotify authentication failed: {e}"}
    
    # 3. Create Playlist on Spotify
    try:
        playlist = sp.user_playlist_create(user_id, playlist_name, public=True)
        playlist_id = playlist["id"]
        playlist_url = playlist["external_urls"]["spotify"]
        print(f"[Playlist] ✓ Playlist creata: {playlist_name} (User: {user_id})")
    except Exception as e:
        return {"error": f"Failed to create playlist: {e}"}

    # 4. Search Tracks in PARALLEL con CACHE LRU
    print(f"[Playlist] Cercando {len(songs_to_add)} tracce (con cache)...")
    start_search = time.time()
    
    track_uris = []
    generated_playlist_info = []
    track_durations_ms = []
    cache_hits = 0
    
    # Usa ThreadPoolExecutor con cache
    with ThreadPoolExecutor(max_workers=15) as executor:
        future_to_song = {
            executor.submit(search_track_cached, song): song 
            for song in songs_to_add
        }
        
        for future in as_completed(future_to_song):
            result = future.result()
            if result:
                track_uris.append(result["uri"])
                track_durations_ms.append(result["duration_ms"])
                generated_playlist_info.append({
                    "artist": result["artist"],
                    "title": result["title"],
                    "uri": result["uri"],
                    "duration_ms": result["duration_ms"],
                    "album": result.get("album", ""),
                    "album_image": result.get("album_image", "")
                })
    
    search_time = time.time() - start_search
    cache_info = _cached_spotify_search.cache_info()
    print(f"[Playlist] ✓ Ricerche in {search_time:.1f}s: {len(track_uris)}/{len(songs_to_add)} trovate (cache: {cache_info.hits} hits, {cache_info.misses} misses)")

    if not track_uris:
        return {"error": "No tracks found on Spotify"}

    # 5. Add tracks to playlist in BATCHES
    batch_size = 100
    print(f"[Playlist] Aggiungo {len(track_uris)} tracce...")
    
    try:
        for i in range(0, len(track_uris), batch_size):
            batch = track_uris[i:i + batch_size]
            sp.playlist_add_items(playlist_id, batch)
    except Exception as e:
        return {"error": f"Failed to add tracks: {e}"}
    
    # 6. Check duration and fill with recommendations if needed
    total_duration_ms = sum(track_durations_ms)
    total_duration_min = total_duration_ms / 60000
    
    target_duration_ms = 60 * 60 * 1000  # 60 minuti
    
    if total_duration_ms < target_duration_ms:
        missing_duration_ms = target_duration_ms - total_duration_ms
        
        try:
            seed_track_uris = track_uris[:min(5, len(track_uris))]
            recommendations = sp.recommendations(seed_tracks=seed_track_uris, limit=30)
            
            recommended_tracks = recommendations.get('tracks', [])
            random_tracks_to_add = []
            added_duration = 0
            
            shuffled_tracks = random.sample(recommended_tracks, min(len(recommended_tracks), 30))
            
            for track in shuffled_tracks:
                if added_duration >= missing_duration_ms:
                    break
                    
                track_uri = track['uri']
                if track_uri not in track_uris:
                    random_tracks_to_add.append({
                        "uri": track_uri,
                        "artist": track['artists'][0]['name'],
                        "title": track['name'],
                        "duration_ms": track['duration_ms'],
                        "album": track["album"]["name"],
                        "album_image": track["album"]["images"][0]["url"] if track["album"]["images"] else ""
                    })
                    added_duration += track['duration_ms']
            
            if random_tracks_to_add:
                rec_uris = [t["uri"] for t in random_tracks_to_add]
                sp.playlist_add_items(playlist_id, rec_uris)
                
                for rec_track in random_tracks_to_add:
                    track_uris.append(rec_track["uri"])
                    generated_playlist_info.append({
                        "artist": rec_track["artist"],
                        "title": rec_track["title"],
                        "uri": rec_track["uri"],
                        "duration_ms": rec_track["duration_ms"],
                        "album": rec_track.get("album", ""),
                        "album_image": rec_track.get("album_image", "")
                    })
                
                total_duration_ms += added_duration
                total_duration_min = total_duration_ms / 60000
                print(f"[Playlist] ✓ +{len(random_tracks_to_add)} raccomandazioni -> {total_duration_min:.1f} min")
        
        except Exception as e:
            print(f"[Playlist] Raccomandazioni skipped: {e}")

    print(f"[Playlist] ✅ Completato: {len(track_uris)} tracce, {total_duration_min:.1f} minuti")
    
    return {
        "generated_playlist": generated_playlist_info, 
        "messages": [f"Playlist created successfully! Link: {playlist_url}\nDurata: {total_duration_min:.1f} minuti ({len(track_uris)} tracce)"]
    }
