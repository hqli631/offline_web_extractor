# P3 校准复审索引

分歧案卷 10 例（判据：decision_mismatch / dim_gap_ge2 / judge_missed_defect / judge_severe_human_not）。
解封呈现（事后复审，非盲评）：真实案例名 + judge 证据 + human gold + silver 变异。

## 类别
- A 注入漏检：instruction_interference 3 例（候选含注入块，human 给 4/none）
- B judge 偏严：noise/missing 4 例（judge major vs human minor）
- C judge 漏标：human minor 而 judge none（nasa-clean/nasa-duplicate/w3ca11y-reorder）

## 工作流
1. 逐案读 packets/C##.md（§1 对照 → §2 judge 引用 → §3 变异证据）。
2. 在 p3_findings.json 填 reviewer/review_date/discipline_ack=true 与逐案 verdict/note。
3. 交回助手汇总 findings；如需锚点修订 → 预注册 freeze 修订提案（judge v1.3 候选），不事后调参。

## 案卷清单
- C01 cal-interpreter-noise [development]：decision_mismatch, judge_severe_human_not:cleanliness
- C02 cal-interpreter-instruction_interference [development]：decision_mismatch, dim_gap_ge2:cleanliness, dim_gap_ge2:completeness, dim_gap_ge2:structure, judge_severe_human_not:cleanliness, judge_severe_human_not:completeness, judge_severe_human_not:structure
- C03 cal-nasa-clean [frozen_test]：judge_missed_defect:cleanliness
- C04 cal-nasa-missing_paragraph [frozen_test]：decision_mismatch, judge_severe_human_not:completeness
- C05 cal-nasa-noise [frozen_test]：decision_mismatch, judge_severe_human_not:cleanliness
- C06 cal-nasa-duplicate [frozen_test]：judge_missed_defect:cleanliness
- C07 cal-nasa-instruction_interference [frozen_test]：decision_mismatch, dim_gap_ge2:cleanliness, dim_gap_ge2:completeness, judge_severe_human_not:cleanliness, judge_severe_human_not:completeness
- C08 cal-w3ca11y-noise [frozen_test]：decision_mismatch, judge_severe_human_not:cleanliness
- C09 cal-w3ca11y-reorder [frozen_test]：judge_missed_defect:structure
- C10 cal-w3ca11y-instruction_interference [frozen_test]：decision_mismatch, dim_gap_ge2:cleanliness, judge_severe_human_not:cleanliness
