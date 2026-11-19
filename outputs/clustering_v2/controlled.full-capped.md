# DOM结构相似度原型

显式阈值：0.7；特征模式：full-capped。

固定特征设置：`{"mode": "full-capped", "path_scope": "body-relative full tag path", "multiplicity": "capped counts", "ignored": "all text, attributes, sibling indexes and head", "count_cap": 3, "feature": "full-capped", "skipped_tags": ["noscript", "script", "style", "template"], "metric": "multiset Jaccard", "threshold": 0.7, "clustering": "threshold-edge connected components"}`

| 页面对 | 相似度 | 人工同组 | 阈值连边 | 最终同簇 | 样本类型 |
| --- | ---: | --- | --- | --- | --- |
| reference / class-drift | 1.0000 | True | True | True | synthetic/synthetic |
| reference / role-drift | 1.0000 | True | True | True | synthetic/synthetic |
| reference / duplicate-main | 0.8182 | False | True | True | synthetic/synthetic |
| reference / content-moved | 0.7273 | False | True | True | synthetic/synthetic |
| class-drift / role-drift | 1.0000 | True | True | True | synthetic/synthetic |
| class-drift / duplicate-main | 0.8182 | False | True | True | synthetic/synthetic |
| class-drift / content-moved | 0.7273 | False | True | True | synthetic/synthetic |
| role-drift / duplicate-main | 0.8182 | False | True | True | synthetic/synthetic |
| role-drift / content-moved | 0.7273 | False | True | True | synthetic/synthetic |
| duplicate-main / content-moved | 0.6154 | False | False | True | synthetic/synthetic |

连通分量：[["class-drift", "content-moved", "duplicate-main", "reference", "role-drift"]]

误聚页面对：7；漏聚页面对：0。

这是标签结构基线；模板分组不保证同一XPath可复用，也不保证正文完整。阈值应在验证前冻结；站点公共外壳与包装层可能主导分数。

链式聚簇警告：{"component": ["class-drift", "content-moved", "duplicate-main", "reference", "role-drift"], "below_threshold_pairs": [{"left": "content-moved", "right": "duplicate-main", "score": 0.6153846153846154}]}
