"""
API REST per la generazione di playlist musicali.

Endpoints:
- POST /generate - Genera una nuova playlist
- GET /status/{task_id} - Verifica lo stato di una generazione
- GET /stream/{task_id} - SSE streaming dello stato
- GET /health - Controlla lo stato dell'API
- POST /news - Ottieni news su artisti/generi/mood
- POST /ask - Fai domande sulla musica
- GET /playlists - Storico playlist (SQLite)
- GET /stats - Statistiche (SQLite + Redis)

STACK:
- SQLite: persistenza playlists, tracks, stats
- Redis: task queue real-time, cache veloce
- Fallback: in-memory se Redis non disponibile
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import uvicorn
import uuid
import re
import asyncio
import httpx
from datetime import datetime
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage
from langchain_perplexity import ChatPerplexity

from src.agent import get_cached_agent
from src.config import PPLX_API_KEY

# Import database e cache
from src.database import DatabaseManager
from src import cache

# Initialize database manager
db = DatabaseManager()

# --- REGEX PRECOMPILATE ---
SPOTIFY_URL_REGEX = re.compile(r'https://open\.spotify\.com/playlist/[a-zA-Z0-9]+')
DURATION_REGEX = re.compile(r'Durata:\s*([\d.]+)\s*minuti')
TRACK_COUNT_REGEX = re.compile(r'\((\d+)\s*tracce\)')
REFERENCE_REGEX = re.compile(r'\[\d+\]|\[\^\d+\]')
MULTIPLE_SPACES_REGEX = re.compile(r'\s+')

# --- SINGLETON CLIENTS ---
_perplexity_client = None
_http_client: Optional[httpx.AsyncClient] = None

# Fallback in-memory (usato solo se Redis non disponibile)
task_storage_fallback: Dict[str, Dict[str, Any]] = {}

def get_perplexity_client():
    global _perplexity_client
    if _perplexity_client is None:
        _perplexity_client = ChatPerplexity(temperature=0.3, model="sonar")
    return _perplexity_client

def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20)
        )
    return _http_client


# --- TASK STORAGE HELPERS (Redis + fallback) ---

def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Ottiene un task da Redis o fallback."""
    # Prima prova Redis
    task = cache.get_task_status(task_id)
    if task:
        return task
    # Fallback in-memory
    return task_storage_fallback.get(task_id)

def set_task(task_id: str, data: Dict[str, Any]) -> None:
    """Salva un task in Redis e fallback."""
    cache.set_task_status(task_id, data)
    task_storage_fallback[task_id] = data

def update_task(task_id: str, updates: Dict[str, Any]) -> None:
    """Aggiorna un task esistente."""
    task = get_task(task_id)
    if task:
        task.update(updates)
        set_task(task_id, task)

def delete_task_storage(task_id: str) -> None:
    """Elimina un task."""
    cache.delete_task(task_id)
    if task_id in task_storage_fallback:
        del task_storage_fallback[task_id]


# --- LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm-up all'avvio: inizializza DB, Redis, e tutti i client"""
    print("🔥 Warming up...")
    
    # Inizializza SQLite
    await db.init_db()
    print("  ✓ SQLite database ready")
    
    # Inizializza Redis
    redis_available = cache.is_redis_available()
    if redis_available:
        print("  ✓ Redis connected")
    else:
        print("  ⚠ Redis not available (using fallback)")
    
    # Pre-inizializza client
    get_perplexity_client()
    print("  ✓ Perplexity client ready")
    
    get_http_client()
    print("  ✓ HTTP client pool ready")
    
    get_cached_agent()
    print("  ✓ Agent graph compiled")
    
    try:
        from src.nodes.playlist_generation import get_spotify_client
        get_spotify_client()
        print("  ✓ Spotify client ready")
    except Exception as e:
        print(f"  ⚠ Spotify client skipped: {e}")
    
    print("🚀 API ready!\n")
    
    yield
    
    # Cleanup
    global _http_client
    if _http_client:
        await _http_client.aclose()
        print("👋 HTTP client closed")


# Inizializza FastAPI
app = FastAPI(
    title="Playlist Generator API",
    description="API per generare playlist musicali usando AI",
    version="3.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi.responses import RedirectResponse
from spotipy.oauth2 import SpotifyOAuth
from src.config import SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI

# --- SPOTIFY AUTH ---
sp_oauth = SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope="playlist-modify-public playlist-modify-private user-read-email"
)

