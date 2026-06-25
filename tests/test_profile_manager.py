import os
import pytest
from src.profile_manager import ProfileManager

def test_profile_manager_flow():
    db_path = "test_profile_manager.db"
    # Ensure any old file is removed
    if os.path.exists(db_path):
        os.remove(db_path)
        
    try:
        pm = ProfileManager(db_path=db_path)
        
        # Test loading a profile that doesn't exist
        loaded = pm.load_profile("user_non_existent")
        assert loaded is None
        
        # Test saving a new profile
        profile = {
            "user_id": "test_user_id_1",
            "username": "王小明",
            "province": "Zhejiang",
            "score": 650,
            "rank": 5000,
            "category": "Physics",
            "subjects": "Physics,Chemistry,Biology",
            "eyesight_color": "Weak",
            "english_score": 115,
            "city_preferences": "Hangzhou,Shanghai"
        }
        pm.save_profile(profile)
        
        # Test loading the saved profile
        loaded = pm.load_profile("test_user_id_1")
        assert loaded is not None
        assert loaded["user_id"] == "test_user_id_1"
        assert loaded["username"] == "王小明"
        assert loaded["province"] == "Zhejiang"
        assert loaded["score"] == 650
        assert loaded["rank"] == 5000
        assert loaded["category"] == "Physics"
        assert loaded["subjects"] == "Physics,Chemistry,Biology"
        assert loaded["eyesight_color"] == "Weak"
        assert loaded["english_score"] == 115
        assert loaded["city_preferences"] == "Hangzhou,Shanghai"

        # Test updating the profile (upsert check)
        profile["username"] = "王大明"
        profile["score"] = 660
        pm.save_profile(profile)
        
        loaded_updated = pm.load_profile("test_user_id_1")
        assert loaded_updated["username"] == "王大明"
        assert loaded_updated["score"] == 660
        
        # Try saving profile with missing user_id
        with pytest.raises(ValueError):
            pm.save_profile({"username": "No ID Student"})
            
    finally:
        # Clean up database file
        if os.path.exists(db_path):
            os.remove(db_path)
