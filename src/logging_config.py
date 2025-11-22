"""
Centralized logging configuration for the Hiker project
This ensures logging is configured consistently across all modules
"""

import logging
import sys
import os


def setup_logging(level=logging.INFO, format_string=None):
    """
    Configure logging for the application
    
    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (optional)
    """
    # Only configure if not already configured (avoid duplicate handlers)
    if logging.root.handlers:
        # Already configured, just update level
        logging.root.setLevel(level)
        return
    
    # Default format
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure logging
    logging.basicConfig(
        level=level,
        format=format_string,
        stream=sys.stdout,
        force=True  # Override any existing configuration
    )


# Auto-configure logging when module is imported (if not already configured)
# This ensures logging works even when modules are imported directly
if not logging.root.handlers:
    # Check for environment variable to set log level
    log_level_env = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_env, logging.INFO)
    setup_logging(level=log_level)


