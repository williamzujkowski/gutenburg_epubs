"""Terminal User Interface for browsing and downloading books."""

import json
import os
import asyncio
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TaskProgressColumn
from rich.spinner import Spinner
from rich.table import Table
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll, ScrollableContainer
from textual.screen import Screen, ModalScreen
from textual.timer import Timer
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label, Static, 
    LoadingIndicator, ProgressBar, Tabs, Tab, TabPane, RadioButton,
    RadioSet, Select, Switch
)
from textual.worker import Worker, get_current_worker

from .database import BookDatabase
from .download_queue import DownloadQueue, Priority, Status as QueueStatus
from .exporter import BookExporter, ExportFormat
from .mirror_manager import MirrorManager, MirrorSite
from .smart_downloader import SmartDownloader

class HelpScreen(Screen):
    """Help screen with keyboard shortcuts and usage information."""
    
    BINDINGS = [("escape", "dismiss", "Back")]
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("# Project Gutenberg EPUB Downloader Help", classes="title"),
            Static("## Keyboard Shortcuts", classes="section"),
            Static("""
            - **q**: Quit application
            - **s**: Search for books
            - **d**: Download selected books
            - **e**: Export current view
            - **r**: Refresh book list
            - **?**: Show this help
            - **Tab**: Switch between tabs
            """, classes="content"),
            Static("## Features", classes="section"),
            Static("""
            - **Browse Books**: Discover popular books by downloads, language, or subject
            - **Search**: Find books by title, author, or content
            - **Download**: Add books to download queue for automatic processing
            - **Mirror Management**: View and control mirror sites for faster downloads
            - **Export**: Save book listings in various formats
            """, classes="content"),
            Static("## Getting Started", classes="section"),
            Static("""
            1. Use the Browse tab to explore books
            2. Click on rows to select books you want to download
            3. Press 'd' or click the Download button to add books to queue
            4. Switch to the Downloads tab to monitor progress
            5. Use the Mirrors tab to view mirror health and status
            """, classes="content"),
            Button("Close", id="close_help"),
            classes="help_container",
        )
        yield Footer()
    
    @on(Button.Pressed, "#close_help")
    def close_help(self) -> None:
        self.dismiss()

class SearchScreen(Screen):
    """Search screen for finding books."""
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("Search for books:"),
            Input(placeholder="Enter search query...", id="search_input"),
            Horizontal(
                Button("Full-text Search", id="search_full"),
                Button("Search by Title", id="search_title"),
                Button("Search by Author", id="search_author"),
                Button("Cancel", id="cancel"),
                id="search_buttons"
            ),
            id="search_container"
        )
        yield Footer()
    
    @on(Button.Pressed, "#search_full")
    def search_full_text(self) -> None:
        query = self.query_one("#search_input", Input).value
        if query:
            self.app.search_type = "full_text"  # type: ignore
            self.app.search_query = query  # type: ignore
            self.dismiss()
    
    @on(Button.Pressed, "#search_title")
    def search_by_title(self) -> None:
        query = self.query_one("#search_input", Input).value
        if query:
            self.app.search_type = "title"  # type: ignore
            self.app.search_query = query  # type: ignore
            self.dismiss()
    
    @on(Button.Pressed, "#search_author")
    def search_by_author(self) -> None:
        query = self.query_one("#search_input", Input).value
        if query:
            self.app.search_type = "author"  # type: ignore
            self.app.search_query = query  # type: ignore
            self.dismiss()
    
    @on(Button.Pressed, "#cancel")
    def cancel_search(self) -> None:
        self.dismiss()

class ExportScreen(Screen):
    """Export screen for saving book data."""
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("Export books to file:"),
            Input(placeholder="Enter filename...", id="filename_input"),
            Label("Select format:"),
            Horizontal(
                Button("CSV", id="export_csv"),
                Button("JSON", id="export_json"),
                Button("Excel", id="export_excel"),
                Button("Markdown", id="export_markdown"),
                Button("Cancel", id="cancel"),
                id="export_buttons"
            ),
            id="export_container"
        )
        yield Footer()
    
    def export_books(self, format: str) -> None:
        filename = self.query_one("#filename_input", Input).value
        if filename:
            if not filename.endswith(f".{format}"):
                filename += f".{format}"
            
            self.app.export_format = format  # type: ignore
            self.app.export_filename = filename  # type: ignore
            self.dismiss()
    
    @on(Button.Pressed, "#export_csv")
    def export_csv(self) -> None:
        self.export_books("csv")
    
    @on(Button.Pressed, "#export_json")
    def export_json(self) -> None:
        self.export_books("json")
    
    @on(Button.Pressed, "#export_excel")
    def export_excel(self) -> None:
        self.export_books("excel")
    
    @on(Button.Pressed, "#export_markdown")
    def export_markdown(self) -> None:
        self.export_books("markdown")
    
    @on(Button.Pressed, "#cancel")
    def cancel_export(self) -> None:
        self.dismiss()

