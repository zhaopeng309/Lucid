import pandas as pd
from typing import List, Dict, Any
from src.calculator import ProbabilityCalculator

class RecommendationEngine:
    def __init__(self, up_bound_ratio=-0.2, down_bound_ratio=0.3, db_path='data/chroma_db'):
        self.up_bound_ratio = up_bound_ratio
        self.down_bound_ratio = down_bound_ratio
        self.prob_calculator = ProbabilityCalculator()
        self.db_path = db_path

    def rough_sort(self, user_rank: int, colleges_data: pd.DataFrame) -> pd.DataFrame:
        """
        粗排：位次带宽扩张筛选
        :param user_rank: 考生全省位次
        :param colleges_data: 包含学校/专业近几年最低录取位次等数据的 DataFrame
                              需要包含 'historical_lowest_rank' 字段，代表该专业近年的位次均值或最低值
        :return: 初筛的高校和专业大池子
        """
        if colleges_data.empty:
            return colleges_data

        # 向上浮动（位次数值变小）和向下浮动（位次数值变大）
        min_rank = int(user_rank * (1 + self.up_bound_ratio))
        max_rank = int(user_rank * (1 + self.down_bound_ratio))
        
        # 确保 rank 为正数
        min_rank = max(1, min_rank)

        filtered_df = colleges_data[
            (colleges_data['historical_lowest_rank'] >= min_rank) & 
            (colleges_data['historical_lowest_rank'] <= max_rank)
        ]
        
        return filtered_df

    def fine_sort(self, rough_pool: pd.DataFrame, preferences: Dict[str, Any]) -> pd.DataFrame:
        """
        精排：多维用户偏好过滤
        :param rough_pool: 粗排大池子
        :param preferences: 偏好字典，如 {'cities': ['Shanghai', 'Beijing'], 'school_levels': ['985', '211'], 'max_tuition': 10000}
        :return: 经过过滤的中池子
        """
        if rough_pool.empty or not preferences:
            return rough_pool

        filtered_pool = rough_pool.copy()

        # 1. 城市过滤
        if 'cities' in preferences and preferences['cities']:
            filtered_pool = filtered_pool[filtered_pool['city'].isin(preferences['cities'])]

        # 2. 院校级别过滤
        if 'school_levels' in preferences and preferences['school_levels']:
            filtered_pool = filtered_pool[filtered_pool['school_level'].isin(preferences['school_levels'])]

        # 3. 学费过滤
        if 'max_tuition' in preferences and preferences['max_tuition'] is not None:
            filtered_pool = filtered_pool[filtered_pool['tuition'] <= preferences['max_tuition']]

        return filtered_pool

    def probability_ranking(self, user_rank: int, fine_pool: pd.DataFrame, user_profile: dict = None) -> pd.DataFrame:
        """
        概率分布分档算法
        :param user_rank: 考生位次 R_user
        :param fine_pool: 过滤后的中池子
        :param user_profile: 可选的考生 profile，若提供则对每个候选志愿进行 AdmissionsAuditEngine 风控排雷
        :return: 包含精确胜率数值的“冲、稳、保、垫”及排雷警告的梯度推荐表
        """
        if fine_pool.empty:
            return fine_pool

        ranked_pool = fine_pool.copy()
        
        probabilities = []
        gradients = []
        
        for index, row in ranked_pool.iterrows():
            historical_ranks = row.get('historical_ranks', [])
            if not isinstance(historical_ranks, list) or len(historical_ranks) == 0:
                probabilities.append(0.0)
                gradients.append(None)
                continue
                
            prob = self.prob_calculator.calculate_probability(user_rank, historical_ranks)
            gradient = self.prob_calculator.get_gradient(prob)
            
            probabilities.append(prob)
            gradients.append(gradient)
            
        ranked_pool['probability'] = probabilities
        ranked_pool['gradient'] = gradients
        
        # Filter out rows where gradient is None (probability < 0.15)
        ranked_pool = ranked_pool[ranked_pool['gradient'].notna()]

        if user_profile is not None:
            from src.audit_engine import AdmissionsAuditEngine
            audit_engine = AdmissionsAuditEngine(db_path=self.db_path)
            
            is_excluded_list = []
            warning_level_list = []
            audit_reason_list = []
            
            for index, row in ranked_pool.iterrows():
                college_name = row.get('school_name') or row.get('college_name') or "Unknown College"
                major_name = row.get('major_name') or "Unknown Major"
                
                audit_res = audit_engine.audit_candidate(user_profile, college_name, major_name)
                is_excluded_list.append(audit_res.get('is_excluded', False))
                warning_level_list.append(audit_res.get('warning_level', 'green'))
                audit_reason_list.append(audit_res.get('reason', ''))
                
            ranked_pool['is_excluded'] = is_excluded_list
            ranked_pool['warning_level'] = warning_level_list
            ranked_pool['audit_reason'] = audit_reason_list
        
        return ranked_pool
