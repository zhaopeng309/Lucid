import os
import sqlite3
import pytest
import pandas as pd
from util.ingest_websites import UniversityIngester

@pytest.fixture
def temp_db(tmp_path):
    """Fixture to provide a clean temporary database path."""
    db_path = str(tmp_path / "test_lucid.db")
    return db_path

@pytest.fixture
def ingester(temp_db):
    """Fixture to provide a fresh UniversityIngester instance with a clean DB."""
    return UniversityIngester(db_path=temp_db)

def test_table_initialization(temp_db):
    """Verify that UniversityIngester creates the college_profiles table upon initialization."""
    ingester = UniversityIngester(db_path=temp_db)
    
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Check that college_profiles table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='college_profiles'")
    assert cursor.fetchone() is not None
    
    # Check table structure
    cursor.execute("PRAGMA table_info(college_profiles)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}
    assert "school_name" in columns
    assert "location_of_school" in columns
    assert "administrative_department" in columns
    assert "school_identification_code" in columns
    assert "level_of_education" in columns
    assert "school_type" in columns
    assert "website" in columns
    
    conn.close()

def test_ingest_valid_excel(ingester, tmp_path):
    """Test ingestion of a valid Excel sheet with some messy column spaces."""
    # Create a mock DataFrame
    data = {
        'school_name': ['北京大学', '清华大学'],
        ' location_of_school': [' 北京市 ', '北京市'],  # has leading space in header, and spaces in values
        'administrative_department': ['教育部', '教育部'],
        'school_identification_code': [4111010001, '4111010002'],  # mixed types (int and str)
        'level_of_education': ['本科', '本科'],
        'school_type': ['公办', '公办'],
        'website': ['http://www.pku.edu.cn', 'https://www.tsinghua.edu.cn']
    }
    df = pd.DataFrame(data)
    
    # Save to a temporary Excel file
    excel_file = tmp_path / "test_universities.xlsx"
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='University', index=False)
        
    imported_count = ingester.ingest_excel(str(excel_file))
    assert imported_count == 2
    
    # Verify in database
    conn = sqlite3.connect(ingester.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM college_profiles ORDER BY school_name ASC")
    rows = cursor.fetchall()
    conn.close()
    
    assert len(rows) == 2
    
    # Check Peking University details
    # '北京大学' is index 0 in sorted order
    pku = rows[0]
    assert pku[0] == "北京大学"
    assert pku[1] == "北京市"  # verified whitespace is trimmed
    assert pku[2] == "教育部"
    assert pku[3] == "4111010001"  # verified integer converted to string
    assert pku[4] == "本科"
    assert pku[5] == "公办"
    assert pku[6] == "http://www.pku.edu.cn"

def test_duplicate_prevention_and_upsert(ingester, tmp_path):
    """Test that ingestion prevents duplicates and updates existing entries correctly."""
    # Step 1: Ingest first record
    data1 = {
        'school_name': ['北京大学'],
        ' location_of_school': ['北京市'],
        'administrative_department': ['教育部'],
        'school_identification_code': ['4111010001'],
        'level_of_education': ['本科'],
        'school_type': ['公办'],
        'website': ['http://www.pku.edu.cn']
    }
    df1 = pd.DataFrame(data1)
    excel_file1 = tmp_path / "test1.xlsx"
    df1.to_excel(excel_file1, sheet_name='University', index=False)
    
    count1 = ingester.ingest_excel(str(excel_file1))
    assert count1 == 1
    
    # Step 2: Ingest updated record for same school name
    data2 = {
        'school_name': ['北京大学'],
        ' location_of_school': ['北京市'],
        'administrative_department': ['教育部'],
        'school_identification_code': ['4111010001'],
        'level_of_education': ['本科'],
        'school_type': ['公办'],
        'website': ['https://new.pku.edu.cn']  # website updated to https and new subdomain
    }
    df2 = pd.DataFrame(data2)
    excel_file2 = tmp_path / "test2.xlsx"
    df2.to_excel(excel_file2, sheet_name='University', index=False)
    
    count2 = ingester.ingest_excel(str(excel_file2))
    assert count2 == 1
    
    # Verify in database that there is only 1 entry and website was updated
    conn = sqlite3.connect(ingester.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM college_profiles")
    rows = cursor.fetchall()
    conn.close()
    
    assert len(rows) == 1
    assert rows[0][0] == "北京大学"
    assert rows[0][6] == "https://new.pku.edu.cn"

def test_validation_missing_required_field(ingester, tmp_path):
    """Test that missing required fields raise ValueError."""
    data = {
        'school_name': ['北京大学', '清华大学'],
        ' location_of_school': ['北京市', ''],  # Tsinghua missing location
        'administrative_department': ['教育部', '教育部'],
        'school_identification_code': ['4111010001', '4111010002'],
        'level_of_education': ['本科', '本科'],
        'school_type': ['公办', '公办'],
        'website': ['http://www.pku.edu.cn', 'https://www.tsinghua.edu.cn']
    }
    df = pd.DataFrame(data)
    excel_file = tmp_path / "invalid.xlsx"
    df.to_excel(excel_file, sheet_name='University', index=False)
    
    with pytest.raises(ValueError) as exc_info:
        ingester.ingest_excel(str(excel_file))
    assert "Missing value for required field" in str(exc_info.value)

def test_validation_invalid_url_format(ingester, tmp_path):
    """Test that non-standard website URL formats are allowed (with warnings) instead of crashing."""
    data = {
        'school_name': ['北京大学'],
        ' location_of_school': ['北京市'],
        'administrative_department': ['教育部'],
        'school_identification_code': ['4111010001'],
        'level_of_education': ['本科'],
        'school_type': ['公办'],
        'website': ['invalid_url_no_dots_or_protocols']  # invalid URL
    }
    df = pd.DataFrame(data)
    excel_file = tmp_path / "invalid_url.xlsx"
    df.to_excel(excel_file, sheet_name='University', index=False)
    
    count = ingester.ingest_excel(str(excel_file))
    assert count == 1
    
    # Verify it is imported and contains the note/value
    conn = sqlite3.connect(ingester.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT website FROM college_profiles WHERE school_name='北京大学'")
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None
    assert row[0] == "invalid_url_no_dots_or_protocols"
