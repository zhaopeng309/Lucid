import numpy as np
from scipy.stats import norm

class ProbabilityCalculator:
    def __init__(self, min_sigma=100):
        self.min_sigma = min_sigma

    def calculate_probability(self, user_rank, historical_ranks):
        """
        Calculate the acceptance probability using Gaussian cumulative distribution function.
        
        :param user_rank: integer, user's equivalent rank
        :param historical_ranks: list of integers, historical lowest accepted ranks
        :return: float, probability of acceptance (0.0 to 1.0)
        """
        if not historical_ranks:
            return 0.0

        mu = np.mean(historical_ranks)
        sigma = np.std(historical_ranks, ddof=1) if len(historical_ranks) > 1 else 0

        if sigma < 10:
            sigma = self.min_sigma

        # Probability that cutoff rank is greater than or equal to user rank
        # P(R_cutoff >= R_user) = Phi((mu - R_user) / sigma)
        probability = norm.cdf((mu - user_rank) / sigma)
        
        return probability

    def get_gradient(self, probability):
        """
        Map probability to a recommendation gradient.
        
        :param probability: float (0.0 to 1.0)
        :return: string, gradient category or None if invalid
        """
        if probability < 0.15:
            return None # Too low, discard
        elif probability < 0.45:
            return 'Reach' # 冲
        elif probability < 0.75:
            return 'Match' # 稳
        elif probability < 0.95:
            return 'Safety' # 保
        else:
            return 'Fall-back' # 垫
