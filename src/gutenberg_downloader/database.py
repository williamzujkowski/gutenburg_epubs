"""Database module for storing and managing book metadata."""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List, Dict, Tuple
from contextlib import contextmanager

from .constants import BASE_URL

logger = logging.getLogger(__name__)


class BookDatabase:
    """SQLite database for storing book metadata and download information."""
    
    def __init__(
        self, 
        db_path: str = "gutenberg_books.db",
        auto_migrate: bool = True,
        run_migrations: bool = True
    ):
        """Initialize the database.
        
        Args:
            db_path: Path to the SQLite database file
            auto_migrate: Whether to automatically apply migrations
            run_migrations: Whether to run migration system at all
        """
        self.db_path = db_path
        
        if run_migrations:
            # Use migration system for schema setup/updates
            from .migrations import get_migration_manager
            
            # Initialize migration manager
            self.migration_manager = get_migration_manager(db_path)
            
            # Check current version and apply migrations if needed
            current_version = self.migration_manager.get_current_version()
            
            if auto_migrate:
                if current_version:
                    logger.info(f"Database current version: {current_version}")
                else:
                    logger.info("Initializing database with migrations")
                
                # Apply any pending migrations
                success = self.migration_manager.migrate_to_latest()
                if not success:
                    logger.error("Failed to apply migrations")
            else:
                # Use legacy table creation if migrations disabled
                self._create_tables()
                
        else:
            # Use legacy table creation
            self._create_tables()
            
        logger.info(f"Initialized book database at {db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Main books table
            cursor.execute("""
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
                )
            """)
            
            # Authors table (many-to-many relationship)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS authors (
                    author_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    birth_year INTEGER,
                    death_year INTEGER,
                    UNIQUE(name)
                )
            """)
            
            # Book-Author relationship table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS book_authors (
                    book_id INTEGER,
                    author_id INTEGER,
                    PRIMARY KEY (book_id, author_id),
                    FOREIGN KEY (book_id) REFERENCES books(book_id),
                    FOREIGN KEY (author_id) REFERENCES authors(author_id)
                )
            """)
            
            # Subjects/Categories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subjects (
                    subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    UNIQUE(name)
                )
            """)
            
            # Book-Subject relationship table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS book_subjects (
                    book_id INTEGER,
                    subject_id INTEGER,
                    PRIMARY KEY (book_id, subject_id),
                    FOREIGN KEY (book_id) REFERENCES books(book_id),
                    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
                )
            """)
            
            # Download formats table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS formats (
                    format_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER,
                    format_type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    mime_type TEXT,
                    FOREIGN KEY (book_id) REFERENCES books(book_id)
                )
            """)
            
            # Enhanced download history table with resume capability
            cursor.execute("""
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
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_language ON books(language)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_download_count ON books(download_count)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloads_book_id ON downloads(book_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_formats_book_id ON formats(book_id)")
            
            # Create FTS5 table for full-text search
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS books_fts USING fts5(
                    book_id,
                    title,
                    author,
                    subjects,
                    content='books',
                    content_rowid='book_id'
                )
            """)
            
            # Create triggers to keep FTS index in sync
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS books_fts_insert AFTER INSERT ON books
                BEGIN
                    INSERT INTO books_fts(book_id, title, author)
                    SELECT new.book_id, new.title, 
                           COALESCE((SELECT GROUP_CONCAT(a.name, ', ')
                                    FROM book_authors ba
                                    JOIN authors a ON ba.author_id = a.author_id
                                    WHERE ba.book_id = new.book_id), '');
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS books_fts_update AFTER UPDATE ON books
                BEGIN
                    UPDATE books_fts
                    SET title = new.title
                    WHERE book_id = new.book_id;
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS books_fts_delete AFTER DELETE ON books
                BEGIN
                    DELETE FROM books_fts WHERE book_id = old.book_id;
                END
            """)
            
            conn.commit()
    
    def insert_book(self, book_data: Dict[str, Any]) -> bool:
        """Insert or update a book in the database.
        
        Args:
            book_data: Dictionary containing book information from API
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if we have full_metadata column (migration 0.5.0+)
                has_full_metadata = False
                try:
                    cursor.execute("SELECT full_metadata FROM books LIMIT 1")
                    has_full_metadata = True
                except sqlite3.OperationalError:
                    pass
                
                # Prepare SQL statement based on schema version
                if has_full_metadata:
                    # Enhanced schema with metadata_version and full_metadata
                    cursor.execute("""
                        INSERT OR REPLACE INTO books 
                        (book_id, title, language, download_count, copyright_status, media_type, 
                         metadata, metadata_version, full_metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        book_data['id'],
                        book_data.get('title', 'Unknown Title'),
                        book_data.get('languages', [''])[0] if book_data.get('languages') else None,
                        book_data.get('download_count', 0),
                        book_data.get('copyright'),
                        book_data.get('media_type'),
                        json.dumps(book_data),
                        2,  # Current metadata version
                        json.dumps(book_data.get('raw_data', book_data))  # Store complete API response
                    ))
                else:
                    # Original schema
                    cursor.execute("""
                        INSERT OR REPLACE INTO books 
                        (book_id, title, language, download_count, copyright_status, media_type, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        book_data['id'],
                        book_data.get('title', 'Unknown Title'),
                        book_data.get('languages', [''])[0] if book_data.get('languages') else None,
                        book_data.get('download_count', 0),
                        book_data.get('copyright'),
                        book_data.get('media_type'),
                        json.dumps(book_data)
                    ))
                
                book_id = book_data['id']
                
                # Handle authors
                for author in book_data.get('authors', []):
                    # Handle both string and dict authors
                    if isinstance(author, dict):
                        author_name = author.get('name')
                        birth_year = author.get('birth_year')
                        death_year = author.get('death_year')
                    else:
                        author_name = author
                        birth_year = None
                        death_year = None
                    
                    if not author_name:
                        continue
                        
                    # Insert author if not exists
                    cursor.execute("""
                        INSERT OR IGNORE INTO authors (name, birth_year, death_year)
                        VALUES (?, ?, ?)
                    """, (author_name, birth_year, death_year))
                    
                    # Get author ID
                    cursor.execute("SELECT author_id FROM authors WHERE name = ?", (author_name,))
                    author_id = cursor.fetchone()[0]
                    
                    # Create book-author relationship
                    cursor.execute("""
                        INSERT OR IGNORE INTO book_authors (book_id, author_id)
                        VALUES (?, ?)
                    """, (book_id, author_id))
                
                # Handle subjects
                for subject in book_data.get('subjects', []):
                    # Insert subject if not exists
                    cursor.execute("""
                        INSERT OR IGNORE INTO subjects (name)
                        VALUES (?)
                    """, (subject,))
                    
                    # Get subject ID
                    cursor.execute("SELECT subject_id FROM subjects WHERE name = ?", (subject,))
                    subject_id = cursor.fetchone()[0]
                    
                    # Create book-subject relationship
                    cursor.execute("""
                        INSERT OR IGNORE INTO book_subjects (book_id, subject_id)
                        VALUES (?, ?)
                    """, (book_id, subject_id))
                
                # Handle bookshelves if migration 0.5.0+ is applied
                try:
                    for bookshelf in book_data.get('bookshelves', []):
                        # Insert bookshelf if not exists
                        cursor.execute("""
                            INSERT OR IGNORE INTO bookshelves (name)
                            VALUES (?)
                        """, (bookshelf,))
                        
                        # Get bookshelf ID
                        cursor.execute("SELECT bookshelf_id FROM bookshelves WHERE name = ?", (bookshelf,))
                        bookshelf_id = cursor.fetchone()[0]
                        
                        # Create book-bookshelf relationship
                        cursor.execute("""
                            INSERT OR IGNORE INTO book_bookshelves (book_id, bookshelf_id)
                            VALUES (?, ?)
                        """, (book_id, bookshelf_id))
                except sqlite3.OperationalError:
                    # Table doesn't exist yet, skip
                    pass
                
                # Handle genres if migration 0.5.0+ is applied
                try:
                    for genre in book_data.get('genres', []):
                        # Insert genre if not exists
                        cursor.execute("""
                            INSERT OR IGNORE INTO genres (name)
                            VALUES (?)
                        """, (genre,))
                        
                        # Get genre ID
                        cursor.execute("SELECT genre_id FROM genres WHERE name = ?", (genre,))
                        genre_id = cursor.fetchone()[0]
                        
                        # Create book-genre relationship with source info
                        cursor.execute("""
                            INSERT OR IGNORE INTO book_genres (book_id, genre_id, confidence, source)
                            VALUES (?, ?, ?, ?)
                        """, (book_id, genre_id, 1.0, 'api'))
                except sqlite3.OperationalError:
                    # Table doesn't exist yet, skip
                    pass
                
                # Handle formats
                formats = book_data.get('formats', {})
                for format_type, url in formats.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO formats (book_id, format_type, url, mime_type)
                        VALUES (?, ?, ?, ?)
                    """, (book_id, format_type, url, format_type))
                    
                # Update FTS table
                try:
                    # Get authors for this book
                    cursor.execute("""
                        SELECT GROUP_CONCAT(a.name, ' ') 
                        FROM authors a 
                        JOIN book_authors ba ON a.author_id = ba.author_id 
                        WHERE ba.book_id = ?
                    """, (book_id,))
                    author_names = cursor.fetchone()[0] or ''
                    
                    # Get subjects for this book
                    cursor.execute("""
                        SELECT GROUP_CONCAT(s.name, ' ') 
                        FROM subjects s 
                        JOIN book_subjects bs ON s.subject_id = bs.subject_id 
                        WHERE bs.book_id = ?
                    """, (book_id,))
                    subject_names = cursor.fetchone()[0] or ''
                    
                    # Check if we have the enhanced FTS schema with bookshelves and genres
                    try:
                        # Get bookshelves for this book
                        cursor.execute("""
                            SELECT GROUP_CONCAT(b.name, ' ') 
                            FROM bookshelves b 
                            JOIN book_bookshelves bb ON b.bookshelf_id = bb.bookshelf_id 
                            WHERE bb.book_id = ?
                        """, (book_id,))
                        bookshelf_names = cursor.fetchone()[0] or ''
                        
                        # Get genres for this book
                        cursor.execute("""
                            SELECT GROUP_CONCAT(g.name, ' ') 
                            FROM genres g 
                            JOIN book_genres bg ON g.genre_id = bg.genre_id 
                            WHERE bg.book_id = ?
                        """, (book_id,))
                        genre_names = cursor.fetchone()[0] or ''
                        
                        # Insert or replace in enhanced FTS table
                        cursor.execute("""
                            INSERT OR REPLACE INTO books_fts(book_id, title, author, subjects, bookshelves, genres)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            book_id,
                            book_data.get('title', 'Unknown Title'),
                            author_names,
                            subject_names,
                            bookshelf_names,
                            genre_names
                        ))
                    except sqlite3.OperationalError:
                        # Fall back to original FTS schema
                        cursor.execute("""
                            INSERT OR REPLACE INTO books_fts(book_id, title, author, subjects)
                            VALUES (?, ?, ?, ?)
                        """, (
                            book_id,
                            book_data.get('title', 'Unknown Title'),
                            author_names,
                            subject_names
                        ))
                except sqlite3.OperationalError as e:
                    logger.warning(f"Error updating FTS table: {e}")
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error inserting book {book_data.get('id')}: {e}")
            return False
    
    def bulk_insert_books(self, books_data: List[Dict[str, Any]]) -> int:
        """Insert multiple books in a single transaction.
        
        Args:
            books_data: List of book dictionaries
            
        Returns:
            Number of books successfully inserted
        """
        from tqdm import tqdm
        
        inserted = 0
        batch_size = 100  # Process in batches
        total_books = len(books_data)
        
        with self._get_connection() as conn:
            # Create progress bar for batch processing
            pbar = tqdm(total=total_books, desc="Processing books", unit="books", 
                       leave=False, colour="blue")
            
            for i in range(0, total_books, batch_size):
                batch = books_data[i:i + batch_size]
                conn.execute("BEGIN TRANSACTION")
                
                try:
                    for book_data in batch:
                        if self.insert_book(book_data):
                            inserted += 1
                            pbar.update(1)
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Error in bulk insert batch {i//batch_size + 1}: {e}")
                    pbar.update(len(batch))  # Update progress even on error
            
            pbar.close()
        
        logger.info(f"Successfully inserted {inserted} of {len(books_data)} books")
        return inserted
    
    def get_book(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Get a book by its ID.
        
        Args:
            book_id: Project Gutenberg book ID
            
        Returns:
            Book data dictionary or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get book data
            cursor.execute("""
                SELECT * FROM books WHERE book_id = ?
            """, (book_id,))
            
            book = cursor.fetchone()
            if not book:
                return None
            
            # Convert to dictionary
            book_dict = dict(book)
            if book_dict['metadata']:
                book_dict['metadata'] = json.loads(book_dict['metadata'])
            
            # Get authors
            cursor.execute("""
                SELECT a.* FROM authors a
                JOIN book_authors ba ON a.author_id = ba.author_id
                WHERE ba.book_id = ?
            """, (book_id,))
            book_dict['authors'] = [dict(author) for author in cursor.fetchall()]
            
            # Get subjects
            cursor.execute("""
                SELECT s.name FROM subjects s
                JOIN book_subjects bs ON s.subject_id = bs.subject_id
                WHERE bs.book_id = ?
            """, (book_id,))
            book_dict['subjects'] = [row['name'] for row in cursor.fetchall()]
            
            # Get formats
            cursor.execute("""
                SELECT format_type, url FROM formats WHERE book_id = ?
            """, (book_id,))
            book_dict['formats'] = {row['format_type']: row['url'] for row in cursor.fetchall()}
            
            return book_dict
    
    def search_books(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        language: Optional[str] = None,
        subject: Optional[str] = None,
        min_downloads: Optional[int] = None,
        has_epub: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search for books with various filters.
        
        Args:
            title: Title search term
            author: Author search term
            language: Language code (e.g., 'en')
            subject: Subject/category search term
            min_downloads: Minimum download count
            has_epub: Only return books with EPUB format
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of matching books
        """
        query = """
            SELECT DISTINCT b.* FROM books b
            LEFT JOIN book_authors ba ON b.book_id = ba.book_id
            LEFT JOIN authors a ON ba.author_id = a.author_id
            LEFT JOIN book_subjects bs ON b.book_id = bs.book_id
            LEFT JOIN subjects s ON bs.subject_id = s.subject_id
            LEFT JOIN formats f ON b.book_id = f.book_id
            WHERE 1=1
        """
        params = []
        
        if title:
            query += " AND b.title LIKE ?"
            params.append(f"%{title}%")
        
        if author:
            query += " AND a.name LIKE ?"
            params.append(f"%{author}%")
        
        if language:
            query += " AND b.language = ?"
            params.append(language)
        
        if subject:
            query += " AND s.name LIKE ?"
            params.append(f"%{subject}%")
        
        if min_downloads:
            query += " AND b.download_count >= ?"
            params.append(min_downloads)
        
        if has_epub:
            query += " AND f.format_type LIKE '%epub%'"
        
        query += " ORDER BY b.download_count DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            books = []
            for row in cursor.fetchall():
                book_dict = dict(row)
                if book_dict['metadata']:
                    book_dict['metadata'] = json.loads(book_dict['metadata'])
                books.append(book_dict)
            
            return books
    
    def get_popular_english_epubs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get popular English books with EPUB format.
        
        Args:
            limit: Maximum number of books to return
            
        Returns:
            List of popular English EPUB books
        """
        return self.search_books(
            language='en',
            has_epub=True,
            limit=limit
        )
    
    def mark_downloaded(self, book_id: int, file_path: str, file_size: int, status: str = "completed"):
        """Mark a book as downloaded.
        
        Args:
            book_id: Project Gutenberg book ID
            file_path: Path where the book was downloaded
            file_size: Size of the downloaded file
            status: Download status
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO downloads (book_id, download_path, file_size, status)
                VALUES (?, ?, ?, ?)
            """, (book_id, file_path, file_size, status))
            conn.commit()
    
    def is_downloaded(self, book_id: int) -> bool:
        """Check if a book has been downloaded.
        
        Args:
            book_id: Project Gutenberg book ID
            
        Returns:
            True if the book has been downloaded
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM downloads 
                WHERE book_id = ? AND status = 'completed'
            """, (book_id,))
            return cursor.fetchone()[0] > 0
    
    def full_text_search(
        self,
        query: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search books using full-text search.
        
        Args:
            query: Search query
            limit: Maximum results to return
            offset: Results offset for pagination
            
        Returns:
            List of matching books
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Use direct search without FTS since we're having issues
                # Create a search pattern with wildcards
                search_pattern = f"%{query}%"
                
                query_sql = """
                    SELECT DISTINCT b.* 
                    FROM books b
                    LEFT JOIN book_authors ba ON b.book_id = ba.book_id
                    LEFT JOIN authors a ON ba.author_id = a.author_id
                    LEFT JOIN book_subjects bs ON b.book_id = bs.book_id
                    LEFT JOIN subjects s ON bs.subject_id = s.subject_id
                    WHERE 
                        b.title LIKE ? OR
                        a.name LIKE ? OR
                        s.name LIKE ?
                    ORDER BY b.download_count DESC
                    LIMIT ? OFFSET ?
                """
                
                cursor.execute(query_sql, (
                    search_pattern, 
                    search_pattern, 
                    search_pattern, 
                    limit, 
                    offset
                ))
                
                results = []
                for row in cursor.fetchall():
                    book = dict(row)
                    # Parse metadata JSON
                    if book['metadata']:
                        book['metadata'] = json.loads(book['metadata'])
                    
                    # Get authors
                    cursor.execute("""
                        SELECT a.* FROM authors a
                        JOIN book_authors ba ON a.author_id = ba.author_id
                        WHERE ba.book_id = ?
                    """, (book['book_id'],))
                    book['authors'] = [dict(author) for author in cursor.fetchall()]
                    
                    # Get subjects
                    cursor.execute("""
                        SELECT s.name FROM subjects s
                        JOIN book_subjects bs ON s.subject_id = bs.subject_id
                        WHERE bs.book_id = ?
                    """, (book['book_id'],))
                    book['subjects'] = [row['name'] for row in cursor.fetchall()]
                    
                    # Get formats
                    cursor.execute("""
                        SELECT format_type, url FROM formats 
                        WHERE book_id = ?
                    """, (book['book_id'],))
                    book['formats'] = {row['format_type']: row['url'] for row in cursor.fetchall()}
                    
                    results.append(book)
                
                return results
                
        except Exception as e:
            logger.error(f"Error searching books: {e}")
            return []
    
    def rebuild_fts_index(self):
        """Rebuild the full-text search index."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Clear existing FTS data
            cursor.execute("DELETE FROM books_fts")
            
            # Rebuild from books table
            cursor.execute("""
                INSERT INTO books_fts(book_id, title, author, subjects)
                SELECT 
                    b.book_id,
                    b.title,
                    COALESCE((SELECT GROUP_CONCAT(a.name, ', ')
                             FROM book_authors ba
                             JOIN authors a ON ba.author_id = a.author_id
                             WHERE ba.book_id = b.book_id), ''),
                    COALESCE((SELECT GROUP_CONCAT(s.subject_name, ', ')
                             FROM book_subjects bs
                             JOIN subjects s ON bs.subject_id = s.subject_id
                             WHERE bs.book_id = b.book_id), '')
                FROM books b
            """)
            
            conn.commit()
            logger.info("Full-text search index rebuilt")
    
    def get_database_version(self) -> Optional[str]:
        """Get current database schema version.
        
        Returns:
            Version string or None if migrations not used
        """
        if hasattr(self, 'migration_manager'):
            return self.migration_manager.get_current_version()
        return None
    
    def get_available_migrations(self) -> List[Tuple[str, str]]:
        """Get list of available migrations.
        
        Returns:
            List of (version, description) tuples
        """
        if hasattr(self, 'migration_manager'):
            return [(m.version, m.description) for m in self.migration_manager.migrations]
        return []
    
    def get_applied_migrations(self) -> List[Tuple[str, str, str]]:
        """Get list of applied migrations.
        
        Returns:
            List of (version, timestamp, description) tuples
        """
        if hasattr(self, 'migration_manager'):
            return self.migration_manager.get_applied_migrations()
        return []
    
    def migrate_to_latest(self, dry_run: bool = False) -> bool:
        """Upgrade database to latest version.
        
        Args:
            dry_run: If True, only show what would be done
            
        Returns:
            True if successful (or no migrations available)
        """
        if hasattr(self, 'migration_manager'):
            return self.migration_manager.migrate_to_latest(dry_run=dry_run)
        logger.warning("Migration system not active")
        return False
    
    def downgrade(self, target_version: Optional[str] = None, dry_run: bool = False) -> bool:
        """Downgrade database to a previous version.
        
        Args:
            target_version: Target version or None for one version back
            dry_run: If True, only show what would be done
            
        Returns:
            True if successful
        """
        if hasattr(self, 'migration_manager'):
            return self.migration_manager.downgrade(target_version=target_version, dry_run=dry_run)
        logger.warning("Migration system not active")
        return False
        
    def get_book_genres(self, book_id: int) -> List[Dict[str, Any]]:
        """Get all genres for a book.
        
        Args:
            book_id: Project Gutenberg book ID
            
        Returns:
            List of genre dictionaries with name, confidence, and source
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if the genres table exists (migration 0.5.0+)
                try:
                    cursor.execute("""
                        SELECT g.genre_id, g.name, bg.confidence, bg.source
                        FROM genres g
                        JOIN book_genres bg ON g.genre_id = bg.genre_id
                        WHERE bg.book_id = ?
                        ORDER BY bg.confidence DESC
                    """, (book_id,))
                    
                    return [dict(row) for row in cursor.fetchall()]
                except sqlite3.OperationalError:
                    # Table doesn't exist yet or book has no genres
                    return []
        except Exception as e:
            logger.error(f"Error getting genres for book {book_id}: {e}")
            return []
    
    def get_book_bookshelves(self, book_id: int) -> List[str]:
        """Get all bookshelves for a book.
        
        Args:
            book_id: Project Gutenberg book ID
            
        Returns:
            List of bookshelf names
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if the bookshelves table exists (migration 0.5.0+)
                try:
                    cursor.execute("""
                        SELECT b.name
                        FROM bookshelves b
                        JOIN book_bookshelves bb ON b.bookshelf_id = bb.bookshelf_id
                        WHERE bb.book_id = ?
                        ORDER BY b.name
                    """, (book_id,))
                    
                    return [row['name'] for row in cursor.fetchall()]
                except sqlite3.OperationalError:
                    # Table doesn't exist yet or book has no bookshelves
                    return []
        except Exception as e:
            logger.error(f"Error getting bookshelves for book {book_id}: {e}")
            return []
    
    def search_by_genre(self, genre: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Search for books by genre.
        
        Args:
            genre: Genre to search for
            limit: Maximum number of results
            
        Returns:
            List of books with the specified genre
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if the genres table exists (migration 0.5.0+)
                try:
                    cursor.execute("""
                        SELECT b.*
                        FROM books b
                        JOIN book_genres bg ON b.book_id = bg.book_id
                        JOIN genres g ON bg.genre_id = g.genre_id
                        WHERE g.name LIKE ?
                        ORDER BY bg.confidence DESC, b.download_count DESC
                        LIMIT ?
                    """, (f'%{genre}%', limit))
                    
                    books = []
                    for row in cursor.fetchall():
                        book = dict(row)
                        if book['metadata']:
                            book['metadata'] = json.loads(book['metadata'])
                        books.append(book)
                    
                    return books
                except sqlite3.OperationalError:
                    # Table doesn't exist yet or no matching books
                    return []
        except Exception as e:
            logger.error(f"Error searching books by genre {genre}: {e}")
            return []
    
    def search_by_bookshelf(self, bookshelf: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Search for books by bookshelf.
        
        Args:
            bookshelf: Bookshelf to search for
            limit: Maximum number of results
            
        Returns:
            List of books on the specified bookshelf
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if the bookshelves table exists (migration 0.5.0+)
                try:
                    cursor.execute("""
                        SELECT b.*
                        FROM books b
                        JOIN book_bookshelves bb ON b.book_id = bb.book_id
                        JOIN bookshelves bs ON bb.bookshelf_id = bs.bookshelf_id
                        WHERE bs.name LIKE ?
                        ORDER BY b.download_count DESC
                        LIMIT ?
                    """, (f'%{bookshelf}%', limit))
                    
                    books = []
                    for row in cursor.fetchall():
                        book = dict(row)
                        if book['metadata']:
                            book['metadata'] = json.loads(book['metadata'])
                        books.append(book)
                    
                    return books
                except sqlite3.OperationalError:
                    # Table doesn't exist yet or no matching books
                    return []
        except Exception as e:
            logger.error(f"Error searching books by bookshelf {bookshelf}: {e}")
            return []
            
    def get_all_genres(self) -> List[Dict[str, Any]]:
        """Get all genres in the database.
        
        Returns:
            List of genre dictionaries with id, name and book count
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if the genres table exists (migration 0.5.0+)
                try:
                    cursor.execute("""
                        SELECT g.genre_id, g.name, COUNT(bg.book_id) as book_count
                        FROM genres g
                        LEFT JOIN book_genres bg ON g.genre_id = bg.genre_id
                        GROUP BY g.genre_id
                        ORDER BY book_count DESC
                    """)
                    
                    return [dict(row) for row in cursor.fetchall()]
                except sqlite3.OperationalError:
                    # Table doesn't exist yet
                    return []
        except Exception as e:
            logger.error(f"Error getting all genres: {e}")
            return []
    
    def get_all_bookshelves(self) -> List[Dict[str, Any]]:
        """Get all bookshelves in the database.
        
        Returns:
            List of bookshelf dictionaries with id, name and book count
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if the bookshelves table exists (migration 0.5.0+)
                try:
                    cursor.execute("""
                        SELECT bs.bookshelf_id, bs.name, COUNT(bb.book_id) as book_count
                        FROM bookshelves bs
                        LEFT JOIN book_bookshelves bb ON bs.bookshelf_id = bb.bookshelf_id
                        GROUP BY bs.bookshelf_id
                        ORDER BY book_count DESC
                    """)
                    
                    return [dict(row) for row in cursor.fetchall()]
                except sqlite3.OperationalError:
                    # Table doesn't exist yet
                    return []
        except Exception as e:
            logger.error(f"Error getting all bookshelves: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics.
        
        Returns:
            Dictionary with various statistics
        """
        stats = {}
        
        # Add database version if migrations enabled
        stats['database_version'] = self.get_database_version()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total books
            cursor.execute("SELECT COUNT(*) FROM books")
            stats['total_books'] = cursor.fetchone()[0]
            
            # Total authors
            cursor.execute("SELECT COUNT(*) FROM authors")
            stats['total_authors'] = cursor.fetchone()[0]
            
            # Total subjects
            cursor.execute("SELECT COUNT(*) FROM subjects")
            stats['total_subjects'] = cursor.fetchone()[0]
            
            # Books by language
            cursor.execute("""
                SELECT language, COUNT(*) as count 
                FROM books 
                GROUP BY language 
                ORDER BY count DESC
            """)
            stats['languages'] = {row['language']: row['count'] for row in cursor.fetchall()}
            
            # Books with EPUB format
            cursor.execute("""
                SELECT COUNT(DISTINCT book_id) 
                FROM formats 
                WHERE format_type LIKE '%epub%'
            """)
            stats['books_with_epub'] = cursor.fetchone()[0]
            
            # Downloaded books
            cursor.execute("""
                SELECT COUNT(DISTINCT book_id) 
                FROM downloads 
                WHERE status = 'completed'
            """)
            stats['downloaded_books'] = cursor.fetchone()[0]
            
            # Most popular books
            cursor.execute("""
                SELECT book_id, title, download_count 
                FROM books 
                ORDER BY download_count DESC 
                LIMIT 10
            """)
            stats['most_popular'] = [dict(row) for row in cursor.fetchall()]
            
            # Enhanced stats if 0.5.0+ migration applied
            try:
                # Total genres
                cursor.execute("SELECT COUNT(*) FROM genres")
                stats['total_genres'] = cursor.fetchone()[0]
                
                # Total bookshelves
                cursor.execute("SELECT COUNT(*) FROM bookshelves")
                stats['total_bookshelves'] = cursor.fetchone()[0]
                
                # Top genres
                cursor.execute("""
                    SELECT g.name, COUNT(bg.book_id) as count
                    FROM genres g
                    JOIN book_genres bg ON g.genre_id = bg.genre_id
                    GROUP BY g.genre_id
                    ORDER BY count DESC
                    LIMIT 10
                """)
                stats['top_genres'] = {row['name']: row['count'] for row in cursor.fetchall()}
                
                # Top bookshelves
                cursor.execute("""
                    SELECT bs.name, COUNT(bb.book_id) as count
                    FROM bookshelves bs
                    JOIN book_bookshelves bb ON bs.bookshelf_id = bb.bookshelf_id
                    GROUP BY bs.bookshelf_id
                    ORDER BY count DESC
                    LIMIT 10
                """)
                stats['top_bookshelves'] = {row['name']: row['count'] for row in cursor.fetchall()}
                
                # Metadata version stats
                cursor.execute("""
                    SELECT metadata_version, COUNT(*) as count
                    FROM books
                    GROUP BY metadata_version
                """)
                stats['metadata_versions'] = {row['metadata_version']: row['count'] for row in cursor.fetchall()}
                
            except sqlite3.OperationalError:
                # Enhanced tables don't exist yet
                pass
            
            return stats