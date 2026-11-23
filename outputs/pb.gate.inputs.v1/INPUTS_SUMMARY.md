# P-B gate inputs (zero-call, sealed-derived)

- dev orig: 12 cases (as-ran v1.2; iana x2 source_only, rest with_gold)
- dev P2: 6 cases (filtered from 18; frozen_test v2 excluded)
- overlay corrections: C01, C02, A01 (all judge_correct, sealed findings)
- sealed gold NOT rewritten; overlay is a derived artifact with full provenance.

| code | case | before -> after |
| --- | --- | --- |
| C01 | cal-interpreter-noise | cleanliness 3/minor -> 2/major; decision uncertain -> fail |
| C02 | cal-interpreter-instruction_interference | cleanliness 4/none -> 1/critical; completeness 4/none -> 2/major; structure 4/none -> 2/major; decision uncertain -> fail |
| A01 | cal-appetite-reorder | structure 3/minor -> 2/major; decision uncertain -> fail |

局限：单标注者；overlay 3 例存在锚定循环性（dev 轨道）；v3 为独立泛化检验；一致率≠准确率。