@app.get("/auth/login", tags=["Auth"])
async def spotify_login():
    """Redirects user to Spotify login."""
    auth_url = sp_oauth.get_authorize_url()
    return {"url": auth_url}

@app.get("/auth/callback", tags=["Auth"])
async def spotify_callback(code: str):
    """Handles Spotify callback and redirects to frontend with token."""
    try:
        token_info = sp_oauth.get_access_token(code)
        access_token = token_info["access_token"]
        refresh_token = token_info.get("refresh_token", "")
        expires_at = token_info.get("expires_at", 0)
        # Pass both tokens to frontend (in production use secure cookies/session)
        return RedirectResponse(
            url=f"http://localhost:3000?spotify_token={access_token}&refresh_token={refresh_token}&expires_at={expires_at}"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Auth failed: {e}")


@app.post("/auth/refresh", tags=["Auth"])
async def refresh_spotify_token(refresh_token: str):
    """Refreshes an expired Spotify access token."""
    try:
        token_info = sp_oauth.refresh_access_token(refresh_token)
        return {
            "access_token": token_info["access_token"],
            "refresh_token": token_info.get("refresh_token", refresh_token),
            "expires_at": token_info.get("expires_at", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token refresh failed: {e}")

# --- MODELS ---

class PlaylistRequest(BaseModel):
    description: str
    duration_minutes: Optional[int] = 60
    spotify_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[int] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Playlist con il vero suono della Dogo Gang",
                "duration_minutes": 60
            }
        }
    )


class PlaylistResponse(BaseModel):
    task_id: str
    status: str
    message: str


class TaskStatus(BaseModel):
    task_id: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[str] = None
    
    model_config = ConfigDict(extra="allow")


class NewsRequest(BaseModel):
    query: str


class NewsResponse(BaseModel):
    query: str
    news: str


class Message(BaseModel):
    type: str
    content: str


class QuestionRequest(BaseModel):
    question: str
    conversation_history: Optional[List[Message]] = []


class AnswerResponse(BaseModel):
    question: str
    answer: str


# --- UTILITY FUNCTIONS ---

def clean_perplexity_output(text: str) -> str:
    if not text:
        return text
    text = REFERENCE_REGEX.sub('', text)
    text = MULTIPLE_SPACES_REGEX.sub(' ', text)
    return text.strip()


# --- ASYNC BACKGROUND TASK ---

