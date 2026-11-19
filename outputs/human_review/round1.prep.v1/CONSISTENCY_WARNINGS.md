# P0 盲评标签 · 协议一致性待确认项

这些不是格式错误，是你的判断与冻结 Rubrics v2 决策规则之间的张力。
**工具不会替你改**，请你逐条决定：改 decision、改 severity，或维持并写理由（记为校准发现）。

| 盲码 | 你的 decision | 提示 | 说明 |
| --- | --- | --- | --- |
| B18 | uncertain | major_or_critical_but_not_fail | Rubrics v2: a major/critical problem implies fail. severe dims=['cleanliness'] |
| B21 | fail | decision_fail_without_major_or_critical | Rubrics v2: fail requires a major/critical problem. Either raise a severity or change the decision. dims={'completeness': 'none', 'cleanliness': 'none', 'structure': 'minor', 'title': 'none', 'format': 'none'} |

