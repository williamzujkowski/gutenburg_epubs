"""Database migration system for schema upgrades.

This module provides tools to manage database schema versions and
migrations between versions, ensuring smooth upgrades for users.
"""

import json
import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Migration:
    """Represents a database migration."""
    
    def __init__(
        self,
        version: str,
        description: str,
        upgrade_func: Callable[[sqlite3.Connection], None],
        downgrade_func: Optional[Callable[[sqlite3.Connection], None]] = None
    ):
        """Initialize migration.
        
        Args:
            version: Migration version (semantic versioning)
            description: Migration description
            upgrade_func: Function to upgrade to this version
            downgrade_func: Optional function to downgrade from this version
        """
        self.version = version
        self.description = description
        self.upgrade = upgrade_func
        self.downgrade = downgrade_func


class MigrationManager:
    """Manages database migrations and versioning."""
    
    # SQL to create migrations table
    MIGRATIONS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS _migrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        version TEXT NOT NULL,
        applied_at TIMESTAMP NOT NULL,
        description TEXT,
        metadata TEXT
    )
    """
    
    def __init__(self, db_path: str):
        """Initialize migration manager.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.migrations: List[Migration] = []
        self._initialize_migrations_table()
        
    def _initialize_migrations_table(self):
        """Initialize migrations tracking table."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(self.MIGRATIONS_TABLE_SQL)
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error initializing migrations table: {e}")
            raise
            
    def register_migration(self, migration: Migration):
        """Register a migration with the manager.
        
        Args:
            migration: Migration to register
        """
        self.migrations.append(migration)
        # Sort by version (semantic versioning)
        self.migrations.sort(key=lambda m: [int(x) for x in m.version.split('.')])
        logger.debug(f"Registered migration: {migration.version} - {migration.description}")
    
    def get_current_version(self) -> Optional[str]:
        """Get the current database schema version.
        
        Returns:
            Current version or None if no migrations have been applied
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT version FROM _migrations ORDER BY id DESC LIMIT 1"
                )
                result = cursor.fetchone()
                return result[0] if result else None
        except sqlite3.Error as e:
            logger.error(f"Error getting current version: {e}")
            return None
            
    def get_applied_migrations(self) -> List[Tuple[str, str, str]]:
        """Get list of applied migrations.
        
        Returns:
            List of (version, datetime, description) tuples
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT version, applied_at, description FROM _migrations ORDER BY id"
                )
                return [(row['version'], row['applied_at'], row['description'])
                        for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting applied migrations: {e}")
            return []
    
    def record_migration(
        self,
        version: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a migration as applied.
        
        Args:
            version: Migration version
            description: Migration description
            metadata: Optional metadata about the migration
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO _migrations (version, applied_at, description, metadata) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        version,
                        datetime.now().isoformat(),
                        description,
                        json.dumps(metadata) if metadata else None
                    )
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error recording migration: {e}")
            raise
    
    def migrate_to_latest(self, dry_run: bool = False) -> bool:
        """Upgrade database to the latest schema version.
        
        Args:
            dry_run: If True, only shows what would be done without making changes
            
        Returns:
            True if successful
        """
        current_version = self.get_current_version()
        logger.info(f"Current database version: {current_version or 'None (initial)'}")
        
        if not self.migrations:
            logger.info("No migrations registered")
            return True
        
        latest_version = self.migrations[-1].version
        
        if current_version == latest_version:
            logger.info(f"Database already at latest version: {latest_version}")
            return True
        
        applied_versions = set()
        if current_version:
            applied = self.get_applied_migrations()
            applied_versions = {v[0] for v in applied}
        
        migrations_to_apply = [
            m for m in self.migrations
            if m.version not in applied_versions
        ]
        
        if not migrations_to_apply:
            logger.info("No migrations to apply")
            return True
        
        logger.info(f"Upgrading database from version {current_version or 'None'} to {latest_version}")
        logger.info(f"Migrations to apply: {len(migrations_to_apply)}")
        
        if dry_run:
            for migration in migrations_to_apply:
                logger.info(f"Would apply migration: {migration.version} - {migration.description}")
            return True
        
        # Apply migrations
        for migration in migrations_to_apply:
            logger.info(f"Applying migration: {migration.version} - {migration.description}")
            start_time = time.time()
            
            try:
                with sqlite3.connect(self.db_path) as conn:
                    # Apply migration
                    migration.upgrade(conn)
                    conn.commit()
                
                # Record migration
                self.record_migration(
                    migration.version,
                    migration.description,
                    {
                        "duration_ms": int((time.time() - start_time) * 1000),
                        "applied_at": datetime.now().isoformat()
                    }
                )
                logger.info(f"Successfully applied migration: {migration.version}")
                
            except Exception as e:
                logger.error(f"Error applying migration {migration.version}: {e}")
                return False
        
        logger.info(f"Successfully upgraded database to version {latest_version}")
        return True
    
    def downgrade(self, target_version: Optional[str] = None, dry_run: bool = False) -> bool:
        """Downgrade database to a previous version.
        
        Args:
            target_version: Target version (None for one version back)
            dry_run: If True, only shows what would be done without making changes
            
        Returns:
            True if successful
        """
        current_version = self.get_current_version()
        if not current_version:
            logger.info("No migrations have been applied, nothing to downgrade")
            return True
        
        applied = self.get_applied_migrations()
        applied_versions = [v[0] for v in applied]
        
        if not target_version:
            # Default to previous version
            if len(applied_versions) <= 1:
                logger.info("Database is at initial version, cannot downgrade further")
                return True
            target_version = applied_versions[-2]
        
        if target_version not in applied_versions:
            logger.error(f"Target version {target_version} has not been applied")
            return False
        
        # Find migrations to downgrade
        current_index = applied_versions.index(current_version)
        target_index = applied_versions.index(target_version)
        
        if target_index > current_index:
            logger.error(f"Target version {target_version} is newer than current version {current_version}")
            return False
        
        versions_to_downgrade = applied_versions[target_index+1:current_index+1]
        versions_to_downgrade.reverse()  # Downgrade in reverse order
        
        # Find corresponding migration objects
        migrations_to_downgrade = []
        for version in versions_to_downgrade:
            migration = next((m for m in self.migrations if m.version == version), None)
            if not migration:
                logger.error(f"Cannot find migration for version {version}")
                return False
            if not migration.downgrade:
                logger.error(f"Migration {version} does not support downgrade")
                return False
            migrations_to_downgrade.append(migration)
        
        logger.info(f"Downgrading database from {current_version} to {target_version}")
        logger.info(f"Migrations to downgrade: {len(migrations_to_downgrade)}")
        
        if dry_run:
            for migration in migrations_to_downgrade:
                logger.info(f"Would downgrade migration: {migration.version} - {migration.description}")
            return True
        
        # Apply downgrades
        for migration in migrations_to_downgrade:
            logger.info(f"Downgrading migration: {migration.version} - {migration.description}")
            
            try:
                with sqlite3.connect(self.db_path) as conn:
                    # Apply downgrade
                    migration.downgrade(conn)  # type: ignore (already checked above)
                    conn.commit()
                
                # Remove migration record
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "DELETE FROM _migrations WHERE version = ?",
                        (migration.version,)
                    )
                    conn.commit()
                
                logger.info(f"Successfully downgraded migration: {migration.version}")
                
            except Exception as e:
                logger.error(f"Error downgrading migration {migration.version}: {e}")
                return False
        
        logger.info(f"Successfully downgraded database to version {target_version}")
        return True


# Define all migrations
MIGRATIONS = [
    Migration(
        version="0.1.0",
        description="Initial database schema",
        upgrade_func=lambda conn: conn.executescript("""
            -- Create books table
            CREATE TABLE IF NOT EXISTS books (
                book_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                language TEXT,
                download_count INTEGER,
                copyright_status BOOLEAN,
                media_type TEXT,
                metadata JSON,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(book_id)
            );
            
            -- Create authors table
            CREATE TABLE IF NOT EXISTS authors (
                author_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                birth_year INTEGER,
                death_year INTEGER,
                UNIQUE(name)
            );
            
            -- Create book_authors table (many-to-many)
            CREATE TABLE IF NOT EXISTS book_authors (
                book_id INTEGER,
                author_id INTEGER,
                PRIMARY KEY (book_id, author_id),
                FOREIGN KEY (book_id) REFERENCES books (book_id),
                FOREIGN KEY (author_id) REFERENCES authors (author_id)
            );
            
            -- Create subjects table
            CREATE TABLE IF NOT EXISTS subjects (
                subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                UNIQUE(name)
            );
            
            -- Create book_subjects table (many-to-many)
            CREATE TABLE IF NOT EXISTS book_subjects (
                book_id INTEGER,
                subject_id INTEGER,
                PRIMARY KEY (book_id, subject_id),
                FOREIGN KEY (book_id) REFERENCES books (book_id),
                FOREIGN KEY (subject_id) REFERENCES subjects (subject_id)
            );
            
            -- Create formats table
            CREATE TABLE IF NOT EXISTS formats (
                format_id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                format_type TEXT NOT NULL,
                url TEXT NOT NULL,
                mime_type TEXT,
                FOREIGN KEY (book_id) REFERENCES books (book_id)
            );
            
            -- Create downloads table
            CREATE TABLE IF NOT EXISTS downloads (
                download_id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                download_path TEXT NOT NULL,
                download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                bytes_downloaded INTEGER DEFAULT 0,
                total_bytes INTEGER DEFAULT 0,
                status TEXT CHECK(status IN ('pending', 'downloading', 'completed', 'failed')),
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                FOREIGN KEY (book_id) REFERENCES books(book_id),
                UNIQUE(book_id, download_path)
            );
            
            -- Create indexes
            CREATE INDEX IF NOT EXISTS idx_books_language ON books(language);
            CREATE INDEX IF NOT EXISTS idx_books_download_count ON books(download_count);
            CREATE INDEX IF NOT EXISTS idx_book_authors_book_id ON book_authors(book_id);
            CREATE INDEX IF NOT EXISTS idx_book_authors_author_id ON book_authors(author_id);
            CREATE INDEX IF NOT EXISTS idx_book_subjects_book_id ON book_subjects(book_id);
            CREATE INDEX IF NOT EXISTS idx_formats_book_id ON formats(book_id);
            CREATE INDEX IF NOT EXISTS idx_downloads_book_id ON downloads(book_id);
            CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads(status);
        """),
        downgrade_func=lambda conn: conn.executescript("""
            DROP TABLE IF EXISTS downloads;
            DROP TABLE IF EXISTS formats;
            DROP TABLE IF EXISTS book_subjects;
            DROP TABLE IF EXISTS subjects;
            DROP TABLE IF EXISTS book_authors;
            DROP TABLE IF EXISTS authors;
            DROP TABLE IF EXISTS books;
        """)
    ),
    Migration(
        version="0.2.0",
        description="Add full-text search capabilities",
        upgrade_func=lambda conn: conn.executescript("""
            -- Create FTS5 virtual table
            CREATE VIRTUAL TABLE IF NOT EXISTS books_fts USING fts5(
                book_id,
                title,
                author,
                subjects,
                content='books',
                content_rowid='book_id'
            );
            
            -- Create FTS table but don't use triggers that reference 'T.author'
            -- We'll handle FTS updates manually in the insert_book method
            CREATE TRIGGER IF NOT EXISTS books_fts_delete AFTER DELETE ON books BEGIN
                DELETE FROM books_fts WHERE book_id = old.book_id;
            END;
        """),
        downgrade_func=lambda conn: conn.executescript("""
            -- Drop FTS triggers
            DROP TRIGGER IF EXISTS books_ai;
            DROP TRIGGER IF EXISTS books_au;
            DROP TRIGGER IF EXISTS books_ad;
            DROP TRIGGER IF EXISTS book_authors_ai;
            DROP TRIGGER IF EXISTS book_authors_ad;
            DROP TRIGGER IF EXISTS book_subjects_ai;
            DROP TRIGGER IF EXISTS book_subjects_ad;
            
            -- Drop FTS table
            DROP TABLE IF EXISTS books_fts;
        """)
    ),
    Migration(
        version="0.3.0",
        description="Add caching system",
        upgrade_func=lambda conn: conn.executescript("""
            -- Create cache table
            CREATE TABLE IF NOT EXISTS cache (
                cache_key TEXT PRIMARY KEY,
                data BLOB,
                content_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                metadata TEXT
            );
            
            -- Create cache index
            CREATE INDEX IF NOT EXISTS idx_cache_expires_at ON cache(expires_at);
        """),
        downgrade_func=lambda conn: conn.executescript("""
            -- Drop cache table
            DROP TABLE IF EXISTS cache;
        """)
    ),
    Migration(
        version="0.4.0",
        description="Add download statistics",
        upgrade_func=lambda conn: conn.executescript("""
            -- Create download stats table
            CREATE TABLE IF NOT EXISTS download_stats (
                stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                download_duration_ms INTEGER,
                file_size_bytes INTEGER,
                success BOOLEAN,
                error_message TEXT,
                source TEXT,
                FOREIGN KEY (book_id) REFERENCES books (book_id)
            );
            
            -- Create session stats table
            CREATE TABLE IF NOT EXISTS session_stats (
                session_id TEXT PRIMARY KEY,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                total_downloads INTEGER DEFAULT 0,
                successful_downloads INTEGER DEFAULT 0,
                failed_downloads INTEGER DEFAULT 0,
                total_bytes_downloaded INTEGER DEFAULT 0,
                avg_download_speed_bps REAL
            );
            
            -- Add indexes
            CREATE INDEX IF NOT EXISTS idx_download_stats_book_id ON download_stats(book_id);
            CREATE INDEX IF NOT EXISTS idx_download_stats_date ON download_stats(download_date);
            CREATE INDEX IF NOT EXISTS idx_session_stats_time ON session_stats(start_time, end_time);
        """),
        downgrade_func=lambda conn: conn.executescript("""
            -- Drop download stats tables
            DROP TABLE IF EXISTS download_stats;
            DROP TABLE IF EXISTS session_stats;
        """)
    ),
    Migration(
        version="0.5.0",
        description="Enhanced metadata: Add bookshelves and genres tables",
        upgrade_func=lambda conn: conn.executescript("""
            -- Create bookshelves table
            CREATE TABLE IF NOT EXISTS bookshelves (
                bookshelf_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                UNIQUE(name)
            );
            
            -- Create book_bookshelves table (many-to-many)
            CREATE TABLE IF NOT EXISTS book_bookshelves (
                book_id INTEGER,
                bookshelf_id INTEGER,
                PRIMARY KEY (book_id, bookshelf_id),
                FOREIGN KEY (book_id) REFERENCES books (book_id),
                FOREIGN KEY (bookshelf_id) REFERENCES bookshelves (bookshelf_id)
            );
            
            -- Create genres table
            CREATE TABLE IF NOT EXISTS genres (
                genre_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_genre_id INTEGER,
                UNIQUE(name),
                FOREIGN KEY (parent_genre_id) REFERENCES genres (genre_id)
            );
            
            -- Create book_genres table (many-to-many)
            CREATE TABLE IF NOT EXISTS book_genres (
                book_id INTEGER,
                genre_id INTEGER,
                confidence REAL DEFAULT 1.0,  -- How confident we are in this genre classification (0.0-1.0)
                source TEXT,  -- Where this genre classification came from (e.g., 'api', 'bookshelf', 'subject')
                PRIMARY KEY (book_id, genre_id),
                FOREIGN KEY (book_id) REFERENCES books (book_id),
                FOREIGN KEY (genre_id) REFERENCES genres (genre_id)
            );
            
            -- Add metadata_version field to books table
            ALTER TABLE books ADD COLUMN metadata_version INTEGER DEFAULT 1;
            
            -- Add full_metadata field to books table (to hold complete JSON from various sources)
            ALTER TABLE books ADD COLUMN full_metadata JSON;
            
            -- Create indexes
            CREATE INDEX IF NOT EXISTS idx_book_bookshelves_book_id ON book_bookshelves(book_id);
            CREATE INDEX IF NOT EXISTS idx_book_bookshelves_bookshelf_id ON book_bookshelves(bookshelf_id);
            CREATE INDEX IF NOT EXISTS idx_book_genres_book_id ON book_genres(book_id);
            CREATE INDEX IF NOT EXISTS idx_book_genres_genre_id ON book_genres(genre_id);
            CREATE INDEX IF NOT EXISTS idx_book_genres_confidence ON book_genres(confidence);
            
            -- Create FTS5 index for searching genres
            CREATE VIRTUAL TABLE IF NOT EXISTS genres_fts USING fts5(
                genre_id,
                name,
                content='genres',
                content_rowid='genre_id'
            );
            
            -- Add trigger to keep genres_fts in sync
            CREATE TRIGGER IF NOT EXISTS genres_fts_insert AFTER INSERT ON genres BEGIN
                INSERT INTO genres_fts(genre_id, name) VALUES (new.genre_id, new.name);
            END;
            
            CREATE TRIGGER IF NOT EXISTS genres_fts_update AFTER UPDATE ON genres BEGIN
                UPDATE genres_fts SET name = new.name WHERE genre_id = new.genre_id;
            END;
            
            CREATE TRIGGER IF NOT EXISTS genres_fts_delete AFTER DELETE ON genres BEGIN
                DELETE FROM genres_fts WHERE genre_id = old.genre_id;
            END;
            
            -- Add support for bookshelves to FTS
            DROP TABLE IF EXISTS books_fts;
            CREATE VIRTUAL TABLE IF NOT EXISTS books_fts USING fts5(
                book_id,
                title,
                author,
                subjects,
                bookshelves,
                genres,
                content='books',
                content_rowid='book_id'
            );
        """),
        downgrade_func=lambda conn: conn.executescript("""
            -- Drop FTS tables first
            DROP TABLE IF EXISTS genres_fts;
            DROP TABLE IF EXISTS books_fts;
            CREATE VIRTUAL TABLE IF NOT EXISTS books_fts USING fts5(
                book_id,
                title,
                author,
                subjects,
                content='books',
                content_rowid='book_id'
            );
            
            -- Drop triggers
            DROP TRIGGER IF EXISTS genres_fts_insert;
            DROP TRIGGER IF EXISTS genres_fts_update;
            DROP TRIGGER IF EXISTS genres_fts_delete;
            
            -- Drop tables
            DROP TABLE IF EXISTS book_genres;
            DROP TABLE IF EXISTS genres;
            DROP TABLE IF EXISTS book_bookshelves;
            DROP TABLE IF EXISTS bookshelves;
            
            -- Remove columns from books table
            CREATE TABLE books_backup (
                book_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                language TEXT,
                download_count INTEGER,
                copyright_status BOOLEAN,
                media_type TEXT,
                metadata JSON,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(book_id)
            );
            
            INSERT INTO books_backup SELECT 
                book_id, title, language, download_count, copyright_status, 
                media_type, metadata, last_updated
            FROM books;
            
            DROP TABLE books;
            ALTER TABLE books_backup RENAME TO books;
            
            -- Recreate indexes
            CREATE INDEX IF NOT EXISTS idx_books_language ON books(language);
            CREATE INDEX IF NOT EXISTS idx_books_download_count ON books(download_count);
        """)
    )
]


# Default instance with common migrations
def get_migration_manager(db_path: str) -> MigrationManager:
    """Get a migration manager with all predefined migrations.
    
    Args:
        db_path: Path to database
        
    Returns:
        Configured migration manager
    """
    manager = MigrationManager(db_path)
    for migration in MIGRATIONS:
        manager.register_migration(migration)
    return manager