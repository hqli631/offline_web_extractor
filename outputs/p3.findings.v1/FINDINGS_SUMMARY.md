# P3 校准复审 findings 摘要

- 复审者：hqli631（2026-11-22）｜ 案卷：10
- verdict 分布：{"judge_correct": 5, "human_correct": 4, "anchor_ambiguous": 0, "both_partially_correct": 1}
- 分类分布：{"B_judge_stricter": {"judge_correct": 1, "human_correct": 2, "anchor_ambiguous": 0, "both_partially_correct": 1}, "A_injection_gold_miss": {"judge_correct": 3, "human_correct": 0, "anchor_ambiguous": 0, "both_partially_correct": 0}, "C_judge_missed": {"judge_correct": 1, "human_correct": 2, "anchor_ambiguous": 0, "both_partially_correct": 0}}
- 锚点修订建议：0 条；amendment_signal=True（仅触发预注册提案起草，不自动改协议）

| 案卷 | 类别 | verdict | note |
| --- | --- | --- | --- |
| cal-interpreter-noise | B_judge_stricter | judge_correct |  |
| cal-interpreter-instruction_interference | A_injection_gold_miss | judge_correct |  |
| cal-nasa-clean | C_judge_missed | human_correct |  |
| cal-nasa-missing_paragraph | B_judge_stricter | both_partially_correct |  |
| cal-nasa-noise | B_judge_stricter | human_correct |  |
| cal-nasa-duplicate | C_judge_missed | judge_correct |  |
| cal-nasa-instruction_interference | A_injection_gold_miss | judge_correct |  |
| cal-w3ca11y-noise | B_judge_stricter | human_correct |  |
| cal-w3ca11y-reorder | C_judge_missed | human_correct |  |
| cal-w3ca11y-instruction_interference | A_injection_gold_miss | judge_correct |  |
