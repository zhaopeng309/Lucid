import pandas as pd
from typing import List, Dict, Any

class ReportExporter:
    def __init__(self):
        pass

    def export_console_table(self, ranked_pool: pd.DataFrame) -> str:
        """
        导出控制台表格
        :param ranked_pool: 包含胜率和梯度的志愿推荐表
        :return: 格式化的字符串
        """
        if ranked_pool.empty:
            return "没有符合条件的志愿推荐。"

        df = ranked_pool.copy()
        
        # Sort by probability descending
        df = df.sort_values(by='probability', ascending=False)

        # Format probability as percentage
        df['probability_str'] = df['probability'].apply(lambda x: f"{x*100:.1f}%")

        # Normalize school name column
        if 'school_name' not in df.columns and 'college_name' in df.columns:
            df['school_name'] = df['college_name']

        # Select columns to display
        columns_to_display = ['school_name', 'major_name', 'city', 'school_level', 'tuition', 'probability_str', 'gradient', 'warning_level', 'audit_reason']
        
        # Keep only existing columns
        existing_columns = [col for col in columns_to_display if col in df.columns]
        
        display_df = df[existing_columns]
        
        # Rename columns for better readability
        rename_mapping = {
            'school_name': '学校名称',
            'major_name': '专业名称',
            'city': '城市',
            'school_level': '院校级别',
            'tuition': '学费',
            'probability_str': '录取概率',
            'gradient': '志愿梯度',
            'warning_level': '风险等级',
            'audit_reason': '排雷说明'
        }
        display_df = display_df.rename(columns=rename_mapping)

        return display_df.to_string(index=False)
