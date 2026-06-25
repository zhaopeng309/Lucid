import pytest
import os
import pandas as pd
from src.mapper import RankScoreMapper

@pytest.fixture
def mapper():
    db_path = 'test_lucid.db'
    if os.path.exists(db_path):
        os.remove(db_path)
    
    m = RankScoreMapper(db_path=db_path)
    
    # Mock data
    data = {
        'year': [2025, 2025, 2025],
        'province': ['Zhejiang', 'Zhejiang', 'Zhejiang'],
        'category': ['Physics', 'Physics', 'Physics'],
        'score': [650, 649, 648],
        'rank_start': [1000, 1050, 1100],
        'rank_end': [1049, 1099, 1150],
        'count': [50, 50, 51]
    }
    df = pd.DataFrame(data)
    m.import_data(df)
    
    yield m
    
    if os.path.exists(db_path):
        os.remove(db_path)

def test_score_to_rank(mapper):
    res = mapper.score_to_rank(2025, 'Zhejiang', 'Physics', 650)
    assert res is not None
    assert res['rank_start'] == 1000
    assert res['rank_end'] == 1049

def test_rank_to_score(mapper):
    score = mapper.rank_to_score(2025, 'Zhejiang', 'Physics', 1020)
    assert score == 650

def test_invalid_score(mapper):
    res = mapper.score_to_rank(2025, 'Zhejiang', 'Physics', 750)
    assert res is None
