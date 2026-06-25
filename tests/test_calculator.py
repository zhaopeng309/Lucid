import pytest
from src.calculator import ProbabilityCalculator

def test_probability_calculation():
    calc = ProbabilityCalculator(min_sigma=100)
    
    # Example: historical ranks mean = 5000, std = 200
    # User rank = 5000 -> probability should be 0.5
    prob = calc.calculate_probability(5000, [4800, 5000, 5200])
    assert pytest.approx(prob, 0.01) == 0.5

    # User rank = 4000 (better than mean) -> probability should be high
    prob_high = calc.calculate_probability(4000, [4800, 5000, 5200])
    assert prob_high > 0.9

    # User rank = 6000 (worse than mean) -> probability should be low
    prob_low = calc.calculate_probability(6000, [4800, 5000, 5200])
    assert prob_low < 0.1

def test_get_gradient():
    calc = ProbabilityCalculator()
    
    assert calc.get_gradient(0.1) is None
    assert calc.get_gradient(0.2) == 'Reach'
    assert calc.get_gradient(0.5) == 'Match'
    assert calc.get_gradient(0.8) == 'Safety'
    assert calc.get_gradient(0.98) == 'Fall-back'

def test_min_sigma():
    calc = ProbabilityCalculator(min_sigma=100)
    # std = 0
    prob = calc.calculate_probability(5000, [5000, 5000, 5000])
    assert pytest.approx(prob, 0.01) == 0.5
