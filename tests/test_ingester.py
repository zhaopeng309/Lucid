import os
import sqlite3
import pytest
import json
from src.ingester import AdmissionsIngester

@pytest.fixture
def temp_db(tmp_path):
    """Fixture to provide a clean temporary database path."""
    db_path = str(tmp_path / "test_lucid.db")
    return db_path

@pytest.fixture
def ingester(temp_db):
    """Fixture to provide a fresh AdmissionsIngester instance with a clean DB."""
    return AdmissionsIngester(db_path=temp_db)

def test_db_initialization(temp_db):
    """Verify that AdmissionsIngester creates the table and indices upon initialization."""
    # Instance creation triggers _init_db
    ingester = AdmissionsIngester(db_path=temp_db)
    
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Check that college_admissions table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='college_admissions'")
    assert cursor.fetchone() is not None
    
    # Check indices are created
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='college_admissions'")
    indices = [row[0] for row in cursor.fetchall()]
    assert "idx_query_rank" in indices
    assert "idx_college_name" in indices
    
    conn.close()

def test_ingest_valid_csv(ingester, tmp_path):
    """Test ingestion of a valid CSV file with mixed spacing, optional fields, and normal values."""
    csv_content = """ province ,year,category, college_code ,college_name,college_tags,city,major_code,major_name,plan_count,min_score,min_rank,tuition
Zhejiang ,2025.0,Physics,10001,Peking University,"985,211",Beijing,01,Computer Science, 10 , 680 , 50 , 5000.0
Sichuan,2025,Comprehensive,10002,Tsinghua University,,Beijing,02,Software Engineering,5,690,15,
"""
    csv_file = tmp_path / "test_admissions.csv"
    csv_file.write_text(csv_content, encoding="utf-8")
    
    imported_count = ingester.ingest_file(str(csv_file))
    assert imported_count == 2
    
    # Verify records in the database
    conn = sqlite3.connect(ingester.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM college_admissions ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    
    assert len(rows) == 2
    
    # Check row 1 details
    r1 = rows[0]
    assert r1[1] == "Zhejiang"      # province
    assert r1[2] == 2025            # year (float 2025.0 converted to int)
    assert r1[3] == "Physics"       # category
    assert r1[4] == "10001"         # college_code
    assert r1[5] == "Peking University" # college_name
    assert r1[6] == "985,211"       # college_tags (whitespace trimmed)
    assert r1[7] == "Beijing"       # city
    assert r1[8] == "01"            # major_code
    assert r1[9] == "Computer Science" # major_name
    assert r1[10] == 10             # plan_count
    assert r1[11] == 680            # min_score
    assert r1[12] == 50             # min_rank
    assert r1[13] == 5000           # tuition (float 5000.0 converted to int)

    # Check row 2 details
    r2 = rows[1]
    assert r2[1] == "Sichuan"
    assert r2[2] == 2025
    assert r2[3] == "Comprehensive"
    assert r2[4] == "10002"
    assert r2[5] == "Tsinghua University"
    assert r2[6] == "" or r2[6] is None  # college_tags is empty string or None
    assert r2[7] == "Beijing"
    assert r2[8] == "02"
    assert r2[9] == "Software Engineering"
    assert r2[10] == 5
    assert r2[11] == 690
    assert r2[12] == 15
    assert r2[13] == 0              # tuition defaults to 0 if empty string

def test_ingest_valid_json_list(ingester, tmp_path):
    """Test ingestion of a valid JSON file containing a list of records."""
    records = [
        {
            "province": "Zhejiang",
            "year": 2025,
            "category": "Physics",
            "college_code": "10001",
            "college_name": "Peking University",
            "college_tags": "985",
            "city": "Beijing",
            "major_code": "01",
            "major_name": "CS",
            "plan_count": 10,
            "min_score": 680,
            "min_rank": 50,
            "tuition": 5000
        }
    ]
    json_file = tmp_path / "test.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(records, f)
        
    count = ingester.ingest_file(str(json_file))
    assert count == 1
    
    # Clear table
    ingester.clear_table()
    # Confirm clear
    conn = sqlite3.connect(ingester.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM college_admissions")
    assert cursor.fetchone()[0] == 0
    conn.close()

def test_ingest_valid_json_dict(ingester, tmp_path):
    """Test ingestion of a valid JSON file where the records are nested under a standard list key."""
    data = {
        "records": [
            {
                "province": "Zhejiang",
                "year": 2024,
                "category": "Physics",
                "college_code": "10001",
                "college_name": "Peking University",
                "city": "Beijing",
                "major_code": "01",
                "major_name": "CS",
                "plan_count": 5,
                "min_score": 670,
                "min_rank": 60
                # optional fields omitted
            }
        ]
    }
    json_file = tmp_path / "test.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f)
        
    count = ingester.ingest_file(str(json_file))
    assert count == 1

def test_ingest_empty_files(ingester, tmp_path):
    """Verify that empty files or files with no entries do not cause exceptions and return 0."""
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("", encoding="utf-8")
    assert ingester.ingest_file(str(empty_csv)) == 0

    empty_json = tmp_path / "empty.json"
    with open(empty_json, "w", encoding="utf-8") as f:
        json.dump([], f)
    assert ingester.ingest_file(str(empty_json)) == 0

def test_ingest_validation_missing_required(ingester, tmp_path):
    """Test validation failure when a required field is missing (atomic rollback validation)."""
    # First row is valid, second row misses 'min_score'
    csv_content = """province,year,category,college_code,college_name,city,major_code,major_name,plan_count,min_score,min_rank
Zhejiang,2025,Physics,10001,Peking,Beijing,01,CS,10,680,50
Sichuan,2025,Comprehensive,10002,Tsinghua,Beijing,02,SE,5,,15
"""
    csv_file = tmp_path / "invalid.csv"
    csv_file.write_text(csv_content, encoding="utf-8")
    
    with pytest.raises(ValueError) as excinfo:
        ingester.ingest_file(str(csv_file))
        
    assert "Missing required field 'min_score'" in str(excinfo.value)
    
    # Ensure atomic rollback: even though the first row was valid, nothing should be in DB
    conn = sqlite3.connect(ingester.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM college_admissions")
    assert cursor.fetchone()[0] == 0
    conn.close()

def test_ingest_validation_invalid_types(ingester, tmp_path):
    """Test validation failure with invalid types for integer fields."""
    csv_content = """province,year,category,college_code,college_name,city,major_code,major_name,plan_count,min_score,min_rank
Zhejiang,2025.5,Physics,10001,Peking,Beijing,01,CS,10,680,50
"""
    csv_file = tmp_path / "invalid.csv"
    csv_file.write_text(csv_content, encoding="utf-8")
    
    with pytest.raises(ValueError) as excinfo:
        ingester.ingest_file(str(csv_file))
    assert "Field 'year' must be an integer" in str(excinfo.value)

    # Invalid non-numeric string for min_rank
    csv_content = """province,year,category,college_code,college_name,city,major_code,major_name,plan_count,min_score,min_rank
Zhejiang,2025,Physics,10001,Peking,Beijing,01,CS,10,680,not-an-int
"""
    csv_file.write_text(csv_content, encoding="utf-8")
    with pytest.raises(ValueError) as excinfo:
        ingester.ingest_file(str(csv_file))
    assert "Field 'min_rank' must be an integer" in str(excinfo.value)

def test_ingest_validation_out_of_bounds(ingester, tmp_path):
    """Test validation failure when values violate logical constraints."""
    # Negative plan_count
    csv_content = """province,year,category,college_code,college_name,city,major_code,major_name,plan_count,min_score,min_rank
Zhejiang,2025,Physics,10001,Peking,Beijing,01,CS,-1,680,50
"""
    csv_file = tmp_path / "invalid.csv"
    csv_file.write_text(csv_content, encoding="utf-8")
    with pytest.raises(ValueError) as excinfo:
        ingester.ingest_file(str(csv_file))
    assert "Field 'plan_count' value -1 must be non-negative" in str(excinfo.value)

    # Invalid year
    csv_content = """province,year,category,college_code,college_name,city,major_code,major_name,plan_count,min_score,min_rank
Zhejiang,1800,Physics,10001,Peking,Beijing,01,CS,10,680,50
"""
    csv_file.write_text(csv_content, encoding="utf-8")
    with pytest.raises(ValueError) as excinfo:
        ingester.ingest_file(str(csv_file))
    assert "Field 'year' value 1800 must be greater than 1900" in str(excinfo.value)

    # Invalid min_rank (must be >= 1)
    csv_content = """province,year,category,college_code,college_name,city,major_code,major_name,plan_count,min_score,min_rank
Zhejiang,2025,Physics,10001,Peking,Beijing,01,CS,10,680,0
"""
    csv_file.write_text(csv_content, encoding="utf-8")
    with pytest.raises(ValueError) as excinfo:
        ingester.ingest_file(str(csv_file))
    assert "Field 'min_rank' value 0 must be a positive integer (>= 1)" in str(excinfo.value)

    # Negative tuition
    csv_content = """province,year,category,college_code,college_name,city,major_code,major_name,plan_count,min_score,min_rank,tuition
Zhejiang,2025,Physics,10001,Peking,Beijing,01,CS,10,680,50,-100
"""
    csv_file.write_text(csv_content, encoding="utf-8")
    with pytest.raises(ValueError) as excinfo:
        ingester.ingest_file(str(csv_file))
    assert "Field 'tuition' cannot be negative, got -100" in str(excinfo.value)

def test_ingest_empty_required_strings(ingester, tmp_path):
    """Test validation failure when a required string field is empty or only whitespace."""
    csv_content = """province,year,category,college_code,college_name,city,major_code,major_name,plan_count,min_score,min_rank
 ,2025,Physics,10001,Peking,Beijing,01,CS,10,680,50
"""
    csv_file = tmp_path / "invalid.csv"
    csv_file.write_text(csv_content, encoding="utf-8")
    with pytest.raises(ValueError) as excinfo:
        ingester.ingest_file(str(csv_file))
    assert "Field 'province' cannot be empty or whitespace only" in str(excinfo.value)

def test_ingest_file_not_found(ingester):
    """Verify that FileNotFoundError is raised if file does not exist."""
    with pytest.raises(FileNotFoundError):
        ingester.ingest_file("does_not_exist.csv")

def test_ingest_unsupported_format(ingester, tmp_path):
    """Verify that ValueError is raised for unsupported formats."""
    some_file = tmp_path / "data.txt"
    some_file.write_text("random text", encoding="utf-8")
    with pytest.raises(ValueError) as excinfo:
        ingester.ingest_file(str(some_file))
    assert "Unsupported file format" in str(excinfo.value)
