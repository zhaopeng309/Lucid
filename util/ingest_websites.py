import os
import sqlite3
import pandas as pd
import argparse
import logging
from typing import Optional

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = [
    'school_name', 'location_of_school', 'administrative_department',
    'school_identification_code', 'level_of_education', 'school_type', 'website'
]

class UniversityIngester:
    def __init__(self, db_path: str = 'data/lucid.db'):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes the database, creating the college_profiles table if it does not exist."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            # Create college_profiles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS college_profiles (
                    school_name VARCHAR(100) PRIMARY KEY,
                    location_of_school VARCHAR(50) NOT NULL,
                    administrative_department VARCHAR(100) NOT NULL,
                    school_identification_code VARCHAR(20) NOT NULL,
                    level_of_education VARCHAR(50) NOT NULL,
                    school_type VARCHAR(50) NOT NULL,
                    website VARCHAR(200) NOT NULL
                )
            ''')
            conn.commit()
        finally:
            conn.close()

    def ingest_excel(self, excel_path: str) -> int:
        """
        Parses university profiles and website URLs from an Excel file and inserts them into the database.
        Ensures atomicity and duplicate handling (INSERT OR REPLACE).
        Returns the number of rows successfully imported.
        """
        if not os.path.exists(excel_path):
            raise FileNotFoundError(f"Excel file not found at: {excel_path}")

        # 1. Load Excel file using pandas
        try:
            df = pd.read_excel(excel_path, sheet_name='University')
        except Exception as e:
            # Fallback to reading first sheet if 'University' is not found
            try:
                df = pd.read_excel(excel_path)
            except Exception as inner_e:
                raise ValueError(f"Failed to read Excel file: {inner_e}")

        # 2. Strip and normalize column names
        df.columns = df.columns.str.strip()

        # Check for missing required columns
        missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Excel file is missing required columns: {missing_cols}")

        # 3. Clean and validate data rows
        # Keep only the required columns
        df = df[REQUIRED_COLUMNS].copy()

        # Fill NaNs with empty string first for processing
        df = df.fillna("")

        # Convert and strip string representations of all cells
        for col in REQUIRED_COLUMNS:
            df[col] = df[col].astype(str).str.strip()

        # Filter out rows with empty school_name or empty website
        # And raise an error if any required field is missing in an invalid way (except complete blank padding rows)
        records_to_insert = []
        for index, row in df.iterrows():
            row_num = index + 1
            school_name = row['school_name']
            website = row['website']

            # If the entire row is blank, we can skip it
            if not any(row.values):
                continue

            # Validate non-empty fields
            for col in REQUIRED_COLUMNS:
                if not row[col]:
                    raise ValueError(f"Row {row_num}: Missing value for required field '{col}'")

            # Validate website format slightly (must start with http/https or contain a domain structure)
            if not (website.startswith("http://") or website.startswith("https://") or "www." in website or "." in website):
                logger.warning(f"Row {row_num}: Non-standard website URL format '{website}' for school '{school_name}'")

            records_to_insert.append((
                row['school_name'],
                row['location_of_school'],
                row['administrative_department'],
                row['school_identification_code'],
                row['level_of_education'],
                row['school_type'],
                row['website']
            ))

        if not records_to_insert:
            return 0

        # 4. Ingest into database using INSERT OR REPLACE (for idempotency)
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            insert_query = '''
                INSERT OR REPLACE INTO college_profiles (
                    school_name, location_of_school, administrative_department,
                    school_identification_code, level_of_education, school_type, website
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            '''
            cursor.executemany(insert_query, records_to_insert)
            conn.commit()
            return len(records_to_insert)
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Lucid University Website & Profile Ingester")
    parser.add_argument("--excel", required=True, help="Path to the University.xlsx Excel file")
    parser.add_argument("--db", default="data/lucid.db", help="Path to the SQLite database (default: data/lucid.db)")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    try:
        ingester = UniversityIngester(db_path=args.db)
        logging.info(f"Starting university profiles and websites ingestion from {args.excel}...")
        count = ingester.ingest_excel(args.excel)
        logging.info(f"Successfully imported {count} university profiles into {args.db}.")
    except Exception as e:
        logging.error(f"Ingestion failed: {e}")
        import sys
        sys.exit(1)
