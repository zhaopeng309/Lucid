import pytest
import pandas as pd
from src.engine import RecommendationEngine

@pytest.fixture
def mock_colleges():
    data = {
        'school_name': ['School A', 'School B', 'School C', 'School D'],
        'city': ['Shanghai', 'Beijing', 'Shanghai', 'Guangzhou'],
        'school_level': ['985', '211', 'Ordinary', '985'],
        'tuition': [5000, 6000, 15000, 5500],
        'historical_lowest_rank': [4000, 5000, 6000, 7000],
        'historical_ranks': [[3800, 3900, 4200, 4100], [4800, 4900, 5200, 5100], [5800, 5900, 6200, 6100], [6800, 6900, 7200, 7100]]
    }
    return pd.DataFrame(data)

def test_rough_sort(mock_colleges):
    engine = RecommendationEngine()
    # User rank = 5000, up_bound = -20% -> 4000, down_bound = +30% -> 6500
    # Should include School A (4000), School B (5000), School C (6000)
    rough_pool = engine.rough_sort(5000, mock_colleges)
    
    assert len(rough_pool) == 3
    assert 'School D' not in rough_pool['school_name'].values

def test_fine_sort(mock_colleges):
    engine = RecommendationEngine()
    
    # test cities
    prefs = {'cities': ['Shanghai']}
    fine_pool = engine.fine_sort(mock_colleges, prefs)
    assert len(fine_pool) == 2
    assert all(fine_pool['city'] == 'Shanghai')
    
    # test multiple preferences
    prefs = {
        'cities': ['Shanghai', 'Beijing'],
        'school_levels': ['985', '211'],
        'max_tuition': 6000
    }
    fine_pool = engine.fine_sort(mock_colleges, prefs)
    # Should be A (Shanghai, 985, 5000) and B (Beijing, 211, 6000)
    assert len(fine_pool) == 2
    assert 'School C' not in fine_pool['school_name'].values

def test_probability_ranking(mock_colleges):
    engine = RecommendationEngine()
    
    # User rank 5000 (Same as School B's mean rank)
    # School B ranks: [4800, 4900, 5200, 5100] -> mean = 5000
    # Expected prob for School B = 0.5 (Match)
    
    # School A ranks: mean = 4000. Prob for 5000 will be low (< 0.15), should be filtered out
    # School C ranks: mean = 6000. Prob for 5000 will be high (Safety/Fall-back)
    
    ranked_pool = engine.probability_ranking(5000, mock_colleges)
    
    assert 'probability' in ranked_pool.columns
    assert 'gradient' in ranked_pool.columns
    
    # School A should be filtered out (probability too low)
    assert 'School A' not in ranked_pool['school_name'].values
    
    school_b_row = ranked_pool[ranked_pool['school_name'] == 'School B']
    assert not school_b_row.empty
    prob_b = school_b_row['probability'].values[0]
    assert pytest.approx(prob_b, 0.01) == 0.5
    assert school_b_row['gradient'].values[0] == 'Match'
    
    school_c_row = ranked_pool[ranked_pool['school_name'] == 'School C']
    assert not school_c_row.empty
    prob_c = school_c_row['probability'].values[0]
    assert prob_c > 0.95
    assert school_c_row['gradient'].values[0] == 'Fall-back'

