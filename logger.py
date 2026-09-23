import logging
import os

def setup_logger():
    log_dir = "app_logging"
    os.makedirs(log_dir, exist_ok=True)
    
    logger = logging.getLogger("AppLogger")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        file_handler = logging.FileHandler(os.path.join(log_dir, "app.log"))
        formatter = logging.Formatter(
            "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger

logger = setup_logger()
logger.info("Logger setup complete.")