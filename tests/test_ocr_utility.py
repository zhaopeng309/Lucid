import os
import sys
import pytest
import sqlite3
import pandas as pd
from PIL import Image
from unittest.mock import MagicMock, patch

# Ensure the project root and util directory are in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'util'))

from util.ocr_score_rank import clean_csv_response, process_data, import_to_db

def test_clean_csv_response():
    """Test that markdown code blocks are correctly stripped from Gemini response."""
    raw_response_1 = "```csv\nscore,num_at_score,cumulative_rank\n650,10,100\n649,15,115\n```"
    expected = "score,num_at_score,cumulative_rank\n650,10,100\n649,15,115"
    assert clean_csv_response(raw_response_1) == expected

    raw_response_2 = "score,num_at_score,cumulative_rank\n650,10,100"
    assert clean_csv_response(raw_response_2) == raw_response_2

    raw_response_3 = "```\nscore,num_at_score,cumulative_rank\n650,10,100\n```"
    assert clean_csv_response(raw_response_3) == "score,num_at_score,cumulative_rank\n650,10,100"


def test_process_data_valid():
    """Test parsing raw CSV and auto-calculating rank_start and other fields."""
    raw_csv = "score,num_at_score,cumulative_rank\n650,10,100\n649,15,115"
    
    df = process_data(raw_csv, province="Hunan", year=2025, category="Physics")
    
    assert len(df) == 2
    
    # Assert correctness of computed and supplied fields
    row1 = df.iloc[0]
    assert row1['year'] == 2025
    assert row1['province'] == "Hunan"
    assert row1['category'] == "Physics"
    assert row1['score'] == 650
    assert row1['count'] == 10
    assert row1['rank_end'] == 100
    assert row1['rank_start'] == 91  # 100 - 10 + 1

    row2 = df.iloc[1]
    assert row2['score'] == 649
    assert row2['count'] == 15
    assert row2['rank_end'] == 115
    assert row2['rank_start'] == 101  # 115 - 15 + 1


def test_process_data_fuzzy_headers():
    """Test that the utility can auto-map Chinese headers or different column cases."""
    raw_csv = "分数,本分人数,累计人数\n650,10,100\n649,15,115"
    
    df = process_data(raw_csv, province="Sichuan", year=2024, category="History")
    
    assert len(df) == 2
    row1 = df.iloc[0]
    assert row1['score'] == 650
    assert row1['count'] == 10
    assert row1['rank_end'] == 100
    assert row1['rank_start'] == 91


def test_process_data_invalid_raises():
    """Test that parsing failure exits gracefully or raises error on missing critical columns."""
    raw_csv = "invalid,header,only\n1,2,3"
    with pytest.raises(SystemExit):
        process_data(raw_csv, province="Hunan", year=2025, category="Physics")


def test_database_import():
    """Test importing processed dataframe into SQLite database's one_mark_one_rank table."""
    db_path = "test_ocr_lucid.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    data = {
        'year': [2025, 2025],
        'province': ['Hunan', 'Hunan'],
        'category': ['Physics', 'Physics'],
        'score': [650, 649],
        'rank_start': [91, 101],
        'rank_end': [100, 115],
        'count': [10, 15]
    }
    df = pd.DataFrame(data)
    
    try:
        # Import to DB
        import_to_db(df, db_path)
        
        # Query DB to check entries
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM one_mark_one_rank ORDER BY score DESC")
        rows = cursor.fetchall()
        
        assert len(rows) == 2
        # Assert schema elements
        # (year, province, category, score, rank_start, rank_end, count)
        assert rows[0] == (2025, "Hunan", "Physics", 650, 91, 100, 10)
        assert rows[1] == (2025, "Hunan", "Physics", 649, 101, 115, 15)
        
        # Test cleaning duplicates on re-import
        new_data = {
            'year': [2025],
            'province': ['Hunan'],
            'category': ['Physics'],
            'score': [650],
            'rank_start': [95],
            'rank_end': [100],
            'count': [6]
        }
        df_new = pd.DataFrame(new_data)
        import_to_db(df_new, db_path)
        
        cursor.execute("SELECT * FROM one_mark_one_rank WHERE year=2025 AND province='Hunan' AND category='Physics'")
        rows_after = cursor.fetchall()
        
        assert len(rows_after) == 1
        assert rows_after[0] == (2025, "Hunan", "Physics", 650, 95, 100, 6)
        
        conn.close()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


@patch('util.ocr_score_rank.run_ocr')
@patch('util.ocr_score_rank.import_to_db')
def test_cli_main_flow(mock_import_to_db, mock_run_ocr):
    """Test full command line flow using mock arguments."""
    mock_run_ocr.return_value = "score,num_at_score,cumulative_rank\n600,5,50"
    
    test_img = "test_image.png"
    # Create a dummy image
    img = Image.new('RGB', (100, 100), color = 'red')
    img.save(test_img)
    
    test_output_csv = "data/test_out.csv"
    if os.path.exists(test_output_csv):
        os.remove(test_output_csv)
        
    try:
        from util.ocr_score_rank import main
        
        test_args = [
            "ocr_score_rank.py",
            "--image", test_img,
            "--province", "Zhejiang",
            "--year", "2025",
            "--category", "Comprehensive",
            "--output", test_output_csv,
            "--import-db",
            "--db-path", "test_ocr_lucid.db"
        ]
        
        with patch('sys.argv', test_args):
            main()
            
        # Assert run_ocr was called with image path
        mock_run_ocr.assert_called_once_with(test_img)
        
        # Check that CSV was written
        assert os.path.exists(test_output_csv)
        df = pd.read_csv(test_output_csv)
        assert len(df) == 1
        assert df.iloc[0]['score'] == 600
        assert df.iloc[0]['rank_start'] == 46
        
        # Assert import_to_db was called with the dataframe and db_path
        mock_import_to_db.assert_called_once()
        called_df = mock_import_to_db.call_args[0][0]
        called_db = mock_import_to_db.call_args[0][1]
        assert called_db == "test_ocr_lucid.db"
        assert len(called_df) == 1
        assert called_df.iloc[0]['score'] == 600
        
    finally:
        if os.path.exists(test_img):
            os.remove(test_img)
        if os.path.exists(test_output_csv):
            os.remove(test_output_csv)
