import sqlite3
import pandas as pd

class RankScoreMapper:
    def __init__(self, db_path='lucid.db'):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS one_mark_one_rank (
                year INTEGER,
                province TEXT,
                category TEXT,
                score INTEGER,
                rank_start INTEGER,
                rank_end INTEGER,
                count INTEGER,
                PRIMARY KEY (year, province, category, score)
            )
        ''')
        conn.commit()
        conn.close()

    def import_data(self, df):
        """
        Import data from a pandas DataFrame.
        Expected columns: year, province, category, score, rank_start, rank_end, count
        """
        conn = sqlite3.connect(self.db_path)
        df.to_sql('one_mark_one_rank', conn, if_exists='append', index=False)
        conn.close()

    def score_to_rank(self, year, province, category, score):
        """
        Map a score to a rank interval [rank_start, rank_end].
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT rank_start, rank_end FROM one_mark_one_rank
            WHERE year = ? AND province = ? AND category = ? AND score = ?
        ''', (year, province, category, score))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {'rank_start': row[0], 'rank_end': row[1]}
        return None

    def rank_to_score(self, year, province, category, target_rank):
        """
        Map a rank to a specific score.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT score FROM one_mark_one_rank
            WHERE year = ? AND province = ? AND category = ? 
            AND rank_start <= ? AND rank_end >= ?
        ''', (year, province, category, target_rank, target_rank))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return row[0]
        return None
