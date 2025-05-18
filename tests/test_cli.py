"""Tests for the CLI module."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from gutenberg_downloader.cli import (
    create_parser,
    discover_command,
    download_command,
    download_popular_command,
    main,
    search_command,
    stats_command,
)


class TestCreateParser:
    """Tests for the create_parser function."""

    def test_parser_creation(self):
        """Test that parser is created with expected commands."""
        parser = create_parser()
        assert parser.prog == "gutenberg-downloader"

    def test_version_argument(self):
        """Test version argument."""
        parser = create_parser()
        with patch("sys.stdout"):
            with pytest.raises(SystemExit) as exc_info:
                parser.parse_args(["--version"])
            assert exc_info.value.code == 0

    def test_verbose_and_quiet_arguments(self):
        """Test verbose and quiet arguments."""
        parser = create_parser()
        args = parser.parse_args(["--verbose", "discover"])
        assert args.verbose is True

        args = parser.parse_args(["--quiet", "discover"])
        assert args.quiet is True

    def test_discover_command_arguments(self):
        """Test discover command arguments."""
        parser = create_parser()
        args = parser.parse_args(["discover", "--limit", "20", "--format", "detailed"])
        assert args.command == "discover"
        assert args.limit == 20
        assert args.format == "detailed"

    def test_download_command_arguments(self):
        """Test download command arguments."""
        parser = create_parser()
        args = parser.parse_args(
            ["download", "123", "--output", "/tmp", "--filename", "test.epub"]
        )
        assert args.command == "download"
        assert args.book_id == 123
        assert args.output == Path("/tmp")
        assert args.filename == "test.epub"

    def test_search_command_arguments(self):
        """Test search command arguments."""
        parser = create_parser()
        args = parser.parse_args(
            ["search", "--title", "Pride", "--limit", "5", "--exact"]
        )
        assert args.command == "search"
        assert args.title == "Pride"
        assert args.limit == 5
        assert args.exact is True

        args = parser.parse_args(["search", "--author", "Austen"])
        assert args.command == "search"
        assert args.author == "Austen"

    def test_stats_command(self):
        """Test stats command."""
        parser = create_parser()
        args = parser.parse_args(["stats"])
        assert args.command == "stats"

    def test_download_popular_command_arguments(self):
        """Test download-popular command arguments."""
        parser = create_parser()
        args = parser.parse_args(
            ["download-popular", "--limit", "3", "--output", "/books", "--skip-existing"]
        )
        assert args.command == "download-popular"
        assert args.limit == 3
        assert args.output == Path("/books")
        assert args.skip_existing is True


class TestDiscoverCommand:
    """Tests for the discover_command function."""

    def test_discover_simple_format(self, capsys):
        """Test discover command with simple format."""
        args = Mock()
        args.limit = 2
        args.format = "simple"

        mock_books = [
            {
                "book_id": 123,
                "metadata": {"title": "Test Book 1", "author": "Author 1"},
                "popularity_rank": 1,
            },
            {
                "book_id": 456,
                "metadata": {"title": "Test Book 2", "author": "Author 2"},
                "popularity_rank": 2,
            },
        ]

        with patch("gutenberg_downloader.cli.BookDiscovery") as MockDiscovery:
            mock_discovery = MockDiscovery.return_value.__enter__.return_value
            mock_discovery.discover_popular_english_epubs.return_value = mock_books

            result = discover_command(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "Found 2 popular English books" in captured.out
            assert "123: Test Book 1 by Author 1" in captured.out
            assert "456: Test Book 2 by Author 2" in captured.out

    def test_discover_detailed_format(self, capsys):
        """Test discover command with detailed format."""
        args = Mock()
        args.limit = 1
        args.format = "detailed"

        mock_books = [
            {
                "book_id": 123,
                "metadata": {
                    "title": "Test Book",
                    "author": "Test Author",
                    "language": "English",
                },
                "download_links": {"epub": "http://example.com/book.epub"},
                "popularity_rank": 1,
            }
        ]

        with patch("gutenberg_downloader.cli.BookDiscovery") as MockDiscovery:
            mock_discovery = MockDiscovery.return_value.__enter__.return_value
            mock_discovery.discover_popular_english_epubs.return_value = mock_books

            result = discover_command(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "--- Book 1 ---" in captured.out
            assert "ID: 123" in captured.out
            assert "Title: Test Book" in captured.out
            assert "Author: Test Author" in captured.out
            assert "Language: English" in captured.out

    def test_discover_no_books(self, capsys):
        """Test discover command when no books are found."""
        _ = capsys  # Needed for pytest fixture
        args = Mock()
        args.limit = 10
        args.format = "simple"

        with patch("gutenberg_downloader.cli.BookDiscovery") as MockDiscovery:
            mock_discovery = MockDiscovery.return_value.__enter__.return_value
            mock_discovery.discover_popular_english_epubs.return_value = []

            with patch("gutenberg_downloader.cli.logger") as mock_logger:
                result = discover_command(args)

                assert result == 0
                mock_logger.info.assert_called_with(
                    "No English books with EPUB files found."
                )

    def test_discover_error(self):
        """Test discover command error handling."""
        args = Mock()
        args.limit = 10
        args.format = "simple"

        with patch("gutenberg_downloader.cli.BookDiscovery") as MockDiscovery:
            MockDiscovery.side_effect = Exception("Discovery error")

            with patch("gutenberg_downloader.cli.logger") as mock_logger:
                result = discover_command(args)

                assert result == 1
                mock_logger.error.assert_called_with("Error discovering books: Discovery error")


class TestDownloadCommand:
    """Tests for the download_command function."""

    def test_download_success(self, tmp_path):
        """Test successful download."""
        args = Mock()
        args.book_id = 123
        args.output = tmp_path
        args.filename = None

        mock_book_details = {
            "book_id": 123,
            "metadata": {"title": "Test Book"},
            "download_links": {"epub": "http://example.com/book.epub"},
        }

        with patch("gutenberg_downloader.cli.BookDiscovery") as MockDiscovery:
            mock_discovery = MockDiscovery.return_value.__enter__.return_value
            mock_discovery.get_book_details.return_value = mock_book_details
            mock_discovery.download_book_epub.return_value = True

            with patch("gutenberg_downloader.cli.logger") as mock_logger:
                result = download_command(args)

                assert result == 0
                mock_discovery.download_book_epub.assert_called_once()
                mock_logger.info.assert_any_call(
                    f"Successfully downloaded to {tmp_path / 'Test_Book.epub'}"
                )

    def test_download_custom_filename(self, tmp_path):
        """Test download with custom filename."""
        args = Mock()
        args.book_id = 123
        args.output = tmp_path
        args.filename = "custom_name.epub"

        mock_book_details = {
            "book_id": 123,
            "metadata": {"title": "Test Book"},
        }

        with patch("gutenberg_downloader.cli.BookDiscovery") as MockDiscovery:
            mock_discovery = MockDiscovery.return_value.__enter__.return_value
            mock_discovery.get_book_details.return_value = mock_book_details
            mock_discovery.download_book_epub.return_value = True

            result = download_command(args)

            assert result == 0
            expected_path = tmp_path / "custom_name.epub"
            mock_discovery.download_book_epub.assert_called_with(
                123, expected_path, book_details=mock_book_details
            )

    def test_download_book_not_found(self):
        """Test download when book is not found."""
        args = Mock()
        args.book_id = 999
        args.output = Path("/tmp")
        args.filename = None

        with patch("gutenberg_downloader.cli.BookDiscovery") as MockDiscovery:
            mock_discovery = MockDiscovery.return_value.__enter__.return_value
            mock_discovery.get_book_details.return_value = None

            with patch("gutenberg_downloader.cli.logger") as mock_logger:
                result = download_command(args)

                assert result == 1
                mock_logger.error.assert_called_with(
                    "Could not fetch details for book ID 999"
                )

    def test_download_failure(self):
        """Test download failure."""
        args = Mock()
        args.book_id = 123
        args.output = Path("/tmp")
        args.filename = None

        mock_book_details = {"metadata": {"title": "Test Book"}}

        with patch("gutenberg_downloader.cli.BookDiscovery") as MockDiscovery:
            mock_discovery = MockDiscovery.return_value.__enter__.return_value
            mock_discovery.get_book_details.return_value = mock_book_details
            mock_discovery.download_book_epub.return_value = False

            with patch("gutenberg_downloader.cli.logger") as mock_logger:
                result = download_command(args)

                assert result == 1
                mock_logger.error.assert_called_with("Failed to download book 123")


class TestSearchCommand:
    """Tests for the search_command function."""

    def test_search_by_title(self, capsys):
        """Test search by title."""
        args = Mock()
        args.title = "Pride"
        args.author = None
        args.limit = 5
        args.exact = False

        mock_results = [
            {
                "book_id": 123,
                "metadata": {"title": "Pride and Prejudice", "author": "Jane Austen"},
                "download_links": {"epub": "url"},
            },
            {
                "book_id": 456,
                "metadata": {"title": "Pride of Lions", "author": "Terry Brooks"},
                "download_links": {"txt": "url"},
            },
        ]

        with patch("gutenberg_downloader.cli.BookDiscovery") as MockDiscovery:
            mock_discovery = MockDiscovery.return_value.__enter__.return_value
            mock_discovery.search_by_title.return_value = mock_results

            result = search_command(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "Found 2 matching books" in captured.out
            assert "Pride and Prejudice" in captured.out
            assert "[EPUB available]" in captured.out
            assert "[No EPUB]" in captured.out

    def test_search_by_author(self, capsys):
        """Test search by author."""
        args = Mock()
        args.title = None
        args.author = "Austen"
        args.limit = 10

        mock_results = [
            {
                "book_id": 123,
                "metadata": {"title": "Pride and Prejudice", "author": "Jane Austen"},
                "download_links": {"epub": "url"},
            }
        ]

        with patch("gutenberg_downloader.cli.BookDiscovery") as MockDiscovery:
            mock_discovery = MockDiscovery.return_value.__enter__.return_value
            mock_discovery.search_by_author.return_value = mock_results

            result = search_command(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "Found 1 matching books" in captured.out
            assert "Jane Austen" in captured.out

    def test_search_no_results(self):
        """Test search with no results."""
        args = Mock()
        args.title = "NonexistentBook"
        args.author = None
        args.limit = 5
        args.exact = True

        with patch("gutenberg_downloader.cli.BookDiscovery") as MockDiscovery:
            mock_discovery = MockDiscovery.return_value.__enter__.return_value
            mock_discovery.search_by_title.return_value = []

            with patch("gutenberg_downloader.cli.logger") as mock_logger:
                result = search_command(args)

                assert result == 0
                mock_logger.info.assert_any_call("No matching books found.")


class TestStatsCommand:
    """Tests for the stats_command function."""

    def test_stats_success(self, capsys):
        """Test stats command success."""
        args = Mock()

        mock_stats = {
            "total_books_sampled": 1000,
            "english_books": 800,
            "books_with_epub": 600,
            "english_books_with_epub": 500,
        }

        with patch("gutenberg_downloader.cli.BookDiscovery") as MockDiscovery:
            mock_discovery = MockDiscovery.return_value.__enter__.return_value
            mock_discovery.get_catalog_stats.return_value = mock_stats

            result = stats_command(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "Project Gutenberg Catalog Statistics" in captured.out
            assert "Total books sampled: 1000" in captured.out
            assert "English books: 800" in captured.out
            assert "English books: 80.0%" in captured.out

    def test_stats_error(self):
        """Test stats command error handling."""
        args = Mock()

        with patch("gutenberg_downloader.cli.BookDiscovery") as MockDiscovery:
            MockDiscovery.side_effect = Exception("Stats error")

            with patch("gutenberg_downloader.cli.logger") as mock_logger:
                result = stats_command(args)

                assert result == 1
                mock_logger.error.assert_called_with("Error gathering statistics: Stats error")


class TestDownloadPopularCommand:
    """Tests for the download_popular_command function."""

    def test_download_popular_success(self, tmp_path, capsys):
        """Test successful popular downloads."""
        args = Mock()
        args.limit = 2
        args.output = tmp_path
        args.skip_existing = False

        mock_books = [
            {
                "book_id": 123,
                "metadata": {"title": "Test Book 1"},
                "download_links": {"epub": "url1"},
            },
            {
                "book_id": 456,
                "metadata": {"title": "Test Book 2"},
                "download_links": {"epub": "url2"},
            },
        ]

        with patch("gutenberg_downloader.cli.BookDiscovery") as MockDiscovery:
            mock_discovery = MockDiscovery.return_value.__enter__.return_value
            mock_discovery.discover_popular_english_epubs.return_value = mock_books
            mock_discovery.download_book_epub.return_value = True

            result = download_popular_command(args)

            assert result == 0
            assert mock_discovery.download_book_epub.call_count == 2
            captured = capsys.readouterr()
            assert "Downloaded: 2" in captured.out

    def test_download_popular_skip_existing(self, tmp_path, capsys):
        """Test skipping existing files."""
        args = Mock()
        args.limit = 2
        args.output = tmp_path
        args.skip_existing = True

        # Create an existing file
        existing_file = tmp_path / "Test_Book_1.epub"
        existing_file.touch()

        mock_books = [
            {
                "book_id": 123,
                "metadata": {"title": "Test Book 1"},
            },
            {
                "book_id": 456,
                "metadata": {"title": "Test Book 2"},
            },
        ]

        with patch("gutenberg_downloader.cli.BookDiscovery") as MockDiscovery:
            mock_discovery = MockDiscovery.return_value.__enter__.return_value
            mock_discovery.discover_popular_english_epubs.return_value = mock_books
            mock_discovery.download_book_epub.return_value = True

            result = download_popular_command(args)

            assert result == 0
            assert mock_discovery.download_book_epub.call_count == 1
            captured = capsys.readouterr()
            assert "Skipped: 1" in captured.out


class TestMain:
    """Tests for the main function."""

    def test_main_with_discover(self):
        """Test main function with discover command."""
        test_args = ["discover", "--limit", "5"]

        with patch("gutenberg_downloader.cli.discover_command") as mock_discover:
            mock_discover.return_value = 0

            result = main(test_args)

            assert result == 0
            mock_discover.assert_called_once()

    def test_main_with_verbose(self):
        """Test main function with verbose flag."""
        test_args = ["--verbose", "stats"]

        with patch("gutenberg_downloader.cli.stats_command") as mock_stats:
            mock_stats.return_value = 0

            with patch("gutenberg_downloader.cli.setup_logger") as mock_setup_logger:
                result = main(test_args)

                assert result == 0
                import logging

                mock_setup_logger.assert_called_with(level=logging.DEBUG)

    def test_main_with_quiet(self):
        """Test main function with quiet flag."""
        test_args = ["--quiet", "discover"]

        with patch("gutenberg_downloader.cli.discover_command") as mock_discover:
            mock_discover.return_value = 0

            with patch("gutenberg_downloader.cli.setup_logger") as mock_setup_logger:
                result = main(test_args)

                assert result == 0
                import logging

                mock_setup_logger.assert_called_with(level=logging.ERROR)

    def test_main_script_entry(self):
        """Test script entry point."""
        # Test that main function can be called directly
        with patch("gutenberg_downloader.cli.discover_command") as mock_discover:
            mock_discover.return_value = 0

            # Test command-line invocation
            result = main(["discover", "--limit", "5"])
            assert result == 0
            mock_discover.assert_called_once()
