import os
import sqlite3
from typing import Dict, Any, Optional

class ProfileManager:
    def __init__(self, db_path: str = 'data/lucid.db'):
        self.db_path = db_path
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initializes the database, creating the user_profiles table if it does not exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id VARCHAR(50) PRIMARY KEY,
                    username VARCHAR(100),
                    province VARCHAR(20) NOT NULL,
                    score INTEGER NOT NULL,
                    rank INTEGER NOT NULL,
                    category VARCHAR(20) NOT NULL,
                    subjects VARCHAR(100),
                    eyesight_color VARCHAR(20) DEFAULT "Normal",
                    english_score INTEGER DEFAULT 0,
                    city_preferences VARCHAR(200)
                )
            ''')
            conn.commit()
        finally:
            conn.close()

    def save_profile(self, profile: Dict[str, Any]) -> None:
        """
        Saves or updates a user profile.
        """
        user_id = profile.get('user_id')
        if not user_id:
            raise ValueError("Profile must contain a user_id")
        
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_profiles (
                    user_id, username, province, score, rank, category, subjects, eyesight_color, english_score, city_preferences
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    province=excluded.province,
                    score=excluded.score,
                    rank=excluded.rank,
                    category=excluded.category,
                    subjects=excluded.subjects,
                    eyesight_color=excluded.eyesight_color,
                    english_score=excluded.english_score,
                    city_preferences=excluded.city_preferences
            ''', (
                user_id,
                profile.get('username'),
                profile.get('province'),
                profile.get('score'),
                profile.get('rank'),
                profile.get('category'),
                profile.get('subjects'),
                profile.get('eyesight_color', 'Normal'),
                profile.get('english_score', 0),
                profile.get('city_preferences')
            ))
            conn.commit()
        finally:
            conn.close()

    def load_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads a user profile by user_id. Returns None if not found.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM user_profiles WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()
