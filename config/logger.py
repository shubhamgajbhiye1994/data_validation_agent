import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(log_dir="logs", log_file="assistant.log", level=logging.INFO):
    """Set up the logger to write to both console and a file in the logs folder."""
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_path = os.path.join(log_dir, log_file)
    
    logger = logging.getLogger("data_quality")
    logger.setLevel(level)
    
    # Avoid adding handlers multiple times
    if not logger.handlers:
        # File handler (10 MB per file, keep 5 backups)
        file_handler = RotatingFileHandler(log_path, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
    return logger

def get_logger(name="data_quality"):
    """Get the pre-configured logger."""
    return logging.getLogger(name)
