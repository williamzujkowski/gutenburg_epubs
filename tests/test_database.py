"""Tests for the database module."""

import json
import sqlite3
from pathlib import Path
import pytest

from gutenberg_downloader.database import BookDatabase


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database file path."""
    return tmp_path / "test.db"


@pytest.fixture
def book_db(temp_db_path):
    """Create a test database instance."""
    db = BookDatabase(temp_db_path)
    return db


@pytest.fixture
def sample_book():
    """Sample book data for testing."""
    return {
        "id": 1342,
        "title": "Pride and Prejudice",
        "authors": [
            {
                "name": "Austen, Jane",
                "birth_year": 1775,
                "death_year": 1817
            }
        ],
        "languages": ["en"],
        "download_count": 46283,
        "formats": {
            "application/epub+zip": "https://www.gutenberg.org/ebooks/1342.epub.images",
            "text/html": "https://www.gutenberg.org/ebooks/1342.html.images"
        },
        "subjects": ["England -- Fiction", "Love stories"]
    }


class TestBookDatabase:
    """Tests for the BookDatabase class."""

    def test_init(self, temp_db_path):
        """Test database initialization."""
        db = BookDatabase(temp_db_path)
        assert db.db_path == temp_db_path
        assert temp_db_path.exists()
        
        # Verify tables were created
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Check essential tables exist
        essential_tables = ['books', 'authors', 'formats', 'subjects', 'downloads']
        for table in essential_tables:
            assert table in tables
        
        conn.close()

    def test_add_book(self, book_db, sample_book):
        """Test adding a book to the database."""
        # Add the book
        book_db.add_book(sample_book)
        
        # Verify the book exists
        conn = sqlite3.connect(book_db.db_path)
        cursor = conn.cursor()
        
        # Check book added
        cursor.execute("SELECT id, title, download_count FROM books WHERE id = ?", (sample_book["id"],))
        book_row = cursor.fetchone()
        assert book_row is not None
        assert book_row[0] == sample_book["id"]
        assert book_row[1] == sample_book["title"]
        assert book_row[2] == sample_book["download_count"]
        
        # Check authors added
        cursor.execute("""
            SELECT a.name 
            FROM authors a 
            JOIN book_authors ba ON a.id = ba.author_id 
            WHERE ba.book_id = ?
        """, (sample_book["id"],))
        author_names = [row[0] for row in cursor.fetchall()]
        assert author_names == [author["name"] for author in sample_book["authors"]]
        
        # Check subjects added
        cursor.execute("""
            SELECT s.name 
            FROM subjects s 
            JOIN book_subjects bs ON s.id = bs.subject_id 
            WHERE bs.book_id = ?
        """, (sample_book["id"],))
        subject_names = [row[0] for row in cursor.fetchall()]
        assert set(subject_names) == set(sample_book["subjects"])
        
        # Check formats added
        cursor.execute("""
            SELECT format_type, url 
            FROM formats 
            WHERE book_id = ?
        """, (sample_book["id"],))
        formats = {row[0]: row[1] for row in cursor.fetchall()}
        assert formats == sample_book["formats"]
        
        conn.close()

    def test_get_book(self, book_db, sample_book):
        """Test retrieving a book from the database."""
        # Add the book
        book_db.add_book(sample_book)
        
        # Get the book
        book = book_db.get_book(sample_book["id"])
        
        # Verify book data
        assert book["id"] == sample_book["id"]
        assert book["title"] == sample_book["title"]
        assert book["download_count"] == sample_book["download_count"]
        
        # Check authors
        assert len(book["authors"]) == len(sample_book["authors"])
        assert book["authors"][0]["name"] == sample_book["authors"][0]["name"]
        
        # Check subjects
        assert set(book["subjects"]) == set(sample_book["subjects"])
        
        # Check formats
        assert book["formats"] == sample_book["formats"]

    def test_search_books(self, book_db, sample_book):
        """Test searching for books."""
        # Add sample book
        book_db.add_book(sample_book)
        
        # Search by title
        results = book_db.search_books(title="Pride")
        assert len(results) == 1
        assert results[0]["id"] == sample_book["id"]
        
        # Search by author
        results = book_db.search_books(author="Austen")
        assert len(results) == 1
        assert results[0]["id"] == sample_book["id"]
        
        # Search by subject
        results = book_db.search_books(subject="Love")
        assert len(results) == 1
        assert results[0]["id"] == sample_book["id"]
        
        # Search with no matches
        results = book_db.search_books(title="Nonexistent")
        assert len(results) == 0

    def test_add_download(self, book_db, sample_book, temp_db_path):
        """Test adding a download record."""
        # Add the book
        book_db.add_book(sample_book)
        
        # Add download record
        download_path = "/path/to/download/pride_and_prejudice.epub"
        book_db.add_download(
            book_id=sample_book["id"],
            format_type="application/epub+zip",
            file_path=download_path,
            size=1024,
            timestamp="2024-05-19T12:00:00"
        )
        
        # Verify download was added
        conn = sqlite3.connect(book_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT book_id, format_type, file_path, size, timestamp
            FROM downloads
            WHERE book_id = ?
        """, (sample_book["id"],))
        
        download = cursor.fetchone()
        assert download is not None
        assert download[0] == sample_book["id"]
        assert download[1] == "application/epub+zip"
        assert download[2] == download_path
        assert download[3] == 1024
        assert download[4] == "2024-05-19T12:00:00"
        
        conn.close()

    def test_get_book_download(self, book_db, sample_book):
        """Test getting download information for a book."""
        # Add the book
        book_db.add_book(sample_book)
        
        # Add download record
        download_path = "/path/to/download/pride_and_prejudice.epub"
        book_db.add_download(
            book_id=sample_book["id"],
            format_type="application/epub+zip",
            file_path=download_path,
            size=1024,
            timestamp="2024-05-19T12:00:00"
        )
        
        # Get download info
        download = book_db.get_book_download(sample_book["id"], "application/epub+zip")
        
        assert download is not None
        assert download["book_id"] == sample_book["id"]
        assert download["format_type"] == "application/epub+zip"
        assert download["file_path"] == download_path
        assert download["size"] == 1024
        assert download["timestamp"] == "2024-05-19T12:00:00"

    def test_get_all_books(self, book_db, sample_book):
        """Test getting all books."""
        # Add a book
        book_db.add_book(sample_book)
        
        # Add another book
        book2 = dict(sample_book)
        book2["id"] = 84
        book2["title"] = "Frankenstein"
        book2["authors"] = [{"name": "Shelley, Mary", "birth_year": 1797, "death_year": 1851}]
        book_db.add_book(book2)
        
        # Get all books
        books = book_db.get_all_books()
        
        assert len(books) == 2
        book_ids = [book["id"] for book in books]
        assert set(book_ids) == {sample_book["id"], book2["id"]}

    def test_get_book_count(self, book_db, sample_book):
        """Test getting book count."""
        # Initially empty
        assert book_db.get_book_count() == 0
        
        # Add books
        book_db.add_book(sample_book)
        assert book_db.get_book_count() == 1
        
        book2 = dict(sample_book)
        book2["id"] = 84
        book_db.add_book(book2)
        assert book_db.get_book_count() == 2

    def test_get_popular_books(self, book_db, sample_book):
        """Test getting popular books."""
        # Add a book with high download count
        book_db.add_book(sample_book)
        
        # Add a book with low download count
        book2 = dict(sample_book)
        book2["id"] = 84
        book2["title"] = "Frankenstein"
        book2["download_count"] = 100
        book_db.add_book(book2)
        
        # Get popular books (limit 1)
        popular = book_db.get_popular_books(1)
        
        assert len(popular) == 1
        assert popular[0]["id"] == sample_book["id"]
        assert popular[0]["download_count"] == sample_book["download_count"]