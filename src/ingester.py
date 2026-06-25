import os
import sqlite3
import csv
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = [
    'province', 'year', 'category', 'college_code',
    'college_name', 'city', 'major_code', 'major_name',
    'plan_count', 'min_score', 'min_rank'
]

class AdmissionsIngester:
    def __init__(self, db_path: str = 'data/lucid.db'):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes the database, creating the table and indices if they do not exist."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            # Create table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS college_admissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    province VARCHAR(20) NOT NULL,
                    year INTEGER NOT NULL,
                    category VARCHAR(20) NOT NULL,
                    college_code VARCHAR(10) NOT NULL,
                    college_name VARCHAR(100) NOT NULL,
                    college_tags VARCHAR(100),
                    city VARCHAR(50) NOT NULL,
                    major_code VARCHAR(20) NOT NULL,
                    major_name VARCHAR(100) NOT NULL,
                    plan_count INTEGER NOT NULL,
                    min_score INTEGER NOT NULL,
                    min_rank INTEGER NOT NULL,
                    tuition INTEGER DEFAULT 0
                )
            ''')
            # Create indices
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_query_rank 
                ON college_admissions (province, category, min_rank)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_college_name 
                ON college_admissions (college_name)
            ''')
            conn.commit()
        finally:
            conn.close()

    def clear_table(self):
        """Clears all records from the college_admissions table."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM college_admissions')
            conn.commit()
        finally:
            conn.close()

    def validate_and_convert(self, row: Dict[str, Any], row_num: int) -> Dict[str, Any]:
        """
        Validates and converts a raw dictionary row into a standardized admissions record.
        Raises ValueError if validation fails.
        """
        cleaned_row = {}

        # 1. Check for missing required fields
        for field in REQUIRED_FIELDS:
            is_empty_int = field in ['year', 'plan_count', 'min_score', 'min_rank'] and isinstance(row.get(field), str) and not row[field].strip()
            if field not in row or row[field] is None or is_empty_int:
                raise ValueError(f"Row {row_num}: Missing required field '{field}'")

        # 2. String fields check (must be non-empty)
        string_fields = [
            'province', 'category', 'college_code', 'college_name', 
            'city', 'major_code', 'major_name'
        ]
        for field in string_fields:
            val = row[field]
            if not isinstance(val, str):
                val = str(val)
            val = val.strip()
            if not val:
                raise ValueError(f"Row {row_num}: Field '{field}' cannot be empty or whitespace only")
            cleaned_row[field] = val

        # 3. Optional string field: college_tags
        college_tags = row.get('college_tags')
        if college_tags is not None:
            if not isinstance(college_tags, str):
                college_tags = str(college_tags)
            cleaned_row['college_tags'] = college_tags.strip()
        else:
            cleaned_row['college_tags'] = None

        # 4. Integer conversions and range checks
        int_fields = {
            'year': (lambda x: x > 1900, "must be greater than 1900"),
            'plan_count': (lambda x: x >= 0, "must be non-negative"),
            'min_score': (lambda x: x >= 0, "must be non-negative"),
            'min_rank': (lambda x: x >= 1, "must be a positive integer (>= 1)")
        }

        for field, (constraint_fn, err_msg) in int_fields.items():
            raw_val = row[field]
            try:
                if isinstance(raw_val, (int, float)):
                    f_val = float(raw_val)
                elif isinstance(raw_val, str):
                    f_val = float(raw_val.strip())
                else:
                    raise TypeError()
                
                if not f_val.is_integer():
                    raise ValueError()
                val = int(f_val)
            except (ValueError, TypeError):
                raise ValueError(f"Row {row_num}: Field '{field}' must be an integer, got '{raw_val}'")

            if not constraint_fn(val):
                raise ValueError(f"Row {row_num}: Field '{field}' value {val} {err_msg}")
            cleaned_row[field] = val

        # 5. Optional integer field: tuition (default to 0)
        raw_tuition = row.get('tuition')
        if raw_tuition is None or (isinstance(raw_tuition, str) and not raw_tuition.strip()):
            cleaned_row['tuition'] = 0
        else:
            try:
                if isinstance(raw_tuition, (int, float)):
                    f_tuition = float(raw_tuition)
                elif isinstance(raw_tuition, str):
                    f_tuition = float(raw_tuition.strip())
                else:
                    raise TypeError()
                
                if not f_tuition.is_integer():
                    raise ValueError()
                tuition_val = int(f_tuition)
            except (ValueError, TypeError):
                raise ValueError(f"Row {row_num}: Field 'tuition' must be an integer, got '{raw_tuition}'")

            if tuition_val < 0:
                raise ValueError(f"Row {row_num}: Field 'tuition' cannot be negative, got {tuition_val}")
            cleaned_row['tuition'] = tuition_val

        return cleaned_row

    def ingest_file(self, file_path: str, format_override: Optional[str] = None) -> int:
        """
        Parses admissions data from a file and inserts it into the database.
        Detects CSV or JSON format, validates and converts all rows in a single atomic transaction.
        Returns the number of rows successfully imported.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine file format
        fmt = format_override
        if not fmt:
            _, ext = os.path.splitext(file_path)
            fmt = ext.lower().lstrip('.')

        if fmt not in ('csv', 'json'):
            raise ValueError(f"Unsupported file format: '{fmt}'. Only CSV and JSON are supported.")

        raw_records = []
        if fmt == 'csv':
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    return 0
                headers = [h.strip() for h in reader.fieldnames if h]
                if not headers:
                    return 0
                
                for row in reader:
                    cleaned_keys_row = {}
                    for k, v in row.items():
                        if k is not None:
                            cleaned_keys_row[k.strip()] = v
                    raw_records.append(cleaned_keys_row)
        else:  # json
            with open(file_path, mode='r', encoding='utf-8') as f:
                try:
                    content = json.load(f)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON file: {e}")
                
                if isinstance(content, list):
                    raw_records = content
                elif isinstance(content, dict):
                    for key in ('records', 'data', 'admissions'):
                        if key in content and isinstance(content[key], list):
                            raw_records = content[key]
                            break
                    else:
                        raise ValueError("JSON dictionary must contain a list of records under 'records' or 'data'")
                else:
                    raise ValueError("JSON root must be an array or a dictionary containing a list of records")

        if not raw_records:
            return 0

        # Validate all records before database insert (to ensure atomicity)
        validated_records = []
        for idx, row in enumerate(raw_records, start=1):
            validated_row = self.validate_and_convert(row, idx)
            validated_records.append(validated_row)

        # Database insertion within a single transaction
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            insert_query = '''
                INSERT INTO college_admissions (
                    province, year, category, college_code, college_name,
                    college_tags, city, major_code, major_name, plan_count,
                    min_score, min_rank, tuition
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            tuples_to_insert = [
                (
                    r['province'], r['year'], r['category'], r['college_code'], r['college_name'],
                    r['college_tags'], r['city'], r['major_code'], r['major_name'], r['plan_count'],
                    r['min_score'], r['min_rank'], r['tuition']
                )
                for r in validated_records
            ]
            
            cursor.executemany(insert_query, tuples_to_insert)
            conn.commit()
            return len(validated_records)
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Lucid Historical Admissions Data Ingester")
    parser.add_argument("file_path", help="Path to the CSV or JSON data file")
    parser.add_argument("--db", default="data/lucid.db", help="Path to the SQLite database (default: data/lucid.db)")
    parser.add_argument("--clear", action="store_true", help="Clear the admissions table before importing")
    parser.add_argument("--format", choices=["csv", "json"], help="Force specific file format (csv/json)")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    try:
        ingester = AdmissionsIngester(db_path=args.db)
        if args.clear:
            logging.info(f"Clearing existing records from 'college_admissions' in {args.db}...")
            ingester.clear_table()

        logging.info(f"Starting ingestion from {args.file_path} into {args.db}...")
        count = ingester.ingest_file(args.file_path, format_override=args.format)
        logging.info(f"Successfully imported {count} admissions records.")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Ingestion failed: {e}")
        sys.exit(1)
