"""Download queue management system."""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from queue import PriorityQueue, Queue
from typing import Dict, List, Optional, Tuple, Any

from .database import BookDatabase
from .smart_downloader import SmartDownloader
from .signal_handler import register_shutdown_callback, shutdown_in_progress

logger = logging.getLogger(__name__)


class Priority(Enum):
    """Download priority levels."""
    HIGH = 1
    NORMAL = 5
    LOW = 10


class Status(Enum):
    """Download status."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(order=True)
class DownloadTask:
    """A download task in the queue."""
    priority: Priority = field(compare=True)
    book_id: int = field(compare=False)
    epub_url: str = field(compare=False)
    output_path: Path = field(compare=False)
    retry_count: int = field(default=0, compare=False)
    status: Status = field(default=Status.PENDING, compare=False)
    error_message: Optional[str] = field(default=None, compare=False)
    created_at: datetime = field(default_factory=datetime.now, compare=False)
    started_at: Optional[datetime] = field(default=None, compare=False)
    completed_at: Optional[datetime] = field(default=None, compare=False)


class DownloadQueue:
    """Manages a queue of book downloads."""
    
    def __init__(
        self, 
        db_path: str = "gutenberg_books.db",
        max_workers: int = 3,
        max_retries: int = 3,
        auto_save_state: bool = True,
        state_file: Optional[str] = "queue_state.json"
    ):
        """Initialize download queue.
        
        Args:
            db_path: Path to database
            max_workers: Maximum concurrent downloads
            max_retries: Maximum retry attempts
            auto_save_state: Whether to automatically save state on shutdown
            state_file: Path to state file for persistence
        """
        self.db = BookDatabase(db_path)
        self.downloader = SmartDownloader(db_path)
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.auto_save_state = auto_save_state
        self.state_file = Path(state_file) if state_file else None
        
        # Queues
        self.task_queue: PriorityQueue[DownloadTask] = PriorityQueue()
        self.status_queue: Queue[Dict[str, Any]] = Queue()
        
        # Worker threads
        self.workers: List[threading.Thread] = []
        self.stop_event = threading.Event()
        
        # Task tracking
        self.active_tasks: Dict[int, DownloadTask] = {}
        self.completed_tasks: List[DownloadTask] = []
        self.failed_tasks: List[DownloadTask] = []
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            "queued": 0,
            "downloading": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
            "total_bytes": 0,
            "downloaded_bytes": 0,
        }
        
        # Register shutdown callback if auto save is enabled
        if auto_save_state and state_file:
            register_shutdown_callback(self._on_shutdown)
    
    def add_task(
        self, 
        book_id: int,
        priority: Priority = Priority.NORMAL,
        output_dir: Optional[Path] = None
    ) -> bool:
        """Add a download task to the queue.
        
        Args:
            book_id: Book ID to download
            priority: Download priority
            output_dir: Output directory
            
        Returns:
            True if task was added, False otherwise
        """
        # Get book metadata
        book = self.db.get_book(book_id)
        if not book:
            logger.error(f"Book {book_id} not found in database")
            return False
        
        # Find EPUB URL
        epub_url = None
        formats = book.get('formats', {})
        for fmt, url in formats.items():
            if 'epub' in fmt.lower():
                epub_url = url
                break
        
        if not epub_url:
            logger.error(f"No EPUB format available for book {book_id}")
            return False
        
        # Determine output path
        if not output_dir:
            output_dir = Path("downloads")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        title = book.get('title', f'book_{book_id}')
        clean_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
        clean_title = clean_title.replace(" ", "_")[:100]
        filename = f"{clean_title}.epub"
        output_path = output_dir / filename
        
        # Create task
        task = DownloadTask(
            priority=priority,
            book_id=book_id,
            epub_url=epub_url,
            output_path=output_path
        )
        
        # Add to queue
        self.task_queue.put(task)
        with self.lock:
            self.stats["queued"] += 1
        
        logger.info(f"Added book {book_id} to download queue with {priority.name} priority")
        return True
    
    def add_search_results(
        self,
        search_results: List[Dict],
        priority: Priority = Priority.NORMAL,
        output_dir: Optional[Path] = None
    ) -> int:
        """Add search results to download queue.
        
        Args:
            search_results: List of search result dictionaries
            priority: Download priority
            output_dir: Output directory
            
        Returns:
            Number of tasks added
        """
        added = 0
        for result in search_results:
            book_id = result.get('book_id')
            if book_id and self.add_task(book_id, priority, output_dir):
                added += 1
        
        logger.info(f"Added {added} books to download queue")
        return added
    
    def _worker(self, worker_id: int):
        """Worker thread for processing download tasks."""
        logger.info(f"Worker {worker_id} started")
        
        while not self.stop_event.is_set() and not shutdown_in_progress():
            try:
                # Get task from queue (timeout to check stop event)
                try:
                    task = self.task_queue.get(timeout=1)
                except TimeoutError:
                    # Regular timeout to check for stop conditions
                    continue
                    
                # Check if we should stop
                if self.stop_event.is_set() or shutdown_in_progress():
                    # Put the task back in the queue for future processing
                    self.task_queue.put(task)
                    break
                
                # Update status
                task.status = Status.DOWNLOADING
                task.started_at = datetime.now()
                
                with self.lock:
                    self.active_tasks[task.book_id] = task
                    self.stats["queued"] -= 1
                    self.stats["downloading"] += 1
                
                # Report status
                self.status_queue.put({
                    "worker_id": worker_id,
                    "task": task,
                    "event": "started"
                })
                
                # Download the book
                logger.info(f"Worker {worker_id} downloading book {task.book_id}")
                success = self.downloader.download_book(
                    task.book_id,
                    task.epub_url,
                    task.output_path.parent,
                    filename=task.output_path.name
                )
                
                # Update status
                task.completed_at = datetime.now()
                
                if success:
                    task.status = Status.COMPLETED
                    with self.lock:
                        self.completed_tasks.append(task)
                        self.stats["downloading"] -= 1
                        self.stats["completed"] += 1
                else:
                    # Check if we're shutting down
                    if self.stop_event.is_set() or shutdown_in_progress():
                        # Save task for future processing
                        task.status = Status.PENDING
                        self.task_queue.put(task)
                        break
                    
                    task.status = Status.FAILED
                    task.retry_count += 1
                    
                    # Retry if under limit
                    if task.retry_count < self.max_retries:
                        task.status = Status.PENDING
                        self.task_queue.put(task)
                        logger.info(f"Retrying book {task.book_id} (attempt {task.retry_count})")
                    else:
                        with self.lock:
                            self.failed_tasks.append(task)
                            self.stats["downloading"] -= 1
                            self.stats["failed"] += 1
                
                # Remove from active tasks
                with self.lock:
                    if task.book_id in self.active_tasks:
                        del self.active_tasks[task.book_id]
                
                # Report status
                self.status_queue.put({
                    "worker_id": worker_id,
                    "task": task,
                    "event": "completed" if success else "failed"
                })
                
            except Exception as e:
                if not isinstance(e, TimeoutError):
                    logger.error(f"Worker {worker_id} error: {e}")
        
        logger.info(f"Worker {worker_id} stopped")
    
    def start(self):
        """Start the download queue workers."""
        logger.info(f"Starting download queue with {self.max_workers} workers")
        
        # Create and start worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker,
                args=(i,),
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
    
    def stop(self, save_state: bool = True, timeout: float = 5.0):
        """Stop the download queue workers.
        
        Args:
            save_state: Whether to save queue state
            timeout: Worker join timeout in seconds
        """
        logger.info("Stopping download queue")
        self.stop_event.set()
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=timeout)
            
        # Check if workers are still alive
        active_workers = sum(1 for w in self.workers if w.is_alive())
        if active_workers > 0:
            logger.warning(f"{active_workers} workers did not exit cleanly")
        
        # Save state if requested
        if save_state and self.state_file:
            self.save_state(self.state_file)
            
    def _on_shutdown(self):
        """Handle application shutdown.
        
        This method is called when the application is shutting down due to a signal.
        It ensures the queue state is saved and resources are released.
        """
        if self.stop_event.is_set():
            # Already stopped or stopping
            return
            
        logger.info("Application shutdown in progress, stopping download queue")
        print("\n📋 Saving download queue state...")
        self.stop(save_state=self.auto_save_state, timeout=2.0)
    
    def get_status(self) -> Dict:
        """Get current queue status."""
        with self.lock:
            return {
                "stats": self.stats.copy(),
                "active_tasks": [
                    {
                        "book_id": task.book_id,
                        "status": task.status.value,
                        "started_at": task.started_at.isoformat() if task.started_at else None
                    }
                    for task in self.active_tasks.values()
                ],
                "queue_size": self.task_queue.qsize(),
                "workers": self.max_workers
            }
    
    def save_state(self, file_path: Path):
        """Save queue state to file."""
        state = {
            "queued": [],
            "active": [],
            "completed": [],
            "failed": []
        }
        
        # Get all tasks from queue (destructive)
        while not self.task_queue.empty():
            try:
                task = self.task_queue.get_nowait()
                state["queued"].append({
                    "book_id": task.book_id,
                    "priority": task.priority.value,
                    "output_path": str(task.output_path),
                    "retry_count": task.retry_count
                })
            except:
                break
        
        # Add active tasks
        with self.lock:
            for task in self.active_tasks.values():
                state["active"].append({
                    "book_id": task.book_id,
                    "priority": task.priority.value,
                    "output_path": str(task.output_path),
                    "retry_count": task.retry_count
                })
            
            # Add completed and failed
            for task in self.completed_tasks:
                state["completed"].append(task.book_id)
            
            for task in self.failed_tasks:
                state["failed"].append({
                    "book_id": task.book_id,
                    "error": task.error_message,
                    "retry_count": task.retry_count
                })
        
        # Save to file
        with open(file_path, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"Queue state saved to {file_path}")
    
    def load_state(self, file_path: Path):
        """Load queue state from file."""
        if not file_path.exists():
            logger.warning(f"State file {file_path} not found")
            return
        
        with open(file_path, 'r') as f:
            state = json.load(f)
        
        # Restore queued tasks
        for task_data in state.get("queued", []):
            task = DownloadTask(
                priority=Priority(task_data["priority"]),
                book_id=task_data["book_id"],
                epub_url="",  # Will be fetched when processing
                output_path=Path(task_data["output_path"]),
                retry_count=task_data.get("retry_count", 0)
            )
            self.task_queue.put(task)
        
        # Restore active tasks as queued (will retry)
        for task_data in state.get("active", []):
            task = DownloadTask(
                priority=Priority(task_data["priority"]),
                book_id=task_data["book_id"],
                epub_url="",
                output_path=Path(task_data["output_path"]),
                retry_count=task_data.get("retry_count", 0)
            )
            self.task_queue.put(task)
        
        logger.info(f"Queue state loaded from {file_path}")
        logger.info(f"Restored {self.task_queue.qsize()} tasks to queue")