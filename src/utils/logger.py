import logging
import sys


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a logger instance with the specified name."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:  # Only add handler if it doesn't exist
        # Create console handler with a higher log level
        console_handler = logging.StreamHandler(sys.stdout)  # Explicitly use stdout
        console_handler.setLevel(level)

        # Create formatter and add it to the handler
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)

        # Add the handler to the logger
        logger.addHandler(console_handler)
        logger.setLevel(level)  # Set the logger level
        
        # Prevent propagation to avoid duplicate logs
        logger.propagate = False

    return logger
