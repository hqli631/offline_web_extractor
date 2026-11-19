# DOM结构相似度原型

显式阈值：0.7；特征模式：semantic-presence。

固定特征设置：`{"mode": "semantic-presence", "path_scope": "body-relative full tag path", "multiplicity": "presence (one per distinct feature)", "ignored": "all text, class, id, URLs, sibling indexes and head", "semantic_roles": ["article", "banner", "complementary", "contentinfo", "main", "navigation", "region", "search"], "semantic_source": "main/nav/aside/article tags and bounded explicit ARIA roles", "feature": "semantic-presence", "skipped_tags": ["noscript", "script", "style", "template"], "metric": "multiset Jaccard", "threshold": 0.7, "clustering": "threshold-edge connected components"}`

| 页面对 | 相似度 | 人工同组 | 阈值连边 | 最终同簇 | 样本类型 |
| --- | ---: | --- | --- | --- | --- |
| reference / class-drift | 1.0000 | True | True | True | synthetic/synthetic |
| reference / role-drift | 0.6000 | True | False | False | synthetic/synthetic |
| reference / duplicate-main | 1.0000 | False | True | True | synthetic/synthetic |
| reference / content-moved | 0.8571 | False | True | True | synthetic/synthetic |
| class-drift / role-drift | 0.6000 | True | False | False | synthetic/synthetic |
| class-drift / duplicate-main | 1.0000 | False | True | True | synthetic/synthetic |
| class-drift / content-moved | 0.8571 | False | True | True | synthetic/synthetic |
| role-drift / duplicate-main | 0.6000 | False | False | False | synthetic/synthetic |
| role-drift / content-moved | 0.5294 | False | False | False | synthetic/synthetic |
| duplicate-main / content-moved | 0.8571 | False | True | True | synthetic/synthetic |

连通分量：[["class-drift", "content-moved", "duplicate-main", "reference"], ["role-drift"]]

误聚页面对：5；漏聚页面对：2。

这是标签结构基线；模板分组不保证同一XPath可复用，也不保证正文完整。阈值应在验证前冻结；站点公共外壳与包装层可能主导分数。
