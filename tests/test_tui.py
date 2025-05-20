"""Tests for the Terminal User Interface."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

# We need to ensure the package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.gutenberg_downloader.tui import GutenbergBrowserApp, run_tui, HelpScreen, SearchScreen, ExportScreen


class TestTUI(unittest.TestCase):
    """Test the TUI functionality."""
    
    @pytest.mark.tui
    @patch('src.gutenberg_downloader.tui.GutenbergBrowserApp')
    def test_run_tui(self, mock_app):
        """Test the run_tui function."""
        # Call the function
        run_tui(db_path="test.db", mirrors_enabled=True, output_dir="test_output", max_workers=2)
        
        # Check that the app was instantiated correctly
        mock_app.assert_called_once_with(
            db_path="test.db",
            mirrors_enabled=True,
            output_dir="test_output",
            max_workers=2
        )
        
        # Check that the app was run
        mock_app.return_value.run.assert_called_once()
    
    @pytest.mark.tui
    @patch('src.gutenberg_downloader.tui.BookDatabase')
    @patch('src.gutenberg_downloader.tui.DownloadQueue')
    @patch('src.gutenberg_downloader.tui.BookExporter')
    @patch('src.gutenberg_downloader.tui.MirrorManager')
    @patch('src.gutenberg_downloader.tui.SmartDownloader')
    def test_gutenberg_browser_app_init(self, mock_downloader, mock_mirror_manager, 
                                      mock_exporter, mock_queue, mock_db):
        """Test GutenbergBrowserApp initialization."""
        # Create a mock for Path.mkdir
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            # Instantiate app
            app = GutenbergBrowserApp(
                db_path="test.db",
                mirrors_enabled=True,
                output_dir="test_output",
                max_workers=2
            )
            
            # Check that directories were created
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
            
            # Check that database was initialized
            mock_db.assert_called_once_with("test.db")
            
            # Check that queue was initialized
            mock_queue.assert_called_once_with("test.db", max_workers=2)
            
            # Check that exporter was initialized
            mock_exporter.assert_called_once_with("test.db")
            
            # Check that mirror manager was initialized
            mock_mirror_manager.assert_called_once()
            
            # Check that downloader was initialized
            mock_downloader.assert_called_once_with("test.db", mirrors_enabled=True)
    
    @pytest.mark.tui
    @pytest.mark.skip("API changes in Textual v3 need updated tests")
    @patch('src.gutenberg_downloader.tui.BookDatabase')
    def test_search_screen(self, mock_db):
        """Test SearchScreen functionality."""
        with patch('textual.app.App.run'):
            # Create mock app
            mock_app = MagicMock()
            
            # Create screen
            screen = SearchScreen()
            screen.app = mock_app
            
            # Test different search actions
            
            # Mock input value
            mock_input = MagicMock()
            mock_input.value = "test query"
            
            # Mock query_one to return input
            screen.query_one = MagicMock(return_value=mock_input)
            
            # Test full-text search
            screen.search_full_text()
            self.assertEqual(mock_app.search_type, "full_text")
            self.assertEqual(mock_app.search_query, "test query")
            mock_app.pop_screen.assert_called_once()
            mock_app.pop_screen.reset_mock()
            
            # Test title search
            screen.search_by_title()
            self.assertEqual(mock_app.search_type, "title")
            self.assertEqual(mock_app.search_query, "test query")
            mock_app.pop_screen.assert_called_once()
            mock_app.pop_screen.reset_mock()
            
            # Test author search
            screen.search_by_author()
            self.assertEqual(mock_app.search_type, "author")
            self.assertEqual(mock_app.search_query, "test query")
            mock_app.pop_screen.assert_called_once()
            mock_app.pop_screen.reset_mock()
            
            # Test cancel
            screen.cancel_search()
            mock_app.pop_screen.assert_called_once()
    
    @pytest.mark.tui
    @pytest.mark.skip("API changes in Textual v3 need updated tests")
    @patch('src.gutenberg_downloader.tui.BookDatabase')
    def test_export_screen(self, mock_db):
        """Test ExportScreen functionality."""
        with patch('textual.app.App.run'):
            # Create mock app
            mock_app = MagicMock()
            
            # Create screen
            screen = ExportScreen()
            screen.app = mock_app
            
            # Mock input value
            mock_input = MagicMock()
            mock_input.value = "test_export"
            
            # Mock query_one to return input
            screen.query_one = MagicMock(return_value=mock_input)
            
            # Test CSV export
            screen.export_csv()
            self.assertEqual(mock_app.export_format, "csv")
            self.assertEqual(mock_app.export_filename, "test_export.csv")
            mock_app.pop_screen.assert_called_once()
            mock_app.pop_screen.reset_mock()
            
            # Test JSON export
            screen.export_json()
            self.assertEqual(mock_app.export_format, "json")
            self.assertEqual(mock_app.export_filename, "test_export.json")
            mock_app.pop_screen.assert_called_once()
            mock_app.pop_screen.reset_mock()
            
            # Test cancel
            screen.cancel_export()
            mock_app.pop_screen.assert_called_once()
    
    @pytest.mark.tui
    @pytest.mark.skip("API changes in Textual v3 need updated tests")
    @patch('src.gutenberg_downloader.tui.BookDatabase')
    @patch('src.gutenberg_downloader.tui.DownloadQueue')
    @patch('src.gutenberg_downloader.tui.BookExporter')
    @patch('src.gutenberg_downloader.tui.SmartDownloader')
    def test_app_update_download_status(self, mock_downloader, mock_exporter, 
                                     mock_queue, mock_db):
        """Test download status update functionality."""
        with patch('textual.app.App.run'):
            with patch('pathlib.Path.mkdir'):
                # Create app
                app = GutenbergBrowserApp(db_path="test.db")
                
                # Mock queue status
                mock_queue_instance = mock_queue.return_value
                mock_queue_instance.get_status.return_value = {
                    'active_tasks': [
                        {'book_id': 1, 'status': 'downloading'}
                    ],
                    'stats': {
                        'queued': 2,
                        'downloading': 1,
                        'completed': 3
                    }
                }
                
                # Mock database get_book
                mock_db_instance = mock_db.return_value
                mock_db_instance.get_book.return_value = {
                    'book_id': 1,
                    'title': 'Test Book'
                }
                
                # Mock downloader get_download_state
                mock_downloader_instance = mock_downloader.return_value
                mock_downloader_instance.get_download_state.return_value = {
                    'status': 'completed',
                    'bytes_downloaded': 1024,
                    'total_bytes': 2048
                }
                
                # Mock containers
                app.query_one = MagicMock()
                mock_container = MagicMock()
                app.query_one.return_value = mock_container
                
                # Mock active_downloads
                app.active_downloads = {1: {
                    'book_id': 1,
                    'title': 'Test Book',
                    'status': 'downloading'
                }}
                
                # Call update
                app.update_download_status()
                
                # Verify download state was queried
                mock_downloader_instance.get_download_state.assert_called_with(1)
                
                # Verify book was removed from active and added to completed
                self.assertEqual(len(app.active_downloads), 0)
                self.assertEqual(len(app.completed_downloads), 1)
                self.assertEqual(app.completed_downloads[0]['book_id'], 1)
                self.assertEqual(app.completed_downloads[0]['status'], 'completed')


if __name__ == '__main__':
    unittest.main()