async def generate_playlist_async(task_id: str, description: str, duration_minutes: int, spotify_token: Optional[str] = None, refresh_token: Optional[str] = None, expires_at: Optional[int] = None):
    """Task ASYNC per generare la playlist con persistenza."""
    import time
    start_time = time.time()
    
    try:
        update_task(task_id, {"status": "processing", "progress": "Processing your request..."})
        
        # Salva task in SQLite per monitoring
        await db.save_task(task_id, "processing", description, "Processing...")
        
        app_agent = get_cached_agent()
        cfg = {"configurable": {"thread_id": task_id}}
        inputs = {
            "messages": [HumanMessage(content=description)],
            "spotify_token": spotify_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at
        }
        
        update_task(task_id, {"progress": "Searching over millions of sources..."})
        print(f"[API Task {task_id[:8]}] Starting generation...")
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: app_agent.invoke(inputs, config=cfg))
        
        elapsed = time.time() - start_time
        print(f"[API Task {task_id[:8]}] Generation done in {elapsed:.1f}s")
        
        # Estrai risultati
        final_messages = result.get("messages", [])
        generated_playlist = result.get("generated_playlist", [])
        
        playlist_url = None
        duration_info = None
        track_count = len(generated_playlist) if generated_playlist else 0
        
        dur_match = None
        for msg in reversed(final_messages):
            content = msg.content if hasattr(msg, 'content') else str(msg)
            
            if "spotify.com" in content:
                url_match = SPOTIFY_URL_REGEX.search(content)
                if url_match:
                    playlist_url = url_match.group(0)
                
                dur_match = DURATION_REGEX.search(content)
                if dur_match:
                    duration_info = f"Durata: {dur_match.group(1)} minuti"
                
                count_match = TRACK_COUNT_REGEX.search(content)
                if count_match:
                    track_count = int(count_match.group(1))
                
                if playlist_url:
                    break
        
        # Formatta tracce
        tracks = []
        if generated_playlist:
            for t in generated_playlist:
                tracks.append({
                    "title": t.get("title", t.get("name", "Unknown")),
                    "artist": t.get("artist", "Unknown"),
                    "album": t.get("album", ""),
                    "album_image": t.get("album_image", ""),
                    "duration": t.get("duration_ms", 0) // 1000 if t.get("duration_ms") else 0,
                    "uri": t.get("uri", "")
                })
        
        total_time = time.time() - start_time
        print(f"[API Task {task_id[:8]}] ✅ Complete in {total_time:.1f}s - {track_count} tracks")
        
        result_data = {
            "playlist_url": playlist_url,
            "duration_info": duration_info,
            "track_count": track_count,
            "tracks": tracks,
            "description": description,
            "generation_time": total_time,
            "success": playlist_url is not None
        }
        
        # Aggiorna task storage
        update_task(task_id, {
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "progress": f"Done in {total_time:.0f}s!",
            "result": result_data
        })
        
        # --- PERSISTENZA SQLite ---
        # Salva playlist
        duration_min = float(dur_match.group(1)) if dur_match else total_time / 60
        await db.save_playlist(
            playlist_id=task_id,
            description=description,
            spotify_url=playlist_url,
            title=description[:100],
            track_count=track_count,
            duration_minutes=duration_min,
            generation_time=total_time
        )
        
        # Salva tracce
        if tracks:
            await db.save_tracks(task_id, tracks)
        
        # Aggiorna task in SQLite
        await db.save_task(
            task_id, "completed", description,
            f"Done in {total_time:.0f}s!",
            result_data,
            completed_at=datetime.now().isoformat()
        )
        
        print(f"[API Task {task_id[:8]}] ✅ Saved to SQLite")
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        elapsed = time.time() - start_time
        
        print(f"[API Task {task_id[:8]}] ❌ Failed after {elapsed:.1f}s: {e}")
        
        update_task(task_id, {
            "status": "failed",
            "completed_at": datetime.now().isoformat(),
            "error": str(e),
            "error_details": error_details,
            "progress": "Failed"
        })
        
        # Salva errore in SQLite
        await db.save_task(
            task_id, "failed", description,
            "Failed", None, str(e),
            datetime.now().isoformat()
        )


# --- ENDPOINTS ---

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Playlist Generator API",
        "version": "3.0.0",
        "docs": "/docs",
        "features": ["sqlite", "redis", "async", "sse-streaming"]
    }


@app.get("/health", tags=["Health"])
async def health_check():
    redis_stats = cache.get_cache_stats()
    db_stats = await db.get_stats()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "redis": redis_stats,
        "sqlite": db_stats
    }

@app.post("/generate", response_model=PlaylistResponse)
async def generate_playlist(request: PlaylistRequest, background_tasks: BackgroundTasks):
    """
    Starts the playlist generation process in the background.
    """
    task_id = str(uuid.uuid4())
    
    # Initialize task in DB
    await db.save_task(
        task_id=task_id,
        status="pending",
        description=request.description,
        progress="Queued"
    )
    
    # Start background processing
    background_tasks.add_task(
        generate_playlist_async, 
        task_id, 
        request.description, 
        request.duration_minutes,
        request.spotify_token,
        request.refresh_token,
        request.expires_at
    )
    
    return PlaylistResponse(
        task_id=task_id,
        status="pending",
        message="Playlist generation started"
    )

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    """
    Checks the status of a generation task.
    """
    task = await db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/playlists")
async def get_playlists(user_id: str = "default", limit: int = 20):
    """
    Returns the user's generated playlists.
    """
    return await db.get_playlists(user_id, limit)

