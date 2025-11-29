"""
SQLite Database Manager for persistence.

Tables:
- playlists: generated playlist history
- tracks: tracks within playlists
- conversations: Music Oracle conversation history
- tasks: async task status and results
"""

import aiosqlite
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database Path
DB_PATH = Path(__file__).parent.parent / "data" / "playlist_generator.db"

class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        # Ensure data directory exists
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = DB_PATH
        self._initialized = True

    async def init_db(self):
        """Initialize the database and create tables if they don't exist."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Playlists Table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS playlists (
                        id TEXT PRIMARY KEY,
                        description TEXT NOT NULL,
                        spotify_url TEXT,
                        title TEXT,
                        track_count INTEGER DEFAULT 0,
                        duration_minutes REAL DEFAULT 0,
                        generation_time REAL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        user_id TEXT DEFAULT 'default'
                    )
                """)
                
                # Tracks Table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS tracks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        playlist_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        artist TEXT NOT NULL,
                        album TEXT,
                        album_image TEXT,
                        duration INTEGER DEFAULT 0,
                        uri TEXT,
                        position INTEGER DEFAULT 0,
                        FOREIGN KEY (playlist_id) REFERENCES playlists(id)
                    )
                """)
                
                # Conversations Table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                """)
                
                # Tasks Table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        progress TEXT,
                        description TEXT,
                        result TEXT,
                        error TEXT,
                        created_at TEXT NOT NULL,
                        completed_at TEXT
                    )
                """)
                
                # Indexes
                await db.execute("CREATE INDEX IF NOT EXISTS idx_playlists_user ON playlists(user_id)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_playlists_created ON playlists(created_at)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_tracks_playlist ON tracks(playlist_id)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
                
                await db.commit()
                logger.info(f"[SQLite] Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"[SQLite] Initialization failed: {e}")
            raise

    # --- PLAYLIST OPERATIONS ---

    async def save_playlist(
        self,
        playlist_id: str,
        description: str,
        spotify_url: Optional[str] = None,
        title: Optional[str] = None,
        track_count: int = 0,
        duration_minutes: float = 0,
        generation_time: float = 0,
        user_id: str = "default"
    ) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO playlists 
                    (id, description, spotify_url, title, track_count, duration_minutes, generation_time, created_at, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    playlist_id, description, spotify_url, title, track_count,
                    duration_minutes, generation_time, datetime.now().isoformat(), user_id
                ))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"[SQLite] Error saving playlist {playlist_id}: {e}")
            return False

    async def save_tracks(self, playlist_id: str, tracks: List[Dict[str, Any]]) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM tracks WHERE playlist_id = ?", (playlist_id,))
                
                for i, track in enumerate(tracks):
                    await db.execute("""
                        INSERT INTO tracks (playlist_id, title, artist, album, album_image, duration, uri, position)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        playlist_id,
                        track.get("title", "Unknown"),
                        track.get("artist", "Unknown"),
                        track.get("album", ""),
                        track.get("album_image", ""),
                        track.get("duration", 0),
                        track.get("uri", ""),
                        i
                    ))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"[SQLite] Error saving tracks for {playlist_id}: {e}")
            return False

    async def get_playlists(self, user_id: str = "default", limit: int = 50) -> List[Dict[str, Any]]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM playlists 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (user_id, limit))
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"[SQLite] Error getting playlists: {e}")
            return []

    async def get_playlist_with_tracks(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM playlists WHERE id = ?", (playlist_id,))
                playlist_row = await cursor.fetchone()
                
                if not playlist_row:
                    return None
                
                playlist = dict(playlist_row)
                
                cursor = await db.execute("""
                    SELECT * FROM tracks WHERE playlist_id = ? ORDER BY position
                """, (playlist_id,))
                tracks_rows = await cursor.fetchall()
                playlist["tracks"] = [dict(row) for row in tracks_rows]
                
                return playlist
        except Exception as e:
            logger.error(f"[SQLite] Error getting playlist details {playlist_id}: {e}")
            return None

    async def delete_playlist(self, playlist_id: str) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM tracks WHERE playlist_id = ?", (playlist_id,))
                await db.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"[SQLite] Error deleting playlist {playlist_id}: {e}")
            return False

    # --- CONVERSATION OPERATIONS ---

    async def save_conversation_message(self, session_id: str, role: str, content: str) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO conversations (session_id, role, content, created_at)
                    VALUES (?, ?, ?, ?)
                """, (session_id, role, content, datetime.now().isoformat()))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"[SQLite] Error saving message: {e}")
            return False

    async def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT role, content, created_at FROM conversations 
                    WHERE session_id = ? 
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (session_id, limit))
                rows = await cursor.fetchall()
                return [dict(row) for row in reversed(rows)]
        except Exception as e:
            logger.error(f"[SQLite] Error getting history: {e}")
            return []

    async def clear_conversation(self, session_id: str) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"[SQLite] Error clearing conversation: {e}")
            return False

    # --- TASK OPERATIONS ---

    async def save_task(
        self,
        task_id: str,
        status: str,
        description: str,
        progress: Optional[str] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        completed_at: Optional[str] = None
    ) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                result_json = json.dumps(result) if result else None
                
                await db.execute("""
                    INSERT OR REPLACE INTO tasks 
                    (id, status, progress, description, result, error, created_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM tasks WHERE id = ?), ?), ?)
                """, (
                    task_id, status, progress, description, result_json, error,
                    task_id, datetime.now().isoformat(), completed_at
                ))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"[SQLite] Error saving task {task_id}: {e}")
            return False

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
                row = await cursor.fetchone()
                if row:
                    task = dict(row)
                    if task.get("result"):
                        task["result"] = json.loads(task["result"])
                    return task
                return None
        except Exception as e:
            logger.error(f"[SQLite] Error getting task {task_id}: {e}")
            return None

    async def get_recent_tasks(self, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?
                """, (limit,))
                rows = await cursor.fetchall()
                tasks = []
                for row in rows:
                    task = dict(row)
                    if task.get("result"):
                        task["result"] = json.loads(task["result"])
                    tasks.append(task)
                return tasks
        except Exception as e:
            logger.error(f"[SQLite] Error getting recent tasks: {e}")
            return []

    async def cleanup_old_tasks(self, days: int = 7) -> int:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    DELETE FROM tasks 
                    WHERE datetime(created_at) < datetime('now', ?)
                """, (f'-{days} days',))
                await db.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"[SQLite] Error cleaning old tasks: {e}")
            return 0

    # --- STATS ---

    async def get_stats(self) -> Dict[str, Any]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                stats = {}
                
                cursor = await db.execute("SELECT COUNT(*) FROM playlists")
                stats["total_playlists"] = (await cursor.fetchone())[0]
                
                cursor = await db.execute("SELECT COUNT(*) FROM tracks")
                stats["total_tracks"] = (await cursor.fetchone())[0]
                
                cursor = await db.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
                stats["completed_tasks"] = (await cursor.fetchone())[0]
                
                cursor = await db.execute("SELECT AVG(generation_time) FROM playlists WHERE generation_time > 0")
                avg_time = (await cursor.fetchone())[0]
                stats["avg_generation_time"] = round(avg_time, 2) if avg_time else 0
                
                return stats
        except Exception as e:
            logger.error(f"[SQLite] Error getting stats: {e}")
            return {}

# Global instance
db = DatabaseManager()