class MirrorDetailsScreen(ModalScreen):
    """Modal screen showing detailed mirror information."""
    
    BINDINGS = [("escape", "dismiss", "Back")]
    
    def __init__(self, mirror: MirrorSite):
        super().__init__()
        self.mirror = mirror
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"# Mirror: {self.mirror.name}", classes="title"),
            Static(f"URL: {self.mirror.base_url}", classes="mirror-url"),
            Static(f"Priority: {self.mirror.priority}", classes="mirror-info"),
            Static(f"Country: {self.mirror.country or 'Unknown'}", classes="mirror-info"),
            Static(f"Active: {'Yes' if self.mirror.active else 'No'}", classes="mirror-info"),
            Static(f"Health Score: {self.mirror.health_score:.2f}", classes="mirror-info"),
            Static(f"Last Checked: {datetime.fromtimestamp(self.mirror.last_checked).strftime('%Y-%m-%d %H:%M:%S') if self.mirror.last_checked else 'Never'}", classes="mirror-info"),
            Static(f"Last Success: {datetime.fromtimestamp(self.mirror.last_success).strftime('%Y-%m-%d %H:%M:%S') if self.mirror.last_success else 'Never'}", classes="mirror-info"),
            Horizontal(
                Button("Test Mirror", id="test_mirror"),
                Button("Toggle Active", id="toggle_active"),
                Button("Close", id="close_button"),
                id="mirror_buttons"
            ),
            id="mirror_details",
        )
    
    @on(Button.Pressed, "#close_button")
    def close_modal(self) -> None:
        self.dismiss()
    
    @on(Button.Pressed, "#test_mirror")
    def test_mirror(self) -> None:
        self.app.test_mirror(self.mirror)  # type: ignore
    
    @on(Button.Pressed, "#toggle_active")
    def toggle_active(self) -> None:
        self.mirror.active = not self.mirror.active
        self.app.save_mirror_state()  # type: ignore
        self.dismiss()

