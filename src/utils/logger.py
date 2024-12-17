import logging

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        # Configure logging only if it hasn't been configured yet
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger 
