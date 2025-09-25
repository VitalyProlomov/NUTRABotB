import logging
import sys
from logging.handlers import RotatingFileHandler
import colorlog


def setup_logging():
    """Setup comprehensive logging configuration"""

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatters
    color_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    )

    standard_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(color_formatter)
    console_handler.setLevel(logging.INFO)

    # File handler
    file_handler = RotatingFileHandler(
        'bot.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(standard_formatter)
    file_handler.setLevel(logging.DEBUG)

    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Set specific log levels for external libraries
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.INFO)

    return logger


# Initialize logging when module is imported
setup_logging()