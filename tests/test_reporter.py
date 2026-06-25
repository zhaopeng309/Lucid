import pytest
import pandas as pd
from src.reporter import ReportExporter

@pytest.fixture
def mock_ranked_pool():
    data = {
        'school_name': ['School C', 'School B', 'School A'],
        'city': ['Shanghai', 'Beijing', 'Shanghai'],
        'school_level': ['Ordinary', '211', '985'],
        'tuition': [15000, 6000, 5000],
        'probability': [0.98, 0.50, 0.10],
        'gradient': ['Fall-back', 'Match', 'Reach']
    }
    return pd.DataFrame(data)

def test_export_console_table(mock_ranked_pool):
    exporter = ReportExporter()
    output = exporter.export_console_table(mock_ranked_pool)
    
    assert "School C" in output
    assert "98.0%" in output
    assert "Fall-back" in output
    assert "School B" in output
    assert "50.0%" in output
    assert "Match" in output
    assert "School A" in output
    assert "10.0%" in output
    assert "Reach" in output

    # Check headers
    assert "学校名称" in output
    assert "录取概率" in output
    assert "志愿梯度" in output

def test_export_console_table_empty():
    exporter = ReportExporter()
    output = exporter.export_console_table(pd.DataFrame())
    
    assert "没有符合条件的志愿推荐" in output
