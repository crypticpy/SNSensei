import logging
import os
from app.config import get_config

def setup_logging():
    config = get_config()
    log_level = config.get('LOG_LEVEL', 'INFO')
    log_format = config.get('LOG_FORMAT', '%(asctime)s - %(levelname)s - %(message)s')

    # Create a logger
    logger = logging.getLogger("ticket_analyzer")
    logger.setLevel(log_level)

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # File handler with rotation
    log_directory = "logs"
    os.makedirs(log_directory, exist_ok=True)
    file_handler = logging.FileHandler(
        filename=os.path.join(log_directory, "ticket_analyzer.log"),
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# Example usage
if __name__ == "__main__":
    logger = setup_logging()
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")