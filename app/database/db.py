"""
Database module for AI Resume ATS System
========================================

Provides database connectivity, schema management, and data operations
for the resume analysis and matching system.
"""

import logging
import sqlite3
from contextlib import contextmanager
from typing import Optional, Any, Dict, List
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

# Try to import aiosqlite, fallback to sync-only if not available
try:
    import aiosqlite
    _async_available = True
except ImportError:
    logger.warning("aiosqlite not available, using synchronous operations only")
    _async_available = False
    aiosqlite = None

# Global connection variables
_sync_conn: Optional[sqlite3.Connection] = None
_async_conn: Optional[Any] = None  # Can be aiosqlite.Connection if available


class DatabaseManager:
    """Professional database manager with connection pooling and error handling."""

    def __init__(self):
        self.db_path = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init_async_connection(self) -> None:
        """Initialize async database connection."""
        if not _async_available:
            logger.info("Async database operations not available (aiosqlite not installed)")
            return

        global _async_conn
        try:
            _async_conn = await aiosqlite.connect(self.db_path)
            await _async_conn.execute("PRAGMA journal_mode=WAL")
            await _async_conn.execute("PRAGMA synchronous=NORMAL")
            await _async_conn.execute("PRAGMA cache_size=1000")
            await _async_conn.execute("PRAGMA temp_store=memory")
            await self._create_tables_async()
            logger.info("✅ Async database connection established")
        except Exception as e:
            logger.error(f"❌ Failed to initialize async database: {e}")
            raise

    async def close_async_connection(self) -> None:
        """Close async database connection."""
        global _async_conn
        if not _async_available or not _async_conn:
            return

        try:
            await _async_conn.close()
            _async_conn = None
            logger.info("✅ Async database connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing async database: {e}")

    def init_sync_connection(self) -> sqlite3.Connection:
        """Initialize synchronous database connection."""
        global _sync_conn
        try:
            _sync_conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                isolation_level=None  # Enable autocommit mode
            )
            _sync_conn.execute("PRAGMA journal_mode=WAL")
            _sync_conn.execute("PRAGMA synchronous=NORMAL")
            _sync_conn.execute("PRAGMA cache_size=1000")
            _sync_conn.execute("PRAGMA temp_store=memory")
            self._create_tables_sync()
            logger.info("✅ Sync database connection established")
            return _sync_conn
        except Exception as e:
            logger.error(f"❌ Failed to initialize sync database: {e}")
            raise

    def close_sync_connection(self) -> None:
        """Close synchronous database connection."""
        global _sync_conn
        if _sync_conn:
            _sync_conn.close()
            _sync_conn = None
            logger.info("✅ Sync database connection closed")

    async def _create_tables_async(self) -> None:
        """Create database tables asynchronously."""
        if not _async_available:
            return

        schema = """
        -- Candidates table for storing processed resume data
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            location TEXT,
            linkedin TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Skills table for normalized skills data
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            skill_name TEXT NOT NULL,
            skill_category TEXT NOT NULL,
            confidence_score REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates (id) ON DELETE CASCADE
        );

        -- Processing history table
        CREATE TABLE IF NOT EXISTS processing_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            operation_type TEXT NOT NULL,
            input_data TEXT,
            output_data TEXT,
            processing_time REAL,
            success BOOLEAN DEFAULT 1,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates (id) ON DELETE CASCADE
        );

        -- Job matches table
        CREATE TABLE IF NOT EXISTS job_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            job_title TEXT NOT NULL,
            match_score REAL NOT NULL,
            matched_skills TEXT,  -- JSON string
            missing_skills TEXT,  -- JSON string
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates (id) ON DELETE CASCADE
        );

        -- Create indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_candidates_email ON candidates(email);
        CREATE INDEX IF NOT EXISTS idx_skills_candidate ON skills(candidate_id);
        CREATE INDEX IF NOT EXISTS idx_processing_history_candidate ON processing_history(candidate_id);
        CREATE INDEX IF NOT EXISTS idx_job_matches_candidate ON job_matches(candidate_id);
        """

        async with _async_conn.executescript(schema):
            pass

    def _create_tables_sync(self) -> None:
        """Create database tables synchronously."""
        schema = """
        -- Candidates table for storing processed resume data
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            location TEXT,
            linkedin TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Skills table for normalized skills data
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            skill_name TEXT NOT NULL,
            skill_category TEXT NOT NULL,
            confidence_score REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates (id) ON DELETE CASCADE
        );

        -- Processing history table
        CREATE TABLE IF NOT EXISTS processing_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            operation_type TEXT NOT NULL,
            input_data TEXT,
            output_data TEXT,
            processing_time REAL,
            success BOOLEAN DEFAULT 1,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates (id) ON DELETE CASCADE
        );

        -- Job matches table
        CREATE TABLE IF NOT EXISTS job_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            job_title TEXT NOT NULL,
            match_score REAL NOT NULL,
            matched_skills TEXT,  -- JSON string
            missing_skills TEXT,  -- JSON string
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates (id) ON DELETE CASCADE
        );

        -- Create indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_candidates_email ON candidates(email);
        CREATE INDEX IF NOT EXISTS idx_skills_candidate ON skills(candidate_id);
        CREATE INDEX IF NOT EXISTS idx_processing_history_candidate ON processing_history(candidate_id);
        CREATE INDEX IF NOT EXISTS idx_job_matches_candidate ON job_matches(candidate_id);
        """

        _sync_conn.executescript(schema)

    @contextmanager
    def get_sync_connection(self):
        """Context manager for synchronous database operations."""
        if not _sync_conn:
            self.init_sync_connection()
        try:
            yield _sync_conn
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            _sync_conn.rollback()
            raise
        else:
            _sync_conn.commit()


