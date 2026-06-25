import os
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from src.engine import RecommendationEngine
from src.reporter import ReportExporter

@patch('src.audit_engine.chromadb.PersistentClient')
def test_end_to_end_recommendation_and_audit(mock_chroma):
    mock_collection = MagicMock()
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection
    
    # Query returns eyesight and english score limit
    mock_collection.query.return_value = {
        "documents": [["本专业要求考生高考英语单科成绩不低于110分。选考科目要求物理。"]]
    }
    
    # Setup RecommendationEngine
    # Using a custom db_path to make sure mock is clean
    engine = RecommendationEngine(db_path='data/chroma_db')
    
    # Setup input candidate dataframe
    mock_colleges = pd.DataFrame({
        'school_name': ['School B', 'School C'],
        'major_name': ['Computer Science', 'English Language'],
        'city': ['Beijing', 'Shanghai'],
        'school_level': ['211', 'Ordinary'],
        'tuition': [6000, 15000],
        'historical_lowest_rank': [5000, 6000],
        'historical_ranks': [[4800, 4900, 5200, 5100], [5800, 5900, 6200, 6100]]
    })
    
    # Setup candidate profile who has english score 105 and has chosen Physics
    user_profile = {
        "user_id": "test_student",
        "username": "李华",
        "province": "Zhejiang",
        "score": 630,
        "rank": 5000,
        "category": "Physics",
        "subjects": "Physics,Chemistry,Biology",
        "eyesight_color": "Normal",
        "english_score": 105
    }
    
    # Run probability ranking with user_profile
    ranked_pool = engine.probability_ranking(5000, mock_colleges, user_profile=user_profile)
    
    # Assert new columns exist in DataFrame
    assert 'is_excluded' in ranked_pool.columns
    assert 'warning_level' in ranked_pool.columns
    assert 'audit_reason' in ranked_pool.columns
    
    # School B should have is_excluded = True because of english score = 105 < 110
    school_b_row = ranked_pool[ranked_pool['school_name'] == 'School B'].iloc[0]
    assert school_b_row['is_excluded']
    assert school_b_row['warning_level'] == 'red'
    assert "英语" in school_b_row['audit_reason']

    # Export to console table
    exporter = ReportExporter()
    output = exporter.export_console_table(ranked_pool)
    
    # Assert headers for risk and reason exist in console output
    assert "风险等级" in output
    assert "排雷说明" in output
    assert "red" in output
    assert "School B" in output
    assert "李华" not in output # Profile details should not clutter the row entries, only audit output