@app.get("/playlists/{playlist_id}")
async def get_playlist_details(playlist_id: str):
    """
    Returns full details of a playlist including tracks.
    """
    playlist = await db.get_playlist_with_tracks(playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return playlist

@app.delete("/playlists/{playlist_id}")
async def delete_playlist(playlist_id: str):
    """
    Deletes a playlist.
    """
    success = await db.delete_playlist(playlist_id)
    if not success:
        raise HTTPException(status_code=404, detail="Playlist not found or could not be deleted")
    return {"status": "deleted"}

@app.get("/stats")
async def get_stats():
    """
    Returns usage statistics.
    """
    return await db.get_stats()


# --- NEWS ENDPOINT ---

@app.post("/news", response_model=NewsResponse, tags=["News"])
async def get_news(request: NewsRequest):
    """Ottiene le ultime news su un artista, genere o mood."""
    # Check cache
    cached = cache.cache_get(f"news:{request.query}")
    if cached:
        return NewsResponse(query=request.query, news=cached)
    
    try:
        llm = get_perplexity_client()
        
        prompt = f"""Provide a brief 2-sentence summary of the latest news about "{request.query}" in the music world. 
        Focus on recent releases, collaborations, tours, or notable events.
        Be concise and informative. Respond in the same language as the query."""
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: llm.invoke(prompt))
        
        news_text = response.content if hasattr(response, 'content') else str(response)
        cleaned_news = clean_perplexity_output(news_text)
        
        # Cache per 1 ora
        cache.cache_set(f"news:{request.query}", cleaned_news, ttl=3600)
        
        return NewsResponse(query=request.query, news=cleaned_news)
        
    except Exception as e:
        print(f"[News API] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch news: {str(e)}")


# --- Q&A ENDPOINT ---

def summarize_conversation(conversation_history: List[Message], llm) -> str:
    if len(conversation_history) <= 20:
        return None
    
    keep_first = 5
    keep_last = 5
    
    first_messages = conversation_history[:keep_first]
    middle_messages = conversation_history[keep_first:-keep_last]
    last_messages = conversation_history[-keep_last:]
    
    middle_text = "\n".join([
        f"{'User' if msg.type == 'user' else 'AI'}: {msg.content}"
        for msg in middle_messages
    ])
    
    summary_prompt = f"""Riassumi questa conversazione sulla musica mantenendo i punti chiave:

{middle_text}

Riassunto conciso (max 200 parole):"""
    
    try:
        summary_response = llm.invoke(summary_prompt)
        summary = summary_response.content if hasattr(summary_response, 'content') else str(summary_response)
        cleaned_summary = clean_perplexity_output(summary)
        
        summarized_history = first_messages + [
            Message(type="ai", content=f"[Riassunto: {cleaned_summary}]")
        ] + last_messages
        
        return "\n".join([
            f"{'User' if msg.type == 'user' else 'AI'}: {msg.content}"
            for msg in summarized_history
        ])
    except Exception as e:
        print(f"[Q&A] Error summarizing: {e}")
        return "\n".join([
            f"{'User' if msg.type == 'user' else 'AI'}: {msg.content}"
            for msg in conversation_history[-15:]
        ])


@app.post("/ask", response_model=AnswerResponse, tags=["Q&A"])
async def ask_question(request: QuestionRequest):
    """Risponde a domande sulla musica con memoria."""
    try:
        llm = get_perplexity_client()
        
        conversation_context = ""
        
        if request.conversation_history and len(request.conversation_history) > 0:
            if len(request.conversation_history) > 20:
                print(f"[Q&A] Applying summarization ({len(request.conversation_history)} messages)...")
                conversation_context = summarize_conversation(request.conversation_history, llm)
            else:
                conversation_context = "\n".join([
                    f"{'User' if msg.type == 'user' else 'AI'}: {msg.content}"
                    for msg in request.conversation_history
                ])
        
        if conversation_context:
            prompt = f"""You are a knowledgeable music expert. Answer considering the conversation context.

Previous conversation:
{conversation_context}

Current question: {request.question}

Provide an informative answer in 2-3 sentences. Respond in the same language as the question."""
        else:
            prompt = f"""You are a knowledgeable music expert. Answer this question:

Question: {request.question}

Provide an informative answer in 2-3 sentences. Respond in the same language as the question."""
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: llm.invoke(prompt))
        
        answer_text = response.content if hasattr(response, 'content') else str(response)
        cleaned_answer = clean_perplexity_output(answer_text)
        
        return AnswerResponse(question=request.question, answer=cleaned_answer)
        
    except Exception as e:
        print(f"[Q&A API] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get answer: {str(e)}")


# --- MAIN ---

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎵 Playlist Generator API v3.0")
    print("="*60)
    print("📖 Docs: http://localhost:8000/docs")
    print("🏥 Health: http://localhost:8000/health")
    print("📊 Stats: http://localhost:8000/stats")
    print("📡 SSE: http://localhost:8000/stream/{task_id}")
    print("💾 SQLite + Redis enabled")
    print("="*60 + "\n")
    
    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
