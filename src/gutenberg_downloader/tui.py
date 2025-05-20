"""Terminal User Interface for browsing and downloading books."""

from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Union

from rich.table import Table
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static

from .database import BookDatabase
from .download_queue import DownloadQueue, Priority
from .exporter import BookExporter, ExportFormat


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
            self.app.pop_screen()
    
    @on(Button.Pressed, "#search_title")
    def search_by_title(self) -> None:
        query = self.query_one("#search_input", Input).value
        if query:
            self.app.search_type = "title"  # type: ignore
            self.app.search_query = query  # type: ignore
            self.app.pop_screen()
    
    @on(Button.Pressed, "#search_author")
    def search_by_author(self) -> None:
        query = self.query_one("#search_input", Input).value
        if query:
            self.app.search_type = "author"  # type: ignore
            self.app.search_query = query  # type: ignore
            self.app.pop_screen()
    
    @on(Button.Pressed, "#cancel")
    def cancel_search(self) -> None:
        self.app.pop_screen()


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
            self.app.pop_screen()
    
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
        self.app.pop_screen()


class BookBrowserApp(App):
    """TUI application for browsing and downloading books."""
    
    CSS = """
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
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "search", "Search"),
        ("d", "download", "Download"),
        ("e", "export", "Export"),
        ("r", "refresh", "Refresh"),
        ("?", "help", "Help"),
    ]
    
    def __init__(self, db_path: str = "gutenberg_books.db"):
        super().__init__()
        self.db: BookDatabase = BookDatabase(db_path)
        self.queue: DownloadQueue = DownloadQueue(db_path)
        self.exporter: BookExporter = BookExporter(db_path)
        self.current_books: List[Dict[str, Any]] = []
        self.selected_book_ids: Set[int] = set()
        
        # Search state
        self.search_type: Optional[str] = None
        self.search_query: Optional[str] = None
        
        # Export state
        self.export_format: Optional[str] = None
        self.export_filename: Optional[str] = None
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Horizontal(
                Button("Search", id="search_btn"),
                Button("Download Selected", id="download_btn"),
                Button("Export", id="export_btn"),
                Button("Refresh", id="refresh_btn"),
                Button("Quit", id="quit_btn"),
                id="control_panel"
            ),
            DataTable(id="book_table"),
            Static("Ready", id="status_bar"),
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the app when mounted."""
        table = self.query_one("#book_table", DataTable)
        table.add_columns("ID", "Title", "Author(s)", "Language", "Downloads")
        table.cursor_type = "row"
        table.zebra_stripes = True
        
        # Load initial data
        self.refresh_books()
    
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
            authors = self.db.get_book_authors(book['book_id'])
            author_names = ", ".join([a['name'] for a in authors])
            
            table.add_row(
                str(book['book_id']),
                book['title'][:50] + "..." if len(book['title']) > 50 else book['title'],
                author_names[:30] + "..." if len(author_names) > 30 else author_names,
                book['language'],
                f"{book['download_count']:,}"
            )
        
        self.update_status(f"Loaded {len(books)} books")
    
    def update_status(self, message: str) -> None:
        """Update the status bar."""
        self.query_one("#status_bar", Static).update(message)
    
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
    
    @on(Screen.Dismissed, SearchScreen)
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
                if 'authors' in book:
                    author_names = ", ".join([a['name'] for a in book['authors']])
                else:
                    authors = self.db.get_book_authors(book['book_id'])
                    author_names = ", ".join([a['name'] for a in authors])
                
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
            if self.queue.add_task(book_id, Priority.NORMAL, Path("downloads")):
                added += 1
        
        self.update_status(f"Added {added} books to download queue")
        self.selected_book_ids.clear()
    
    @on(Button.Pressed, "#export_btn")
    def action_export(self) -> None:
        """Show export screen."""
        self.push_screen(ExportScreen())
    
    @on(Screen.Dismissed, ExportScreen)
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
            
            success = self.exporter._export_csv(
                books_to_export, 
                Path(self.export_filename)
            ) if self.export_format == "csv" else False
            
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
    
    @on(Button.Pressed, "#quit_btn")
    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
    
    def action_help(self) -> None:
        """Show help."""
        help_text = """
        Keyboard Shortcuts:
        
        q - Quit application
        s - Search for books
        d - Download selected books
        e - Export current view
        r - Refresh book list
        ? - Show this help
        
        Click on rows to select/deselect books.
        """
        self.update_status(help_text.strip())


def run_tui(db_path: str = "gutenberg_books.db") -> None:
    """Run the TUI application."""
    app = BookBrowserApp(db_path)
    app.run()