class GutenbergBrowserApp(App):
    """TUI application for browsing and downloading books from Project Gutenberg."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    .title {
        text-align: center;
        padding: 1;
        color: $accent;
        text-style: bold;
    }
    
    .section {
        color: $accent;
        text-style: bold;
        margin-top: 1;
    }
    
    .content {
        margin-left: 2;
        margin-bottom: 1;
    }
    
    #search_container, #export_container {
        align: center middle;
        background: $surface;
        border: tall $primary;
        padding: 2;
        margin: 2;
        height: auto;
    }
    
    #search_buttons, #export_buttons {
        margin-top: 1;
    }
    
    Button {
        margin: 0 1;
    }
    
    DataTable {
        height: 100%;
        width: 100%;
    }
    
    #status_bar {
        dock: bottom;
        height: 3;
        background: $panel;
        border-top: solid $primary;
        padding: 1;
    }
    
    #control_panel {
        height: 5;
        background: $panel;
        border-bottom: solid $primary;
        padding: 1;
    }
    
    #main_tabs {
        height: 95%;
    }
    
    #downloads_container {
        padding: 1;
        height: 100%;
    }
    
    .download-item {
        height: 5;
        margin-bottom: 1;
        padding: 1;
        border: solid $primary;
    }
    
    .download-progress {
        width: 100%;
    }
    
    .mirror-header {
        text-align: center;
        padding: 1;
        color: $accent;
        text-style: bold;
        background: $panel;
        border-bottom: solid $primary;
    }
    
    .mirror-item {
        height: 5;
        margin-bottom: 1;
        padding: 1;
        border: solid $primary;
    }
    
    .mirror-status-active {
        color: $success;
    }
    
    .mirror-status-inactive {
        color: $error;
    }
    
    .mirror-health-good {
        color: $success;
    }
    
    .mirror-health-medium {
        color: $warning;
    }
    
    .mirror-health-poor {
        color: $error;
    }
    
    #mirror_details {
        align: center middle;
        background: $surface;
        border: tall $primary;
        padding: 2;
        margin: 2;
        height: auto;
        width: 60;
    }
    
    .mirror-url {
        color: $text;
        margin-bottom: 1;
    }
    
    .mirror-info {
        margin-top: 1;
    }
    
    #mirror_buttons {
        margin-top: 2;
    }
    
    .help_container {
        padding: 2;
        margin: 2;
        height: auto;
        width: 100%;
    }
    
    .info-text {
        text-align: center;
        margin: 2 0;
    }
    
    #download_queue_table {
        width: 100%;
        height: 80%;
    }
    
    #active_downloads_container {
        height: 50%;
        border-bottom: solid $primary;
    }
    
    #pending_downloads_container {
        height: 50%;
    }
    
    .download-status-completed {
        color: $success;
    }
    
    .download-status-downloading {
        color: $accent;
    }
    
    .download-status-pending {
        color: $text;
    }
    
    .download-status-failed {
        color: $error;
    }

    .settings-group {
        margin: 1 0;
        border: solid $primary;
        padding: 1;
    }

    .settings-label {
        width: 30%;
    }

    .settings-control {
        width: 70%;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "search", "Search"),
        ("d", "download", "Download"),
        ("e", "export", "Export"),
        ("r", "refresh", "Refresh"),
        ("?", "help", "Help"),
        ("tab", "next_tab", "Next Tab"),
        ("shift+tab", "prev_tab", "Prev Tab"),
    ]
    
    def __init__(
        self, 
        db_path: str = "gutenberg_books.db",
        mirrors_enabled: bool = True,
        output_dir: str = "downloads",
        max_workers: int = 3
    ):
        super().__init__()
        self.db_path = db_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mirrors_enabled = mirrors_enabled
        self.max_workers = max_workers
        
        # Initialize components
        self.db = BookDatabase(db_path)
        self.queue = DownloadQueue(db_path, max_workers=max_workers)
        self.exporter = BookExporter(db_path)
        self.mirror_manager = MirrorManager() if mirrors_enabled else None
        self.downloader = SmartDownloader(db_path, mirrors_enabled=mirrors_enabled)
        
        # Book listing state
        self.current_books: List[Dict[str, Any]] = []
        self.selected_book_ids: Set[int] = set()
        
        # Search state
        self.search_type: Optional[str] = None
        self.search_query: Optional[str] = None
        
        # Export state
        self.export_format: Optional[str] = None
        self.export_filename: Optional[str] = None
        
        # Download tracking
        self.active_downloads: Dict[int, Dict[str, Any]] = {}
        self.download_progresses: Dict[int, Tuple[int, int]] = {}  # (bytes_downloaded, total_bytes)
        self.pending_downloads: List[Dict[str, Any]] = []
        self.completed_downloads: List[Dict[str, Any]] = []
        
        # Update timers
        self.update_timer: Optional[Timer] = None
        self.mirror_check_timer: Optional[Timer] = None
    
    def compose(self) -> ComposeResult:
        """Compose the app interface."""
        yield Header()
        
        # Main tabs container
        with Tabs(id="main_tabs") as tabs:
            # Browse tab
            with TabPane("Browse", id="browse_tab"):
                yield Container(
                    Horizontal(
                        Button("Search", id="search_btn"),
                        Button("Download Selected", id="download_btn"),
                        Button("Export", id="export_btn"),
                        Button("Refresh", id="refresh_btn"),
                        id="control_panel"
                    ),
                    DataTable(id="book_table"),
                )
            
            # Downloads tab
            with TabPane("Downloads", id="downloads_tab"):
                yield VerticalScroll(
                    Container(
                        Horizontal(
                            Button("Start Queue", id="start_queue_btn"),
                            Button("Stop Queue", id="stop_queue_btn"),
                            Button("Resume Downloads", id="resume_downloads_btn"),
                            Button("Clear Completed", id="clear_completed_btn"),
                            id="downloads_control"
                        ),
                        Static("Active Downloads (0)", id="active_downloads_header", classes="section"),
                        Container(id="active_downloads_container"),
                        Static("Pending Downloads (0)", id="pending_downloads_header", classes="section"),
                        Container(id="pending_downloads_container"),
                        Static("Completed Downloads (0)", id="completed_downloads_header", classes="section"),
                        Container(id="completed_downloads_container"),
                        id="downloads_container"
                    ),
                )
            
            # Mirror management tab
            with TabPane("Mirrors", id="mirrors_tab"):
                yield VerticalScroll(
                    Container(
                        Static("Mirror Sites", classes="mirror-header"),
                        Horizontal(
                            Button("Check All Mirrors", id="check_mirrors_btn"),
                            Button("Save Mirror Config", id="save_mirrors_btn"),
                            id="mirrors_control"
                        ),
                        Container(id="mirrors_container")
                    ),
                )
            
            # Settings tab
            with TabPane("Settings", id="settings_tab"):
                yield Container(
                    Static("# Application Settings", classes="title"),
                    
                    Static("## General Settings", classes="section"),
                    Container(
                        Horizontal(
                            Static("Database Path:", classes="settings-label"),
                            Input(value=self.db_path, id="db_path_input", classes="settings-control")
                        ),
                        Horizontal(
                            Static("Output Directory:", classes="settings-label"),
                            Input(value=str(self.output_dir), id="output_dir_input", classes="settings-control")
                        ),
                        Horizontal(
                            Static("Enable Mirrors:", classes="settings-label"),
                            Switch(value=self.mirrors_enabled, id="mirrors_switch", classes="settings-control")
                        ),
                        classes="settings-group"
                    ),
                    
                    Static("## Download Settings", classes="section"),
                    Container(
                        Horizontal(
                            Static("Max Download Workers:", classes="settings-label"),
                            Input(value=str(self.max_workers), id="max_workers_input", classes="settings-control")
                        ),
                        Horizontal(
                            Static("Skip Existing Files:", classes="settings-label"),
                            Switch(value=True, id="skip_existing_switch", classes="settings-control")
                        ),
                        Horizontal(
                            Static("Resume Downloads:", classes="settings-label"),
                            Switch(value=True, id="resume_downloads_switch", classes="settings-control")
                        ),
                        classes="settings-group"
                    ),
                    
                    Horizontal(
                        Button("Save Settings", id="save_settings_btn"),
                        Button("Reset to Defaults", id="reset_settings_btn"),
                        id="settings_controls"
                    ),
                )
        
        # Status bar
        yield Static("Ready", id="status_bar")
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the app when mounted."""
        # Setup book table
        table = self.query_one("#book_table", DataTable)
        table.add_columns("ID", "Title", "Author(s)", "Language", "Downloads")
        table.cursor_type = "row"
        table.zebra_stripes = True
        
        # Start timers for periodic updates
        self.update_timer = self.set_interval(1, self.update_download_status)
        self.mirror_check_timer = self.set_interval(300, self.check_mirrors)  # Check mirrors every 5 minutes
        
        # Start the download queue
        self.queue.start()
        
        # Load initial data
        self.refresh_books()
        
        # Populate mirrors
        self.populate_mirrors()
    
    def update_status(self, message: str) -> None:
        """Update the status bar."""
        self.query_one("#status_bar", Static).update(message)
    
    def refresh_books(self, limit: int = 100) -> None:
        """Refresh the book list."""
        self.update_status("Loading books...")
        
        # Get books from database
        books = self.db.get_popular_english_epubs(limit)
        self.current_books = books
        
        # Update table
        table = self.query_one("#book_table", DataTable)
        table.clear()
        
        for book in books:
            # Get authors from metadata if available, otherwise use empty list
            if 'metadata' in book and book['metadata']:
                # Handle both string and dict metadata
                if isinstance(book['metadata'], str):
                    try:
                        metadata = json.loads(book['metadata'])
                    except json.JSONDecodeError:
                        metadata = {}
                else:
                    metadata = book['metadata']
                
                # Extract authors
                if 'authors' in metadata and metadata['authors']:
                    authors = metadata['authors']
                    author_names = ", ".join([a['name'] for a in authors])
                else:
                    author_names = "Unknown"
            else:
                author_names = "Unknown"
            
            table.add_row(
                str(book['book_id']),
                book['title'][:50] + "..." if len(book['title']) > 50 else book['title'],
                author_names[:30] + "..." if len(author_names) > 30 else author_names,
                book['language'],
                f"{book['download_count']:,}"
            )
        
        self.update_status(f"Loaded {len(books)} books")
    
    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        if event.row_key is not None:
            row_index = event.row_key.value
            if row_index < len(self.current_books):
                book = self.current_books[row_index]
                book_id = book['book_id']
                
                if book_id in self.selected_book_ids:
                    self.selected_book_ids.remove(book_id)
                else:
                    self.selected_book_ids.add(book_id)
                
                self.update_status(f"Selected {len(self.selected_book_ids)} books")
    
    @on(Button.Pressed, "#search_btn")
    def action_search(self) -> None:
        """Show search screen."""
        self.push_screen(SearchScreen())
    
    def on_screen_dismissed(self, event) -> None:
        """Handle screen dismissed events."""
        if isinstance(event.screen, SearchScreen):
            self.handle_search_result()
        elif isinstance(event.screen, ExportScreen):
            self.handle_export_result()
        elif isinstance(event.screen, MirrorDetailsScreen):
            # Just refresh mirrors display after details screen is dismissed
            self.populate_mirrors()
            
    def handle_search_result(self) -> None:
        """Handle search result."""
        if self.search_type and self.search_query:
            self.update_status(f"Searching for '{self.search_query}'...")
            
            if self.search_type == "full_text":
                results = self.db.full_text_search(self.search_query)
            elif self.search_type == "title":
                # Simple title search
                with self.db._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT * FROM books WHERE title LIKE ? LIMIT 100",
                        (f"%{self.search_query}%",)
                    )
                    results = [dict(row) for row in cursor.fetchall()]
            else:  # author search
                with self.db._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT DISTINCT b.* FROM books b
                        JOIN book_authors ba ON b.book_id = ba.book_id
                        JOIN authors a ON ba.author_id = a.author_id
                        WHERE a.name LIKE ? LIMIT 100
                    """, (f"%{self.search_query}%",))
                    results = [dict(row) for row in cursor.fetchall()]
            
            # Update current books
            self.current_books = results
            table = self.query_one("#book_table", DataTable)
            table.clear()
            
            for book in results:
                # Get authors from metadata if available, otherwise use empty list
                if 'metadata' in book and book['metadata'] and 'authors' in json.loads(book['metadata']):
                    authors = json.loads(book['metadata'])['authors']
                    author_names = ", ".join([a['name'] for a in authors])
                else:
                    author_names = "Unknown"
                
                table.add_row(
                    str(book['book_id']),
                    book['title'][:50] + "..." if len(book['title']) > 50 else book['title'],
                    author_names[:30] + "..." if len(author_names) > 30 else author_names,
                    book.get('language', 'en'),
                    f"{book.get('download_count', 0):,}"
                )
            
            self.update_status(f"Found {len(results)} books")
            self.search_type = None
            self.search_query = None
    
    @on(Button.Pressed, "#download_btn")
    def action_download(self) -> None:
        """Add selected books to download queue."""
        if not self.selected_book_ids:
            self.update_status("No books selected")
            return
        
        added = 0
        for book_id in self.selected_book_ids:
            if self.queue.add_task(book_id, Priority.NORMAL, self.output_dir):
                added += 1
        
        self.update_status(f"Added {added} books to download queue")
        
        # Auto-switch to Downloads tab
        tabs = self.query_one("#main_tabs", Tabs)
        tabs.active = "downloads_tab"
        
        # Clear selection
        self.selected_book_ids.clear()
    
    @on(Button.Pressed, "#export_btn")
    def action_export(self) -> None:
        """Show export screen."""
        self.push_screen(ExportScreen())
    
    def handle_export_result(self) -> None:
        """Handle export result."""
        if self.export_format and self.export_filename:
            self.update_status(f"Exporting to {self.export_filename}...")
            
            format_map = {
                "csv": ExportFormat.CSV,
                "json": ExportFormat.JSON,
                "excel": ExportFormat.EXCEL,
                "markdown": ExportFormat.MARKDOWN
            }
            
            # Export current view
            books_to_export = []
            for book in self.current_books:
                authors = self.db.get_book_authors(book['book_id'])
                book_data = {
                    'book_id': book['book_id'],
                    'title': book['title'],
                    'authors': [a['name'] for a in authors],
                    'language': book.get('language', 'en'),
                    'download_count': book.get('download_count', 0),
                    'subjects': [],
                    'formats': []
                }
                books_to_export.append(book_data)
            
            success = self.exporter.export_books(
                format_map[self.export_format],
                Path(self.export_filename),
                None
            )
            
            if success:
                self.update_status(f"Exported {len(books_to_export)} books to {self.export_filename}")
            else:
                self.update_status("Export failed")
            
            self.export_format = None
            self.export_filename = None
    
    @on(Button.Pressed, "#refresh_btn")
    def action_refresh(self) -> None:
        """Refresh the book list."""
        self.refresh_books()
    
    @on(Button.Pressed, "#start_queue_btn")
    def action_start_queue(self) -> None:
        """Start the download queue."""
        if not self.queue.workers:
            self.queue.start()
            self.update_status("Download queue started")
    
    @on(Button.Pressed, "#stop_queue_btn")
    def action_stop_queue(self) -> None:
        """Stop the download queue."""
        if self.queue.workers:
            self.queue.stop()
            self.update_status("Download queue stopped")
    
    @on(Button.Pressed, "#resume_downloads_btn")
    def action_resume_downloads(self) -> None:
        """Resume all pending downloads."""
        successful, failed = self.downloader.resume_all_downloads(self.output_dir)
        self.update_status(f"Resumed {successful} downloads ({failed} failed)")
    
    @on(Button.Pressed, "#clear_completed_btn")
    def action_clear_completed(self) -> None:
        """Clear completed downloads."""
        self.completed_downloads = []
        self.update_download_display()
        self.update_status("Cleared completed downloads")
    
    @on(Button.Pressed, "#check_mirrors_btn")
    def action_check_mirrors(self) -> None:
        """Check health of all mirrors."""
        self.check_mirrors(True)
    
    @on(Button.Pressed, "#save_mirrors_btn")
    def action_save_mirrors(self) -> None:
        """Save mirror configuration."""
        self.save_mirror_state()
        self.update_status("Mirror configuration saved")
    
    @on(Button.Pressed, "#save_settings_btn")
    def action_save_settings(self) -> None:
        """Save application settings."""
        # Get values from inputs
        db_path = self.query_one("#db_path_input", Input).value
        output_dir = self.query_one("#output_dir_input", Input).value
        mirrors_enabled = self.query_one("#mirrors_switch", Switch).value
        max_workers = int(self.query_one("#max_workers_input", Input).value)
        
        # Save settings (for this session - in a real app would save to config file)
        restart_needed = False
        
        if db_path != self.db_path or mirrors_enabled != self.mirrors_enabled:
            restart_needed = True
        
        self.db_path = db_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if max_workers != self.max_workers:
            self.max_workers = max_workers
            # Would need to restart the queue with new worker count
            if self.queue.workers:
                self.queue.stop()
                self.queue = DownloadQueue(db_path, max_workers=max_workers)
                self.queue.start()
        
        self.update_status("Settings saved" + (" (restart required for some changes)" if restart_needed else ""))
    
    @on(Button.Pressed, "#reset_settings_btn")
    def action_reset_settings(self) -> None:
        """Reset settings to defaults."""
        self.query_one("#db_path_input", Input).value = "gutenberg_books.db"
        self.query_one("#output_dir_input", Input).value = "downloads"
        self.query_one("#mirrors_switch", Switch).value = True
        self.query_one("#max_workers_input", Input).value = "3"
        self.query_one("#skip_existing_switch", Switch).value = True
        self.query_one("#resume_downloads_switch", Switch).value = True
        
        self.update_status("Settings reset to defaults")
    
    def action_search(self) -> None:
        """Show search screen."""
        self.push_screen(SearchScreen())
    
    def action_download(self) -> None:
        """Add selected books to download queue."""
        self.action_download()
    
    def action_export(self) -> None:
        """Show export screen."""
        self.push_screen(ExportScreen())
    
    def action_refresh(self) -> None:
        """Refresh the book list."""
        self.refresh_books()
    
    def action_help(self) -> None:
        """Show help screen."""
        self.push_screen(HelpScreen())
    
    def action_next_tab(self) -> None:
        """Switch to the next tab."""
        tabs = self.query_one("#main_tabs", Tabs)
        current_index = tabs.active_tab.index
        next_index = (current_index + 1) % len(tabs.tabs)
        tabs.active = tabs.tabs[next_index].id
    
    def action_prev_tab(self) -> None:
        """Switch to the previous tab."""
        tabs = self.query_one("#main_tabs", Tabs)
        current_index = tabs.active_tab.index
        prev_index = (current_index - 1) % len(tabs.tabs)
        tabs.active = tabs.tabs[prev_index].id
    
    def update_download_status(self) -> None:
        """Update download status information."""
        # Get queue status
        status = self.queue.get_status()
        
        # Update active tasks
        for task_info in status.get('active_tasks', []):
            book_id = task_info['book_id']
            
            # Fetch additional info if not already tracked
            if book_id not in self.active_downloads:
                book = self.db.get_book(book_id)
                if book:
                    self.active_downloads[book_id] = {
                        'book_id': book_id,
                        'title': book.get('title', f'Book {book_id}'),
                        'status': task_info['status'],
                        'started_at': task_info.get('started_at'),
                        'bytes_downloaded': 0,
                        'total_bytes': 0
                    }
        
        # Check for completed tasks
        current_active_ids = {task['book_id'] for task in status.get('active_tasks', [])}
        completed_ids = set(self.active_downloads.keys()) - current_active_ids
        
        for book_id in completed_ids:
            # Move to completed list
            if book_id in self.active_downloads:
                download_state = self.downloader.get_download_state(book_id)
                
                if download_state and download_state['status'] == 'completed':
                    completed_info = self.active_downloads[book_id].copy()
                    completed_info['status'] = 'completed'
                    completed_info['bytes_downloaded'] = download_state.get('bytes_downloaded', 0)
                    completed_info['total_bytes'] = download_state.get('total_bytes', 0)
                    completed_info['completed_at'] = datetime.now().isoformat()
                    
                    self.completed_downloads.append(completed_info)
                    
                # Remove from active
                del self.active_downloads[book_id]
        
        # Check for pending tasks
        pending_downloads = self.downloader.get_pending_downloads(10)
        self.pending_downloads = pending_downloads
        
        # Update display
        self.update_download_display()
    
    def update_download_display(self) -> None:
        """Update the downloads display."""
        # Update active downloads container
        active_container = self.query_one("#active_downloads_container", Container)
        active_container.remove_children()
        
        # Update header counts
        self.query_one("#active_downloads_header", Static).update(f"Active Downloads ({len(self.active_downloads)})")
        self.query_one("#pending_downloads_header", Static).update(f"Pending Downloads ({len(self.pending_downloads)})")
        self.query_one("#completed_downloads_header", Static).update(f"Completed Downloads ({len(self.completed_downloads)})")
        
        # Add active downloads
        for book_id, download in self.active_downloads.items():
            # Get progress data
            bytes_downloaded, total_bytes = self.download_progresses.get(book_id, (0, 1))
            
            # Avoid division by zero
            if total_bytes <= 0:
                total_bytes = 1
                
            progress_value = min(1.0, bytes_downloaded / total_bytes)
            
            # Create progress widget
            progress_widget = ProgressBar(
                progress=progress_value * 100,
                id=f"progress_{book_id}",
                classes="download-progress"
            )
            
            # Format sizes
            downloaded_mb = bytes_downloaded / (1024 * 1024)
            total_mb = total_bytes / (1024 * 1024)
            
            # Create container
            download_container = Container(
                Static(f"{download['title'][:40]}... ({round(downloaded_mb, 1)}MB / {round(total_mb, 1)}MB)"),
                progress_widget,
                classes="download-item"
            )
            
            active_container.mount(download_container)
        
        # Update pending downloads container
        pending_container = self.query_one("#pending_downloads_container", Container)
        pending_container.remove_children()
        
        for download in self.pending_downloads:
            pending_container.mount(
                Static(
                    f"[{download['book_id']}] {download.get('title', '')[:50]} - {download.get('status', 'pending')}",
                    classes=f"download-status-{download.get('status', 'pending')}"
                )
            )
        
        # Update completed downloads container
        completed_container = self.query_one("#completed_downloads_container", Container)
        completed_container.remove_children()
        
        for download in reversed(self.completed_downloads[-10:]):  # Show most recent 10
            completed_container.mount(
                Static(
                    f"[{download['book_id']}] {download.get('title', '')[:50]} - completed",
                    classes="download-status-completed"
                )
            )
    
    def populate_mirrors(self) -> None:
        """Populate the mirrors container with mirror site information."""
        if not self.mirror_manager:
            return
            
        try:
            mirrors_container = self.query_one("#mirrors_container", Container)
            mirrors_container.remove_children()
            
            for mirror in self.mirror_manager.get_mirrors():
                # Determine status class
                status_class = "mirror-status-active" if mirror.active else "mirror-status-inactive"
                
                # Determine health class
                health_class = "mirror-health-good"
                if mirror.health_score < 0.7:
                    health_class = "mirror-health-medium"
                if mirror.health_score < 0.4:
                    health_class = "mirror-health-poor"
                
                # Create mirror item
                mirror_item = Container(
                    Horizontal(
                        Static(f"{mirror.name} ({mirror.country or 'Unknown'})", classes=status_class),
                        Static(f"Health: {mirror.health_score:.2f}", classes=health_class),
                        Button("Details", id=f"mirror_details_{mirror.base_url}"),
                    ),
                    Static(f"URL: {mirror.base_url}"),
                    classes="mirror-item"
                )
                
                mirrors_container.mount(mirror_item)
        except Exception as e:
            self.update_status(f"Error populating mirrors: {e}")
    
    @on(Button.Pressed, "#mirror_details_*")
    def show_mirror_details(self, event: Button.Pressed) -> None:
        """Show details for a specific mirror."""
        # Extract the mirror URL from the button ID
        mirror_url = event.button.id.replace("mirror_details_", "")
        
        # Find the mirror
        for mirror in self.mirror_manager.get_mirrors():
            if mirror.base_url == mirror_url:
                self.push_screen(MirrorDetailsScreen(mirror))
                break
    
    def test_mirror(self, mirror: MirrorSite) -> None:
        """Test a mirror's health."""
        if not self.mirror_manager:
            return
            
        # Show status message
        self.update_status(f"Testing mirror: {mirror.name}...")
        
        # Run the test
        is_healthy = self.mirror_manager.check_mirror_health(mirror)
        
        # Update the display
        self.populate_mirrors()
        
        # Show result
        if is_healthy:
            self.update_status(f"Mirror {mirror.name} is healthy (Score: {mirror.health_score:.2f})")
        else:
            self.update_status(f"Mirror {mirror.name} is unhealthy (Score: {mirror.health_score:.2f})")
    
    def check_mirrors(self, show_status: bool = False) -> None:
        """Check all mirrors."""
        if not self.mirror_manager:
            return
            
        if show_status:
            self.update_status("Checking all mirrors...")
            
        # Run the check
        results = self.mirror_manager.check_all_mirrors()
        
        # Update the display
        self.populate_mirrors()
        
        if show_status:
            healthy_count = sum(1 for healthy in results.values() if healthy)
            self.update_status(f"Mirror check complete: {healthy_count}/{len(results)} mirrors healthy")
    
    def save_mirror_state(self) -> None:
        """Save mirror state to disk."""
        if not self.mirror_manager:
            return
            
        self.mirror_manager.save_mirrors()
    
    def on_unmount(self) -> None:
        """Clean up when the app is closed."""
        # Stop timers
        if self.update_timer:
            self.update_timer.stop()
            
        if self.mirror_check_timer:
            self.mirror_check_timer.stop()
            
        # Stop the download queue
        if self.queue.workers:
            self.queue.stop()
            
        # Close other resources
        if self.mirror_manager:
            self.mirror_manager.close()
            
        if self.downloader:
            self.downloader.client.close()


def run_tui(
    db_path: str = "gutenberg_books.db", 
    mirrors_enabled: bool = True,
    output_dir: str = "downloads",
    max_workers: int = 3
) -> None:
    """Run the TUI application.
    
    Args:
        db_path: Path to the database
        mirrors_enabled: Whether to use mirror sites
        output_dir: Directory for downloads
        max_workers: Maximum number of concurrent downloads
    """
    app = GutenbergBrowserApp(
        db_path=db_path,
        mirrors_enabled=mirrors_enabled,
        output_dir=output_dir,
        max_workers=max_workers
    )
    app.run()


if __name__ == "__main__":
    run_tui()