# Global database manager instance
db_manager = DatabaseManager()


# Public API functions for backward compatibility and main.py
async def init_database() -> None:
    """Initialize database connections and schema."""
    await db_manager.init_async_connection()


async def close_database() -> None:
    """Close database connections."""
    await db_manager.close_async_connection()


# Utility functions for data operations
async def save_candidate_data(candidate_data: Dict[str, Any]) -> int:
    """Save candidate information to database."""
    if not _async_available or not _async_conn:
        logger.warning("Async database not available, skipping candidate save")
        return 0

    async with _async_conn.execute("""
        INSERT INTO candidates (name, email, phone, location, linkedin)
        VALUES (?, ?, ?, ?, ?)
    """, (
        candidate_data.get("name", "Unknown"),
        candidate_data.get("email", ""),
        candidate_data.get("phone", ""),
        candidate_data.get("location", ""),
        candidate_data.get("linkedin", "")
    )) as cursor:
        return cursor.lastrowid


async def save_processing_history(
    candidate_id: Optional[int],
    operation_type: str,
    input_data: str,
    output_data: str,
    processing_time: float,
    success: bool = True,
    error_message: str = ""
) -> None:
    """Save processing operation to history."""
    if not _async_available or not _async_conn:
        logger.debug("Async database not available, skipping history save")
        return

    async with _async_conn.execute("""
        INSERT INTO processing_history
        (candidate_id, operation_type, input_data, output_data, processing_time, success, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (candidate_id, operation_type, input_data, output_data, processing_time, success, error_message)):
        pass


async def get_candidate_history(candidate_id: int) -> List[Dict[str, Any]]:
    """Get processing history for a candidate."""
    if not _async_available or not _async_conn:
        return []

    async with _async_conn.execute("""
        SELECT operation_type, processing_time, success, created_at
        FROM processing_history
        WHERE candidate_id = ?
        ORDER BY created_at DESC
    """, (candidate_id,)) as cursor:
        rows = await cursor.fetchall()
        return [
            {
                "operation": row[0],
                "processing_time": row[1],
                "success": bool(row[2]),
                "timestamp": row[3]
            }
            for row in rows
        ]