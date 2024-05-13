import logging
import os
from datetime import datetime


def setup_logging(config):
    log_level = config["log_level"]
    log_format = config["log_format"]

    # Create a logger for the application
    logger = logging.getLogger("ticket_analyzer")
    logger.setLevel(log_level)

    # Create a logger for OpenAI API requests
    openai_logger = logging.getLogger("openai")
    openai_logger.setLevel(logging.DEBUG)

    # Create file handlers and set the log levels
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("../logs", exist_ok=True)
    info_file_handler = logging.FileHandler(f"../logs/info_{timestamp}.log")
    info_file_handler.setLevel(logging.INFO)
    error_file_handler = logging.FileHandler(f"../logs/error_{timestamp}.log")

    # Set the log level for the error file handler
    error_file_handler.setLevel(logging.ERROR)

    # Create a formatter and add it to the handlers
    formatter = logging.Formatter(log_format)
    info_file_handler.setFormatter(formatter)
    error_file_handler.setFormatter(formatter)

    # Add the handlers to the loggers
    logger.addHandler(info_file_handler)
    logger.addHandler(error_file_handler)
    openai_logger.addHandler(info_file_handler)

    return logger
