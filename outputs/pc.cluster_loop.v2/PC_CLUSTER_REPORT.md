# P-C 聚簇 + 同簇规则复用闭环报告

冻结参数：`{"threshold": 0.7, "feature_mode": "full-counts", "num_perm": 128, "seed": 20261123, "bands": 16, "rows": 8, "drift_threshold": 0.7}`

零模型调用、零网络。真实与合成分母分离；簇纯度≠提取准确率；唯一匹配≠正文完整。

## real 语料（13 页）

- complete-linkage 簇：`[["github"], ["gnu"], ["iana", "iana-abuse"], ["iana-whois"], ["mdn"], ["nasa"], ["python-appetite"], ["python-controlflow"], ["python-interpreter"], ["python-introduction"], ["python-library-index"], ["python-search"]]`
- 抗链式违规：0；连通分量：11（链式警告 1）
- 簇纯度：精度 1.0000 / 召回 0.0769 / ARI 0.1220
- LSH：候选 3 / 全对 78；对精确≥0.7 正例召回 1.0000
- 规则复用：派生 12 次 / 13 页（节省代理 0.0769）；转移成员复用率 1.0；回退 0（0.0000）；漂移 0

| 成员 | 簇 | 代表 | 复用 | 回退 | 漂移 | 指纹相似 | 规则状态 | 原因 |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| github | c0 | Y | True | False | False | 1.000 | ok |  |
| gnu | c1 | Y | True | False | False | 1.000 | ok |  |
| iana | c2 | Y | True | False | False | 1.000 | ok |  |
| iana-abuse | c2 |  | True | False | False | 0.724 | ok |  |
| iana-whois | c3 | Y | True | False | False | 1.000 | ok |  |
| mdn | c4 | Y | True | False | False | 1.000 | ok |  |
| nasa | c5 | Y | True | False | False | 1.000 | ok |  |
| python-appetite | c6 | Y | True | False | False | 1.000 | ok |  |
| python-controlflow | c7 | Y | True | False | False | 1.000 | ok |  |
| python-interpreter | c8 | Y | True | False | False | 1.000 | ok |  |
| python-introduction | c9 | Y | True | False | False | 1.000 | ok |  |
| python-library-index | c10 | Y | True | False | False | 1.000 | ok |  |
| python-search | c11 | Y | True | False | False | 1.000 | ok |  |

## controlled 语料（5 页）

- complete-linkage 簇：`[["class-drift", "content-moved", "reference", "role-drift"], ["duplicate-main"]]`
- 抗链式违规：0；连通分量：2（链式警告 0）
- 簇纯度：精度 0.5000 / 召回 1.0000 / ARI 0.4444
- LSH：候选 10 / 全对 10；对精确≥0.7 正例召回 1.0000
- 规则复用：派生 1 次 / 5 页（节省代理 0.8000）；转移成员复用率 0.666667；回退 2（0.4000）；漂移 2

| 成员 | 簇 | 代表 | 复用 | 回退 | 漂移 | 指纹相似 | 规则状态 | 原因 |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| class-drift | c0 | Y | True | False | False | 1.000 | ok |  |
| content-moved | c0 |  | True | False | False | 0.727 | ok |  |
| reference | c0 |  | True | False | False | 1.000 | ok |  |
| role-drift | c0 |  | False | True | True | 1.000 | rule_no_match | rule_failure |
| duplicate-main | c1 | Y | False | True | True | 1.000 | no_rule | no_shared_rule |

## 局限

- 小语料（real 13 + synthetic 5），非生产规模；"千亿级"仅业务语境。
- iana-help 为跨站评估族（同属 development manifest），非严格独立采集 holdout；阈值 0.7 继承先前冻结消融。
- 确定性规则派生器是结构化启发式（非 LLM Agent）；Agentic RL/GRPO 属 P-E（gated）。
- 指纹排除属性 → role-drift 类漂移靠规则执行校验捕获（非指纹）；content-moved 规则 ok 但正文不完整（quality 揭示）。
- LSH 为概率候选过滤；本小语料 definitive 聚簇用精确全对，LSH 召回实测见上。
