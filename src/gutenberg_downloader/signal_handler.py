"""Signal handling for graceful shutdown."""

import logging
import signal
import sys
from typing import Callable, Dict, List, Optional, Set, Any

logger = logging.getLogger(__name__)


class SignalHandler:
    """Manages signal handling for graceful application shutdown.
    
    This class provides a central place to register cleanup callbacks that should
    be executed when the application receives termination signals like SIGINT (Ctrl+C),
    SIGTERM, etc. It ensures resources are properly released and state is saved before
    the application exits.
    """
    
    def __init__(self):
        """Initialize the signal handler."""
        self.shutdown_in_progress = False
        self.exit_code = 0
        self.callbacks: List[Callable[[], None]] = []
        self.registered_signals: Set[int] = set()
    
    def register_signal(self, sig: signal.Signals):
        """Register a signal to be handled.
        
        Args:
            sig: Signal to register
        """
        if sig.value in self.registered_signals:
            return
            
        original_handler = signal.getsignal(sig)
        
        def handler(signum, frame):
            self.initiate_shutdown(signum, original_handler)
        
        signal.signal(sig, handler)
        self.registered_signals.add(sig.value)
        logger.debug(f"Registered handler for signal {sig.name}")
    
    def register_common_signals(self):
        """Register common termination signals."""
        # SIGINT (Ctrl+C)
        self.register_signal(signal.SIGINT)
        
        # SIGTERM (termination request)
        self.register_signal(signal.SIGTERM)
        
        # On Unix systems, register additional signals
        if sys.platform != "win32":
            # SIGHUP (terminal closed)
            self.register_signal(signal.SIGHUP)
            
        logger.info("Registered handlers for common termination signals")
    
    def register_callback(self, callback: Callable[[], None]):
        """Register a cleanup callback function.
        
        Args:
            callback: Function to call during shutdown
        """
        self.callbacks.append(callback)
        logger.debug(f"Registered shutdown callback: {callback.__name__}")
    
    def initiate_shutdown(self, signum: int, original_handler: Optional[Callable] = None):
        """Initiate the shutdown process.
        
        Args:
            signum: Signal number that triggered shutdown
            original_handler: Original signal handler to call after cleanup
        """
        if self.shutdown_in_progress:
            logger.warning("Shutdown already in progress, received another signal")
            # Force exit on second signal
            sys.exit(1)
            
        self.shutdown_in_progress = True
        signal_name = signal.Signals(signum).name
        
        logger.info(f"Received signal {signal_name} ({signum}), initiating graceful shutdown")
        print(f"\n⚠️  Received {signal_name} signal. Shutting down gracefully...")
        print("Please wait while operations are completed and resources are released...")
        
        # Execute all registered callbacks
        for callback in reversed(self.callbacks):
            try:
                logger.debug(f"Executing shutdown callback: {callback.__name__}")
                callback()
            except Exception as e:
                logger.error(f"Error in shutdown callback {callback.__name__}: {e}")
        
        # After cleanup, exit or call original handler
        if original_handler and callable(original_handler) and original_handler != signal.SIG_IGN and original_handler != signal.SIG_DFL:
            logger.debug(f"Calling original handler for signal {signal_name}")
            original_handler(signum, None)
        else:
            logger.info("Shutdown complete, exiting")
            sys.exit(self.exit_code)
    
    def set_exit_code(self, code: int):
        """Set the exit code to use when terminating.
        
        Args:
            code: Exit code
        """
        self.exit_code = code


# Singleton instance
handler = SignalHandler()


def setup_signal_handling():
    """Set up signal handling for the application."""
    handler.register_common_signals()
    return handler


def register_shutdown_callback(callback: Callable[[], None]):
    """Register a callback to be called during shutdown.
    
    Args:
        callback: Function to call during shutdown
    """
    handler.register_callback(callback)


def shutdown_in_progress() -> bool:
    """Check if shutdown is in progress.
    
    Returns:
        True if shutdown is in progress
    """
    return handler.shutdown_in_progress


def handle_keyboard_interrupt(func: Callable) -> Callable:
    """Decorator to handle KeyboardInterrupt gracefully.
    
    This decorator wraps a function to catch KeyboardInterrupt (Ctrl+C)
    and handle it by initiating the graceful shutdown process instead of
    crashing with a stack trace.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received, initiating graceful shutdown")
            print("\n\nKeyboardInterrupt received. Shutting down gracefully...")
            handler.initiate_shutdown(signal.SIGINT.value)
            return 1  # Return non-zero exit code
    
    return wrapper