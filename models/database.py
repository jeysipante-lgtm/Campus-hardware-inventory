import sqlite3
from logger import logger

def init_db(db_name="lab_tracker.db"):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            
            # 1. User Authentication Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL
                )
            """)
            
            # 2. Experiments Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    status TEXT NOT NULL
                )
            """)
            
        logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Database setup error: {e}")