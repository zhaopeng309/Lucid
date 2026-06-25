import os
import json
import pytest
from unittest.mock import patch, MagicMock
from src.audit_engine import AdmissionsAuditEngine

@patch('src.audit_engine.chromadb.PersistentClient')
def test_admissions_audit_heuristics(mock_chroma):
    mock_collection = MagicMock()
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection
    
    # Mock retrieve_regulations returning color weakness and English score restrictions
    mock_collection.query.return_value = {
        "documents": [["本专业不招收色弱考生。高考英语单科成绩不低于110分。选考科目须选考物理和化学。"]]
    }
    
    # Do not pass :memory: to use PersistentClient which is mocked
    engine = AdmissionsAuditEngine()
    
    # 1. Test Color Weakness audit
    profile_weak_eyes = {
        "username": "Test Student",
        "eyesight_color": "Weak",
        "english_score": 120,
        "subjects": "Physics,Chemistry,Biology"
    }
    res = engine.audit_candidate(profile_weak_eyes, "Zhejiang University", "Clinical Medicine")
    assert res["is_excluded"] is True
    assert res["warning_level"] == "red"
    assert "色弱" in res["reason"]
    
    # 2. Test English Score too low audit
    profile_low_english = {
        "username": "Test Student",
        "eyesight_color": "Normal",
        "english_score": 105,
        "subjects": "Physics,Chemistry,Biology"
    }
    res = engine.audit_candidate(profile_low_english, "Zhejiang University", "English Language")
    assert res["is_excluded"] is True
    assert res["warning_level"] == "red"
    assert "英语" in res["reason"]
    
    # 3. Test Missing Subject requirements
    profile_no_physics = {
        "username": "Test Student",
        "eyesight_color": "Normal",
        "english_score": 120,
        "subjects": "Chemistry,Biology,History",
        "category": "History"
    }
    res = engine.audit_candidate(profile_no_physics, "Zhejiang University", "Computer Science")
    assert res["is_excluded"] is True
    assert res["warning_level"] == "red"
    assert "物理" in res["reason"]

    # 4. Test safe profile
    profile_safe = {
        "username": "Test Student",
        "eyesight_color": "Normal",
        "english_score": 115,
        "subjects": "Physics,Chemistry,Biology"
    }
    res = engine.audit_candidate(profile_safe, "Zhejiang University", "Computer Science")
    assert res["is_excluded"] is False
    assert res["warning_level"] == "green"


@patch('src.audit_engine.chromadb.PersistentClient')
@patch('src.audit_engine.genai.GenerativeModel')
def test_admissions_audit_gemini_api(mock_model_class, mock_chroma):
    mock_collection = MagicMock()
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection
    mock_collection.query.return_value = {
        "documents": [["Some regulations context."]]
    }
    
    mock_model_inst = MagicMock()
    mock_model_class.return_value = mock_model_inst
    
    # Mock Gemini response returning valid JSON
    mock_response = MagicMock()
    mock_response.text = '{"is_excluded": true, "warning_level": "red", "reason": "Excluded by LLM audit"}'
    mock_model_inst.generate_content.return_value = mock_response
    
    engine = AdmissionsAuditEngine()
    
    profile = {
        "username": "Test Student",
        "eyesight_color": "Normal",
        "english_score": 120,
        "subjects": "Physics,Chemistry,Biology"
    }
    
    # Pass real-looking API key to trigger Gemini path
    with patch.dict(os.environ, {"GEMINI_API_KEY": "real_api_key"}):
        res = engine.audit_candidate(profile, "Zhejiang University", "Physics")
        assert res["is_excluded"] is True
        assert res["warning_level"] == "red"
        assert res["reason"] == "Excluded by LLM audit"
        assert mock_model_inst.generate_content.called
