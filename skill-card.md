## Description: <br>
高考志愿智能推荐与招生章程 RAG 风控排雷系统。采用等效位次化和高斯正态分布累积积分算法，精确量化“冲稳保垫”胜率，并基于 ChromaDB + Gemini 大语言模型技术对目标高校招生章程进行全方位排雷审计（包含单科、选科及体检限制）。 <br>

This skill is ready for commercial/non-commercial use. <br>

## Publisher: <br>
小龙虾 🦞 <br>

### License/Terms of Use: <br>
MIT <br>


## Use Case: <br>
高考考生、家长及志愿规划师使用本系统，通过输入考生基础位次与选科情况，自动匹配、推荐高匹配度的志愿高校及专业，并能有效避免因招生简章中体检、选科及单科分数限制引发的滑档和退档风险。 <br>

### Deployment Geography for Use: <br>
中国（新高考与传统高考省份） <br>

## Known Risks and Mitigations: <br>
Risk: 大模型可能在分析极其偏门的招生条件时产生幻觉（Hallucination），漏掉细微限制。 <br>
Mitigation: 结合了离线启发式正则提取双重保障机制，在关键结果后明示免责声明，建议填报前由人工校对省教育考试院和各高校官方发布的纸质招生简章。 <br>
Risk: 概率计算结果基于历史往年录取分布，若当年发生重大报考人数剧变或招生政策调整可能存在预测偏差。 <br>
Mitigation: 采用多维可配带宽粗排以及往年提档位次的均值和标准差建模，同时在报表中提醒预测精度的变化区间。 <br>


## Reference(s): <br>
- [Database Design](plan/Database_Design.md) <br>
- [Algorithm Design](plan/Algorithm_Design.md) <br>
- [Lucid Development Plan](plan/Lucid_Development_Plan.md) <br>


## Skill Output: <br>
**Output Type(s):** [Guidance, Quantitative Reports, Recommendations, Risk Warnings] <br>
**Output Format:** [Markdown Structured Reports with Detailed Evaluation Matrix] <br>
**Output Parameters:** [Candidate Profile Checkpoint, REACH / MATCH / SAFETY / FALL-BACK Matrix, RAG Check Remarks] <br>
**Other Properties Related to Output:** [输出必须使用对话状态机分步提问引导，生成最终志愿推荐表前必须由考生进行 Checkpoint 确认。] <br>

## Skill Version(s): <br>
1.0.0 <br>

## Ethical Considerations: <br>
高考填报志愿关乎考生前途命运。系统仅提供客观数据建议与风险分析，绝不替代考生的最终决策。建议充分了解考生个人志趣、身体状况后审慎使用。 <br>
